# Deney 001 — Yön ve çoklu zaman dilimi bölge filtresi

30 Eylül 2026'da gerçekleştirilen ilk karşılaştırma. Bu araştırma özeti bir başarı sertifikası veya yatırım önerisi değildir.

## Düzen

- Aynı 180 günlük Binance USD-M vadeli işlem verisi; BTCUSDT ve ETHUSDT ayrı değerlendirilmiştir.
- Her sembolde 17.280 kapanmış 15 dakika mumu ve 540 tarihsel fonlama kaydı.
- Bağlam 4 saat, kurulum 1 saat, giriş 15 dakika. Dört varyant aynı veri üzerinde çalışır.
- Her sembol bağımsız 10.000 USDT başlangıç, işlem başına %10 sermaye tahsisi; hesap getirisi aşağıdadır.
- Normal maliyet: her yönde 10 baz puan komisyon + 5 baz puan kayma; gerçekleşen tarihsel fonlama ayrıca dahil. Stres: komisyon ve kayma iki kat.
- Parametreler sonuçlara bakılarak bu deney içinde optimize edilmedi. Mevcut prototip ve yakın dönem daha önce incelendiğinden bu dönemler tarafsız/dokunulmamış holdout değildir.

## Sonuçlar

| Sembol | Varyant | Kapanmış işlem | Kazanma oranı | Net hesap getirisi | Kapanış bazlı azami düşüş | 2× maliyette getiri |
|---|---|---:|---:|---:|---:|---:|
| BTC | Yalnız long | 26 | %15,38 | −%0,57 | %1,17 | −%1,34 |
| BTC | Long + short | 43 | %20,93 | −%0,54 | %0,99 | −%1,81 |
| BTC | Long + MTF bölge filtresi | 9 | %22,22 | +%0,18 | %0,52 | −%0,09 |
| BTC | Long + short + MTF | 12 | %25,00 | +%0,17 | %0,58 | −%0,19 |
| ETH | Yalnız long | 32 | %15,63 | −%0,83 | %1,37 | −%1,77 |
| ETH | Long + short | 52 | %25,00 | −%0,82 | %1,52 | −%2,35 |
| ETH | Long + MTF bölge filtresi | 7 | %0,00 | −%0,75 | %0,75 | −%0,95 |
| ETH | Long + short + MTF | 12 | %8,33 | −%0,99 | %0,99 | −%1,35 |

Kazanma oranı yalnız kapanmış işlemlerden; hesap getirisi varsa açık pozisyonun kapanış fiyatıyla değerini içerir. İşlem sayıları küçük; MTF filtreleri örneklemi daha da daraltmıştır. Kapanış bazlı düşüş, mum içindeki riski göstermez.

## Yorum ve karar

BTC'de bu MTF giriş filtresi normal maliyet altında sonucu iyileştirdi, fakat maliyet stresine dayanmadı. ETH'de çoklu bölge/iki yön birleşimi daha iyi sonuç vermedi. Short eklemek işlem ve kazanma oranını bazı varyantlarda artırdı; maliyet sonrası belirgin bir ekonomik avantaj ortaya koymadı.

Bütün varyantlar iki kat maliyet altında negatiftir. Bu nedenle hiçbir aday otomatik olarak ana tarayıcıya terfi ettirilmedi. Sonraki araştırma, kaybeden işlemlerin giriş/çıkış gerekçelerinin görsel incelenmesi ve yeni adayların önceden belirlenmiş kurallarla henüz görülmemiş ileri dönemde değerlendirilmesidir. Kazanma oranını tek başına yükseltmek hedeflenmez.

BIST şirket işlemi/veri bütünlüğü doğrulaması tamamlanmadığından bu tabloya BIST kârlılık karşılaştırması eklenmedi; BIST günlük tarama olarak kalır.

## Tekrarlama

```powershell
python -m unittest discover -s tests -v
python tools/compare_variants.py --days 180
python tools/validate_experiments.py
```

Canlı veri kaynağı ve hareketli bitiş tarihi nedeniyle daha sonraki tekrarların sayıları değişebilir. Tam başlangıç/bitiş, parametreler ve fonlama sayısı yerel JSON raporunda; ilgili ham veri `data/experiments` önbelleğindedir. Bu dosyalar repoda yer almaz.

Kaynak: [Binance USD-M piyasa verileri ve fonlama API'si](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data).
