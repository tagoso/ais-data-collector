import websocket
import json
import os
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

print("🟢 Script started")
print("API_KEY:", API_KEY)
print("MMSI_TARGET:", MMSI_TARGET)

# === Load env ===
load_dotenv()
API_KEY = os.environ.get("API_KEY")
MMSI_TARGET = os.environ.get("TARGET_MMSI")
DATA_FILE = "data.json"
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_RECORDS = 100

# === Read/write ===
def load_existing_data():
    try:
        with open(os.path.join(REPO_DIR, DATA_FILE), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    with open(os.path.join(REPO_DIR, DATA_FILE), "w") as f:
        json.dump(data, f, indent=2)

# === Git ===
def git_push():
    subprocess.run(["git", "add", DATA_FILE], cwd=REPO_DIR)
    subprocess.run(["git", "commit", "-m", f"Update {datetime.utcnow().isoformat()}"], cwd=REPO_DIR)
    subprocess.run(["git", "push"], cwd=REPO_DIR)

# === WebSocket Handlers ===
def on_message(ws, message):
    try:
        data = json.loads(message)
        if data.get("MMSI") == MMSI_TARGET:
            print(f"✅ Matched MMSI: {MMSI_TARGET}")
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "lat": data.get("LAT"),
                "lon": data.get("LON"),
                "speed": data.get("SPEED"),
                "course": data.get("COURSE")
            }
            existing = load_existing_data()
            existing.append(entry)
            if len(existing) > MAX_RECORDS:
                existing = existing[-MAX_RECORDS:]
            save_data(existing)
            git_push()
    except Exception as e:
        print("❌ Error processing message:", e)

def on_open(ws):
    if not API_KEY or not MMSI_TARGET:
        print("❌ Missing API key or MMSI.")
        ws.close()
        return

    sub_msg = {
        "APIKey": API_KEY,
        "BoundingBoxes": [[[-90, -180], [90, 180]]],
        "FiltersShipMMSI": [str(MMSI_TARGET)],
        "FilterMessageTypes": ["PositionReport"]
    }

    print("✅ Sending subscription:", sub_msg)
    ws.send(json.dumps(sub_msg))

def on_error(ws, error):
    print("❌ WebSocket error:", error)

def on_close(ws, code, msg):
    print("🔌 WebSocket connection closed")

# === Reconnect Loop ===
def connect_with_retries():
    error_count = 0
    while True:
        try:
            print("🔄 Connecting to AISstream WebSocket...")
            ws = websocket.WebSocketApp(
                "wss://stream.aisstream.io/v0/stream",
                on_message=on_message,
                on_open=on_open,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever()
            error_count = 0  # Reset if succeeded
        except Exception as e:
            print("❌ Connection exception:", e)
            error_count += 1

        # control intervals
        if error_count < 3:
            wait = 30  # wait for 30 sec
        else:
            wait = 600  # if cut many times, wait longer

        print(f"⏳ Reconnecting in {wait} seconds (error_count={error_count})")
        time.sleep(wait)

# === Entry Point ===
if __name__ == "__main__":
    print("🚀 Starting script")
    print("API_KEY:", API_KEY)
    print("MMSI:", MMSI_TARGET)

    if not API_KEY:
        print("ERROR: API_KEY is not set!")
        exit(1)

    connect_with_retries()

