# MAGNATRIX — Panduan Deploy ke Hostinger VPS

## Informasi Server

| Parameter | Nilai |
|---|---|
| Host | `72.61.211.141` |
| SSH Port | `65002` |
| SSH User | `u721595593` |
| FTP Host | `72.61.211.141` |
| FTP User | `u721595593` |

## Database MySQL

| Parameter | Nilai |
|---|---|
| phpMyAdmin | https://auth-db1867.hstgr.io |
| DB Name | `u721595593_TfDUU` |
| DB User | `u721595593_z8x9N` |
| Host | `auth-db1867.hstgr.io` |
| Port | `3306` |

## Cara Deploy

### 1. Setup Pertama Kali di VPS

```bash
ssh -p 65002 u721595593@72.61.211.141

# Install Docker & Docker Compose
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# Buat direktori
mkdir -p /opt/magnatrix && cd /opt/magnatrix

# Clone repo
git clone https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git .

# Buat .env (ganti PASSWORD dengan password sebenarnya)
cat > .env << 'EOF'
MAGNATRIX_ENV=production
SECRET_KEY=ganti-dengan-secret-32-char
MAGNATRIX_DB_URL=mysql+pymysql://u721595593_z8x9N:PASSWORD@auth-db1867.hstgr.io:3306/u721595593_TfDUU?charset=utf8mb4
MAGNATRIX_REDIS_URL=redis://redis:6379
EOF

# Jalankan
docker-compose -f infrastructure/docker/docker-compose.hostinger.yml up -d
```

### 2. Auto Deploy via GitHub Actions

Tambahkan secrets ke GitHub repository:

| Secret | Deskripsi |
|---|---|
| `HOSTINGER_SSH_KEY` | Private key SSH (generate dengan `ssh-keygen`) |
| `HOSTINGER_DB_PASSWORD` | Password database MySQL |
| `HOSTINGER_FTP_PASSWORD` | Password FTP (optional) |
| `MAG_SECRET_KEY` | Secret key aplikasi MAGNATRIX |
| `OPENAI_KEY` | API key OpenAI |
| `ANTHROPIC_KEY` | API key Anthropic |
| `GROQ_KEY` | API key Groq |
| `BINANCE_KEY` | API key Binance |
| `BINANCE_SECRET` | Secret Binance |
| `GH_TOKEN` | GitHub token |

Push ke branch `main` akan otomatis trigger deploy.

### 3. Manual Deploy via FTP (Fallback)

Jika SSH tidak tersedia, upload file via FTP:

```bash
lftp -u u721595593,PASSWORD 72.61.211.141 << 'EOF'
mirror -R . /public_html/magnatrix
EOF
```

### 4. Setup SSH Key untuk CI/CD

Di VPS:
```bash
ssh -p 65002 u721595593@72.61.211.141
mkdir -p ~/.ssh && chmod 700 ~/.ssh
cat > ~/.ssh/authorized_keys
# Paste public key dari GitHub Actions
chmod 600 ~/.ssh/authorized_keys
```

### 5. Health Check

Setelah deploy, cek service:
```bash
curl http://72.61.211.141:8080/health
curl http://72.61.211.141:8081/status  # P2P mesh
```

## Struktur Service di Hostinger

```
72.61.211.141:8080  → MAGNATRIX Core API
72.61.211.141:8081  → P2P Mesh Node
72.61.211.141:8082  → Web Dashboard
72.61.211.141:6379  → Redis (internal)
```

## Troubleshooting

| Masalah | Solusi |
|---|---|
| Docker tidak jalan | `sudo systemctl start docker` |
| Port tidak terbuka | Cek firewall Hostinger panel |
| DB connection error | Verifikasi password di `.env` |
| Out of memory | VPS Hostinger shared hosting limit — naikkan plan atau turunkan `memory` di compose |

## Catatan Keamanan

- **Jangan commit `.env` atau password ke GitHub**
- `.env.example` hanya berisi placeholder
- Semua password disimpan sebagai GitHub Secrets
- Rotate password secara berkala di panel Hostinger
