import os
import logging
import random
import gspread
import time
import threading
from datetime import datetime, timedelta
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template, request, session, jsonify

# Configuration from environment variables
GOOGLE_SHEET_URL = os.environ.get("GOOGLE_SHEET_URL")
SECRET_KEY = os.environ.get("SECRET_KEY")
PORT = int(os.environ.get("PORT", 5000))
DEBUG = os.environ.get("DEBUG", "False").lower() == "true"

# Cache configuration
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", 300))  # default 5 minutes

# Quiz configuration
QUIZ_TIME_SECONDS = int(os.environ.get("QUIZ_TIME_SECONDS", 10))
MASTERY_THRESHOLD = int(os.environ.get("MASTERY_THRESHOLD", 10))
NUM_OPTIONS = 4

# Initialize Flask app
app = Flask(__name__)

# Security: Require SECRET_KEY in production
if not SECRET_KEY:
    if not DEBUG:
        raise ValueError("SECRET_KEY environment variable must be set in production")
    SECRET_KEY = os.urandom(24)

app.secret_key = SECRET_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global sheet variable
sheet = None

# In-process TTL cache for sheet data
_cache_lock = threading.Lock()
_sheet_cache = {
    "records": None,           # list of row dicts (as returned by get_all_records)
    "headers": None,           # list of header names
    "header_map": None,        # header name -> 1-based column index
    "phrase_row_map": None,    # phrase -> row index in sheet (1-based)
    "incorrect_pool": None,    # list of incorrect answers
    "ts": 0,
}


def initialize_sheet():
    """Initialize Google Sheets connection."""
    global sheet

    if not GOOGLE_SHEET_URL:
        raise ValueError("GOOGLE_SHEET_URL environment variable not set")

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(GOOGLE_SHEET_URL).sheet1
        logger.info("Successfully connected to Google Sheets")
    except FileNotFoundError:
        logger.error("credentials.json file not found")
        raise
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        raise


def _rebuild_cache_locked():
    """Assumes _cache_lock is held. Fetch data from sheet and build helper maps."""
    global _sheet_cache
    if sheet is None:
        raise RuntimeError("Sheet not initialized")

    records = sheet.get_all_records()  # full read only when cache miss
    headers = sheet.row_values(1)
    header_map = {h: i + 1 for i, h in enumerate(headers)}

    # get_all_records returns rows starting from sheet row 2
    phrase_row_map = {}
    incorrect_pool = []
    for i, row in enumerate(records):
        row_index = i + 2
        phrase = (row.get("Phrases") or "").strip()
        one_word = (row.get("One Word") or "").strip()
        if phrase:
            phrase_row_map[phrase] = row_index
        if one_word:
            incorrect_pool.append(one_word)

    _sheet_cache.update({
        "records": records,
        "headers": headers,
        "header_map": header_map,
        "phrase_row_map": phrase_row_map,
        "incorrect_pool": incorrect_pool,
        "ts": time.time(),
    })


def get_sheet_data_cached():
    """Return cached sheet data, rebuilding if TTL expired.

    Returns the list of records (dicts). Helper maps are kept in global cache.
    """
    global _sheet_cache
    now = time.time()
    with _cache_lock:
        if _sheet_cache["records"] is not None and (now - _sheet_cache["ts"] < CACHE_TTL_SECONDS):
            return _sheet_cache["records"]
        # Cache miss/expired: rebuild
        _rebuild_cache_locked()
        return _sheet_cache["records"]


def get_cached_helpers():
    """Return header_map and phrase_row_map; rebuild cache on miss.
    Caller should not mutate returned structures.
    """
    with _cache_lock:
        if _sheet_cache["records"] is None or (time.time() - _sheet_cache["ts"] >= CACHE_TTL_SECONDS):
            _rebuild_cache_locked()
        return _sheet_cache["header_map"], _sheet_cache["phrase_row_map"], _sheet_cache["incorrect_pool"]


def clear_sheet_cache():
    """Clear the cached sheet data."""
    global _sheet_cache
    with _cache_lock:
        _sheet_cache.update({
            "records": None,
            "headers": None,
            "header_map": None,
            "phrase_row_map": None,
            "incorrect_pool": None,
            "ts": 0,
        })


@app.route("/")
def quiz():
    """Display a random quiz question from Google Sheets."""
    try:
        if sheet is None:
            logger.error("Sheet not initialized")
            return render_template(
                "error.html",
                error_title="Configuration Error",
                error_message="The application is not properly configured. Please try again later."
            ), 500

        # Get cached data to reduce API calls
        data = get_sheet_data_cached()
        header_map, phrase_row_map, incorrect_pool = get_cached_helpers()

        # Filter questions that haven't reached mastery threshold
        df_filtered = [row for row in data if int(row.get("Corrects", 0)) < MASTERY_THRESHOLD]

        if not df_filtered:
            logger.info("All phrases mastered")
            return render_template("quiz.html", complete=True)

        row = random.choice(df_filtered)
        current_phrase = (row.get("Phrases", "") or "").strip()
        correct_answer = (row.get("One Word", "") or "").strip()

        if not current_phrase or not correct_answer:
            logger.error("Invalid row data in sheet")
            return render_template(
                "error.html",
                error_title="Data Error",
                error_message="Invalid data in the quiz sheet. Please contact support."
            ), 500

        correct_count = int(row.get("Corrects", 0))
        attempts_count = int(row.get("Attempts", 0))

        # Store in session for /answer endpoint
        session["current_phrase"] = current_phrase
        session["correct_answer"] = correct_answer
        session.permanent = True

        # Build options list using cached pool (avoid rebuilding from full data each request)
        # exclude the correct answer from pool
        pool = [x for x in incorrect_pool if x != correct_answer]
        if not pool:
            logger.warning("Not enough incorrect options available")
            pool = ["Option A", "Option B", "Option C"]

        options = [correct_answer] + random.sample(
            pool,
            min(NUM_OPTIONS - 1, len(pool))
        )
        random.shuffle(options)

        logger.info(f"Serving quiz for phrase: {current_phrase}")

        return render_template(
            "quiz.html",
            complete=False,
            phrase=current_phrase,
            options=options,
            correct=correct_count,
            attempts=attempts_count,
            remaining=len(df_filtered),
            quiz_time=QUIZ_TIME_SECONDS,
        )
    except Exception as e:
        logger.error(f"Quiz route error: {e}", exc_info=True)
        return render_template(
            "error.html",
            error_title="Error Loading Quiz",
            error_message="An unexpected error occurred. Please try again later."
        ), 500


@app.route("/answer", methods=["POST"])
def answer():
    """Process the user's answer and update the Google Sheet."""
    try:
        # Get and validate form data
        selected_option = (request.form.get("option", "") or "").strip()
        current_phrase = (session.get("current_phrase", "") or "").strip()
        correct_answer = (session.get("correct_answer", "") or "").strip()

        if not current_phrase or not correct_answer:
            logger.warning("Missing session data for answer submission")
            return jsonify({"error": "Session expired. Please refresh the page."}), 401

        if sheet is None:
            logger.error("Sheet not initialized")
            return jsonify({"error": "Server error. Please try again."}), 500

        # Determine if answer is correct
        is_correct = selected_option == correct_answer

        logger.info(f"Answer submitted for '{current_phrase}': {is_correct}")

        header_map, phrase_row_map, _ = get_cached_helpers()

        # Get row index from cached map to avoid expensive sheet.find()
        row_index = phrase_row_map.get(current_phrase)

        # If not in cache, fall back to find
        if row_index is None:
            try:
                cell = sheet.find(current_phrase)
                row_index = cell.row
            except gspread.exceptions.CellNotFound:
                logger.error(f"Phrase not found in sheet: {current_phrase}")
                return jsonify({"error": "Question not found in database"}), 404

        # Fetch only the row we need to read current counters
        attempts_col = header_map.get("Attempts")
        corrects_col = header_map.get("Corrects")
        if attempts_col is None or corrects_col is None:
            logger.error("Required columns not present in sheet headers")
            return jsonify({"error": "Server configuration error"}), 500

        # Retry loop to reduce chance of lost updates (optimistic retry)
        max_attempts = 3
        for attempt_no in range(1, max_attempts + 1):
            try:
                row_vals = sheet.row_values(row_index)
                current_attempts = int(row_vals[attempts_col - 1] or 0)
                current_corrects = int(row_vals[corrects_col - 1] or 0)

                updates = [
                    {
                        "range": gspread.utils.rowcol_to_a1(row_index, attempts_col),
                        "values": [[current_attempts + 1]]
                    }
                ]
                if is_correct:
                    updates.append({
                        "range": gspread.utils.rowcol_to_a1(row_index, corrects_col),
                        "values": [[current_corrects + 1]]
                    })

                sheet.batch_update(updates)

                # Update in-memory cache (best-effort) to avoid full cache invalidation
                with _cache_lock:
                    records = _sheet_cache.get("records")
                    if records:
                        # records are in-order starting at sheet row 2
                        rec_index = row_index - 2
                        if 0 <= rec_index < len(records):
                            records[rec_index]["Attempts"] = current_attempts + 1
                            if is_correct:
                                records[rec_index]["Corrects"] = current_corrects + 1
                            # bump timestamp to keep cache fresh
                            _sheet_cache["ts"] = time.time()

                logger.info(f"Sheet updated successfully for '{current_phrase}'")
                break

            except gspread.exceptions.APIError as e:
                logger.warning(f"API error updating sheet (attempt {attempt_no}): {e}")
                if attempt_no == max_attempts:
                    logger.error("Exceeded retries updating sheet")
                    return jsonify({"error": "Failed to update progress"}), 500
                time.sleep(0.2 * attempt_no)
            except Exception as e:
                logger.error(f"Sheet update error: {e}", exc_info=True)
                return jsonify({"error": "Failed to update progress"}), 500

        return jsonify({
            "is_correct": is_correct,
            "correct_answer": correct_answer
        })

    except Exception as e:
        logger.error(f"Answer route error: {e}", exc_info=True)
        return jsonify({"error": "Server error"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    logger.warning(f"404 error: {request.path}")
    return render_template(
        "error.html",
        error_title="Page Not Found",
        error_message="The page you're looking for doesn't exist."
    ), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    logger.error(f"500 error: {error}", exc_info=True)
    return render_template(
        "error.html",
        error_title="Server Error",
        error_message="An unexpected error occurred. Please try again later."
    ), 500


if __name__ == "__main__":
    # Initialize sheet connection before starting the app
    try:
        initialize_sheet()
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=DEBUG
    )
