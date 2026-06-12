import streamlit as st
import pandas as pd
import plotly.express as px

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon Finansal Analiz Paneli", layout="wide")

st.title("🎯 Amazon CEO Finansal Analiz Paneli")
st.markdown("Amazon raporundaki **Ürün Detayları** ile Maliyet listesindeki **ÜRÜN ADI** birebir nokta atışı ve doğru matematiksel formatta eşleştirilir.")
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

    # Boş satırları temizle
    df_master = df_master.dropna(subset=['ÜRÜN ADI', 'KDV li Maaliyet'])
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()

    # MALİYET İÇİN VİRGÜLÜ NOKTAYA ÇEVİRME MOTORU
    def clean_maliyet_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').strip()
        # Eğer binlik ayırıcı nokta, kuruş virgül ise (Örn: 1.664,00)
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: 
            return float(val_str)
        except: 
            return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master['KDV li Maaliyet'].apply(clean_maliyet_num)
    
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

    # Çift kayıtları Sipariş No bazında temizle
    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    # AMAZON İÇİN NOKTASAL HASSASİYET MOTORU
    df_amazon_all['Toplam (TRY)'] = pd.to_numeric(df_amazon_all['Toplam (TRY)'], errors='coerce').fillna(0.0)
    df_amazon_all['Toplam ürün fiyatları'] = pd.to_numeric(df_amazon_all['Toplam ürün fiyatları'], errors='coerce').fillna(0.0)

    # Miktar Sütunu Standardizasyonu
    stok_col_amz = [c for c in df_amazon_all.columns if c.lower() == 'miktar']
    if stok_col_amz:
        df_amazon_all['miktar_clean'] = pd.to_numeric(df_amazon_all[stok_col_amz[0]], errors='coerce').fillna(1)
    else:
        df_amazon_all['miktar_clean'] = 1

    # 🎯 %100 NOKTA ATIŞI TEKLİ EŞLEŞTİRME MOTORU
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # 1. Aşama: Tam birebir eşleşme var mı?
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        # 2. Aşama: Yoksa tam başlangıç eşleşmesi var mı?
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        # 3. Aşama: O da yoksa akıllı içerik araması yap ama SADECE EN İYİ uyuşan tek bir satırı al!
        if matches.empty:
            kisa_baslangic = clean_search[:20].lower()
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(kisa_baslangic, regex=False, na=False)]
            
        if not matches.empty:
            matched_row = matches.iloc[0]
            mapping[name] = {
                'Master_Name': matched_row['ÜRÜN ADI_clean'], 
                'Maliyet': matched_row['KDV_li_Maliyet_num']
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0}

    # İşlemleri Filtreleme ve Maliyet Atama
    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])

    # 📦 GERÇEK ADET KONTROLÜ
    df_valid_actions['Adet'] = df_valid_actions['miktar_clean'].abs()
    
    # Toplam Maliyet Hesabı (Sipariş Ödemesinde normal, Para İadesinde eksi maliyet olarak yansır)
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Adet']), axis=1
    )
    
    # NET KÂR MATEMATİĞİ
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # KÜMÜLATİF ÖZET TABLOSU
    product_summary = df_valid_actions.groupby(['Ürün Detayları', 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Toplam (TRY)', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    # Satış ve İade adetlerini süzme
    def get_detailed_qtys(r):
        s_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Sipariş Ödemesi')]['Adet'].sum()
        i_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Para İadesi')]['Adet'].sum()
        return pd.Series([s_adet, i_adet, round((i_adet / s_adet * 100), 2) if s_adet > 0 else 0.0])

    product_summary[['Satış Adedi', 'İade Adedi', 'İade Oranı (%)']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Ürün Adı',
        'Gercek_Urun_Adi': 'Sizin Listedeki Tam Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)',
        'Toplam_Mal_Maliyeti': 'Toplam Ürün Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    # Genel Toplam Hesapları (Kuruşu kuruşuna gerçek payout)
    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 📑 SEKMELİ SAYFA TASARIMI
    sekme1, sekme2 = st.tabs(["💰 Ana Finans Paneli", "📉 İade Analiz Merkezi"])

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
        st.subheader("📋 Tüm Ürünlerin Kusursuz Analiz Tablosu")
        st.dataframe(product_summary, use_container_width=True)

    with sekme2:
        st.subheader("📉 İade Durumu")
        iade_tablosu = product_summary[product_summary['İade Adedi'] > 0][['Sizin Listedeki Tam Adı', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']].sort_values(by='İade Adedi', ascending=False)
        if not iade_tablosu.empty:
            st.dataframe(iade_tablosu, use_container_width=True)
        else:
            st.info("🎉 Maşallah kanka! İncelediğin bu tarih aralığında hiç iade almamışsın.")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
