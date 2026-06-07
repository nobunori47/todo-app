from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic
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
ai_client = Anthropic()

@app.route("/")
def index():
    todos = sheet.get_all_records()
    today = datetime.now().date()
    for todo in todos:
        due = todo.get("期日", "")
        try:
            due_date = datetime.strptime(str(due), "%Y-%m-%d").date()
            diff = (due_date - today).days
            if diff <= 3:
                todo["due_color"] = "red"
            elif diff <= 7:
                todo["due_color"] = "orange"
            else:
                todo["due_color"] = "normal"
        except:
            todo["due_color"] = "normal"
    return render_template("index.html", todos=todos)

@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        todo_id = str(uuid.uuid4())[:8]
        title = request.form["title"]
        content = request.form["content"]
        due_date = request.form["due_date"]
        priority = request.form["priority"]
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        sheet.append_row([todo_id, title, content, due_date, created_at, priority])
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
        sheet.update_cell(row, 6, request.form["priority"])
        return redirect(url_for("index"))
    return render_template("edit.html", todo=todo)

@app.route("/delete/<todo_id>", methods=["POST"])
def delete(todo_id):
    todos = sheet.get_all_records()
    todo = next((t for t in todos if str(t["id"]) == todo_id), None)
    if todo:
        cell = sheet.find(todo_id)
        sheet.delete_rows(cell.row)
    return redirect(url_for("index"))

@app.route("/decompose/<todo_id>")
def decompose(todo_id):
    todos = sheet.get_all_records()
    todo = next((t for t in todos if str(t["id"]) == todo_id), None)
    if not todo:
        return redirect(url_for("index"))

    response = ai_client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": f"""以下のタスクを、実行可能な具体的なサブタスクに分解してください。

タスク名：{todo.get('タイトル', '')}
内容：{todo.get('内容', '')}

・5〜7つのサブタスクに分解してください
・各サブタスクは1行で、番号付きリストで返してください
・すぐに着手できる具体的なアクションにしてください
・余分な説明は不要です。リストのみ返してください"""
            }
        ]
    )

    subtasks = response.content[0].text
    return render_template("decompose.html", todo=todo, subtasks=subtasks)

if __name__ == "__main__":
    app.run(debug=True)