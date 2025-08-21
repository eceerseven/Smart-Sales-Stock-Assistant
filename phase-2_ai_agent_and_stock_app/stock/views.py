# stock/views.py
import re
import json
import pandas as pd
from datetime import datetime
from django.shortcuts import render, redirect
from .forms import StokForm
from utils.ai import get_ai_response  # AI çağrısı

# --- Yaş aralığı sırası (grafik eksenini sabitlemek için) ---
AGE_ORDER = ["1-3 Ay", "3-6 Ay", "6-9 Ay", "9-12 Ay", "12-24 Ay", "24+ Ay"]

# === Basit yönlendirme: import hatalarını önlemek için dosyanın en üstünde tanımlı ===
def stock_home(request):
    # URL adı 'stok-analizi' ise anasayfa buraya dönsün
    return redirect('stok-analizi')


# Yardımcı: kolon adlarını güvenle seç
def _safe_col(df, candidates, required=False):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise KeyError(f"Gerekli sütun(lar) eksik: {candidates}")
    return None


def stok_analizi(request):
    context = {}

    if request.method == 'POST':
        form = StokForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['stok_dosyasi']
            df = pd.read_excel(excel_file)

            # --- Kolon adlarını normalize et ---
            df.columns = (
                df.columns
                .str.strip().str.lower()
                .str.replace(" ", "_", regex=False)
                .str.replace("ç", "c", regex=False)
                .str.replace("ğ", "g", regex=False)
                .str.replace("ı", "i", regex=False)
                .str.replace("ö", "o", regex=False)
                .str.replace("ş", "s", regex=False)
                .str.replace("ü", "u", regex=False)
            )

            # --- Kolon alias'ları ---
            col_date    = _safe_col(df, ["stok_giris_tarihi","giris_tarihi","stok_tarihi","stock_entry_date"], required=True)
            col_brand   = _safe_col(df, ["marka","brand"], required=True)
            col_segment = _safe_col(df, ["segment","kategori","category"], required=False)
            col_product = _safe_col(df, ["urun","model","sku","product","urun_adi","product_name"], required=False)

            # --- Tarih ve stok yaşı ---
            df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
            df = df.dropna(subset=[col_date])
            if df.empty:
                context["form"] = form
                context["stok_analiz_ai"] = "Veri bulunamadı (geçerli tarih alanı olan satır yok)."
                return render(request, "stock/stok_analysis.html", context)

            bugun = pd.Timestamp(datetime.now().date())
            df["stok_yasi"] = (bugun - df[col_date]).dt.days

            def yas_araligi(g):
                if g <= 90:  return "1-3 Ay"
                if g <= 180: return "3-6 Ay"
                if g <= 270: return "6-9 Ay"
                if g <= 365: return "9-12 Ay"
                if g <= 730: return "12-24 Ay"
                return "24+ Ay"
            df["yas_araligi"] = df["stok_yasi"].apply(yas_araligi)

            # --- Grafik verileri (segment opsiyonel) ---
            if col_segment:
                seg_pivot = df.groupby(["yas_araligi", col_segment]).size().unstack(fill_value=0)
                # X eksenini sabit sıraya getir
                seg_pivot = seg_pivot.reindex(AGE_ORDER, fill_value=0)
                segment_labels = list(seg_pivot.index)
                segment_datasets = [{"label": str(c), "data": list(map(int, seg_pivot[c]))} for c in seg_pivot.columns]
            else:
                seg_pivot = pd.DataFrame()
                segment_labels, segment_datasets = [], []

            mark_pivot = df.groupby(["yas_araligi", col_brand]).size().unstack(fill_value=0)
            # X eksenini sabit sıraya getir
            mark_pivot = mark_pivot.reindex(AGE_ORDER, fill_value=0)
            marka_labels = list(mark_pivot.index)
            marka_datasets = [{"label": str(c), "data": list(map(int, mark_pivot[c]))} for c in mark_pivot.columns]

            # --- Zaman bantları ve odak ---
            total_12_24 = int(df[(df["stok_yasi"] > 365) & (df["stok_yasi"] <= 730)].shape[0])
            total_24p   = int(df[df["stok_yasi"] > 730].shape[0])
            focus_band  = "12–24 Ay" if total_12_24 > total_24p else "24+ Ay"

            band_counts = df["yas_araligi"].value_counts().sort_values(ascending=False)
            band_top_name = str(band_counts.index[0]) if not band_counts.empty else None
            band_top_count = int(band_counts.iloc[0]) if not band_counts.empty else 0

            # --- En uzun bekleyen tekil ürün ---
            oldest_row = df.sort_values("stok_yasi", ascending=False).iloc[0]
            oldest_desc = {
                "marka":   str(oldest_row[col_brand]),
                "urun":    str(oldest_row[col_product]) if col_product else None,
                "segment": str(oldest_row[col_segment]) if col_segment else None,
                "gun":     int(oldest_row["stok_yasi"]),
            }

            # --- Kümeler (brand/product/segment) ---
            def group_keys(cols): return [c for c in cols if c]
            keys_brand = group_keys([col_brand])
            keys_prod  = group_keys([col_brand, col_product]) if col_product else group_keys([col_brand])
            keys_seg   = group_keys([col_brand, col_segment]) if col_segment else group_keys([col_brand])

            band_12_24 = df[(df["stok_yasi"] > 365) & (df["stok_yasi"] <= 730)]
            band_24p   = df[df["stok_yasi"] > 730]

            def topn(gdf, keys, n=10):
                if not keys: return pd.DataFrame(columns=["adet"])
                t = gdf.groupby(keys).size().reset_index(name="adet")
                t = t[t["adet"] > 0].sort_values("adet", ascending=False).head(n)
                return t

            top_brand_12_24 = topn(band_12_24, keys_brand)
            top_brand_24    = topn(band_24p,   keys_brand)
            top_prod_12_24  = topn(band_12_24, keys_prod)
            top_prod_24     = topn(band_24p,   keys_prod)
            top_seg_12_24   = topn(band_12_24, keys_seg)
            top_seg_24      = topn(band_24p,   keys_seg)

            # --- 24+’ta en çok bekleyen ürüne sahip marka(lar) (tie destekli) ---
            brand_leaders_24, brand_leaders_24_count, brand_second_24_count = [], 0, 0
            if not top_brand_24.empty:
                top_count = int(top_brand_24["adet"].max())
                brand_leaders_24 = (
                    top_brand_24.loc[top_brand_24["adet"] == top_count, col_brand]
                    .astype(str).tolist()
                )
                brand_leaders_24_count = top_count
                lesser = top_brand_24.loc[top_brand_24["adet"] < top_count, "adet"]
                brand_second_24_count = int(lesser.max()) if not lesser.empty else 0

            if brand_leaders_24:
                leaders_str = ", ".join(brand_leaders_24)
                multi = len(brand_leaders_24) > 1
                brand_most_24_txt = (
                    f"{leaders_str} — {brand_leaders_24_count} adet (24+ Ay, en çok bekleyen ürüne sahip {'markalar' if multi else 'marka'}"
                    f"{f'; ikinci sıradaki marka {brand_second_24_count} adet' if brand_second_24_count else ''})"
                )
            else:
                brand_most_24_txt = "Yok"

            # --- 24+’ta ortalama yaşı en yüksek kategori/segment ---
            longest_cat_txt = "Segment sütunu yok."
            if col_segment and not band_24p.empty:
                seg_age = band_24p.groupby(col_segment)["stok_yasi"].mean().sort_values(ascending=False)
                if not seg_age.empty:
                    longest_cat_txt = f"{str(seg_age.index[0])} (ortalama {int(round(seg_age.iloc[0]))} gün)"

            # --- AI'ya giden metin tabloları ---
            def df_to_txt(d): return d.to_string(index=False) if d is not None and not d.empty else "Yok"
            mark_txt    = mark_pivot.fillna(0).astype(int).to_string()
            brand12_txt = df_to_txt(top_brand_12_24)
            brand24_txt = df_to_txt(top_brand_24)
            prod12_txt  = df_to_txt(top_prod_12_24)
            prod24_txt  = df_to_txt(top_prod_24)
            seg12_txt   = df_to_txt(top_seg_12_24)
            seg24_txt   = df_to_txt(top_seg_24)

            oldest_txt = f"Marka: {oldest_desc['marka']}"
            if oldest_desc.get("urun"):    oldest_txt += f", Urun: {oldest_desc['urun']}"
            if oldest_desc.get("segment"): oldest_txt += f", Segment: {oldest_desc['segment']}"
            oldest_txt += f", Bekleme: {oldest_desc['gun']} gün"

            # --- ROL + Güçlü PROMPT ---
            prompt = f"""
ROL: Deneyimli Stok Yönetim Uzmanı (retail & e-ticaret).
AMAÇ: 12–24 ve 24+ yaşlı stokları en hızlı şekilde ERİTMEK; yaşlı stokta taşıma maliyeti ve değer kaybını azaltmak.

GÖREV: Aşağıdaki tablolara dayanarak 6–7 adet veri-temelli madde yaz (tercihen 7). Her madde tek satır olsun; satır içinde birden fazla cümle kurabilirsin. Satır başına numara/sembol koyma. Talimat metnini veya başlıkları tekrar etme; doğal cümle kur.

KATI KURALLAR:
- “Yeni ürün eklemek/çeşidi artırmak/stok artırmak” gibi ifadeler YASAK. Amaç mevcut yaşlı stokları likide etmek.
- 0 adet olan hiçbir şeye değinme.
- Ürün adı en fazla 2 maddede geçebilir (tercihen: en uzun bekleyen tekil ürün ve—varsa—en uzun bekleyen model). Diğer maddelerde marka/segment odaklı kal.
- Her maddede Hedef (örn. 2–4 haftada %20–40, medyan yaşı 365 altına indirme, 24+ stoğunu sıfırlama) ve Gerekçe (en az 2 cümle) yer alsın; sayısal dayanak kullan (band toplamı {total_12_24}/{total_24p}, marka içi pay, ikinci markaya fark, yaş ort/medyan, devir hızı, kanal/promosyon elastikiyeti, tahmini kâr etkisi).
- Ürün listesi (A, B, C) verme; tekil ürün adı kullanılacaksa tek bir üründen söz et.

ZORUNLU KAPSAM:
- En uzun bekleyen tekil ürün (ürün adı + marka + gün) → net aksiyon + Hedef & Gerekçe.
- 24+ Ay bandında **en çok bekleyen ürüne sahip marka(lar)** (adet ve ikinci markaya fark veya beraberlik) → net aksiyon + Hedef & Gerekçe (birikme = olumsuz durum).
- 24+ Ay bandında ortalama yaşı en yüksek kategori/segment (varsa) → ortalama gün/adet ile → Hedef & Gerekçe.
- Zaman bandı birikmesi: {band_top_name} bandında {band_top_count} adet varsa, birikme gerekçesi ve aksiyon → Hedef & Gerekçe.
- En az 2 ek analitik madde: marka veya segment odaklı, kıyas ve Hedef & Gerekçe ile.

GERÇEKLER (AYNIYLA KULLAN; ÇELİŞME YASAK):
- 24+ Ay bandında en çok bekleyen ürüne sahip marka(lar): {", ".join(brand_leaders_24) if brand_leaders_24 else "Yok"} ({brand_leaders_24_count} adet; ikinci: {brand_second_24_count})

TABLOLAR
[MARKA x YAŞ ARALIĞI (adet)]
{mark_txt}

[12–24 Ay | En çok adet (MARKA)]
{brand12_txt}

[24+ Ay | En çok adet (MARKA)]
{brand24_txt}

[12–24 Ay | En çok adet (MARKA×ÜRÜN)]
{prod12_txt}

[24+ Ay | En çok adet (MARKA×ÜRÜN)]
{prod24_txt}

[12–24 Ay | En çok adet (MARKA×SEGMENT)]
{seg12_txt}

[24+ Ay | En çok adet (MARKA×SEGMENT)]
{seg24_txt}

[En uzun bekleyen tekil ürün]
{oldest_txt}

[24+ Ay'da en çok bekleyen ürüne sahip marka(lar)]
{brand_most_24_txt}

[24+’ta ortalama yaşı en yüksek kategori/segment]
{longest_cat_txt}
"""

            # --- AI cevabı al ---
            raw = get_ai_response(prompt) or ""

            # --- Satır başı numara/bullet/tırnak temizliği ---
            lines = [
                re.sub(r'^\s*(?:[-*•]+|\d+[.)])\s*', '', l).strip().strip('"“”')
                for l in raw.splitlines()
                if l.strip()
            ]

            # --- Talimat/başlık kopyalama temizliği ---
            heading_pat = re.compile(
                r'^(En uzun bekleyen tekil ürün|24\+\s*bandında en çok .*?marka|24\+\s*ay bandında en çok .*?marka|24\+\s*bandında ortalama yaşı en yüksek .*?|Zaman bandı birikmesi)\s*:\s*',
                flags=re.IGNORECASE
            )
            lines = [heading_pat.sub('', l) for l in lines]

            # --- Ters yönlü ifadeleri likidasyon diline çevir ---
            banned_map = [
                (r"ürün çeşitliliğini art(?:tır|ır)(?:mak)?", "mevcut 12–24/24+ stokları likide etmek"),
                (r"yeni ürün(?:ler)? ekle(?:mek)?",           "yaşlı stokları hızla eritmek"),
                (r"assortman[ıi] (?:genişlet|art(?:tır|ır))", "SKU daraltma ve konsolidasyon"),
                (r"stok(?:u|ları|lar[ıi]) art(?:tır|ır)(?:mak)?", "yaşlı stok seviyesini düşürmek"),
            ]
            cleaned = []
            for l in lines:
                s = l
                for pat, repl in banned_map:
                    s = re.sub(pat, repl, s, flags=re.IGNORECASE)
                s = re.sub(r'\*{2,}', '', s).strip()
                cleaned.append(s)
            lines = [x for x in cleaned if x]

            # --- "lider/önde" kelimelerini doğru söyleme çevir (genel) ---
            def fix_leader_words(text: str) -> str:
                if re.search(r'\b(lider(lik)?|önde|baş(ı)?n[ıi] çekiyor)\b', text, flags=re.IGNORECASE):
                    if brand_leaders_24:
                        b_list = ", ".join(brand_leaders_24)
                        return re.sub(r'\b(lider(lik)?|önde|baş(ı)?n[ıi] çekiyor)\b',
                                      f"24+ Ay bandında en çok bekleyen ürüne sahip marka(lar) {b_list}",
                                      text, flags=re.IGNORECASE)
                    else:
                        return re.sub(r'\b(lider(lik)?|önde|baş(ı)?n[ıi] çekiyor)\b',
                                      "en çok bekleyen ürüne sahip marka", text, flags=re.IGNORECASE)
                return text
            lines = [fix_leader_words(l) for l in lines]

            # --- ÜRÜN ADI EN FAZLA 2 MADDE ---
            if col_product:
                product_names = sorted(
                    [str(x) for x in df[col_product].dropna().astype(str).unique()],
                    key=lambda s: -len(s)
                )
                def contains_product(text):
                    for name in product_names:
                        if name and name in text:
                            return True
                    return False

                seen_product_lines = 0
                new_lines = []
                for l in lines:
                    if contains_product(l):
                        if seen_product_lines < 2:
                            seen_product_lines += 1
                            new_lines.append(l)
                        else:
                            l_neutral = l
                            for name in product_names:
                                if name:
                                    l_neutral = l_neutral.replace(name, "ilgili ürün")
                            new_lines.append(l_neutral)
                    else:
                        new_lines.append(l)
                lines = new_lines

            # --- 24+ "en çok bekleyen ürüne sahip marka" beyanını doğrula ---
            if brand_leaders_24:
                brand_names_all = sorted(
                    [str(x) for x in df[col_brand].dropna().astype(str).unique()],
                    key=lambda s: -len(s)
                )
                leader_claim_pat = re.compile(
                    r'24\+\s*ay.*?en\s*çok.*?(bekleyen)?.*(ürün|adet).*sahip.*?marka', re.IGNORECASE
                )
                def fix_leader_line(line: str) -> str:
                    if not leader_claim_pat.search(line):
                        return line
                    if any(ldr in line for ldr in brand_leaders_24):
                        return line
                    fixed = line
                    for b in brand_names_all:
                        if b in brand_leaders_24:
                            continue
                        if re.search(rf'\b{re.escape(b)}\b', fixed):
                            fixed = re.sub(rf'\b{re.escape(b)}\b', brand_leaders_24[0], fixed, count=1)
                            break
                    return fixed
                lines = [fix_leader_line(l) for l in lines]

            # --- En az gereksinim: "Hedef" ve "Gerekçe" zorunlu ---
            lines = [l for l in lines if re.search(r'Hedef\s*:', l) and re.search(r'Gerekçe\s*:', l)]

            # --- Negatif çerçeve zorunlu ---
            def enforce_accumulation_risk(text: str) -> str:
                if re.search(r'en\s*çok.*sahip.*marka', text, flags=re.IGNORECASE):
                    if not re.search(r'birikme|risk|likidasyon|taşıma maliyeti|deger kayb', text, flags=re.IGNORECASE):
                        if 'Gerekçe:' in text:
                            return text.rstrip('.') + "; ayrıca bu birikme taşıma maliyeti ve değer kaybı riski doğurur, likidasyon önceliği verilmelidir."
                return text
            lines = [enforce_accumulation_risk(l) for l in lines]

            # --- Fallback satırları (min 6) ---
            def brand_total(brand):
                try:
                    return int(df[df[col_brand] == brand].shape[0])
                except Exception:
                    return 0
            def pct(x, y): return round((x / y) * 100, 1) if y else 0.0

            fallback = []

            if brand_leaders_24:
                b_list = ", ".join(brand_leaders_24)
                c1 = brand_leaders_24_count
                c2 = brand_second_24_count
                diff_txt = f"; ikinci sıradaki marka {c2} adet" if c2 else ""
                target_pct = min(50, max(25, c1 * 10))
                fallback.append(
                    f"24+ Ay bandında en çok bekleyen ürüne sahip marka(lar) {b_list} ({c1} adet{diff_txt}). Hedef: 3–4 haftada %{target_pct} 24+ stok azaltımı ve medyan yaşı 365 gün altına çekmek. Gerekçe: band toplamı {total_24p}; yaş ortalaması yüksek ve devir hızı düşük; bu birikme taşıma maliyetini artırır ve değer kaybı riski doğurur."
                )

            if band_top_name:
                target_pct = 30 if "24+" in band_top_name else 25
                fallback.append(
                    f"{band_top_name} bandında {band_top_count} adet ile birikme görülüyor. Hedef: 2–4 haftada %{target_pct} azaltım ve band medyan yaşını bir alt banda indirmek. Gerekçe: bu band diğerlerine kıyasla daha yüksek yük taşıyor; kademeli indirim, kampanya görünürlüğü ve kanal kaydırma ile talep tetiklenebilir, stok devir hızı iyileşir."
                )

            long_line = f"{oldest_desc['gun']} gün bekleyen tekil ürün öncelikli likidasyon adayı; marka {oldest_desc['marka']}{(' – ' + oldest_desc['urun']) if oldest_desc.get('urun') else ''}. Hedef: 2–3 haftada %25–35 eritmek ve 24+ bandından çıkarmak. Gerekçe: aşırı bekleme yaşı finansal taşıma maliyetini artırıyor; fırsat etiketi + agresif fiyat + takas/yenileme + online/outlet vitrin yaklaşımı dönüşümü artırır."
            fallback.append(long_line)

            if col_segment and longest_cat_txt != "Segment sütunu yok.":
                fallback.append(
                    f"24+ Ay bandında ortalama yaşı en yüksek kategori/segment {longest_cat_txt}. Hedef: 3 haftada %25–30 azaltım ve SKU karmasında sadeleşme. Gerekçe: segment yaş ortalaması yüksek; düşük dönen SKU’larda derin indirim ve bundle ile talep yaratılabilir; kanal bazlı vitrinleme görünürlüğü artırır."
                )

            if not top_brand_12_24.empty:
                b1, c1 = str(top_brand_12_24.iloc[0][col_brand]), int(top_brand_12_24.iloc[0]["adet"])
                c2 = int(top_brand_12_24.iloc[1]["adet"]) if len(top_brand_12_24) > 1 else 0
                diff = c1 - c2
                target_pct = min(40, max(20, c1 * 8))
                fallback.append(
                    f"12–24 Ay bandında {b1} öne çıkıyor ({c1} adet; ikinci markadan {diff} adet fazla). Hedef: 2–3 haftada %{target_pct} azaltım ve 12–24 stoklarının medyan yaşını 365 gün altına indirmek. Gerekçe: orta yaş bandının hacmi yüksek; kademeli indirim + bundle + güçlü vitrinleme ile hızlı likidasyon mümkün, stok devir hızı artar."
                )

            if total_24p > 0:
                fallback.append(
                    f"24+ bandı için kanal stratejisi: clearance/outlet odaklı satış. Hedef: 3 hafta içinde 24+ toplam stoğun %30’unu eritmek. Gerekçe: yaşlı stokta fiyat elastikiyeti yüksek; outlet görünürlüğü ve bedava kargo/ekstra taksit gibi teşvikler dönüşümü artırır, taşıma maliyetini düşürür."
                )

            if len(lines) < 6:
                need = 6 - len(lines)
                lines.extend(fallback[:max(0, need)])

            # ====== PROGRAMATİK EK MADDELER ======
            extras = []

            def band_top_product_line(band_label: str):
                if not col_product:
                    return None
                sub = df[df["yas_araligi"] == band_label]
                if sub.empty:
                    return None
                grp = sub.groupby([col_brand, col_product]).size().reset_index(name="adet")
                grp = grp.sort_values("adet", ascending=False)
                top = grp.iloc[0]
                brand = str(top[col_brand]); prod = str(top[col_product]); adet = int(top["adet"])
                band_total = int(sub.shape[0])
                share = round((adet / band_total) * 100, 1) if band_total else 0.0
                med_age = int(sub["stok_yasi"].median()) if not sub.empty else 0
                target_pct = min(40, max(15, adet * 8))
                return (
                    f"{band_label} bandında en çok bekleyen ürün {brand} – {prod} ({adet} adet; band içi pay %{share}, medyan yaş {med_age} gün). "
                    f"Hedef: 2–3 haftada %{target_pct} azaltım ve band medyan yaşını aşağı çekmek. "
                    f"Gerekçe: bu bantta toplam {band_total} adet içinde ilgili model en yüksek yükü oluşturuyor; "
                    f"fiyat kademesi + güçlü vitrin + uygun bundle ile dönüşüm hızlandırılabilir."
                )

            for band_label in ["1-3 Ay", "3-6 Ay", "6-9 Ay", "9-12 Ay"]:
                line_b = band_top_product_line(band_label)
                if line_b:
                    extras.append(line_b)

            if col_segment:
                seg_counts_all = df.groupby(col_segment).size().reset_index(name="adet").sort_values("adet", ascending=False)
                if not seg_counts_all.empty:
                    seg_name = str(seg_counts_all.iloc[0][col_segment])
                    seg_adet = int(seg_counts_all.iloc[0]["adet"])
                    total_all = int(df.shape[0])
                    seg_share = round((seg_adet / total_all) * 100, 1) if total_all else 0.0
                    med_age_seg = int(df[df[col_segment] == seg_name]["stok_yasi"].median())
                    target_pct = min(40, max(20, seg_adet * 5))
                    extras.append(
                        f"Tüm yaş aralıklarında en çok bekleyen segment {seg_name} ({seg_adet} adet; toplam pay %{seg_share}, medyan yaş {med_age_seg} gün). "
                        f"Hedef: 3–4 haftada %{target_pct} segment bazlı azaltım. "
                        f"Gerekçe: bu segment genel stok havuzunda birikim yaratıyor; indirim derinliği ve kampanya görünürlüğü artırıldığında devir hızı iyileşir, taşıma maliyeti düşer."
                    )

            if col_product:
                prod_counts_all = df.groupby([col_brand, col_product]).size().reset_index(name="adet").sort_values("adet", ascending=False)
                if not prod_counts_all.empty:
                    b = str(prod_counts_all.iloc[0][col_brand])
                    p = str(prod_counts_all.iloc[0][col_product])
                    a = int(prod_counts_all.iloc[0]["adet"])
                    total_all = int(df.shape[0])
                    share_all = round((a / total_all) * 100, 1) if total_all else 0.0
                    med_age_prod = int(df[(df[col_brand] == b) & (df[col_product] == p)]["stok_yasi"].median())
                    target_pct = min(45, max(20, a * 6))
                    extras.append(
                        f"Tüm yaş aralıklarında en çok bekleyen ürün {b} – {p} ({a} adet; toplam pay %{share_all}, medyan yaş {med_age_prod} gün). "
                        f"Hedef: 3–4 haftada %{target_pct} azaltım ve yaşlı bantlardan genç bantlara çekmek. "
                        f"Gerekçe: bu model stok havuzunun en büyük tekil yükünü oluşturuyor; agresif fiyat + kanal kaydırma + takas programı ile hızlı likidasyon mümkündür."
                    )

            lines.extend(extras)

            # --- Final metin ---
            ai_yorum_final = "\n".join(lines)

            # --- Context (grafikler ve yorum) ---
            context = {
                "form": form,
                "stok_analiz": df.to_dict(orient="records"),
                "segment_labels": json.dumps(segment_labels),
                "segment_datasets": json.dumps(segment_datasets),
                "marka_labels": json.dumps(marka_labels),
                "marka_datasets": json.dumps(marka_datasets),
                "stok_analiz_ai": ai_yorum_final,
                "focus_band": focus_band,
            }
        else:
            context["form"] = form
    else:
        context["form"] = StokForm()

    return render(request, "stock/stok_analysis.html", context)
