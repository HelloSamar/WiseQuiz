# WiseQuiz

WiseQuiz is a fresh SSC vocabulary trainer. The home page opens with four practice boxes: One Word Substitution, Idioms, Synonyms, and Antonyms.

## Features

- Fresh responsive dashboard.
- Separate quiz boxes for OWS, idioms, synonyms, and antonyms.
- Smart repetition that gives more practice to weak and unattempted questions.
- Filters for mastered, weak, and unlearned questions.
- Smart progression and instant mastery modes.
- Keyboard shortcuts: number keys answer choices and Enter moves to the next question.
- Browser progress storage with localStorage.
- Flask wrapper for deployment with gunicorn.

## Files

- `index.html` is the app page.
- `styles.css` contains the UI.
- `app.js` contains the quiz logic.
- `ows.json`, `idioms.json`, `synonyms.json`, and `antonyms.json` contain quiz data.
- `index.py` serves the app and JSON files.
- `Procfile` runs `gunicorn index:app`.

## Run locally

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python index.py
```

Open `http://localhost:5000`.

## Deploy

Use the existing Procfile command:

```bash
gunicorn index:app
```

No Google Sheets configuration is required for this version.

## Health check

Open `/health`. It should return app status as JSON.

## Data notes

Each data file must be a JSON array. OWS rows use `Phrases` and `One Word Substitution`. Idiom rows use `Idiom` and `Meaning`. Synonym rows use `Word` and `Synonym`. Antonym rows use `Word` and `Antonym`.

The committed JSON files are starter datasets. Replace them with larger JSON arrays when expanding the quiz.
