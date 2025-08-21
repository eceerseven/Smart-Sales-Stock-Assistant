import pandas as pd
from datetime import datetime

AGE_BUCKETS = [
    ("1-3 Ay", 30, 90),
    ("3-6 Ay", 91, 180),
    ("6-9 Ay", 181, 270),
    ("9-12 Ay", 271, 365),
    ("12-24 Ay", 366, 730),
    ("24+ Ay", 731, float('inf'))
]

def hesapla_stok_yasi(df):
    # 🧼 Sütun adlarını normalize et (güvenlik için tekrar ekliyoruz)
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

    today = datetime.today()
    df["stok_yasi_gun"] = (today - pd.to_datetime(df["stok_giris_tarihi"])).dt.days

    def get_age_bucket(days):
        for label, min_day, max_day in AGE_BUCKETS:
            if min_day <= days <= max_day:
                return label
        return "Bilinmiyor"

    df["yaş_aralığı"] = df["stok_yasi_gun"].apply(get_age_bucket)

    grouped = df.groupby(["yaş_aralığı", "segment"]).agg({"ürün_adı": "count"}).reset_index()
    grouped.rename(columns={"ürün_adı": "ürün_sayısı"}, inplace=True)

    pivot_df = grouped.pivot(index="yaş_aralığı", columns="segment", values="ürün_sayısı").fillna(0).astype(int)
    pivot_df = pivot_df.reindex([bucket[0] for bucket in AGE_BUCKETS])  # Doğru sırada

    return pivot_df, df
