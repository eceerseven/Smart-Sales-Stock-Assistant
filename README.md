
# 📊 Smart Sales & Stock Assistant

**Smart Sales & Stock Assistant**, satış ve stok verilerini analiz eden, kullanıcıdan gelen hedeflere göre karşılaştırmalı performans sunan ve yapay zekâ destekli önerilerde bulunan web tabanlı bir Django uygulamasıdır.  
Register sayfasında kullanıcı adı, şifre ve mail bilgileri ile kayıt olduktan sonra giriş sağlayabilirsiniz, anasayfada satış ve stok analizi olarak iki seçenek bulunmaktadır.  
Satış seçildikten sonra gelen sayfada excel dosyaları yükleyerek sisteme satış gerçekleşen ve hedef bilgilerinin girişi sağlanır, ek olarak yüklediğiniz data içerisinde analizini yapılmasını istediğiniz zaman aralığını sayfadaki filtrelerden seçmeniz gerekmektedir.  
Gönder butonuna basınca satış analizi ve yapay zeka'nın satışı arttırmak için alınabilecek aksiyon-analizleri ve ay bazlı hedef gerçekleşen grafikleri ekranda gösterilir.

---

**ÖNEMLİ: Örnek satış, hedef ve stok excel dosyaları proje dosyasında yer almaktadır, bu dosyalar ile test edebilirsiniz.**  
**Stok analiz fonksiyonları ikinci aşamada entegre edilmiştir ve aktif çalışmaktadır.**

---

## 🚀 Özellikler

- Aylık satış verilerini hedeflerle karşılaştırma
- Gerçekleşme oranlarını hesaplama
- Aylık grafiksel analiz (adet & gelir)
- AI destekli satış önerileri (OpenAI GPT-3.5-Turbo API)
- Stok yaşı hesaplama ve yaş aralıklarına göre sınıflandırma:
  - 1–3 ay, 3–6 ay, 6–9 ay, 9–12 ay, 12–24 ay, 24+ ay
- Segment bazlı stok dağılımı grafiği (Chart.js)
- Stok yönetimi için AI önerileri
- Kullanıcının yüklediği raporlar veritabanında tutulur
  - Eğer aynı kullanıcı ve aynı ay için kayıt varsa *güncellenir*
  - Yoksa yeni kayıt olarak *eklenir*
- AI Agent entegrasyonu: Satış verisi yüklemeyen kullanıcılar tespit edilip, **karar destekli şekilde hatırlatma e-postası gönderilir**

---

## ⚙️ Kullanılan Teknolojiler

| Alan         | Teknoloji                      |
|--------------|--------------------------------|
| Backend      | Python 3.10+, Django 4.x       |
| Frontend     | HTML, Bootstrap, Chart.js      |
| AI           | OpenAI GPT-3.5 Turbo           |
| Data         | Pandas, Dateparser, Openpyxl   |
| Mail         | Django Email Backend (SMTP)    |
| Diğer        | python-dotenv, SQLite3         |

---

## 📦 Kurulum Talimatları

### 1. Projeyi klonlayın:

```bash
git clone https://github.com/eceerseven/Smart-Sales-Stock-Assistant.git
cd Smart-Sales-Stock-Assistant
```

### 2. Sanal ortam oluşturun ve aktif edin:

```bash
python -m venv projectEnvironment
projectEnvironment\Scripts\activate
```

### 3. Gereksinimleri yükleyin:

```bash
pip install -r requirements.txt
```

> 💡 *Phase 2 ile birlikte aşağıdaki kütüphaneler eklenmiştir:*
>
> ```text
> openai
> python-dotenv
> dateparser
> ```

### 4. Ortam değişkenlerini girin:

Proje kök dizinine `.env` adında bir dosya oluşturun:

```env
OPENAI_API_KEY=your_openai_api_key
EMAIL_HOST_USER=your_email_address
EMAIL_HOST_PASSWORD=your_email_password
```

> `.env.txt` değil, sadece `.env` olmalı!

---

## 🧪 Nasıl Kullanılır?

1. Ana sayfada "Sales" veya "Stock" modülüne giriş yapın.
2. Satış takibi için:
   - Hedef dosyasını (.xlsx)
   - Satış dosyasını (.xlsx)
   - Başlangıç ve bitiş aylarını seçin
3. Gönder'e tıklayın
4. Performans grafikleri ve AI analizleri görüntülenir

---

## 🧪 Stok Analizi Nasıl Çalışır?

1. `Stock` sayfasından `.xlsx` dosyanızı yükleyin
2. Sistem, ürün giriş tarihine göre stok yaşını hesaplar
3. Aşağıdaki yaş gruplarına göre segment bazlı grafik gösterilir:
   - 1–3 ay, 3–6 ay, 6–9 ay, 9–12 ay, 12–24 ay, 24+ ay
4. Ekranda AI yorumları gösterilir
5. Örnek dosya `example_stock_data.xlsx` olarak proje içinde mevcuttur

---

## 📤 Phase 2 AI Agent - Hatırlatma Maili Gönderimi 

Veri yüklemeyen kullanıcılar tespit edilir.  
OpenAI ile çalışan AI Agent, durumu değerlendirir ve uygunsa e-posta gönderilir.

**Test için komut:**

```bash
python manage.py send_reminders
```

> `.env` dosyasındaki e-posta ve API bilgileri doğru olmalıdır.

---

## 📁 Klasör Yapısı (Özet)

```
Smart-Sales-Stock-Assistant/
├── phase-1_initial_ai_integration/
│   └── (ilk sürüm kodları-güncellemeler buraya da eklendi)
├── phase-2_ai_agent_and_stock_app/
│   ├── sales/
│   ├── stock/
│   ├── mailagent/
│   ├── utils/
│   └── ...
├── requirements.txt
├── README.md
└── manage.py
```

---

## 👩‍💻 Geliştirici

**Ece Erseven**  
AI First Developer | Business Analytics  
📫 GitHub: [@eceerseven](https://github.com/eceerseven)

---

Herhangi bir sorunuz varsa benimle iletişime geçebilirsiniz. Projeyi test ettiğinizde geri bildirim vermeyi unutmayın 😊
