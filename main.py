import os
import re
import telebot
import gspread
from datetime import datetime
from telebot import types
from keep_alive import keep_alive
keep_alive()  # This runs the web server
from oauth2client.service_account import ServiceAccountCredentials

# === Config ===
BOT_TOKEN = "7819908648:AAGf1LErgGAtnX2sKp3VK5bUNSc1fqx7c78"
JSON_FILE = "abc-rebate-28c4c9b196fe.json"
MAIN_SHEET = "ABC Rebate"
MONTHLY_SHEET = "MonthlyAccounts"
ADMIN_USERNAME = "abrelo28"

# === Google Sheets Setup ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_FILE, scope)
client = gspread.authorize(creds)
main_sheet = client.open(MAIN_SHEET).sheet1
monthly_sheet = client.open(MAIN_SHEET).worksheet(MONTHLY_SHEET)

# === Bot Setup ===
bot = telebot.TeleBot(BOT_TOKEN)

# === Helper Functions ===
def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

def validate_account(account):
    return account.isdigit() and len(account) >= 5

def get_user_row(user):
    rows = main_sheet.get_all_values()
    for idx, row in enumerate(rows[1:], start=2):
        if row[1] == user:
            return idx, row
    return None, None

def get_monthly_submission_row(user, month):
    rows = monthly_sheet.get_all_values()
    for idx, row in enumerate(rows[1:], start=2):
        if row[1] == user and row[4].strip().lower() == month.strip().lower():
            return idx
    return None

# === Start Command ===
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔰 Register", "✏️ Update Info")
    markup.add("📤 Submit MT5 Account", "ℹ️ Help")
    markup.add("📜 Terms & Conditions")
    welcome_text = (
        "💰 Get <b>Paid</b> to <b>Trade</b> – Join Our Trading Rebate Program!\n\n"
        "💸Turn every trade into <b>real cash!</b> With our exclusive rebate program, you earn money back on every trade you make—no <b>extra cost</b>.\n\n"
        "📈 Whether you <b>win</b> or <b>lose</b>, you still earn rebates automatically, <b>paid</b> monthly.\n\n"
        "🔥 <b>Trade more. Earn more. It's that simple.</b>\n\n"
        "🔗 New to Exness? <a href='https://one.exnesstrack.org/a/ovqr8pxq08'><b>Register here</b></a>\n\n"
        "👤 Already have an Exness account? Contact our <b>admin</b>: @ABC_Admin1\n\n"
        "👇 Choose an option below to continue:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=markup)

# === Register ===
@bot.message_handler(func=lambda msg: msg.text == "🔰 Register")
def register(message):
    user = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    row_idx, _ = get_user_row(user)
    if row_idx:
        bot.send_message(message.chat.id, "❗ You are already registered. Use ✏️ Update Info to make changes.")
        return
    msg = bot.send_message(message.chat.id, "📝 Enter your *Full Name*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, ask_email)

def ask_email(message):
    full_name = message.text.strip()
    if len(full_name) < 2:
        msg = bot.send_message(message.chat.id, "❌ Name too short. Please try again:")
        bot.register_next_step_handler(msg, ask_email)
        return
    msg = bot.send_message(message.chat.id, "📧 Enter your *Email*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, lambda m: save_registration(m, full_name))

def save_registration(message, full_name):
    email = message.text.strip()
    if not is_valid_email(email):
        msg = bot.send_message(message.chat.id, "❌ Invalid email format. Please try again:")
        bot.register_next_step_handler(msg, lambda m: save_registration(m, full_name))
        return
    user = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, user, full_name, email, "N/A", "N/A", "Pending"]
    main_sheet.append_row(row)
    bot.send_message(message.chat.id, "✅ Registration complete! Use 📤 Submit MT5 Account each month.")

# === Update Info ===
@bot.message_handler(func=lambda msg: msg.text == "✏️ Update Info")
def update_info(message):
    user = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    row_idx, _ = get_user_row(user)
    if row_idx is None:
        bot.send_message(message.chat.id, "❗ You are not registered. Use 🔰 Register first.")
        return
    msg = bot.send_message(message.chat.id, "✏️ Enter your *updated Full Name*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, update_email, row_idx)

def update_email(message, row_idx):
    full_name = message.text.strip()
    msg = bot.send_message(message.chat.id, "📧 Enter your *updated Email*:", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_update, row_idx, full_name)

def save_update(message, row_idx, full_name):
    email = message.text.strip()
    if not is_valid_email(email):
        msg = bot.send_message(message.chat.id, "❌ Invalid email. Please try again:")
        bot.register_next_step_handler(msg, lambda m: save_update(m, row_idx, full_name))
        return
    main_sheet.update(values=[[full_name]], range_name=f"C{row_idx}")
    main_sheet.update(values=[[email]], range_name=f"D{row_idx}")
    bot.send_message(message.chat.id, "✅ Your info has been updated!")

# === Submit MT5 Account ===
@bot.message_handler(func=lambda msg: msg.text == "📤 Submit MT5 Account")
def submit_account(message):
    user = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    row_idx, user_data = get_user_row(user)
    if not row_idx:
        bot.send_message(message.chat.id, "❗ You must register first. Use 🔰 Register.")
        return
    current_month = datetime.now().strftime("%B")
    email = user_data[3]
    full_name = user_data[2]
    bot.send_message(message.chat.id, f"📅 You are entering your *{current_month}* information.\n🔢 Please enter your *MT5 Account Number*:", parse_mode="Markdown")
    bot.register_next_step_handler(message, save_monthly_submission, user, current_month, email, full_name)

def save_monthly_submission(message, user, month, email, full_name):
    mt5_account = message.text.strip()
    if not validate_account(mt5_account):
        msg = bot.send_message(message.chat.id, "❌ Invalid account number. Please try again:")
        bot.register_next_step_handler(msg, save_monthly_submission, user, month, email, full_name)
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_row = get_monthly_submission_row(user, month)
    if existing_row:
        monthly_sheet.update(values=[[timestamp]], range_name=f"A{existing_row}")
        monthly_sheet.update(values=[[mt5_account]], range_name=f"D{existing_row}")
        monthly_sheet.update(values=[["Pending"]], range_name=f"H{existing_row}")
        bot.send_message(message.chat.id, f"✅ Updated your MT5 submission for {month}!")
    else:
        row = [timestamp, user, full_name, mt5_account, month, email, "", "Pending"]
        # Insert new row at the top (row 2, right after headers)
        monthly_sheet.insert_row(row, 2)
        bot.send_message(message.chat.id, f"✅ MT5 Account submitted for {month}!")

# === Help ===
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Help")
def help_command(message):
    text = (
        "*Bot Help*\n\n"
        "*Tutorial:*\n"
        "1. Use Register to create your account\n"
        "2. Enter your full name and email\n"
        "3. Submit your MT5 account monthly\n"
        "4. Wait for admin approval\n\n"
        "*Commands:*\n"
        "Register - Submit your Exness details\n"
        "Update Info - Edit your registration\n"
        "Submit MT5 Account - Submit monthly account\n"
        "Terms & Conditions - View terms\n\n"
        "*Admin Contact:*\n"
        "@ABC\\_Admin1 - For support and inquiries"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 Terms & Conditions")
def terms_conditions(message):
    terms_text = (
        "*📜 Terms & Conditions*\n\n"
        "1. Submissions must be made monthly\n"
        "2. Only valid MT5 accounts accepted\n"
        "3. Rebates are paid monthly\n"
        "4. Keep your contact info updated\n"
        "5. One account per user\n"
        "6. Admin decisions are final\n\n"
        "By using this bot, you agree to these terms."
    )
    bot.send_message(message.chat.id, terms_text, parse_mode="Markdown")

# === Admin Panel ===
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.username != ADMIN_USERNAME:
        bot.reply_to(message, "❌ You are not authorized.")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👥 View Users", callback_data="admin_view_all"))
    markup.add(types.InlineKeyboardButton("⏳ Pending", callback_data="admin_pending"))
    markup.add(types.InlineKeyboardButton("📊 Monthly", callback_data="admin_monthly"))
    bot.send_message(message.chat.id, "🔐 *Admin Panel*", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_callback(call):
    if call.data == "admin_view_all":
        rows = main_sheet.get_all_values()[1:]
        text = "👥 *Users:*\n" + "\n".join(f"{r[1]} | {r[2]} | {r[4]} | Status: {r[6]}" for r in rows)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    elif call.data == "admin_pending":
        pending = [r for r in main_sheet.get_all_values()[1:] if r[6] == "Pending"]
        text = "⏳ *Pending:*\n" + "\n".join(f"{r[1]} | {r[2]} | {r[4]}" for r in pending)
        bot.send_message(call.message.chat.id, text, parse_mode="Markdown") if pending else bot.send_message(call.message.chat.id, "✅ No pending users.")
    elif call.data == "admin_monthly":
        rows = monthly_sheet.get_all_values()[1:]
        if not rows:
            bot.send_message(call.message.chat.id, "📊 No monthly data.")
        else:
            text = "📊 *Monthly Submissions:*\n" + "\n".join(f"{r[1]} | {r[3]} | {r[4]} | Status: {r[7]}" for r in rows)
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# === Run Bot ===
if __name__ == "__main__":
    print("✅ Bot is running...")
    bot.polling()