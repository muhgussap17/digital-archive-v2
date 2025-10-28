# Sistem Arsip Digital

Aplikasi web untuk mendigitalkan dan mengelola dokumen PDF institusi pemerintah.

## 📋 Fitur Utama

- ✅ Upload dokumen PDF dengan metadata
- ✅ Kategorisasi otomatis (SPD, Belanjaan: ATK, Konsumsi, BBM, dll)
- ✅ Penamaan file otomatis dengan format standar
- ✅ Pencarian dan filter dokumen
- ✅ Manajemen data pegawai untuk SPD
- ✅ Jejak audit aktivitas dokumen
- ✅ Dashboard statistik
- ✅ Backup otomatis
- ✅ Responsive design (Bootstrap Argon)

## 🛠️ Tech Stack

- **Backend:** Django 4.2
- **Database:** PostgreSQL
- **Frontend:** Bootstrap 4 Argon v1.2.1
- **API:** Django REST Framework

## 📦 Instalasi

### 1. Prerequisites

- Python 3.9+
- PostgreSQL 12+
- pip
- virtualenv

### 2. Clone Repository

```bash
git clone <repository-url>
cd arsip_digital
```

### 3. Buat Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Setup Database

Buat database PostgreSQL:

```sql
CREATE DATABASE arsip_digital;
CREATE USER arsip_user WITH PASSWORD 'your_password';
ALTER ROLE arsip_user SET client_encoding TO 'utf8';
ALTER ROLE arsip_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE arsip_user SET timezone TO 'Asia/Jakarta';
GRANT ALL PRIVILEGES ON DATABASE arsip_digital TO arsip_user;
```

### 6. Konfigurasi Environment

Salin file `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

Edit `.env` dan sesuaikan konfigurasi:

```env
SECRET_KEY=generate-random-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=arsip_digital
DB_USER=arsip_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

**Generate SECRET_KEY:**

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 7. Migrasi Database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 8. Load Initial Data

```bash
python manage.py loaddata initial_categories.json
```

### 9. Buat Superuser

```bash
python manage.py createsuperuser
```

### 10. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 11. Jalankan Development Server

```bash
python manage.py runserver
```

Akses aplikasi di: `http://localhost:8000`

## 👥 Manajemen Data Pegawai

Setelah login sebagai superuser:

1. Akses Admin Panel: `http://localhost:8000/admin`
2. Buka menu **Pegawai**
3. Tambahkan data pegawai dengan NIP dan nama lengkap

## 📤 Upload Dokumen

### Upload Dokumen Belanjaan

1. Klik tombol **"Upload Dokumen"**
2. Pilih kategori (ATK, Konsumsi, BBM, dll)
3. Isi tanggal dokumen
4. Upload file PDF
5. Judul dokumen akan otomatis: `Kategori - DD MMMM YYYY`
6. File akan dinamai: `Kategori_YYYY-MM-DD.pdf`

### Upload Dokumen SPD

1. Klik tombol **"Upload SPD"**
2. Pilih pegawai dari dropdown
3. Pilih tujuan perjalanan
4. Isi tanggal mulai dan selesai
5. Upload file PDF
6. Judul dokumen akan otomatis: `SPD - NamaPegawai → Tujuan (DD MMMM YYYY)`
7. File akan dinamai: `SPD_NamaPegawai_Tujuan_YYYY-MM-DD.pdf`

## 🔍 Pencarian & Filter

- **Search Bar:** Cari berdasarkan nama pegawai, tujuan, atau kategori
- **Filter Kategori:** Sidebar menu kategori
- **Filter Tanggal:** Range tanggal dokumen
- **Filter Pegawai:** Khusus untuk dokumen SPD

**Note:** Judul dokumen di-generate otomatis dari metadata, tidak perlu input manual.

## 💾 Backup

### Manual Backup

```bash
# Backup database dan files
python manage.py backup_documents

# Backup dengan retention 60 hari
python manage.py backup_documents --retention-days 60
```

### Otomatis Backup (Cron Job)

Tambahkan ke crontab (Linux):

```bash
# Backup setiap hari jam 02:00
0 2 * * * cd /path/to/arsip_digital && /path/to/venv/bin/python manage.py backup_documents
```

Windows Task Scheduler:

```batch
cd C:\path\to\arsip_digital
C:\path\to\venv\Scripts\python.exe manage.py backup_documents
```

## 🧹 Maintenance

### Cleanup Dokumen Terhapus

```bash
# Dry run (lihat apa yang akan dihapus)
python manage.py cleanup_deleted --days 90 --dry-run

# Hapus permanent dokumen yang dihapus >90 hari
python manage.py cleanup_deleted --days 90
```

### Generate Laporan

```bash
# Laporan bulan ini
python manage.py generate_report

# Laporan bulan tertentu
python manage.py generate_report --month 2024-01 --output report_jan2024.csv
```

## 🚀 Deployment (Production)

### 1. Update Settings

```python
# config/settings.py
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com']
```

### 2. Gunakan Gunicorn

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 3. Setup Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /static/ {
        alias /path/to/arsip_digital/staticfiles/;
    }

    location /media/ {
        alias /path/to/arsip_digital/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Setup Systemd Service (Linux)

```ini
# /etc/systemd/system/arsip_digital.service
[Unit]
Description=Arsip Digital Django App
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/arsip_digital
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable arsip_digital
sudo systemctl start arsip_digital
```

## 📊 API Documentation

API endpoint tersedia di: `http://localhost:8000/api/`

### Endpoints:

- `GET /api/documents/` - List dokumen
- `POST /api/documents/` - Upload dokumen
- `GET /api/documents/{id}/` - Detail dokumen
- `GET /api/documents/{id}/download/` - Download dokumen
- `GET /api/categories/` - List kategori
- `GET /api/spd/` - List SPD
- `GET /api/dashboard/stats/` - Dashboard statistics

## 🔐 User Roles

- **Superuser:** Full access (admin panel + semua fitur)
- **Staff:** Upload, view, download dokumen
- **Regular User:** View dan download dokumen

## 📝 Format Penamaan File

### SPD:
```
SPD_JohnDoe_Jakarta_2024-01-15.pdf
SPD_JaneSmith_Surabaya_2024-02-20.pdf
```

### Belanjaan:
```
ATK_2024-01-15.pdf
Konsumsi_2024-01-20.pdf
BBM_2024-01-25.pdf
```

## 🗂️ Struktur Folder Upload

```
media/uploads/
├── spd/
│   └── 2024/
│       ├── 01-January/
│       │   └── SPD_JohnDoe_Jakarta_2024-01-15.pdf
│       └── 02-February/
│           └── SPD_JaneSmith_Surabaya_2024-02-05.pdf
└── belanjaan/
    ├── atk/
    │   └── 2024/
    │       └── 01-January/
    │           └── ATK_2024-01-10.pdf
    ├── konsumsi/
    └── bbm/
```

## ⚠️ Troubleshooting

### Error: locale not supported

Jika Indonesian locale tidak tersedia:

```bash
# Linux
sudo locale-gen id_ID.UTF-8
sudo update-locale

# Windows
# Indonesian locale biasanya sudah tersedia
```

### Error: PostgreSQL connection

Pastikan PostgreSQL service berjalan:

```bash
# Linux
sudo systemctl status postgresql

# Windows
# Cek di Services
```

### Error: Permission denied (media folder)

```bash
# Linux
chmod -R 755 media/
chown -R www-data:www-data media/
```

## 📞 Support

Untuk bantuan lebih lanjut, hubungi administrator sistem.

## 📄 License

Proprietary - Internal Use Only