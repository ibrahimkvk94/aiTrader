# Deney 004 — Senaryo ile giriş zaman dilimini ayırma

Bu dosya sonuç görülmeden yazılmıştır; koşu başlamadan kod, veri ve protokol SHA-256 özetleri manifestte sabitlenir. Dışarıdan denetlenmiş ön-kayıt değildir. Önceki donmuş kaynaklar, ana tarayıcı ve BIST değişmez. Parametre taraması yoktur.

## Dayanak ve atıf sınırı

Kriptotiks'in [ETH senaryoları](https://tr.tradingview.com/chart/ETHUSDT/h2GVGNdp/), [BTC büyük/küçük yapı ayrımı](https://tr.tradingview.com/chart/BTCUSDT/q7XXeQag/) ve [pozisyon yönetimi açıklaması](https://x.com/cryptotiks/status/2103081820233383976) hipotez kaynağıdır. Aşağıdaki sayısallaştırma bize aittir: onun doğrulanmış veya birebir stratejisi değildir. Telegram açık önizlemesine erişilemedi; görülmeyen mesajlara dayanılmaz. Stop kullanmadığı veya tüm çıkışlarının belirli bir mum kapanışına dayandığı iddia edilmez.

## Politikalar

Giriş: değişmeyen long+short+MTF modeli, 4h bağlam / 1h bölge / 15m teyit. İki mevcut referans ve iki yeni aday:

1. `pivot`: eski 15m pivot koruması, Deney 001/002 ile aynı.
2. `bos_confirmed`: Deney 003'teki 15m BOS teyitli koruma.
3. `scenario_only`: başlangıçtaki 1h bölge sınırı sabit tutulur. Yalnız tamamlanmış 1h kapanışı bu sınırı aşınca veya 4h yapı işlem yönünün tersine dönünce çıkılır. 15m fitil/kapanışı tek başına çıkış değildir. Bölgenin tarama ömrünün bitmesi açık pozisyonu kapatmaz.
4. `setup_bos`: `scenario_only` ile aynı; ek olarak koruma seviyesi yalnız yeni 1h BOS ile taşınır. Karşı pivot kırılma mumunun açılışında zaten onaylı, kırılan swing'den sonra ve işlem girişinden önce olmayacak şekilde oluşmuş olmalıdır. Koruma yalnız sıkılaşır. Çıkış testi eski referansa göre yapılır, sonra taşıma uygulanır. Taşınmış sınır da yalnız 1h kapanışıyla geçersizleşir; aradaki 15m mumlarında yeniden taşıma yapılmaz.

Long açıklamasının short karşılığı fiyat yansımasıyla simetriktir. Sinyal hesabı performans hesabı değildir; tüm gerçekleşme, ücret, kayma ve fonlama orijinal fiyatlardan hesaplanır. Çıkış sinyalden sonraki 15m açılışındadır; boşluklar kaybı büyütebilir. Son mumda sinyal bekler, açık işlem zorla kapatılmaz. Bölge sınırına eşit kapanış kırılım sayılmaz.

Bu değişiklik zarar sınırı garantisi vermez. 1h kapanışını beklemek ve daha seyrek koruma taşımak elde tutma süresi, MAE ve düşüşü artırabilir. Sabit yüzde stop, kısmi çıkış, yeni giriş modeli veya endeks filtresi bu deneyde eklenmez: etkileri karıştırılmayacaktır.

## Veri ve değerlendirme

Deney 003 manifestindeki aynı iki incelenmiş geliştirme dönemi ve BTC/ETH önbellekleri. Yeni veri indirilmez. İlk dönemin eski ısınma koşulları korunur; ikinci dönem 14 gün ısınır. Bunlar holdout, walk-forward veya ileri sanal işlem değildir.

Her sembol bağımsız 10.000 USDT hesap ve %10 sermaye tahsisi; aynı ücret, kayma ve tarihsel fonlama, ayrıca iki kat ücret/kayma. Getiri açık pozisyonun son kapanış değerini içerir; varsayımsal gelecekteki çıkış maliyeti dahil değildir. Düşüş yalnız kapanışlardan ölçülür; tasfiye, emir defteri ve mum içi risk simülasyonu değildir.

Çıkış süresi daha sonraki girişleri ve yön çatışmalarını değiştirebilir. Ortak gerçekleşmiş giriş sayısı raporlanır; bu eşleştirilmiş işlem deneyi değildir. Long/short sinyal akışları ayrı, muhasebe sembol başına tek pozisyondur. Kurulum etiketine göre PnL ayrıştırması betimseldir, ayrı strateji testi değildir.

Her aday/sembol/dönem için net getiri, 2x maliyet, düşüş, işlem sayısı, kazanma oranı, profit factor, en kötü işlem, ortalama tutma süresi, işlem başına net PnL, açık pozisyon, bekleyen sinyaller, model/yön/çıkış nedeni kırılımı raporlanır. En iyi kapanmış işlem çıkarıldığında kalan PnL, yoğunlaşma tanısıdır; tekrar simülasyon değildir.

Araştırma eleği: her dört sembol/dönem hücresinde en az 30 kapanmış işlem, pozitif normal ve stresli getiri, en iyi kapanmış işlem çıkarılınca pozitif PnL, `pivot`tan düşük olmayan net getiri ve yüksek olmayan kapanış düşüşü. Eleği geçmek bile bağımsız doğrulama değildir ve otomatik terfi sağlamaz. Başarısız hücreler gizlenmez. Aday seçimi bu geliştirme verisine göre optimize edilmez.

## Kontroller ve sonraki sıra

Eski iki politika Deney 003 sonuçlarını birebir üretmeli. Yeni iki politikada her dönem/sembol/yön için yarım ve üç çeyrek veri kesimlerinde geçmiş olaylar değişmemeli. Birim testler kapanış zamanını, sonraki açılışta gerçekleşmeyi, 4h önceliğini, korumayı gevşetmeme ve giriş öncesi/same-close pivot reddini denetler. Eski donmuş dosyaların hash'leri doğrulanır; farklı manifest/sonuç üstüne yazılmaz.

Sonraki ayrı araştırmalar: bölgeden dönüş ile kırılım-yeniden test girişlerini bağımsız tanımlama; kısmi kâr/runner muhasebesi; zaman hizalı BTC/ETH ve BIST endeks filtresi. BIST'te bu kripto sonuçları başarı kanıtı sayılmaz; seans ve şirket işlemi doğrulaması ayrıca gerekir.
