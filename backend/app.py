from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import redis
import requests
import pandas as pd
import json
from sqlalchemy import text

app = Flask(__name__)
CORS(app)

# Konfigürasyon
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://doviz_user:doviz_password@localhost:5432/doviz_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Redis bağlantısı
try:
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    redis_client.ping()  
except Exception as e:
    print(f"Redis bağlantı hatası: {e}")
    redis_client = None

# Veritabanı
db = SQLAlchemy(app)

# Veri modeli
class DovizKuru(db.Model):
    __tablename__ = 'doviz_kurlari'
    
    id = db.Column(db.Integer, primary_key=True)
    tarih = db.Column(db.Date, nullable=False)
    doviz_kodu = db.Column(db.String(10), nullable=False)
    doviz_adi = db.Column(db.String(50), nullable=False)
    alis_kuru = db.Column(db.Float, nullable=False)
    satis_kuru = db.Column(db.Float, nullable=False)
    efektif_alis = db.Column(db.Float, nullable=False)
    efektif_satis = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('tarih', 'doviz_kodu', name='unique_tarih_doviz'),)

# TCMB API servisi
class TCMBService:
    def __init__(self):
        self.base_url = os.getenv('TCMB_API_URL', 'https://evds2.tcmb.gov.tr/service/evds')
        self.api_key = os.getenv('TCMB_API_KEY', '')
    
    def get_daily_rates(self, date=None):
        """Günlük döviz kurlarını çeker"""
        try:
            # TCMB'nin güncel API endpoint'i - today.xml kullan
            url = "https://www.tcmb.gov.tr/kurlar/today.xml"
            
            print(f"TCMB API'ye istek gönderiliyor: {url}")
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response.raise_for_status()
            
            # XML'i parse et
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
            
            rates = []
            for currency in root.findall('.//Currency'):
                code = currency.get('Kod')
                name = currency.find('Isim').text
                
                # Güvenli float dönüşümü
                try:
                    forex_buying = float(currency.find('ForexBuying').text or 0)
                    forex_selling = float(currency.find('ForexSelling').text or 0)
                    banknote_buying = float(currency.find('BanknoteBuying').text or 0)
                    banknote_selling = float(currency.find('BanknoteSelling').text or 0)
                except (ValueError, TypeError):
                    continue
                
                if forex_buying > 0:  # Sadece geçerli kurları al
                    rates.append({
                        'doviz_kodu': code,
                        'doviz_adi': name,
                        'alis_kuru': forex_buying,
                        'satis_kuru': forex_selling,
                        'efektif_alis': banknote_buying,
                        'efektif_satis': banknote_selling
                    })
            
            print(f"{len(rates)} adet döviz kuru çekildi")
            return rates
            
        except requests.exceptions.RequestException as e:
            print(f"TCMB API bağlantı hatası: {e}")
            # Test için mock data döndür
            return self._get_mock_rates()
        except Exception as e:
            print(f"TCMB API genel hata: {e}")
            return self._get_mock_rates()
    
    def _get_mock_rates(self):
        """Test için mock döviz kurları"""
        print("Mock veri kullanılıyor...")
        return [
            {
                'doviz_kodu': 'USD',
                'doviz_adi': 'US DOLLAR',
                'alis_kuru': 32.50,
                'satis_kuru': 32.60,
                'efektif_alis': 32.45,
                'efektif_satis': 32.65
            },
            {
                'doviz_kodu': 'EUR',
                'doviz_adi': 'EURO',
                'alis_kuru': 35.20,
                'satis_kuru': 35.30,
                'efektif_alis': 35.15,
                'efektif_satis': 35.35
            },
            {
                'doviz_kodu': 'GBP',
                'doviz_adi': 'POUND STERLING',
                'alis_kuru': 41.80,
                'satis_kuru': 41.90,
                'efektif_alis': 41.75,
                'efektif_satis': 41.95
            }
        ]

tcmb_service = TCMBService()

# API Endpoints
@app.route('/api/health', methods=['GET'])
def health_check():
    """Sağlık kontrolü"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/rates/latest', methods=['GET'])
def get_latest_rates():
    """En son döviz kurlarını getir"""
    try:
        # Cache'den kontrol et
        if redis_client:
            cache_key = 'latest_rates'
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                return jsonify({'data': json.loads(cached_data), 'source': 'cache'})
        
        # Veritabanından en son tarihi alıyor
        latest_date = db.session.query(db.func.max(DovizKuru.tarih)).scalar()
        
        if not latest_date:
            return jsonify({'error': 'Veri bulunamadı'}), 404
        
        rates = DovizKuru.query.filter_by(tarih=latest_date).all()
        
        result = []
        for rate in rates:
            result.append({
                'tarih': rate.tarih.strftime('%Y-%m-%d'),
                'doviz_kodu': rate.doviz_kodu,
                'doviz_adi': rate.doviz_adi,
                'alis_kuru': rate.alis_kuru,
                'satis_kuru': rate.satis_kuru,
                'efektif_alis': rate.efektif_alis,
                'efektif_satis': rate.efektif_satis
            })
        
        
        if redis_client:
            redis_client.setex(cache_key, 300, json.dumps(result))
        
        return jsonify({'data': result, 'source': 'database'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rates/history', methods=['GET'])
def get_rate_history():
    """Döviz kuru geçmişini getir"""
    try:
        doviz_kodu = request.args.get('doviz_kodu', 'USD')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = DovizKuru.query.filter_by(doviz_kodu=doviz_kodu)
        
        if start_date:
            query = query.filter(DovizKuru.tarih >= start_date)
        if end_date:
            query = query.filter(DovizKuru.tarih <= end_date)
        
        rates = query.order_by(DovizKuru.tarih.desc()).limit(100).all()
        
        result = []
        for rate in rates:
            result.append({
                'tarih': rate.tarih.strftime('%Y-%m-%d'),
                'doviz_kodu': rate.doviz_kodu,
                'doviz_adi': rate.doviz_adi,
                'alis_kuru': rate.alis_kuru,
                'satis_kuru': rate.satis_kuru,
                'efektif_alis': rate.efektif_alis,
                'efektif_satis': rate.efektif_satis
            })
        
        return jsonify({'data': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rates/update', methods=['POST'])
def update_rates():
    """Manuel olarak döviz kurlarını güncelle"""
    try:
        # TCMB'den veri çek
        rates = tcmb_service.get_daily_rates()
        
        if not rates:
            return jsonify({'error': 'TCMB\'den veri çekilemedi'}), 500
        
        today = datetime.now().date()
        saved_count = 0
        
        for rate_data in rates:
            # Veritabanında var mı kontrol et
            existing = DovizKuru.query.filter_by(
                tarih=today, 
                doviz_kodu=rate_data['doviz_kodu']
            ).first()
            
            if not existing:
                new_rate = DovizKuru(
                    tarih=today,
                    doviz_kodu=rate_data['doviz_kodu'],
                    doviz_adi=rate_data['doviz_adi'],
                    alis_kuru=rate_data['alis_kuru'],
                    satis_kuru=rate_data['satis_kuru'],
                    efektif_alis=rate_data['efektif_alis'],
                    efektif_satis=rate_data['efektif_satis']
                )
                db.session.add(new_rate)
                saved_count += 1
        
        db.session.commit()
        
        # Cache'i temizle
        if redis_client:
            redis_client.delete('latest_rates')
        
        return jsonify({
            'message': f'{saved_count} yeni kur kaydedildi',
            'date': today.strftime('%Y-%m-%d')
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """İstatistikleri getir"""
    try:
        # Toplam kayıt sayısı
        total_records = DovizKuru.query.count()
        
        # En son güncelleme tarihi
        last_update = db.session.query(db.func.max(DovizKuru.created_at)).scalar()
        
        # Mevcut döviz kodları
        currencies = db.session.query(DovizKuru.doviz_kodu, DovizKuru.doviz_adi).distinct().all()
        
        return jsonify({
            'total_records': total_records,
            'last_update': last_update.isoformat() if last_update else None,
            'currencies': [{'code': c[0], 'name': c[1]} for c in currencies]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_currency():
    """Döviz kurları arası dönüşüm yapar"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Veri bulunamadı'}), 400
        
        amount = data.get('amount')
        from_currency = data.get('from_currency')
        to_currency = data.get('to_currency')
        
        if not all([amount, from_currency, to_currency]):
            return jsonify({'error': 'Miktar, kaynak para birimi ve hedef para birimi gerekli'}), 400
        
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'error': 'Geçersiz miktar'}), 400
        
        # En son tarihteki kurları al
        latest_date = db.session.query(db.func.max(DovizKuru.tarih)).scalar()
        
        if not latest_date:
            return jsonify({'error': 'Döviz kuru verisi bulunamadı'}), 404
        
        # Dönüşüm hesaplaması
        if from_currency == 'TRY':
            # TL'den başka bir para birimine
            to_rate = DovizKuru.query.filter_by(
                tarih=latest_date, 
                doviz_kodu=to_currency
            ).first()
            
            if not to_rate:
                return jsonify({'error': f'{to_currency} para birimi için kur bulunamadı'}), 404
            
            converted_amount = amount / to_rate.satis_kuru
            from_rate_value = 1.0
            to_rate_value = to_rate.satis_kuru
            
        elif to_currency == 'TRY':
            # Başka bir para biriminden TL'ye
            from_rate = DovizKuru.query.filter_by(
                tarih=latest_date, 
                doviz_kodu=from_currency
            ).first()
            
            if not from_rate:
                return jsonify({'error': f'{from_currency} para birimi için kur bulunamadı'}), 404
            
            converted_amount = amount * from_rate.satis_kuru
            from_rate_value = from_rate.satis_kuru
            to_rate_value = 1.0
            
        else:
            # İki farklı para birimi arası (TL üzerinden)
            from_rate = DovizKuru.query.filter_by(
                tarih=latest_date, 
                doviz_kodu=from_currency
            ).first()
            
            to_rate = DovizKuru.query.filter_by(
                tarih=latest_date, 
                doviz_kodu=to_currency
            ).first()
            
            if not from_rate:
                return jsonify({'error': f'{from_currency} para birimi için kur bulunamadı'}), 404
            
            if not to_rate:
                return jsonify({'error': f'{to_currency} para birimi için kur bulunamadı'}), 404
            
            # Önce TL'ye çevir
            tl_amount = amount * from_rate.satis_kuru
            # Sonra hedef para birimine çevir
            converted_amount = tl_amount / to_rate.satis_kuru
            from_rate_value = from_rate.satis_kuru
            to_rate_value = to_rate.satis_kuru
        
        return jsonify({
            'amount': amount,
            'from_currency': from_currency,
            'to_currency': to_currency,
            'converted_amount': round(converted_amount, 4),
            'rate_date': latest_date.strftime('%Y-%m-%d'),
            'from_rate': from_rate_value,
            'to_rate': to_rate_value
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/currencies', methods=['GET'])
def get_currencies():
    """Mevcut para birimlerini getir"""
    try:
        # En son tarihteki tüm para birimlerini al
        latest_date = db.session.query(db.func.max(DovizKuru.tarih)).scalar()
        
        if not latest_date:
            return jsonify({'error': 'Döviz kuru verisi bulunamadı'}), 404
        
        currencies = DovizKuru.query.filter_by(tarih=latest_date).all()
        
        result = []
        for currency in currencies:
            result.append({
                'code': currency.doviz_kodu,
                'name': currency.doviz_adi,
                'buy_rate': currency.alis_kuru,
                'sell_rate': currency.satis_kuru
            })
        
        # TL'yi de ekle
        result.append({
            'code': 'TRY',
            'name': 'TÜRK LİRASI',
            'buy_rate': 1.0,
            'sell_rate': 1.0
        })
        
        return jsonify({'currencies': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Veritabanı tablolarını oluştur
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 