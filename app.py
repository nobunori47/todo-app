from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
from datetime import datetime
import uuid

load_dotenv()

app = Flask(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
if creds_json:
    creds_info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
else:
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_FILE"), scopes=SCOPES
    )

gc = gspread.authorize(creds)
sheet = gc.open_by_key(os.getenv("SPREADSHEET_ID")).worksheet("Todo")

@app.route("/")
def index():
    todos = sheet.get_all_records()
    return render_template("index.html", todos=todos)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        todo_id = str(uuid.uuid4())[:8]
        title = request.form["title"]
        content = request.form["content"]
        due_date = request.form["due_date"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([todo_id, title, content, due_date, created_at])
        return redirect(url_for("index"))
    return render_template("add.html")

@app.route("/edit/<todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    todos = sheet.get_all_records()
    todo = next((t for t in todos if str(t["id"]) == todo_id), None)
    if not todo:
        return redirect(url_for("index"))
    if request.method == "POST":
        cell = sheet.find(todo_id)
        row = cell.row
        sheet.update_cell(row, 2, request.form["title"])
        sheet.update_cell(row, 3, request.form["content"])
        sheet.update_cell(row, 4, request.form["due_date"])
        return redirect(url_for("index"))
    return render_template("edit.html", todo=todo)

if __name__ == "__main__":
    app.run(debug=True)