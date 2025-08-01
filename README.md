# TCMB Döviz Kurları Takip Sistemi

Merkez Bankası'ndan günlük döviz kurlarını otomatik olarak çeken ve görselleştiren modern web uygulaması.

## 🚀 Özellikler

- **Otomatik Veri Çekme**: Her gün saat 04:00'da TCMB'den döviz kurlarını otomatik çeker
- **Modern Web Arayüzü**: React ile geliştirilmiş responsive tasarım
- **Gerçek Zamanlı Grafikler**: Recharts ile interaktif döviz kuru grafikleri
- **Veritabanı Saklama**: PostgreSQL ile güvenli veri saklama
- **Cache Sistemi**: Redis ile performans optimizasyonu
- **Docker Desteği**: Kolay kurulum ve dağıtım
- **API Endpoints**: RESTful API ile veri erişimi

## 📋 Gereksinimler

- Docker ve Docker Compose
- En az 4GB RAM
- İnternet bağlantısı (TCMB API erişimi için)

## 🛠️ Kurulum

### 1. Projeyi İndirin
```bash
git clone <repository-url>
cd doviz
```

### 2. Docker Compose ile Başlatın
```bash
docker-compose up -d
```

### 3. Servisleri Kontrol Edin
```bash
docker-compose ps
```

## 🌐 Erişim

- **Frontend**: http://localhost:3000
- **API**: http://localhost:5000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 📊 API Endpoints

### Sağlık Kontrolü
```http
GET /api/health
```

### Güncel Kurlar
```http
GET /api/rates/latest
```

### Geçmiş Veriler
```http
GET /api/rates/history?doviz_kodu=USD&start_date=2024-01-01&end_date=2024-01-31
```

### Manuel Güncelleme
```http
POST /api/rates/update
```

### İstatistikler
```http
GET /api/stats
```

## ⚙️ Konfigürasyon

### Environment Variables

`.env` dosyası oluşturarak aşağıdaki değişkenleri ayarlayabilirsiniz:

```env
# Veritabanı
DATABASE_URL=postgresql://doviz_user:doviz_password@postgres:5432/doviz_db

# Redis
REDIS_URL=redis://redis:6379

# TCMB API
TCMB_API_URL=https://evds2.tcmb.gov.tr/service/evds
TCMB_API_KEY=your_api_key_here
```

## 🔧 Geliştirme

### Backend Geliştirme
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Geliştirme
```bash
cd frontend
npm install
npm start
```

### Veritabanı Bağlantısı
```bash
docker exec -it doviz_db psql -U doviz_user -d doviz_db
```

## 📈 Scheduler

Scheduler servisi her gün saat 04:00'da (Türkiye saati) otomatik olarak çalışır:

- TCMB'den günlük döviz kurlarını çeker
- PostgreSQL veritabanına kaydeder
- Redis cache'ini temizler
- Log dosyalarını oluşturur

### Manuel Çalıştırma
```bash
docker exec -it doviz_scheduler python scheduler.py
```

## 📝 Loglar

Scheduler logları:
```bash
docker logs doviz_scheduler
```

API logları:
```bash
docker logs doviz_api
```

## 🔍 Sorun Giderme

### Servisler Başlamıyor
```bash
# Tüm servisleri durdur
docker-compose down

# Volume'ları temizle
docker-compose down -v

# Yeniden başlat
docker-compose up -d
```

### Veritabanı Bağlantı Hatası
```bash
# PostgreSQL container'ını kontrol et
docker logs doviz_db

# Veritabanı bağlantısını test et
docker exec -it doviz_db psql -U doviz_user -d doviz_db -c "SELECT 1;"
```

### API Hatası
```bash
# API loglarını kontrol et
docker logs doviz_api

# API sağlık kontrolü
curl http://localhost:5000/api/health
```

## 📊 Veritabanı Şeması

```sql
CREATE TABLE doviz_kurlari (
    id SERIAL PRIMARY KEY,
    tarih DATE NOT NULL,
    doviz_kodu VARCHAR(10) NOT NULL,
    doviz_adi VARCHAR(50) NOT NULL,
    alis_kuru FLOAT NOT NULL,
    satis_kuru FLOAT NOT NULL,
    efektif_alis FLOAT NOT NULL,
    efektif_satis FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tarih, doviz_kodu)
);
```

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 📞 İletişim

Sorularınız için cerengol21@gmail.com a mail atabilirsiniz.

---

**Not**: Bu uygulama TCMB'nin resmi API'sini kullanır. API kullanım koşullarına uygun kullanım yapılması gerekmektedir. 
