# Deney 003 — Yapı kırılması teyitli koruma seviyesi

Tek yeni değişken: korunan referansın taşınma kuralı. Deney 001/002 kaynaklarına, ana tarayıcıya ve BIST'e dokunulmaz; ayrı `priceaction/exit_research.py` modülü açıkça seçilerek kullanılır.

## Kesin tanım

Long için, 15m kapanışın daha önce bilinen ve henüz kırılmamış swing tepesini ilk kez yukarı geçmesi gerekir. Kırılma mumunun açılışında zaten onaylı olan **en son swing dip** adaydır. Bu dip kırılan tepenin kaynak mumundan sonra, kırılma mumundan önce oluşmuş olmalıdır. Ayrıca işlem girişinden önce oluşmuş dip kabul edilmez. Mevcut referansı yalnız yukarı taşıyan ve kapanışın altında kalan dip uygundur.

Aynı kapanışta yeni onaylanan dip bu kırılmada kullanılmaz. Eski bir kırılma sonradan tekrar kullanılamaz. Kırılma mumunun gövdesi için yeni ATR eşiği eklenmez; mevcut kapanış bazlı yapı kırılması tanımı kullanılır. Short için fiyat yansıması üzerinden tepe/dip ve yön tam simetriktir.

Her mumda önce mevcut referans ve kurulum/üst zaman dilimi geçersizlikleri kontrol edilir. Çıkış gerekiyorsa yeni referans taşıma işlemi yapılmaz. Taşınan seviye ancak sonraki mumlarda çıkış kontrolünde kullanılır. Fitil tek başına çıkış vermez; sinyal kapanışta, varsayımsal gerçekleşme sonraki açılıştadır. Başlangıç bölgesi, üst yapı bozulması ve sabit fiyat stopu olmaması aynen korunur.

## Karşılaştırma

- Yalnız long+short+MTF giriş modeli; süpürme zorunluluğu eklenmez.
- `pivot`: mevcut her onaylı lehte pivotta taşıma.
- `bos_confirmed`: yukarıdaki yeni kural.
- Deney 001'in 2026-04-03 → 2026-09-30 ve Deney 002'nin 2025-10-01 → 2026-04-01 kayıtlı dönemleri, kendi orijinal başlangıç/ısınma koşullarıyla ayrı değerlendirilir.
- Bunların ikisi de artık incelenmiş geliştirme verisidir. Yeni sonuçlar holdout/forward test diye sunulmaz; dönemler birleştirilip bağımsız portföy gibi raporlanmaz.
- BTC/ETH, aynı 10.000 USDT başlangıç ve %10 tahsis, aynı ücret/kayma/fonlama; ayrıca 2× ücret/kayma stresi. Parametre taraması yoktur.
- Giriş **kuralları** aynı kalır; farklı çıkış süresi daha sonraki girişleri engelleyebileceği için gerçekleşen girişler birebir aynı olmak zorunda değildir. Ortak giriş sayısı ayrıca raporlanır. Bu eşleştirilmiş tek-işlem karşılaştırması değil, sistem düzeyinde tek-kural karşılaştırmasıdır.
- İşlem sayısı, kazanma oranı, net getiri, kapanış bazlı düşüş, maliyet stresi ve açık pozisyon raporlanır. Az işlem veya artan zarar/düşüş göz ardı edilmez. Sonuç ne olursa olsun bu koşu otomatik olarak ana stratejiye terfi ettirilmez.

## Doğrulama

İki eski rapordaki mevcut MTF sonuçları yeniden aynen üretilmeli. Yeni politikada iki yön için veri kesimleri geçmiş olayları değiştirmemeli. Eski donmuş dosyalar ve raporlar korunmalı; yeni manifest kaynak ve veri özetlerini ayrı tutmalı. Tüm sonuçlar açıklanır; kazanan sembol/dönem seçilmez.
