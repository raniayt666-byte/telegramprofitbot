"""
Telegram Profit Tracker Bot
Bot untuk tracking profit harian, mingguan, dan bulanan di group Telegram
Commands menggunakan titik (.) bukan slash (/)
Storage: PostgreSQL | Per-group tracking | Keterangan support
"""

import os
import re
import psycopg2
from datetime import datetime, date
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """Get database connection"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            user_name TEXT NOT NULL,
            amount INTEGER NOT NULL,
            keterangan TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_chat_date 
        ON transactions (chat_id, created_at)
    """)
    conn.commit()
    cur.close()
    conn.close()

# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════

def get_week_number(d):
    """Get week number of the month (1-5)"""
    first_day = d.replace(day=1)
    dom = d.day
    adjusted_dom = dom + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1

def get_week_date_range(d):
    """Get start and end date of the current week in the month"""
    week_num = get_week_number(d)
    first_day = d.replace(day=1)
    # Calculate start of week
    start_offset = (week_num - 1) * 7 - first_day.weekday()
    if start_offset < 0:
        start_offset = 0
    start_date = first_day.replace(day=1 + start_offset)
    # End is 6 days later or end of month
    import calendar
    last_day_of_month = calendar.monthrange(d.year, d.month)[1]
    end_day = min(start_date.day + 6, last_day_of_month)
    end_date = d.replace(day=end_day)
    return start_date, end_date

def parse_amount_and_keterangan(text):
    """
    Parse amount dan keterangan dari text
    Format: +5k netflix, -2k refund, +10000 langganan
    Returns: (amount, keterangan) or (None, None)
    """
    text = text.strip()
    
    # Must start with + or -
    if not (text.startswith('+') or text.startswith('-')):
        return None, None
    
    # Split into parts: amount, and optional keterangan
    parts = text.split(None, 1)  # Split max 1 time on whitespace
    amount_text = parts[0]
    keterangan = parts[1].strip() if len(parts) > 1 else ""
    
    # Parse amount
    raw = amount_text
    if raw.startswith('+'):
        raw = raw[1:]
        is_positive = True
    elif raw.startswith('-'):
        raw = raw[1:]
        is_positive = False
    else:
        is_positive = True
    
    raw = raw.strip().lower()
    
    # Format: 2k, 2K, 2rb, 2RB, 2ribu
    match_ribu = re.match(r'^(\d+(?:\.\d+)?)\s*(k|rb|ribu)$', raw, re.IGNORECASE)
    if match_ribu:
        amount = float(match_ribu.group(1)) * 1000
        amount = int(amount) if is_positive else -int(amount)
        return amount, keterangan
    
    # Format: 2jt, 2juta
    match_juta = re.match(r'^(\d+(?:\.\d+)?)\s*(jt|juta)$', raw, re.IGNORECASE)
    if match_juta:
        amount = float(match_juta.group(1)) * 1000000
        amount = int(amount) if is_positive else -int(amount)
        return amount, keterangan
    
    # Format: 2000 (angka biasa)
    match_number = re.match(r'^(\d+)$', raw)
    if match_number:
        amount = int(match_number.group(1))
        amount = amount if is_positive else -amount
        return amount, keterangan
    
    return None, None

def format_rupiah(amount):
    """Format jumlah ke format Rupiah: Rp. X.XXX"""
    if amount < 0:
        return f"-Rp. {abs(amount):,.0f}".replace(",", ".")
    return f"Rp. {amount:,.0f}".replace(",", ".")

def get_month_name(month):
    """Get Indonesian month name"""
    months = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
              "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
    return months[month]

# ═══════════════════════════════════════
# DATABASE QUERIES
# ═══════════════════════════════════════

def db_add_transaction(chat_id, user_name, amount, keterangan=""):
    """Insert a new transaction"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transactions (chat_id, user_name, amount, keterangan) VALUES (%s, %s, %s, %s)",
        (chat_id, user_name, amount, keterangan)
    )
    conn.commit()
    cur.close()
    conn.close()

def db_get_daily_total(chat_id):
    """Get total profit for today"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE chat_id = %s AND created_at::date = CURRENT_DATE",
        (chat_id,)
    )
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

def db_get_weekly_total(chat_id):
    """Get total profit for this week of the month"""
    today = date.today()
    start_date, end_date = get_week_date_range(today)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE chat_id = %s AND created_at::date >= %s AND created_at::date <= %s",
        (chat_id, str(start_date), str(end_date))
    )
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

def db_get_monthly_total(chat_id):
    """Get total profit for this month"""
    today = date.today()
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE chat_id = %s AND EXTRACT(YEAR FROM created_at) = %s AND EXTRACT(MONTH FROM created_at) = %s",
        (chat_id, today.year, today.month)
    )
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return total

def db_get_daily_history(chat_id, limit=10):
    """Get today's transaction history"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_name, amount, keterangan, created_at FROM transactions WHERE chat_id = %s AND created_at::date = CURRENT_DATE ORDER BY created_at ASC LIMIT %s",
        (chat_id, limit)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def db_get_daily_count(chat_id):
    """Get number of transactions today"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM transactions WHERE chat_id = %s AND created_at::date = CURRENT_DATE",
        (chat_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

def db_reset_group(chat_id):
    """Delete all transactions for a group"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM transactions WHERE chat_id = %s", (chat_id,))
    conn.commit()
    cur.close()
    conn.close()

# ═══════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════

async def safe_send(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Send message safely - fallback to send_message if reply_text fails"""
    try:
        await update.message.reply_text(text)
    except BadRequest:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    except Exception:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

# ═══════════════════════════════════════
# MESSAGE HANDLERS
# ═══════════════════════════════════════

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle semua pesan masuk"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    chat_id = update.effective_chat.id
    
    # Handle dot commands
    if text.lower().startswith('.'):
        command = text[1:].split()[0].lower()
        
        if command in ('start', 'help'):
            await start_handler(update, context)
        elif command == 'status':
            await status_handler(update, context)
        elif command in ('daily', 'harian'):
            await daily_handler(update, context)
        elif command in ('weekly', 'mingguan'):
            await weekly_handler(update, context)
        elif command in ('monthly', 'bulanan'):
            await monthly_handler(update, context)
        elif command in ('history', 'riwayat'):
            await history_handler(update, context)
        elif command == 'reset':
            await reset_handler(update, context)
        return
    
    # Handle profit input (+/-)
    if not (text.startswith('+') or text.startswith('-')):
        return
    
    amount, keterangan = parse_amount_and_keterangan(text)
    if amount is None:
        return
    
    user_name = update.message.from_user.first_name
    
    # Save to database
    db_add_transaction(chat_id, user_name, amount, keterangan)
    
    # Get totals
    daily_total = db_get_daily_total(chat_id)
    weekly_total = db_get_weekly_total(chat_id)
    monthly_total = db_get_monthly_total(chat_id)
    
    formatted_amount = format_rupiah(abs(amount))
    formatted_daily = format_rupiah(daily_total)
    formatted_weekly = format_rupiah(weekly_total)
    formatted_monthly = format_rupiah(monthly_total)
    
    # 30% bagi hasil untuk 9host
    share_9host = int(monthly_total * 0.3)
    formatted_share = format_rupiah(share_9host)
    
    today = date.today()
    month_name = get_month_name(today.month)
    
    if amount > 0:
        sign = "+"
        action_emoji = "💰"
    else:
        sign = "-"
        action_emoji = "📉"
    
    # Keterangan line (only show if provided)
    ket_line = f"\n   ꒰ 📋 ꒱  {keterangan}" if keterangan else ""
    
    response = f"""⟡ ─────────────────── ⟡
   {action_emoji} 𝑷𝑹𝑶𝑭𝑰𝑻 𝑼𝑷𝑫𝑨𝑻𝑬
⟡ ─────────────────── ⟡

   ꒰ 👤 ꒱  {user_name}
   ꒰ 💸 ꒱  {sign}{formatted_amount}{ket_line}

   ┊ 📆 Today    ➜  {formatted_daily}
   ┊ 📅 Week     ➜  {formatted_weekly}
   ┊ 🗓 {month_name}  ➜  {formatted_monthly}

   ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
   ꒰ 💎 ꒱  30% 9host ➜  {formatted_share}

⟡ ─────────────────── ⟡"""

    await safe_send(update, context, response)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .start atau .help"""
    response = """⟡ ─────────────────── ⟡
   🤖 𝑷𝑹𝑶𝑭𝑰𝑻 𝑻𝑹𝑨𝑪𝑲𝑬𝑹
⟡ ─────────────────── ⟡

   Bot untuk tracking profit
   harian, mingguan & bulanan.

   ┈┈┈ 𝗜𝗡𝗣𝗨𝗧 𝗙𝗢𝗥𝗠𝗔𝗧 ┈┈┈

   ꒰ 💰 ꒱ +2k ∙ +2rb ∙ +2ribu
   ꒰ 💰 ꒱ +2jt ∙ +2juta
   ꒰ 💰 ꒱ +5000
   ꒰ 📉 ꒱ -5k
   ꒰ 📋 ꒱ +5k netflix

   ┈┈┈ 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 ┈┈┈

   ┊ .status    ➜  Status lengkap
   ┊ .daily     ➜  Profit hari ini
   ┊ .weekly    ➜  Profit minggu ini
   ┊ .monthly   ➜  Profit bulan ini
   ┊ .history   ➜  Riwayat transaksi
   ┊ .reset     ➜  Reset semua data

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .status"""
    chat_id = update.effective_chat.id
    today = date.today()
    month_name = get_month_name(today.month)
    week_num = get_week_number(today)
    
    daily_total = db_get_daily_total(chat_id)
    weekly_total = db_get_weekly_total(chat_id)
    monthly_total = db_get_monthly_total(chat_id)
    tx_count = db_get_daily_count(chat_id)
    
    formatted_daily = format_rupiah(daily_total)
    formatted_weekly = format_rupiah(weekly_total)
    formatted_monthly = format_rupiah(monthly_total)
    
    # 30% bagi hasil untuk 9host
    share_9host = int(monthly_total * 0.3)
    formatted_share = format_rupiah(share_9host)
    
    if monthly_total > 0:
        emoji = "💎"
    elif monthly_total < 0:
        emoji = "📉"
    else:
        emoji = "📊"
    
    response = f"""⟡ ─────────────────── ⟡
   {emoji} 𝑺𝑻𝑨𝑻𝑼𝑺 𝑷𝑹𝑶𝑭𝑰𝑻
⟡ ─────────────────── ⟡

   ꒰ 📆 ꒱  𝗛𝗮𝗿𝗶 𝗜𝗻𝗶
          {today.strftime('%d/%m/%Y')}
          ➜  {formatted_daily}

   ꒰ 📅 ꒱  𝗠𝗶𝗻𝗴𝗴𝘂 𝗸𝗲-{week_num}
          {month_name}
          ➜  {formatted_weekly}

   ꒰ 🗓 ꒱  𝗕𝘂𝗹𝗮𝗻 {month_name}
          {today.year}
          ➜  {formatted_monthly}

   ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈

   ꒰ 📝 ꒱  Transaksi hari ini: {tx_count}
   ꒰ 💎 ꒱  30% 9host ➜  {formatted_share}

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

async def daily_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .daily"""
    chat_id = update.effective_chat.id
    daily_total = db_get_daily_total(chat_id)
    formatted = format_rupiah(daily_total)
    emoji = "💰" if daily_total >= 0 else "📉"
    
    response = f"""⟡ ─────────────────── ⟡
   {emoji} 𝑷𝑹𝑶𝑭𝑰𝑻 𝑯𝑨𝑹𝑰 𝑰𝑵𝑰
⟡ ─────────────────── ⟡

   ┊ ➜  {formatted}

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

async def weekly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .weekly"""
    chat_id = update.effective_chat.id
    today = date.today()
    week_num = get_week_number(today)
    month_name = get_month_name(today.month)
    weekly_total = db_get_weekly_total(chat_id)
    formatted = format_rupiah(weekly_total)
    emoji = "💰" if weekly_total >= 0 else "📉"
    
    response = f"""⟡ ─────────────────── ⟡
   {emoji} 𝑷𝑹𝑶𝑭𝑰𝑻 𝑴𝑰𝑵𝑮𝑮𝑼𝑨𝑵
⟡ ─────────────────── ⟡

   ꒰ 📅 ꒱  Minggu ke-{week_num} ({month_name})
   ┊ ➜  {formatted}

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

async def monthly_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .monthly"""
    chat_id = update.effective_chat.id
    today = date.today()
    month_name = get_month_name(today.month)
    monthly_total = db_get_monthly_total(chat_id)
    formatted = format_rupiah(monthly_total)
    emoji = "💰" if monthly_total >= 0 else "📉"
    
    # 30% bagi hasil untuk 9host
    share_9host = int(monthly_total * 0.3)
    formatted_share = format_rupiah(share_9host)
    
    response = f"""⟡ ─────────────────── ⟡
   {emoji} 𝑷𝑹𝑶𝑭𝑰𝑻 𝑩𝑼𝑳𝑨𝑵𝑨𝑵
⟡ ─────────────────── ⟡

   ꒰ 🗓 ꒱  {month_name} {today.year}
   ┊ ➜  {formatted}

   ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
   ꒰ 💎 ꒱  30% 9host ➜  {formatted_share}

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .history"""
    chat_id = update.effective_chat.id
    today = date.today()
    
    rows = db_get_daily_history(chat_id, limit=10)
    
    if not rows:
        response = """⟡ ─────────────────── ⟡
   📜 𝑹𝑰𝑾𝑨𝒀𝑨𝑻
⟡ ─────────────────── ⟡

   Belum ada transaksi hari ini.

⟡ ─────────────────── ⟡"""
        await safe_send(update, context, response)
        return
    
    daily_total = db_get_daily_total(chat_id)
    formatted_daily = format_rupiah(daily_total)
    
    header = f"""⟡ ─────────────────── ⟡
   📜 𝑹𝑰𝑾𝑨𝒀𝑨𝑻
   {today.strftime('%d/%m/%Y')}
⟡ ─────────────────── ⟡
"""
    
    entries = ""
    for user_name, amount, keterangan, created_at in rows:
        time_str = created_at.strftime("%H:%M")
        formatted_amt = format_rupiah(abs(amount))
        dot = "🟢" if amount >= 0 else "🔴"
        sign = "+" if amount >= 0 else "-"
        ket = f" ({keterangan})" if keterangan else ""
        entries += f"   {dot} {time_str} ∙ {user_name}\n      {sign}{formatted_amt}{ket}\n"
    
    footer = f"""
   ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈
   ꒰ 💵 ꒱  Total: {formatted_daily}
⟡ ─────────────────── ⟡"""
    
    await safe_send(update, context, header + entries + footer)

async def reset_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle .reset"""
    chat_id = update.effective_chat.id
    db_reset_group(chat_id)
    
    response = """⟡ ─────────────────── ⟡
   🔄 𝑹𝑬𝑺𝑬𝑻
⟡ ─────────────────── ⟡

   Semua data profit grup ini
   telah direset ke Rp. 0

⟡ ─────────────────── ⟡"""
    await safe_send(update, context, response)

# ═══════════════════════════════════════
# MAIN
# ═══════════════════════════════════════

def main():
    """Main function untuk menjalankan bot"""
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ Error: BOT_TOKEN belum di-set!")
        print("Set environment variable: BOT_TOKEN=your_token_here")
        return
    
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL belum di-set!")
        print("Tambahkan PostgreSQL di Railway dan set DATABASE_URL")
        return
    
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    print("🤖 Bot sedang berjalan...")
    print("Tekan Ctrl+C untuk menghentikan bot")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
