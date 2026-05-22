import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from flask import Flask
from threading import Thread

BOT_TOKEN = os.environ['BOT_TOKEN']
CHANNEL_USERNAME = "@Taqdimat1"
CHANNEL_LINK = "https://t.me/Taqdimat1"

web_app = Flask('')

@web_app.route('/')
def home():
    return "البوت شغال"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.daemon = True
    t.start()

async def check_subscription(user_id, context):
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"خطأ: {e}")
        return False

async def send_subscribe_message(message_obj):
    keyboard = [
        [InlineKeyboardButton("اشترك في القناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("تحققت من المتابعة", callback_data="check_sub")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🔒 لازم تتابع قناتنا أولاً عشان تستخدم البوت\n\nاضغط على الزر أدناه للمتابعة، ثم اضغط تحققت من المتابعة."
    await message_obj.reply_text(text, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context)
    if is_subscribed:
        await update.message.reply_text(
            "مرحباً! أرسل لي رابط فيديو من:\n"
            "يوتيوب، تيك توك، تويتر/X، انستقرام\n"
            "وراح أحمله لك مباشرة"
        )
    else:
        await send_subscribe_message(update.message)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_subscribed = await check_subscription(user_id, context)
    
    if not is_subscribed:
        await send_subscribe_message(update.message)
        return
    
    url = update.message.text
    
    if not any(x in url for x in ['youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com', 'x.com', 'instagram.com']):
        await update.message.reply_text("أرسل رابط صحيح من يوتيوب، تيك توك، تويتر، أو انستقرام")
        return
    
    msg = await update.message.reply_text("جاري التحميل...")
    
    ydl_opts = {
        'format': 'best[filesize<50M]/best',
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
            if not file_path.endswith('.mp4'):
                file_path = file_path.rsplit('.', 1)[0] + '.mp4'
        
        file_size = os.path.getsize(file_path)
        
        if file_size > 50 * 1024 * 1024:
            await msg.edit_text("الفيديو كبير جداً حتى بعد الضغط، جرب فيديو أقصر")
            os.remove(file_path)
            return
        
        await msg.edit_text("جاري الإرسال...")
        
        with open(file_path, 'rb') as video:
            await update.message.reply_video(video=video)
        
        await msg.delete()
        os.remove(file_path)
    
    except Exception as e:
        await msg.edit_text("حدث خطأ أثناء التحميل، تأكد من الرابط وحاول مرة ثانية")
        print(f"خطأ: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "check_sub":
        user_id = query.from_user.id
        is_subscribed = await check_subscription(user_id, context)
        if is_subscribed:
            await query.edit_message_text(
                "مرحباً! أرسل لي رابط فيديو من:\n"
                "يوتيوب، تيك توك، تويتر/X، انستقرام\n"
                "وراح أحمله لك مباشرة"
            )
        else:
            await query.answer("لم تشترك بعد! اشترك في القناة أولاً", show_alert=True)

def main():
    keep_alive()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    app_bot.add_handler(CallbackQueryHandler(button_handler))
    print("البوت شغال...")
    app_bot.run_polling()

if __name__ == "__main__":
    main()
