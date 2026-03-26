from fastapi import FastAPI
import sqlite3

app = FastAPI()

conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()


@app.get("/events")
def get_events():
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    return rows


@app.get("/fraud-alerts")
def get_fraud():
    cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()
    return rows
