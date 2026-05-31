import os
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template_string, request, session, jsonify

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# Google Sheets authentication
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open the Google Sheet
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1dcQiwJVKEDhis5qHTuHjbu6lor_e4BZz29QhY22I5-0/edit?usp=drive_link"
).sheet1

QUIZ_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>OWS Quiz</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg: #0f0e17;
            --surface: #1a1928;
            --surface2: #242336;
            --accent: #ff6b35;
            --accent2: #ffd166;
            --correct: #06d6a0;
            --wrong: #ef476f;
            --text: #fffffe;
            --muted: #a7a9be;
        }

        body {
            font-family: 'DM Sans', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            background-image: radial-gradient(ellipse at 20% 50%, rgba(255,107,53,0.08) 0%, transparent 60%),
                              radial-gradient(ellipse at 80% 20%, rgba(255,209,102,0.06) 0%, transparent 50%);
        }

        .card {
            width: 100%;
            max-width: 440px;
            background: var(--surface);
            border-radius: 20px;
            padding: 28px 24px;
            border: 1px solid rgba(255,255,255,0.06);
            box-shadow: 0 24px 64px rgba(0,0,0,0.5);
            position: relative;
            animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes slideUp {
            from { opacity: 0; transform: translateY(20px); }
            to   { opacity: 1; transform: translateY(0); }
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }

        .brand {
            font-family: 'Playfair Display', serif;
            font-size: 18px;
            color: var(--accent);
            letter-spacing: 0.02em;
        }

        .timer-wrap {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .timer-ring {
            position: relative;
            width: 44px;
            height: 44px;
        }

        .timer-ring svg {
            transform: rotate(-90deg);
        }

        .timer-ring circle {
            fill: none;
            stroke-width: 3;
        }

        .timer-ring .bg { stroke: var(--surface2); }
        .timer-ring .fg {
            stroke: var(--accent);
            stroke-linecap: round;
            stroke-dasharray: 113;
            stroke-dashoffset: 0;
            transition: stroke-dashoffset 1s linear, stroke 0.3s;
        }

        .timer-num {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 600;
            color: var(--accent);
        }

        .prompt {
            font-size: 13px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 10px;
        }

        .phrase {
            font-family: 'Playfair Display', serif;
            font-size: 24px;
            line-height: 1.3;
            color: var(--text);
            margin-bottom: 28px;
            min-height: 64px;
        }

        .options {
            display: grid;
            gap: 10px;
            margin-bottom: 20px;
        }

        .option {
            background: var(--surface2);
            border: 1.5px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 14px 18px;
            font-family: 'DM Sans', sans-serif;
            font-size: 16px;
            font-weight: 500;
            color: var(--text);
            cursor: pointer;
            text-align: left;
            transition: border-color 0.2s, background 0.2s, transform 0.1s;
            position: relative;
            overflow: hidden;
        }

        .option:hover:not(:disabled) {
            border-color: var(--accent);
            background: rgba(255,107,53,0.1);
            transform: translateX(4px);
        }

        .option:active:not(:disabled) {
            transform: translateX(2px) scale(0.99);
        }

        .option.correct {
            background: rgba(6,214,160,0.15);
            border-color: var(--correct);
            color: var(--correct);
        }

        .option.wrong {
            background: rgba(239,71,111,0.15);
            border-color: var(--wrong);
            color: var(--wrong);
        }

        .option:disabled { cursor: default; }

        .stats {
            display: flex;
            gap: 12px;
            padding-top: 16px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }

        .stat {
            flex: 1;
            background: var(--surface2);
            border-radius: 10px;
            padding: 10px 14px;
            text-align: center;
        }

        .stat-val {
            font-size: 20px;
            font-weight: 700;
            color: var(--accent2);
        }

        .stat-lbl {
            font-size: 11px;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 2px;
        }

        .result-banner {
            display: none;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 15px;
            margin-bottom: 16px;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to   { opacity: 1; transform: scale(1); }
        }

        .result-banner.show { display: flex; }
        .result-banner.correct-banner { background: rgba(6,214,160,0.12); color: var(--correct); border: 1px solid rgba(6,214,160,0.3); }
        .result-banner.wrong-banner  { background: rgba(239,71,111,0.12); color: var(--wrong);   border: 1px solid rgba(239,71,111,0.3); }

        .complete {
            text-align: center;
            padding: 40px 20px;
        }

        .complete .emoji { font-size: 56px; margin-bottom: 16px; }
        .complete h1 {
            font-family: 'Playfair Display', serif;
            font-size: 28px;
            margin-bottom: 8px;
        }
        .complete p { color: var(--muted); font-size: 15px; }
    </style>
</head>
<body>
{% if complete %}
<div class="card">
    <div class="complete">
        <div class="emoji">🏆</div>
        <h1>All Mastered!</h1>
        <p>You've completed every phrase in this set. Outstanding work.</p>
    </div>
</div>
{% else %}
<div class="card">
    <div class="header">
        <span class="brand">OWS Quiz</span>
        <div class="timer-wrap">
            <div class="timer-ring">
                <svg width="44" height="44" viewBox="0 0 44 44">
                    <circle class="bg" cx="22" cy="22" r="18"/>
                    <circle class="fg" id="timerCircle" cx="22" cy="22" r="18"/>
                </svg>
                <div class="timer-num" id="timerNum">10</div>
            </div>
        </div>
    </div>

    <div class="prompt">One-word substitution for:</div>
    <div class="phrase">{{ phrase }}</div>

    <div class="result-banner" id="resultBanner"></div>

    <div class="options" id="options">
        {% for option in options %}
        <button class="option" onclick="selectAnswer(this, '{{ option | e }}')">{{ option }}</button>
        {% endfor %}
    </div>

    <div class="stats">
        <div class="stat">
            <div class="stat-val">{{ correct }}</div>
            <div class="stat-lbl">Correct</div>
        </div>
        <div class="stat">
            <div class="stat-val">{{ attempts }}</div>
            <div class="stat-lbl">Attempts</div>
        </div>
        <div class="stat">
            <div class="stat-val">{{ remaining }}</div>
            <div class="stat-lbl">Remaining</div>
        </div>
    </div>
</div>

<script>
    const TOTAL_TIME = 10;
    const circumference = 2 * Math.PI * 18; // ~113.1
    let timeLeft = TOTAL_TIME;
    let answered = false;
    let timerInterval;

    const circle = document.getElementById('timerCircle');
    const numEl  = document.getElementById('timerNum');
    circle.style.strokeDasharray = circumference;

    function updateTimer() {
        const frac = timeLeft / TOTAL_TIME;
        circle.style.strokeDashoffset = circumference * (1 - frac);
        numEl.textContent = timeLeft;

        if (timeLeft <= 3) circle.style.stroke = '#ef476f';
        else if (timeLeft <= 6) circle.style.stroke = '#ffd166';

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            if (!answered) timeOut();
        }
        timeLeft--;
    }

    updateTimer();
    timerInterval = setInterval(updateTimer, 1000);

    function disableAll() {
        document.querySelectorAll('.option').forEach(b => b.disabled = true);
    }

    function showBanner(correct, correctWord) {
        const banner = document.getElementById('resultBanner');
        if (correct) {
            banner.className = 'result-banner show correct-banner';
            banner.textContent = '✓ Correct!';
        } else {
            banner.className = 'result-banner show wrong-banner';
            banner.textContent = '✗ Answer: ' + correctWord;
        }
    }

    function selectAnswer(btn, selected) {
        if (answered) return;
        answered = true;
        clearInterval(timerInterval);
        disableAll();

        fetch('/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'option=' + encodeURIComponent(selected)
        })
        .then(r => r.json())
        .then(data => {
            document.querySelectorAll('.option').forEach(b => {
                if (b.textContent.trim() === data.correct_answer) b.classList.add('correct');
                else if (b.textContent.trim() === selected) b.classList.add('wrong');
            });
            showBanner(data.is_correct, data.correct_answer);
            setTimeout(() => window.location.href = '/', 1800);
        });
    }

    function timeOut() {
        answered = true;
        disableAll();
        fetch('/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: 'option='
        })
        .then(r => r.json())
        .then(data => {
            document.querySelectorAll('.option').forEach(b => {
                if (b.textContent.trim() === data.correct_answer) b.classList.add('correct');
            });
            showBanner(false, data.correct_answer);
            setTimeout(() => window.location.href = '/', 1800);
        });
    }
</script>
{% endif %}
</body>
</html>
"""


@app.route("/")
def quiz():
    """Display a random quiz question from Google Sheets."""
    try:
        data = sheet.get_all_records()
        df_filtered = [row for row in data if int(row["Corrects"]) < 10]

        if not df_filtered:
            return render_template_string(QUIZ_TEMPLATE, complete=True)

        row = random.choice(df_filtered)
        current_phrase   = row["Phrases"]
        correct_answer   = row["One Word"]
        correct_count    = row["Corrects"]
        attempts_count   = row["Attempts"]

        # Store in session so /answer can access them safely
        session["current_phrase"]   = current_phrase
        session["correct_answer"]   = correct_answer

        incorrect_answers = [r["One Word"] for r in data if r["One Word"] != correct_answer]
        options = [correct_answer] + random.sample(incorrect_answers, min(3, len(incorrect_answers)))
        random.shuffle(options)

        return render_template_string(
            QUIZ_TEMPLATE,
            complete=False,
            phrase=current_phrase,
            options=options,
            correct=correct_count,
            attempts=attempts_count,
            remaining=len(df_filtered),
        )
    except Exception as e:
        app.logger.error(f"Quiz route error: {e}")
        return "Error loading quiz. Please try again later.", 500


@app.route("/answer", methods=["POST"])
def answer():
    """Process the user's answer and update the Google Sheet."""
    selected_option = request.form.get("option", "")
    current_phrase  = session.get("current_phrase")
    correct_answer  = session.get("correct_answer")

    if not current_phrase or not correct_answer:
        return jsonify({"error": "No active question"}), 400

    is_correct = selected_option == correct_answer

    try:
        cell      = sheet.find(current_phrase)
        row_index = cell.row

        # Fetch column indices
        headers       = sheet.row_values(1)
        attempts_col  = headers.index("Attempts") + 1
        corrects_col  = headers.index("Corrects") + 1

        row_vals         = sheet.row_values(row_index)
        current_attempts = int(row_vals[attempts_col - 1] or 0)
        current_corrects = int(row_vals[corrects_col - 1] or 0)

        # Batch update
        updates = [
            {"range": gspread.utils.rowcol_to_a1(row_index, attempts_col),
             "values": [[current_attempts + 1]]},
        ]
        if is_correct:
            updates.append({
                "range": gspread.utils.rowcol_to_a1(row_index, corrects_col),
                "values": [[current_corrects + 1]]
            })
        sheet.batch_update(updates)

    except Exception as e:
        app.logger.error(f"Sheet update error: {e}")
        return jsonify({"error": "Failed to update sheet"}), 500

    return jsonify({"is_correct": is_correct, "correct_answer": correct_answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
