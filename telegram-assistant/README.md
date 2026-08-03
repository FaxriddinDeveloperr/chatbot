# 🤖 Shaxsiy AI Yordamchi Bot (Telegram Business)

Telegram Business'ning **Chatbots** funksiyasiga ulanadigan shaxsiy AI yordamchi.
Siz offline bo'lganingizda shaxsiy akkauntingizga kelgan xabarlarga **sizning
nomingizdan** javob yozadi. Bu userbot EMAS — rasmiy Bot API (`business_connection`)
orqali ishlaydi.

## Imkoniyatlar

- 🔌 Telegram Business ulanishi — javoblar sizning akkauntingizdan kelgandek ko'rinadi
- 🧠 Google Gemini (gemini-2.0-flash) — bilim bazangiz asosida javob yozadi
- 🟢/🔴 Online/offline: qo'lda (`/on`, `/off`) yoki avtomatik (15 daqiqa jimlik)
- ⭐ Ruxsat darajalari: whitelist (avto-javob), notanish (siz tasdiqlaysiz), blacklist
- ✅ Tasdiqlash oqimi: Yubor / Tahrirlash / Qayta yoz / Bekor / Whitelist'ga qo'sh
- 🌐 Til avtomatik aniqlanadi (uz/ru/en), javob o'sha tilda
- 🔊 Ovozli javob (edge-tts, rus/ingliz) va ovozli xabarni tushunish (Gemini STT)
- 📚 Bilim bazasi to'liq bot ichidan boshqariladi (`/knowledge`)
- 📊 Statistika, tarix, xatoliklar jurnali
- 🛡 Prompt injection himoyasi, rate limiting, "typing" bilan tabiiy kechikish

---

## 1. Botni yaratish (BotFather)

1. Telegram'da [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` yuboring → bot nomini kiriting (masalan: `Faxriddin Assistant`)
3. Username kiriting (masalan: `faxriddin_helper_bot`)
4. BotFather bergan **tokenni** nusxalang — `.env` dagi `BOT_TOKEN` ga yoziladi
5. **MUHIM:** `/mybots` → botingiz → **Bot Settings** → **Business Mode** → **Turn on**
   (busiz Telegram Business botni ko'rmaydi)

## 2. Gemini API kalitini olish

1. [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) ga kiring
2. Google akkauntingiz bilan login qiling
3. **Create API key** tugmasini bosing
4. Kalitni nusxalab `.env` dagi `GEMINI_API_KEY` ga yozing

Tekin tier yetarli: gemini-2.0-flash uchun kunlik limit shaxsiy foydalanish uchun
bemalol yetadi.

## 3. O'zingizning Telegram ID'ingizni olish

[@userinfobot](https://t.me/userinfobot) ga istalgan xabar yuboring — u sizning
ID raqamingizni aytadi. Uni `.env` dagi `OWNER_ID` ga yozing.

(Yoki: `.env` da `OWNER_ID=0` qoldirib botni ishga tushiring va botga `/start`
yozing — bot ID'ingizni o'zi aytadi.)

## 4. Lokal ishga tushirish (test uchun)

```bash
cd telegram-assistant

# Virtual muhit
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# ffmpeg kerak (ovozli javob uchun)
sudo apt install ffmpeg

# Sozlamalar
cp .env.example .env
nano .env        # BOT_TOKEN, OWNER_ID, GEMINI_API_KEY

# Ishga tushirish
python -m src.main
```

## 5. Telegram Business'ga ulash

**Talab:** Telegram Premium obunasi bo'lishi kerak (Business funksiyalari
Premium'da ochiladi).

1. Telegram → **Sozlamalar** → **Telegram Business** → **Chatbots**
2. Bot username'ini kiriting (masalan `@faxriddin_helper_bot`)
3. Bot qaysi chatlarda ishlashini tanlang (masalan: *All 1-to-1 Chats* yoki
   faqat ma'lum toifalar; **Exclude** bilan kerakli odamlarni chiqarib tashlash mumkin)
4. **Reply to messages** ruxsatini yoqing
5. Ulangach bot sizga "🔗 ...ulandim" deb yozadi

## 6. Serverga o'rnatish (Ubuntu / Amazon Lightsail)

```bash
# Loyihani serverga ko'chiring (lokal kompyuterdan):
scp -r telegram-assistant ubuntu@SERVER_IP:/home/ubuntu/

# Serverga kiring:
ssh ubuntu@SERVER_IP
cd /home/ubuntu/telegram-assistant

# Avtomatik o'rnatish (python, ffmpeg, venv, systemd):
bash deploy/setup.sh

# Kalitlarni kiriting:
nano .env

# Ishga tushirish:
sudo systemctl start assistant

# Holatni tekshirish / loglar:
sudo systemctl status assistant
sudo journalctl -u assistant -f
```

Bot server qayta yoqilganda ham avtomatik ishga tushadi (`systemctl enable`
allaqachon qilingan).

Yangilash:

```bash
cd /home/ubuntu/telegram-assistant
# yangi kodni ko'chirgach:
sudo systemctl restart assistant
```

## 7. Foydalanish

| Komanda | Vazifasi |
|---|---|
| `/start` | Bosh menyu (tugmalar bilan) |
| `/off` | Men offlaynman — **bot javob beradi** |
| `/on` | Men onlaynman — bot jim (avto-detektor davom etadi) |
| `/status` | Hozirgi holat |
| `/knowledge` | Bilim bazasi: bo'lim qo'shish/tahrirlash/o'chirish/tartib |
| `/people` | Whitelist / blacklist / notanishlar; qidiruv: `/people @username` |
| `/settings` | Auto-offline vaqti, ovoz, model, kontekst, kechikish |
| `/stats` | Bugun / hafta / oy statistikasi |
| `/history` | Oxirgi 10 ta javob |
| `/logs` | Oxirgi xatoliklar |
| `/schedule` | Xabarni ma'lum vaqtda yuborishni rejalashtirish |
| `/scheduled` | Rejalashtirilgan xabarlar ro'yxati (bekor qilish mumkin) |

### Ish mantiqi

1. Odam sizga yozadi → bot siz **offline** ekaningizni tekshiradi
   (qo'lda `/off` yoki 15 daqiqa jimlik)
2. **Whitelist**dagi odamga — javob avtomatik yuboriladi (typing + 3-8 soniya
   kechikish bilan, tabiiy ko'rinishi uchun)
3. **Notanish** odam uchun — bot javob tayyorlab **sizga tasdiqqa yuboradi**:
   ✅ Yubor · ✏️ Tahrirlash · 🔄 Qayta yoz · ❌ Bekor · ⭐ Whitelist'ga qo'sh
   (1 soatda javob bermasangiz so'rov bekor bo'ladi)
4. **Blacklist** — umuman javob yo'q
5. Siz istalgan chatga o'zingiz yozsangiz — bot darhol jim bo'ladi

### Xabarni rejalashtirish (/schedule)

Ikki yo'l bilan ishlaydi:

**1. Bitta xabarda hammasi** (qulay, Gemini orqali):

```
"Bahodirga va Abdulvahob akaga soat 10:00da: Salom, band edim, ertaga boraman"
```

**2. Bosqichma-bosqich** (kafolatlangan, AI ishlatilmaydi) — agar (1) ishlamasa
(AI band/kvota tugagan) yoki shunchaki ism yozsangiz, avtomatik shu rejimga
o'tiladi:

1. **Kimga?** — ism-familiya yoki `@username` (bir nechta bo'lsa vergul bilan:
   `Bahodir, @aziza_k`)
2. **Qachon?** — `14:00` | `bugun 18:30` | `ertaga 09:00` | `05.08 14:00` |
   `30 daqiqadan keyin`
3. **Nima deb yozay?** — xabar matni

Ism qidiruvi imlo xatolariga chidamli (masalan "Abdulvahhob" ↔ "Abdulvahob").

- Ism bir nechta odamga mos kelsa — kimni nazarda tutganingizni so'raydi
- Yuborishdan oldin har doim tasdiq so'raladi (✅/❌)
- Bot qayta ishga tushsa ham (server qayta yuklansa) rejalashtirilgan
  xabarlar yo'qolmaydi — bazadan qayta yuklanadi
- `/scheduled` — kutayotgan xabarlar ro'yxati, har birini bekor qilish tugmasi bilan

**Cheklov:** bot faqat avval sizga Business orqali yozgan odamlarga xabar
yubora oladi (`/people` ro'yxatidagilar) — Telegram hali suhbat boshlamagan
odamga botning/business ulanishning birinchi bo'lib yozishiga ruxsat bermaydi.

### Ovozli xabarlar

- Kelgan ovozli xabarlar Gemini orqali matnga aylantiriladi va tushunilib javob beriladi
- Rus/ingliz tilidagi javoblar ovozli yuborilishi mumkin (odam ovozli yozgan
  bo'lsa yoki javob 300 belgidan uzun bo'lsa — `/settings` da sozlanadi)
- O'zbek tili — hozircha faqat matn (keyinchalik ElevenLabs ulanadi:
  `src/tts/elevenlabs.py` yozib, `.env` da `TTS_PROVIDER=elevenlabs`)

## 8. Fayl tuzilmasi

```
telegram-assistant/
├── .env.example          # sozlamalar namunasi (izohlar bilan)
├── requirements.txt
├── deploy/
│   ├── assistant.service # systemd unit
│   └── setup.sh          # serverga o'rnatish skripti
├── src/
│   ├── main.py           # kirish nuqtasi
│   ├── config.py         # .env o'qish
│   ├── database/         # SQLAlchemy modellar, seed, so'rovlar
│   ├── handlers/         # business, komandalar, tasdiqlash, menyular
│   ├── services/         # Gemini, prompt, presence, rate limit
│   ├── tts/              # ovoz sintezi (abstraksiya + edge-tts)
│   ├── stt/              # ovozni tushunish (abstraksiya + Gemini)
│   └── utils/            # klaviaturalar, logger
└── data/
    └── bot.db            # SQLite baza (avtomatik yaratiladi)
```

## Muammolarni hal qilish

- **Bot business xabarlarni ko'rmayapti** — BotFather'da Business Mode
  yoqilganini va Telegram Business → Chatbots'da bot ulanganini tekshiring.
  Telegram Premium faol bo'lishi shart.
- **"GEMINI_API_KEY yo'q" ogohlantirishi** — `.env` faylni tekshiring, botni
  qayta ishga tushiring.
- **Ovoz yuborilmayapti** — serverda `ffmpeg` o'rnatilganini tekshiring:
  `ffmpeg -version`. Bo'lmasa bot avtomatik matn yuboradi.
- **Xatoliklarni ko'rish** — `/logs` komandasi yoki
  `sudo journalctl -u assistant -f`.
