# 📊 Smart Sales & Stock Assistant

**Smart Sales & Stock Assistant**, satış ve stok verilerini analiz eden, kullanıcıdan gelen hedeflere göre karşılaştırmalı performans sunan ve yapay zekâ destekli önerilerde bulunan web tabanlı bir Django uygulamasıdır. 
Register sayfasında kullanıcı adı ve şifre ile kayıt olduktan sonra giriş sağlayabilirsiniz, anasayfada satış ve stok analizi olarak iki seçenek bulunmaktadır.
-Satış seçildikten sonra gelen sayfada excel dosyaları yükleyerek sisteme satış gerçekleşen ve hedef bilgilerinin girişi sağlanır, ek olarak yüklediğiniz data içerisinde analizini yapılmasını istediğiniz zaman aralığını sayfadaki filtelerden seçmeniz gerekmektedir.Gönder butonuna basınca satış analizi ve yapay zeka'nın satışı arttırmak için alınabilecek aksiyon ve analizleri gösterilir. Ek olarak ay bazlı hedef gerçekleşen grafikleri de yer almaktadır.
-Stok seçildikten sonra sadece stok excel dosyası yüklenir, göndere bastıktan sonra ekranın üst kısmında AI destekli satış analizi ve satışı arttırmaya yönelik strateji önerileri yer almaktadır, ekranın alt kısmında ise stok yaş aralığına göre ürün segment dağılımı ve yaş aralığına göre stokta bekleyen marka dağılımı grafikleri gösterilir. 
---

** Örnek satış, hedef ve stok excel dosyaları proje dosyasında yer almaktadır bu dosyalar ile test gerçekleştirilebilir.
---

## 🚀 Özellikler

- Aylık satış verilerini hedeflerle karşılaştırma
- Gerçekleşme oranlarını hesaplama
- Aylık grafiksel analiz (adet & gelir)
- Stok yaşı hesaplama ve sınıflandırma (Stok modülüyle birlikte)
- AI destekli satış önerileri (OpenAI GPT-3.5-Turbo API)
- Türkçe & İngilizce dosya destekli sütun eşleştirme
- Bootstrap destekli responsive kullanıcı arayüzü

---

## ⚙️ Kullanılan Teknolojiler

| Alan         | Teknoloji                      |
|--------------|--------------------------------|
| Backend      | Python 3.10+, Django 4.x       |
| Frontend     | HTML, Bootstrap, Chart.js      |
| AI           | OpenAI GPT-3.5 Turbo           |
| Data         | Pandas, Dateparser             |
| Diğer        | python-dotenv                  |

---

## 📦 Kurulum Talimatları

Aşağıdaki adımlarla projeyi çalıştırabilirsiniz:

### 1. Projeyi klonlayın:

```bash
git clone https://github.com/eceerseven/Smart-Sales-Stock-Assistant.git
cd smart-sales-assistant
```

### 2. Sanal ortam oluşturun ve aktif edin:

```bash
python -m venv venv
source venv/bin/activate  # Windows için: venv\Scripts\activate
```

### 3. Gereksinimleri yükleyin:

```bash
pip install -r requirements.txt
```

### 4. Ortam değişkenlerini girin:

Proje kök dizinine bir `.env` dosyası oluşturun ve içine aşağıdaki satırı ekleyin:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

> Not: `.env` dosyasının adı **`.env.txt` değil**, sadece `.env` olmalıdır. Gerekirse dosya uzantısını gösterip düzeltin.

### 5. Sunucuyu başlatın:

```bash
python manage.py runserver
```

Uygulama şu adreste çalışacaktır: `http://127.0.0.1:8000/`

---

## 🧪 Nasıl Kullanılır?

1. Ana sayfada "Sales" veya "Stock" modülüne giriş yapın.
2. Satış takibi için:
   - Hedef dosyasını (.xlsx)
   - Satış dosyasını (.xlsx)
   - Başlangıç ve bitiş aylarını girin
3. Gönder'e tıklayın.
4. Aylık performans grafikleri ve AI önerileri görüntülenir.
5. Stok takibi için sadece stok verisi yüklenmesi yeterlidir (.xlsx)
---

## 📁 Klasör Yapısı (Özet)

```
smart-sales-assistant/
├── sales/
│   ├── views.py
│   ├── forms.py
│   ├── templates/sales/sales_form.html
│   └── ...
├── stock/
├── utils/
│   └── ai.py
├── .env
├── requirements.txt
├── README.md
└── manage.py
```

---

## 💡 Notlar

- AI modülü için GPT-3.5 Turbo kullanılır. Token limiti ve maliyet için OpenAI panelinizi kontrol ediniz.
- Giriş ekranı, kullanıcılar arasında yönlendirme sağlar; doğrudan /sales/ veya /stock/ sayfasına gidebilirsiniz.

---

## 👩‍💻 Geliştirici

**Ece Erseven**  
AI First Developer | Business Analytics

---

Projenin çalışmasında sorun yaşarsanız benimle iletişime geçebilirsiniz. 
