pythonimport os
from dotenv import load_dotenv

load_dotenv()

# .env faylidan o'qiladi (pastdagi .env.example ga qarang)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Loyiha statuslari haqida xabar yuboriladigan kanal ID yoki @username
# Masalan: -1001234567890  yoki  @mening_kanalim
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

# Botni boshqara oladigan adminlar Telegram ID lari (vergul bilan ajratilgan)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]

# Necha daqiqada bir marta barcha loyihalar avtomatik tekshiriladi
CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))

# Bir loyihani tekshirishda javob kutish vaqti (soniya)
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))

# Sekin ishlayapti deb hisoblanadigan javob vaqti chegarasi (soniya)
SLOW_THRESHOLD = float(os.getenv("SLOW_THRESHOLD", "3.0"))

DB_PATH = os.getenv("DB_PATH", "projects.db")
