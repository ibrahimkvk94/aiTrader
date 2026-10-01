# Deney 004 — Ana senaryo / giriş zaman dilimi ayrımı

1 Ekim 2026. [Protokol](experiment-004-protocol.md) ve kaynak/veri özetleri sonuç hesaplaması başlamadan 10:50:41 UTC'de yerel manifestte sabitlendi. İki yeni aday uygulandı ve çalıştırıldı; ana tarayıcı, BIST, eski deney kaynakları ve raporları değiştirilmedi. Bu Kriptotiks'in birebir stratejisinin veya başarısının testi değildir.

## Sonuç

Her iki yeni aday da eski `pivot` politikasına göre dört hücrenin üçünde net getiriyi artırdı, **dördünde de azami düşüşü artırdı**. Yakın dönem ETH her iki adayda kötüleşti. Hiçbiri önceden tanımlanmış araştırma eleğini geçmedi; ana stratejiye terfi edilmedi. İşlemi daha uzun taşımak tek başına güvenilir bir iyileştirme değil.

Her sembol bağımsız 10.000 USDT başlangıç ve %10 sermaye tahsisi; sonuçlar hesap getirileridir, kazanma oranı değildir. Normal maliyet her yönde 10 bp ücret + 5 bp kayma ve tarihsel fonlamadır. %10 tahsis kayıp riski limiti değildir.

| Dönem (UTC) | Sembol | Eski 15m pivot | Önceki 15m BOS | Ana senaryo (`scenario_only`) | 1h BOS (`setup_bos`) |
|---|---|---:|---:|---:|---:|
| 2026-04-03 → 2026-09-30 | BTC | +%0,17 | +%1,33 | +%0,80 | +%1,08 |
| 2026-04-03 → 2026-09-30 | ETH | −%0,99 | −%1,59 | −%1,11 | −%1,62 |
| 2025-10-01 → 2026-04-01 | BTC | −%0,11 | +%0,25 | +%1,28 | +%1,11 |
| 2025-10-01 → 2026-04-01 | ETH | −%0,30 | −%0,59 | +%1,14 | +%0,50 |

`scenario_only`: 1h başlangıç bölgesi kapanışla kaybedilene veya 4h karşı yapı onaylanana kadar taşı. `setup_bos`: buna 1h BOS ile teyitli, yalnız sıkılaşan yapısal koruma ekle. İkisinde de 15m kırılım tek başına çıkış değildir. Sinyal kapanışta, gerçekleşme sonraki 15m açılışındadır; fitil/sabit yüzde hedefi kullanılmaz.

## Risk ve maliyet stresi

| Dönem / sembol | Eski azami düşüş | Ana senaryo düşüş | 1h BOS düşüş | Ana senaryo 2× maliyet net | 1h BOS 2× maliyet net |
|---|---:|---:|---:|---:|---:|
| 2026 / BTC | %0,58 | %1,21 | %1,03 | +%0,51 | +%0,79 |
| 2026 / ETH | %0,99 | %1,76 | %1,92 | −%1,43 | −%1,97 |
| 2025–26 / BTC | %0,35 | %0,67 | %0,66 | +%1,04 | +%0,87 |
| 2025–26 / ETH | %0,73 | %1,65 | %1,30 | +%0,93 | +%0,29 |

Düşüş kapanış bazlıdır; mum içi kaybın üst sınırı değildir. 2× stres komisyon/kaymayı ikiye katlar, tarihsel fonlamayı aynen kullanır. Sonucun pozitif kalması gerçek gerçekleşme veya likidasyon güvenliği kanıtı değildir.

| Dönem / sembol | Ana senaryo işlem / kazanma | 1h BOS işlem / kazanma | Ortalama taşıma saati (ana / BOS) | En kötü işlem USDT (eski / ana / BOS) |
|---|---:|---:|---:|---:|
| 2026 / BTC | 9 / %11,11 | 9 / %11,11 | 48,78 / 39,44 | −17,23 / −30,42 / −21,94 |
| 2026 / ETH | 11 / %9,09 | 12 / %8,33 | 49,18 / 19,42 | −22,84 / −27,66 / −27,49 |
| 2025–26 / BTC | 8 / %50,00 | 8 / %50,00 | 85,53 / 62,91 | −12,59 / −19,18 / −19,15 |
| 2025–26 / ETH | 7 / %57,14 | 7 / %42,86 | 106,14 / 76,57 | −26,35 / −63,47 / −37,56 |

Kazanma oranı tek başına başarı ölçüsü değildir: yakın dönem BTC'de iki aday da yalnız 1/9 kapanmış işlemi kazanırken pozitif net hesap getirisi üretti. Ancak en iyi kapanmış işlem PnL'si toplam hesap PnL'sinden çıkarılınca sırasıyla −109,97 ve −83,58 USDT kalıyor; sonuç tek kazanca bağımlı. Bu çıkarma yeniden simülasyon değil, yoğunlaşma tanısıdır.

Eski dönemde aynı tanı `scenario_only` BTC/ETH için +18,08/+9,64 USDT, `setup_bos` için +32,72/−51,19 USDT. Örneklem tüm hücrelerde 7–12 işlem; 30 işlem eleğinin altında. Adayların tüm hücrelerde düşüş koşulunu da ihlal etmesi nedeniyle hiçbiri eleği geçmedi.

## Yorum ve sonraki hipotez

Ana senaryoyu korumak bazı uzun hareketleri yakaladı, fakat yanlış girişi iyileştirmedi. Yakın dönem ETH `scenario_only` koşusunda 11 kapanmış işlemin 10'u başlangıç bölgesi geçersizliğiyle, hepsi zararla kapandı. Tek 4h-yapı çıkışı +105,53 USDT kazandırdı ama kalan kayıpları kapatamadı. Bu, yalnız çıkışı geciktirmek yerine girişin bölge konumunu ve piyasa bağlamını incelememiz gerektiğine işaret ediyor; nedensel kanıt değildir.

Sonraki ayrı deney önceliği: bölgeden dönüş ve kırılım-yeniden test girişlerini ayrı tanımlamak; sinyalin bölgeden uzaklaşmasını ve karşı yapıyı incelemek. Ardından kısmi kâr/runner ve endeks uyumu ayrı değişkenler olarak test edilmeli. Bu koşuda bunlar uygulanmadı; sonuç görüp yeni eşik/parametre seçilmedi. BIST'e kripto sonucu taşınmadı.

## Veri ve doğrulama

- 59 birim testi geçti (önceki 46 + 13 yeni). Giriş eşitliği, 15m/1h kapanış ayrımı, fitil ve eşitlik sınırı, sonraki açılış/gap gerçekleşmesi, 4h çıkışı, giriş öncesi/aynı anda öğrenilen pivot reddi, koruma sıkılaştırma ve eski üst mumun yeniden kullanılamaması dahil.
- Mevcut iki politika tüm dört veri hücresinde Deney 003'ün işlem dökümleri, açık pozisyonu, performans metrikleri ve stres getirisiyle birebir aynı üretildi.
- Yeni iki politika × iki dönem × iki sembol × iki yön × iki kesim = **32 geçmiş-olay değişmezlik kontrolü** geçti. Yalnız tamamlanmış üst mumlar kullanıldı.
- Eski manifest kaynakları ve önceki rapor/ham mum-fonlama hash'leri doğrulandı. Veri indirme veya gerçek emir yok.
- Giriş kuralları sabit ama gerçekleşen girişler sabit değil: uzun taşıma sonraki fırsatları engelliyor. Eskiyle ortak giriş sayıları (açıklar dahil) ana senaryoda 10/11/8/7; 1h BOS'ta 10/12/8/7. Eski giriş sayıları 12/12/8/11. Bunlar eşleştirilmiş aynı-işlem karşılaştırması değildir.
- Yakın dönem BTC'de her iki yeni adayın birer açık pozisyonu var. Net getiri son kapanış değerini içerir; gelecekteki çıkış maliyeti dahil değildir. Diğer yeni aday hücrelerinde açık pozisyon yok.
- Her iki dönem daha önce incelenmiş geliştirme verisidir; bağımsız test/forward performans değildir. Etiketlere göre PnL kırılımı ayrı stratejilerin bağımsız sınanması anlamına gelmez.

## Yeniden çalıştırma

```powershell
python -m unittest discover -s tests -v
python tools/compare_scenario_policies.py
```

Deney 001–003'ün aynı yerel rapor, manifest ve önbellekleri gerekir. Araç ağdan alternatif veri indirmez; önceki kaynak/kanıt değişirse veya farklı sonuç üzerine yazılacaksa durur. Ayrıntılı çıktı `reports/experiments/experiment-004/results.json`; protokol/kod/veri özeti `manifest.json`. Ham piyasa verileri ve bu yerel ayrıntılı raporlar Git'e dahil edilmez.

Programatik kullanım: `replay_scenario(cfg, bars, side=1, policy='scenario_only', trade_start=...)`. Motor içi hesap sinyal üretmek içindir; ekonomik değerlendirme `orders_from` ve orijinal fiyat/fonlamayla `account` üzerinden yapılmalıdır. Short olay fiyatları yansıtılmış uzaydadır, gerçek piyasa seviyesi diye sunulmamalıdır.
