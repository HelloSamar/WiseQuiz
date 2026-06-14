# WiseQuiz

WiseQuiz is a lightweight SSC vocabulary quiz app. It runs as a static browser app and includes a tiny Flask wrapper for deployment.

## What is included

- One Word Substitution practice
- Idioms practice
- Synonyms practice
- Antonyms practice
- Smart repetition for weak and unattempted items
- Smart Progression and Instant Mastery modes
- Browser-based progress storage with `localStorage`
- Keyboard shortcuts for fast practice

## Clean repository structure

```text
.
├── index.html
├── app.js
├── styles.css
├── ows.json
├── idioms.json
├── synonyms.json
├── antonyms.json
├── index.py
├── requirements.txt
├── Procfile
├── .gitignore
└── README.md
```

Generated folders such as `venv/`, cache files, local credentials, and archives should not be committed.

## Run locally

### Static server

```bash
python -m http.server 5000
```

Open `http://localhost:5000`.

### Flask server

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python index.py
```

Open `http://localhost:5000`.

## Deploy

The included `Procfile` runs:

```bash
gunicorn index:app
```

No Google Sheets or secret credentials are required for this version.

## Data files

All quiz content is loaded from JSON files. Keep them as JSON arrays.

### OWS format

```json
{
  "Phrases": "Become less intense or widespread",
  "One Word Substitution": "Abate",
  "Hindi Meaning": "रोक-थाम करना",
  "Example": "The storm began to abate after several hours of heavy rain.",
  "Level": "Important"
}
```

### Idioms format

```json
{
  "Idiom": "A piece of cake",
  "Meaning": "Something that is easy to understand or do.",
  "Example": "Completing the assignment was a piece of cake for him."
}
```

### Synonyms format

```json
{
  "Word": "Abate",
  "Synonym": "Subside",
  "Meaning": "Become less intense",
  "Example": "The storm began to abate by evening."
}
```

### Antonyms format

```json
{
  "Word": "Accept",
  "Antonym": "Reject",
  "Meaning": "Refuse to receive or agree",
  "Example": "The committee may reject the proposal."
}
```

## Progress storage

Progress is saved in the browser. Use the app's export/import controls when moving progress between browsers or devices.

## Health check

`/health` returns a small JSON status payload when running through Flask.
