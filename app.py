from flask import Flask, render_template, request, redirect, session, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
import random

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Change for production
socketio = SocketIO(app)

waiting_users = []
user_rooms = {}
user_sid_map = {}  # username -> sid

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        if username:
            session["username"] = username
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session["username"])

@socketio.on("join")
def handle_join():
    username = session.get("username")
    sid = request.sid
    user_sid_map[username] = sid

    if waiting_users:
        partner_username = waiting_users.pop(0)
        partner_sid = user_sid_map[partner_username]
        room = f"room_{username}_{partner_username}"
        join_room(room, sid)
        join_room(room, partner_sid)
        user_rooms[username] = room
        user_rooms[partner_username] = room
        emit("match", {"partner": partner_username}, to=sid)
        emit("match", {"partner": username}, to=partner_sid)
    else:
        waiting_users.append(username)

@socketio.on("next")
def handle_next():
    username = session.get("username")
    sid = request.sid
    leave_room(user_rooms.get(username, ""), sid)
    if username in waiting_users:
        waiting_users.remove(username)
    handle_join()

@socketio.on("stop")
def handle_stop():
    username = session.get("username")
    room = user_rooms.get(username, "")
    if room:
        emit("stop_chat", to=room)
    if username in waiting_users:
        waiting_users.remove(username)
    leave_room(room)

@socketio.on("signal")
def handle_signal(data):
    emit("signal", data, to=user_sid_map.get(data["target"]))

@socketio.on("disconnect")
def handle_disconnect():
    username = None
    for user, sid in list(user_sid_map.items()):
        if sid == request.sid:
            username = user
            break
    if username:
        user_sid_map.pop(username, None)
        if username in waiting_users:
            waiting_users.remove(username)
        if username in user_rooms:
            room = user_rooms.pop(username)
            emit("stop_chat", to=room)
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)