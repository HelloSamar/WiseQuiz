# WiseQuiz 🎓

A simple Flask quiz application for mastering one-word substitutions. Questions, correct counts, and attempt counts are stored in Google Sheets.

## Features

- Interactive multiple-choice quiz UI
- Google Sheets question source and progress tracking
- Timed questions with automatic timeout submission
- Cached sheet reads to reduce Google API calls
- Production-friendly `gunicorn index:app` entrypoint
- Optional credentials from either `credentials.json` or `GOOGLE_CREDENTIALS_JSON`

## Required Google Sheet columns

The first row of the sheet must include these exact headers:

| Column | Purpose |
| --- | --- |
| `Phrases` | Prompt shown to the learner |
| `One Word` | Correct answer |
| `Corrects` | Number of correct answers |
| `Attempts` | Total attempts |

## Local setup

```bash
git clone https://github.com/HelloSamar/WiseQuiz.git
cd WiseQuiz
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file or export these variables in your shell:

```bash
export GOOGLE_SHEET_URL="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
export SECRET_KEY="replace-with-a-long-random-secret"
export DEBUG="true"
export PORT="5000"
```

Add your Google service-account credentials as one of the following:

```bash
# Option 1: local file, ignored by git
cp /path/to/service-account.json credentials.json

# Option 2: custom file path
export GOOGLE_CREDENTIALS_FILE="/secure/path/service-account.json"

# Option 3: cloud deployments
export GOOGLE_CREDENTIALS_JSON='{"type":"service_account", ... }'
```

Share the Google Sheet with the service-account email before running the app.

## Run locally

```bash
python index.py
```

Open `http://localhost:5000`.

## Deploy

The included `Procfile` uses:

```bash
gunicorn index:app
```

Set these production environment variables on your hosting platform:

```bash
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
SECRET_KEY=replace-with-a-long-random-secret
GOOGLE_CREDENTIALS_JSON={...service-account-json...}
```

Optional configuration:

| Variable | Default | Description |
| --- | ---: | --- |
| `PORT` | `5000` | Local port when running `python index.py` |
| `DEBUG` | `false` | Enables Flask debug mode only for local development |
| `CACHE_TTL_SECONDS` | `300` | Google Sheet read-cache TTL |
| `QUIZ_TIME_SECONDS` | `10` | Countdown per question |
| `MASTERY_THRESHOLD` | `10` | Correct answers required before a phrase is mastered |
| `NUM_OPTIONS` | `4` | Maximum number of answer choices |

## Health check

```bash
curl http://localhost:5000/health
```

## Security notes

- Do not commit `.env`, `credentials.json`, or service-account JSON.
- Use a stable `SECRET_KEY` in production so sessions survive restarts.
- The app uses HTTP-only, same-site session cookies.
