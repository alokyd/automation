import tkinter as tk
from tkinter import ttk
import threading
import botx


class BotGUI:
    def __init__(self, root):
        self.root = root
        root.title("⚡ Trading Bot Dashboard")
        root.geometry("500x720")
        root.resizable(False, False)

        # ===================== THEME =====================
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#0f172a")
        style.configure("Card.TFrame", background="#020617", relief="ridge")
        style.configure("TLabel", background="#020617", foreground="#e5e7eb")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Value.TLabel", font=("Segoe UI", 11, "bold"))

        # ===================== RUNTIME CONFIG =====================
        self.base_amount = tk.IntVar(value=20)
        self.max_recovery = tk.IntVar(value=5)
        self.wins_reset = tk.IntVar(value=8)

        # ✅ TRADE MODE (REPLACES CHECKBOX)
        self.trade_mode = tk.StringVar(value="LIVE")  # LIVE / READ_ONLY

        # ===================== LIVE VALUES =====================
        self.timer = tk.StringVar(value="-")
        self.current_base_amount = tk.StringVar(value=f"₹ {self.base_amount.get()}")
        self.result = tk.StringVar(value="-")
        self.history = tk.StringVar(value="-")
        self.pattern_id = tk.StringVar(value="-")
        self.trade_amount = tk.StringVar(value="-")
        self.status = tk.StringVar(value="STOPPED")

        # ===================== MAIN CONTENT =====================
        main = ttk.Frame(root)
        main.pack(fill="both", padx=12, pady=12)

        # ===================== HEADER =====================
        header = ttk.Frame(main, style="Card.TFrame")
        header.pack(fill="x", pady=8)

        ttk.Label(
            header,
            text="🚀 Automated Trading Bot",
            style="Title.TLabel"
        ).pack(pady=14)

        # ===================== CONFIG CARD =====================
        self.card(main, "⚙ Bot Configuration", [
            ("Base Amount", self.base_amount),
            ("Max Recovery", self.max_recovery),
            ("Wins To Reset", self.wins_reset),
        ])

        # ===================== TRADE MODE CARD (FIXED UI) =====================
        mode_card = ttk.Frame(main, style="Card.TFrame")
        mode_card.pack(fill="x", pady=8)

        ttk.Label(
            mode_card,
            text="🧭 Trade Mode",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=12, pady=8)

        modes = ttk.Frame(mode_card)
        modes.pack(anchor="w", padx=12, pady=6)

        ttk.Radiobutton(
            modes,
            text="Live Trading",
            variable=self.trade_mode,
            value="LIVE"
        ).pack(side="left", padx=10)

        ttk.Radiobutton(
            modes,
            text="Read Only (No Trade)",
            variable=self.trade_mode,
            value="READ_ONLY"
        ).pack(side="left", padx=10)

        # ===================== LIVE STATUS CARD =====================
        status_card = ttk.Frame(main, style="Card.TFrame")
        status_card.pack(fill="x", pady=8)

        ttk.Label(
            status_card,
            text="📊 Live Status",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=12, pady=8)

        self.status_row(status_card, "⏱ Timer", self.timer)
        self.status_row(status_card, "💼 Current Base Amount", self.current_base_amount)
        self.status_row(status_card, "📥 Result", self.result)
        self.status_row(status_card, "📚 History", self.history)
        self.status_row(status_card, "🎯 Pattern ID", self.pattern_id)
        self.status_row(status_card, "💰 Trade Amount", self.trade_amount)
        self.status_row(status_card, "📊 Status", self.status)

        # ===================== CONTROL BAR =====================
        control = tk.Frame(root, bg="#020617")
        control.pack(fill="x", pady=10)

        tk.Button(
            control,
            text="▶ START BOT",
            command=self.start_bot,
            bg="#000000",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=20,
            pady=10
        ).pack(side="left", expand=True, padx=15)

        tk.Button(
            control,
            text="⏹ STOP BOT",
            command=self.stop_bot,
            bg="#000000",
            fg="white",
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            padx=20,
            pady=10
        ).pack(side="right", expand=True, padx=15)

    # ===================== HELPERS =====================

    def card(self, parent, title, fields):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="x", pady=8)

        ttk.Label(card, text=title, font=("Segoe UI", 12, "bold")).pack(
            anchor="w", padx=12, pady=8
        )

        for label, var in fields:
            row = ttk.Frame(card)
            row.pack(fill="x", padx=12, pady=6)
            ttk.Label(row, text=label, width=20).pack(side="left")
            ttk.Entry(row, textvariable=var, width=12).pack(side="right")

    def status_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=12, pady=4)
        ttk.Label(row, text=label, width=20).pack(side="left")
        ttk.Label(row, textvariable=var, style="Value.TLabel").pack(side="right")

    # ===================== BOT CONTROL =====================

    def start_bot(self):
        self.status.set("RUNNING")

        read_only_flag = (self.trade_mode.get() == "READ_ONLY")

        botx.set_runtime_config(
            self.base_amount.get(),
            self.max_recovery.get(),
            self.wins_reset.get(),
            self.update_gui,
            read_only_flag
        )

        threading.Thread(target=botx.run_bot, daemon=True).start()

    def stop_bot(self):
        botx.stop_bot()
        self.status.set("STOPPED")

    # ===================== GUI CALLBACK =====================

    def update_gui(self, data):
        if "timer" in data:
            self.timer.set(data["timer"])
        if "current_base_amount" in data:
            self.current_base_amount.set(f"₹ {data['current_base_amount']}")
        if "result" in data:
            self.result.set(data["result"])
        if "history" in data:
            self.history.set(str(data["history"]))
        if "pattern_id" in data and data["pattern_id"]:
            self.pattern_id.set(data["pattern_id"])
        if "trade_amount" in data:
            self.trade_amount.set(f"₹ {data['trade_amount']}")
        if "status" in data:
            self.status.set(data["status"])


def start_gui():
    root = tk.Tk()
    BotGUI(root)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
