# Deney 002 — Sonuç: hiçbir aday araştırma eleğini geçmedi

[Protokol](experiment-002-protocol.md) 30 Eylül 2026, 15:12:53 UTC'de yerel manifest ile sabitlendi; ardından veri indirildi ve tek koşu yapıldı. Ayarlar sonuçlara göre değiştirilmedi. Bu çalışma daha eski, bu projede daha önce incelenmemiş döneme aktarımı sınar; gerçek forward test veya kârlılık kanıtı değildir.

## Veri ve uygulama

- Ölçüm: 2025-10-01 00:00 UTC → 2026-04-01 00:00 UTC, 182 gün.
- BTCUSDT ve ETHUSDT için ayrı ayrı 17.472 ölçüm mumu; 14 günlük ısınmayla toplam 18.816 adet 15m mum ve 588 fonlama kaydı.
- Isınmada işlem açılmaz; ölçüm hesabı 10.000 USDT nakitle başlar. İşlem başına %10 sermaye tahsisidir, %10 kayıp limiti değildir.
- Normal: her yönde 10 bp komisyon + 5 bp kayma ve tarihsel fonlama. Stres: 20 bp + 10 bp, aynı tarihsel fonlama.
- Short sinyalleri fiyat yansımasıyla simetrik kurallardan çıkarılır, hesaplama gerçek fiyatlarla yapılır. Tanı dosyalarındaki `demand`/`korunan dip` etiketleri short için simetrik arz/korunan tepeyi anlatır.
- Gerçek emir gönderilmedi; ana tarayıcı veya BIST kuralları değiştirilmedi.

## Bütün sonuçlar

Getiriler işlem başına değil, bağımsız hesap toplamı içindir. Net değer varsa açık pozisyonun kapanış fiyatıyla değerini içerir. ETH temel long ve long+short modellerinde dönem sonunda açık işlem vardır; zorla kapatılmadığı için olası çıkış ücreti henüz düşülmez.

| Sembol | Varyant | Kapanmış işlem | Kazanma oranı | Net hesap getirisi | 2× maliyet | Azami düşüş |
|---|---|---:|---:|---:|---:|---:|
| BTC | Long | 15 | %40,00 | −%0,61 | −%1,06 | %0,81 |
| BTC | Long + short | 42 | %35,71 | −%1,26 | −%2,50 | %1,76 |
| BTC | Long + MTF | 5 | %40,00 | −%0,16 | −%0,31 | %0,19 |
| BTC | Long + short + MTF | 8 | %37,50 | −%0,11 | −%0,35 | %0,35 |
| BTC | Long + short + MTF + süpürme | 4 | %25,00 | −%0,22 | −%0,34 | %0,24 |
| ETH | Long | 27 | %22,22 | −%1,19 | −%2,00 | %1,79 |
| ETH | Long + short | 51 | %31,37 | −%0,77 | −%2,28 | %1,88 |
| ETH | Long + MTF | 7 | %42,86 | +%0,25 | +%0,04 | %0,18 |
| ETH | Long + short + MTF | 11 | %27,27 | −%0,30 | −%0,63 | %0,73 |
| ETH | Long + short + MTF + süpürme | 8 | %37,50 | −%0,06 | −%0,30 | %0,64 |

Düşüş yalnız mum kapanışları üzerinden ölçülür; mum içi, likidasyon ve gerçek gerçekleşme riski modellenmez.

## Hipotez hakkında karar

Süpürme şartı, long+short+MTF modeline göre ETH'de zararı azaltırken BTC'de sonucu kötüleştirdi. Yalnız 4 ve 8 kapanmış işlemle genelleme yapılamaz. Bu hipotezin güvenilir biçimde avantaj sağladığı gösterilemedi.

ETH long+MTF tek pozitif kombinasyondur; ancak sadece 7 işlem vardır. En iyi tek kapanmış işlemin PnL'sini hesap sonucundan çıkarınca +24,97 USDT yerine −6,24 USDT kalır. Bu, yeni bir simülasyon değil kazancın tek işleme bağımlılık kontrolüdür. Ayrıca BTC'deki karşılığı negatiftir. Dolayısıyla bunu kazanan strateji olarak seçmedik.

Önceden tanımlı asgari işlem sayısı, normal/stres getirisi, üç zaman bloğu ve tek kazanç bağımlılığı koşullarının tümünü iki sembolde birden sağlayan varyant: **yok**. 30 işlem eşiği istatistiksel anlamlılık sertifikası değildir.

## Önceki örneklemden tanı

2026-04-03 → 2026-09-30 geliştirme örnekleminin long+short temel modelindeki net kapanmış PnL, tanı amaçlı model etiketlerine ayrıldı:

| Sembol | Giriş modeli | İşlem / kayıp | Net PnL (USDT) |
|---|---|---:|---:|
| BTC | Breaker | 14 / 11 | −42,42 |
| BTC | Bölge devamı | 15 / 12 | −47,89 |
| BTC | Süpürmeli bölge | 14 / 11 | +36,10 |
| ETH | Breaker | 13 / 9 | +94,62 |
| ETH | Bölge devamı | 19 / 15 | −115,49 |
| ETH | Süpürmeli bölge | 20 / 15 | −61,07 |

Aynı model etiketi farklı sembollerde ters sonuçlar vermektedir. Etiket bazında sembole özel kural seçmek bu veriye uyum sağlama riski taşır. Çıkışların çoğunun korunan 15m seviyesinden gelmesi, stopu genişletmenin çözüm olduğu anlamına gelmez. Bu testte çıkışlar değiştirilmedi.

## Doğrulama ve kayıt

- 32 birim testi geçti.
- Eski iki sembolün dört varyantı için işlem sayısı, net getiri ve maliyet stresli getiri aynen yeniden üretildi.
- Yeni adayda iki sembol × iki yön × iki veri kesimi = 8 geçmiş-sinyal değişmezlik kontrolü geçti.
- Isınma sırasında emir oluşmadığı kontrol edildi. Kuralların/verinin özetleri ve değiştirilemeyen deney manifesti kaydedildi.
- Yerel kanıtlar: `reports/experiments/experiment-002/manifest.json`, `development-diagnostics.json`, `results.json`. Ham veriler `data/experiments` altında; Git'e dahil edilmez.

Sonraki araştırma için öneri: yeni eşikler denemek yerine az sayıda kaybeden/kazanan işlemi mum ve bölge seviyeleriyle tek tek inceleyerek giriş/çıkış tanımlarının piyasa yapısıyla gerçekten örtüşüp örtüşmediğini kontrol etmek. Bu dönem artık incelendi; gelecekteki adaylar için yeniden dokunulmamış test diye kullanılamaz. Gerçek ileriye dönük sanal hesap doğrulaması henüz yapılmadı.
