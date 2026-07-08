# INT-05 — Internal Flow Catalog & Opportunity Radar

Arya-AI Stajyer Proje Portföyü kapsamında geliştirilen, şirket içi bot/akış (flow) geçmişini analiz ederek yeni satış fırsatlarına, bakım önceliklerine ve ürünleşebilir task kataloglarına dönüştüren bir sistem.

**Teslim tarihi:** 17 Temmuz Cuma
**Ekip:** [Merve Mızraklı] (Yazılım Mühendisi) · [Sedat Bakla] (Bilgisayar Mühendisi) · [Beyza Öztürk] (Endüstri Mühendisi)

---

## 1. Problem Tanımı

Arya'nın mevcut akış/bot/task geçmişi ham veri olarak duruyor ama bu veriden:
- Hangi flow'ların **yeni satış fırsatı** olduğu,
- Hangi flow'ların **bakım açısından riskli** olduğu,
- Hangi flow'ların **ürünleşmeye / marketplace'e uygun** olduğu

net olarak görülemiyor. Bu proje, bu ham veriyi otomatik olarak sınıflandırıp skorlayan ve karar vericilere gösteren bir dashboard sunuyor.

---

## 2. Sistem Mimarisi
| Katman | Teknoloji | Sorumlu |
|---|---|---|
| Veri işleme & sınıflandırma | Python | [Merve Mızraklı] |
| Veri depolama | SQLite | [Merve Mızraklı] |
| Dashboard | Streamlit | [Sedat Bakla] |
| Skorlama mantığı (iş kuralı) | Excel prototip → Python | [Beyza Öztürk] |

> **Neden bu mimari seçildi?** — Ayrıntılı gerekçe için bkz. Bölüm 7.

---

## 3. Veri Seti

Proje 2 ana CSV dosyası + demo versiyonları üzerinden çalışır:

### `flow_catalog_sample.csv` (110 satır)
Şirket içi flow/bot kayıtlarının farazi veri seti.

| Kolon | Açıklama |
|---|---|
| Flow ID | Benzersiz kayıt numarası |
| Flow Name | Flow/bot adı (sınıflandırma bu alandaki anahtar kelimeye göre yapılır) |
| Customer | Flow'u kullanan müşteri (`Internal` = şirket içi) |
| Department | Flow'u içeride sahiplenen departman |
| Capability | Flow'un iş kabiliyeti kategorisi (ground truth — test/doğrulama amaçlı) |
| Run Count | Aylık çalışma sıklığı |
| Error Rate | Hata oranı (%) |
| Manual Time | Otomasyon öncesi manuel süre (dakika) |
| Transaction Volume | Aylık işlem hacmi |
| Customer Count | Bu Capability'yi kaç farklı müşterinin kullandığı (satılabilirlik göstergesi) |

### `task_capability_taxonomy.csv`
Keyword → Capability eşleştirme sözlüğü. Sistem, `Flow Name` içinde geçen anahtar kelimeye göre otomatik sınıflandırma yapar (örn. "Invoice" → Finance).

### Demo dosyaları
`flow_catalog_demo.csv` (10 satır) ve `task_capability_taxonomy_demo.csv` — hızlı test ve sunum gösterimi için küçültülmüş versiyonlar. Her capability'den en az bir örnek içerir; ayrıca bilerek bir satırda Department ≠ Capability bırakılmıştır (departman eşleşme kontrolünü test etmek için).

---

## 4. Skorlama Metodolojisi

Her flow için 4 kritere dayalı, 0-100 arası bir **ürünleşme skoru** hesaplanır:
| Kriter | Ağırlık | Hesaplanan Kolon | Mantık |
|---|---|---|---|
| Kullanım Yoğunluğu | %30 | `Run Count` (min-max normalize) | Az kullanılan flow'un ticari değeri düşük |
| Hata Etkisi | %25 | `Error Rate` (min-max normalize, ters) | Sık hata veren flow satışta risklidir |
| Yeniden Satılabilirlik | %25 | `Customer Count` (min-max normalize) | Zaten çok müşteride çalışan flow ürünleşmeye en hazır olandır |
| Ürünleşme Potansiyeli | %20 | `Manual Time` (min-max normalize) | Ne kadar çok zaman kazandırıyorsa o kadar değerli |

Tüm normalizasyon **min-max yöntemi** ile yapılır: `(Değer - Min) / (Max - Min) × 100`

Ağırlıkların ve formülün Excel prototipi: `skorlama_modeli.xlsx` — canlı formüllerle, ağırlıklar değiştirildiğinde otomatik güncellenir.

---

## 5. Kurulum

```bash
# Repo'yu klonlayın
git clone [repo-linki]
cd [proje-klasörü]

# Bağımlılıkları kurun
pip install -r requirements.txt

# Uygulamayı çalıştırın
streamlit run app.py
```

**Gereksinimler:** Python 3.x, pandas, streamlit, sqlite3 *(kesinleşince güncellenecek)*

---

## 6. Zorunlu Fonksiyonlar — Durum Takibi

- [ ] Flow catalog import (CSV)
- [ ] Kabiliyet sınıflandırma (keyword eşleştirme)
- [ ] Skorlama (4 kriter)
- [ ] Dashboard: Top 10 fırsat
- [ ] Dashboard: Riskli akışlar
- [ ] Dashboard: Müşteri genişleme önerisi
- [ ] Marketplace formatına export

---

## 7. Teknik Karar Notu — Neden Bu Mimari?

- Neden Streamlit ve React değil?
- Neden SQLite ve başka bir DB değil?
- Neden kural bazlı sınıflandırma ve ML tabanlı değil?
- Skorlama ağırlıkları neden bu şekilde seçildi?

---

## 8. Test Senaryoları ve Bilinen Limitler

### 8.1 Zorunlu Testler

| # | Senaryo | Beklenen Sonuç |
|---|---|---|
| T1 | `flow_catalog_sample.csv` import edilir | 110 satır hatasız yüklenir |
| T2 | "Invoice Processing" adlı bir flow sınıflandırılır | Taxonomy'deki "Invoice" → "Finance" eşleşmesiyle doğru capability atanır |
| T3 | Skorlama motoru 110 satır üzerinde çalıştırılır | Her satır için 0-100 arası tek bir SKOR üretilir |
| T4 | Dashboard açılır | Top 10 fırsat, riskli akışlar, müşteri genişleme önerisi bölümleri veri ile dolu gelir |

### 8.2 İş Değeri Testleri

| # | Senaryo | Neden Önemli |
|---|---|---|
| T5 | Aynı capability'de, biri 10 müşteride biri 1 müşteride kullanılan iki flow karşılaştırılır | 10 müşterili olan daha yüksek skor almalı — bu skorlama modelinin en kritik doğrulaması |
| T6 | Yüksek Error Rate + Yüksek Run Count olan flow | "Riskli akışlar" listesinde en üstte çıkmalı — Arya için en büyük itibar/müşteri kaybı riski |
| T7 | Bir müşterinin, başka müşterilerin kullandığı ama kendisinde olmayan bir capability'si | Dashboard'un "müşteri genişleme önerisi" bunu doğru tespit edip önermeli |

### 8.3 Opsiyonel Testler (zaman kalırsa)

| # | Senaryo | Ne kadar ek iş ister |
|---|---|---|
| T8 | Flow Name'de taxonomy'de hiç geçmeyen bir kelime varsa | Küçük — bilinmeyenleri "Diğer" kategorisine düşürecek 1 satırlık kontrol |
| T9 | Tüm satırlarda bir metrik aynı değerdeyse (min=max) | Küçük — normalizasyon formülüne 0'a bölme kontrolü (if payda==0) |
| T10 | CSV'de eksik/boş hücre varsa | Orta — satırı atlama veya varsayılan değer atama mantığı |

### 8.4 Bilinen Limitler

- Sınıflandırma tamamen **kural/keyword bazlı** çalışıyor; NLP/ML kullanılmıyor. Keyword geçmeyen ya da yazım hatalı flow adları yanlış sınıflandırılabilir.
- Veri seti **farazi** (gerçek şirket verisi değil), bu yüzden gerçek dünyadaki dağılım ve korelasyonları birebir yansıtmayabilir.
- Skorlama ağırlıkları (%30/%25/%25/%20) **sabit** — farklı iş öncelikleri için yeniden kalibre edilmesi gerekebilir.
- Sistem şu an **tek seferlik batch analiz** yapıyor; gerçek zamanlı/canlı veri akışı desteklemiyor.
- Boş/eksik veri ve birden fazla keyword çakışması gibi uç durumlar mevcut veri setinde test edilmedi; gerçek/canlı veriyle karşılaşılırsa ek geliştirme gerekebilir.

---

## 9. Ekip

| İsim | Rol | Sorumluluk |
|---|---|---|
| [Merve Mızraklı] | Yazılım Mühendisi | Sistem mimarisi,veri işleme,skorlama kodu |
| [Sedat Bakla] | Bilgisayar Mühendisi | Dashboard,sınıflandırma entegrasyon |
| [Beyza Öztürk] | Endüstri Mühendisi | Veri tasarımı, skorlama mantığı, dokümantasyon |

---

## 10. Demo

*(demo video linki buraya gelecek)*
