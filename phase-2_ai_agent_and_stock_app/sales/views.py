# sales/views.py

from django.shortcuts import render
import pandas as pd
import unicodedata
import re
import dateparser
import datetime
from .forms import SalesDataForm
from utils.ai import get_sales_suggestion  # AI entegrasyonu
from .models import SalesRecord

# ----------------------------- Yardımcılar -----------------------------

def normalize_column(col):
    col = unicodedata.normalize('NFKD', col).encode('ascii', 'ignore').decode('utf-8')
    col = col.strip().lower().replace(" ", "_")
    col = re.sub(r"[^\w]", "_", col)
    return col

# Esnek sütun eşleştirme tanımları (segment opsiyonel)
SALES_COLUMN_ALIASES = {
    'urun_adi':    ['urun_adi', 'urun_ad', 'product', 'product_name', 'item', 'sku_adi'],
    'tarih':       ['tarih', 'date', 'sales_date'],
    'gelir':       ['gelir', 'amount', 'revenue', 'sales_amount'],
    'segment':     ['segment','Segment' 'kategori', 'category', 'urun_grubu'],  # opsiyonel
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

# --- normalize sonrası olası ÇİFT sütun adlarını güvenle benzersizleştir ---
def _dedupe_columns(cols):
    seen = {}
    out = []
    for c in cols:
        if c in seen:
            seen[c] += 1
            out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0
            out.append(c)
    return out

# ---------------------- Sayı formatlama (TR binlik ayraç) ----------------------

def _fmt_thousands(num):
    """10200200 -> '10.200.200' (tam sayı)"""
    try:
        n = int(round(float(num)))
        return "{:,}".format(n).replace(",", ".")
    except Exception:
        return str(num)

def _fmt_in_text_contextual(s: str) -> str:
    """
    Metindeki büyük sayıları yalnızca ' TL' veya ' adet' ile biten kalıplarda 10.200.200 formatına çevirir.
    - 2025 gibi yılları bozmaz
    - % işaretlerinden sonraki sayılara dokunmaz
    """
    def repl(match):
        val = match.group(1)
        return _fmt_thousands(val)
    # ... 12345 TL
    s = re.sub(r'(\d{4,})(?=(?:\s*TL\b))', repl, s)
    # ... 12345 adet
    s = re.sub(r'(\d{4,})(?=(?:\s*adet\b))', repl, s)
    # ... =12345 TL, parantez, vs.
    s = re.sub(r'(\d{4,})(?=(?:\s*TL[) ,.;:!?]))', repl, s)
    s = re.sub(r'(\d{4,})(?=(?:\s*adet[) ,.;:!?]))', repl, s)
    return s

# ---------------------- ÇIKTI TEMİZLİĞİ & GARANTİ KATMANI ----------------------

LABEL_PATTERNS = [
    r'^\s*(Öneri|Çözüm|Süre|Hedef|Aksiyon|Not|Recommendation|Solution|Target|Action)\s*[:\-]\s*',
    r'^\s*(Madde|Madde\s*\d+)\s*[:\-]\s*',
]
BULLET_PAT = r'^\s*(?:[-*•]+|\d+[.)])\s*'

def _strip_labels(text: str) -> str:
    s = re.sub(BULLET_PAT, '', text).strip()
    for pat in LABEL_PATTERNS:
        s = re.sub(pat, '', s, flags=re.IGNORECASE).strip()
    return s.strip('“”"').strip()

def _ensure_sentence(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    if s[-1] not in '.!?':
        s = s + '.'
    return s

def _min_three_sentences(lines):
    """En az 3 cümle kuralını uygula (noktalama sayımına dayalı kaba kontrol)."""
    good = []
    for l in lines:
        punct = l.count('.') + l.count('!') + l.count('?')
        if punct < 3:
            continue
        good.append(l)
    return good

def _prioritize_and_cap(lines, cap=10):
    cleaned = []
    for l in lines:
        l = l.strip()
        if not l:
            continue
        cleaned.append(l)
    return cleaned[:cap]

def _renumber_1paren(lines):
    """1), 2), ... numaralama uygula."""
    return [f"{i+1}) {l}" for i, l in enumerate(lines)]

def _build_fallback_items(metrics, need):
    out = []

    last_month = metrics.get('last_month', 'ilgili')
    low_prod = metrics.get('low_prod_name') or "belirli bir ürün"
    top_seg = metrics.get('top_segment_name', 'bilinmiyor')
    top_seg_q = metrics.get('top_segment_qty', 0)
    top_seg_pct = metrics.get('top_segment_pct', 0.0)
    low_seg = metrics.get('low_segment_name', 'bilinmiyor')
    low_seg_pct = metrics.get('low_segment_pct', 0.0)

    out.append(
        f"Trend verileri, {metrics.get('trend_comment', 'belirsiz')} bir eğilim göstermektedir. "
        f"Son 3 ayın ortalama satış adedi {_fmt_thousands(metrics.get('ma3_qty', 0))}, gelir ise {_fmt_thousands(metrics.get('ma3_rev', 0))} TL'dir. "
        f"Aylık değişim oranı {abs(metrics.get('mom_pct_abs', 0.0)):.1f}% seviyesindedir."
    )

    out.append(
        f"{last_month} ayında {_fmt_thousands(metrics.get('last_qty', 0))} adet satış gerçekleşmiştir. "
        f"Bu sayı, önceki aya göre {metrics.get('qty_diff_comment', 'önemli bir fark göstermektedir')}. "
        "Bu değişim mevsimsellik, kampanya etkisi ya da stok durumuna bağlı olabilir."
    )

    out.append(
        f"En çok satan ürün: {metrics.get('top_prod_name', 'bilinmiyor')} ({_fmt_thousands(metrics.get('top_prod_qty', 0))} adet). "
        f"En az satan ürün: {low_prod}. "
        "Bu ürünlerin kanal bazlı görünürlüğü ve fiyat pozisyonu incelenmelidir."
    )

    out.append(
        f"Segment dağılımına göre en güçlü kategori: {top_seg} "
        f"({_fmt_thousands(top_seg_q)} adet, %{top_seg_pct:.1f}). "
        f"En zayıf segment: {low_seg} (%{low_seg_pct:.1f}). "
        "Zayıf segmentler için hedefleme ve görünürlük optimizasyonu yapılmalıdır."
    )

    out.append(
        f"{low_prod} ürününün satışları düşüktür. "
        "Bu ürün için arama görünürlüğü artırılmalı, ana kategori sayfasında vitrinlenmeli ve benzer ürünlerle bundle fırsatları sunulmalıdır. "
        "Fiyat kademesi testi ile marj-kayıp olmadan dönüşüm artışı sağlanabilir."
    )

    expected_rev = metrics.get('expected_revenue')
    actual_rev = metrics.get('last_rev', 0)
    rev_gap = expected_rev - actual_rev if expected_rev else 0
    out.append(
        f"{last_month} ayında toplam {_fmt_thousands(actual_rev)} TL gelir elde edilmiştir. "
        f"Aynı ay için hedeflenen gelir {_fmt_thousands(expected_rev)} TL olduğundan sapma {_fmt_thousands(rev_gap)} TL'dir. "
        "Bu fark, ürün karışımı, ortalama sepet büyüklüğü ve kampanya etkinliği üzerinden analiz edilmelidir."
    )

    forecast_qty = metrics.get('ma3_qty', 0)
    forecast_rev = metrics.get('ma3_rev', 0)
    out.append(
        f"Eğer mevcut trend sürerse gelecek ay {_fmt_thousands(forecast_qty)} adet ve {_fmt_thousands(forecast_rev)} TL ciro beklenmektedir. "
        f"Aynı segmentte geçmiş 2 ayda büyüme oranı {metrics.get('segment_growth_comment', 'durgun')} olarak kaydedilmiştir. "
        f"Bu doğrultuda, {top_seg} segmentine yatırım artırılmalı; düşük performanslı ürünler kampanya ile desteklenmelidir."
    )

    return out[:need]

def _enforce_max_product_mentions(lines, allowed_names, max_mentions=2):
    mentions = {name: 0 for name in allowed_names}
    updated = []

    for l in lines:
        line = l
        for name in allowed_names:
            if name and name in line:
                if mentions[name] < max_mentions:
                    mentions[name] += 1
                else:
                    line = line.replace(name, "ilgili ürün")
        updated.append(line)
    return updated

# ----------------------------------------------------------------------

def sales_form_view(request):
    form = SalesDataForm()
    result = None
    warnings = []
    suggestion = None

    if request.method == "POST":
        form = SalesDataForm(request.POST, request.FILES)
        if form.is_valid():
            start_month = form.cleaned_data['start_month']
            end_month = form.cleaned_data['end_month']
            sales_file = request.FILES['sales_excel']
            target_file = request.FILES['target_excel']

            # --- Dosyaları oku ve kolonları normalize et
            try:
                df_sales = pd.read_excel(sales_file)
                df_sales.columns = [normalize_column(c) for c in df_sales.columns]
                # normalize'dan sonra aynı isme düşen sütunları benzersizleştir (\"segment\" çakışmasını da önler)
                df_sales.columns = _dedupe_columns(list(df_sales.columns))
            except Exception as e:
                warnings.append(f"Satış Excel dosyası okunamadı: {e}")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            try:
                df_target = pd.read_excel(target_file)
                df_target.columns = [normalize_column(c) for c in df_target.columns]
                df_target.columns = _dedupe_columns(list(df_target.columns))
            except Exception as e:
                warnings.append(f"Hedef Excel dosyası okunamadı: {e}")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # --- Alias eşleştirme
            sales_cols = map_column(df_sales.columns, SALES_COLUMN_ALIASES)
            target_cols = map_column(df_target.columns, TARGET_COLUMN_ALIASES)

            # Zorunlu alan kontrolleri
            for key in ['urun_adi', 'tarih', 'gelir']:
                if key not in sales_cols:
                    warnings.append(f"Satış dosyasında '{key}' için eşleşen sütun bulunamadı.")
            for key in ['ay', 'hedef_adet', 'hedef_gelir']:
                if key not in target_cols or 'yl' not in df_target.columns:
                    warnings.append(f"Hedef dosyasında '{key}' veya 'yl' sütunu eksik.")

            if warnings:
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # --- Tip dönüşümleri ve türetilmiş alanlar
            df_sales[sales_cols['tarih']] = pd.to_datetime(df_sales[sales_cols['tarih']], errors='coerce')
            df_sales = df_sales.dropna(subset=[sales_cols['tarih']]).copy()
            if df_sales.empty:
                warnings.append("Satış verisinde geçerli tarihli satır bulunamadı.")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # Segment sütunu güvenli yönetim:
            # - Kullanıcı dosyasında zaten varsa: asla yeniden ekleme (insert) yapma.
            # - Yoksa ve otomatik üretilecekse: doğrudan atama ile oluştur (insert kullanma).
            # Örnek otomatik üretim (kapalı):
            # if 'segment' not in df_sales.columns:
            #     df_sales['segment'] = None  # veya ürün adına göre haritalama
            # NOT: Aşağıda sadece varlık kontrolü yapıyoruz; ekleme yapmıyoruz.
            col_segment_name = sales_cols.get('segment') if 'segment' in sales_cols else ('segment' if 'segment' in df_sales.columns else None)

            df_sales['adet'] = 1
            df_sales['gelir'] = pd.to_numeric(df_sales[sales_cols['gelir']], errors='coerce').fillna(0).astype(float)

            # Filtre (başlangıç/bitiş dahil son ayın ay sonuna kadar)
            mask = (
                (df_sales[sales_cols['tarih']] >= pd.to_datetime(start_month)) &
                (df_sales[sales_cols['tarih']] <= pd.to_datetime(end_month) + pd.offsets.MonthEnd(1))
            )
            df_sales_filtered = df_sales.loc[mask].copy()
            if df_sales_filtered.empty:
                warnings.append("Seçilen tarih aralığında satış verisi yok.")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            # Segment (opsiyonel)
            has_segment = (col_segment_name in df_sales_filtered.columns) if col_segment_name else False

            df_sales_filtered['year_month'] = df_sales_filtered[sales_cols['tarih']].dt.to_period('M')

            # --- Aylık satış özetleri
            monthly_sales = (
                df_sales_filtered
                .groupby('year_month')
                .agg(adet=('adet', 'sum'), gelir=('gelir', 'sum'))
                .reset_index()
                .sort_values('year_month')
            )

            # --- Hedef dosyasını period alanına çevir
            if 'yl' not in df_target.columns:
                warnings.append("Hedef dosyasında 'yl' (yıl) sütunu bulunamadı (örn: 'yıl' normalize edilince 'yl' olur).")
                return render(request, "sales/sales_form.html", {"form": form, "warnings": warnings})

            df_target['period'] = df_target.apply(
                lambda r: dateparser.parse(f"{r[target_cols['ay']]} {r['yl']}") if pd.notna(r.get(target_cols['ay'])) and pd.notna(r.get('yl')) else None,
                axis=1
            )
            df_target['period'] = pd.to_datetime(df_target['period'], errors='coerce').dt.to_period('M')
            df_target = df_target.dropna(subset=['period']).copy()
            target_dict = df_target.set_index('period').to_dict('index')

            # --- Hedef-gerçekleşen listesi
            comparison = []
            for _, row in monthly_sales.iterrows():
                ym = row['year_month']
                hedef = target_dict.get(ym, {})
                tq = hedef.get(target_cols['hedef_adet'])
                tr = hedef.get(target_cols['hedef_gelir'])
                sq = int(row['adet'])
                sr = float(row['gelir'])
                pct = (sq / tq * 100) if tq else 0
                comparison.append({
                    "period": str(ym),
                    "sales_quantity": sq,
                    "sales_revenue": sr,
                    "target_quantity": tq,
                    "target_revenue": tr,
                    "completion_rate": pct
                })
            result = comparison

            # --- Veri kalitesi: Aynı ürün-aynı ay fiyat sabitliği
            tmp = df_sales_filtered.copy()
            tmp['yil'] = tmp[sales_cols['tarih']].dt.year
            tmp['ay']  = tmp[sales_cols['tarih']].dt.month
            price_var = (
                tmp.groupby([sales_cols['urun_adi'], 'yil', 'ay'])['gelir']
                .nunique().reset_index(name='fiyat_sayisi')
            )
            inconsistent = price_var[price_var['fiyat_sayisi'] > 1]
            if not inconsistent.empty:
                warnings.append(
                    f"Dikkat: Aynı ürün-aynı ay içinde birden fazla fiyat tespit edildi ({len(inconsistent)} ürün-ay). "
                    "Satış raporunda ürün bazında ay içi fiyat sabit olmalı."
                )

            # --- Ürün bazlı özetler
            try:
                prod_series = (
                    df_sales_filtered
                    .groupby(sales_cols['urun_adi'])['adet']
                    .sum()
                    .sort_values(ascending=False)
                )
                top_prod, top_qty = prod_series.index[0], int(prod_series.iloc[0])
                low_prod, low_qty = prod_series.index[-1], int(prod_series.iloc[-1])
            except Exception:
                top_prod = low_prod = None
                top_qty = low_qty = 0

            # --- Segment özeti (opsiyonel ve dinamik)
            segment_sent = None
            if has_segment:
                seg_df = (
                    df_sales_filtered
                    .groupby(col_segment_name)['adet'].sum()
                    .sort_values(ascending=False)
                )
                if not seg_df.empty:
                    total_q = int(df_sales_filtered['adet'].sum())
                    # en çok & en az satan segment
                    top_seg = seg_df.index[0]
                    top_seg_q = int(seg_df.iloc[0])
                    top_share = round((top_seg_q / total_q) * 100, 1) if total_q else 0.0

                    low_seg = seg_df.index[-1]
                    low_seg_q = int(seg_df.iloc[-1])
                    low_share = round((low_seg_q / total_q) * 100, 1) if total_q else 0.0

                    segment_sent = (
                        f"Segmentlerde en yüksek katkı: {top_seg} ({_fmt_thousands(top_seg_q)} adet, %{top_share}). "
                        f"En düşük katkı: {low_seg} ({_fmt_thousands(low_seg_q)} adet, %{low_share}). "
                        "Düşük katkılı segment(ler) için teklif derinliği, kanal hedefleme ve vitrin önceliği artırılmalı; "
                        "yüksek katkılı segment(ler)de ise tempo korunurken marj korunumu gözetilmelidir."
                    )

            # --- Trend ve tahmin
            ms_full = monthly_sales.set_index('year_month').sort_index()
            last_qty = int(ms_full['adet'].iloc[-1]) if not ms_full.empty else 0
            last_rev = float(ms_full['gelir'].iloc[-1]) if not ms_full.empty else 0.0
            if len(ms_full) >= 2:
                prev_qty = int(ms_full['adet'].iloc[-2])
                prev_rev = float(ms_full['gelir'].iloc[-2])
                mom_qty = last_qty - prev_qty
                mom_pct = (mom_qty / prev_qty * 100) if prev_qty else 0.0
            else:
                prev_qty = prev_rev = None
                mom_qty = None
                mom_pct = None
            ma3_qty = int(round(ms_full['adet'].rolling(3).mean().iloc[-1])) if len(ms_full) >= 3 else last_qty
            ma3_rev = float(round(ms_full['gelir'].rolling(3).mean().iloc[-1])) if len(ms_full) >= 3 else last_rev

            # --- Seçili son ay tamamlanmış mı?
            selected_last_period = pd.Period(result[-1]['period']) if result else None
            selected_last_end = selected_last_period.end_time.date() if selected_last_period else datetime.date.today()
            today = datetime.date.today()
            is_completed_last = selected_last_end < today

            # --- Aktif ay ise kalan metrikler
            if result:
                this_period = result[-1]
                if is_completed_last:
                    kalan_adet = 0
                    kalan_gun = 0
                    gereken_gunluk = 0.0
                else:
                    p_end = selected_last_end
                    kalan_adet = max((this_period['target_quantity'] or 0) - (this_period['sales_quantity'] or 0), 0)
                    kalan_gun = max((p_end - today).days, 1)
                    gereken_gunluk = round(kalan_adet / kalan_gun, 2) if kalan_adet else 0.0
            else:
                kalan_adet = kalan_gun = 0
                gereken_gunluk = 0.0

            # --- Performans özeti (fallback için metrikler)
            perf_df = pd.DataFrame(result)
            perf_df['rate'] = perf_df['completion_rate'].fillna(0.0)
            worst = best = None
            under_months = int((perf_df['rate'] < 100).sum()) if not perf_df.empty else 0
            if not perf_df.empty:
                widx = perf_df['rate'].idxmin()
                bidx = perf_df['rate'].idxmax()
                worst = {
                    'period': perf_df.loc[widx, 'period'],
                    'rate': float(perf_df.loc[widx, 'rate']),
                    'gap':  int((perf_df.loc[widx, 'target_quantity'] or 0) - (perf_df.loc[widx, 'sales_quantity'] or 0))
                }
                best = {
                    'period': perf_df.loc[bidx, 'period'],
                    'rate': float(perf_df.loc[bidx, 'rate']),
                }

            # --- AI PROMPT (ROL + KURALLAR) — VERİ-BAĞLAYICI & DİNAMİK SEGMENT ---
            prompt = (
                "ROL: Bir perakende/e-ticaret şirketinde Kıdemli Satış Müdürü ve Veri Analisti olarak davran.\n"
                "AMAÇ: Satışları iyileştirmek; eksikleri tespit edip uygulanabilir çözümler önermek; trend analizi yapmak; ileriye dönük tahmin üretmek.\n\n"
                "YANIT TALİMATI (ZORUNLU):\n"
                "- Yanıtı mutlaka 1), 2), 3) ... şeklinde NUMARALI maddelerle yaz.\n"
                "- Tam olarak 10 madde yaz. Her madde EN AZ 3 TAM cümle içersin; cümleler eksiksiz, analitik ve VERİYE DAYALI olsun.\n"
                "- Rakamları binlik ayraçla yaz (ör. 10200200 -> 10.200.200). TL ve adet için bu formatı kullan.\n"
                "- Madde sırası ve kapsamı sabittir: "
                "(1) Son 6 ay trend analizi; "
                "(2) Hedef–Gerçekleşen ve SEÇİLİ SON AY ile ÖNCEKİ AY adet karşılaştırması; "
                "(3) En çok ve en az satan ÜRÜNLER (tek madde); "
                "(4) Strateji #1 (fiyat, kampanya, stok önceliği); "
                "(5) Strateji #2 (kanal/ROI, vitrin/arama, bundle); "
                "(6) Segment bazlı analiz (rapordaki segmentlere dayanarak: en çok ve en az satan segmentleri sayı ve % pay ile ver); "
                "(7) Veri destekli ürün/segment düşüş tespiti + somut aksiyon; "
                "(8) Satışı yüksek ama hâlâ büyüme potansiyeli olan ürün/segment için kampanya ve kanal planı öner.; "
                "(9) Satışı düşük kalan ürün/segment için fiyatlama, görünürlük veya bundle stratejisi öner; "
                "(10) Segment bazlı satışları değerlendir, önümüzdeki ay için tahmin yap ve aksiyon planı öner.\n"
                "- Aynı ürünü birden fazla maddede tekrarlama."
                "- Tüm maddeler veriye dayalı olmalı (ör: 'X ürününün satışları %15 düştü, bu nedenle...' gibi)."
                "- Yalnızca BİR maddede belirli bir ürün adı kullanabilirsin; diğer maddelerde segment/kanal/strateji düzeyinde yaz.\n"
                "- Etiketli girişler KULLANMA (örn. 'Çözüm:', 'Öneri:', 'Hedef:'); doğal cümleler kur.\n"
                "- Seçili son ay TAMAMLANMIŞ ise kalan gün/günlük tempo YAZMA; aktif ay ise kalan adet, kalan gün ve gerekli günlük tempoyu belirt.\n"
                "- 'Strateji geliştirilmelidir' gibi genel ifadelerle yetinme; her strateji cümlesini en az 2 alt cümle ile açıkla (örneğin: hangi kanalda, nasıl bir teklif, hangi ürün segmenti, hangi zaman aralığı vs.).\n"
                "- 'Strateji geliştirilmelidir', 'önlemler alınmalıdır' gibi genel ifadelerle yetinme.\n"
                "- Her aksiyon cümlesi en az iki alt fikir içermeli: örneğin hangi ürün/segment, hangi kanal, hangi zamanlama, hangi teknik.\n"
                "- Mutlaka önerilen stratejilerin nasıl uygulanabileceğini açıkla.\n"
                "- Aksiyonlar ölçülebilir ve uygulanabilir olmalı; örneğin 'arama görünürlüğü artırılmalı' yerine 'X kategorisi altında %20 daha fazla gösterim alınması için SEO başlıkları güncellenmeli' gibi.\n"
                "- stratejiler geliştirmek önemli olacaktır diyorsan hangi stratejinin nasıl uygulanabileceğini de detaylı en az 2 cümleyle açıkla.\n"
                "- Çıktılar, profesyonel bir satış analistinin üst yönetime sunduğu bir rapor formatında olmalı.\n"
                "- Cümleler kurumsal ve sade bir dille yazılsın.\n"
                "- İçinde strateji ya da Strateji geçen her cümlede MUTLAKA STRATEJİYİ DETAYLANDIR EN AZ 2 CÜMLEYLE HANGİ STRATEJİ NASIL UYGULANIR VE NE AÇIDAN FAYDA SAĞLAR AÇIKLA! .\n"

                "- Maddeler 6–10 VERİ REFERANSLI olsun: ürün/segment/ay bazında % değişim, adet farkı veya TL farkı ver ve öneriyi bu sayıya bağla.\n\n"
            )

            # Bağlam bilgisi (AI'ye veri gönder) — sayıları binlik formatla
            if top_prod:
                prompt += f"- En çok satılan ürün: {top_prod} ({_fmt_thousands(top_qty)} adet)\n"
            if low_prod:
                prompt += f"- En az satılan ürün: {low_prod} ({_fmt_thousands(low_qty)} adet)\n"
            if mom_pct is not None:
                prompt += f"- Aylık değişim (MoM, adet): {mom_pct:+.1f}%\n"
            prompt += f"- 3A hareketli ortalama (adet/ciro): {_fmt_thousands(ma3_qty)} / {_fmt_thousands(int(ma3_rev))}\n"
            prompt += f"- Seçili son ay tamamlanmış mı?: {'Evet' if is_completed_last else 'Hayır'}\n"
            if not is_completed_last:
                prompt += f"- Aktif ay kalan adet/gün/günlük tempo: {_fmt_thousands(kalan_adet)} / {kalan_gun} / {gereken_gunluk}\n"

            # Segment özeti (varsa; hem top hem low segment veriyle)
            if segment_sent:
                prompt += f"- Segment özeti: {segment_sent}\n"

            # Aylık özet — sayıları binlik formatla
            prompt += "\nAylık özet (Hedef/Fiili):\n"
            for r in result:
                tq = r['target_quantity'] or 0
                tr = r['target_revenue'] or 0
                prompt += (
                    f"  {r['period']}: Adet={_fmt_thousands(r['sales_quantity'])}/{_fmt_thousands(tq)}, "
                    f"Ciro={_fmt_thousands(int(r['sales_revenue']))}/{_fmt_thousands(int(tr))} TL, "
                    f"Tamamlanma={r['completion_rate']:.1f}%\n"
                )
            prompt += (
                "\nYanıtı 1), 2), 3) ... biçiminde numaralı 10 madde olarak ver; her madde en az üç cümle içersin ve "
                "trend, hedef–gerçekleşen ve önceki ay kıyası, segment/portföy içgörüleri, veri destekli strateji ve tahminleri NET biçimde içersin. "
                "Maddeler 6–10’da ürün veya segment bazlı düşüş/yükseliş için yüzde veya adet farkı ver ve öneriyi bu sayıya bağla."
            )

            # --- AI çağrısı
            try:
                raw = get_sales_suggestion(prompt) or ""
            except Exception as e:
                raw = f"AI yanıtı alınamadı: {e}"

            # --- ÇIKTI TEMİZLİĞİ: etiket temizle, cümle sonları, min 3 cümle, tek ürün adı sınırı, 10 madde, numaralandır, rakam formatla
            lines = [ln for ln in (raw.splitlines()) if ln.strip()]
            lines = [_strip_labels(l) for l in lines]
            lines = [_ensure_sentence(l) for l in lines if l]
            lines = _min_three_sentences(lines)

            # Fallback metrikleri topla

            metrics = {
                'mom_pct_abs': abs(mom_pct or 0.0),
                'ma3_qty': ma3_qty,
                'ma3_rev': ma3_rev,
                'last_qty': last_qty,
                'last_rev': last_rev,  # EKLENDİ
                'prev_qty': prev_qty,
                'top_prod_name': top_prod,
                'top_prod_qty': top_qty,
                'low_prod_name': low_prod,
                'low_prod_qty': low_qty,
                'top_segment_name': top_seg if has_segment else "bilinmiyor",  # EKLENDİ
                'top_segment_qty': top_seg_q if has_segment else 0,  # EKLENDİ
                'top_segment_pct': top_share if has_segment else 0.0,  # EKLENDİ
                'low_segment_name': low_seg if has_segment else "bilinmiyor",  # EKLENDİ
                'low_segment_pct': low_share if has_segment else 0.0,  # EKLENDİ
                'expected_revenue': this_period.get('target_revenue') if result else 0,  # EKLENDİ
                'last_month': result[-1]['period'] if result else "ilgili"  # EKLENDİ
            }

            if len(lines) < 10:
                need = 10 - len(lines)
                lines.extend(_build_fallback_items(metrics, need))

            # Tek ürün adı en fazla 1 maddede
            lines = _enforce_max_product_mentions(lines, [top_prod, low_prod], max_mentions=4)

            # Rakamları (adet/TL bağlamında) binlik ayraçla biçimlendir
            lines = [_fmt_in_text_contextual(l) for l in lines]

            # 10’a kırp ve 1) 2) … numarala
            lines = _prioritize_and_cap(lines, cap=10)
            lines = _renumber_1paren(lines)

            suggestion = "\n".join(lines)

            # --- Kayıt
            try:
                for r in result:
                    try:
                        period_obj = pd.Period(r['period'])
                        period_end = period_obj.end_time.date()
                    except Exception:
                        period_end = datetime.date.today()

                    hedef_adet = r['target_quantity'] or 0
                    hedef_gelir = r['target_revenue'] or 0
                    toplam_adet = r['sales_quantity'] or 0
                    toplam_gelir = r['sales_revenue'] or 0.0
                    tamamlanma = r['completion_rate'] or 0.0

                    gun_sayisi = max(datetime.date.today().day, 1)
                    gunluk_ortalama = toplam_adet / gun_sayisi if gun_sayisi else 0.0
                    if period_end < datetime.date.today():
                        kalan_gunluk_gerekli = 0.0
                    else:
                        kalan_gunluk_gerekli = max((hedef_adet - toplam_adet) / max((period_end - datetime.date.today()).days, 1), 0.0)

                    SalesRecord.objects.update_or_create(
                        user=request.user,
                        period=str(r['period']),
                        defaults={
                            'hedef_adet': int(hedef_adet),
                            'hedef_gelir': int(hedef_gelir),
                            'toplam_adet': int(toplam_adet),
                            'toplam_gelir': float(toplam_gelir),
                            'gunluk_ortalama': float(gunluk_ortalama),
                            'kalan_gunluk_gerekli': float(kalan_gunluk_gerekli),
                            'tamamlama_yuzdesi': float(tamamlanma),
                            'yorum': suggestion
                        }
                    )
            except Exception as e:
                warnings.append(f"Kayıt sırasında hata: {e}")

            # --- Render
            return render(request, "sales/sales_form.html", {
                "form": form,
                "result": result,
                "warnings": warnings,
                "suggestion": suggestion
            })

    # GET
    return render(request, "sales/sales_form.html", {
        "form": form,
        "result": result,
        "warnings": warnings,
        "suggestion": suggestion
    })