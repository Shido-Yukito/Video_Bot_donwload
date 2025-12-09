import telebot
import yt_dlp
import os
import re
import unicodedata # Added for robust Unicode filename handling

# Your bot token - REPLACE WITH YOUR ACTUAL TOKEN
BOT_TOKEN = "8581963441:AAE8WtEdXBtqf-ZOXIIsNRJ15Z0I_1zaszg"
bot = telebot.TeleBot(BOT_TOKEN)

# Optional: cookies for private/age-restricted videos
COOKIE_FILE = 'cookies.txt' 
if not os.path.exists(COOKIE_FILE):
    COOKIE_FILE = None

# 🛑 CRITICAL FIX: Direct FFmpeg Path for merging video and audio
# This path must point directly to the 'ffmpeg.exe' file.
FFMPEG_PATH = 'C:/ffmpep/ffmpeg-8.0.1-essentials_build/bin/ffmpeg.exe' 

# --- Helper Function (Fixed for robust cleanup and renaming) ---

def send_file(chat_id, filename):
    # 1. Normalize filename to handle complex Unicode characters (like Khmer)
    try:
        # Normalize the filename path for better Windows compatibility
        filename = unicodedata.normalize('NFKC', filename)
    except Exception:
        pass # Ignore normalization errors

    # Check if the file was actually downloaded
    if not os.path.exists(filename):
        bot.send_message(chat_id, f"❌ Downloaded file not found: {filename}")
        return

    # Clean illegal Windows characters
    folder, file = os.path.split(filename)
    safe_file = re.sub(r'[\\/*?:"<>|]', "", file)
    safe_filename = os.path.join(folder, safe_file)
    
    final_file_path = filename

    if filename != safe_filename:
        try:
            # Rename the file to the clean name
            os.rename(filename, safe_filename)
            final_file_path = safe_filename
        except Exception as rename_error:
            # If rename fails (file lock/permission), we try to use the original path
            print(f"Warning: Rename failed. Error: {rename_error}")
            final_file_path = filename 

    try:
        # 2. Attempt to send the file
        if os.path.exists(final_file_path):
            with open(final_file_path, 'rb') as video:
                bot.send_document(chat_id, video)
        else:
            bot.send_message(chat_id, f"❌ File not found at final path: {final_file_path}")
    except Exception as e:
        # Handle errors during SENDING
        bot.send_message(chat_id, f"❌ Failed to send video. Error: {e}")
    finally:
        # 3. GUARANTEED DELETION BLOCK (Ensures file is NOT left on your laptop)
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
            print(f"Cleaned up file: {final_file_path}")
        elif os.path.exists(filename):
             os.remove(filename)
             print(f"Cleaned up original file: {filename}")


## --- Bot Handlers ---

@bot.message_handler(commands=['start'])
def start(msg):
    bot.reply_to(msg, "Send me any video link or playlist. I will download it for you 🎬")

@bot.message_handler(func=lambda msg: True)
def download_video(msg):
    url = msg.text.strip()
    chat_id = msg.chat.id
    status_msg = bot.send_message(chat_id, "📥 Downloading, please wait...")

    try:
        downloaded_files = []
        
        def hook(d):
            if d['status'] == 'finished':
                downloaded_files.append(d['filename'])
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best', 
            'merge_output_format': 'mp4',
            # 🛑 FIX: Save directly to the script directory for simplicity
            'outtmpl': '%(title)s.%(ext)s', 
            
            'ffmpeg_location': FFMPEG_PATH, 
            
            'noplaylist': False,
            'ignoreerrors': True,
            'retries': 3,
            'quiet': True, # Keep it True unless you need to debug a failure
            'nocheckcertificate': True,
            'geo_bypass': True,
            'cookiefile': COOKIE_FILE,
            'progress_hooks': [hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url]) 

        if not downloaded_files:
            bot.edit_message_text("❌ No downloadable video found or extraction failed.", chat_id, status_msg.message_id)
            return

        for filename in downloaded_files:
            send_file(chat_id, filename)

        bot.edit_message_text("✅ All downloads completed!", chat_id, status_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Failed to download. Error: {e}", chat_id, status_msg.message_id)
        if 'downloaded_files' in locals():
            for filename in downloaded_files:
                if os.path.exists(filename):
                    os.remove(filename)


if __name__ == '__main__':
    print("Bot is starting...")
    bot.polling(none_stop=True)