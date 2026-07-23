import os
import sqlite3
from flask import Flask, request, jsonify, send_from_directory

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = Flask(__name__, static_folder=None)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 3000")
    return conn


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/manifest.json")
def manifest():
    return send_from_directory(STATIC_DIR, "manifest.json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(STATIC_DIR, "sw.js")


@app.route("/icon-192.png")
def icon_192():
    return send_from_directory(STATIC_DIR, "icon-192.png")


@app.route("/icon-512.png")
def icon_512():
    return send_from_directory(STATIC_DIR, "icon-512.png")


@app.route("/api/kv/<key>", methods=["GET"])
def get_kv(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM kv WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify({"key": key, "value": row[0]})


@app.route("/api/kv/<key>", methods=["PUT"])
def set_kv(key):
    body = request.get_json(silent=True) or {}
    value = body.get("value")
    if not isinstance(value, str):
        return jsonify({"error": "'value' must be a string"}), 400
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO kv (key, value, updated_at) VALUES (?, ?, datetime('now'))
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, value),
    )
    conn.commit()
    conn.close()
    return jsonify({"key": key, "value": value})


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True})


init_db()

if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=8000)
