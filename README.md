# 💰 Telegram Profit Tracker Bot

Bot Telegram untuk tracking profit harian, mingguan & bulanan di group.

## ✨ Fitur

- **Track Profit/Loss** — Otomatis mendeteksi `+5k`, `-2k`, dll
- **Per-Group Tracking** — Setiap group punya data terpisah
- **Keterangan** — Tambahkan catatan: `+5k netflix`
- **Multi Periode** — Harian, mingguan, bulanan
- **PostgreSQL** — Data aman, tidak hilang saat deploy ulang
- **Aesthetic Output** — Tampilan Unicode aesthetic

## 📋 Format Input

| Format | Contoh | Hasil |
|--------|--------|-------|
| `+Xk` | `+2k` | +Rp. 2.000 |
| `+Xrb` / `+Xribu` | `+2rb` | +Rp. 2.000 |
| `+Xjt` / `+Xjuta` | `+2jt` | +Rp. 2.000.000 |
| `+X` | `+5000` | +Rp. 5.000 |
| `-Xk` | `-1k` | -Rp. 1.000 |
| `+Xk catatan` | `+5k netflix` | +Rp. 5.000 (netflix) |

## 📱 Commands (pakai titik `.`)

| Command | Alias | Deskripsi |
|---------|-------|-----------|
| `.start` / `.help` | — | Panduan penggunaan |
| `.status` | — | Status profit lengkap |
| `.daily` | `.harian` | Profit hari ini |
| `.weekly` | `.mingguan` | Profit minggu ini |
| `.monthly` | `.bulanan` | Profit bulan ini |
| `.history` | `.riwayat` | Riwayat transaksi |
| `.reset` | — | Reset semua data grup |

## 🚀 Cara Setup

### 1. Buat Bot di Telegram

1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`, ikuti instruksi
3. Copy **token** yang diberikan

### 2. Deploy ke Railway

1. Push kode ini ke **GitHub**
2. Buka [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Tambah **PostgreSQL**: klik **"+ New"** → **"Database"** → **"Add PostgreSQL"**
4. Set **Environment Variables** di service bot:
   - `BOT_TOKEN` = token dari BotFather
   - `DATABASE_URL` = reference dari PostgreSQL service (biasanya otomatis)
5. Deploy! ✅

### 3. Tambahkan Bot ke Group

1. Tambahkan bot ke group Telegram
2. Jadikan bot sebagai admin, atau matikan Group Privacy di @BotFather (`/setprivacy` → Disable)
3. Bot siap digunakan!

## 💡 Contoh Penggunaan

```
User: +5k netflix
Bot:
⟡ ─────────────────── ⟡
   💰 𝑷𝑹𝑶𝑭𝑰𝑻 𝑼𝑷𝑫𝑨𝑻𝑬
⟡ ─────────────────── ⟡

   ꒰ 👤 ꒱  John
   ꒰ 💸 ꒱  +Rp. 5.000
   ꒰ 📋 ꒱  netflix

   ┊ 📆 Today    ➜  Rp. 5.000
   ┊ 📅 Week     ➜  Rp. 5.000
   ┊ 🗓 Februari  ➜  Rp. 5.000

⟡ ─────────────────── ⟡
```

## ⚙️ Jalankan Lokal (Opsional)

```bash
pip install -r requirements.txt
export BOT_TOKEN=your_token_here
export DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
python profit_bot.py
```

## 📝 Catatan

- Data disimpan di **PostgreSQL** (aman saat re-deploy)
- Setiap group Telegram punya data **terpisah**
- Bot harus running terus menerus
- Untuk hosting, gunakan Railway (free trial $5/bulan)
