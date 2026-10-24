# ربات تلگرامی پرسش‌وپاسخ سازمانی

ربات فارسی پرسش‌وپاسخ برای خدمات سازمانی، منابع انسانی، ساختار سازمانی، بیمه تکمیلی و امور رفاهی دانشگاه.

## قابلیت‌ها

- منوی چندسطحی پویا بر اساس پایگاه داده
- جستجوی فارسی هوشمند (یکسان‌سازی ی/ک، نیم‌فاصله)
- پنل مدیریت کامل داخل تلگرام (`/admin`)
- واردسازی خودکار از فایل‌های Excel و Word
- کنترل دسترسی مدیران
- ثبت آمار و لاگ تغییرات
- پشتیبان‌گیری پایگاه داده

## پیش‌نیازها

- Python 3.10 یا بالاتر
- توکن ربات از [@BotFather](https://t.me/BotFather)

## نصب

```bash
cd telegram_qa_bot
python3 -m venv .venv
source .venv/bin/activate   # ویندوز: .venv\Scripts\activate
pip install -r requirements.txt
```

## تنظیمات

```bash
cp .env.example .env
nano .env
```

مقادیر ضروری:

```
BOT_TOKEN=توکن_ربات_شما
ADMIN_TELEGRAM_IDS=شناسه_عددی_تلگرام_شما
DATABASE_URL=sqlite:///data/bot.db
```

شناسه عددی خود را از ربات [@userinfobot](https://t.me/userinfobot) بگیرید.

## راه‌اندازی اولیه

```bash
# ۱. ایجاد پایگاه داده
python scripts/initialize_db.py

# ۲. واردسازی داده‌های سه فایل منبع
python scripts/import_initial_data.py

# ۳. اجرای ربات
python app.py
```

## دستورات ربات

| دستور | توضیح |
|--------|--------|
| `/start` | منوی اصلی |
| `/help` | راهنما |
| `/search` | جستجو |
| `/admin` | پنل مدیریت (فقط مدیران) |
| `/cancel` | لغو عملیات جاری |

## پشتیبان‌گیری

```bash
python scripts/backup_db.py
```

فایل پشتیبان در پوشه `data/` ذخیره می‌شود.

## تست‌ها

```bash
pytest tests/ -v
```

## اجرای دائمی روی سرور (systemd)

فایل `/etc/systemd/system/telegram-qa-bot.service`:

```ini
[Unit]
Description=Telegram QA Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/telegram_qa_bot
Environment=PATH=/path/to/telegram_qa_bot/.venv/bin
ExecStart=/path/to/telegram_qa_bot/.venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-qa-bot
sudo systemctl start telegram-qa-bot
sudo systemctl status telegram-qa-bot
```

## ساختار پروژه

```
telegram_qa_bot/
├── app.py                 # نقطه ورود
├── config.py
├── requirements.txt
├── database/              # مدل‌ها و اتصال
├── bot/                   # هندلرهای کاربری و مدیریت
├── services/              # منطق کسب‌وکار
├── importers/             # واردسازی Excel/Word
├── utils/                 # ابزارهای کمکی
├── scripts/               # اسکریپت‌های راه‌اندازی
├── tests/
└── data/                  # پایگاه داده
```

## عیب‌یابی

| مشکل | راه‌حل |
|------|--------|
| `BOT_TOKEN تنظیم نشده` | فایل `.env` را بررسی کنید |
| دسترسی مدیریت ندارید | `ADMIN_TELEGRAM_IDS` را درست تنظیم کنید |
| داده‌ای نمایش داده نمی‌شود | اسکریپت `import_initial_data.py` را اجرا کنید |
| خطای SQLite locked | فقط یک نمونه از ربات در حال اجرا باشد |

## مجوز

این پروژه برای استفاده داخلی سازمانی تهیه شده است.

## قابلیت هوش مصنوعی (RAG)

پاسخ‌گویی هوشمند فقط بر اساس محتوای تأییدشدهٔ دیتابیس (سه فایل مرجع) انجام می‌شود.

### تنظیم

در فایل `.env`:

```
OPENROUTER_API_KEY=sk-or-...
AI_MODEL=meta-llama/llama-3.2-3b-instruct:free
AI_ENABLED=1
AI_SCORE_THRESHOLD=12
AI_TOP_K=4
```

کلید رایگان: [openrouter.ai](https://openrouter.ai)

بدون API Key، ربات همچنان کار می‌کند و در صورت یافتن منبع مرتبط، پاسخ ثبت‌شده را مستقیم نشان می‌دهد.

### استفاده کاربر

منوی اصلی → **🤖 پرسش از هوش مصنوعی** → نوشتن سؤال طبیعی

### پنل ادمین

`/admin` → **🤖 تنظیمات AI**
- فعال/غیرفعال
- بازسازی نمایه جست‌وجو پس از تغییر محتوا

### اصول امنیتی

- بدون شواهد کافی در منابع، پاسخ محتوایی ساخته نمی‌شود
- System Prompt و کنترل کد هر دو محدودیت منابع را اعمال می‌کنند
- محدودیت نرخ درخواست برای هر کاربر
- API Key در لاگ یا پیام تلگرام ظاهر نمی‌شود
