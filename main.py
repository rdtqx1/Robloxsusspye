import time, threading, requests
from datetime import datetime
from dotenv import load_dotenv
import os
from keep_alive import keep_alive

load_dotenv()
WEBHOOK = os.getenv("WEB")
ROBLOSECURITY = os.getenv("ROBLOSECURITY")
COOLDOWN = 5

HEADERS = {"Content-Type":"application/json","Cookie":f".ROBLOSECURITY={ROBLOSECURITY}"}
USERNAMES = ["9Dcx","bjkqt1","mwaochaa"]

def get_user_id(name):
    resp = requests.post("https://users.roblox.com/v1/usernames/users",
                         json={"usernames":[name],"excludeBannedUsers":False}, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json().get("data",[])
    return data[0]["id"] if data else None

def check_presence(uid):
    resp = requests.post("https://presence.roblox.com/v1/presence/users",
                         json={"userIds":[uid]}, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()["userPresences"][0]

def get_game_name(place_id):
    resp = requests.get(f"https://games.roblox.com/v1/games?universeIds={place_id}")
    if resp.ok:
        info = resp.json().get("data",[])
        return info[0].get("name") if info else None
    return None

def send_embed(username, event, status_code, place_id, start_time, end_time):
    status_names=["Offline","Online","In Game","In Studio","Invisible"]
    status=status_names[status_code] if status_code<len(status_names) else f"Unknown({status_code})"
    now = datetime.utcnow()
    duration = f"{(now - start_time).seconds // 60}m {(now - start_time).seconds % 60}s" if start_time else "N/A"
    embed={"title":f"{username} – {event}",
           "color":0x00ff00 if status_code else 0xff0000,
           "fields":[
             {"name":"New Status","value":status,"inline":True},
             {"name":"Since","value":start_time.strftime('%Y-%m-%d %H:%M:%S UTC'),"inline":True},
             {"name":"Duration","value":duration,"inline":True}],
           "footer":{"text":"Advanced Roblox Tracker"}}
    if status_code==2 and place_id:
        name=get_game_name(place_id)
        url=f"https://www.roblox.com/games/{place_id}"
        embed["fields"] += [
          {"name":"Game","value":name or "Unknown","inline":True},
          {"name":"Link","value":f"[Enter Game]({url})","inline":False}]
    requests.post(WEBHOOK, json={"embeds":[embed]})

def monitor_user(name):
    uid=get_user_id(name)
    if not uid:
        print(f"❌ {name} not found"); return
    last_status=None; last_game=None; start_time=None
    while True:
        try:
            p=check_presence(uid)
            s=p.get("userPresenceType",0)
            g=p.get("placeId")
            if s!=last_status or g!=last_game:
                event="Status Changed"
                if last_status is None: event="Tracker Started"
                elif s==0: event="Went Offline"
                elif last_status==0 and s!=0: event="Came Online"
                elif g and g!=last_game: event="Joined New Game"
                send_embed(name, event, s, g, datetime.utcnow(), None)
                last_status,s_last = s,s
                last_game,g_last = g,g
                start_time=datetime.utcnow()
            time.sleep(COOLDOWN)
        except Exception as e:
            print(f"Error {name}:",e)
            time.sleep(COOLDOWN)

if __name__=="__main__":
    keep_alive()
    for u in USERNAMES:
        threading.Thread(target=monitor_user,args=(u,),daemon=True).start()
    while True: time.sleep(60)
