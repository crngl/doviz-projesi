import os
import sys
import time
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
import requests
import xml.etree.ElementTree as ET
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis

# Logging konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Veritabanı bağlantısı
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://doviz_user:doviz_password@localhost:5432/doviz_db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis bağlantısı
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# Türkiye saati
turkey_tz = pytz.timezone('Europe/Istanbul')

class TCMBDataCollector:
    def __init__(self):
        self.base_url = "https://www.tcmb.gov.tr/kurlar"
    
    def get_daily_rates(self, date=None):
        """TCMB'den günlük döviz kurlarını çeker"""
        if not date:
            date = datetime.now(turkey_tz).strftime('%d%m%Y')
        
        year = date[:4]
        month = date[4:6]
        
        url = f"{self.base_url}/{year}/{month}/{date}.xml"
        
        try:
            logger.info(f"TCMB'den veri çekiliyor: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # XML'i parse et
            root = ET.fromstring(response.content)
            
            rates = []
            for currency in root.findall('.//Currency'):
                code = currency.get('Kod')
                name = currency.find('Isim').text
                
                # Sayısal değerleri güvenli şekilde al
                forex_buying = self._safe_float(currency.find('ForexBuying').text)
                forex_selling = self._safe_float(currency.find('ForexSelling').text)
                banknote_buying = self._safe_float(currency.find('BanknoteBuying').text)
                banknote_selling = self._safe_float(currency.find('BanknoteSelling').text)
                
                if forex_buying > 0:  # Sadece geçerli kurları al
                    rates.append({
                        'doviz_kodu': code,
                        'doviz_adi': name,
                        'alis_kuru': forex_buying,
                        'satis_kuru': forex_selling,
                        'efektif_alis': banknote_buying,
                        'efektif_satis': banknote_selling
                    })
            
            logger.info(f"{len(rates)} adet döviz kuru çekildi")
            return rates
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TCMB API hatası: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"XML parse hatası: {e}")
            return []
        except Exception as e:
            logger.error(f"Beklenmeyen hata: {e}")
            return []
    
    def _safe_float(self, value):
        """Güvenli float dönüşümü"""
        try:
            return float(value) if value else 0.0
        except (ValueError, TypeError):
            return 0.0

class DatabaseManager:
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def save_rates(self, rates, date):
        """Döviz kurlarını veritabanına kaydet"""
        session = self.SessionLocal()
        
        try:
            saved_count = 0
            
            for rate_data in rates:
                # Veritabanında var mı kontrol et
                existing = session.execute(
                    text("SELECT id FROM doviz_kurlari WHERE tarih = :tarih AND doviz_kodu = :doviz_kodu"),
                    {"tarih": date, "doviz_kodu": rate_data['doviz_kodu']}
                ).first()
                
                if not existing:
                    # Yeni kayıt ekle
                    session.execute(
                        text("""
                            INSERT INTO doviz_kurlari 
                            (tarih, doviz_kodu, doviz_adi, alis_kuru, satis_kuru, efektif_alis, efektif_satis, created_at)
                            VALUES (:tarih, :doviz_kodu, :doviz_adi, :alis_kuru, :satis_kuru, :efektif_alis, :efektif_satis, :created_at)
                        """),
                        {
                            "tarih": date,
                            "doviz_kodu": rate_data['doviz_kodu'],
                            "doviz_adi": rate_data['doviz_adi'],
                            "alis_kuru": rate_data['alis_kuru'],
                            "satis_kuru": rate_data['satis_kuru'],
                            "efektif_alis": rate_data['efektif_alis'],
                            "efektif_satis": rate_data['efektif_satis'],
                            "created_at": datetime.now()
                        }
                    )
                    saved_count += 1
            
            session.commit()
            logger.info(f"{saved_count} yeni döviz kuru kaydedildi")
            
            # Cache'i temizle
            redis_client.delete('latest_rates')
            
            return saved_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Veritabanı hatası: {e}")
            return 0
        finally:
            session.close()

def collect_daily_rates():
    """Günlük döviz kurlarını topla ve kaydet"""
    logger.info("Günlük döviz kuru toplama işlemi başladı")
    
    collector = TCMBDataCollector()
    db_manager = DatabaseManager()
    
    # Bugünün tarihi
    today = datetime.now(turkey_tz).date()
    
    # TCMB'den veri çek
    rates = collector.get_daily_rates()
    
    if rates:
        # Veritabanına kaydet
        saved_count = db_manager.save_rates(rates, today)
        logger.info(f"İşlem tamamlandı. {saved_count} yeni kayıt eklendi.")
    else:
        logger.warning("TCMB'den veri çekilemedi")

def main():
    """Ana scheduler fonksiyonu"""
    logger.info("Döviz kuru scheduler başlatılıyor...")
    
    scheduler = BlockingScheduler(timezone=turkey_tz)
    
    # Her gün saat 04:00'da çalıştır
    scheduler.add_job(
        collect_daily_rates,
        CronTrigger(hour=4, minute=0, timezone=turkey_tz),
        id='daily_rate_collection',
        name='Günlük döviz kuru toplama',
        replace_existing=True
    )
    
    # Test modu için (geliştirme sırasında kullanılabilir)
    # scheduler.add_job(
    #     collect_daily_rates,
    #     'interval',
    #     minutes=1,
    #     id='test_collection',
    #     name='Test toplama',
    #     replace_existing=True
    # )
    
    logger.info("Scheduler başlatıldı. Her gün saat 04:00'da çalışacak.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler durduruluyor...")
        scheduler.shutdown()

if __name__ == "__main__":
    main() 