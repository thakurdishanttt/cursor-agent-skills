import sqlite3, subprocess
from flask import Flask, request, send_file
app = Flask(__name__)
DB = sqlite3.connect("app.db", check_same_thread=False)

@app.get("/health")
def health():
    return "ok"

@app.get("/user")
def get_user():
    uid = request.args["id"]
    return str(DB.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone())

@app.get("/report")
def report():
    name = request.args.get("file", "report.pdf")
    return send_file("/srv/reports/" + name)

@app.post("/ping")
def ping():
    host = request.form["host"]
    return subprocess.check_output(f"ping -c 1 {host}", shell=True)
