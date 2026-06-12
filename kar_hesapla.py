import streamlit as st
import pandas as pd
import re
import plotly.express as px

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon Finansal Analiz Paneli", layout="wide")

st.title("🎯 Amazon CEO Finansal Analiz Paneli")
st.markdown("Amazon raporundaki **Ürün Detayları** ile Maliyet listesindeki **ÜRÜN ADI** akıllıca eşleştirilerek net kâr hesaplanır.")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

# TEMEL DOSYALAR YOKSA KILAVUZ GÖSTERİR VE DURUR
if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

# DOSYALAR GELDİYSE ANA MOTOR ÇALIŞIR
try:
    # 1. Maliyet Dosyasını Oku
    try: 
        df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: 
            df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: 
            df_master = pd.read_csv(maliyet_file, encoding='latin1')

    df_master.columns = df_master.columns.str.strip()

    # Boş isim veya maliyet satırlarını temizle
    df_master = df_master.dropna(subset=['ÜRÜN ADI', 'KDV li Maaliyet'])
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()

    # Sayısal Değerleri Temizleme Fonksiyonu
    def clean_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('.', '').replace(',', '.').replace('TRY','').strip()
        try: 
            return float(val_str)
        except: 
            return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master['KDV li Maaliyet'].apply(clean_num)
    
    # Gerçek satış fiyatı sütununu algıla
    satis_fiyati_col = 'GERÇEK SATIŞ FİYATI' if 'GERÇEK SATIŞ FİYATI' in df_master.columns else 'SATIŞ FİYATI\n(KDV DAHİL)'
    df_master['Gercek_Satis_Fiyati_num'] = df_master[satis_fiyati_col].apply(clean_num)
    
    # Maliyet listesindeki güncel stok sütununu bul
    stok_col = [c for c in df_master.columns if 'STOK' in c.upper()]
    df_master['Guncel_Stok_num'] = df_master[stok_col[0]].apply(clean_num) if stok_col else 0.0

    # 2. Amazon Finans Dosyalarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: 
            df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: 
                df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: 
                df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    df_amazon_all.columns = df_amazon_all.columns.str.strip()

    # Benzersiz işlemleri koru
    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    # Sayısal alanları temizle
    df_amazon_all['Toplam (TRY)'] = df_amazon_all['Toplam (TRY)'].apply(clean_num)
    df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam ürün fiyatları'].apply(clean_num)

    # 📅 TARİH SÜTUNU AYARLAMA
    date_col = 'Tarih' if 'Tarih' in df_amazon_all.columns else ('Tarih/Saat' if 'Tarih/Saat' in df_amazon_all.columns else None)
    if date_col:
        df_amazon_all['Clean_Date'] = df_amazon_all[date_col].astype(str).str.split(' ').str[0]
        df_amazon_all['Clean_Date'] = pd.to_datetime(df_amazon_all['Clean_Date'], format='%d.%m.%Y', errors='coerce')
        
        min_date = df_amazon_all['Clean_Date'].min()
        max_date = df_amazon_all['Clean_Date'].max()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Zaman Filtresi")
        selected_dates = st.sidebar.date_input("Analiz Aralığı Seçin", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
            df_amazon_all = df_amazon_all[(df_amazon_all['Clean_Date'] >= pd.to_datetime(start_date)) & (df_amazon_all['Clean_Date'] <= pd.to_datetime(end_date))]

    # 🎯 AKILLI İSİM EŞLEŞTİRME MOTORU
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        matched_row = None
        
        # Amazon isminin sonundaki '...' kısmını temizleyip eşleştirme kalitesi artırılır
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # Tam veya başlangıç eşleşmesi kontrolü
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
        
        if matches.empty:
            # İçerik bazlı akıllı arama (İlk 15 karakter)
            kisa_baslangic = clean_search[:15].lower()
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(kisa_baslangic, regex=False, na=False)]
            
        if not matches.empty:
            matched_row = matches.iloc[0]

        if matched_row is not None:
            mapping[name] = {
                'Master_Name': matched_row['ÜRÜN ADI_clean'], 
                'Maliyet': matched_row['KDV_li_Maliyet_num'],
                'Tekli_Satis': matched_row['Gercek_Satis_Fiyati_num'], 
                'Mevcut_Stok': matched_row['Guncel_Stok_num']
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0, 'Mevcut_Stok': 0.0}

    # Sipariş Ödemesi ve Geri Ödemeleri Ayıkla
    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])
    df_valid_actions['Giris_Stok'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Mevcut_Stok'])

    # 📦 ADET TESPİT MOTORU (Fiyat / Tekli Satış)
    def detect_quantity(row):
        if row['Tekli_Satis_Fiyati'] > 0 and abs(row['Toplam ürün fiyatları']) > 0:
            return max(1, round(abs(row['Toplam ürün fiyatları']) / row['Tekli_Satis_Fiyati']))
        return 1

    df_valid_actions['Hesaplanan_Adet'] = df_valid_actions.apply(detect_quantity, axis=1)
    
    # Toplam ürün maliyetini hesaplama (İadelerde eksi maliyet yansır)
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Hesaplanan_Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Hesaplanan_Adet']), axis=1
    )
    
    # NET KÂR: Amazon'un Yatırdığı Son Tutar - Bizim Ürün Geliş Maliyetimiz
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

    # Kalan Stok Takibi (Maliyet listesindeki stoktan düşer)
    def get_kalan_stok(r):
        base_stok = df_valid_actions[df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']]['Giris_Stok'].iloc[0]
        return max(0, base_stok - r['Net Satış Adedi'])

    product_summary['Mevcut Tahmini Stok'] = product_summary.apply(get_kalan_stok, axis=1)
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Ürün Adı',
        'Gercek_Urun_Adi': 'Sizin Listedeki Tam Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)',
        'Toplam_Mal_Maliyeti': 'Toplam Ürün Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # Stoku azalan ürünlerin tespiti
    kritik_stoklar = product_summary[product_summary['Mevcut Tahmini Stok'] <= 5][['Sizin Listedeki Tam Adı', 'Mevcut Tahmini Stok']].drop_duplicates()

    # 📑 SEKMELİ SAYFA TASARIMI
    sekme1, sekme2, sekme3 = st.tabs(["💰 Ana Finans Paneli", "🚨 Kritik Stok Alarmları", "📉 İade Analiz Merkezi"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KÂR: {final_net_kar:,.2f} TL")

        st.markdown("---")
        fig_kar = px.bar(product_summary.head(10), x='Net Temiz Kâr (TRY)', y='Sizin Listedeki Tam Adı', 
                         orientation='h', title="🏆 En Çok Kâr Getiren Top 10 Ürün",
                         color='Net Temiz Kâr (TRY)', color_continuous_scale='Greens')
        fig_kar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_kar, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Tüm Ürünlerin Detaylı Analiz Tablosu")
        st.dataframe(product_summary, use_container_width=True)

    with sekme2:
        st.subheader("🚨 Listeye Göre Stoku Kritik Seviyede Olan Ürünler (5 veya Daha Az)")
        if not kritik_stoklar.empty:
            st.warning("⚠️ Aşağıdaki ürünlerin maliyet listesindeki stoku bitmek üzere kanka!")
            st.dataframe(kritik_stoklar, use_container_width=True)
        else:
            st.info("✅ Harika! Şu anda stoku kritik seviyeye düşen hiçbir ürün yok kanka.")

    with sekme3:
        st.subheader("📉 En Çok İade Gelen Sabıkalı Ürünler")
        iade_tablosu = product_summary[product_summary['İade Adedi'] > 0][['Sizin Listedeki Tam Adı', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']].sort_values(by='İade Adedi', ascending=False)
        
        if not iade_tablosu.empty:
            st.error("⚠️ İadesi en yüksek olan ürünler listelenmiştir.")
            st.dataframe(iade_tablosu, use_container_width=True)
        else:
            st.info("🎉 Maşallah kanka! İncelediğin bu tarih aralığında hiç iade almamışsın.")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
