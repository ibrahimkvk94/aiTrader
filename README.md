# aiTrader — Structure Lab

İlk çalışan araştırma sürümü. Kripto ve BIST ayrı veri, kural, rapor ve kayıtlarla çalışır.
Gerçek emir gönderme kodu, API anahtarı, kaldıraç veya para transferi yoktur.

## Çalıştırma

Python 3.11+ yeterlidir; dış paket kurulumu gerekmez.

```powershell
python run.py serve
```

Panel: <http://127.0.0.1:8765>. Sunucu yerel bilgisayara bağlanır.
Kripto her 60 saniyede, BIST yaklaşık 30 dakikada bir kontrol edilir.
Sunucu terminalden başlatıldıysa Ctrl+C ile kapanır. Windows yeniden başladığında otomatik açılmaz.

Tek tarama ve testler:

```powershell
python run.py scan --days 60
python -m unittest discover -s tests -v
```

Varsayılan araştırma evreni BTCUSDT, ETHUSDT; THYAO.IS, GARAN.IS, EREGL.IS.
Bu seçim altyapıyı denemek içindir, yatırım önerisi veya tarihsel evren değildir.

```powershell
python run.py serve --symbols BTCUSDT ETHUSDT --bist THYAO.IS GARAN.IS EREGL.IS --port 8765
```

## Mevcut çalışma biçimi

- **Kripto:** Binance herkese açık spot verisi, 60 günlük 15dk mum. Giriş 15dk, kurulum 1 saat, bağlam 4 saat.
- **BIST:** Yahoo Finance deneysel ücretsiz günlük veri. Giriş günlük, kurulum haftalık, bağlam aylık. Bugünkü günlük mum kullanılmaz. Manuel inceleme/tarama amaçlıdır.
- Her güncelleme kayıtlı geçmişi kronolojik olarak tekrar işler. Paneldeki pozisyonlar ve PnL geçmiş tekrarının varsayımsal sonuçlarıdır; canlı veya ileriye dönük sanal gerçekleşme değildir.
- Ayrı `observations` tablosu tarayıcının gerçekten çalıştığı anda gözlemlediği son kararı saklar. Bu gözlemler de emir gerçekleşmesi değildir.
- Kripto serisinin başlangıcı ilk indirmeden itibaren korunur; yeni mumlar eklenir. `--days` azaltmak önbelleği daraltmaz, artırmak gerekirse daha eski veriyi indirir.
- BIST'te güncel ve sertifikalı şirket işlemi verisi bulunmadığından panelde performans metriği yayımlanmaz.

## v0.1 karar kuralları

1. Swing tepe/dip: soldaki ve sağdaki ikişer mumdan kesin yüksek/düşük olmalı. Sağdaki ikinci mum kapandığında öğrenilir; geçmişteki pivot mumunda biliniyormuş gibi kullanılmaz.
2. Yapı yönü: önceden onaylı swing seviyesinin kapanışla ilk geçilmesi. Yükseliş ve düşüş kırılması eşit yön değiştirme mantığına sahiptir.
3. Güçlü hareket: mum gövdesi, önceki 14 mumun ortalama true range değerinin en az 0,8 katı. ATR yalnız hareket ölçüsü ve açılış boşluğu filtresidir; fiyat stopu değildir.
4. Aday talep/arz: güçlü yapı kırılmasından önceki altı mum içindeki son karşı yönlü mumun tam fiyat aralığı. Bu ilk sürüm tek mumlu order-block benzeri **operasyonel yaklaşım** kullanır; çok mumlu sıkışma tabanı, tam Supply–Demand puanlaması henüz yoktur.
5. Bullish breaker: aktif arz bölgesinin üstünde güçlü yükseliş kırılmasıyla kapanış; bölge ancak bundan sonra breaker olarak bilinir. Bu basitleştirilmiş bir aday tanımıdır, her ICT breaker varyasyonunu kapsamaz.
6. Alış: bağlam ve kurulum yönü yukarı; aktif talep/breaker'a dönüş; en fazla sekiz giriş mumu içinde bölge üstünde kapanışla yeni yükseliş yapı kırılması. Bölge onaylandığı mumun içinde yeniden test edilmiş sayılmaz. Her bölgeye en fazla bir giriş sinyali.
7. Likidite etiketi: son sekiz giriş mumunda önceden bilinen dip altına fitil ve üstüne kapanış varsa `demand_sweep`; diğer talep girişleri `demand_continuation`. Gerçek stop/emir havuzları gözlemlenmez. Eşit dip kümeleri, önceki gün seviyeleri ve bağımsız dönüş modeli ileriki sürümdedir.
8. Çıkış: kurulum kapanışı başlangıç bölgesinin altına inerse, üst yapı düşüşe dönerse veya giriş zaman dilimi korunan dip altında kapanırsa. Yeni onaylı ve daha yüksek dipler korunan referansı yalnız yukarı taşır. Fitil tek başına çıkış değildir.
9. Alış/satış sinyali kapanışta oluşur; fiyat kayması eklenmiş **sonraki mevcut mum açılışında** varsayımsal gerçekleşme olur. Veri bitince açık işlem zorla kapatılmaz. Son sinyal bekleyen emir olarak kalabilir.
10. Açılışta bölge altına boşluk veya sinyal fiyatından bir ATR'den büyük uzaklaşma varsa giriş iptal edilir. Sabit yüzdesel stop ve kâr alma yoktur; kısmi çıkış da henüz yoktur.

Üst mumlar yalnız tamamlandıktan sonra kullanılır. Kriptoda eksik/çakışan mum taramayı durdurur; tamamlanmayan üst dönem oluşturulmaz.
BIST günlük mumları sonraki UTC gece yarısında, hafta/ay mumları takvim dönemi bitince kullanılabilir sayılır. Bu muhafazakâr zamanlama gerçek seans içi sinyal motoru değildir.

## BIST veri sınırları

- Yahoo'nun belgelenmemiş chart erişimi değişebilir veya kesilebilir. Yalnız kişisel araştırma; yeniden dağıtım/ücretli veri garantisi yoktur.
- Açık null kayıtlar için doğrulanmış dört 2026 tam tatil günü atlanır; bu liste tam borsa takvimi değildir. Diğer eksik günlük kayıtlardan sonra geçmiş yeniden başlatılır. Fiyat uydurulmaz veya ileri doldurulmaz.
- Kaynak bölünme bildirirse yapı analizi son bölünmeden sonraki veriye sıfırlanır. Temettüler, tüm bedelli/bedelsiz işlemler, sessiz eksik günler ve tarihsel revizyonlar tam doğrulanmış değildir.
- İlk veri çekiminde THYAO/GARAN 2024-04-09 eksik yarım gününden sonra başlatıldı. EREGL'de bildirilen son bölünme sonrasındaki dönem kullanıldı. Kesilen dönem metadata'da kayıtlıdır.
- Bugünkü fiyat, gün içi bildirim veya aracı kurum emri yoktur. Günlük/haftalık tarama kullanıcı manuel incelemesine aday üretir; modelin tuttuğu pozisyon kullanıcının gerçek pozisyonu sayılmaz.

Kendi verisiyle tarama (mevcut BIST profilinde günlük, haftalık, aylık dosyalar):

```powershell
python run.py import-bist --symbol ORNEK.IS --base gunluk.csv --setup haftalik.csv --context aylik.csv
```

Üç dosyanın sütunları:

```csv
timestamp,close_timestamp,open,high,low,close,volume
2026-09-28T10:00:00+03:00,2026-09-28T18:10:00+03:00,100,103,99,102,10000
```

Zamanlar saat dilimi içermeli; `close_timestamp` o mumun gerçekten öğrenilebilir olduğu zamanı belirtmeli. Seans/şirket işlemi düzeltmesinin doğruluğu veri sağlayıcısına aittir. Import raporu `reports/bist` altında oluşur; çevrimiçi varsayılan tarayıcı aynı sembolün raporunu sonraki kontrolde yenileyebilir.

## Maliyet ve sermaye

Kriptoda her sembol bağımsız 10.000 USDT deney hesabıdır. Her alışta mevcut nakdin %10'u tahsis edilir. Bu **kayıp riski limiti değildir**. Her yönde 10 baz puan komisyon ve 5 baz puan fiyat kayması deney varsayımıdır; gerçek hesap komisyonu/spread ölçümü değildir.

PnL ücretleri içerir; açık pozisyon kapanış fiyatından değerlenir. Azami düşüş kapanışlar üzerinden hesaplanır, mum içi düşüşü sınırlamaz. Sabit stop olmadığından kapanışı beklerken ve fiyat boşluklarında kayıp büyüyebilir.

Mevcut sonuçlar çok kısa örneklemli mühendislik doğrulamasıdır. Walk-forward, dokunulmamış değerlendirme, maliyet stresi, tarihsel evren, portföy korelasyonu ve gerçek gerçekleşme ölçümü yapılmadan kârlılık iddiası kurulmaz. BIST sonuçlarına ücret/lot/şirket işlemi varsayımları nedeniyle ekonomik anlam yüklenmez.

## Kayıtlar ve öğrenme

- `data/research.sqlite3`: ham mumlar, değişmez tekrar koşuları, bütün WATCH/HOLD/giriş/çıkış kararları, varsayımsal işlemler, gerçek zamanlı tarayıcı gözlemleri.
- `reports/crypto/*.json`, `reports/bist/*.json`: son rapor; parametre ve veri özeti, işlem dökümü, MFE/MAE (işlem içi olumlu/olumsuz hareket), maliyet, açıklamalar.
- Her koşuda parametre + motor sürümü ve veri özeti hash'lenir. Revize veri ayrı araştırma koşusu üretir. Motor davranışı değişirse sürüm artırılmalıdır.
- Aynı geçmişi her kontrolde çoğaltmamak için yeni kararlar, önceki koşuya referans veren fark kayıtlarıyla saklanır. `Store.run_records(run_id)` tüm günlüğü geri kurar; geçmiş değişmişse yeni ve bağımsız bir kayıt dalı açılır.
- İlk sürüm **öğrenme için veri toplar; otomatik öğrenmez veya kendi kurallarını değiştirmez**.

Sonraki geliştirme sırası: bağımsız kurulum etiketleme ve görsel inceleme → daha uzun/maliyet stresli walk-forward karşılaştırma → yeniden başlatılabilen ileriye dönük sanal hesap → doğrulanan aday stratejiyi sürümleme. Kullanıcı manuel işlemleri için gerçek gerçekleşme günlüğü ayrı eklenmeli.

## Kaynaklar

- [SMC kod referansı](https://github.com/joshyattridge/smart-money-concepts): geleceğe bağımlı işaretlerin doğrudan kullanılmaması gerekçesi.
- [Binance spot piyasa verileri](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints).
- [Yahoo borsa/veri gecikmeleri](https://help.yahoo.com/kb/finance/article-exchanges-data-delays-sln2310.html).
- [BIST resmi tatiller](https://www.borsaistanbul.com/resmi-tatil-gunleri).
- [Freqtrade test varsayımları](https://docs.freqtrade.io/en/stable/backtesting/#assumptions-made-by-backtesting).
- [Backtest overfitting araştırması](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf).

Harici strateji kodu kopyalanmadı; bu repo standart Python kitaplığıyla yazılmış ayrı bir deneysel uygulamadır.
