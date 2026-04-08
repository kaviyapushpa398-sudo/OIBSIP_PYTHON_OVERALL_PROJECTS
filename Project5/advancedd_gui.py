"""
╔══════════════════════════════════════════════════════════════╗
║   💬 PyChat Advanced — GUI Client                            ║
║   Tkinter-based chat client                                  ║
║                                                              ║
║   Features:                                                  ║
║     • Login / Register screen                                ║
║     • Multi-room sidebar (join / create rooms)               ║
║     • Bubble-style message display                           ║
║     • Private DM (click username)                            ║
║     • Emoji picker panel                                     ║
║     • Image / file sharing (base64)                          ║
║     • Desktop notifications (flash title bar)                ║
║     • Unread badge counts per room                           ║
║     • Sleek dark theme                                       ║
╚══════════════════════════════════════════════════════════════╝

Usage:
    python advanced_gui.py [--host HOST] [--port PORT]
"""

import socket
import threading
import json
import struct
import base64
import os
import argparse
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from typing import Optional

# Optional image support
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ──────────────────────────────────────────────────────────────
#  DEFAULTS
# ──────────────────────────────────────────────────────────────
HOST     = "127.0.0.1"
PORT     = 9191
ENCODING = "utf-8"

# ──────────────────────────────────────────────────────────────
#  COLOURS  (dark theme)
# ──────────────────────────────────────────────────────────────
C = {
    "bg":          "#0d1117",
    "sidebar":     "#161b22",
    "panel":       "#1c2128",
    "card":        "#21262d",
    "accent":      "#58a6ff",
    "accent2":     "#3fb950",
    "accent_dm":   "#f0883e",
    "text":        "#e6edf3",
    "subtext":     "#8b949e",
    "border":      "#30363d",
    "own_bubble":  "#1f4175",   # user's own messages
    "other_bubble":"#2d333b",   # others' messages
    "notify":      "#da3633",
    "input_bg":    "#1c2128",
    "btn":         "#21262d",
    "btn_hover":   "#30363d",
    "room_active": "#1f4175",
}

EMOJIS = [
    "😀","😂","😍","🥺","😎","🤔","👍","👎","❤️","🔥",
    "🎉","😅","🙏","💯","😭","🤣","✨","😊","🤩","😤",
    "🤦","👀","💬","🚀","🎮","💻","📱","🌍","🍕","☕",
]


# ──────────────────────────────────────────────────────────────
#  PROTOCOL HELPERS  (mirrors advanced_server.py)
# ──────────────────────────────────────────────────────────────
def send_msg(sock: socket.socket, obj: dict) -> None:
    data   = json.dumps(obj, ensure_ascii=False).encode(ENCODING)
    header = struct.pack(">I", len(data))
    try:
        sock.sendall(header + data)
    except OSError:
        pass


def recv_msg(sock: socket.socket) -> Optional[dict]:
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


def _recv_exact(sock: socket.socket, n: int) -> Optional[bytes]:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def ts_now() -> str:
    return datetime.datetime.now().strftime("%H:%M")


# ──────────────────────────────────────────────────────────────
#  TOOLTIP HELPER
# ──────────────────────────────────────────────────────────────
class Tooltip:
    """Simple tooltip that appears on hover."""
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text   = text
        self.tip    = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, bg="#30363d", fg=C["text"],
                 font=("Helvetica", 9), padx=6, pady=3).pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ══════════════════════════════════════════════════════════════
#  LOGIN WINDOW
# ══════════════════════════════════════════════════════════════
class LoginWindow(tk.Tk):
    """First screen: connect info + login or register."""

    def __init__(self, host: str, port: int):
        super().__init__()
        self.host = host
        self.port = port
        self.result: Optional[dict] = None   # filled on success

        self.title("PyChat — Sign In")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self._center()
        self._build()

    def _center(self):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - 420) // 2
        y  = (sh - 520) // 2
        self.geometry(f"420x520+{x}+{y}")

    def _build(self):
        # ── Brand header ─────────────────────────────────
        hdr = tk.Frame(self, bg=C["bg"], pady=30)
        hdr.pack(fill="x")
        tk.Label(hdr, text="💬", font=("Helvetica", 40),
                 bg=C["bg"], fg=C["accent"]).pack()
        tk.Label(hdr, text="PyChat", font=("Helvetica", 22, "bold"),
                 bg=C["bg"], fg=C["text"]).pack()
        tk.Label(hdr, text="Real-time messaging", font=("Helvetica", 10),
                 bg=C["bg"], fg=C["subtext"]).pack(pady=(2, 0))

        # ── Card ─────────────────────────────────────────
        card = tk.Frame(self, bg=C["panel"], padx=32, pady=24)
        card.pack(fill="x", padx=32)

        # Server address
        tk.Label(card, text="Server", font=("Helvetica", 9),
                 bg=C["panel"], fg=C["subtext"], anchor="w").pack(fill="x")
        srv_row = tk.Frame(card, bg=C["panel"])
        srv_row.pack(fill="x", pady=(2, 12))
        self.host_var = tk.StringVar(value=self.host)
        self.port_var = tk.StringVar(value=str(self.port))
        tk.Entry(srv_row, textvariable=self.host_var,
                 **self._entry_style(), width=18).pack(side="left")
        tk.Label(srv_row, text=":", bg=C["panel"], fg=C["subtext"],
                 font=("Helvetica", 12)).pack(side="left", padx=4)
        tk.Entry(srv_row, textvariable=self.port_var,
                 **self._entry_style(), width=6).pack(side="left")

        # Username
        tk.Label(card, text="Username", font=("Helvetica", 9),
                 bg=C["panel"], fg=C["subtext"], anchor="w").pack(fill="x")
        self.user_var = tk.StringVar()
        tk.Entry(card, textvariable=self.user_var,
                 **self._entry_style()).pack(fill="x", pady=(2, 12), ipady=6)

        # Password
        tk.Label(card, text="Password", font=("Helvetica", 9),
                 bg=C["panel"], fg=C["subtext"], anchor="w").pack(fill="x")
        self.pass_var = tk.StringVar()
        tk.Entry(card, textvariable=self.pass_var, show="•",
                 **self._entry_style()).pack(fill="x", pady=(2, 18), ipady=6)

        # Buttons
        btn_row = tk.Frame(card, bg=C["panel"])
        btn_row.pack(fill="x")
        btn_row.columnconfigure((0, 1), weight=1)

        self.btn_login = tk.Button(
            btn_row, text="Sign In",
            font=("Helvetica", 11, "bold"),
            bg=C["accent"], fg="#fff",
            activebackground="#388bde", activeforeground="#fff",
            relief="flat", cursor="hand2",
            command=lambda: self._attempt("LOGIN"),
        )
        self.btn_login.grid(row=0, column=0, sticky="ew", padx=(0, 6), ipady=8)

        self.btn_reg = tk.Button(
            btn_row, text="Register",
            font=("Helvetica", 11),
            bg=C["card"], fg=C["text"],
            activebackground=C["btn_hover"], activeforeground=C["text"],
            relief="flat", cursor="hand2",
            command=lambda: self._attempt("REGISTER"),
        )
        self.btn_reg.grid(row=0, column=1, sticky="ew", ipady=8)

        # Status label
        self.status_var = tk.StringVar()
        tk.Label(self, textvariable=self.status_var,
                 bg=C["bg"], fg=C["notify"],
                 font=("Helvetica", 9), wraplength=360).pack(pady=(12, 0))

        # Bind Enter key
        self.bind("<Return>", lambda e: self._attempt("LOGIN"))

    def _entry_style(self) -> dict:
        return dict(
            bg=C["card"], fg=C["text"], insertbackground=C["text"],
            relief="flat", bd=6, font=("Helvetica", 11),
            highlightbackground=C["border"], highlightthickness=1,
        )

    def _attempt(self, msg_type: str):
        host = self.host_var.get().strip()
        port_str = self.port_var.get().strip()
        username = self.user_var.get().strip()
        password = self.pass_var.get()

        if not username or not password:
            self.status_var.set("⚠️  Username and password are required.")
            return

        try:
            port = int(port_str)
        except ValueError:
            self.status_var.set("⚠️  Invalid port number.")
            return

        self.status_var.set("🔌  Connecting …")
        self.update()

        # Try to connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            sock.settimeout(None)
        except (ConnectionRefusedError, OSError) as e:
            self.status_var.set(f"❌  Cannot connect: {e}")
            return

        # Send auth
        send_msg(sock, {"type": msg_type, "username": username, "password": password})
        response = recv_msg(sock)

        if response is None or response.get("type") == "AUTH_ERROR":
            msg = response.get("message", "Authentication failed.") if response else "No response."
            self.status_var.set(f"❌  {msg}")
            sock.close()
            return

        # Success
        self.result = {"sock": sock, "username": username}
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT WINDOW
# ══════════════════════════════════════════════════════════════
class ChatWindow(tk.Tk):
    """
    Full chat interface with:
      • Left sidebar — rooms + online users
      • Center — scrollable message bubbles
      • Bottom bar — emoji, input, send, attach
    """

    def __init__(self, sock: socket.socket, username: str):
        super().__init__()
        self.sock      = sock
        self.username  = username
        self.current_room = "general"
        self.rooms: dict[str, dict] = {}       # room_name → {frame, text_widget, unread}
        self.dm_windows: dict[str, "DMWindow"] = {}
        self.emoji_panel: Optional[tk.Toplevel] = None
        self.stop_event = threading.Event()

        self.title(f"💬 PyChat  —  {username}")
        self.geometry("1080x700")
        self.minsize(760, 500)
        self.configure(bg=C["bg"])
        self._center()
        self._build_ui()
        self._start_receive_thread()

        # Ask server for room list
        send_msg(self.sock, {"type": "LIST_ROOMS"})
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center(self):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"1080x700+{(sw-1080)//2}+{(sh-700)//2}")

    # ──────────────────────────────────────────────────────────
    #  UI CONSTRUCTION
    # ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=220)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Sidebar ───────────────────────────────────────────
        self.sidebar = tk.Frame(self, bg=C["sidebar"], width=220)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(2, weight=1)
        self.sidebar.rowconfigure(4, weight=1)

        # Brand
        brand = tk.Frame(self.sidebar, bg=C["sidebar"], pady=14)
        brand.grid(row=0, column=0, sticky="ew")
        tk.Label(brand, text="💬 PyChat", font=("Helvetica", 14, "bold"),
                 bg=C["sidebar"], fg=C["accent"]).pack()
        self.lbl_online = tk.Label(brand, text="● 1 online",
                                   font=("Helvetica", 8),
                                   bg=C["sidebar"], fg=C["accent2"])
        self.lbl_online.pack()

        # Rooms section
        rh = tk.Frame(self.sidebar, bg=C["sidebar"])
        rh.grid(row=1, column=0, sticky="ew", padx=10, pady=(6, 2))
        tk.Label(rh, text="ROOMS", font=("Helvetica", 8, "bold"),
                 bg=C["sidebar"], fg=C["subtext"]).pack(side="left")
        tk.Button(rh, text="+", font=("Helvetica", 10), bg=C["sidebar"],
                  fg=C["subtext"], relief="flat", cursor="hand2",
                  command=self._open_create_room).pack(side="right")

        self.room_list_frame = tk.Frame(self.sidebar, bg=C["sidebar"])
        self.room_list_frame.grid(row=2, column=0, sticky="nsew")

        # Separator
        tk.Frame(self.sidebar, bg=C["border"], height=1).grid(
            row=3, column=0, sticky="ew", padx=10, pady=6)

        # Online users section
        tk.Label(self.sidebar, text="ONLINE", font=("Helvetica", 8, "bold"),
                 bg=C["sidebar"], fg=C["subtext"], anchor="w").grid(
            row=3, column=0, sticky="ew", padx=10, pady=(2, 2))

        self.user_list_frame = tk.Frame(self.sidebar, bg=C["sidebar"])
        self.user_list_frame.grid(row=4, column=0, sticky="nsew")

        # User info at bottom
        bottom = tk.Frame(self.sidebar, bg=C["panel"], pady=8)
        bottom.grid(row=5, column=0, sticky="ew")
        tk.Label(bottom, text=f"  👤 {self.username}",
                 font=("Helvetica", 10, "bold"),
                 bg=C["panel"], fg=C["text"], anchor="w").pack(fill="x")
        tk.Label(bottom, text="  Connected",
                 font=("Helvetica", 8),
                 bg=C["panel"], fg=C["accent2"], anchor="w").pack(fill="x")

        # ── Main panel ─────────────────────────────────────────
        self.main_frame = tk.Frame(self, bg=C["bg"])
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Top bar
        self.top_bar = tk.Frame(self.main_frame, bg=C["panel"], height=50)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        self.top_bar.columnconfigure(0, weight=1)
        self.top_bar.grid_propagate(False)

        self.lbl_room = tk.Label(self.top_bar, text="# general",
                                  font=("Helvetica", 13, "bold"),
                                  bg=C["panel"], fg=C["text"], anchor="w", padx=16)
        self.lbl_room.grid(row=0, column=0, sticky="ew", pady=12)

        self.lbl_members = tk.Label(self.top_bar, text="",
                                     font=("Helvetica", 9),
                                     bg=C["panel"], fg=C["subtext"], padx=16)
        self.lbl_members.grid(row=0, column=1, sticky="e")

        # ── Message notebook (one tab per room) ───────────────
        self.msg_container = tk.Frame(self.main_frame, bg=C["bg"])
        self.msg_container.grid(row=1, column=0, sticky="nsew")
        self.msg_container.columnconfigure(0, weight=1)
        self.msg_container.rowconfigure(0, weight=1)

        # ── Input bar ─────────────────────────────────────────
        self._build_input_bar()

    def _build_input_bar(self):
        bar = tk.Frame(self.main_frame, bg=C["panel"], pady=10)
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        # Emoji button
        btn_emoji = tk.Button(bar, text="😀", font=("Helvetica", 14),
                               bg=C["panel"], fg=C["text"],
                               activebackground=C["panel"],
                               relief="flat", cursor="hand2",
                               command=self._toggle_emoji_panel)
        btn_emoji.grid(row=0, column=0, padx=(12, 4))
        Tooltip(btn_emoji, "Emoji picker")

        # Text input
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            bar, textvariable=self.input_var,
            font=("Helvetica", 12),
            bg=C["input_bg"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=8,
            highlightbackground=C["border"],
            highlightthickness=1,
        )
        self.input_entry.grid(row=0, column=1, sticky="ew", ipady=8, padx=4)
        self.input_entry.bind("<Return>", lambda e: self._send_message())
        self.input_entry.focus()

        # Attach file button
        btn_attach = tk.Button(bar, text="📎", font=("Helvetica", 14),
                                bg=C["panel"], fg=C["text"],
                                activebackground=C["panel"],
                                relief="flat", cursor="hand2",
                                command=self._attach_file)
        btn_attach.grid(row=0, column=2, padx=4)
        Tooltip(btn_attach, "Send image/file")

        # Send button
        btn_send = tk.Button(
            bar, text="Send  ➤",
            font=("Helvetica", 11, "bold"),
            bg=C["accent"], fg="#fff",
            activebackground="#388bde", activeforeground="#fff",
            relief="flat", cursor="hand2",
            command=self._send_message,
        )
        btn_send.grid(row=0, column=3, padx=(4, 14), ipady=6, ipadx=10)

    # ──────────────────────────────────────────────────────────
    #  ROOM MANAGEMENT
    # ──────────────────────────────────────────────────────────
    def _ensure_room_tab(self, room_name: str) -> None:
        """Create a message frame for a room if it doesn't exist yet."""
        if room_name in self.rooms:
            return

        # Message text area
        frame = tk.Frame(self.msg_container, bg=C["bg"])

        txt = scrolledtext.ScrolledText(
            frame,
            font=("Helvetica", 11),
            bg=C["bg"], fg=C["text"],
            relief="flat", bd=0,
            state="disabled",
            wrap="word",
            spacing1=2, spacing3=6,
            padx=16, pady=12,
        )
        txt.pack(fill="both", expand=True)

        # Configure text tags for bubble styling
        txt.tag_configure("own",   background=C["own_bubble"],   foreground=C["text"],
                          lmargin1=120, lmargin2=120, rmargin=20, spacing1=4, spacing3=4)
        txt.tag_configure("other", background=C["other_bubble"], foreground=C["text"],
                          lmargin1=20,  lmargin2=20,  rmargin=120, spacing1=4, spacing3=4)
        txt.tag_configure("sender_own",   foreground=C["accent"],  font=("Helvetica", 9, "bold"),
                          lmargin1=120, lmargin2=120, justify="right")
        txt.tag_configure("sender_other", foreground=C["accent2"], font=("Helvetica", 9, "bold"),
                          lmargin1=20,  lmargin2=20)
        txt.tag_configure("time",  foreground=C["subtext"], font=("Helvetica", 8))
        txt.tag_configure("notify", foreground=C["subtext"], font=("Helvetica", 9, "italic"),
                          justify="center", spacing1=6, spacing3=6)
        txt.tag_configure("dm",    foreground=C["accent_dm"],  font=("Helvetica", 10, "italic"),
                          lmargin1=20, rmargin=20)
        txt.tag_configure("error", foreground=C["notify"])

        self.rooms[room_name] = {"frame": frame, "text": txt, "unread": 0}

    def _switch_room(self, room_name: str) -> None:
        """Show the frame for room_name, hide all others."""
        self._ensure_room_tab(room_name)

        # Hide all room frames
        for r, data in self.rooms.items():
            data["frame"].grid_forget()

        # Show selected
        self.rooms[room_name]["frame"].grid(row=0, column=0, sticky="nsew")
        self.rooms[room_name]["unread"] = 0
        self.current_room = room_name
        self.lbl_room.configure(text=f"# {room_name}")

        # Refresh sidebar button colours
        self._refresh_room_buttons()

        # Request user list for this room
        send_msg(self.sock, {"type": "LIST_USERS", "room": room_name})

    def _refresh_room_buttons(self):
        for w in self.room_list_frame.winfo_children():
            w.destroy()

        for room_name, data in sorted(self.rooms.items()):
            active  = (room_name == self.current_room)
            unread  = data.get("unread", 0)
            bg      = C["room_active"] if active else C["sidebar"]
            label   = f"  # {room_name}"
            if unread:
                label += f"  🔴{unread}"

            btn = tk.Button(
                self.room_list_frame, text=label,
                font=("Helvetica", 10),
                bg=bg, fg=C["text"],
                activebackground=C["btn_hover"], activeforeground=C["text"],
                relief="flat", anchor="w", cursor="hand2",
                command=lambda r=room_name: self._join_room(r),
            )
            btn.pack(fill="x", padx=6, pady=1, ipady=5)

    def _join_room(self, room_name: str) -> None:
        if room_name == self.current_room:
            return
        send_msg(self.sock, {"type": "JOIN_ROOM", "room": room_name})

    def _open_create_room(self):
        dlg = tk.Toplevel(self)
        dlg.title("Create Room")
        dlg.geometry("320x200")
        dlg.configure(bg=C["bg"])
        dlg.grab_set()

        tk.Label(dlg, text="Create a New Room", font=("Helvetica", 12, "bold"),
                 bg=C["bg"], fg=C["text"]).pack(pady=(20, 10))

        name_var = tk.StringVar()
        tk.Label(dlg, text="Room name (lowercase, no spaces):",
                 bg=C["bg"], fg=C["subtext"], font=("Helvetica", 9)).pack()
        tk.Entry(dlg, textvariable=name_var, font=("Helvetica", 11),
                 bg=C["card"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", bd=6).pack(fill="x", padx=24, pady=6, ipady=6)

        def create():
            name = name_var.get().strip().lower().replace(" ", "-")
            if not name:
                return
            send_msg(self.sock, {"type": "CREATE_ROOM", "room": name})
            dlg.destroy()

        tk.Button(dlg, text="Create Room", font=("Helvetica", 10, "bold"),
                  bg=C["accent"], fg="#fff", relief="flat", cursor="hand2",
                  command=create).pack(pady=12, ipady=6, ipadx=14)

    # ──────────────────────────────────────────────────────────
    #  SENDING
    # ──────────────────────────────────────────────────────────
    def _send_message(self):
        text = self.input_var.get().strip()
        if not text:
            return

        send_msg(self.sock, {
            "type":    "MESSAGE",
            "room":    self.current_room,
            "content": text,
        })
        # Show own message immediately (server only broadcasts to others)
        self._append_message(self.current_room, self.username, text, ts_now(), own=True)
        self.input_var.set("")

    def _attach_file(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                       ("All files", "*.*")],
        )
        if not path:
            return

        filename = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data_b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return

        send_msg(self.sock, {
            "type":     "IMAGE",
            "room":     self.current_room,
            "filename": filename,
            "data":     data_b64,
        })
        self._append_image(self.current_room, self.username, data_b64, filename,
                           ts_now(), own=True)

    # ──────────────────────────────────────────────────────────
    #  EMOJI PICKER
    # ──────────────────────────────────────────────────────────
    def _toggle_emoji_panel(self):
        if self.emoji_panel and self.emoji_panel.winfo_exists():
            self.emoji_panel.destroy()
            self.emoji_panel = None
            return

        panel = tk.Toplevel(self)
        panel.wm_overrideredirect(True)
        panel.configure(bg=C["panel"])
        panel.attributes("-topmost", True)

        # Position near the input bar
        x = self.winfo_rootx() + 220 + 12
        y = self.winfo_rooty() + self.winfo_height() - 220
        panel.geometry(f"300x120+{x}+{y}")

        frame = tk.Frame(panel, bg=C["panel"])
        frame.pack(padx=6, pady=6)

        for i, em in enumerate(EMOJIS):
            btn = tk.Button(
                frame, text=em, font=("Helvetica", 16),
                bg=C["panel"], fg=C["text"],
                activebackground=C["btn_hover"],
                relief="flat", cursor="hand2",
                command=lambda e=em: self._insert_emoji(e, panel),
            )
            btn.grid(row=i // 10, column=i % 10, padx=1, pady=1)

        self.emoji_panel = panel
        panel.bind("<FocusOut>", lambda e: panel.destroy())

    def _insert_emoji(self, emoji: str, panel: tk.Toplevel):
        current = self.input_var.get()
        self.input_var.set(current + emoji)
        self.input_entry.focus()
        panel.destroy()
        self.emoji_panel = None

    # ──────────────────────────────────────────────────────────
    #  MESSAGE DISPLAY
    # ──────────────────────────────────────────────────────────
    def _append_message(self, room: str, sender: str, content: str,
                         timestamp: str, own: bool = False,
                         tag_override: str = "") -> None:
        self._ensure_room_tab(room)
        txt = self.rooms[room]["text"]
        tag = tag_override or ("own" if own else "other")
        sender_tag = "sender_own" if own else "sender_other"

        txt.configure(state="normal")
        txt.insert(tk.END, f"\n")
        if not own:
            txt.insert(tk.END, f"{sender}  {timestamp}\n", sender_tag)
        txt.insert(tk.END, f"  {content}  \n", tag)
        if own:
            txt.insert(tk.END, f"{timestamp}  You\n", sender_tag)
        txt.configure(state="disabled")
        txt.see(tk.END)

        # Badge count if not current room
        if room != self.current_room and not own:
            self.rooms[room]["unread"] = self.rooms[room].get("unread", 0) + 1
            self._refresh_room_buttons()
            self._flash_title(room, sender)

    def _append_image(self, room: str, sender: str, data_b64: str,
                       filename: str, timestamp: str, own: bool = False) -> None:
        self._ensure_room_tab(room)
        txt = self.rooms[room]["text"]
        tag = "own" if own else "other"
        sender_tag = "sender_own" if own else "sender_other"

        txt.configure(state="normal")
        txt.insert(tk.END, "\n")

        if PIL_AVAILABLE:
            try:
                import io
                raw = base64.b64decode(data_b64)
                img = Image.open(io.BytesIO(raw))
                img.thumbnail((240, 200))
                photo = ImageTk.PhotoImage(img)
                # Store reference so it isn't garbage collected
                if not hasattr(txt, "_images"):
                    txt._images = []
                txt._images.append(photo)
                txt.insert(tk.END, f"{sender}  {timestamp}\n", sender_tag)
                txt.image_create(tk.END, image=photo)
                txt.insert(tk.END, "\n")
            except Exception:
                txt.insert(tk.END, f"{sender}  {timestamp}\n", sender_tag)
                txt.insert(tk.END, f"  📎 {filename}  \n", tag)
        else:
            txt.insert(tk.END, f"{sender}  {timestamp}\n", sender_tag)
            txt.insert(tk.END, f"  📎 {filename}  \n", tag)

        txt.configure(state="disabled")
        txt.see(tk.END)

    def _append_notification(self, room: str, text: str) -> None:
        self._ensure_room_tab(room)
        txt = self.rooms[room]["text"]
        txt.configure(state="normal")
        txt.insert(tk.END, f"\n  ─── {text} ───\n", "notify")
        txt.configure(state="disabled")
        txt.see(tk.END)

    def _flash_title(self, room: str, sender: str) -> None:
        """Flash title bar to notify about a new message."""
        original = self.title()
        self.title(f"🔔 {sender} in #{room}")
        self.after(3000, lambda: self.title(original))

    # ──────────────────────────────────────────────────────────
    #  ONLINE USERS SIDEBAR
    # ──────────────────────────────────────────────────────────
    def _update_user_list(self, room: str, users: list[str]) -> None:
        for w in self.user_list_frame.winfo_children():
            w.destroy()

        self.lbl_members.configure(text=f"👥 {len(users)} members")

        for u in sorted(users):
            is_me = (u == self.username)
            row   = tk.Frame(self.user_list_frame, bg=C["sidebar"])
            row.pack(fill="x", padx=6, pady=1)
            dot_color = C["accent2"] if not is_me else C["accent"]
            tk.Label(row, text="●", font=("Helvetica", 8),
                     bg=C["sidebar"], fg=dot_color).pack(side="left", padx=(4, 2))
            lbl = tk.Label(row,
                           text=u + (" (you)" if is_me else ""),
                           font=("Helvetica", 9),
                           bg=C["sidebar"], fg=C["text"], anchor="w",
                           cursor="hand2" if not is_me else "arrow")
            lbl.pack(side="left", fill="x")
            if not is_me:
                lbl.bind("<Button-1>", lambda e, u=u: self._open_dm(u))
                Tooltip(lbl, f"DM {u}")

    # ──────────────────────────────────────────────────────────
    #  DIRECT MESSAGES
    # ──────────────────────────────────────────────────────────
    def _open_dm(self, to_user: str) -> None:
        if to_user in self.dm_windows and self.dm_windows[to_user].winfo_exists():
            self.dm_windows[to_user].lift()
            return
        win = DMWindow(self, to_user)
        self.dm_windows[to_user] = win

    def _receive_dm(self, from_user: str, content: str, timestamp: str) -> None:
        """Route incoming DM to the right window (or open one)."""
        if from_user not in self.dm_windows or not self.dm_windows[from_user].winfo_exists():
            win = DMWindow(self, from_user)
            self.dm_windows[from_user] = win
        self.dm_windows[from_user].receive(from_user, content, timestamp)
        self._flash_title("DM", from_user)

    # ──────────────────────────────────────────────────────────
    #  RECEIVE THREAD
    # ──────────────────────────────────────────────────────────
    def _start_receive_thread(self):
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        while not self.stop_event.is_set():
            msg = recv_msg(self.sock)
            if msg is None:
                if not self.stop_event.is_set():
                    self.after(0, lambda: messagebox.showerror(
                        "Disconnected", "Connection to server lost."))
                break
            # Route to main thread via after()
            self.after(0, self._handle_server_msg, msg)

    def _handle_server_msg(self, msg: dict) -> None:
        mtype = msg.get("type", "")

        if mtype == "MESSAGE":
            room    = msg["room"]
            sender  = msg["sender"]
            content = msg["content"]
            ts      = msg.get("timestamp", ts_now())
            self._ensure_room_tab(room)
            self._append_message(room, sender, content, ts, own=False)

        elif mtype == "IMAGE":
            room   = msg["room"]
            sender = msg["sender"]
            data   = msg.get("data", "")
            fname  = msg.get("filename", "image")
            ts     = msg.get("timestamp", ts_now())
            self._ensure_room_tab(room)
            self._append_image(room, sender, data, fname, ts, own=False)

        elif mtype == "NOTIFICATION":
            room = msg.get("room", self.current_room)
            self._append_notification(room, msg.get("message", ""))
            # Refresh user list after join/leave
            send_msg(self.sock, {"type": "LIST_USERS", "room": self.current_room})

        elif mtype == "ROOM_LIST":
            for r in msg.get("rooms", []):
                self._ensure_room_tab(r["name"])
            self._refresh_room_buttons()

        elif mtype == "JOIN_SUCCESS":
            room    = msg["room"]
            history = msg.get("history", [])
            users   = msg.get("users", [])
            self._ensure_room_tab(room)
            self._switch_room(room)

            # Load history
            txt = self.rooms[room]["text"]
            txt.configure(state="normal")
            txt.delete("1.0", tk.END)
            txt.configure(state="disabled")

            if history:
                self._append_notification(room, f"── Last {len(history)} messages ──")
                for h in history:
                    own = (h["sender"] == self.username)
                    if h.get("msg_type") == "image":
                        self._append_message(room, h["sender"],
                                              f"📎 {h['content']}",
                                              h["timestamp"], own=own)
                    else:
                        self._append_message(room, h["sender"],
                                              h["content"], h["timestamp"], own=own)
                self._append_notification(room, "── Live ──")

            self._update_user_list(room, users)

        elif mtype == "USER_LIST":
            self._update_user_list(msg["room"], msg.get("users", []))

        elif mtype == "PRIVATE":
            self._receive_dm(msg["from"], msg["content"],
                              msg.get("timestamp", ts_now()))

        elif mtype == "PRIVATE_ACK":
            to      = msg["to"]
            content = msg["content"]
            if to in self.dm_windows and self.dm_windows[to].winfo_exists():
                self.dm_windows[to].receive(self.username, content, ts_now(), own=True)

        elif mtype == "ONLINE_COUNT":
            self.lbl_online.configure(text=f"● {msg['count']} online")

        elif mtype == "ROOM_CREATED":
            room_name = msg.get("message", "").split("#")[-1].split(" ")[0]
            send_msg(self.sock, {"type": "LIST_ROOMS"})

        elif mtype == "ERROR":
            self._append_notification(
                self.current_room, f"⚠️ {msg.get('message','')}")

    # ──────────────────────────────────────────────────────────
    #  CLEANUP
    # ──────────────────────────────────────────────────────────
    def _on_close(self):
        self.stop_event.set()
        try:
            self.sock.close()
        except OSError:
            pass
        self.destroy()


# ══════════════════════════════════════════════════════════════
#  DIRECT MESSAGE WINDOW
# ══════════════════════════════════════════════════════════════
class DMWindow(tk.Toplevel):
    """A small floating window for a private conversation."""

    def __init__(self, parent: ChatWindow, to_user: str):
        super().__init__(parent)
        self.parent   = parent
        self.to_user  = to_user
        self.title(f"💬 DM — {to_user}")
        self.geometry("420x380")
        self.configure(bg=C["bg"])
        self._build()

    def _build(self):
        tk.Label(self, text=f"🔒 Private chat with {self.to_user}",
                 font=("Helvetica", 10, "bold"),
                 bg=C["bg"], fg=C["accent_dm"]).pack(pady=(12, 0))

        self.txt = scrolledtext.ScrolledText(
            self, font=("Helvetica", 10),
            bg=C["panel"], fg=C["text"],
            relief="flat", bd=0, state="disabled",
            wrap="word", padx=10, pady=8,
        )
        self.txt.pack(fill="both", expand=True, padx=8, pady=8)
        self.txt.tag_configure("own",   foreground=C["accent"],     font=("Helvetica", 10, "bold"))
        self.txt.tag_configure("other", foreground=C["accent_dm"],  font=("Helvetica", 10, "bold"))
        self.txt.tag_configure("body",  foreground=C["text"])

        bar = tk.Frame(self, bg=C["panel"], pady=6)
        bar.pack(fill="x")
        bar.columnconfigure(0, weight=1)

        self.dm_var = tk.StringVar()
        e = tk.Entry(bar, textvariable=self.dm_var, font=("Helvetica", 10),
                     bg=C["input_bg"], fg=C["text"], insertbackground=C["text"],
                     relief="flat", bd=6)
        e.grid(row=0, column=0, sticky="ew", padx=(8, 4), ipady=7)
        e.bind("<Return>", lambda ev: self._send())

        tk.Button(bar, text="Send", font=("Helvetica", 10, "bold"),
                  bg=C["accent_dm"], fg="#fff",
                  relief="flat", cursor="hand2",
                  command=self._send).grid(row=0, column=1, padx=(0, 8), ipady=5, ipadx=8)

    def _send(self):
        text = self.dm_var.get().strip()
        if not text:
            return
        send_msg(self.parent.sock, {
            "type":    "PRIVATE",
            "to":      self.to_user,
            "content": text,
        })
        self.dm_var.set("")

    def receive(self, sender: str, content: str, timestamp: str, own: bool = False):
        tag = "own" if own else "other"
        self.txt.configure(state="normal")
        self.txt.insert(tk.END, f"{sender}  {timestamp}\n", tag)
        self.txt.insert(tk.END, f"{content}\n\n", "body")
        self.txt.configure(state="disabled")
        self.txt.see(tk.END)
        if not own:
            self.lift()


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="PyChat Advanced GUI")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    # ── Login screen ──────────────────────────────────────────
    login = LoginWindow(args.host, args.port)
    login.mainloop()

    if login.result is None:
        return  # user closed the window

    sock     = login.result["sock"]
    username = login.result["username"]

    # ── Main chat window ──────────────────────────────────────
    app = ChatWindow(sock, username)
    app.mainloop()


if __name__ == "__main__":
    main()
