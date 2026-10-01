# Deney 005 — Eşleştirilmiş ekleme karşılaştırması

Sonuç hesabından önce yazılmış araştırma protokolü. Kod, protokol ve mevcut veri hash'leri koşu öncesi manifestte sabitlenir. Parametre araması veya otomatik strateji terfisi yoktur. Kriptotiks'in doğrulanmış stratejisi değildir.

## Ortak setup üretimi

Bu yeni araştırma adaptörü önceki motorun işlemlerini aynen çoğaltmaz. Önceki iki BTC/ETH geliştirme dönemi ve tarihsel fonlama kullanılır; yeni veri indirilmez. BIST verisi olmadığı için BIST performansı ölçülmez.

- Yön için tamamlanmış 4h ve 1h yapı birlikte yukarı olmalı; short için aynı kurallar fiyat yansımasıyla uygulanır. Yansıma sabiti ilk mumdan alınır, ekonomik hesaplar gerçek fiyatlardadır.
- Sinyal mumunun açılışında bilinen, aktif 1h demand/breaker bölgelerinden kapanışın altındaki en yakın bölge ilk giriş; bunun tamamen altındaki en yakın ayrık bölge tek ekleme bölgesidir. Eşitliklerde en yeni bölge seçilir.
- Stop, ekleme bölgesinin altında kalan, önceden doğrulanmış 1h/4h swing dipleri ve aktif 4h demand/breaker alt sınırlarından en yakınıdır. Stop keyfi yüzde değildir.
- TP1/TP2, mevcut kapanışın ve ilk bölgenin üstünde kalan bilinen 1h/4h swing tepeleri ile aktif arz alt sınırlarının en yakın iki farklı fiyatıdır. Her biri gerçekleşmiş miktarın yarısını kapatır. Eksik stop/hedef/ikinci bölge varsa setup üretilmez; eksikler sayılır.
- Aynı yön ve ilk/ekleme bölgesi çifti yalnız bir kez planlanır. Plan tüm seviyeler bilindikten sonra, sinyal mumu kapanışında oluşturulur; ardından 8 adet 15m mum süresince ilk giriş aranır. Giriş için bölge içi 15m kapanış ve bölge içinde sonraki açılış gerekir. İlk TP sinyali eklemeyi kapatır. Stop/koruma 1h kapanışına ve mevcut BOS yönetim kurallarına bağlıdır. Yeni 4h dönüşü ayrıca çıkış tetiklemez.
- Üretim, hiçbir yönetim kolunun PnL'sini veya pozisyon durumunu okumaz. Kesişen setuplar bağımsız eşleştirilmiş denemelerdir; sonuçların toplamı tek hesap getirisi veya portföy düşüşü değildir.

## Üç yönetim kolu

1. `single`: Ortak referans riskin tamamını ilk bölgede kullan, ekleme yapma.
2. `scale_in`: Ortak referans riskin %50'sini ilk bölgede, %50'sini önceden belirlenmiş ikinci bölgede kullan. Miktarlar eşit olmak zorunda değil; maliyet ve stop mesafesiyle hesaplanır.
3. `half_control`: `scale_in` ile aynı ilk miktar; ekleme yok. Bu tanısal kontrol, eklemenin etkisini başlangıç miktarını küçültmenin etkisinden ayırır. Tam riskli iki ana kolla eşit riskli değildir.

Bağımsız setup hesabı 10.000 USDT, toplam giriş tutarı üst sınırı 1.000 USDT, maliyet dahil referans risk tavanı 100 USDT. Bunlar araştırma ölçeğidir, canlı yatırım önerisi değildir. İlk iki kolun planlanan normal maliyetli riskleri eşittir. Ortak R; iki kolun normal/2x maliyette tutar ve risk tavanlarını aşmaması için gerekirse birlikte küçültülür. Bu nedenle R her setup'ta farklı olabilir. Stop kapanışı ve sonraki açılış nedeniyle gerçekleşen kayıp R'yi aşabilir.

Normal maliyet her yönde 10 bp komisyon ve 5 bp kayma; gerçek fonlama. Stres her iki maliyeti ikiye katlar, miktar/plan/seviyeleri değiştirmez. Stres ve normal aynı ortak normal-maliyet R ile normalize edilir. Kaldıraç, likidasyon, emir defteri, minimum kontrat adımı simüle edilmez.

## Ölçüm ve doğrulama

Her dönem/sembol ve yön için üretilen, giriş yapan, kapanan, açık/bekleyen setup; ekleme gerçekleşme sayısı; ortalama net R, kapananlarda kazanma oranı, profit factor; ortalama ve en kötü setup kapanış-düşüşü/R; en kötü setup PnL/R; ücret/fonlama raporlanır. Net R açık pozisyon son kapanış değerini içerir, gelecekteki çıkış masrafını içermez. Kazanma oranı kısmi çıkış sayısı değil kapanmış setup bazındadır.

Eşleştirilmiş delta ve ekleme yapılan/yapılmayan kırılımlar raporlanır; sonradan seçilen bu alt gruplar bağımsız strateji değildir. Örneklem bağımlı ve dönemler önceden incelenmiş olduğundan anlamlılık/başarı garantisi iddiası yoktur. Portföy getirisi veya portföy azami düşüşü raporlanmaz.

Her veri hücresinin yarım/üç çeyrek kesiminde üretim ve tüm kolların geçmiş karar/gerçekleşme/özsermaye kayıtları değişmemeli. İlk iki kol ve kontrol aynı ilk giriş zamanına sahip olmalı. Normal/stres miktarları aynı olmalı. Eski deney kaynakları ve veri hash'leri korunmalı.

Eklemenin araştırmaya devam etmeye değer bulunması için dört hücrenin her birinde en az 30 kapanmış eşleşme ve 10 ekleme; normal ve stres ortalama R'si tek girişten yüksek; normal ortalama setup düşüşü/R tek girişten yüksek olmamalı. Geçse bile otomatik terfi yok; ayrı dokunulmamış veri/forward test gerekir. Koşullar sonuç görüldükten sonra değiştirilmez.
