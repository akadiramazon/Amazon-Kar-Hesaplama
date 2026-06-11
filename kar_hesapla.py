import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from datetime import datetime

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Finansal Analiz & Dashboard Paneli")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

# NOT DEFTERİ HAFIZASINI YÜKLEME
manuel_hafiza = {}
if os.path.exists("yanlis_eslesme_duzelt.txt"):
    try:
        with open("yanlis_eslesme_duzelt.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and ":" in line:
                    parts = line.split(":", 1)
                    clean_key = re.sub(r'\s+', '', parts[0].strip().lower().replace('...', ''))
                    manuel_hafiza[clean_key] = parts[1].strip()
    except:
        pass

# DOSYALAR YOKSA KILAVUZ GÖSTERİR VE DURUR
if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Raporlarınızı** seçin kanka!")
    st.stop()

# DOSYALAR GELDİYSE ANA MOTOR ÇALIŞIR
try:
    # 1. Maliyet Dosyasını Oku
    try: df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(maliyet_file, encoding='latin1')

    df_master = df_master.dropna(subset=['ÜRÜN ADI', 'KDV li Maaliyet'])
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()

    def clean_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('.', '').replace(',', '.').replace('TRY','').strip()
        try: return float(val_str)
        except: return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master['KDV li Maaliyet'].apply(clean_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master['GERÇEK SATIŞ FİYATI'].apply(clean_num)
    df_master['Guncel_Stok_num'] = df_master['GÜNCEL STOK\nMİKTARI\nHAFTALIK '].apply(clean_num)

    # 2. Amazon Dosyalarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    # 📅 TARİH SÜTUNUNU FORMATLAMA VE AYARLAMA
    if 'Tarih/Saat' in df_amazon_all.columns:
        df_amazon_all['Clean_Date'] = df_amazon_all['Tarih/Saat'].str.split(' ').str[0]
        df_amazon_all['Clean_Date'] = pd.to_datetime(df_amazon_all['Clean_Date'], format='%d.%m.%Y', errors='coerce')
        
        min_date = df_amazon_all['Clean_Date'].min()
        max_date = df_amazon_all['Clean_Date'].max()
        
        # Sol menüye tarih filtresi ekleme
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Zaman Filtresi")
        selected_dates = st.sidebar.date_input("Analiz Aralığı Seçin", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
            df_amazon_all = df_amazon_all[(df_amazon_all['Clean_Date'] >= pd.to_datetime(start_date)) & (df_amazon_all['Clean_Date'] <= pd.to_datetime(end_date))]

    # 3. İsim Eşleştirme Sözlüğü
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search_key = re.sub(r'\s+', '', search_name.lower().replace('...', ''))
        
        if clean_search_key in manuel_hafiza:
            dogru_isim = manuel_hafiza[clean_search_key]
            matches = df_master[df_master['ÜRÜN ADI_clean'] == dogru_isim]
            if not matches.empty:
                best_match = matches.iloc[0]
                mapping[name] = {
                    'Master_Name': best_match['ÜRÜN ADI_clean'], 'Maliyet': best_match['KDV_li_Maliyet_num'],
                    'Tekli_Satis': best_match['Gercek_Satis_Fiyati_num'], 'Mevcut_Stok': best_match['Guncel_Stok_num']
                }
                continue

        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.startswith(clean_search, na=False)]
        if matches.empty:
            kisa_baslangic = clean_search[:15].lower()
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(kisa_baslangic, regex=False, na=False)]
            
        if not matches.empty:
            best_match = matches.iloc[0]
            mapping[name] = {
                'Master_Name': best_match['ÜRÜN ADI_clean'], 'Maliyet': best_match['KDV_li_Maliyet_num'],
                'Tekli_Satis': best_match['Gercek_Satis_Fiyati_num'], 'Mevcut_Stok': best_match['Guncel_Stok_num']
            }
        else:
            s_name = clean_search.lower()
            keywords = [w for w in re.split(r'\W+', s_name) if len(w) > 2]
            best_score = 0
            best_row = None
            for idx, row in df_master.iterrows():
                m_name = str(row['ÜRÜN ADI_clean']).lower()
                score = sum(1 for kw in keywords if kw in m_name)
                if score > best_score:
                    best_score = score
                    best_row = row
            if best_score >= max(2, len(keywords) * 0.4):
                mapping[name] = {
                    'Master_Name': best_row['ÜRÜN ADI_clean'], 'Maliyet': best_row['KDV_li_Maliyet_num'],
                    'Tekli_Satis': best_row['Gercek_Satis_Fiyati_num'], 'Mevcut_Stok': best_row['Guncel_Stok_num']
                }
            else:
                mapping[name] = {'Master_Name': "MALIYET LISTESINDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0, 'Mevcut_Stok': 0.0}

    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])
    df_valid_actions['Giris_Stok'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Mevcut_Stok'])

    def detect_quantity(row):
        if row['Tekli_Satis_Fiyati'] > 0 and abs(row['Toplam ürün fiyatları']) > 0:
            return max(1, round(abs(row['Toplam ürün fiyatları']) / row['Tekli_Satis_Fiyati']))
        return 1

    df_valid_actions['Hesaplanan_Adet'] = df_valid_actions.apply(detect_quantity, axis=1)
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Hesaplanan_Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Hesaplanan_Adet']), axis=1
    )
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # KÜMÜLATİF ÖZET TABLOSU
    product_summary = df_valid_actions.groupby(['Ürün Detayları', 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Toplam (TRY)', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    def get_detailed_qtys(r):
        s_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Sipariş Ödemesi')]['Hesaplanan_Adet'].sum()
        i_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Para İadesi')]['Hesaplanan_Adet'].sum()
        return pd.Series([s_adet, i_adet, round((i_adet / s_adet * 100), 2) if s_adet > 0 else 0.0])

    product_summary[['Satış Adedi', 'İade Adedi', 'İade Oranı (%)']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']

    def get_kalan_stok(r):
        base_stok = df_valid_actions[df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']]['Giris_Stok'].iloc[0]
        return max(0, base_stok - r['Net Satış Adedi'])

    product_summary['Kalan Stok'] = product_summary.apply(get_kalan_stok, axis=1)
    product_summary['Kar Marjı (%)'] = product_summary.apply(lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Net_Gelen'] * 100), 2) if r['Toplam_Net_Gelen'] > 0 else 0, axis=1)
    product_summary['ROI (%)'] = product_summary.apply(lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Mal_Maliyeti'] * 100), 2) if r['Toplam_Mal_Maliyeti'] > 0 else 0, axis=1)
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Ürün Adı',
        'Gercek_Urun_Adi': 'Sizin Listedeki Tam Adı',
        'Toplam_Net_Gelen': 'Net Ciro (TRY)',
        'Toplam_Mal_Maliyeti': 'Toplam Ürün Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kar (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 🚨 STOK ALARMI KONTROLÜ (5 adetten az kalanlar)
    kritik_stoklar = product_summary[product_summary['Kalan Stok'] <= 5][['Sizin Listedeki Tam Adı', 'Kalan Stok']].drop_duplicates()

    # 📑 SEKMELİ SAYFA TASARIMI
    sekme1, sekme2, sekme3 = st.tabs(["💰 Ana Finans Paneli", "🚨 Stok Alarmları", "📉 İade Analiz Merkezi"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Seçili Tarihteki Net Hakediş", f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KAR: {final_net_kar:,.2f} TL")

        st.markdown("---")
        # Grafik
        fig_kar = px.bar(product_summary.head(10), x='Net Temiz Kar (TRY)', y='Sizin Listedeki Tam Adı', 
                         orientation='h', title="🏆 En Çok Kar Getiren Top 10 Ürün",
                         color='Net Temiz Kar (TRY)', color_continuous_scale='Greens')
        fig_kar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_kar, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Tüm Ürünlerin Detay Tablosu")
        st.dataframe(product_summary, use_container_width=True)

    with sekme2:
        st.subheader("🚨 Stoku Kritik Seviyede Olan Ürünler (5 veya Daha Az)")
        if not kritik_stoklar.empty:
            st.warning("⚠️ Aşağıdaki ürünlerin stoku bitmek üzere kanka! Sipariş geçmeyi unutma.")
            st.dataframe(kritik_stoklar, use_container_width=True)
        else:
            st.info("✅ Harika! Şu anda stoku kritik seviyeye düşen hiçbir ürün yok kanka.")

    with sekme3:
        st.subheader("📉 En Çok İade Gelen Sabıkalı Ürünler")
        iade_tablosu = product_summary[product_summary['İade Adedi'] > 0][['Sizin Listedeki Tam Adı', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']].sort_values(by='İade Adedi', ascending=False)
        
        if not iade_tablosu.empty:
            st.error("iadesi en yüksek olan ürünler listelenmiştir. Bu ürünlerin kalitesini veya kargo paketlemesini kontrol etmek isteyebilirsin.")
            st.dataframe(iade_tablosu, use_container_width=True)
        else:
            st.info("🎉 Maşallah kanka! İncelediğin bu tarih aralığında hiç iade almamışsın.")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")