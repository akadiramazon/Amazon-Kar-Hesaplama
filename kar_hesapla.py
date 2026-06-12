import streamlit as st
import pandas as pd

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO %100 Nokta Atışı Finansal Analiz Paneli")
st.markdown("Sütun uyuşmazlığı hatası düzeltilmiştir. Maliyetler doğrudan ürünler.csv üzerinden çekilir.")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ ürünler.csv Listesini Seçin", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

if not maliyet_file or not amazon_files:
    st.info("💡 Paneli çalıştırmak için sol menüden **ürünler.csv** dosyanızı ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

try:
    # 1. Ana Maliyet Dosyasını Oku (ürünler.csv)
    try: df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(maliyet_file, encoding='latin1')

    # Sütun isimlerindeki gizli boşlukları temizle
    df_master.columns = df_master.columns.str.strip()
    
    # Sütun İsimlerini Senin Listene Göre Tamamen Sabitledik (Hata Önleyici Çizgi)
    urun_adi_col = "ÜRÜN ADI"
    maliyet_col = "KDV li Maaliyet"
    satis_col = "GERÇEK SATIŞ FİYATI"

    # Gerekli sütunlar mevcut mu kontrolü
    if urun_adi_col not in df_master.columns or maliyet_col not in df_master.columns:
        st.error(f"🚨 Yüklediğiniz ürünler.csv dosyasında '{urun_adi_col}' veya '{maliyet_col}' sütunu bulunamadı! Lütfen dosyanızı kontrol edin.")
        st.stop()

    df_master = df_master.dropna(subset=[urun_adi_col, maliyet_col])
    df_master['ÜRÜN ADI_clean'] = df_master[urun_adi_col].astype(str).str.strip()

    # Sayısal Dönüştürme Motoru (Maliyetlerdeki virgül/nokta krizini çözer)
    def clean_maliyet_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').replace('TL','').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: return float(val_str)
        except: return 0.0

    # Gerçek maliyetleri ve satış fiyatlarını senin ana listenizden (ürünler.csv) canlı okuyoruz!
    df_master['KDV_li_Maliyet_num'] = df_master[maliyet_col].apply(clean_maliyet_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master[satis_col].apply(clean_maliyet_num) if satis_col in df_master.columns else df_master['KDV_li_Maliyet_num']

    master_maliyet_dict = df_master.set_index('ÜRÜN ADI_clean')['KDV_li_Maliyet_num'].to_dict()
    master_satis_dict = df_master.set_index('ÜRÜN ADI_clean')['Gercek_Satis_Fiyati_num'].to_dict()

    # 2. Amazon Raporlarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    df_amazon_all.columns = df_amazon_all.columns.str.strip()

    # Mükerrer sipariş koruması
    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    df_amazon_all['Toplam (TRY)'] = pd.to_numeric(df_amazon_all['Toplam (TRY)'], errors='coerce').fillna(0.0)
    df_amazon_all['Toplam ürün fiyatları'] = pd.to_numeric(df_amazon_all['Toplam ürün fiyatları'], errors='coerce').fillna(0.0)

    # 🎯 ARKA PLANDAKİ CANLI HİBRİT EŞLEŞTİRME MOTORU
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # 1. Aşama: Harfi harfine birebir tam isim araması
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        # 2. Aşama: Başlangıç kontrolü (Amazon'daki üç noktalı yarım isimleri yakalar)
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        # 3. Aşama: Gelişmiş içerik araması (İlk 15 karakter güvenlik sınırı)
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(clean_search.lower()[:15], na=False)]
            
        if not matches.empty:
            matched_row = matches.iloc[0]
            m_name = matched_row['ÜRÜN ADI_clean']
            # Eşleşen ürünün fiyat ve maliyetini sizin ana listenizden (ürünler.csv) çekiyoruz
            mapping[name] = {
                'Master_Name': m_name, 
                'Maliyet': master_maliyet_dict.get(m_name, 0.0),
                'Tekli_Satis': master_satis_dict.get(m_name, 0.0)
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0}

    # Finansal Verileri Ayrıştırma
    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])

    # 📦 HASSAS ADET BULUCU MOTOR
    df_valid_actions['Adet'] = df_valid_actions.apply(
        lambda r: max(1, round(abs(r['Toplam ürün fiyatları']) / r['Tekli_Satis_Fiyati'])) if r['Tekli_Satis_Fiyati'] > 0 else 1, axis=1
    )
    
    # Siparişe göre kümülatif maliyet ve net kâr hesabı
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Adet']), axis=1
    )
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # ÖZET TABLO OLUŞTURMA
    product_summary = df_valid_actions.groupby(['Ürün Detayları', 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Toplam (TRY)', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    def get_detailed_qtys(r):
        s_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Sipariş Ödemesi')]['Adet'].sum()
        i_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Para İadesi')]['Adet'].sum()
        return pd.Series([s_adet, i_adet])

    product_summary[['Satış Adedi', 'İade Adedi']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary_show = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Raporundaki Ürün Adı', 'Gercek_Urun_Adi': 'Sizin Listede Eşleşen Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Mal Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 📑 GÖSTERİM PANELİ ARAYÜZÜ
    st.subheader("📊 Dönemsel Performans Özetiniz")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{topham_payout if 'topham_payout' in locals() else toplam_payout:,.2f} TL")
    kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
    st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KÂR: {final_net_kar:,.2f} TL")

    st.markdown("---")
    st.subheader("📋 %100 Canlı Eşleşmeli Kârlılık Rapor Tablosu")
    st.dataframe(product_summary_show, use_container_width=True)

    csv_data = product_summary_show.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Kusursuz Kârlılık Raporunu İndir",
        data=csv_data,
        file_name='amazon_kesin_kar_raporu.csv',
        mime='text/csv',
    )

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
