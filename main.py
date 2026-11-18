import os
import re
import random
import string
import logging
import openpyxl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler,
)

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Conversation States
GET_FILENAME, GET_PASSWORD = range(2)

# Temporary storage for user sessions
user_sessions = {}

# --- ADMIN CONFIGURATION ---
ADMIN_IDS = [8392369574]

# Global registry to track all users
registered_users = {}

# --- MONO TYPE (MONOSPACE) FONT CONVERTER ---
def to_mono_type(text: str) -> str:
    """টেক্সটকে ইউনিকোড মোনোস্পেস ফন্টে রূপান্তর করার ফাংশন"""
    mono_mapping = {
        'A':'𝙰','B':'𝙱','C':'𝙲','D':'𝙳','E':'𝙴','F':'𝙵','G':'𝙶','H':'𝙷','I':'𝙸','J':'𝙹','K':'𝙺','L':'𝙻','M':'𝙼',
        'N':'𝙽','O':'𝙾','P':'𝙿','Q':'ℚ','R':'𝚁','S':'𝚂','T':'𝚃','U':'𝚄','V':'𝚅','W':'𝚆','X':'𝚇','Y':'𝚈','Z':'𝚉',
        'a':'𝚊','b':'𝚋','c':'𝚌','d':'𝚍','e':'𝚎','f':'𝚏','g':'𝚐','h':'𝚑','i':'𝚒','j':'𝚓','k':'𝚔','l':'𝚕','m':'𝚖',
        'n':'𝚗','o':'𝚘','p':'𝚙','q':'𝚚','r':'𝚛','s':'𝚜','t':'𝚝','u':'𝚞','v':'𝚟','w':'𝚠','x':'𝚡','y':'𝚢','z':'𝚣',
        '0':'𝟘','1':'𝟙','2':'𝟐','3':'𝟛','4':'𝟜','5':'𝟝','6':'𝟞','7':'𝟟','8':'𝟠','9':'𝟡'
    }
    return "".join(mono_mapping.get(c, c) for c in text)

def extract_single_cookie(cookie_text: str) -> dict:
    cleaned = cookie_text.replace('\r\n', '\n').strip()
    if not cleaned:
        return None
        
    c_match = re.search(r'c_user[=\s\t:]+(\d+)', cleaned, re.IGNORECASE)
    if c_match:
        uid = c_match.group(1)
        clean_cookie = " ".join(cleaned.split())
        return {'uid': uid, 'cookie': clean_cookie}
    else:
        gen_match = re.search(r'\b\d{10,16}\b', cleaned)
        uid = gen_match.group(0) if gen_match else "UNKNOWN_UID"
        clean_cookie = " ".join(cleaned.split())
        return {'uid': uid, 'cookie': clean_cookie}

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start Bot & Reset Session"),
        BotCommand("name", "Open Interactive Name Generator"),
        BotCommand("pass", "Open Interactive Password Generator"),
        BotCommand("duplicate", "Check duplicate cookies"),
        BotCommand("remove", "Remove duplicate cookies"),
        BotCommand("all", "Generate Excel file with custom name"),
        BotCommand("history", "Ager Export dekha (Last Excel)"),
        BotCommand("admin", "Admin Panel (Admin only)"),
        BotCommand("broadcast", "Send message to all users (Admin only)"),
        BotCommand("getfile", "Get user's excel file /getfile <user_id>"),
        BotCommand("cancel", "Cancel current action")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    registered_users[user_id] = {
        'name': user.full_name,
        'username': user.username or "N/A"
    }

    if user_id not in user_sessions:
        user_sessions[user_id] = {'pairs': [], 'last_file': None, 'last_count': 0, 'file_name': ''}
    user_sessions[user_id]['pairs'] = []
    
    await update.message.reply_text(
        "👋 **Welcome!**\n\n"
        "আপনি কুকিগুলো একটি একটি করে পাঠাতে পারেন।\n\n"
        "🛠 **অন্যান্য কমান্ডসমূহ:**\n"
        "• `/name` - স্টাইলিশ নাম জেনারেটর মেনু\n"
        "• `/pass` - পাসওয়ার্ড জেনারেটর মেনু\n"
        "• `/duplicate` - ডুপ্লিকেট চেক করতে\n"
        "• `/remove` - ডুপ্লিকেট মুছতে\n"
        "• `/all` - এক্সেল ফাইল বানাতে\n"
        "• `/history` - আগের এক্সপোর্ট দেখতে\n"
    )

# --- INTERACTIVE NAME GENERATOR MENU ---
async def generate_names_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🇸🇦 Arabic", callback_data="gen_name_ar"),
            InlineKeyboardButton("🇺🇸 USA", callback_data="gen_name_us"),
            InlineKeyboardButton("🇧🇩 BD", callback_data="gen_name_bd")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="gen_close")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "« 👤 **NAME GENERATOR** »\n"
        "──────────────────────────────\n"
        "Select a country to generate 3 random realistic full names:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- INTERACTIVE PASSWORD GENERATOR MENU ---
async def generate_passwords_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("6 Digits", callback_data="gen_pass_6"),
            InlineKeyboardButton("8 Digits", callback_data="gen_pass_8"),
            InlineKeyboardButton("12 Digits", callback_data="gen_pass_12")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="gen_close")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "« 🔑 **PASSWORD GENERATOR** »\n"
        "──────────────────────────────\n"
        "Select length to generate 3 random secure passwords:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# --- BUTTON CLICK HANDLER (FOR BOTH NAME & PASS) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "gen_close":
        await query.message.delete()
        return

    # --- NAME GENERATION LOGIC ---
    if data.startswith("gen_name_"):
        name_databases = {
            "bd": {
                "first": ["Anik", "Rahim", "Tanvir", "Sakib", "Fahim", "Nayeem", "Sadia", "Nusrat", "Ratul", "Imran"],
                "last": ["Hossain", "Ahmed", "Islam", "Khan", "Chowdhury", "Rahman", "Akter", "Khatun", "Mahmud", "Uddin"]
            },
            "us": {
                "first": ["James", "John", "Robert", "Michael", "William", "David", "Emma", "Olivia", "Sophia", "Liam"],
                "last": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Taylor", "Anderson"]
            },
            "ar": {
                "first": ["Mohammed", "Abdullah", "Ibrahim", "Yusuf", "Omar", "Fatima", "Ayesha", "Zainab", "Ali", "Hassan"],
                "last": ["Al-Amin", "Rahman", "Hossain", "Khan", "Al-Mahmud", "Malik", "Sheikh", "Nasser"]
            }
        }

        country_key = data.replace("gen_name_", "")
        if country_key not in name_databases:
            country_key = "bd"

        selected_db = name_databases[country_key]
        generated_lines = []
        
        for _ in range(3):
            raw_name = f"{random.choice(selected_db['first'])} {random.choice(selected_db['last'])}"
            mono_name = to_mono_type(raw_name)
            generated_lines.append(f"`{mono_name}`")

        names_text = "\n".join(generated_lines)
        country_names_map = {"bd": "🇧🇩 Bangladeshi", "us": "🇺🇸 American", "ar": "🇸🇦 Arabic"}
        current_title = country_names_map.get(country_key, "Global")

        keyboard = [
            [
                InlineKeyboardButton("🇸🇦 Arabic", callback_data="gen_name_ar"),
                InlineKeyboardButton("🇺🇸 USA", callback_data="gen_name_us"),
                InlineKeyboardButton("🇧🇩 BD", callback_data="gen_name_bd")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="gen_close")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            f"« 👤 **NAME GENERATOR ({current_title})** »\n"
            f"──────────────────────────────\n\n"
            f"{names_text}\n\n"
            f"💡 যেকোনো নামের ওপর **ট্যাপ** করলেই সেটি কপি হয়ে যাবে!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    # --- PASSWORD GENERATION LOGIC ---
    elif data.startswith("gen_pass_"):
        length_str = data.replace("gen_pass_", "")
        length = int(length_str) if length_str.isdigit() else 8

        chars = string.ascii_letters + string.digits + "@#$!%"
        pwd_lines = []
        
        for _ in range(3):
            raw_pwd = "".join(random.choice(chars) for _ in range(length))
            mono_pwd = to_mono_type(raw_pwd)
            pwd_lines.append(f"`{mono_pwd}`")

        pwd_text = "\n".join(pwd_lines)

        keyboard = [
            [
                InlineKeyboardButton("6 Digits", callback_data="gen_pass_6"),
                InlineKeyboardButton("8 Digits", callback_data="gen_pass_8"),
                InlineKeyboardButton("12 Digits", callback_data="gen_pass_12")
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="gen_close")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            f"« 🔑 **PASSWORD GENERATOR ({length} Digits)** »\n"
            f"──────────────────────────────\n\n"
            f"{pwd_text}\n\n"
            f"💡 যেকোনো পাসওয়ার্ডের ওপর **ট্যাপ** করলেই সেটি কপি হয়ে যাবে!",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ এই কমান্ডটি ব্যবহার করার অনুমতি আপনার নেই।")
        return

    total_users = len(registered_users)
    user_list_text = "👥 **Registered Users List:**\n\n"
    
    for uid, info in registered_users.items():
        user_list_text += f"• **Name:** {info['name']}\n  **ID:** `{uid}`\n  **Username:** @{info['username']}\n\n"

    if not registered_users:
        user_list_text = "⚠️ এখনো কোনো ইউজার বট স্টার্ট করেনি।"

    await update.message.reply_text(
        f"🛠 **Admin Control Panel**\n\n"
        f"• Total Bot Users: **{total_users}**\n\n"
        f"{user_list_text}\n"
        f"💡 কোনো ইউজারের ফাইল নিতে চাইলে `/getfile <user_id>` কমান্ড দিন।"
    )

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ এই কমান্ডটি ব্যবহার করার অনুমতি আপনার নেই।")
        return

    message_text = " ".join(context.args)
    if not message_text and update.message.reply_to_message:
        if update.message.reply_to_message.text:
            message_text = update.message.reply_to_message.text

    if not message_text:
        await update.message.reply_text("⚠️ দয়া করে ব্রডকাস্ট করার মেসেজটি দিন।")
        return

    success_count = 0
    fail_count = 0
    status_msg = await update.message.reply_text("⏳ ব্রডকাস্ট পাঠানো শুরু হয়েছে...")

    for uid in registered_users.keys():
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 **Announcement:**\n\n{message_text}", parse_mode="Markdown")
            success_count += 1
        except Exception:
            fail_count += 1

    await status_msg.edit_text(f"✅ **Broadcast Completed!**\n\n• সফল: **{success_count}**\n• ফেইল: **{fail_count}**")

async def get_user_file_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ এই কমান্ডটি ব্যবহার করার অনুমতি আপনার নেই।")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ ইউজার ID দিন। উদাহরণ: `/getfile 123456789`")
        return

    target_user_id = args[0]
    found_file = None
    for f in os.listdir('.'):
        if f.endswith(f"_{target_user_id}.xlsx"):
            found_file = f
            break

    if found_file and os.path.exists(found_file):
        with open(found_file, "rb") as f:
            await update.message.reply_document(document=f, caption=f"📂 Admin Access: User ID `{target_user_id}`")
    else:
        await update.message.reply_text(f"⚠️ এই User ID (`{target_user_id}`) এর কোনো ফাইল নেই।")

async def check_duplicates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions or not user_sessions[user_id]['pairs']:
        await update.message.reply_text("⚠️ কোনো কুকি জমা হয়নি!")
        return

    pairs = user_sessions[user_id]['pairs']
    total_count = len(pairs)
    seen_uids = set()
    duplicates_count = 0
    
    for item in pairs:
        if item['uid'] in seen_uids:
            duplicates_count += 1
        else:
            seen_uids.add(item['uid'])

    await update.message.reply_text(f"📊 মোট কুকি: **{total_count}** | ডুপ্লিকেট: **{duplicates_count}**\nরিমুভ করতে `/remove` দিন।")

async def remove_duplicates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions or not user_sessions[user_id]['pairs']:
        await update.message.reply_text("⚠️ কুকি নেই!")
        return

    pairs = user_sessions[user_id]['pairs']
    before_count = len(pairs)
    unique_pairs = []
    seen_uids = set()
    
    for item in pairs:
        if item['uid'] not in seen_uids or item['uid'] == 'UNKNOWN_UID':
            seen_uids.add(item['uid'])
            unique_pairs.append(item)
            
    user_sessions[user_id]['pairs'] = unique_pairs
    removed_count = before_count - len(unique_pairs)

    await update.message.reply_text(f"✅ বাদ গেছে: **{removed_count}** টি। ইউনিক বাকি আছে: **{len(unique_pairs)}** টি। `/all` দিন।")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions or not user_sessions[user_id].get('last_file'):
        await update.message.reply_text("⚠️ কোনো হিস্ট্রি নেই। ব্যস্ততার কারণে ফাইল পাওয়া যায়নি।")
        return

    last_file = user_sessions[user_id]['last_file']
    try:
        with open(last_file, "rb") as f:
            await update.message.reply_document(document=f, caption="📂 আপনার পূর্ববর্তী এক্সেল ফাইল।")
    except FileNotFoundError:
        await update.message.reply_text("⚠️ ফাইল পাওয়া যায়নি।")

async def collect_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()

    if user_id not in registered_users:
        registered_users[user_id] = {'name': user.full_name, 'username': user.username or "N/A"}

    if user_id not in user_sessions:
        user_sessions[user_id] = {'pairs': [], 'last_file': None, 'last_count': 0, 'file_name': ''}

    pair = extract_single_cookie(text)
    if pair:
        user_sessions[user_id]['pairs'].append(pair)
        total_count = len(user_sessions[user_id]['pairs'])
        await update.message.reply_text(
            f"✅ কুকি সেভ হয়েছে! (মোট জমা: **{total_count}** টি)\n"
            f"• ডুপ্লিকেট চেক করতে `/duplicate`\n"
            f"• ডুপ্লিকেট মুছতে `/remove`\n"
            f"• ফাইল বানাতে `/all` দিন."
        )
    else:
        await update.message.reply_text("⚠️ সঠিক কুকি ফরম্যাট নয়:")

async def trigger_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_sessions or not user_sessions[user_id]['pairs']:
        await update.message.reply_text("⚠️ কোনো কুকি জমা হয়নি!")
        return ConversationHandler.END

    await update.message.reply_text("📁 আপনার **Excel File-er Name** দিন:")
    return GET_FILENAME

async def receive_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file_name_input = update.message.text.strip()
    safe_name = re.sub(r'[\/*?:"<>|]', "", file_name_input)
    if not safe_name:
        safe_name = f"accounts_{user_id}"

    user_sessions[user_id]['file_name'] = safe_name
    await update.message.reply_text("🔑 একটি **Common Password** দিন:")
    return GET_PASSWORD

async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    password = update.message.text.strip()

    if user_id not in user_sessions or not user_sessions[user_id]['pairs']:
        await update.message.reply_text("Session expire হয়ে গেছে। /start দিন।")
        return ConversationHandler.END

    pairs = user_sessions[user_id]['pairs']
    custom_name = user_sessions[user_id].get('file_name', f"accounts_{user_id}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Accounts Data"
    ws.views.sheetView[0].showGridLines = True

    headers = ["UID", "Password", "Cookies"]
    ws.append(headers)

    for item in pairs:
        ws.append([item['uid'], password, item['cookie']])

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max(max_length + 3, 10), 60)

    file_name = f"{custom_name}_{user_id}.xlsx"
    wb.save(file_name)

    user_sessions[user_id]['last_file'] = file_name
    user_sessions[user_id]['last_count'] = len(pairs)

    await update.message.reply_text(f"🎉 ফাইল তৈরি হয়েছে:")
    with open(file_name, "rb") as f:
        await update.message.reply_document(document=f, caption=f"📊 মোট {len(pairs)}টি অ্যাকাউন্ট।")

    user_sessions[user_id]['pairs'] = []
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if user_id in user_sessions:
        user_sessions[user_id]['pairs'] = []
    await update.message.reply_text("Action cancel করা হয়েছে।")
    return ConversationHandler.END

def main():
    TOKEN = "9149922182:AAHy8DbsIKNS04ng9niIrIjd2gPn7pTZ2Rc"

    app = ApplicationBuilder().token(TOKEN).post_init(set_bot_commands).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('all', trigger_all_command)],
        states={
            GET_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filename)],
            GET_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('name', generate_names_menu))
    app.add_handler(CommandHandler('pass', generate_passwords_menu))
    app.add_handler(CommandHandler('duplicate', check_duplicates))
    app.add_handler(CommandHandler('remove', remove_duplicates))
    app.add_handler(CommandHandler('removeduplicate', remove_duplicates))
    app.add_handler(CommandHandler('history', show_history))
    app.add_handler(CommandHandler('admin', admin_panel))
    app.add_handler(CommandHandler('broadcast', broadcast_message))
    app.add_handler(CommandHandler('getfile', get_user_file_admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(conv_handler)
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect_cookies))

    print("Bot is running perfectly...")
    app.run_polling()

if __name__ == '__main__':
    main()
