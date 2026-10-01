# Kriptotiks — çizim mantığı incelemesi 001

1 Ekim 2026. Amaç PnL veya kişinin toplam performansını değerlendirmek değil; fiyat grafiklerindeki bölge ve çizgi seçimini yeniden üretilebilir kurallara çevirmek. Kaynak: giriş yapılmış Telegram Web üzerinden yalnız [Kriptotiks Analiz](https://t.me/kriptotiks) kanalının grafik mesajları. Üyelik satın alınmadı, özel gruba girilmedi, mesaj gönderilmedi. Bu notlar ana strateji kodunu değiştirmez; Deney 004 onun çizim yönteminin testi değildir.

## İncelenen örnekler

Üç ayrı sembol, toplam dört fiyat grafiği. Paylaşım zamanları Telegram arayüzündeki gösterimdir. Aşağıdaki fiyatlar tarihsel çizim etiketleridir, güncel işlem önerisi değildir. Mor bant uçları sayısal etiket taşımadığı için yaklaşık gözlemdir; kesin OHLCV ölçümü değildir.

| Kaynak mesaj | Görselde zaman dilimi | Doğrudan görülen çizim |
|---|---|---|
| IMX, 26 Eylül 2026 14:13 | 4D / 4 günlük | Geçmişte birden çok mumun temas ettiği mor yatay bant; bant içinde yatay çizgi; fiyat bandın üstünde. Mavi 0,1616; yukarıda kırmızı kesikli 0,1993 / 0,2896 / 0,4798; aşağıda siyah kesikli 0,1065 / 0,0810. |
| IMX güncelleme, 28 Eylül 2026 11:50 | D / günlük | Aynı mor bant ve 0,1616 referansı daha küçük zaman diliminde korunuyor. 0,1993 kırmızı çizgisi de aynı. Bölge yaklaşık 0,135–0,158 aralığında; önceki grafikteki daha uzun geçmiş bu yakınlaştırmada yok. |
| LDO, 29 Eylül 2026 12:00 | W / haftalık | Mor bant eski destek kaybı ve sonraki birden çok temasın çevresinde; fiyat üstüne çıkmış. Mavi 0,4449; kırmızı 0,5239 / 0,7687; aşağıda siyah 0,2915 / 0,1499. |
| [EDU, 21 Eylül 2026 11:44](https://t.me/kriptotiks/21806) | W / haftalık | Uzun düşüş sonrası yatay tepki kümesi, bu bölgenin altına düşüş ve daha sonra geri kazanılması. Mor bant yaklaşık 0,041–0,046; eski uzun üst fitiller bandın dışında. Mavi 0,0464; kırmızı 0,0589 / 0,0900 / 0,1414; siyah 0,0314 / 0,0198 / 0,0105. |

EDU bağlantısı Telegram'ın “Copy Message Link” komutuyla doğrulandı. Diğerleri kanal ve paylaşım tarih/saatleriyle tanımlanmıştır; kopyalanmış doğrudan bağlantıları henüz yok. Görseller tarayıcıda açılarak incelendi, bazıları 2× yakınlaştırıldı. Yerel yüksek çözünürlüklü kopya alma denemesi tamamlanmadı; arşivlenmiş orijinal görsel varmış gibi sunulmaz.

## Gözlem, yorum ve bilinmeyenler

**Yüksek güvenli gözlem:** Üç sembolde de benzer bir görsel sözlük var: mor yatay bant, bant içi çizgi, bant civarı mavi fiyat etiketi, üstte kırmızı ve altta siyah kesikli seviyeler. IMX çiftinde üst zaman dilimindeki bölge daha küçük zaman dilimine taşınmış; güncellemede yeniden tanımlanmamış görünüyor. Bu, en az bu örnekte çoklu zaman dilimiyle aynı bölgenin izlenmesinin doğrudan kanıtı.

**Orta güvenli yorum:** Ortak kurgu, geçmişte önemli olan yatay bandın kaybedildikten sonra geri kazanılması; başka deyişle destek/direnç rol değişimi veya “reclaim” adayı. Bu adlandırma bizim yorumumuzdur. Görsel üstüne BOS/CHOCH/breaker açıklaması yazılmadığı için belirli bir ICT breaker tanımını doğrulanmış kabul edemeyiz. Bandın birden çok eski temas çevresinde bulunması, yalnız son karşı yönlü mumdan seçildiğini göstermiyor.

**EDU'dan dar ama önemli çıkarım:** Mor bant çevresindeki uzun üst fitiller bandın dışında kalıyor. Bu örnekte tüm tepki kümesinin veya tüm ilgili mumların en düşük–en yüksek aralığı boyanmamış. Bu, “her zaman sadece gövde kullanıyor” kuralını kanıtlamaz; kaynak mumu/alt zaman dilimi bilinmediği için tek mumlu OB ihtimalini de bütün strateji için kesin olarak dışlamaz.

**Seviye rolleri:** IMX güncelleme metni giriş ve TP takibinden söz ediyor; aynı mavi/kırmızı referanslar korunuyor. Kırmızı seviyeler üst hedef/referans adayları olarak yorumlanabilir. Ancak diğer grafiklerdeki bütün siyah alt seviyelerin stop olduğu, bant orta çizgisinin yüzde 50 dengesi olduğu, üst çizgilerin likidite/arz/Fibonacci veya sabit R katlarından türetildiği doğrulanmış değil. Renk tek başına anlam kanıtı değildir.

**Zamanlama sınırı:** Grafiklerde mevcut mum için kalan süre sayaçları görülüyor. Dolayısıyla açık üst zaman dilimi mumları görüntüde bulunuyor. Görselden “mutlaka haftalık/4 günlük kapanış bekleyerek girdi” sonucu çıkarılamaz. Alt kısımdaki yazılı tarih ile paylaşım tarihi her örnekte aynı değil; bunun dönem sonu etiketi mi başka bir açıklama mı olduğu doğrulanmadı. Mum serisiyle zaman hizası kurulmadan çizimler tarihsel giriş anı etiketi sayılmaz.

Henüz bilinmeyenler: bandı başlatan tam mum veya küme; sınır seçiminde gövde/fitil kararı; bant içi çizginin hesabı; zaman dilimi seçme koşulu; ilk kırılım mı yeniden test mi gerektiği; kapanışın hangi zaman diliminde beklendiği; bölgenin iptal kuralı; kırmızı/siyah seviyelerin türetildiği geçmiş; short tarafının gerçekten simetrik olup olmadığı.

## Mevcut motorla fark

Mevcut 4h/1h/15m deneyimiz bir yapı kırılmasından önceki son karşı yönlü mumun tam aralığını bölge adayı yapıyor. Burada gözlenen haftalık/4 günlük geniş yatay bantlar ve günlük izleme aynı operasyonel tanım değil. Çıkış süresini değiştirmek bu farkı gidermez. “Kriptotiks stratejisini uyguladık” denmemeli.

## Yeniden üretme için önerilen araştırma sırası

1. Başlangıç çizimlerini ve varsa sonraki aynı-grafik güncellemelerini ayrı etiketle. Başlangıçtaki fiyat geleceği görünmeden hangi bölgenin çizildiğini kaydet. Yalnız sonradan iyi görünen örnekleri seçme.
2. Veri kaynağı, parite, zaman dilimi ve mum açılış/kapanışlarını grafikle eşleştir. Özellikle 4 günlük gruplamanın başlangıç ankrajı ve haftalık seans/UTC hizası eşleşmeli. Ekrandaki açık mum, geriye dönük teste tamamlanmış mum gibi sokulamaz.
3. Önce **çizim eşleşmesini** sınayacak adayları oluştur: (A) eski tek mum tam-aralık OB; (B) teyitli swing/tepki fiyatlarının gövde ağırlıklı yatay kümesi; (C) belirgin düşüş öncesi çok mumlu taban. B ve C çıkarımsal adaylardır, doğrulanmış yazar kuralları değildir.
4. Bant seçilince sınırlarını dondur; sonraki fiyatı görerek taşımayı yasakla. İleride oluşan temasları eski tarihte bandı seçmek için kullanma. Pivotlar ancak sağ teyit mumları kapandığında bilinir.
5. Başarıyı ilk etapta PnL değil, bant aralığı örtüşmesi (IoU), sınır fiyat hatası, doğru tarih ve aynı bandı alt zaman dilimine taşıma tutarlılığıyla ölç. Çizim geliştirme ve doğrulama örneklerini ayrı tut; eşikleri kâr sonucuna göre ayarlama.
6. Çizim motoru makul eşleşince ayrı giriş deneyleri kur: bant geri kazanımı ve kırılım–yeniden test. Yalnız üst kapanışı bekleme ile alt zaman dilimi teyidi alternatifleri açıkça bizim deney varsayımımız olarak kaydedilmeli.
7. Sonrasında maliyetli tarihsel test/bağımsız dönem; kısmi çıkış ve dinamik koruma ayrı deneyler. Üç sembollük bu inceleme BIST veya short için kural doğrulaması değildir.

Bu turda çizim hipotezi ve belirsizlikler kaydedildi. Strateji, ana tarayıcı ve donmuş deney dosyaları değiştirilmedi; yeni performans koşusu yapılmadı.
