from playwright.sync_api import sync_playwright
import time
import sqlite3
import winsound
from datetime import datetime

# ===================== CONFIG =====================

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
URL = "https://tgdream.pro/#/saasLottery/WinGo?gameCode=WinGo_30S&lottery=WinGo"

USER_DATA_DIR = "brave_profile"
BASE_AMOUNT = 20
SCAN_INTERVAL = 30

DB_FILE = "bot_data.db"

# ===================== ALERT =====================

def alert_loss():
    tones = [(1800,120),(2200,180)]
    for _ in range(2):
        for f,d in tones:
            winsound.Beep(f,d)
            time.sleep(0.05)

# ===================== DATABASE =====================

conn = sqlite3.connect(DB_FILE)
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
    timestamp TEXT,
    win_streak INTEGER,
    loss_streak INTEGER,
    total_wins INTEGER,
    total_losses INTEGER
)
""")

conn.commit()

# ===================== BET FUNCTION =====================

def place_bet(page, target, attempt_index):
    amount = BASE_AMOUNT * (2 ** attempt_index)

    if target == "Big":
        page.locator(".Betting__C-foot-b").click()
        print("🟦 Clicked BIG")
    else:
        page.locator(".Betting__C-foot-s").click()
        print("🟨 Clicked SMALL")

    time.sleep(1)

    amt = page.locator(".m input[type='number']")
    amt.fill(str(amount))

    time.sleep(1)
    page.locator("button.bet-amount").click()

    print(f"✅ Bet placed: {target} ₹{amount}")
    return amount

# ===================== PLAYWRIGHT =====================

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

    # ===================== STATE =====================

    history = []
    pattern_active = False
    cooldown_active = False

    target_value = None
    attempts_left = 0
    attempt_index = 0
    round_id = None

    last_seen = None

    win_streak = 0
    loss_streak = 0
    total_wins = 0
    total_losses = 0

    # ===================== TIME LOCK =====================

    next_tick = time.time()

    while True:
        if time.time() < next_tick:
            time.sleep(next_tick - time.time())
        next_tick += SCAN_INTERVAL
        print("⏱", time.strftime("%H:%M:%S"))
        ts = datetime.utcnow().isoformat()

        # -------- READ RESULT --------
        row = page.locator(".record-body .van-row").first
        num = int(row.locator(".numcenter").inner_text())
        value = "Big" if num >= 5 else "Small"

        print(f"📥 {num} → {value}")

        # -------- STORE RESULT --------
        cur.execute(
            "INSERT INTO results VALUES (NULL,?,?,?)",
            (ts, num, value)
        )
        conn.commit()

        # -------- COOLDOWN --------
        if cooldown_active:
            if value == last_seen:
                cooldown_active = False
                history.clear()
                print("🔓 Cooldown finished")
            else:
                last_seen = value
                continue

        last_seen = value

        # -------- HISTORY --------
        history.append(value)
        history[:] = history[-4:]
        print("📚", history)

        # -------- PATTERN DETECT --------
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
            amount = place_bet(page, target_value, attempt_index)

            cur.execute(
                "INSERT INTO bets VALUES (NULL,?,?,?,?,?,NULL)",
                (round_id, ts, target_value, amount, attempt_index)
            )
            conn.commit()
            continue

        # -------- CHASE MODE --------
        if pattern_active:
            if value == target_value:
                print("🏆 WIN")
                pattern_active = False

                win_streak += 1
                loss_streak = 0
                total_wins += 1

                cur.execute(
                    "UPDATE bets SET outcome='Win' WHERE round_id=? AND outcome IS NULL",
                    (round_id,)
                )

            else:
                attempts_left -= 1
                attempt_index += 1
                target_value = value

                if attempts_left > 0:
                    amount = place_bet(page, target_value, attempt_index)
                    cur.execute(
                        "INSERT INTO bets VALUES (NULL,?,?,?,?,?,NULL)",
                        (round_id, ts, target_value, amount, attempt_index)
                    )
                else:
                    print("❌ LOSE")
                    alert_loss()

                    pattern_active = False
                    cooldown_active = True

                    win_streak = 0
                    loss_streak += 1
                    total_losses += 1

                    cur.execute(
                        "UPDATE bets SET outcome='Lose' WHERE round_id=? AND outcome IS NULL",
                        (round_id,)
                    )

            cur.execute(
                "INSERT INTO stats VALUES (?,?,?,?,?)",
                (ts, win_streak, loss_streak, total_wins, total_losses)
            )
            conn.commit()
