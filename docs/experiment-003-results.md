# Deney 003 — BOS teyitli koruma seviyesi

30 Eylül 2026. Yeni kural ayrı deney modülüne eklendi; ana tarayıcı ve BIST değiştirilmedi. [Protokol](experiment-003-protocol.md) koşudan önce 16:42:46 UTC'de yerel kaynak özetleriyle sabitlendi. Bu bir bağımsız ön-kayıt hizmeti değildir.

## Uygulanan davranış

`pivot` eski politikadır. `bos_confirmed`, korunan seviyeyi ancak işlem yönünde yeni kapanış bazlı swing kırılması gerçekleştiğinde taşır. Kullanılan karşı swing kırılan swing'den ve işlem girişinden sonra oluşmuş, kırılma mumu açılmadan önce onaylanmış olmalıdır. Aynı kapanışta yeni öğrenilen pivot kullanılamaz; referans asla gevşetilmez. Başlangıç bölgesi ve üst zaman dilimi geçersizlikleri korunur. Fitil tek başına çıkış değildir; çıkış hâlâ sonraki mum açılışındadır.

Bu deney, aynı long+short+MTF giriş kurallarıyla iki çıkış politikasını karşılaştırır. Parametre araması yapılmadı. Sonuçlar önceden incelenmiş iki geliştirme döneminden gelir; holdout veya forward başarı kanıtı değildir.

## Net hesap getirileri ve risk

Her sembol bağımsız 10.000 USDT hesap, %10 sermaye tahsisi. Normal maliyet her yönde 10 bp komisyon + 5 bp kayma ve tarihsel fonlama; stres 20/10 bp ve aynı fonlamadır. Getiriler işlem kazanma oranı değildir.

| Dönem | Sembol | Eski net | Yeni net | Eski 2× maliyet | Yeni 2× maliyet | Eski / yeni azami düşüş |
|---|---|---:|---:|---:|---:|---:|
| 2026-04-03 → 2026-09-30 | BTC | +%0,17 | +%1,33 | −%0,19 | +%0,98 | %0,58 / %0,70 |
| 2026-04-03 → 2026-09-30 | ETH | −%0,99 | −%1,59 | −%1,35 | −%1,94 | %0,99 / %1,59 |
| 2025-10-01 → 2026-04-01 | BTC | −%0,11 | +%0,25 | −%0,35 | +%0,01 | %0,35 / %0,43 |
| 2025-10-01 → 2026-04-01 | ETH | −%0,30 | −%0,59 | −%0,63 | −%0,89 | %0,73 / %1,28 |

Düşüş kapanış bazlıdır; mum içi risk ve gerçek borsa likidasyon/gerçekleşme mekanizmaları modellenmez. Yeni BTC 2026 koşusunda bir açık işlem vardır; net hesap getirisi bunun kapanış fiyatından değerini içerir, gelecekteki çıkış ücreti henüz düşülmez.

| Dönem / sembol | Eski / yeni kapanmış işlem | Eski / yeni kazanma oranı | Ortalama elde tutma saati (eski / yeni) | En kötü kapanmış PnL, USDT (eski / yeni) |
|---|---:|---:|---:|---:|
| 2026 / BTC | 12 / 11 | %25,00 / %27,27 | 7,02 / 18,68 | −17,23 / −18,55 |
| 2026 / ETH | 12 / 12 | %8,33 / %8,33 | 4,83 / 10,98 | −22,84 / −28,71 |
| 2025–26 / BTC | 8 / 8 | %37,50 / %50,00 | 5,81 / 17,13 | −12,59 / −17,11 |
| 2025–26 / ETH | 11 / 10 | %27,27 / %20,00 | 5,70 / 18,63 | −26,35 / −31,79 |

Giriş kuralları aynı olsa da pozisyon daha uzun açık kaldığında sonraki giriş değişebilir. Açık pozisyonlar dahil ortak giriş sayıları sırasıyla 12/12, 12/12, 8/8 ve 10'dur; son satırda eski model 11, yeni model 10 giriş yaptı. Dolayısıyla son satır birebir eşleştirilmiş işlem deneyi değildir.

## Karar ve sınırlamalar

- BTC iki dönemde de iyileşti, ETH iki dönemde de kötüleşti.
- Azami düşüş ve en kötü kapanmış işlem kaybı dört karşılaştırmada da arttı. Daha seyrek koruma taşımanın risk bedeli var.
- BTC'deki iyileşme tek büyük kazanca bağımlı: 2026 koşusunda en iyi kapanmış işlem +191,28 USDT; toplam hesap PnL'sinden bunu çıkarınca −58,40 USDT kalır. Daha eski BTC koşusunda en iyi +29,93 USDT çıkarıldığında −4,83 USDT kalır. Bu çıkarma yeniden simülasyon değil, kazanç yoğunlaşması tanısıdır.
- İşlem sayıları çok küçük; iki dönem de hipotez geliştirme sürecinde görüldü. Sonuçtan hareketle BTC'ye özel politikayı seçmek de ayrıca veri seçimi/uyum riskidir.

Yeni politika **deney seçeneği olarak tutuldu, ana tarayıcıya geçirilmedi**. Başarılı genel strateji bulunduğu iddia edilmiyor. Kodlama isteği tamamlandı; daha ileri araştırma için yeni bir bağımsız dönem/ileri sanal hesap ve daha çok işlem gerekir.

## Kontroller ve kullanım

- 46 birim testi geçti: teyitsiz pivot, kırılmadan önce bilinme, swing sırası, tekrar kırılma, korumayı gevşetmeme, giriş öncesi pivotu reddetme, üst zaman dilimi çıkış önceliği, fitil/kapanış ve sonraki açılış davranışları dahil.
- Eski MTF metrikleri iki dönemde iki sembol için aynen yeniden üretildi.
- Yeni politikada iki dönem × iki sembol × iki yön × iki kesim = 16 geçmiş-olay değişmezlik kontrolü geçti; koruma taşıma kanıtları da karşılaştırıldı.
- Deney 002'nin donmuş kaynak hash'leri ve kayıtları korundu. Deney 003 kendi manifestini ve veri/kod özetlerini ayrı saklar.

```powershell
python -m unittest discover -s tests -v
python tools/compare_exit_policies.py
```

Yerel Deney 001/002 raporları ve önbellekleri gereklidir. Yeni veri indirme veya gerçek emir yoktur. Çıktı: `reports/experiments/experiment-003/results.json`; kural hareketlerinin kaynak swing'leri `replay_exit(...).events` içindeki `protection_update` alanında bulunur. Short olaylarındaki seviyeler sinyal üretimi için yansıtılmış fiyat uzayındadır; portföy sonuçları gerçek fiyatlarla hesaplanır.

Programatik kullanım: `replay_exit(cfg, bars, side=1, policy='bos_confirmed', trade_start=..., use_mtf=True)`. Bu API'nin motor hesabı sinyal üretim hesabıdır; yatırım performansı için `orders_from` ve orijinal fiyat/fonlama verisiyle `account` kullanılmalıdır. Örnek tam akış karşılaştırma aracındadır.
