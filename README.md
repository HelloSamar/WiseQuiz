# WiseQuiz 🎓

A simple, elegant quiz application for mastering one-word substitutions. Built with Flask and Google Sheets.

## Features

- 🎯 **Interactive Quiz Interface** - Beautiful, responsive design with timer
- 📊 **Google Sheets Integration** - Questions stored and tracked in a Google Sheet
- ⏱️ **Timed Questions** - 10-second countdown for each question
- 📈 **Progress Tracking** - Automatic tracking of correct answers and attempts
- 🎨 **Modern UI** - Dark theme with smooth animations

## Quick Start

### Prerequisites

- Python 3.8+
- Google Sheets API credentials (Service Account)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/HelloSamar/WiseQuiz.git
   cd WiseQuiz
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up credentials**
   - Download your Google Service Account credentials JSON
   - Save as `credentials.json` in the project root
   - Create `.env` file:
     ```
     GOOGLE_CLIENT_ID=your_client_id
     GOOGLE_CLIENT_SECRET=your_client_secret
     SECRET_KEY=your_secret_key
     PORT=5000
     ```

5. **Run the application**
   ```bash
   python app.py
   ```
   - Open browser to `http://localhost:5000`

## How It Works

1. **Quiz Route** (`/`) - Fetches a random unanswered question from Google Sheets
2. **Answer Route** (`/answer`) - Processes answer and updates sheet with progress
3. **Progress Tracking** - Questions mastered after 10 correct answers
4. **Completion** - Shows celebration screen when all questions are mastered

## Project Structure

```
WiseQuiz/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not committed)
├── .gitignore         # Git exclusions
└── credentials.json   # Google API credentials (not committed)
```

## Technology Stack

- **Backend**: Flask 3.0.3
- **Google Sheets API**: gspread, oauth2client
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)

## Configuration

Edit the Google Sheet URL in `app.py` (line 19) to use your own sheet:

```python
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
).sheet1
```

Your sheet should have columns:
- `Phrases` - The one-word substitution prompt
- `One Word` - The correct answer
- `Corrects` - Number of correct answers (auto-updated)
- `Attempts` - Total attempts (auto-updated)

## Security

- ⚠️ **Never commit** `.env` or `credentials.json` to git
- Both files are in `.gitignore`
- Use environment variables for all sensitive data

## License

MIT License - feel free to use and modify!

## Support

For issues or questions, open an issue on GitHub.

---

**Happy Quizzing! 🚀**
