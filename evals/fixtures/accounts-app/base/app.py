"""Customer portal: sign-up and sign-in."""
import os
import sqlite3

from flask import Flask, abort, request, session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ["PORTAL_SECRET_KEY"]
DB_PATH = "portal.db"


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db() as c:
        c.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            " id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)"
        )


@app.post("/signup")
def signup():
    email = request.form["email"].strip().lower()
    password = request.form["password"]
    if len(password) < 12:
        abort(400, "password must be at least 12 characters")
    with db() as c:
        c.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, generate_password_hash(password)))
    return "", 201


@app.post("/login")
def login():
    email = request.form["email"].strip().lower()
    with db() as c:
        row = c.execute("SELECT id, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not check_password_hash(row["password_hash"], request.form["password"]):
        abort(401)
    session["user_id"] = row["id"]
    return "", 204
