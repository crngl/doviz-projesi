import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';
import { tr } from 'date-fns/locale';
import { 
  CurrencyDollarIcon, 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon,
  ClockIcon,
  ChartBarIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

function App() {
  const [rates, setRates] = useState([]);
  const [history, setHistory] = useState([]);
  const [stats, setStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [selectedCurrency, setSelectedCurrency] = useState('USD');
  const [lastUpdate, setLastUpdate] = useState(null);
  
  // Dönüşüm state'leri
  const [currencies, setCurrencies] = useState([]);
  const [convertAmount, setConvertAmount] = useState('');
  const [fromCurrency, setFromCurrency] = useState('USD');
  const [toCurrency, setToCurrency] = useState('TRY');
  const [conversionResult, setConversionResult] = useState(null);
  const [converting, setConverting] = useState(false);

  // API base URL
  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5000';

  // Veri çekme fonksiyonları
  const fetchLatestRates = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/rates/latest`);
      setRates(response.data.data || []);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Güncel kurlar çekilemedi:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('İstatistikler çekilemedi:', error);
    }
  };

  const fetchHistory = async (currency = selectedCurrency) => {
    try {
      const response = await axios.get(`${API_BASE}/api/rates/history`, {
        params: { doviz_kodu: currency }
      });
      setHistory(response.data.data || []);
    } catch (error) {
      console.error('Geçmiş veriler çekilemedi:', error);
    }
  };

  const updateRates = async () => {
    try {
      setLoading(true);
      await axios.post(`${API_BASE}/api/rates/update`);
      await fetchLatestRates();
      await fetchStats();
      await fetchCurrencies();
      alert('Kurlar başarıyla güncellendi!');
    } catch (error) {
      alert('Kurlar güncellenirken hata oluştu!');
      console.error('Güncelleme hatası:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrencies = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/currencies`);
      setCurrencies(response.data.currencies || []);
    } catch (error) {
      console.error('Para birimleri çekilemedi:', error);
    }
  };

  const convertCurrency = async () => {
    if (!convertAmount || parseFloat(convertAmount) <= 0) {
      alert('Lütfen geçerli bir miktar girin!');
      return;
    }

    if (fromCurrency === toCurrency) {
      setConversionResult({
        amount: parseFloat(convertAmount),
        from_currency: fromCurrency,
        to_currency: toCurrency,
        converted_amount: parseFloat(convertAmount),
        rate_date: new Date().toISOString().split('T')[0]
      });
      return;
    }

    try {
      setConverting(true);
      const response = await axios.post(`${API_BASE}/api/convert`, {
        amount: parseFloat(convertAmount),
        from_currency: fromCurrency,
        to_currency: toCurrency
      });
      setConversionResult(response.data);
    } catch (error) {
      alert('Dönüşüm yapılırken hata oluştu!');
      console.error('Dönüşüm hatası:', error);
    } finally {
      setConverting(false);
    }
  };

  // İlk yükleme
  useEffect(() => {
    const initializeData = async () => {
      setLoading(true);
      await Promise.all([
        fetchLatestRates(),
        fetchStats(),
        fetchHistory(),
        fetchCurrencies()
      ]);
      setLoading(false);
    };

    initializeData();
  }, []);

  // Seçili para birimi değiştiğinde geçmiş verileri güncelle
  useEffect(() => {
    fetchHistory(selectedCurrency);
  }, [selectedCurrency]);

  // Otomatik yenileme (5 dakikada bir)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLatestRates();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  // Grafik verilerini hazırla
  const chartData = history.map(item => ({
    tarih: format(new Date(item.tarih), 'dd MMM', { locale: tr }),
    alis: item.alis_kuru,
    satis: item.satis_kuru,
    efektif_alis: item.efektif_alis,
    efektif_satis: item.efektif_satis
  })).reverse();

  // Para birimi değişim hesaplama
  const getChangePercentage = (current, previous) => {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / previous) * 100;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Veriler yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <CurrencyDollarIcon className="h-8 w-8 text-blue-600" />
              <h1 className="ml-3 text-2xl font-bold text-gray-900">
                TCMB Döviz Kurları
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-500">
                <ClockIcon className="inline h-4 w-4 mr-1" />
                Son güncelleme: {lastUpdate ? format(lastUpdate, 'HH:mm:ss') : 'Bilinmiyor'}
              </div>
              <button
                onClick={updateRates}
                disabled={loading}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                Güncelle
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* İstatistikler */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ChartBarIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Toplam Kayıt
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {stats.total_records || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <CurrencyDollarIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Para Birimi Sayısı
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {stats.currencies?.length || 0}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ClockIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Son Güncelleme
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {stats.last_update ? format(new Date(stats.last_update), 'dd/MM/yyyy') : 'Yok'}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="p-5">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <ArrowTrendingUpIcon className="h-6 w-6 text-gray-400" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      Güncel Kurlar
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {rates.length}
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Döviz Dönüştürücü */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Döviz Dönüştürücü
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Miktar
                </label>
                <input
                  type="number"
                  value={convertAmount}
                  onChange={(e) => setConvertAmount(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.00"
                  step="0.01"
                  min="0"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Kaynak Para Birimi
                </label>
                <select
                  value={fromCurrency}
                  onChange={(e) => setFromCurrency(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {currencies.map((currency) => (
                    <option key={currency.code} value={currency.code}>
                      {currency.code} - {currency.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Hedef Para Birimi
                </label>
                <select
                  value={toCurrency}
                  onChange={(e) => setToCurrency(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {currencies.map((currency) => (
                    <option key={currency.code} value={currency.code}>
                      {currency.code} - {currency.name}
                    </option>
                  ))}
                </select>
              </div>
              
              <div className="flex items-end">
                <button
                  onClick={convertCurrency}
                  disabled={converting || !convertAmount}
                  className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {converting ? 'Dönüştürülüyor...' : 'Dönüştür'}
                </button>
              </div>
            </div>
            
            {conversionResult && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900 mb-2">
                    {conversionResult.amount} {conversionResult.from_currency} = {conversionResult.converted_amount} {conversionResult.to_currency}
                  </div>
                  <div className="text-sm text-gray-600">
                    Kur Tarihi: {conversionResult.rate_date}
                  </div>
                  {conversionResult.from_currency !== 'TRY' && conversionResult.to_currency !== 'TRY' && (
                    <div className="text-xs text-gray-500 mt-2">
                      {conversionResult.from_currency} → TRY: {conversionResult.from_rate} | TRY → {conversionResult.to_currency}: {conversionResult.to_rate}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Güncel Kurlar Tablosu */}
        <div className="bg-white shadow rounded-lg mb-8">
          <div className="px-4 py-5 sm:p-6">
            <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4">
              Güncel Döviz Kurları
            </h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Para Birimi
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Alış
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Satış
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Efektif Alış
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Efektif Satış
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {rates.map((rate, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-sm font-medium text-gray-900">
                            {rate.doviz_kodu}
                          </div>
                          <div className="text-sm text-gray-500 ml-2">
                            {rate.doviz_adi}
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rate.alis_kuru.toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rate.satis_kuru.toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rate.efektif_alis.toFixed(4)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {rate.efektif_satis.toFixed(4)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Grafik */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900">
                {selectedCurrency} Kuru Geçmişi
              </h3>
              <select
                value={selectedCurrency}
                onChange={(e) => setSelectedCurrency(e.target.value)}
                className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              >
                {stats.currencies?.map((currency) => (
                  <option key={currency.code} value={currency.code}>
                    {currency.code} - {currency.name}
                  </option>
                ))}
              </select>
            </div>
            
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tarih" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="alis" 
                    stroke="#3B82F6" 
                    strokeWidth={2}
                    name="Alış Kuru"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="satis" 
                    stroke="#EF4444" 
                    strokeWidth={2}
                    name="Satış Kuru"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="efektif_alis" 
                    stroke="#10B981" 
                    strokeWidth={2}
                    name="Efektif Alış"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="efektif_satis" 
                    stroke="#F59E0B" 
                    strokeWidth={2}
                    name="Efektif Satış"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-12">
                <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">Veri yok</h3>
                <p className="mt-1 text-sm text-gray-500">
                  Seçilen para birimi için geçmiş veri bulunamadı.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App; 