from playwright.sync_api import sync_playwright
import time
import sqlite3
import winsound
from datetime import datetime, timezone

# ===================== RUNTIME FLAGS =====================
RUNNING = False
GUI_CALLBACK = None

# ===================== CONFIG =====================

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
URL = "https://tgdream.pro/#/saasLottery/WinGo?gameCode=WinGo_30S&lottery=WinGo"

USER_DATA_DIR = "brave_profile"

BASE_AMOUNT = 20
SCAN_INTERVAL = 30
DB_FILE = "bot_data.db"

# recovery rules
MAX_RECOVERY_LEVEL = 5
WINS_TO_RESET = 8

# ===================== GUI CONTROL =====================

def set_runtime_config(base_amount, max_recovery, wins_reset, gui_callback=None):
    global BASE_AMOUNT, MAX_RECOVERY_LEVEL, WINS_TO_RESET, GUI_CALLBACK
    BASE_AMOUNT = base_amount
    MAX_RECOVERY_LEVEL = max_recovery
    WINS_TO_RESET = wins_reset
    GUI_CALLBACK = gui_callback

def stop_bot():
    global RUNNING
    RUNNING = False

def gui_update(**data):
    if GUI_CALLBACK:
        GUI_CALLBACK(data)

# ===================== ALERT =====================

def alert_loss():
    for _ in range(2):
        winsound.Beep(1800,120)
        winsound.Beep(2200,180)
        time.sleep(0.05)

# ===================== DATABASE =====================

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    result_num INTEGER,
    result_text TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    round_id TEXT,
    timestamp TEXT,
    target TEXT,
    amount INTEGER,
    attempt_index INTEGER,
    outcome TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    win_streak INTEGER,
    loss_streak INTEGER,
    total_wins INTEGER,
    total_losses INTEGER
)
""")

conn.commit()

# ===================== LOAD LAST STATE =====================

def load_last_stats():
    cur.execute("""
        SELECT win_streak, loss_streak, total_wins, total_losses
        FROM stats
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    return row if row else (0, 0, 0, 0)

# ===================== BET FUNCTION =====================

def place_bet(page, target, attempt_index, current_base_amount):
    amount = current_base_amount * (2 ** attempt_index)

    if target == "Big":
        page.locator(".Betting__C-foot-b").click()
    else:
        page.locator(".Betting__C-foot-s").click()

    time.sleep(1)
    page.locator(".m input[type='number']").fill(str(amount))
    time.sleep(1)
    page.locator("button.bet-amount").click()

    print(f"✅ Bet placed: {target} ₹{amount}")

    gui_update(trade_amount=amount)

    return amount

# ===================== MAIN BOT =====================

def run_bot():
    global RUNNING
    RUNNING = True

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            executable_path=BRAVE_PATH,
            headless=False
        )

        page = context.pages[0] if context.pages else context.new_page()
        if page.url != URL:
            page.goto(URL)

        page.wait_for_selector(".record-body .van-row", timeout=0)
        print("🤖 Bot started\n")

        history = []
        pattern_active = False
        cooldown_active = False

        target_value = None
        attempts_left = 0
        attempt_index = 0
        round_id = None
        last_seen = None

        win_streak, loss_streak, total_wins, total_losses = load_last_stats()

        current_base_amount = BASE_AMOUNT
        recovery_level = 0
        wins_since_last_loss = 0

        next_tick = time.time()

        while RUNNING:
            if time.time() < next_tick:
                time.sleep(next_tick - time.time())
            next_tick += SCAN_INTERVAL

            ts = datetime.now(timezone.utc).isoformat()
            timer_text = time.strftime("%H:%M:%S")

            row = page.locator(".record-body .van-row").first
            num = int(row.locator(".numcenter").inner_text())
            value = "Big" if num >= 5 else "Small"

            print("⏱", timer_text)
            print(f"📥 {num} → {value}")

            cur.execute(
                "INSERT INTO results VALUES (NULL,?,?,?)",
                (ts, num, value)
            )
            conn.commit()

            if cooldown_active:
                if value == last_seen:
                    history.append(last_seen)
                    cooldown_active = False
                else:
                    last_seen = value
                    continue

            last_seen = value
            history.append(value)
            history[:] = history[-4:]

            print("📚", history)

            gui_update(
                timer=timer_text,
                result=f"{num} → {value}",
                history=list(history),
                pattern_id=round_id,
                status="RUNNING"
            )

            if not pattern_active and history in (
                ["Big","Small","Big","Small"],
                ["Small","Big","Small","Big"]
            ):
                alert_loss()
                pattern_active = True
                target_value = history[-1]
                attempts_left = 4
                attempt_index = 0
                round_id = f"R{int(time.time())}"

                print(f"🎯 Pattern detected → {round_id}")

                gui_update(
                    pattern_id=round_id,
                    status="PATTERN DETECTED"
                )

                amount = place_bet(page, target_value, attempt_index, current_base_amount)

                cur.execute(
                    "INSERT INTO bets VALUES (NULL,?,?,?,?,?,NULL)",
                    (round_id, ts, target_value, amount, attempt_index)
                )
                conn.commit()
                continue

            if pattern_active:
                if value == target_value:
                    print("🏆 WIN")

                    cur.execute("""
                        UPDATE bets SET outcome='Win'
                        WHERE round_id=? AND attempt_index=?
                    """, (round_id, attempt_index))

                    win_streak += 1
                    loss_streak = 0
                    total_wins += 1
                    wins_since_last_loss += 1

                    gui_update(status="WIN")

                    if wins_since_last_loss >= WINS_TO_RESET:
                        recovery_level = 0
                        current_base_amount = BASE_AMOUNT
                        wins_since_last_loss = 0

                    pattern_active = False

                else:
                    cur.execute("""
                        UPDATE bets SET outcome='Lose'
                        WHERE round_id=? AND attempt_index=?
                    """, (round_id, attempt_index))

                    attempts_left -= 1
                    attempt_index += 1
                    target_value = value

                    if attempts_left > 0:
                        amount = place_bet(page, target_value, attempt_index, current_base_amount)
                        cur.execute(
                            "INSERT INTO bets VALUES (NULL,?,?,?,?,?,NULL)",
                            (round_id, ts, target_value, amount, attempt_index)
                        )
                    else:
                        print("❌ FINAL LOSE")

                        gui_update(status="LOSE")

                        history.clear()
                        win_streak = 0
                        loss_streak += 1
                        total_losses += 1
                        wins_since_last_loss = 0

                        if recovery_level < MAX_RECOVERY_LEVEL:
                            recovery_level += 1
                            current_base_amount = BASE_AMOUNT * (2 ** recovery_level)
                            gui_update(current_base_amount=current_base_amount)

                        pattern_active = False
                        cooldown_active = True

                cur.execute(
                    "INSERT INTO stats VALUES (NULL,?,?,?,?,?)",
                    (ts, win_streak, loss_streak, total_wins, total_losses)
                )
                conn.commit()

        print("🛑 Bot stopped")
        gui_update(status="STOPPED")
