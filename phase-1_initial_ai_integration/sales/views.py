# sales/views.py

# sales/views.py

from django.shortcuts import render
import pandas as pd
import unicodedata
import re
import dateparser
from .forms import SalesDataForm
from utils.ai import get_sales_suggestion  # AI entegrasyonu

# Sütun adlarını normalize eden fonksiyon
def normalize_column(col):
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
    col = col.strip().lower().replace(" ", "_")
    col = re.sub(r"[^\w]", "_", col)
    return col

# Esnek sütun eşleştirme tanımları
SALES_COLUMN_ALIASES = {
    'urun_adi':    ['urun_adi', 'urun_ad', 'product', 'product_name', 'item'],
    'tarih':       ['tarih', 'date', 'sales_date'],
    'gelir':       ['gelir', 'amount', 'revenue', 'sales_amount'],
}
TARGET_COLUMN_ALIASES = {
    'ay':           ['ay', 'month', 'period', 'tarih'],
    'hedef_adet':   ['hedef_adet', 'target_quantity', 'sales_target'],
    'hedef_gelir':  ['hedef_gelir', 'target_revenue', 'amount', 'revenue'],
}

def map_column(columns, aliases):
    mapped = {}
    for key, options in aliases.items():
        for opt in options:
            if opt in columns:
                mapped[key] = opt
                break
    return mapped

def sales_form_view(request):
    form = SalesDataForm()
    result = None
    warnings = []
    suggestion = None

    if request.method == "POST":
        form = SalesDataForm(request.POST, request.FILES)
        if form.is_valid():
            start_month  = form.cleaned_data['start_month']
            end_month    = form.cleaned_data['end_month']
            sales_file   = request.FILES['sales_excel']
            target_file  = request.FILES['target_excel']

            # --- Satış dosyasını oku ---
            try:
                df_sales = pd.read_excel(sales_file)
                df_sales.columns = [normalize_column(c) for c in df_sales.columns]
            except Exception as e:
                warnings.append(f"Satış Excel dosyası okunamadı: {e}")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # --- Hedef dosyasını oku ---
            try:
                df_target = pd.read_excel(target_file)
                df_target.columns = [normalize_column(c) for c in df_target.columns]
            except Exception as e:
                warnings.append(f"Hedef Excel dosyası okunamadı: {e}")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # --- Sütun eşleştirme ---
            sales_cols  = map_column(df_sales.columns, SALES_COLUMN_ALIASES)
            target_cols = map_column(df_target.columns, TARGET_COLUMN_ALIASES)

            for key in ['urun_adi','tarih','gelir']:
                if key not in sales_cols:
                    warnings.append(f"Satış dosyasında '{key}' için eşleşen sütun bulunamadı.")
            for key in ['ay','hedef_adet','hedef_gelir']:
                if key not in target_cols or 'yl' not in df_target.columns:
                    warnings.append(f"Hedef dosyasında '{key}' veya 'yl' sütunu eksik.")

            if warnings:
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # --- Satış verisini işle ---
            df_sales[sales_cols['tarih']] = pd.to_datetime(df_sales[sales_cols['tarih']], errors='coerce')
            df_sales['adet']   = 1
            df_sales['gelir']  = pd.to_numeric(df_sales[sales_cols['gelir']], errors='coerce').fillna(0)
            df_sales['year_month'] = df_sales[sales_cols['tarih']].dt.to_period('M')

            mask = (
                (df_sales[sales_cols['tarih']] >= pd.to_datetime(start_month)) &
                (df_sales[sales_cols['tarih']] <= pd.to_datetime(end_month) + pd.offsets.MonthEnd(1))
            )
            df_sales_filtered = df_sales.loc[mask]

            # --- Aylık satışları grupla ---
            monthly_sales = df_sales_filtered.groupby('year_month').agg({
                'adet': 'sum',
                'gelir': 'sum'
            }).reset_index()

            # --- Hedef verisini işle ---
            df_target['period'] = df_target.apply(
                lambda r: dateparser.parse(f"{r[target_cols['ay']]} {r['yl']}"), axis=1
            )
            df_target['period'] = pd.to_datetime(df_target['period'], errors='coerce').dt.to_period('M')
            df_target = df_target.dropna(subset=['period'])
            target_dict = df_target.set_index('period').to_dict('index')

            # --- Karşılaştırma listesi ---
            comparison = []
            for _, row in monthly_sales.iterrows():
                ym = row['year_month']
                hedef = target_dict.get(ym, {})
                tq  = hedef.get(target_cols['hedef_adet'])
                tr  = hedef.get(target_cols['hedef_gelir'])
                sq  = int(row['adet'])
                sr  = float(row['gelir'])
                pct = (sq / tq * 100) if tq else 0

                comparison.append({
                    "period": str(ym),
                    "sales_quantity": sq,
                    "sales_revenue":  sr,
                    "target_quantity": tq,
                    "target_revenue":  tr,
                    "completion_rate": pct
                })

            result = comparison

            # ————————— AI ÖNERİSİ (EN AZ 10 MADDE) ————————— #
            try:
                # Ürün bazlı toplam satış
                prod_series = (
                    df_sales_filtered
                    .groupby(sales_cols['urun_adi'])['adet']
                    .sum()
                    .sort_values(ascending=False)
                )
                top_prod, top_qty = prod_series.index[0], prod_series.iloc[0]
                low_prod, low_qty = prod_series.index[-1], prod_series.iloc[-1]

                # Aylık MoM değişim (son iki dönem)
                if len(result) >= 2:
                    prev, curr = result[-2], result[-1]
                    mom_qty = curr['sales_quantity'] - prev['sales_quantity']
                    mom_pct = (mom_qty / prev['sales_quantity'] * 100) if prev['sales_quantity'] else 0
                else:
                    mom_qty = mom_pct = None

                # Mevcut ay kalan adet
                this_month = result[-1]
                rem_qty = max((this_month['target_quantity'] or 0) - this_month['sales_quantity'], 0)

                # Prompt hazırlığı
                prompt = (
                    "Aşağıda aylık satış ve hedef verileri var. "
                    "Lütfen **EN AZ 10 MADDE** halinde, "
                    "ürün bazlı insight’lar, aylık değişim, "
                    "mevcut ay için kalan adet ve hangi üründen ne kadar satış gerektiği bilgilerini de ekleyerek "
                    "nokta atışı kampanya ve aksiyon önerileri sunun:\n\n"
                )
                prompt += f"- En çok satılan ürün: {top_prod} ({top_qty} adet)\n"
                prompt += f"- En az satılan ürün:  {low_prod} ({low_qty} adet)\n"
                if mom_qty is not None:
                    prompt += f"- Önceki aya göre değişim: {mom_qty:+d} adet ({mom_pct:.1f}%)\n"
                prompt += f"- {this_month['period']} için kalan adet: {rem_qty} adet\n\n"

                for r in result:
                    prompt += (
                        f"{r['period']}: Satış={r['sales_quantity']}/{r['target_quantity'] or 0} adet, "
                        f"Ciro={r['sales_revenue']:.0f}/{r['target_revenue'] or 0:.0f} TL, "
                        f"Tamamlama={r['completion_rate']:.1f}%\n"
                    )
                prompt += "\nLütfen en az 10 ayrı madde halinde yanıtlayın."

                suggestion = get_sales_suggestion(prompt)
            except Exception as e:
                suggestion = f"AI yanıtı alınamadı: {e}"
            # —————————————————————————————————————————————— #

        else:
            print("❌ Form is NOT valid")

    return render(request, "sales/sales_form.html", {
        "form": form,
        "result": result,
        "warnings": warnings,
        "suggestion": suggestion
    })
