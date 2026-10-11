


from flask import Flask, request, redirect, render_template_string
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)

DATABASE = "habits.db"


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS completions (
            habit_id INTEGER NOT NULL,
            completion_date TEXT NOT NULL,
            PRIMARY KEY (habit_id, completion_date),
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        )
    """)

    connection.commit()
    connection.close()


@app.route("/")
def home():
    today = date.today().isoformat()
    connection = get_db()

    habits = connection.execute("""
        SELECT habits.id, habits.name,
               CASE WHEN completions.habit_id IS NOT NULL
                    THEN 1 ELSE 0 END AS completed
        FROM habits
        LEFT JOIN completions
            ON habits.id = completions.habit_id
            AND completions.completion_date = ?
        ORDER BY habits.id
    """, (today,)).fetchall()

    connection.close()

    total = len(habits)
    completed = sum(habit["completed"] for habit in habits)
    percentage = int(completed / total * 100) if total else 0

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Daily Habit Tracker</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f1fa;
                margin: 0;
                padding: 40px 20px;
                color: #302b3d;
            }
            .container {
                max-width: 650px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 18px;
                box-shadow: 0 5px 20px #ddd5eb;
            }
            h1 { color: #7451a6; }
            .subtitle { color: #777; margin-bottom: 30px; }
            .habit {
                background: #f8f6fc;
                padding: 15px;
                margin: 12px 0;
                border-radius: 10px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 12px;
            }
            button {
                background: #7451a6;
                color: white;
                border: none;
                padding: 10px 14px;
                border-radius: 8px;
                cursor: pointer;
            }
            .completed { background: #4b9569; }
            input {
                flex: 1;
                min-width: 0;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            .add-form { display: flex; gap: 10px; }
            .progress {
                background: #e8e1f2;
                height: 10px;
                border-radius: 10px;
                margin-top: 15px;
            }
            .progress-fill {
                background: #9474c2;
                height: 10px;
                border-radius: 10px;
            }
            .empty { color: #777; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>My Daily Habits 🌷</h1>
            <p class="subtitle">Small steps create big changes.</p>

            <h3>Add a new habit</h3>
            <form class="add-form" action="/add" method="POST">
                <input name="habit_name" type="text"
                       placeholder="e.g. Drink water" required maxlength="100">
                <button type="submit">Add Habit</button>
            </form>
            <p><a href="/weekly" style="color: #7451a6;">📊 View Weekly Progress →</a></p>

            <h3>Today's Habits</h3>

            {% if habits %}
                {% for habit in habits %}
                    <div class="habit">
                        <span>
                            {{ "✓ " if habit["completed"] else "" }}{{ habit["name"] }}
                        </span>
                        <form action="/toggle/{{ habit['id'] }}" method="POST">
                            <button class="{{ 'completed' if habit['completed'] else '' }}"
                                    type="submit">
                                {{ "Undo" if habit["completed"] else "Mark Done" }}
                            </button>
                        
                        </form>

                        <form action="/delete/{{ habit['id'] }}" method="POST"
                              onsubmit="return confirm('Delete this habit?');">
                            <button type="submit" style="background: #c45b65;">
                                Delete
                            </button>
                        </form>
                    </div>
                {% endfor %}

            {% else %}
                <p class="empty">No habits yet. Add your first habit above!</p>
            {% endif %}

            <p>Progress: {{ completed }} of {{ total }} completed ({{ percentage }}%)</p>
            <div class="progress">
                <div class="progress-fill" style="width: {{ percentage }}%;"></div>
            </div>
        </div>
        </body>
    </html>
    """, habits=habits, completed=completed,
         total=total, percentage=percentage )


@app.route("/add", methods=["POST"])
def add_habit():
    name = request.form.get("habit_name", "").strip()

    if name:
        connection = get_db()
        connection.execute(
            "INSERT INTO habits (name) VALUES (?)",
            (name,)
        )
        connection.commit()
        connection.close()

    return redirect("/")


@app.route("/toggle/<int:habit_id>", methods=["POST"])
def toggle_habit(habit_id):
    today = date.today().isoformat()
    connection = get_db()

    habit = connection.execute(
        "SELECT id FROM habits WHERE id = ?", (habit_id,)
    ).fetchone()

    if habit:
        completion = connection.execute(
            """SELECT habit_id FROM completions
               WHERE habit_id = ? AND completion_date = ?""",
            (habit_id, today)
        ).fetchone()

        if completion:
            connection.execute(
                """DELETE FROM completions
                   WHERE habit_id = ? AND completion_date = ?""",
                (habit_id, today)
            )
        else:
            connection.execute(
                """INSERT INTO completions (habit_id, completion_date)
                   VALUES (?, ?)""",
                (habit_id, today)
            )

    connection.commit()
    connection.close()
    return redirect("/")

@app.route("/delete/<int:habit_id>", methods=["POST"])
def delete_habit(habit_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM completions WHERE habit_id = ?",
        (habit_id,)
    )

    connection.execute(
        "DELETE FROM habits WHERE id = ?",
        (habit_id,)
    )

    connection.commit()
    connection.close()

    return redirect("/")

@app.route("/weekly")
def weekly_progress():
    today = date.today()
    start_date = today - timedelta(days=6)

    connection = get_db()

    habits = connection.execute(
        "SELECT id, name FROM habits ORDER BY id"
    ).fetchall()

    daily_data = []

    for day_offset in range(7):
        current_day = start_date + timedelta(days=day_offset)
        day_string = current_day.isoformat()

        completed_count = connection.execute(
            """SELECT COUNT(*) AS total
               FROM completions
               WHERE completion_date = ?""",
            (day_string,)
        ).fetchone()["total"]

        daily_data.append({
    "day": current_day.strftime("%a"),
    "date": current_day.strftime("%b %d"),
    "completed": completed_count,
    "percentage": round(completed_count / len(habits) * 100)
        if habits else 0
})
    connection.close()

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Weekly Progress</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f1fa;
                padding: 30px 20px;
                color: #302b3d;
            }
            .container {
                max-width: 650px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 18px;
                box-shadow: 0 5px 20px #ddd5eb;
            }
            h1 { color: #7451a6; }
            .day {
                background: #f8f6fc;
                padding: 14px;
                margin: 12px 0;
                border-radius: 10px;
            }
            .bar {
                background: #e8e1f2;
                height: 12px;
                border-radius: 10px;
                margin-top: 8px;
            }
            .fill {
                background: #9474c2;
                height: 12px;
                border-radius: 10px;
            }
            a { color: #7451a6; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>My Weekly Progress 📊</h1>
            <p>Your completed habits over the last seven days.</p>

            {% for item in daily_data %}
                <div class="day">
                    <strong>{{ item["day"] }}, {{ item["date"] }}</strong>
                    <div>{{ item["completed"] }} habit completions · {{ item["percentage"] }}%</div>
                    <div class="bar">
                        <div class="fill"
                             style="width: {{ item['percentage'] }}%;"
                        </div>
                    </div>
                </div>
            {% endfor %}

            <p><a href="/">← Back to My Daily Habits</a></p>
        </div>
    </body>
    </html>
    """, daily_data=daily_data, habits=habits)






if __name__ == "__main__":
    create_database()
    app.run(debug=True)

