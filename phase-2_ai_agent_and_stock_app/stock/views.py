import pandas as pd
import json
from django.shortcuts import render, redirect
from datetime import datetime
from .forms import StokForm
from utils.ai import get_ai_response  # stok özelinde prompt içeriyor ama adı değişmedi

def stock_home(request):
    return redirect('stok-analizi')

def stok_analizi(request):
    context = {}

    if request.method == 'POST':
        form = StokForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['stok_dosyasi']
            df = pd.read_excel(excel_file)

            # ✅ Sütun adlarını normalize et (boşluk ve Türkçe karakterleri dönüştür)
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(" ", "_")
                .str.replace("ç", "c")
                .str.replace("ğ", "g")
                .str.replace("ı", "i")
                .str.replace("ö", "o")
                .str.replace("ş", "s")
                .str.replace("ü", "u")
            )

            # 📅 Stok yaşı hesapla
            df['stok_giris_tarihi'] = pd.to_datetime(df['stok_giris_tarihi'])
            bugun = pd.Timestamp(datetime.now().date())
            df['stok_yasi'] = (bugun - df['stok_giris_tarihi']).dt.days

            # 🧮 Yaş aralığı kategorisi ata
            def yas_araligi(gun):
                if gun <= 90:
                    return "1-3 Ay"
                elif gun <= 180:
                    return "3-6 Ay"
                elif gun <= 270:
                    return "6-9 Ay"
                elif gun <= 365:
                    return "9-12 Ay"
                elif gun <= 730:
                    return "12-24 Ay"
                else:
                    return "24+ Ay"
            df["yas_araligi"] = df["stok_yasi"].apply(yas_araligi)

            # 📊 Segment bazlı grafik verisi
            seg = df.groupby(["yas_araligi", "segment"]).size().unstack(fill_value=0)
            segment_labels = list(seg.index)
            segment_datasets = [
                {"label": col, "data": list(seg[col])}
                for col in seg.columns
            ]

            # 🏷️ Marka bazlı grafik verisi
            mark = df.groupby(["yas_araligi", "marka"]).size().unstack(fill_value=0)
            marka_labels = list(mark.index)
            marka_datasets = [
                {"label": col, "data": list(mark[col])}
                for col in mark.columns
            ]

            # 🤖 AI'dan yorum al
            prompt = f"Aşağıdaki stok segmenti verisine göre öneri ver:\n{seg.to_string()}"
            ai_yorum = get_ai_response(prompt)

            # 📦 Şablona verileri gönder
            context = {
                "form": form,
                "stok_analiz": df.to_dict(orient="records"),
                "segment_labels": json.dumps(segment_labels),
                "segment_datasets": json.dumps(segment_datasets),
                "marka_labels": json.dumps(marka_labels),
                "marka_datasets": json.dumps(marka_datasets),
                "stok_analiz_ai": ai_yorum
            }

    else:
        context["form"] = StokForm()

    return render(request, "stock/stok_analysis.html", context)
