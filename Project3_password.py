"""
╔══════════════════════════════════════════════════════╗
║         ADVANCED PASSWORD GENERATOR                  ║
║         GUI-based with Tkinter | No pyperclip        ║
╚══════════════════════════════════════════════════════╝

Features:
  - GUI using Tkinter (dark cyberpunk theme)
  - Uppercase, Lowercase, Digits, Symbols character sets
  - Exclude specific/ambiguous characters
  - Password strength meter (live)
  - Security rules enforcement
  - Multi-password batch generation
  - Clipboard integration (via tkinter built-in)
  - Password history log
  - Copy individual or all passwords
"""

import tkinter as tk
from tkinter import ttk, messagebox, font
import random
import string
import re
import time


# ─────────────────────────────────────────────────────────
#  CORE PASSWORD LOGIC
# ─────────────────────────────────────────────────────────

SYMBOL_SET = "!@#$%^&*()-_=+[]{}|;:,.<>?/"

def build_charset(use_upper, use_lower, use_digits, use_symbols,
                  exclude_chars="", exclude_ambiguous=False):
    """Assemble character pool based on user selections."""
    pool = ""
    if use_upper:   pool += string.ascii_uppercase
    if use_lower:   pool += string.ascii_lowercase
    if use_digits:  pool += string.digits
    if use_symbols: pool += SYMBOL_SET

    if exclude_ambiguous:
        ambiguous = "Il1O0oB8S5Z2"
        pool = "".join(c for c in pool if c not in ambiguous)

    if exclude_chars:
        pool = "".join(c for c in pool if c not in exclude_chars)

    return pool


def enforce_security_rules(password, use_upper, use_lower,
                            use_digits, use_symbols):
    """
    Guarantee at least one character from every selected category
    by replacing random positions — preserves exact length.
    """
    pwd = list(password)
    mandatory = []
    if use_upper   and not any(c.isupper()       for c in pwd):
        mandatory.append(random.choice(string.ascii_uppercase))
    if use_lower   and not any(c.islower()        for c in pwd):
        mandatory.append(random.choice(string.ascii_lowercase))
    if use_digits  and not any(c.isdigit()        for c in pwd):
        mandatory.append(random.choice(string.digits))
    if use_symbols and not any(c in SYMBOL_SET    for c in pwd):
        mandatory.append(random.choice(SYMBOL_SET))

    for ch in mandatory:
        idx = random.randrange(len(pwd))
        pwd[idx] = ch

    random.shuffle(pwd)
    return "".join(pwd)


def generate_password(length, use_upper, use_lower, use_digits,
                      use_symbols, exclude_chars="",
                      exclude_ambiguous=False, enforce_rules=True):
    """Generate a single password."""
    pool = build_charset(use_upper, use_lower, use_digits, use_symbols,
                         exclude_chars, exclude_ambiguous)
    if not pool:
        return None, "⚠ No characters available — enable at least one set."
    if length < 4 and enforce_rules:
        return None, "⚠ Minimum length is 4 when security rules are on."

    password = "".join(random.choices(pool, k=length))

    if enforce_rules:
        password = enforce_security_rules(password, use_upper, use_lower,
                                          use_digits, use_symbols)
    return password, None


def score_password(password):
    """
    Returns (score 0-100, label, colour).
    Checks length, character variety, entropy patterns.
    """
    if not password:
        return 0, "—", "#555566"

    score = 0
    length = len(password)

    # Length bonus
    if length >= 8:  score += 10
    if length >= 12: score += 15
    if length >= 16: score += 15
    if length >= 20: score += 10

    # Character variety
    if re.search(r"[A-Z]", password): score += 10
    if re.search(r"[a-z]", password): score += 10
    if re.search(r"\d",    password): score += 10
    if re.search(r"[^A-Za-z0-9]", password): score += 15

    # Uniqueness ratio
    unique_ratio = len(set(password)) / length
    score += int(unique_ratio * 5)

    score = min(score, 100)

    if score < 30:   return score, "VERY WEAK",  "#ff4455"
    if score < 50:   return score, "WEAK",       "#ff8844"
    if score < 70:   return score, "FAIR",       "#ffcc00"
    if score < 85:   return score, "STRONG",     "#88dd44"
    return score,                  "VERY STRONG","#44ffaa"


# ─────────────────────────────────────────────────────────
#  GUI APPLICATION
# ─────────────────────────────────────────────────────────

BG        = "#0d0d1a"
PANEL     = "#13132a"
ACCENT    = "#00e5ff"
ACCENT2   = "#ff00cc"
TEXT      = "#e0e0ff"
MUTED     = "#6666aa"
SUCCESS   = "#44ffaa"
WARNING   = "#ffcc00"
DANGER    = "#ff4455"
ENTRY_BG  = "#1a1a35"
BORDER    = "#2a2a55"


class PasswordGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ CipherForge — Password Generator")
        self.configure(bg=BG)
        self.resizable(False, False)

        self._history = []        # list of generated passwords
        self._setup_vars()
        self._build_ui()
        self._update_strength()   # initialise meter

    # ── Variables ──────────────────────────────────────
    def _setup_vars(self):
        self.var_length      = tk.IntVar(value=16)
        self.var_upper       = tk.BooleanVar(value=True)
        self.var_lower       = tk.BooleanVar(value=True)
        self.var_digits      = tk.BooleanVar(value=True)
        self.var_symbols     = tk.BooleanVar(value=True)
        self.var_ambiguous   = tk.BooleanVar(value=False)
        self.var_rules       = tk.BooleanVar(value=True)
        self.var_count       = tk.IntVar(value=1)
        self.var_exclude     = tk.StringVar(value="")

    # ── Master Layout ───────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=24, pady=(20, 4))

        tk.Label(hdr, text="⚡ CIPHER", font=("Courier New", 22, "bold"),
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Label(hdr, text="FORGE", font=("Courier New", 22, "bold"),
                 fg=ACCENT2, bg=BG).pack(side="left")
        tk.Label(hdr, text=" — Advanced Password Generator",
                 font=("Courier New", 10), fg=MUTED, bg=BG).pack(side="left", pady=(6,0))

        sep = tk.Frame(self, bg=ACCENT, height=1)
        sep.pack(fill="x", padx=24, pady=(4,16))

        # ── Two-column body ──
        body = tk.Frame(self, bg=BG)
        body.pack(padx=24, pady=0)

        left  = tk.Frame(body, bg=BG)
        left.grid(row=0, column=0, sticky="n", padx=(0,16))

        right = tk.Frame(body, bg=BG)
        right.grid(row=0, column=1, sticky="n")

        self._build_controls(left)
        self._build_output(right)

        # ── History ──
        self._build_history()

        # ── Status bar ──
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(self, textvariable=self.status_var, font=("Courier New", 8),
                 fg=MUTED, bg=BG).pack(pady=(2,8))

    # ── Left panel: controls ─────────────────────────────
    def _build_controls(self, parent):
        self._section(parent, "PASSWORD LENGTH")
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0,10))

        self.len_scale = tk.Scale(
            row, from_=4, to=64, orient="horizontal",
            variable=self.var_length, command=self._on_length_change,
            bg=PANEL, fg=ACCENT, troughcolor=BORDER,
            highlightthickness=0, relief="flat",
            activebackground=ACCENT, length=220, sliderrelief="flat"
        )
        self.len_scale.pack(side="left")

        self.len_label = tk.Label(row, text="16", width=3,
                                  font=("Courier New", 14, "bold"),
                                  fg=ACCENT2, bg=BG)
        self.len_label.pack(side="left", padx=8)

        # ── Character Sets ──
        self._section(parent, "CHARACTER SETS")
        sets = [
            ("Uppercase  A–Z", self.var_upper),
            ("Lowercase  a–z", self.var_lower),
            ("Digits     0–9", self.var_digits),
            ("Symbols    !@#…", self.var_symbols),
        ]
        for label, var in sets:
            self._checkbox(parent, label, var)

        # ── Exclusions ──
        self._section(parent, "EXCLUSIONS")
        self._checkbox(parent, "Exclude ambiguous chars  (I l 1 O 0 …)", self.var_ambiguous)

        excl_row = tk.Frame(parent, bg=BG)
        excl_row.pack(fill="x", pady=(6,0))
        tk.Label(excl_row, text="Exclude specific chars:",
                 font=("Courier New", 9), fg=TEXT, bg=BG).pack(side="left")
        tk.Entry(excl_row, textvariable=self.var_exclude, width=14,
                 font=("Courier New", 10), bg=ENTRY_BG, fg=ACCENT2,
                 insertbackground=ACCENT2, relief="flat",
                 highlightbackground=BORDER, highlightthickness=1
                 ).pack(side="left", padx=(8,0))

        # ── Rules & Count ──
        self._section(parent, "OPTIONS")
        self._checkbox(parent, "Enforce security rules (min 1 of each set)", self.var_rules)

        cnt_row = tk.Frame(parent, bg=BG)
        cnt_row.pack(fill="x", pady=(8,0))
        tk.Label(cnt_row, text="Generate how many?",
                 font=("Courier New", 9), fg=TEXT, bg=BG).pack(side="left")
        tk.Spinbox(cnt_row, from_=1, to=20, textvariable=self.var_count,
                   width=4, font=("Courier New", 10),
                   bg=ENTRY_BG, fg=ACCENT, buttonbackground=PANEL,
                   relief="flat", highlightbackground=BORDER,
                   highlightthickness=1).pack(side="left", padx=8)

        # ── Generate button ──
        tk.Button(parent, text="⚡  GENERATE PASSWORD",
                  font=("Courier New", 11, "bold"),
                  fg=BG, bg=ACCENT, activebackground=ACCENT2,
                  activeforeground=BG, relief="flat",
                  cursor="hand2", padx=12, pady=8,
                  command=self._generate
                  ).pack(fill="x", pady=(18, 4))

    # ── Right panel: output ──────────────────────────────
    def _build_output(self, parent):
        self._section(parent, "GENERATED PASSWORD")

        # main password display
        pwd_frame = tk.Frame(parent, bg=PANEL,
                             highlightbackground=ACCENT,
                             highlightthickness=1)
        pwd_frame.pack(fill="x", pady=(0, 8))

        self.pwd_var = tk.StringVar(value="")
        pwd_entry = tk.Entry(pwd_frame, textvariable=self.pwd_var,
                             font=("Courier New", 14, "bold"),
                             fg=SUCCESS, bg=PANEL, relief="flat",
                             insertbackground=SUCCESS, width=28,
                             readonlybackground=PANEL, state="readonly")
        pwd_entry.pack(padx=10, pady=10)

        # copy button
        tk.Button(parent, text="⎘  COPY TO CLIPBOARD",
                  font=("Courier New", 10, "bold"),
                  fg=BG, bg=SUCCESS, activebackground=WARNING,
                  relief="flat", cursor="hand2", padx=8, pady=6,
                  command=self._copy_main
                  ).pack(fill="x", pady=(0, 14))

        # ── Strength Meter ──
        self._section(parent, "STRENGTH METER")
        meter_bg = tk.Frame(parent, bg=BORDER, height=12)
        meter_bg.pack(fill="x", pady=(0, 4))
        meter_bg.pack_propagate(False)

        self.meter_bar = tk.Frame(meter_bg, bg=DANGER, height=12, width=0)
        self.meter_bar.place(x=0, y=0, height=12)

        info_row = tk.Frame(parent, bg=BG)
        info_row.pack(fill="x")
        self.strength_label = tk.Label(info_row, text="—",
                                       font=("Courier New", 10, "bold"),
                                       fg=MUTED, bg=BG)
        self.strength_label.pack(side="left")
        self.score_label = tk.Label(info_row, text="",
                                    font=("Courier New", 9),
                                    fg=MUTED, bg=BG)
        self.score_label.pack(side="right")

        # ── Batch list ──
        self._section(parent, "BATCH OUTPUT")
        list_frame = tk.Frame(parent, bg=PANEL,
                              highlightbackground=BORDER,
                              highlightthickness=1)
        list_frame.pack(fill="both", pady=(0, 4))

        scrollbar = tk.Scrollbar(list_frame, bg=PANEL,
                                 troughcolor=BG, relief="flat")
        scrollbar.pack(side="right", fill="y")

        self.batch_list = tk.Listbox(list_frame,
                                     font=("Courier New", 10),
                                     fg=ACCENT, bg=PANEL,
                                     selectbackground=BORDER,
                                     selectforeground=ACCENT2,
                                     relief="flat", height=6, width=34,
                                     yscrollcommand=scrollbar.set,
                                     activestyle="none")
        self.batch_list.pack(side="left", fill="both")
        scrollbar.config(command=self.batch_list.yview)

        tk.Button(parent, text="⎘  COPY ALL",
                  font=("Courier New", 9, "bold"),
                  fg=BG, bg=MUTED, activebackground=ACCENT,
                  relief="flat", cursor="hand2", padx=6, pady=4,
                  command=self._copy_all
                  ).pack(fill="x", pady=(0, 2))

    # ── History panel ────────────────────────────────────
    def _build_history(self):
        sep = tk.Frame(self, bg=BORDER, height=1)
        sep.pack(fill="x", padx=24, pady=(8, 0))

        hdr_row = tk.Frame(self, bg=BG)
        hdr_row.pack(fill="x", padx=24, pady=(6, 2))
        tk.Label(hdr_row, text="HISTORY",
                 font=("Courier New", 9, "bold"),
                 fg=MUTED, bg=BG).pack(side="left")
        tk.Button(hdr_row, text="Clear",
                  font=("Courier New", 8),
                  fg=MUTED, bg=BG, relief="flat",
                  cursor="hand2", activeforeground=DANGER,
                  command=self._clear_history
                  ).pack(side="right")

        hist_frame = tk.Frame(self, bg=PANEL,
                              highlightbackground=BORDER,
                              highlightthickness=1)
        hist_frame.pack(fill="x", padx=24, pady=(0, 6))

        h_scroll = tk.Scrollbar(hist_frame, orient="vertical",
                                bg=PANEL, troughcolor=BG, relief="flat")
        h_scroll.pack(side="right", fill="y")

        self.hist_list = tk.Listbox(hist_frame,
                                    font=("Courier New", 9),
                                    fg=MUTED, bg=PANEL,
                                    selectbackground=BORDER,
                                    selectforeground=TEXT,
                                    relief="flat", height=3,
                                    yscrollcommand=h_scroll.set,
                                    activestyle="none")
        self.hist_list.pack(fill="x")
        h_scroll.config(command=self.hist_list.yview)

        self.hist_list.bind("<Double-Button-1>", self._copy_hist_item)
        tk.Label(self, text="↑ double-click history entry to copy",
                 font=("Courier New", 7), fg=MUTED, bg=BG
                 ).pack(pady=(0, 4))

    # ── Helpers ──────────────────────────────────────────
    def _section(self, parent, title):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(12, 4))
        tk.Label(row, text=title, font=("Courier New", 8, "bold"),
                 fg=MUTED, bg=BG).pack(side="left")
        tk.Frame(row, bg=BORDER, height=1).pack(side="left",
                                                fill="x", expand=True,
                                                padx=(6, 0), pady=(4, 0))

    def _checkbox(self, parent, label, var):
        cb = tk.Checkbutton(parent, text=label, variable=var,
                            font=("Courier New", 9),
                            fg=TEXT, bg=BG, activeforeground=ACCENT,
                            activebackground=BG,
                            selectcolor=PANEL,
                            relief="flat", cursor="hand2",
                            command=self._update_strength)
        cb.pack(anchor="w", pady=1)

    def _flash_status(self, msg, colour=SUCCESS):
        self.status_var.set(msg)
        self.after(3000, lambda: self.status_var.set("Ready."))

    # ── Event Handlers ───────────────────────────────────
    def _on_length_change(self, val):
        self.len_label.config(text=str(int(float(val))))
        self._update_strength()

    def _update_strength(self, *_):
        """Recompute strength for the currently shown password."""
        pwd = self.pwd_var.get()
        score, label, colour = score_password(pwd)
        self.strength_label.config(text=label, fg=colour)
        self.score_label.config(text=f"{score}/100")

        # resize bar — total width of meter_bar's parent
        self.update_idletasks()
        total_w = self.meter_bar.master.winfo_width() or 260
        bar_w   = int(total_w * score / 100)
        self.meter_bar.config(bg=colour, width=max(bar_w, 1))
        self.meter_bar.place(x=0, y=0, width=max(bar_w, 1), height=12)

    def _generate(self):
        count = self.var_count.get()
        length = self.var_length.get()
        passwords = []

        for _ in range(count):
            pwd, err = generate_password(
                length        = length,
                use_upper     = self.var_upper.get(),
                use_lower     = self.var_lower.get(),
                use_digits    = self.var_digits.get(),
                use_symbols   = self.var_symbols.get(),
                exclude_chars = self.var_exclude.get(),
                exclude_ambiguous = self.var_ambiguous.get(),
                enforce_rules = self.var_rules.get(),
            )
            if err:
                messagebox.showwarning("Generation Error", err)
                return
            passwords.append(pwd)

        # update main display with first password
        self.pwd_var.set(passwords[0])
        self._update_strength()

        # update batch list
        self.batch_list.delete(0, "end")
        for p in passwords:
            self.batch_list.insert("end", p)

        # add to history (most recent first)
        ts = time.strftime("%H:%M:%S")
        for p in passwords:
            entry = f"[{ts}]  {p}"
            self._history.insert(0, entry)

        self.hist_list.delete(0, "end")
        for h in self._history[:30]:
            self.hist_list.insert("end", h)

        self._flash_status(f"✓ Generated {count} password(s).")

    def _copy_main(self):
        pwd = self.pwd_var.get()
        if not pwd:
            self._flash_status("⚠ Nothing to copy.", WARNING)
            return
        self._clipboard_write(pwd)
        self._flash_status("✓ Password copied to clipboard!")

    def _copy_all(self):
        items = self.batch_list.get(0, "end")
        if not items:
            self._flash_status("⚠ Nothing to copy.", WARNING)
            return
        self._clipboard_write("\n".join(items))
        self._flash_status(f"✓ {len(items)} password(s) copied to clipboard!")

    def _copy_hist_item(self, event):
        sel = self.hist_list.curselection()
        if sel:
            raw = self.hist_list.get(sel[0])
            # strip timestamp prefix  "[HH:MM:SS]  "
            pwd = raw.split("]  ", 1)[-1].strip()
            self._clipboard_write(pwd)
            self._flash_status("✓ History entry copied!")

    def _clear_history(self):
        self._history.clear()
        self.hist_list.delete(0, "end")
        self._flash_status("History cleared.")

    def _clipboard_write(self, text):
        """Copy text to clipboard using Tkinter's built-in mechanism."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()    # keeps clipboard alive even after app closes (Windows)


# ─────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = PasswordGeneratorApp()
    app.mainloop()
