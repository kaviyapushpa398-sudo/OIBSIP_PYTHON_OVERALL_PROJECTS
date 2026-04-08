"""
╔══════════════════════════════════════════╗
║   💬 PyChat CLI — Server                 ║
║   Handles multiple clients via threads   ║
╚══════════════════════════════════════════╝

Usage:
    python cli_server.py [--host HOST] [--port PORT]

Defaults:
    host = 0.0.0.0  (listens on all interfaces)
    port = 9090
"""

import socket
import threading
import argparse
import datetime


# ──────────────────────────────────────────────────────────────
#  GLOBALS
# ──────────────────────────────────────────────────────────────
clients: dict[socket.socket, str] = {}   # socket → username
clients_lock = threading.Lock()          # thread-safe access to clients dict

HOST = "0.0.0.0"
PORT = 9090


# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────
def timestamp() -> str:
    """Return current time as HH:MM string."""
    return datetime.datetime.now().strftime("%H:%M")


def broadcast(message: str, exclude: socket.socket | None = None) -> None:
    """Send a message to every connected client except the sender."""
    encoded = message.encode("utf-8")
    with clients_lock:
        dead = []
        for sock in clients:
            if sock is exclude:
                continue
            try:
                sock.sendall(encoded)
            except OSError:
                dead.append(sock)  # mark for cleanup
        for sock in dead:
            _remove_client(sock)


def _remove_client(sock: socket.socket) -> None:
    """Remove a client socket from the registry (call inside clients_lock)."""
    if sock in clients:
        del clients[sock]
    try:
        sock.close()
    except OSError:
        pass


def server_log(msg: str) -> None:
    """Print a timestamped server log line."""
    print(f"[{timestamp()}] SERVER ▶ {msg}")


# ──────────────────────────────────────────────────────────────
#  CLIENT HANDLER  (runs in its own thread)
# ──────────────────────────────────────────────────────────────
def handle_client(sock: socket.socket, addr: tuple) -> None:
    """
    Lifecycle of a single connected client:
      1. Ask for a username
      2. Register them and notify everyone
      3. Relay every incoming message to all others
      4. Clean up on disconnect
    """
    server_log(f"New connection from {addr[0]}:{addr[1]}")

    # ── Step 1: Collect username ───────────────────────────────
    try:
        sock.sendall("Enter your username: ".encode("utf-8"))
        username = sock.recv(1024).decode("utf-8").strip()
        if not username:
            username = f"User_{addr[1]}"
    except OSError:
        server_log(f"Connection from {addr} dropped before login.")
        sock.close()
        return

    # ── Step 2: Register & announce ───────────────────────────
    with clients_lock:
        clients[sock] = username

    join_msg = f"[{timestamp()}] ✅ {username} joined the chat  ({len(clients)} online)"
    broadcast(join_msg)
    server_log(f"{username} connected — {len(clients)} users online")

    # Send welcome message only to the new user
    welcome = (
        f"\n  Welcome, {username}! 🎉\n"
        f"  {len(clients)} user(s) online. Type /quit to exit.\n"
        f"{'─'*46}\n"
    )
    try:
        sock.sendall(welcome.encode("utf-8"))
    except OSError:
        pass

    # ── Step 3: Message relay loop ─────────────────────────────
    while True:
        try:
            raw = sock.recv(4096)
            if not raw:
                break                    # client closed connection cleanly

            text = raw.decode("utf-8").strip()

            if text.lower() == "/quit":
                break                    # user asked to disconnect

            if text.lower() == "/users":
                # Send list of online users back to requester only
                with clients_lock:
                    names = list(clients.values())
                user_list = "  👥 Online: " + ", ".join(names) + "\n"
                sock.sendall(user_list.encode("utf-8"))
                continue

            # Format and broadcast the message
            formatted = f"[{timestamp()}] {username}: {text}"
            broadcast(formatted, exclude=sock)
            server_log(f"[relay] {username}: {text[:60]}")

        except ConnectionResetError:
            break   # client crashed / force-closed
        except OSError:
            break

    # ── Step 4: Clean up ──────────────────────────────────────
    with clients_lock:
        _remove_client(sock)

    leave_msg = f"[{timestamp()}] ❌ {username} left the chat  ({len(clients)} online)"
    broadcast(leave_msg)
    server_log(f"{username} disconnected — {len(clients)} users remaining")


# ──────────────────────────────────────────────────────────────
#  SERVER ENTRY POINT
# ──────────────────────────────────────────────────────────────
def start_server(host: str = HOST, port: int = PORT) -> None:
    """Bind, listen, and spawn a thread for every accepted connection."""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_sock.bind((host, port))
    except OSError as e:
        print(f"❌  Cannot bind to {host}:{port} → {e}")
        return

    server_sock.listen(20)   # queue up to 20 pending connections
    print(f"\n{'═'*46}")
    print(f"  💬  PyChat CLI Server")
    print(f"  🌐  Listening on {host}:{port}")
    print(f"  ⌨️   Ctrl-C to stop")
    print(f"{'═'*46}\n")

    try:
        while True:
            client_sock, addr = server_sock.accept()
            # Each client gets its own daemon thread so the server
            # continues accepting new connections without blocking.
            t = threading.Thread(
                target=handle_client,
                args=(client_sock, addr),
                daemon=True,   # dies automatically when main thread exits
            )
            t.start()
    except KeyboardInterrupt:
        print("\n\n  🛑  Server shutting down...")
    finally:
        # Notify all connected clients
        broadcast("[SERVER] 🛑 Server is shutting down. Goodbye!")
        with clients_lock:
            for s in list(clients):
                s.close()
        server_sock.close()
        print("  ✅  Server stopped cleanly.")


# ──────────────────────────────────────────────────────────────
#  CLI ARGUMENT PARSING
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyChat CLI Server")
    parser.add_argument("--host", default=HOST, help="Bind address")
    parser.add_argument("--port", type=int, default=PORT, help="Port number")
    args = parser.parse_args()
    start_server(args.host, args.port)
