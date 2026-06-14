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


@app.route("/app.js")
def app_js():
    return send_from_directory(BASE_DIR, "app.js")


@app.route("/styles.css")
def styles_css():
    return send_from_directory(BASE_DIR, "styles.css")


@app.route("/ows.json")
def ows_json():
    return send_from_directory(BASE_DIR, "ows.json")


@app.route("/idioms.json")
def idioms_json():
    return send_from_directory(BASE_DIR, "idioms.json")


@app.route("/synonyms.json")
def synonyms_json():
    return send_from_directory(BASE_DIR, "synonyms.json")


@app.route("/antonyms.json")
def antonyms_json():
    return send_from_directory(BASE_DIR, "antonyms.json")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=os.environ.get("DEBUG", "false").lower() == "true")
