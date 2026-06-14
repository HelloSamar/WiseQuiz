import os
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

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
def assets(filename):
    allowed = {
        "app.js",
        "styles.css",
        "ows.json",
        "idioms.json",
        "synonyms.json",
        "antonyms.json",
    }
    if filename not in allowed:
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(BASE_DIR, filename)


if __name__ == "__main__":
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=PORT, debug=debug)
