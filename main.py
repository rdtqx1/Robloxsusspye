import os
import time
import threading
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WEBHOOK = os.getenv("WEB")
ROBLOSECURITY = os.getenv("ROBLOSECURITY")
COOLDOWN = 5  # seconds between checks

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f".ROBLOSECURITY={ROBLOSECURITY}"
}

# Users to track
USERNAMES = ["9Dcx", "bjkqt1"]

# Maps usernames to tracking info
user_tracking = {}

# Roblox presence status codes
STATUS_MAP = {
    0: "Offline",
    1: "Online on Website",
    2: "In Game",
    3: "In Studio",
    4: "Invisible"
}

def get_user_id(username):
    response = requests.post(
        "https://users.roblox.com/v1/usernames/users",
        json={"usernames": [username], "excludeBannedUsers": False},
        headers=HEADERS
    )
    data = response.json().get("data", [])
    return data[0]["id"] if data else None

def get_avatar_url(user_id):
    return f"https://www.roblox.com/headshot-thumbnail/image?userId={user_id}&width=150&height=150&format=png"

def check_presence(user_id):
    response = requests.post(
        "https://presence.roblox.com/v1/presence/users",
        json={"userIds": [user_id]},
        headers=HEADERS
    )
    return response.json()["userPresences"][0]

def get_game_info(universe_id):
    try:
        response = requests.get(f"https://games.roblox.com/v1/games?universeIds={universe_id}")
        data = response.json().get("data", [])
        return data[0]["name"] if data else "Unknown Game"
    except:
        return "Unknown Game"

def format_duration(seconds):
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    return f"{hours}h {mins}m {secs}s"

def send_discord_embed(username, user_id, event, presence, times):
    now = datetime.utcnow()
    status = STATUS_MAP.get(presence.get("userPresenceType", 0), "Unknown")
    place_id = presence.get("placeId")
    universe_id = presence.get("universeId")
    game_id = presence.get("gameId")

    duration_online = format_duration(int(times.get("online", 0)))
    duration_offline = format_duration(int(times.get("offline", 0)))
    duration_game = format_duration(int(times.get("game", 0)))

    fields = [
        {"name": "Event", "value": event, "inline": True},
        {"name": "Status", "value": status, "inline": True},
        {"name": "Online Duration", "value": duration_online, "inline": True},
        {"name": "Offline Duration", "value": duration_offline, "inline": True},
        {"name": "In-Game Duration", "value": duration_game, "inline": True},
        {"name": "Timestamp", "value": now.strftime("%Y-%m-%d %H:%M:%S UTC"), "inline": False},
    ]

    if place_id:
        game_link = f"https://www.roblox.com/games/{place_id}"
        fields.append({"name": "Game Link", "value": f"[Join Game]({game_link})", "inline": False})

    if universe_id:
        game_name = get_game_info(universe_id)
        fields.append({"name": "Game Name", "value": game_name, "inline": True})

    if game_id:
        join_link = f"roblox://experiences/start?placeId={place_id}&gameId={game_id}"
        fields.append({"name": "Join Server", "value": join_link, "inline": False})
        fields.append({"name": "Server ID", "value": game_id, "inline": True})

    embed = {
        "title": f"🔔 {username} Activity Update",
        "color": 0x00ff00 if presence["userPresenceType"] != 0 else 0xff0000,
        "fields": fields,
        "thumbnail": {"url": get_avatar_url(user_id)},
        "footer": {"text": "Roblox Presence Tracker"},
        "timestamp": now.isoformat()
    }

    requests.post(WEBHOOK, json={"embeds": [embed]})

def monitor_user(username):
    user_id = get_user_id(username)
    if not user_id:
        print(f"[!] User not found: {username}")
        return

    last_presence_type = None
    last_timestamp = datetime.utcnow()

    # Time tracking (seconds)
    times = {
        "online": 0,
        "offline": 0,
        "game": 0
    }

    user_tracking[username] = {
        "user_id": user_id,
        "times": times,
        "last_status": None
    }

    while True:
        try:
            presence = check_presence(user_id)
            presence_type = presence.get("userPresenceType", 0)
            current_time = datetime.utcnow()
            delta = (current_time - last_timestamp).total_seconds()
            last_timestamp = current_time

            # Time category update
            if presence_type == 0:
                times["offline"] += delta
            else:
                times["online"] += delta
                if presence_type == 2:
                    times["game"] += delta

            # Trigger change event
            if presence_type != last_presence_type:
                event = {
                    0: "Went Offline",
                    1: "Came Online (Website)",
                    2: "Joined Game",
                    3: "Entered Studio",
                }.get(presence_type, "Status Changed")

                send_discord_embed(username, user_id, event, presence, times)

                last_presence_type = presence_type

        except Exception as e:
            print(f"Error tracking {username}: {e}")

        time.sleep(COOLDOWN)

# Launch threads for each user
if __name__ == "__main__":
    for user in USERNAMES:
        threading.Thread(target=monitor_user, args=(user,), daemon=True).start()
    while True:
        time.sleep(60)
