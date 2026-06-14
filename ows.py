"""Backward-compatible entrypoint for older WiseQuiz deployments.

The application now lives in index.py so it can be imported by WSGI servers as
`index:app`. This wrapper keeps `python ows.py` working without maintaining a
second, stale Flask app.
"""

from index import DEBUG, PORT, app, initialize_sheet


if __name__ == "__main__":
    initialize_sheet()
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
