import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Yapay Zekâ & Hafızalı Finansal Analiz Paneli")
st.markdown("Sistem kullandıkça ürünlerinizi öğrenir ve hafızaya alır. Raporlar günlük de olsa %100 nokta atışı kâr çıkarır.")
st.markdown("---")

# 📁 HAFIZA DOSYASI KONTROLÜ
HAFIZA_DOSYASI = "eslesme_hafizasi.csv"
if os.path.exists(HAFIZA_DOSYASI):
    df_hafiza = pd.read_csv(HAFIZA_DOSYASI)
    # Temizlik
    df_hafiza['amz_name'] = df_hafiza['amz_name'].astype(str).str.strip()
    df_hafiza['master_name'] = df_hafiza['master_name'].astype(str).str.strip()
    hafiza_dict = df_hafiza.set_index('amz_name')['master_name'].to_dict()
else:
    hafiza_dict = {}

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

try:
    # 1. Maliyet Dosyasını Oku
    try: df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(maliyet_file, encoding='latin1')

    df_master.columns = df_master.columns.str.strip()
    df_master = df_master.dropna(subset=['ÜRÜN ADI', 'KDV li Maaliyet'])
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()

    # Sayısal Dönüştürme Motoru
    def clean_maliyet_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: return float(val_str)
        except: return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master['KDV li Maaliyet'].apply(clean_maliyet_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master['GERÇEK SATIŞ FİYATI'].apply(clean_maliyet_num)

    # Master listeyi hızlı arama sözlüğüne çevir
    master_maliyet_dict = df_master.set_index('ÜRÜN ADI_clean')['KDV_li_Maliyet_num'].to_dict()
    master_satis_dict = df_master.set_index('ÜRÜN ADI_clean')['Gercek_Satis_Fiyati_num'].to_dict()
    master_urun_listesi = sorted(df_master['ÜRÜN ADI_clean'].unique().tolist())

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

    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', 'İşlem tipi', 'Ürün Detayları', 'Toplam (TRY)'])

    df_amazon_all['Toplam (TRY)'] = pd.to_numeric(df_amazon_all['Toplam (TRY)'], errors='coerce').fillna(0.0)
    df_amazon_all['Toplam ürün fiyatları'] = pd.to_numeric(df_amazon_all['Toplam ürün fiyatları'], errors='coerce').fillna(0.0)

    # 🎯 HAFIZALI HİBRİT EŞLEŞTİRME MOTORU
    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    def get_words(text):
        text_clean = str(text).lower().replace('...', '').replace('-', ' ').replace(',', ' ')
        return set([w for w in text_clean.split() if len(w) > 1])

    for name in unique_amazon_names:
        search_name = str(name).strip()
        
        # 0. AŞAMA: HAFIZADA VAR MI? (Kuş uçurtmayan kısım)
        if search_name in hafiza_dict:
            m_name = hafiza_dict[search_name]
            if m_name in master_maliyet_dict:
                mapping[name] = {
                    'Master_Name': m_name,
                    'Maliyet': master_maliyet_dict[m_name],
                    'Tekli_Satis': master_satis_dict[m_name],
                    'Kaynak': "🧠 HAFIZA"
                }
                continue

        # Hafızada yoksa akıllı arama algoritması devreye girer
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        if matches.empty:
            amz_words = get_words(clean_search)
            best_score = 0
            best_row = None
            for _, row in df_master.iterrows():
                master_words = get_words(row['ÜRÜN ADI_clean'])
                score = len(amz_words.intersection(master_words))
                if score > best_score:
                    best_score = score
                    best_row = row
            if best_row is not None and best_score >= 1:
                matches = pd.DataFrame([best_row])

        if not matches.empty:
            matched_row = matches.iloc[0]
            mapping[name] = {
                'Master_Name': matched_row['ÜRÜN ADI_clean'], 
                'Maliyet': matched_row['KDV_li_Maliyet_num'],
                'Tekli_Satis': matched_row['Gercek_Satis_Fiyati_num'],
                'Kaynak': "🤖 YAPAY ZEKÂ"
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0, 'Kaynak': "❌ BULUNAMADI"}

    # Finansal Hesaplamalar
    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])

    # Adet Bulucu
    def detect_quantity(row):
        if row['Tekli_Satis_Fiyati'] > 0 and abs(row['Toplam ürün fiyatları']) > 0:
            return max(1, round(abs(row['Toplam ürün fiyatları']) / row['Tekli_Satis_Fiyati']))
        return 1

    df_valid_actions['Adet'] = df_valid_actions.apply(detect_quantity, axis=1)
    
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Adet']), axis=1
    )
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # KÜMÜLATİF TABLO
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

    # Sütun İsimlerini Güzelleştirme
    product_summary_show = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Raporundaki Adı', 'Gercek_Urun_Adi': 'Sizin Listedeki Karşılığı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Ürün Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 📑 ARAYÜZ GÖSTERİMİ
    sekme1, sekme2 = st.tabs(["💰 Ana Finans Paneli", "🧠 Yapay Zekâ Eşleşme Hafıza Odası"])

    with sekme1:
        st.subheader("📊 Günlük Performans Özetiniz")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{topham_payout:,.2f} TL" if 'topham_payout' in locals() else f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        st.success(f"🔥 NET TEMİZ KÂR: {final_net_kar:,.2f} TL")

        st.markdown("---")
        st.subheader("📋 Kârlılık Raporu Tablosu")
        st.dataframe(product_summary_show, use_container_width=True)

    with sekme2:
        st.subheader("🧠 Akıllı Eşleşme Düzenleyici ve Onay Merkezi")
        st.markdown("Kodun otomatik yaptığı eşleşmeleri aşağıdan kontrol edebilirsin kanka. Yanlış olan varsa doğrusunu seçip hafızaya kazı.")
        
        # Kullanıcı arayüzünde eşleştirme formu
        with st.form("hafiza_form"):
            güncellenecek_veriler = []
            for idx, row in product_summary.iterrows():
                amz_name = row['Ürün Detayları']
                current_match = row['Gercek_Urun_Adi']
                kaynak_turu = mapping[amz_name]['Kaynak']
                
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.text_area(f"🛒 Amazon Adı ({kaynak_turu})", value=amz_name, disabled=True, key=f"amz_{idx}")
                
                # Eğer listede yoksa varsayılanı ayarla
                default_idx = master_urun_listesi.index(current_match) if current_match in master_urun_listesi else 0
                secilen_master = c2.selectbox(f"🎯 Sizin Listeden Eşleşen", options=master_urun_listesi, index=default_idx, key=f"master_{idx}")
                
                güncellenecek_veriler.append({'amz_name': amz_name, 'master_name': secilen_master})
                st.markdown("---")
                
            submitted = st.form_submit_button("🧠 Seçimleri Onayla ve Hafızaya Kaydet")
            
            if submitted:
                df_yeni_hafiza = pd.DataFrame(güncellenecek_veriler)
                df_yeni_hafiza.to_csv(HAFIZA_DOSYASI, index=False)
                st.success("🎉 Harika kanka! Seçtiğin tüm ürün eşleşmeleri kalıcı olarak hafızaya yazıldı. Sayfa yenileniyor...")
                st.rerun()

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
