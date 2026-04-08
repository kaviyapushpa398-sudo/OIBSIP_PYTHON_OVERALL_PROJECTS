"""
╔══════════════════════════════════════════════════════════════╗
║   💬 PyChat Advanced — Server                                ║
║                                                              ║
║   Features:                                                  ║
║     • Multi-room chat (join / leave / list)                  ║
║     • User registration & login (SHA-256 + salt)             ║
║     • Message history stored in SQLite                       ║
║     • Private (DM) messaging                                 ║
║     • Image / file sharing (base64)                          ║
║     • Online user tracking per room                          ║
║     • JSON protocol with 4-byte length-prefix framing        ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python advanced_server.py [--host HOST] [--port PORT]
"""

import socket
import threading
import json
import struct
import sqlite3
import hashlib
import secrets
import datetime
import argparse
import os

# ──────────────────────────────────────────────────────────────
#  CONFIGURATION
# ──────────────────────────────────────────────────────────────
HOST     = "0.0.0.0"
PORT     = 9191
DB_PATH  = os.path.join(os.path.dirname(__file__), "chat.db")
MAX_HIST = 50      # messages of history to send on room join
ENCODING = "utf-8"


# ──────────────────────────────────────────────────────────────
#  MESSAGE FRAMING UTILITIES
#  Protocol: [4-byte big-endian length][JSON payload bytes]
# ──────────────────────────────────────────────────────────────
def send_msg(sock: socket.socket, obj: dict) -> None:
    """Serialise obj to JSON and send with a 4-byte length prefix."""
    data = json.dumps(obj, ensure_ascii=False).encode(ENCODING)
    header = struct.pack(">I", len(data))   # big-endian uint32
    try:
        sock.sendall(header + data)
    except OSError:
        pass


def recv_msg(sock: socket.socket) -> dict | None:
    """
    Read exactly 4 bytes for the length, then that many bytes for payload.
    Returns parsed dict or None if the connection was closed / errored.
    """
    try:
        header = _recv_exact(sock, 4)
        if header is None:
            return None
        length = struct.unpack(">I", header)[0]
        body   = _recv_exact(sock, length)
        if body is None:
            return None
        return json.loads(body.decode(ENCODING))
    except (OSError, json.JSONDecodeError):
        return None


def _recv_exact(sock: socket.socket, n: int) -> bytes | None:
    """Read exactly n bytes from sock, or return None on disconnect."""
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


# ──────────────────────────────────────────────────────────────
#  DATABASE SETUP
# ──────────────────────────────────────────────────────────────
def init_db() -> None:
    """Create tables if they don't already exist."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Users table — passwords stored as  salt:sha256hash
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL COLLATE NOCASE,
            salt       TEXT NOT NULL,
            pw_hash    TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # Messages table — all rooms stored here, filterable by room
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            room       TEXT NOT NULL,
            sender     TEXT NOT NULL,
            content    TEXT NOT NULL,
            msg_type   TEXT NOT NULL DEFAULT 'text',
            timestamp  TEXT NOT NULL
        )
    """)

    # Default rooms
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            name        TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            created_at  TEXT NOT NULL
        )
    """)
    defaults = [
        ("general",  "Main chat room",       now()),
        ("random",   "Off-topic discussion", now()),
        ("tech",     "Tech talk",            now()),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO rooms (name, description, created_at) VALUES (?,?,?)",
        defaults,
    )
    con.commit()
    con.close()


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────────────────────
#  AUTH HELPERS
# ──────────────────────────────────────────────────────────────
def hash_password(password: str, salt: str) -> str:
    """Return hex digest of SHA-256(salt + password)."""
    combined = (salt + password).encode(ENCODING)
    return hashlib.sha256(combined).hexdigest()


def register_user(username: str, password: str) -> tuple[bool, str]:
    """Insert a new user; returns (success, message)."""
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    salt    = secrets.token_hex(16)
    pw_hash = hash_password(password, salt)

    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO users (username, salt, pw_hash, created_at) VALUES (?,?,?,?)",
            (username, salt, pw_hash, now()),
        )
        con.commit()
        con.close()
        return True, "Registration successful."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' is already taken."


def verify_user(username: str, password: str) -> tuple[bool, str]:
    """Check credentials; returns (success, message)."""
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT salt, pw_hash FROM users WHERE username=? COLLATE NOCASE",
        (username,),
    ).fetchone()
    con.close()

    if row is None:
        return False, "Username not found."

    salt, stored_hash = row
    if hash_password(password, salt) == stored_hash:
        return True, "Login successful."
    return False, "Incorrect password."


# ──────────────────────────────────────────────────────────────
#  MESSAGE HISTORY
# ──────────────────────────────────────────────────────────────
def save_message(room: str, sender: str, content: str, msg_type: str = "text") -> None:
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT INTO messages (room, sender, content, msg_type, timestamp) VALUES (?,?,?,?,?)",
        (room, sender, content, msg_type, now()),
    )
    con.commit()
    con.close()


def get_history(room: str, limit: int = MAX_HIST) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        """SELECT sender, content, msg_type, timestamp
           FROM messages WHERE room=?
           ORDER BY id DESC LIMIT ?""",
        (room, limit),
    ).fetchall()
    con.close()
    return [
        {"sender": r[0], "content": r[1], "msg_type": r[2], "timestamp": r[3]}
        for r in reversed(rows)
    ]


def get_room_list() -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("SELECT name, description FROM rooms").fetchall()
    con.close()
    return [{"name": r[0], "description": r[1]} for r in rows]


def create_room(name: str, description: str = "") -> tuple[bool, str]:
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute(
            "INSERT INTO rooms (name, description, created_at) VALUES (?,?,?)",
            (name.lower(), description, now()),
        )
        con.commit()
        con.close()
        return True, f"Room #{name} created."
    except sqlite3.IntegrityError:
        return False, f"Room #{name} already exists."


# ──────────────────────────────────────────────────────────────
#  SERVER STATE
# ──────────────────────────────────────────────────────────────
# rooms_users: room_name → set of usernames currently in the room
rooms_users: dict[str, set[str]] = {"general": set(), "random": set(), "tech": set()}
rooms_lock   = threading.Lock()

# clients: username → socket
clients: dict[str, socket.socket] = {}
clients_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────
#  BROADCAST / UNICAST
# ──────────────────────────────────────────────────────────────
def broadcast_room(room: str, msg: dict, exclude: str | None = None) -> None:
    """Send msg to everyone in the given room except exclude."""
    with rooms_lock:
        members = set(rooms_users.get(room, []))

    with clients_lock:
        for username in members:
            if username == exclude:
                continue
            sock = clients.get(username)
            if sock:
                send_msg(sock, msg)


def send_to(username: str, msg: dict) -> bool:
    """Send msg to a specific user; returns False if not online."""
    with clients_lock:
        sock = clients.get(username)
    if sock:
        send_msg(sock, msg)
        return True
    return False


def notify_room(room: str, text: str, exclude: str | None = None) -> None:
    """Send a server notification to a room."""
    broadcast_room(room, {
        "type":      "NOTIFICATION",
        "room":      room,
        "message":   text,
        "timestamp": now(),
    }, exclude=exclude)


# ──────────────────────────────────────────────────────────────
#  CLIENT HANDLER
# ──────────────────────────────────────────────────────────────
def handle_client(sock: socket.socket, addr: tuple) -> None:
    """Full lifecycle of one connected client."""
    username = None

    # ── Authentication phase ───────────────────────────────────
    try:
        auth_msg = recv_msg(sock)
        if auth_msg is None:
            sock.close()
            return

        msg_type = auth_msg.get("type")
        uname    = auth_msg.get("username", "").strip()
        passwd   = auth_msg.get("password", "")

        if msg_type == "REGISTER":
            ok, info = register_user(uname, passwd)
            send_msg(sock, {"type": "AUTH_SUCCESS" if ok else "AUTH_ERROR",
                            "message": info, "username": uname if ok else ""})
            if not ok:
                sock.close()
                return
        elif msg_type == "LOGIN":
            ok, info = verify_user(uname, passwd)
            send_msg(sock, {"type": "AUTH_SUCCESS" if ok else "AUTH_ERROR",
                            "message": info, "username": uname if ok else ""})
            if not ok:
                sock.close()
                return
        else:
            send_msg(sock, {"type": "AUTH_ERROR", "message": "Send LOGIN or REGISTER first."})
            sock.close()
            return

        username = uname

        # Check for duplicate login
        with clients_lock:
            if username in clients:
                send_msg(sock, {"type": "AUTH_ERROR",
                                "message": f"'{username}' is already logged in."})
                sock.close()
                return
            clients[username] = sock

        log(f"✅ {username} authenticated from {addr[0]}:{addr[1]}")

    except OSError:
        sock.close()
        return

    # ── Auto-join General ──────────────────────────────────────
    _join_room(username, "general", sock)

    # ── Message relay loop ─────────────────────────────────────
    try:
        while True:
            msg = recv_msg(sock)
            if msg is None:
                break   # connection dropped

            mtype   = msg.get("type", "")
            room    = msg.get("room", "general")
            content = msg.get("content", "")

            # ── TEXT MESSAGE ─────────────────────────────────
            if mtype == "MESSAGE":
                if not content.strip():
                    continue
                save_message(room, username, content, "text")
                broadcast_room(room, {
                    "type":      "MESSAGE",
                    "room":      room,
                    "sender":    username,
                    "content":   content,
                    "timestamp": now(),
                }, exclude=username)

            # ── IMAGE / FILE ─────────────────────────────────
            elif mtype == "IMAGE":
                filename = msg.get("filename", "image.png")
                data_b64 = msg.get("data", "")
                save_message(room, username, filename, "image")
                broadcast_room(room, {
                    "type":      "IMAGE",
                    "room":      room,
                    "sender":    username,
                    "filename":  filename,
                    "data":      data_b64,
                    "timestamp": now(),
                }, exclude=username)

            # ── PRIVATE MESSAGE ──────────────────────────────
            elif mtype == "PRIVATE":
                to      = msg.get("to", "")
                reached = send_to(to, {
                    "type":      "PRIVATE",
                    "from":      username,
                    "content":   content,
                    "timestamp": now(),
                })
                send_msg(sock, {
                    "type":    "PRIVATE_ACK",
                    "to":      to,
                    "content": content,
                    "reached": reached,
                })

            # ── JOIN ROOM ────────────────────────────────────
            elif mtype == "JOIN_ROOM":
                room_name = msg.get("room", "").lower()
                _join_room(username, room_name, sock)

            # ── LEAVE ROOM ───────────────────────────────────
            elif mtype == "LEAVE_ROOM":
                _leave_room(username, room)

            # ── CREATE ROOM ──────────────────────────────────
            elif mtype == "CREATE_ROOM":
                room_name = msg.get("room", "").lower().strip()
                desc      = msg.get("description", "")
                ok, info  = create_room(room_name, desc)
                if ok:
                    with rooms_lock:
                        rooms_users[room_name] = set()
                send_msg(sock, {"type": "ROOM_CREATED" if ok else "ERROR",
                                "message": info})

            # ── LIST ROOMS ───────────────────────────────────
            elif mtype == "LIST_ROOMS":
                rooms = get_room_list()
                with rooms_lock:
                    for r in rooms:
                        r["online"] = len(rooms_users.get(r["name"], set()))
                send_msg(sock, {"type": "ROOM_LIST", "rooms": rooms})

            # ── LIST USERS IN ROOM ───────────────────────────
            elif mtype == "LIST_USERS":
                with rooms_lock:
                    users = list(rooms_users.get(room, []))
                send_msg(sock, {"type": "USER_LIST", "room": room, "users": users})

            # ── ONLINE COUNT ─────────────────────────────────
            elif mtype == "ONLINE_COUNT":
                with clients_lock:
                    count = len(clients)
                send_msg(sock, {"type": "ONLINE_COUNT", "count": count})

    except Exception as e:
        log(f"⚠️  Error handling {username}: {e}")

    # ── Cleanup ────────────────────────────────────────────────
    finally:
        if username:
            # Leave all rooms
            with rooms_lock:
                for room_set in rooms_users.values():
                    room_set.discard(username)
            with clients_lock:
                clients.pop(username, None)
            log(f"❌ {username} disconnected — {len(clients)} online")
            # Notify all rooms they were in (best effort)
            for room_name in list(rooms_users.keys()):
                notify_room(room_name, f"👋 {username} went offline")
        sock.close()


# ──────────────────────────────────────────────────────────────
#  ROOM JOIN / LEAVE HELPERS
# ──────────────────────────────────────────────────────────────
def _join_room(username: str, room_name: str, sock: socket.socket) -> None:
    """Add user to room, send history, notify members."""
    # Verify room exists in DB
    con = sqlite3.connect(DB_PATH)
    exists = con.execute("SELECT 1 FROM rooms WHERE name=?", (room_name,)).fetchone()
    con.close()
    if not exists:
        send_msg(sock, {"type": "ERROR", "message": f"Room #{room_name} does not exist."})
        return

    with rooms_lock:
        rooms_users.setdefault(room_name, set()).add(username)
        members = list(rooms_users[room_name])

    # Send join success + history + user list
    history = get_history(room_name)
    send_msg(sock, {
        "type":    "JOIN_SUCCESS",
        "room":    room_name,
        "history": history,
        "users":   members,
    })
    notify_room(room_name, f"➡️  {username} joined #{room_name}", exclude=username)
    log(f"  {username} joined #{room_name}")


def _leave_room(username: str, room_name: str) -> None:
    with rooms_lock:
        rooms_users.get(room_name, set()).discard(username)
    notify_room(room_name, f"⬅️  {username} left #{room_name}")
    log(f"  {username} left #{room_name}")


# ──────────────────────────────────────────────────────────────
#  LOGGING
# ──────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# ──────────────────────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────────────────────
def start_server(host: str = HOST, port: int = PORT) -> None:
    init_db()
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((host, port))
    except OSError as e:
        print(f"❌  Bind failed on {host}:{port} → {e}")
        return

    server_sock.listen(50)
    print(f"\n{'═'*50}")
    print(f"  💬  PyChat Advanced Server")
    print(f"  🌐  {host}:{port}  |  DB: {DB_PATH}")
    print(f"  ⌨️   Ctrl-C to stop")
    print(f"{'═'*50}\n")

    try:
        while True:
            client_sock, addr = server_sock.accept()
            threading.Thread(
                target=handle_client,
                args=(client_sock, addr),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n  🛑  Shutting down …")
    finally:
        server_sock.close()
        print("  ✅  Server stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyChat Advanced Server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    start_server(args.host, args.port)
