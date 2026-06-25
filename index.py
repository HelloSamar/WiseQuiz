import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory, abort

BASE_DIR = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "5000"))

app = Flask(__name__, static_folder=None)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "app": "WiseQuiz", "mode": "static-vocabulary"})


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/<path:filename>")
def assets(filename: str):
    """
    Serve first-party static assets from the repository root.
    This avoids manual allow-list bugs when adding new decks or browser assets.
    """
    file_path = BASE_DIR / filename

    if file_path.is_file() and file_path.suffix in {".js", ".css", ".json", ".ico", ".webmanifest"}:
        return send_from_directory(BASE_DIR, filename)

    return abort(404)


if __name__ == "__main__":
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=PORT, debug=debug)
