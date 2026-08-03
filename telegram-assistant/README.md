# 📅 Xabar Rejalashtiruvchi Bot (Telegram Business)

Telegram Business'ning **Chatbots** funksiyasiga ulanadigan shaxsiy vosita —
sizga avval Business orqali yozgan odamlarga xabarni **ma'lum vaqtda**
yuborishni rejalashtirasiz. Bu userbot EMAS — rasmiy Bot API
(`business_connection`) orqali ishlaydi.

## Imkoniyatlar

- 📅 `/schedule` — kimga, qachon, nima deb yozishni rejalashtirish
  - Hammasini bitta xabarda yozish mumkin (Gemini yordamida tez tahlil qilinadi)
  - Yoki bosqichma-bosqich (kimga → qachon → nima) — **AI ishlatilmaydi**,
    shuning uchun Gemini kvotasi tugab qolsa ham 100% ishlayveradi
  - Ism qidiruvi imlo xatolariga chidamli (masalan "Abdulvahhob" ↔ "Abdulvahob")
  - Bir nechta odamga bitta xabar
  - Bot qayta ishga tushsa ham rejalashtirilgan xabarlar yo'qolmaydi
- 🗓 `/scheduled` — kutayotgan xabarlar ro'yxati, har birini bekor qilish
- 📜 `/history` — yuborilgan xabarlar tarixi
- ⚙️ `/settings` — Gemini modelini tanlash
- 🐞 `/logs` — xatoliklar jurnali

---

## 1. Botni yaratish (BotFather)

1. Telegram'da [@BotFather](https://t.me/BotFather) ga kiring
2. `/newbot` yuboring → bot nomini kiriting
3. Username kiriting
4. BotFather bergan **tokenni** nusxalang — `.env` dagi `BOT_TOKEN` ga yoziladi
5. **MUHIM:** `/mybots` → botingiz → **Bot Settings** → **Business Mode** → **Turn on**
   (busiz Telegram Business botni ko'rmaydi)

## 2. Gemini API kalitini olish (ixtiyoriy)

`/schedule`ning bitta xabarda tahlil qilish qulayligi uchun kerak — bo'lmasa
ham bosqichma-bosqich rejim baribir to'liq ishlayveradi.

1. [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) ga kiring
2. Google akkauntingiz bilan login qiling
3. **Create API key** tugmasini bosing
4. Kalitni nusxalab `.env` dagi `GEMINI_API_KEY` ga yozing

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

# Sozlamalar
cp .env.example .env
nano .env        # BOT_TOKEN, OWNER_ID, (ixtiyoriy) GEMINI_API_KEY

# Ishga tushirish
python -m src.main
```

## 5. Telegram Business'ga ulash

**Talab:** Telegram Premium obunasi bo'lishi kerak (Business funksiyalari
Premium'da ochiladi).

1. Telegram → **Sozlamalar** → **Telegram Business** → **Chatbots**
2. Bot username'ini kiriting
3. Bot qaysi chatlarda ishlashini tanlang (masalan: *All 1-to-1 Chats*)
4. **Reply to messages** ruxsatini yoqing
5. Ulangach bot sizga "🔗 ...ulandim" deb yozadi

Ulanish paytida (va undan keyin ham) sizga yozgan odamlar avtomatik
"kontakt" sifatida yozib boriladi — `/schedule` ularni shundan qidiradi.

## 6. Serverga o'rnatish (Ubuntu / Amazon Lightsail)

```bash
# Loyihani serverga ko'chiring (lokal kompyuterdan):
scp -r telegram-assistant ubuntu@SERVER_IP:/home/ubuntu/

# Serverga kiring:
ssh ubuntu@SERVER_IP
cd /home/ubuntu/telegram-assistant

# Avtomatik o'rnatish (python, venv, systemd):
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
| `/schedule` | Xabarni ma'lum vaqtda yuborishni rejalashtirish |
| `/scheduled` | Rejalashtirilgan xabarlar ro'yxati (bekor qilish mumkin) |
| `/history` | Yuborilgan xabarlar tarixi |
| `/settings` | Gemini modelini tanlash |
| `/logs` | Oxirgi xatoliklar |

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

**Cheklov:** bot faqat avval sizga Business orqali yozgan odamlarga xabar
yubora oladi — Telegram hali suhbat boshlamagan odamga botning/business
ulanishning birinchi bo'lib yozishiga ruxsat bermaydi.

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
│   ├── handlers/         # business (kontakt yozish), rejalashtirish, menyular
│   ├── services/         # Gemini klienti, rejalashtirish mantiqi, sozlamalar
│   └── utils/            # klaviaturalar, logger
└── data/
    └── bot.db            # SQLite baza (avtomatik yaratiladi)
```

## Muammolarni hal qilish

- **Bot business xabarlarni ko'rmayapti** — BotFather'da Business Mode
  yoqilganini va Telegram Business → Chatbots'da bot ulanganini tekshiring.
  Telegram Premium faol bo'lishi shart.
- **/schedule odamni topa olmayapti** — o'sha odam avval sizga Business orqali
  hech bo'lmasa bitta xabar yozgan bo'lishi kerak (shundagina kontakt
  sifatida saqlanadi).
- **"Business_peer_invalid" xatosi** — bu kod xatosi emas, Telegram'ning o'zi
  shu aniq chat uchun bot ruxsatini o'chirgan bo'lishi mumkin. Odam bilan
  suhbatni ochib, bot ruxsati yoqilganini tekshiring.
- **Xatoliklarni ko'rish** — `/logs` komandasi yoki
  `sudo journalctl -u assistant -f`.
