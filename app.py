import os
import psycopg2
from flask import Flask, jsonify, request

APP_VERSION = "1.0"

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        dbname=os.environ["DB_NAME"],
    )


def ensure_table(cur):
    cur.execute(
        "CREATE TABLE IF NOT EXISTS posts ("
        "id SERIAL PRIMARY KEY, title TEXT NOT NULL, content TEXT, "
        "created_at TIMESTAMP DEFAULT NOW())"
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": APP_VERSION})


@app.route("/posts", methods=["GET"])
def list_posts():
    conn = get_conn()
    cur = conn.cursor()
    ensure_table(cur)
    cur.execute("SELECT id, title, content, created_at FROM posts ORDER BY id DESC LIMIT 50")
    rows = cur.fetchall()
    conn.commit()
    conn.close()
    return jsonify(
        [
            {"id": r[0], "title": r[1], "content": r[2], "created_at": r[3].isoformat()}
            for r in rows
        ]
    )


@app.route("/posts", methods=["POST"])
def create_post():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    conn = get_conn()
    cur = conn.cursor()
    ensure_table(cur)
    cur.execute("INSERT INTO posts (title, content) VALUES (%s, %s) RETURNING id", (title, content))
    new_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return jsonify({"id": new_id, "title": title, "content": content}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
