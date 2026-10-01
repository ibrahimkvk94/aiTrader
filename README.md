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

## Planlı setup / dinamik işlem yönetimi

Eklemeli/eklemesiz eşit referans risk karşılaştırması: [Deney 005 sonuçları](docs/experiment-005-results.md).
`python tools/compare_additions.py` mevcut donmuş BTC/ETH verisinde üç yönetim kolunu karşılaştırır;
bu bağımsız setup araştırmasıdır, tek hesap getirisi veya BIST testi değildir. Otomatik bölge
üreticisi bu araştırmaya özeldir; canlı tarayıcıya bağlanmamıştır.

Yeni `planned-lifecycle-v1` modülü, baştan belirlenen giriş/ekleme bölgeleri,
yapısal stop ve TP'leri değişmez bir plan olarak saklar. Kripto vadeli long/short,
kripto spot long ve BIST long ayrı profillerdir. Bu katman **çevrimdışı araştırmadır**;
mevcut `scan`/`serve` tarayıcısının stratejisini veya çalışan panelini değiştirmez.
Otomatik bölge çıkarımı henüz bu katmana bağlanmadı; seviyeler giriş JSON'unda verilir.
Kriptotiks'in birebir stratejisi veya kârlılığı doğrulanmış bir sistem değildir.

```powershell
python run.py plan-replay --demo
python run.py plan-replay --input examples/planned-trade.json
```

Demo dört **sentetik** senaryo çalıştırır: long, short, kısmi kâr sonrası boşluklu stop,
BIST/seans boşlukları. Örnek dosyanın fiyatları/zamanları yalnız yazılım testi içindir,
işlem sinyali değildir. Gerçek veriyle aynı şema kullanılabilir. Varsayılan raporlar
`reports/plans/` altında içerik hash'li JSON olarak saklanır. `--output yeni-dosya.json`
verilebilir; farklı mevcut raporun üstüne yazılmaz. Kaynak, plan ve veri hash'leri,
tüm kararlar, gerçekleşmeler, ücretler, koruma değişiklikleri ve prefix kontrolleri kaydedilir.

### İlk sürümün açık işlem kuralları

- Plan, `created_at` zamanında tüm seviyelerin bilindiğini varsayar; gelecekte öğrenilen
  bölgeleri geçmiş plana koymak yasaktır. Alan bunu belgeler, manuel kaynağı doğrulamaz.
- Giriş/ekleme: baz mum **sıradaki bölgenin içinde kapandığında** sinyal; sonraki açılış
  hâlâ bölgedeyse maliyetli simülasyon. Anlık dokunma/limit emri simüle edilmez. Her kademe
  bir kere dolar, en fazla bir kademe/mum. Kaçan emir tekrar uygun kapanış bekleyebilir.
- Kurulum giriş öncesi stop zaman diliminde geçersizleşirse veya süresi dolarsa iptal olur.
  `expires_at` yalnız ilk girişi sınırlar; açık işlemi zaman aşımıyla kapatmaz.
- Stop: `stop_frame` mumunun aktif sınırın **kesin ötesinde** kapanışı; fitil veya eşit
  kapanış çıkış değildir. Gerçekleşme sonraki mevcut açılıştadır; boşluk zararı gizlenmez.
- TP: baz mum kapanışı hedefi doğrular, sonraki açılışta kısmi çıkılır. Bu da limit TP
  değildir; sonraki açılışın kötüleşmesi gerçek simülasyon sonucuna yansır. Aynı kapanışta
  stop önceliklidir; birden fazla TP geçilirse toplam pay tek emirde çıkar.
- İlk TP sinyaliyle kalan eklemeler kapanır. TP payları o andaki **gerçekten dolmuş**
  toplam miktarın payıdır, toplamları 1 olur. BIST kısmi lotları aşağı yuvarlanır;
  bir lot altı ara hedef atlanır, son hedef kalan bütün lotları kapatır.
- `protection: "bos"`: stop zaman diliminde yönlü yapı kırılması sonrası, kırılan swing'den
  sonra ve girişten itibaren oluşmuş, kırılım mumu açılmadan önce teyit edilmiş karşı pivot
  koruma adayıdır. Koruma yalnız sıkılaşır; yeni seviye aynı mumun geçmişine uygulanmaz.
  `"fixed"` başlangıç yapısal sınırını korur. Keyfî genişletme, otomatik maliyet stopu veya
  stop olduktan sonra yeniden giriş yoktur. Yeniden giriş yeni plan gerektirir.
- Tüm kademeler tek `max_notional` ve `risk_budget` paylaşır; her kademe ayrı risk bütçesi
  açmaz. `risk_budget`, stop referans fiyatında masraflı **tahmini** kayıptır, gerçek azami
  zarar garantisi değildir. Kapanışı bekleme, boşluk ve fonlama bunu aşabilir.
- Hesap tam teminatlı varsayımsaldır; kaldıraç/tasfiye motoru veya portföy çapında risk
  havuzu yoktur. Planlar bağımsız hesaplanır, getirileri ortak portföy gibi toplanamaz.
- İsteğe bağlı `funding`: `{ "time": UTC_saniye, "mark": fiyat, "rate": oran }` kayıtları.
  Açılış sınırındaki fonlama yeni emirlerden önce eski pozisyona uygulanır. Sağlanmazsa
  raporda eksik olduğu belirtilir; boş liste kullanıcının sıfır olay beyanıdır.
- Kripto kapanmış üst mumları aynı baz seriden üretilir. BIST haftalık/aylık stop için
  `stop_bars` ayrıca verilmelidir; kapanış zamanları, tatiller ve şirket işlemleri veri
  sağlayıcısında doğrulanmalıdır. BIST kısa satış/vadeli emir gönderimi yoktur.
  Seans aralığında bilinir hale gelen üst mum, ilk sonraki baz kapanışında değerlendirilir;
  bu çevrimdışı adaptör seans açılışından önce ayrı bir karar döngüsü çalıştırmaz.
- Son mumdaki sinyal beklemede kalır, veri bitti diye işlem kapatılmaz. Açık PnL ilerideki
  çıkış maliyetlerini içermez. Birim test/demo başarısı strateji getirisi kanıtı değildir.

## Long/short ve çoklu bölge karşılaştırması

Bu deney canlı tarayıcıdan ayrıdır; mevcut tarayıcı hâlâ ilk alış yönlü kurallarla çalışır.

```powershell
python tools/compare_variants.py --days 180
python tools/validate_experiments.py
```

Her sembol için aynı Binance USD-M vadeli mumları ve tarihsel fonlama kayıtları üzerinde dört varyant karşılaştırılır:
`long_only_baseline`, `long_short_baseline`, `long_only_mtf`, `long_short_mtf`.
MTF adayı, 1 saatlik giriş bölgesinin aktif 4 saatlik destekleyici bölgeyle örtüşmesini ve karşı 4 saatlik bölgeye en az bir yapısal geçersizleşme mesafesi kadar alan bulunmasını ister. Giriş teyidi yine 15 dakikadır; çıkış kuralları aynı tutulur.

Short sinyalleri, yalnız ilk mumun açılışıyla belirlenen sabit bir eksen etrafında fiyat yansıtılarak long kurallarının simetriğiyle üretilir. Yansıtılmış sanal hesap sonuçları kullanılmaz; işlemler gerçek vadeli fiyatlarından, short yönüne uygun komisyon/fiyat kayması ve tarihsel fonlamayla yeniden muhasebeleştirilir. Eksenin hesaplanmasında gelecekteki maksimum/minimum fiyat kullanılmaz.

Hesap başlangıcı 10.000 USDT, işlem başına sermaye tahsisi %10; aynı anda bir tam teminatlı pozisyon. Karşı yön sinyalleri varsa önce çıkış sonra giriş işlenir. Bu bir borsa teminat kademesi/tasfiye simülatörü değildir. Normal ve iki kat maliyet sonuçları, işlem sayısı, kazanma oranı, azami düşüş ve üç kronolojik dönemin getirileri kaydedilir. Yakın dönem önceden incelendiği için sonuçlar **dokunulmamış test / doğrulanmış başarı** olarak sunulmaz.

Yerel sonuç: `reports/experiments/comparison.json`; tekrar doğrulama: `reports/experiments/validation.json`. Ham piyasa verileri ve ayrıntılı çalışma raporları GitHub'a yüklenmez. İlk deneyin özeti [deney notlarında](docs/experiment-001.md).

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

## Dondurulmuş dönem testi — Deney 002

[Önceden sabitlenen protokol](docs/experiment-002-protocol.md) ve [tüm sonuçlar](docs/experiment-002-results.md).
2025-10-01 → 2026-04-01 döneminde dört mevcut modele tek bir MTF+süpürme adayı eklendi. Hiçbir aday iki sembolde araştırma eleğini geçmedi; ana strateji değiştirilmedi. Bu daha eski tarihsel döneme aktarım testidir, kronolojik walk-forward veya gerçek forward test değildir.

```powershell
python tools/test_frozen_period.py
```

Komut önce Deney 001'in yerel raporu/önbelleğiyle sonuç eşitliğini doğrular; bu yüzden aynı `reports/experiments/comparison.json` ve ilgili `data/experiments` dosyaları gerekir. Bunlar henüz yoksa önce Deney 001 çalıştırılmalıdır; yeni tarihte oluşturulan bir geliştirme raporu orijinal koşunun birebir tekrarı olmaz. Deney 002 kendi manifestini, veri/kod özetlerini ve raporunu ayrı klasöre yazar; mevcut farklı kanıtların üstüne yazmayı reddeder. API tarihsel verisi revize olabilir.

### İşlem düzeyinde görsel inceleme

[İnceleme 001](docs/trade-review-001.md): maliyet ayrıştırması, korunan seviyenin hareketi ve altı örnek işlem. `python tools/review_trades.py` mevcut Deney 002 kayıtlarını inceler; isteğe bağlı `--charts` için Matplotlib gerekir. Strateji değiştirmez, yeni test sonucu üretmez. Raporlar ve grafikler `reports/trade-review/` altında tutulur.

### BOS teyitli çıkış deneyi — Deney 003

`priceaction/exit_research.py` modülündeki `bos_confirmed` politikası koruma seviyesini yalnız işlem yönünde yeni yapı kırılması teyit edildiğinde taşır. Varsayılan `Engine` ve tarayıcı değişmedi. [Kesin kural](docs/experiment-003-protocol.md) ve [karşılaştırma sonuçları](docs/experiment-003-results.md): BTC iyileşirken ETH kötüleşti, dört karşılaştırmada da düşüş arttı; otomatik terfi yapılmadı. İki dönem de geliştirme verisidir, bağımsız test değildir.

```powershell
python tools/compare_exit_policies.py
```

Mevcut Deney 001/002 raporları/önbellekleri gerekir; sonuçlar ayrı `reports/experiments/experiment-003/` klasöründedir. Önceki donmuş kaynaklar değiştirilmez.

### Ana senaryo / giriş zaman dilimi ayrımı — Deney 004

`priceaction/scenario_research.py` iki yeni, yalnız araştırma amaçlı çıkış politikası ekler: `scenario_only` başlangıç 1h bölgesinin kapanışla kaybı veya 4h karşı yapı ile çıkar; `setup_bos` buna yalnız 1h BOS ile taşınan koruma ekler. 15m kapanışı tek başına çıkış değildir. Giriş ve maliyet kuralları değişmez. Bu, Kriptotiks paylaşımlarından esinlenen **bizim operasyonel hipotezimizdir**, onun birebir stratejisi değildir.

[Kesin protokol](docs/experiment-004-protocol.md) ve [tüm sonuçlar](docs/experiment-004-results.md): iki aday da dört eşleşmenin üçünde eski net getiriyi artırdı; hepsinde düşüş arttı, yakın dönem ETH kötüleşti. 59 birim testi ve 32 geçmiş-olay değişmezlik kontrolü geçti. Hiçbir aday araştırma eleğini geçmedi; ana tarayıcı ve BIST değişmedi.

```powershell
python tools/compare_scenario_policies.py
```

Aynı yerel Deney 001–003 kaynak/rapor/önbellekleri gerekir; yeni ağ verisi indirilmez. Manifest ve ayrıntılı sonuç `reports/experiments/experiment-004/` altındadır. Kısmi çıkış, ayrı giriş modelleri ve endeks filtresi henüz eklenmedi; sonraki ayrı deneylerdir. Her iki dönem de geliştirme verisidir, bağımsız başarı doğrulaması değildir.
