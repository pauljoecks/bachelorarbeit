from pathlib import Path

from flask import Flask, jsonify, send_from_directory

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
count = 0


@app.get("/api/count")
def get_count():
    return jsonify(count=count)


@app.post("/api/increment")
def increment():
    global count
    count += 1
    return jsonify(count=count)


@app.get("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    return send_from_directory(BASE_DIR, path)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
