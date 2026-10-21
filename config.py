import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Admin foydalanuvchilar ID lari (Telegram ID ni hech kim soxtalashtira olmaydi)
ADMIN_IDS = [
    1226176004  # Asadbek Ataboyev (@maksudovich17)
]

# Admin username lar
ADMIN_USERNAMES = [
    "maksudovich17"
]

# Ovoz: uz-UZ-SardorNeural (Jarangli, insoniy erkak ovozi), uz-UZ-MadinaNeural (Ayol)
TTS_VOICE = os.getenv("TTS_VOICE", "uz-UZ-SardorNeural")
