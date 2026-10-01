# Deney 002 — Önceden sabitlenmiş dönem aktarım testi

Bu protokol 30 Eylül 2026'da yeni dönemin verisi indirilmeden ve sonuçları görülmeden yazıldı. Kod/konfigürasyon SHA-256 özeti, çalıştırıcının ilk adımında yerel `manifest.json` dosyasına kaydedilir. Bu kayıt yerel bir zaman damgasıdır; bağımsız bir ön-kayıt hizmeti değildir.

## Hipotez ve sabit kurallar

İlk deneyin çıkışları çoğunlukla 15 dakikalık korunan yapı bozulmasıdır; bu gözlem tek başına bir neden veya çözüm kanıtı değildir. Yalnız bir yeni giriş hipotezi sınanır: MTF bölge filtresine ek olarak son sekiz 15 dakikalık mumda (mevcut kapanan mum dahil) önceden bilinen swing seviyesinin fitille aşılması ve geri kapanışla geri alınması zorunlu olsun. Long için dip, short için tepe süpürmesi. Breaker girişleri de bu şarttan muaf değildir. Eşit tepe/dip kümeleri veya gerçek emir havuzları ölçülmez.

- Dört eski varyant aynen korunur; beşinci `long_short_mtf_sweep` eklenir. Sonuçtan sonra eşik taraması veya strateji değişikliği yapılmaz.
- Test: **2025-10-01 00:00 UTC dahil → 2026-04-01 00:00 UTC hariç**. Öncesinde 14 gün yalnız gösterge/yapı ısınması; test başlangıcında hesap nakittir. Başlangıç anında bilinen son kapanışın sinyali ilk test açılışında kullanılabilir.
- BTCUSDT ve ETHUSDT USD-M vadeli mumları ve tarihsel fonlama. Bu dönem önceki 2026-04-03 → 2026-09-30 örneklemiyle çakışmaz.
- Bu daha eski tarihsel dönemdir: **geriye doğru dönem aktarımı**, kronolojik walk-forward veya gerçek ileriye dönük test değildir. İncelendikten sonra artık dokunulmamış sayılmaz.
- Zaman dilimleri 4h/1h/15m; diğer tüm ayarlar `configs/crypto.json` dosyasından sabitlenir. Çıkış mantığı değişmez, sabit fiyat stopu eklenmez.
- Her sembolde bağımsız 10.000 USDT, %10 sermaye tahsisi. Aynı anda en çok bir yön. Komisyon/kayma her yönde 10/5 baz puan, ayrıca tarihsel fonlama; stres 20/10 baz puan. Gerçek emir/hesap bağlantısı yoktur.
- Üç eşit ardışık zaman bloğu ayrıca raporlanır; bloklar arasında pozisyon sıfırlanmaz. Son açık pozisyon piyasaya göre değerlenir, zorla kapatılmaz.

## Önceden tanımlı araştırma eleği

Bir varyantın her iki sembolde de: en az 30 kapanmış işlemi, pozitif net getirisi, 2× maliyette pozitif getirisi, üç bloğun en az ikisinde pozitif getirisi ve en iyi tek kapanmış işlemin PnL'si çıkarıldığında pozitif toplam hesap PnL'si olmalı. Son ölçü yeniden simülasyon değil, yoğunlaşma hassasiyetidir.

30 işlem yalnız asgari örneklem eleğidir; istatistiksel anlamlılık iddiası değildir. Beş varyant ve iki sembol için tüm sonuçlar açıklanır; yalnız kazanan seçilmez. Eleği geçmek bile canlı kullanıma onay değildir: gerçek ileriye dönük sanal hesap, veri kalitesi ve gerçekleşme kontrolleri hâlâ gereklidir.

## Denetim

Önce eski örneklemde aynı başlangıç/bitiş ve ayarlarla sonuçların değişmediği doğrulanır; model/yön/çıkış nedeni bazında işlem dökümü oluşturulur. Yeni filtre için iki farklı veri kesiminde geçmiş sinyallerin değişmediği kontrol edilir. Isınma işlemleri performansa alınmaz. Eski deney raporu üzerine yazılmaz. Ham veriler ve raporlar Git dışında yerel tutulur.

```powershell
python -m unittest discover -s tests -v
python tools/test_frozen_period.py
```

Veri kaynağı: [Binance USD-M piyasa verileri ve fonlama API](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).
