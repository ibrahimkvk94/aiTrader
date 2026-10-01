# Deney 005 — Eklemeli / eklemesiz yönetim sonucu

1 Ekim 2026. Protokol, kaynaklar ve veri hash'leri sonuç hesabından önce 12:05:56 UTC'de yerel manifestte sabitlendi. [Önceden belirlenen kurallar](experiment-005-protocol.md) değiştirilmedi. Canlı emir yok; ana tarayıcıya terfi yok.

## Kısa sonuç

Eşit toplam referans riskli eklemeli kol dört hücrede de ortalama net R'yi artırdı; eski iki hücreyi pozitif yapamadı. Ortalama setup düşüşü dört hücrede azaldı; **en kötü setup düşüşü üç hücrede arttı**. İki kat maliyette eklemeli kolun dört hücresinden üçü negatif. Örneklem ve ekleme sayısı önceden belirlenen araştırma eleğini geçmiyor.

329 planın 92'si giriş yaptı; 91'i kapandı, yakın dönem BTC'de bir setup açık. 237 plan giriş yapmadan iptal oldu. Ekleme 28 setup'ta gerçekleşti. Bunlar bağımsız ve bazen çakışan eşleşmiş setup denemeleri; 92 girişin toplam PnL'si tek hesap getirisi değildir. BTC/ETH ve long/short aynı portföyde yönetilmedi.

Bu deney yeni, açık kurallı bir bölge üreticisini kullanır; eski deneylerin girişleriyle veya eski kazanma oranlarıyla birebir karşılaştırılamaz. Kriptotiks'in birebir stratejisi olduğu iddia edilmez.

## Eşit riskli ana karşılaştırma

R, her setup için maliyet ve sermaye tavanlarıyla belirlenen ortak normal-maliyetli referans kayıp tutarıdır; tüm setuplarda 100 USDT değildir. `single` ilk girişte 1R; `scale_in` ilk bölgede 0,5R ve ikinci bölgede 0,5R planlar. Gerçekleşmeyen eklemenin bütçesi nakitte kalır. Kapanışla stop/sonraki açılış nedeniyle kayıp 1R'yi aşabilir. Ortalama net R, giriş yapan tüm setupları ve açık setup'ın son kapanış değerini içerir.

| Dönem (UTC, bitiş hariç) / sembol | Giriş / kapanan / eklenen | Tek giriş ort. net R | Eklemeli ort. net R | Fark R | Kazanma oranı tek / eklemeli |
|---|---:|---:|---:|---:|---:|
| 2026-04-03 → 2026-09-30 / BTC | 22 / 21 / 5 | +0,0384 | +0,1430 | +0,1046 | %76,19 / %76,19 |
| 2026-04-03 → 2026-09-30 / ETH | 26 / 26 / 9 | +0,0121 | +0,0591 | +0,0469 | %73,08 / %73,08 |
| 2025-10-01 → 2026-04-01 / BTC | 15 / 15 / 4 | −0,0919 | −0,0750 | +0,0170 | %46,67 / %53,33 |
| 2025-10-01 → 2026-04-01 / ETH | 29 / 29 / 10 | −0,0052 | −0,0049 | +0,0003 | %65,52 / %65,52 |

Kazanma oranı yalnız kapanmış setup başına, tüm kısmi çıkışlar/komisyon/fonlama birleştirilerek hesaplanır. Yüksek kazanma oranı pozitif beklenti garantisi değildir: eski ETH'de %65,52 kazanma oranına rağmen iki kol da negatiftir. Eski ETH farkı ekonomik olarak çok küçüktür.

## Risk ve maliyet

| Hücre | Ortalama setup düşüşü/R tek → eklemeli | En kötü setup düşüşü/R tek → eklemeli | 2× maliyet ort. net R tek → eklemeli |
|---|---:|---:|---:|
| Yakın BTC | 0,411 → 0,309 | 0,995 → 1,531 | −0,0768 → +0,0561 |
| Yakın ETH | 0,462 → 0,393 | 1,155 → 1,501 | −0,0961 → −0,0335 |
| Eski BTC | 0,472 → 0,341 | 1,431 → 1,053 | −0,1807 → −0,1312 |
| Eski ETH | 0,518 → 0,440 | 1,343 → 2,179 | −0,0709 → −0,0576 |

Düşüş, setup hesabının kapanış özsermaye tepesinden sonraki kaybıdır; portföy düşüşü veya başlangıç sermayesinden net zarar değildir. Eski ETH'deki 2,179R düşüşün yanında en kötü net setup sonucu tek girişte −1,324R, eklemelide −1,566R'dir. Mum içi risk daha büyük olabilir.

Her yönde normal 10 bp komisyon + 5 bp kayma ve tarihsel fonlama kullanıldı. 2× koşu miktar ve seviyeleri değiştirmeden komisyon/kaymayı ikiye katlar, fonlamayı aynen tutar. Açık PnL gelecekteki çıkış maliyetini içermez. Kaldıraç, likidasyon ve minimum kontrat adımı modellenmez.

## Ekleme mi, küçük başlamak mı?

`half_control`, eklemeli kolla birebir aynı ilk miktarı kullanır ama ekleme yapmaz. Toplam plan riski ana kolların yarısıdır; eşit riskli alternatif değil, etkileri ayıran kontroldür.

| Hücre | Küçük ilk giriş, ekleme yok: ort. net R | Eklemeli eksi bu kontrol: ort. R |
|---|---:|---:|
| Yakın BTC | +0,0192 | +0,1238 |
| Yakın ETH | +0,0061 | +0,0530 |
| Eski BTC | −0,0460 | −0,0290 |
| Eski ETH | −0,0026 | −0,0023 |

Dolayısıyla eski dönemde tam büyüklükte tek girişe göre iyileşmeyi doğrudan eklemeye bağlayamayız: küçük başlayıp hiç eklememek daha iyi sonuç verdi. Yakın dönemde ise ekleme, aynı ilk miktarlı kontrolün üzerinde net katkı sağladı. Kontrolün düşüşü dört hücrede de eklemeli koldan daha düşüktür.

Ekleme yapılan setuplarda, tam riskli tek girişe karşı daha iyi/kötü sonuç sayıları yakın BTC 5/0, yakın ETH 7/2, eski BTC 4/0, eski ETH 4/6'dır. Aynı küçük ilk girişli kontrole karşı bu sayılar 4/1, 4/5, 2/2, 4/6'dır. Gruplar gerçekleşen eklemeye göre sonradan ayrılmıştır; ayrı bir giriş stratejisi veya nedensel kanıt değildir.

## Long / short ayrımı

| Hücre / yön | Giriş / ekleme | Tek giriş ort. R | Eklemeli ort. R |
|---|---:|---:|---:|
| Yakın BTC long | 12 / 0 | −0,0323 | −0,0161 |
| Yakın BTC short | 10 / 5 | +0,1232 | +0,3340 |
| Yakın ETH long | 16 / 3 | +0,0630 | +0,0961 |
| Yakın ETH short | 10 / 6 | −0,0692 | −0,0001 |
| Eski BTC long | 6 / 2 | −0,3157 | −0,2288 |
| Eski BTC short | 9 / 2 | +0,0573 | +0,0276 |
| Eski ETH long | 12 / 6 | −0,2167 | −0,0919 |
| Eski ETH short | 17 / 4 | +0,1441 | +0,0566 |

Yakın BTC long'da hiç ekleme yok; fark sadece ilk pozisyonun yarıya inmesinden geliyor. Eski dönemde iki sembolün short tarafı eklemeli kolda kötüleşti. Toplam dört hücredeki iyileşme her yönde iyileşme demek değildir. Bu kırılımlar görülüp yön filtresi eklenmedi.

## Karar ve sınırlar

Hiçbir hücre en az 30 kapanmış eşleşme koşulunu geçmedi; yalnız eski ETH en az 10 ekleme koşulunu sağladı. Normal/stres göreli iyileşme ve ortalama düşüş koşulları dört hücrede sağlandı. Buna rağmen araştırma eleği bütünüyle başarısız; ana tarayıcı değişmedi.

İki dönem daha önce incelenmiş geliştirme verisidir; bağımsız holdout veya ileri sanal işlem değildir. Sonuç, eklemeyi varsayılan açmak için yeterli değil. Sonraki adım kuralları değiştirmeden dokunulmamış veri veya ileri sanal işlemlerde daha fazla eşleşme toplamak; özellikle kuyruk kaybı ve eklemelerin kontrol koluna katkısını izlemektir. BIST için doğrulanmış seans/şirket işlemi verisiyle ayrı deney gerekir; burada BIST/spot başarısı ölçülmedi.

## Yeniden üretme ve kanıt

```powershell
python -m unittest discover -s tests -v
python tools/compare_additions.py
```

- 91 birim testi geçti; 6 yeni test eşit risk/miktar, long/short, kontrol, bilinirlik, raporlama ve geçmiş-kayıt denetimini kapsıyor.
- Dört veri hücresi × iki kesimde sekiz geçmiş-değişmezlik kontrolü geçti. Her kesimde tüm üretilen planlar ve plan başına altı kolun (üç politika × iki maliyet) geçmiş kararları, gerçekleşmeleri ve özsermaye noktaları karşılaştırıldı.
- Her eşleşmede üç kolun ilk giriş zamanı aynı. Stres miktarları normalle aynı; kaynak/ham veri/fonlama ve önceki deney kanıt hash'leri doğrulandı.
- Ayrıntılar yerel `reports/experiments/experiment-005/results.json`, `manifest.json` ve dört hücre JSON'unda. Her planın seviye kaynağı/bilinme zamanı, orijinal planı, R'si, gerçekleşmeleri, kararları ve özsermaye eğrisi saklanır. Short seviye kanıtı yansıtılmış uzayda etiketlidir; gerçek işlem seviyeleri plan alanındadır.
- Farklı manifest/sonuç üzerine yazılmaz. Ham veri ve yerel raporlar Git'e dahil edilmez. Canlı emir ve ağdan veri indirme yok.
