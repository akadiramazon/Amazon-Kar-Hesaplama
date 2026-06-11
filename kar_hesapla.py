import streamlit as st
import pandas as pd
... (diğer importlar)

st.title("🎯 Amazon CEO Finansal Analiz & Gerçek Zamanlı Envanter Paneli")

# 🌟 BUTONU TAM BURAYA YAPIŞTIR
if maliyet_file is not None and live_stock_file is not None:
    # ... (o verdiğim buton kodu)import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Finansal Analiz & Gerçek Zamanlı Envanter Paneli")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

# 🚀 CANLI STOK KUTUSU (.txt desteği)
live_stock_file = st.sidebar.file_uploader("3️⃣ Canlı Amazon Stok Raporunu Seçin (.txt)", type=["txt"], key="live_stock")

# TEMEL DOSYALAR YOKSA KILAVUZ GÖSTERİR VE DURUR
if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

# DOSYALAR GELDİYSE ANA MOTOR ÇALIŞIR
try:
    # 1. Maliyet Dosyasını Oku
    try: df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(maliyet_file, encoding='latin1')

    df_master.columns = df_master.columns.str.strip()
    asin_col = 'ASIN' if 'ASIN' in df_master.columns else ('SKU' if 'SKU' in df_master.columns else None)

    df_master = df_master.dropna(subset=['ÜRÜN ADI', 'KDV li Maaliyet'])
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()

    def clean_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('.', '').replace(',', '.').replace('TRY','').strip()
        try: return float(val_str)
        except: return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master['KDV li Maaliyet'].apply(clean_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master['GERÇEK SATIŞ FİYATI'].apply(clean_num)
    
    # Excel'deki eski sabit stok sütunu
    stok_col = [c for c in df_master.columns if 'STOK' in c.upper()]
    df_master['Guncel_Stok_num'] = df_master[stok_col[0]].apply(clean_num) if stok_col else 0.0

    if asin_col:
        df_master['ASIN_clean'] = df_master[asin_col].astype(str).str.strip().str.upper()

    # 🌟 EĞER CANLI STOK (.TXT) DOSYASI YÜKLENDİYSE EXCELDEKİ STOKLARI GÜNCELLE
    live_stock_dict = {}
    if live_stock_file is not None:
        try:
            df_live_stock = pd.read_csv(live_stock_file, sep='\t', on_bad_lines='skip', encoding='utf-8')
        except:
            df_live_stock = pd.read_csv(live_stock_file, sep='\t', on_bad_lines='skip', encoding='latin1')
            
        df_live_stock.columns = df_live_stock.columns.str.strip()
        
        amz_asin_key = 'asin' if 'asin' in df_live_stock.columns else ([c for c in df_live_stock.columns if 'ASIN' in c.upper() or 'SKU' in c.upper()] + [None])[0]
        amz_qty_key = 'afn-fulfillable-quantity' if 'afn-fulfillable-quantity' in df_live_stock.columns else ('quantity' if 'quantity' in df_live_stock.columns else [c for c in df_live_stock.columns if 'QTY' in c.upper() or 'QUANTITY' in c.upper() or 'STOK' in c.upper() or 'MİKTAR' in c.upper()][0])
        
        if amz_asin_key and amz_qty_key:
            for _, row in df_live_stock.iterrows():
                a_code = str(row[amz_asin_key]).strip().upper()
                try: q_val = float(row[amz_qty_key])
                except: q_val = 0.0
                live_stock_dict[a_code] = q_val
            
            if asin_col:
                df_master['Guncel_Stok_num'] = df_master['ASIN_clean'].map(lambda x: live_stock_dict.get(x, 0.0))

    # 2. Amazon Finans Dosyalarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    df_amazon_all.columns = df_amazon_all.columns.str.strip()

    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    # 📅 TARİH SÜTUNU AYARLAMA
    if 'Tarih/Saat' in df_amazon_all.columns:
        df_amazon_all['Clean_Date'] = df_amazon_all['Tarih/Saat'].str.split(' ').str[0]
        df_amazon_all['Clean_Date'] = pd.to_datetime(df_amazon_all['Clean_Date'], format='%d.%m.%Y', errors='coerce')
        
        min_date = df_amazon_all['Clean_Date'].min()
        max_date = df_amazon_all['Clean_Date'].max()
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Zaman Filtresi")
        selected_dates = st.sidebar.date_input("Analiz Aralığı Seçin", [min_date, max_date], min_value=min_date, max_value=max_date)
        
        if len(selected_dates) == 2:
            start_date, end_date = selected_dates
            df_amazon_all = df_amazon_all[(df_amazon_all['Clean_Date'] >= pd.to_datetime(start_date)) & (df_amazon_all['Clean_Date'] <= pd.to_datetime(end_date))]

    # 🎯 ASIN BAZLI NOKTA ATIŞI EŞLEŞTİRME
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    amazon_asin_col = 'ASIN' if 'ASIN' in df_amazon_all.columns else ([c for c in df_amazon_all.columns if 'ASIN' in c.upper() or 'SKU' in c.upper()] + [None])[0]

    for name in unique_amazon_names:
        search_name = str(name).strip()
        matched_row = None
        
        asin_match = re.search(r'(B[0-9A-Z]{9})', search_name.upper())
        if asin_match and asin_col:
            extracted_asin = asin_match.group(1)
            master_match = df_master[df_master['ASIN_clean'] == extracted_asin]
            if not master_match.empty:
                matched_row = master_match.iloc[0]
        
        if matched_row is None and amazon_asin_col and asin_col:
            sample_row = df_amazon_all[df_amazon_all['Ürün Detayları'] == name]
            if not sample_row.empty:
                amz_asin = str(sample_row.iloc[0][amazon_asin_col]).strip().upper()
                master_match = df_master[df_master['ASIN_clean'] == amz_asin]
                if not master_match.empty:
                    matched_row = master_match.iloc[0]

        if matched_row is None:
            clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.startswith(clean_search, na=False)]
            if matches.empty:
                kisa_baslangic = clean_search[:15].lower()
                matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(kisa_baslangic, regex=False, na=False)]
            if not matches.empty:
                matched_row = matches.iloc[0]

        if matched_row is not None:
            mapping[name] = {
                'Master_Name': matched_row['ÜRÜN ADI_clean'], 'Maliyet': matched_row['KDV_li_Maliyet_num'],
                'Tekli_Satis': matched_row['Gercek_Satis_Fiyati_num'], 'Mevcut_Stok': matched_row['Guncel_Stok_num']
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
        if live_stock_file is not None:
            return base_stok
        return max(0, base_stok - r['Net Satış Adedi'])

    product_summary['Mevcut Canlı Stok'] = product_summary.apply(get_kalan_stok, axis=1)
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

    # STOK ALARMI KONTROLÜ
    kritik_stoklar = product_summary[product_summary['Mevcut Canlı Stok'] <= 5][['Sizin Listedeki Tam Adı', 'Mevcut Canlı Stok']].drop_duplicates()

    # 📑 SEKMELİ SAYFA TASARIMI
    sekme1, sekme2, sekme3, sekme4 = st.tabs(["💰 Ana Finans Paneli", "🚨 Kritik Stok Alarmları", "📉 İade Analiz Merkezi", "💤 Canlı Ölü Stok Radarı"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Seçili Tarihteki Net Hakediş", f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KAR: {final_net_kar:,.2f} TL")

        st.markdown("---")
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
            st.warning("⚠️ Aşağıdaki ürünlerin gerçek stoku bitmek üzere kanka! Sipariş geçmeyi unutma.")
            st.dataframe(kritik_stoklar, use_container_width=True)
        else:
            st.info("✅ Harika! Şu anda stoku kritik seviyeye düşen hiçbir ürün yok kanka.")

    with sekme3:
        st.subheader("📉 En Çok İade Gelen Sabıkalı Ürünler")
        iade_tablosu = product_summary[product_summary['İade Adedi'] > 0][['Sizin Listedeki Tam Adı', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']].sort_values(by='İade Adedi', ascending=False)
        
        if not iade_tablosu.empty:
            st.error("⚠️ İadesi en yüksek olan ürünler listelenmiştir. Kalite veya paketlemeyi kontrol etmek isteyebilirsin.")
            st.dataframe(iade_tablosu, use_container_width=True)
        else:
            st.info("🎉 Maşallah kanka! İncelediğin bu tarih aralığında hiç iade almamışsın.")

    with sekme4:
        st.subheader("💤 %100 Doğrulanmış Ölü Stok Radarı")
        if live_stock_file is not None:
            st.success("✅ Canlı Amazon Envanter Raporu başarıyla yüklendi! Ölü stok verileri %100 güncel Amazon sayımıyla doğrulanmıştır kanka.")
        else:
            st.warning("⚠️ Şu an sadece Excel'deki tahmini stok verilerini kullanıyorum. Gerçek zamanlı analiz için sol menüden Amazon .txt envanter raporunu yükle kanka!")
            
        satilan_urunler = set(df_valid_actions['Gercek_Urun_Adi'].dropna().unique())
        
        # 🌟 GÜNCELLEME: ASIN SÜTUNUNU DA TABLOYA GETİRİYORUZ
        olu_stoklar = df_master[~df_master['ÜRÜN ADI_clean'].isin(satilan_urunler)][['ASIN_clean', 'ÜRÜN ADI_clean', 'Guncel_Stok_num', 'KDV_li_Maliyet_num']]
        olu_stoklar = olu_stoklar[olu_stoklar['Guncel_Stok_num'] > 0]
        
        if not olu_stoklar.empty:
            olu_stoklar['Depoda Bağlı Kalan Sermaye (TL)'] = olu_stoklar['Guncel_Stok_num'] * olu_stoklar['KDV_li_Maliyet_num']
            olu_stoklar = olu_stoklar.rename(columns={
                'ASIN_clean': 'ASIN Kodu',
                'ÜRÜN ADI_clean': 'Hiç Satmayan Ölü Ürün Adı',
                'Guncel_Stok_num': 'Amazon Deposundaki Canlı Stok',
                'KDV_li_Maliyet_num': 'Birim Ürün Maliyeti (TL)'
            }).sort_values(by='Depoda Bağlı Kalan Sermaye (TL)', ascending=False)
            
            # Sütun sırasını göze şık gelecek şekilde ayarla (Önce ASIN gelsin)
            olu_stoklar = olu_stoklar[['ASIN Kodu', 'Hiç Satmayan Ölü Ürün Adı', 'Amazon Deposundaki Canlı Stok', 'Birim Ürün Maliyeti (TL)', 'Depoda Bağlı Kalan Sermaye (TL)']]
            
            st.dataframe(olu_stoklar, use_container_width=True)
        else:
            st.success("🎉 Muazzam kanka! Bu dönemde depodaki her malından en az 1 tane satmışsın, ölü sermayen sıfır!")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
