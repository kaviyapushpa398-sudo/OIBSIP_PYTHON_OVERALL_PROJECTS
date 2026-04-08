"""
╔══════════════════════════════════════════╗
║   💬 PyChat CLI — Client                 ║
║   Connect to a running PyChat server     ║
╚══════════════════════════════════════════╝

Usage:
    python cli_client.py [--host HOST] [--port PORT]

Commands while connected:
    /quit     — Disconnect and exit
    /users    — List online users
"""

import socket
import threading
import sys
import argparse


# ──────────────────────────────────────────────────────────────
#  DEFAULTS
# ──────────────────────────────────────────────────────────────
HOST = "127.0.0.1"   # connect to localhost by default
PORT = 9090


# ──────────────────────────────────────────────────────────────
#  RECEIVE THREAD  — runs in background, prints incoming msgs
# ──────────────────────────────────────────────────────────────
def receive_messages(sock: socket.socket, stop_event: threading.Event) -> None:
    """
    Continuously read from the server socket and print messages.
    Sets stop_event when the connection drops so the send loop can exit.
    """
    while not stop_event.is_set():
        try:
            data = sock.recv(4096)
            if not data:
                # Server closed the connection
                print("\n\n  🔌  Connection closed by server.")
                stop_event.set()
                break

            message = data.decode("utf-8")
            # Move cursor to start of line, clear it, then print message
            # so it doesn't interleave with what the user is typing
            sys.stdout.write(f"\r{' ' * 80}\r")   # clear current input line
            print(message, end="" if message.endswith("\n") else "\n")
            sys.stdout.write("  You ▶ ")
            sys.stdout.flush()

        except OSError:
            if not stop_event.is_set():
                print("\n  ❌  Lost connection to server.")
            stop_event.set()
            break


# ──────────────────────────────────────────────────────────────
#  SEND LOOP  — runs on the main thread, reads stdin
# ──────────────────────────────────────────────────────────────
def send_messages(sock: socket.socket, stop_event: threading.Event) -> None:
    """
    Read lines from stdin and send them to the server.
    Exits when the user types /quit or the connection drops.
    """
    while not stop_event.is_set():
        try:
            sys.stdout.write("  You ▶ ")
            sys.stdout.flush()
            text = input()   # blocks until Enter is pressed

            if stop_event.is_set():
                break

            if not text.strip():
                continue     # don't send blank messages

            sock.sendall(text.encode("utf-8"))

            if text.strip().lower() == "/quit":
                stop_event.set()
                break

        except (EOFError, KeyboardInterrupt):
            # Ctrl-C / Ctrl-D
            try:
                sock.sendall("/quit".encode("utf-8"))
            except OSError:
                pass
            stop_event.set()
            break
        except OSError:
            stop_event.set()
            break


# ──────────────────────────────────────────────────────────────
#  MAIN — connect and launch threads
# ──────────────────────────────────────────────────────────────
def start_client(host: str = HOST, port: int = PORT) -> None:
    """Connect to the server, then hand off to send/receive threads."""
    print(f"\n{'═'*46}")
    print(f"  💬  PyChat CLI Client")
    print(f"  🔌  Connecting to {host}:{port} …")
    print(f"{'═'*46}\n")

    # ── Create socket and connect ──────────────────────────────
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except ConnectionRefusedError:
        print(f"  ❌  Cannot connect to {host}:{port}.")
        print("  ▶   Is the server running?  python cli_server.py\n")
        return
    except OSError as e:
        print(f"  ❌  Connection error: {e}\n")
        return

    print("  ✅  Connected! Type /users to list online users, /quit to exit.\n")

    # stop_event lets both threads exit cleanly when either side drops
    stop_event = threading.Event()

    # ── Spawn background receive thread ───────────────────────
    recv_thread = threading.Thread(
        target=receive_messages,
        args=(sock, stop_event),
        daemon=True,
    )
    recv_thread.start()

    # ── Run send loop on main thread ──────────────────────────
    send_messages(sock, stop_event)

    # ── Tear down ─────────────────────────────────────────────
    sock.close()
    print("\n  👋  Disconnected. Goodbye!\n")


# ──────────────────────────────────────────────────────────────
#  CLI ARGUMENT PARSING
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PyChat CLI Client")
    parser.add_argument("--host", default=HOST, help="Server IP address")
    parser.add_argument("--port", type=int, default=PORT, help="Server port")
    args = parser.parse_args()
    start_client(args.host, args.port)
