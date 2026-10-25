import os
import platform
import socket
import time
from datetime import datetime

import psycopg2
from flask import Flask, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)

DB_CONFIG = dict(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "tasksdb"),
    user=os.getenv("DB_USER", "taskuser"),
    password=os.getenv("DB_PASSWORD", "taskpass"),
)


def query(sql, params=None, fetch=False):
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if fetch else None
    finally:
        conn.close()


def init_db(retries=15):
    """Create the table, waiting for the database container to be ready."""
    for _ in range(retries):
        try:
            query(
                """CREATE TABLE IF NOT EXISTS tasks (
                       id SERIAL PRIMARY KEY,
                       title VARCHAR(200) NOT NULL,
                       done BOOLEAN NOT NULL DEFAULT FALSE,
                       created_at TIMESTAMP DEFAULT NOW()
                   )"""
            )
            # keeps older volumes (from the first version of the app) working
            query("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS done BOOLEAN NOT NULL DEFAULT FALSE")
            return
        except psycopg2.OperationalError:
            time.sleep(2)
    raise RuntimeError("Database not reachable")


init_db()


@app.route("/")
def index():
    tasks = query(
        "SELECT id, title, done, created_at FROM tasks ORDER BY done ASC, id DESC",
        fetch=True,
    )
    total = len(tasks)
    done = sum(1 for t in tasks if t[2])
    stats = {"total": total, "done": done, "pending": total - done}
    return render_template(
        "index.html", tasks=tasks, stats=stats, host=socket.gethostname(), page="tasks"
    )


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    if title:
        query("INSERT INTO tasks (title) VALUES (%s)", (title[:200],))
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    query("UPDATE tasks SET done = NOT done WHERE id = %s", (task_id,))
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    query("DELETE FROM tasks WHERE id = %s", (task_id,))
    return redirect(url_for("index"))


@app.route("/system")
def system():
    """Shows which container/instance served the request: great for the ALB demo."""
    try:
        db_version = query("SELECT version()", fetch=True)[0][0].split(",")[0]
        task_count = query("SELECT COUNT(*) FROM tasks", fetch=True)[0][0]
        db_ok = True
    except Exception:
        db_version, task_count, db_ok = "unreachable", 0, False
    info = {
        "Container hostname": socket.gethostname(),
        "Python": platform.python_version(),
        "Database host": DB_CONFIG["host"],
        "Database": db_version,
        "Tasks stored": task_count,
        "Server time (UTC)": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return render_template(
        "system.html", info=info, db_ok=db_ok, host=socket.gethostname(), page="system"
    )


@app.route("/health")
def health():
    """Used by the AWS Load Balancer target group health check."""
    try:
        query("SELECT 1", fetch=True)
        return jsonify(status="ok", host=socket.gethostname()), 200
    except Exception:
        return jsonify(status="db-unreachable"), 503
