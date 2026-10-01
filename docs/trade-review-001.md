# İşlem incelemesi 001 — giriş, maliyet ve çıkış ayrımı

30 Eylül 2026. Deney 002'nin mevcut verisi tekrar incelendi; yeni strateji veya yeni performans testi çalıştırılmadı. Ana motor, sabitlenmiş protokol ve deney sonuçları değiştirilmedi.

## Kapsam

2025-10-01 → 2026-04-01 döneminde long+short temel modelin 93, long+short+MTF modelinin 19 kapanmış işlemi analiz edildi. Bunlar farklı stratejilerin sonuçlarıdır; toplamı 112 bağımsız fırsat diye yorumlanmaz, aynı fırsatlar tekrar bulunabilir. Açık işlemler bu tanıya dahil değildir. Bu nedenle ETH temel modelinin aşağıdaki kapanmış PnL'si, açık pozisyon içeren toplam hesap getirisinden farklıdır.

Her model/sembol için işlemler ve hesap getirisi Deney 002 ile birebir eşleştirildi. Her kapanmış işlemde şu denklem doğrulandı: ham açılış fiyat hareketi PnL − komisyon − kayma + fonlama = net PnL. Ham PnL gerçek strateji alternatifi değil, mevcut işlem miktarlarının maliyet ayrıştırmasıdır.

## Maliyet ayrıştırması

| Sembol / model | Kapanmış işlem | Ham fiyat PnL | Komisyon | Kayma | Fonlama | Net PnL |
|---|---:|---:|---:|---:|---:|---:|
| BTC temel | 42 | −1,11 | 83,42 | 41,71 | −0,05 | −126,29 |
| ETH temel | 51 | +56,32 | 101,50 | 50,75 | −0,97 | −96,90 |
| BTC MTF | 8 | +12,53 | 15,96 | 7,98 | −0,06 | −11,48 |
| ETH MTF | 11 | +3,36 | 22,08 | 11,04 | −0,28 | −30,03 |

Tüm tutarlar USDT. Komisyon ve kayma test varsayımlarıdır, gerçek hesapta ölçülmüş maliyetler değildir. İki MTF hesabının kapanmış işlemlerinde toplam +15,90 USDT ham fiyat hareketi, yaklaşık 57,40 USDT maliyet/fonlama etkisiyle −41,51 USDT olur. Bu toplam tek bir ortak portföy simülasyonu değildir.

## Çıkış yapısı

- MTF modelinde **19/19 işlemde** korunan seviye girişten sonra taşınmış; çıkış sinyali kapanışında başlangıç bölgesinin geçersizlik sınırı henüz aşılmamıştır. Bu sadece başlangıç fiyat sınırına göre tanıdır; bölgenin tüm yaşam döngüsünün hâlâ aktif olduğunu iddia etmez.
- Temel modelde aynı durum BTC'de 40/42, ETH'de 47/51 kapanmış işlemde görülür.
- Mevcut motor, long işlemde girişten sonra oluşan her onaylı daha yüksek 15m dip ile referansı yükseltir; yeni bir lehte yapı kırılması ayrıca aranmaz. Short tarafında bunun simetriği vardır.
- Koruma seviyesi taşınması hem kazanan hem kaybeden işlemlerde çalışıyor. Bu yüzden bu gözlem, daha geniş veya daha geç çıkışın daha iyi olduğunu kanıtlamaz. Daha geç çıkış kaybı da büyütebilir.

## Giriş ve lehte hareket

MTF modelinin bölge sınırından sinyal kapanışına uzaklığı medyan olarak BTC'de 1,95 ATR, ETH'de 2,32 ATR'dir. Bu bir tanı ölçüsüdür; bir eşik seçilmedi. Fiyat, teyit beklenirken bölgeden uzaklaşabiliyor.

MTF kayıplarının BTC'de 3/5'i, ETH'de 6/8'i en az bir kez giriş fiyatının lehte tarafında kapanmış. BTC kayıplarında medyan en iyi kapanış yalnız %0,09, ETH'de %0,41. Bu değerler ücret/fonlama sonrası çıkılabilir kâr değildir. İşlem içi en iyi fitil/kapanış geriye bakılarak seçilir; ona göre kâr alma kuralı uydurulamaz.

## Altı grafik örneği

Seçim kuralı her sembolün MTF işlemlerinde net PnL'ye göre en kötü, en iyi ve kayıpların üst ortanca sırasındaki işlemidir. Temsili rastgele örneklem veya bağımsız doğrulama değildir. Saatler UTC'dir.

| Örnek | Giriş UTC | Yön | Net PnL | Lehte azami hareket | Görsel bulgu |
|---|---|---|---:|---:|---|
| BTC en kötü | 2025-10-22 02:15 | Long | −12,59 | %0,00 | Yaklaşık 46 saatlik bölgeye dönüşte giriş; işlem fiyatı lehte ilerlemedi. Sadece çıkış sorunu diye açıklanamaz. |
| BTC en iyi | 2025-11-09 13:30 | Long | +15,00 | %2,45 | Lehte hareket boyunca referans yukarı taşınıp kazancı korudu. |
| BTC ortanca kayıp | 2025-10-05 17:00 | Long | −6,79 | %0,12 | Giriş sinyali bölgeden 3,95 ATR uzakta; takip eden yerel dip kırılması çıkış verdi. |
| ETH en kötü | 2026-03-03 13:15 | Short | −26,35 | %1,12 | Önce lehte hareket, ardından sert yukarı kapanış; 1976,51'e taşınan referans aşıldı. 2002,47 başlangıç sınırı sinyal kapanışında henüz aşılmamıştı. |
| ETH en iyi | 2025-10-01 08:30 | Long | +31,21 | %4,23 | Eski bir bölge ve uzak giriş bu örnekte kazançlı; basit yaş/mesafe filtresi tek başına çözüm sayılamaz. |
| ETH ortanca kayıp | 2025-10-01 01:30 | Long | −7,20 | %0,47 | Daralan koruma referansı çıkış verdi; sonrasındaki yükseliş ancak geriye bakınca görülür. |

Grafiklerde 15m mumlar, 1h bağlam, sinyal anında bilinen 1h/4h bölgeleri, giriş/çıkış açılışı ve kapanıştan sonra bilinen koruma yolu birlikte gösterilir. Bölgeler teyit zamanından önce çizilmez; giriş anındaki bantlar referans olarak uzatılır, sonraki aktif/pasif durumları gösterilmez. Gri alan çıkış sonrasıdır ve işlem istatistiklerine dahil değildir. 1h paneli bağlam için tamamlanmış tarihsel mumları gösterir; giriş sırasında kısmen oluşmuş saatin sonradan öğrenilen tamamı da görünür. Bu panel karar anı ekran görüntüsü değildir.

PNG dosyaları yerelde `reports/trade-review/` altında: `btcusdt-worst.png`, `btcusdt-best.png`, `btcusdt-median-loss.png`, `ethusdt-worst.png`, `ethusdt-best.png`, `ethusdt-median-loss.png`. Tam işlem tanısı: `review.json`.

## Araştırma kararı

Güvenilir giriş avantajı henüz gösterilmedi. Bir sonraki tek-değişkenli deney adayı: **korunan seviyeyi her küçük pivotta değil, işlem yönünde yeni bir yapı kırılması teyit edildiğinde, o kırılmadan önce bilinen uygun swing seviyesine taşımak**. Başlangıç bölgesi ve üst zaman dilimi geçersizliği yine korunur; sabit yüzdesel stop eklenmez.

Bu sadece hipotezdir; uygulanmadı ve daha iyi olduğu iddia edilmiyor. Önce kırılma/korunan swing eşleşmesi örneklerle kesin tanımlanmalı, ardından tek değişken olarak eski çıkışla karşılaştırılmalıdır. İncelenen iki dönem artık geliştirme verisidir; bunlarda bulunan iyileşme için ayrıca dokunulmamış dönem ve gerçek ileriye dönük sanal hesap gerekir.

## Tekrar çalıştırma

```powershell
python tools/review_trades.py
python -m unittest discover -s tests -v
# Grafikler için isteğe bağlı yerel bağımlılık:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install matplotlib==3.11.2
.\.venv\Scripts\python.exe tools/review_trades.py --charts
```

Araç yalnız Deney 002'nin yerel raporunu/önbelleğini okur; yeni piyasa verisi indirmez. Grafik bağımlılığı ana motor için gerekli değildir. 35 birim testi geçti; özellikle short fiyat yönü, çıkış mumunun sonradan oluşan uçlarının dışlanması ve örnek seçimi sınandı. Önceki deney kaynaklarının hash'leri ayrıca kontrol edildi.
