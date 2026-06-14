import json
import logging
import os
import random
import threading
import time

import gspread
from flask import Flask, jsonify, render_template, request, session
from oauth2client.service_account import ServiceAccountCredentials


def _bool_from_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_from_env(name, default, minimum=None):
    raw_value = os.environ.get(name)
    if raw_value is None or str(raw_value).strip() == "":
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be greater than or equal to {minimum}")
    return value


# Application configuration
GOOGLE_SHEET_URL = os.environ.get("GOOGLE_SHEET_URL", "").strip()
SECRET_KEY = os.environ.get("SECRET_KEY")
PORT = _int_from_env("PORT", 5000, minimum=1)
DEBUG = _bool_from_env("DEBUG", False)

# Cache configuration
CACHE_TTL_SECONDS = _int_from_env("CACHE_TTL_SECONDS", 300, minimum=0)

# Quiz configuration
QUIZ_TIME_SECONDS = _int_from_env("QUIZ_TIME_SECONDS", 10, minimum=1)
MASTERY_THRESHOLD = _int_from_env("MASTERY_THRESHOLD", 10, minimum=1)
NUM_OPTIONS = _int_from_env("NUM_OPTIONS", 4, minimum=2)
REQUIRED_COLUMNS = ("Phrases", "One Word", "Corrects", "Attempts")

# Initialize Flask app
app = Flask(__name__)

# Security: require a stable secret key outside debug mode.
if not SECRET_KEY:
    if not DEBUG:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    SECRET_KEY = os.urandom(24)

app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global sheet variable and locks
sheet = None
_sheet_init_lock = threading.Lock()

# In-process TTL cache for sheet data
_cache_lock = threading.Lock()
_sheet_cache = {
    "records": None,           # list of row dicts; each row includes internal __row_index
    "headers": None,           # list of header names
    "header_map": None,        # header name -> 1-based column index
    "phrase_row_map": None,    # phrase -> row index in sheet (1-based)
    "incorrect_pool": None,    # unique list of incorrect answers
    "ts": 0,
}


def clean_text(value):
    """Return a safe stripped string for sheet/user values."""
    if value is None:
        return ""
    return str(value).strip()


def safe_int(value, default=0):
    """Convert common sheet values to int without crashing on blanks/bad cells."""
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    value = clean_text(value)
    if not value:
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def get_row_value(row_values, one_based_col, default=""):
    """Safely read a 1-based column from a sparse Google Sheet row."""
    index = one_based_col - 1
    if index < 0 or index >= len(row_values):
        return default
    return row_values[index]


def clear_sheet_cache():
    """Clear cached sheet data."""
    with _cache_lock:
        _sheet_cache.update({
            "records": None,
            "headers": None,
            "header_map": None,
            "phrase_row_map": None,
            "incorrect_pool": None,
            "ts": 0,
        })


def _load_google_credentials(scope):
    """Load service-account credentials from JSON env or a local file."""
    credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if credentials_json:
        try:
            credentials_info = json.loads(credentials_json)
        except json.JSONDecodeError as exc:
            raise ValueError("GOOGLE_CREDENTIALS_JSON is not valid JSON") from exc
        return ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)

    credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    return ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)


def initialize_sheet(force=False):
    """Initialize Google Sheets connection exactly once unless force=True."""
    global sheet

    with _sheet_init_lock:
        if sheet is not None and not force:
            return sheet

        if not GOOGLE_SHEET_URL:
            raise ValueError("GOOGLE_SHEET_URL environment variable is not set")

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        creds = _load_google_credentials(scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1
        clear_sheet_cache()
        logger.info("Successfully connected to Google Sheets")
        return sheet


def ensure_sheet_initialized():
    """Lazy-init Sheets so WSGI deployments work after importing index:app."""
    if sheet is None:
        initialize_sheet()
    return sheet


def _rebuild_cache_locked():
    """Assumes _cache_lock is held. Fetch data from sheet and build helper maps."""
    if sheet is None:
        raise RuntimeError("Sheet not initialized")

    raw_records = sheet.get_all_records()  # full read only when cache misses/expires
    headers = [clean_text(header) for header in sheet.row_values(1)]
    header_map = {header: index + 1 for index, header in enumerate(headers) if header}

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in header_map]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise RuntimeError(f"Google Sheet is missing required column(s): {missing}")

    records = []
    phrase_row_map = {}
    incorrect_pool = []
    seen_answers = set()

    # get_all_records returns data rows starting from sheet row 2.
    for index, raw_row in enumerate(raw_records):
        row_index = index + 2
        row = dict(raw_row)
        row["__row_index"] = row_index

        phrase = clean_text(row.get("Phrases"))
        one_word = clean_text(row.get("One Word"))

        if phrase and phrase not in phrase_row_map:
            phrase_row_map[phrase] = row_index

        answer_key = one_word.casefold()
        if one_word and answer_key not in seen_answers:
            incorrect_pool.append(one_word)
            seen_answers.add(answer_key)

        records.append(row)

    _sheet_cache.update({
        "records": records,
        "headers": headers,
        "header_map": header_map,
        "phrase_row_map": phrase_row_map,
        "incorrect_pool": incorrect_pool,
        "ts": time.time(),
    })


def get_sheet_data_cached():
    """Return cached sheet records, rebuilding if TTL expired."""
    now = time.time()
    with _cache_lock:
        if _sheet_cache["records"] is not None and (now - _sheet_cache["ts"] < CACHE_TTL_SECONDS):
            return _sheet_cache["records"]
        _rebuild_cache_locked()
        return _sheet_cache["records"]


def get_cached_helpers():
    """Return cache helper maps, rebuilding on miss/expiry."""
    with _cache_lock:
        if _sheet_cache["records"] is None or (time.time() - _sheet_cache["ts"] >= CACHE_TTL_SECONDS):
            _rebuild_cache_locked()
        return (
            _sheet_cache["header_map"],
            _sheet_cache["phrase_row_map"],
            _sheet_cache["incorrect_pool"],
        )


def build_options(correct_answer, incorrect_pool):
    """Build unique multiple-choice options around the correct answer."""
    correct_key = correct_answer.casefold()
    wrong_answers = []
    seen = {correct_key}

    for answer in incorrect_pool or []:
        answer = clean_text(answer)
        answer_key = answer.casefold()
        if answer and answer_key not in seen:
            wrong_answers.append(answer)
            seen.add(answer_key)

    sample_size = min(NUM_OPTIONS - 1, len(wrong_answers))
    options = [correct_answer] + random.sample(wrong_answers, sample_size)
    random.shuffle(options)
    return options


@app.route("/health")
def health():
    """Small health endpoint for deployment platforms."""
    return jsonify({
        "status": "ok",
        "sheet_configured": bool(GOOGLE_SHEET_URL),
    })


@app.route("/")
def quiz():
    """Display a random quiz question from Google Sheets."""
    try:
        ensure_sheet_initialized()
        data = get_sheet_data_cached()
        _, _, incorrect_pool = get_cached_helpers()

        # Only serve usable questions that have not reached the mastery threshold.
        available_questions = [
            row for row in data
            if clean_text(row.get("Phrases"))
            and clean_text(row.get("One Word"))
            and safe_int(row.get("Corrects")) < MASTERY_THRESHOLD
        ]

        if not available_questions:
            logger.info("All phrases mastered or no valid questions available")
            return render_template("quiz.html", complete=True)

        row = random.choice(available_questions)
        current_phrase = clean_text(row.get("Phrases"))
        correct_answer = clean_text(row.get("One Word"))
        row_index = safe_int(row.get("__row_index"))

        correct_count = safe_int(row.get("Corrects"))
        attempts_count = safe_int(row.get("Attempts"))

        # Store in session for /answer endpoint.
        session["current_phrase"] = current_phrase
        session["correct_answer"] = correct_answer
        session["current_row_index"] = row_index
        session.permanent = True

        options = build_options(correct_answer, incorrect_pool)
        logger.info("Serving quiz for sheet row %s", row_index)

        return render_template(
            "quiz.html",
            complete=False,
            phrase=current_phrase,
            options=options,
            correct=correct_count,
            attempts=attempts_count,
            remaining=len(available_questions),
            quiz_time=QUIZ_TIME_SECONDS,
        )
    except Exception as exc:
        logger.error("Quiz route error: %s", exc, exc_info=True)
        return render_template(
            "error.html",
            error_title="Error Loading Quiz",
            error_message="The quiz could not be loaded. Check the server configuration and Google Sheet columns.",
        ), 500


@app.route("/answer", methods=["POST"])
def answer():
    """Process the user's answer and update the Google Sheet."""
    try:
        selected_option = clean_text(request.form.get("option"))
        current_phrase = clean_text(session.get("current_phrase"))
        correct_answer = clean_text(session.get("correct_answer"))
        row_index = safe_int(session.get("current_row_index"))

        if not current_phrase or not correct_answer:
            logger.warning("Missing session data for answer submission")
            return jsonify({"error": "Session expired. Please refresh the page."}), 401

        ensure_sheet_initialized()
        is_correct = selected_option == correct_answer
        logger.info("Answer submitted for sheet row %s: %s", row_index, is_correct)

        header_map, phrase_row_map, _ = get_cached_helpers()
        if row_index <= 1:
            row_index = safe_int(phrase_row_map.get(current_phrase))

        if row_index <= 1:
            try:
                cell = sheet.find(current_phrase)
                row_index = cell.row
            except gspread.exceptions.CellNotFound:
                logger.error("Phrase not found in sheet: %s", current_phrase)
                return jsonify({"error": "Question not found in database"}), 404

        attempts_col = header_map.get("Attempts")
        corrects_col = header_map.get("Corrects")
        if attempts_col is None or corrects_col is None:
            logger.error("Required columns are not present in sheet headers")
            return jsonify({"error": "Server configuration error"}), 500

        max_attempts = 3
        for attempt_no in range(1, max_attempts + 1):
            try:
                row_values = sheet.row_values(row_index)
                current_attempts = safe_int(get_row_value(row_values, attempts_col))
                current_corrects = safe_int(get_row_value(row_values, corrects_col))

                updates = [
                    {
                        "range": gspread.utils.rowcol_to_a1(row_index, attempts_col),
                        "values": [[current_attempts + 1]],
                    }
                ]
                if is_correct:
                    updates.append({
                        "range": gspread.utils.rowcol_to_a1(row_index, corrects_col),
                        "values": [[current_corrects + 1]],
                    })

                sheet.batch_update(updates)

                with _cache_lock:
                    records = _sheet_cache.get("records")
                    if records:
                        record_index = row_index - 2
                        if 0 <= record_index < len(records):
                            records[record_index]["Attempts"] = current_attempts + 1
                            if is_correct:
                                records[record_index]["Corrects"] = current_corrects + 1
                            _sheet_cache["ts"] = time.time()

                for key in ("current_phrase", "correct_answer", "current_row_index"):
                    session.pop(key, None)

                logger.info("Sheet updated successfully for row %s", row_index)
                break
            except gspread.exceptions.APIError as exc:
                logger.warning("API error updating sheet on attempt %s: %s", attempt_no, exc)
                if attempt_no == max_attempts:
                    return jsonify({"error": "Failed to update progress"}), 500
                time.sleep(0.2 * attempt_no)
            except Exception as exc:
                logger.error("Sheet update error: %s", exc, exc_info=True)
                return jsonify({"error": "Failed to update progress"}), 500

        return jsonify({
            "is_correct": is_correct,
            "correct_answer": correct_answer,
        })
    except Exception as exc:
        logger.error("Answer route error: %s", exc, exc_info=True)
        return jsonify({"error": "Server error"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning("404 error: %s", request.path)
    return render_template(
        "error.html",
        error_title="Page Not Found",
        error_message="The page you're looking for doesn't exist.",
    ), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error("500 error: %s", error, exc_info=True)
    return render_template(
        "error.html",
        error_title="Server Error",
        error_message="An unexpected error occurred. Please try again later.",
    ), 500


if __name__ == "__main__":
    initialize_sheet()
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
