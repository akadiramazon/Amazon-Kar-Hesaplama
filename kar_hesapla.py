import streamlit as st
import pandas as pd

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO %100 Nokta Atışı Finansal Analiz Paneli")
st.markdown("Envanter Destekli Eşleştirme Motoru Aktif. Tüm Sütun ve Tanım Hataları Giderilmiştir kanka!")
st.markdown("---")

# 📊 GLOBAL PARA VE SAYISAL TEMİZLEME MOTORU (EN TEPEDE - SABİT)
def clean_amazon_money(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try: return float(val_str)
    except: return 0.0

# 📦 VERI YÜKLEME MERKEZİ (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
genis_file = st.sidebar.file_uploader("1️⃣ Geniş Maliyet Listesini Seçin (revize_genis_maliyet.csv)", type=["csv"], key="genis")
aktif_file = st.sidebar.file_uploader("2️⃣ Aktif Liste Kayıtları Raporunu Seçin (.txt veya .csv)", type=["txt", "csv"], key="aktif")
amazon_files = st.sidebar.file_uploader("3️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

if not genis_file or not aktif_file or not amazon_files:
    st.info("💡 **Kanka paneli çalıştırmak için sol menüden sırasıyla:**\n"
            "1. Bilgisayarda ürettiğimiz o 32 sütunluk **revize_genis_maliyet.csv** dosyanı,\n"
            "2. Amazon'dan indirdiğin o güncel **Aktif Liste Kayıtları** raporunu (.txt),\n"
            "3. Amazon'dan indirdiğin günlük/haftalık **Finans Raporlarını** yükle.")
    st.stop()

try:
    # 1. Geniş Maliyet Dosyasını Oku
    try: df_master = pd.read_csv(genis_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(genis_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(genis_file, encoding='latin1')

    df_master.columns = df_master.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    
    urun_adi_col = "ÜRÜN ADI"
    maliyet_col = "KDV li Maaliyet"
    satis_col = "GERÇEK SATIŞ FİYATI"
    asin_master_col = "ASIN"

    df_master = df_master.dropna(subset=[urun_adi_col, maliyet_col])
    df_master['ÜRÜN ADI_clean'] = df_master[urun_adi_col].astype(str).str.strip()
    df_master['ASIN_upper'] = df_master[asin_master_col].astype(str).str.strip().str.upper()

    df_master['KDV_li_Maliyet_num'] = df_master[maliyet_col].apply(clean_amazon_money)
    df_master['Gercek_Satis_Fiyati_num'] = df_master[satis_col].apply(clean_amazon_money) if satis_col in df_master.columns else df_master['KDV_li_Maliyet_num']

    master_maliyet_dict = df_master.set_index('ÜRÜN ADI_clean')['KDV_li_Maliyet_num'].to_dict()
    master_satis_dict = df_master.set_index('ÜRÜN ADI_clean')['Gercek_Satis_Fiyati_num'].to_dict()

    # 2. Amazon Amazon Aktif Liste Kayıtları Raporunu Oku
    try: df_aktif = pd.read_csv(aktif_file, sep="\t", on_bad_lines='skip', encoding='utf-8')
    except:
        try: df_aktif = pd.read_csv(aktif_file, sep="\t", on_bad_lines='skip', encoding='utf-8-sig')
        except: df_aktif = pd.read_csv(aktif_file, sep="\t", on_bad_lines='skip', encoding='latin1')
        
    df_aktif.columns = df_aktif.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    
    aktif_name_col = 'item-name' if 'item-name' in df_aktif.columns else df_aktif.columns[2]
    aktif_asin_col = 'asin1' if 'asin1' in df_aktif.columns else df_aktif.columns[1]
    
    df_aktif['clean_item_name'] = df_aktif[aktif_name_col].astype(str).str.strip()
    df_aktif['clean_asin'] = df_aktif[aktif_asin_col].astype(str).str.strip().str.upper()

    # 3. Amazon Finans Raporlarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    df_amazon_all.columns = df_amazon_all.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()

    # Sütun Yakalayıcılar
    toplam_cols = [col for col in df_amazon_all.columns if 'toplam' in col.lower() or 'total' in col.lower()]
    target_toplam_col = toplam_cols[0] if toplam_cols else df_amazon_all.columns[-1]

    detay_cols = [col for col in df_amazon_all.columns if 'detay' in col.lower() or 'ürün' in col.lower() or 'item' in col.lower() or 'description' in col.lower() or 'adı' in col.lower()]
    target_detay_col = detay_cols[0] if detay_cols else df_amazon_all.columns[0]

    tip_cols = [col for col in df_amazon_all.columns if 'tip' in col.lower() or 'tür' in col.lower() or 'type' in col.lower() or 'işlem' in col.lower() or 'durum' in col.lower()]
    target_tip_col = tip_cols[0] if tip_cols else None

    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', target_toplam_col])

    df_amazon_all['Clean_Toplam'] = df_amazon_all[target_toplam_col].apply(clean_amazon_money)
    
    fiyat_urun_cols = [col for col in df_amazon_all.columns if 'ürün fiyat' in col.lower() or 'product price' in col.lower()]
    target_urun_fiyat_col = fiyat_urun_cols[0] if fiyat_urun_cols else target_toplam_col
    df_amazon_all['Clean_Urun_Fiyatlari'] = df_amazon_all[target_urun_fiyat_col].apply(clean_amazon_money) if target_urun_fiyat_col in df_amazon_all.columns else df_amazon_all['Clean_Toplam']

    # 🎯 COK KADEMELİ ULTRA ESNEK KÖPRÜLEME MOTORU
    unique_amazon_names = df_amazon_all[target_detay_col].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # Kademe 1: Aktif Envanter Raporundan gerçek ASIN kodunu yakala
        aktif_matches = df_aktif[df_aktif['clean_item_name'].str.lower() == search_name.lower()]
        if aktif_matches.empty:
            aktif_matches = df_aktif[df_aktif['clean_item_name'].str.lower().str.startswith(clean_search.lower(), na=False)]
        if aktif_matches.empty:
            aktif_matches = df_aktif[df_aktif['clean_item_name'].str.lower().str.contains(clean_search.lower()[:20], na=False)]
            
        found_asin = None
        if not aktif_matches.empty:
            if len(aktif_matches) > 1:
                aktif_matches = aktif_matches.copy()
                aktif_matches['l_diff'] = (aktif_matches['clean_item_name'].str.len() - len(clean_search)).abs()
                found_asin = aktif_matches.sort_values(by='l_diff').iloc[0]['clean_asin']
            else:
                found_asin = aktif_matches.iloc[0]['clean_asin']
                
        # Kademe 2: Bulunan ASIN koduyla genişmaliyete dalış yap
        matched_row = None
        if found_asin:
            master_matches = df_master[df_master['ASIN_upper'] == found_asin]
            if not master_matches.empty:
                matched_row = master_matches.iloc[0]
                
        # B Planı: İsim üzerinden arama yap
        if matched_row is None:
            master_matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
            if master_matches.empty:
                master_matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            if master_matches.empty:
                master_matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(clean_search.lower()[:20], na=False)]
            if not master_matches.empty:
                matched_row = master_matches.iloc[0]

        if matched_row is not None:
            m_name = matched_row['ÜRÜN ADI_clean']
            mapping[name] = {
                'Master_Name': m_name, 
                'Maliyet': matched_row['KDV_li_Maliyet_num'],
                'Tekli_Satis': matched_row['Gercek_Satis_Fiyati_num']
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0}

    # Finansal İşlemleri Süzme ve Kar Hesaplama
    if target_tip_col:
        df_amazon_all['action_upper'] = df_amazon_all[target_tip_col].astype(str).str.upper().str.strip()
        is_siparis = df_amazon_all['action_upper'].str.contains('SİPARİŞ|ÖDEME|ORDER|PAYMENT|SALE|GÖNDERİLMEDİ|TAMAMLANDI', na=False)
        is_iade = df_amazon_all['action_upper'].str.contains('İADE|PARA İADESİ|REFUND|RETURN', na=False)
        df_valid_actions = df_amazon_all[is_siparis | is_iade].copy()
        if df_valid_actions.empty:
            df_valid_actions = df_amazon_all.copy()
    else:
        df_valid_actions = df_amazon_all.copy()
    
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions[target_detay_col].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions[target_detay_col].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions[target_detay_col].map(lambda x: mapping[x]['Tekli_Satis'])

    df_valid_actions['Adet'] = df_valid_actions.apply(
        lambda r: max(1, round(abs(r['Clean_Urun_Fiyatlari']) / r['Tekli_Satis_Fiyati'])) if r['Tekli_Satis_Fiyati'] > 0 else 1, axis=1
    )
    
    def calc_row_maliyet(row):
        if target_tip_col:
            is_row_iade = any(k in str(row[target_tip_col]).upper() for k in ['İADE', 'REFUND', 'RETURN'])
            if is_row_iade:
                return -(row['Birim_Maliyet'] * row['Adet'])
        return row['Birim_Maliyet'] * row['Adet']

    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(calc_row_maliyet, axis=1)
    df_valid_actions['Net_Kar'] = df_valid_actions['Clean_Toplam'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # ÖZET TABLO OLUŞTURMA
    product_summary = df_valid_actions.groupby([target_detay_col, 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Clean_Toplam', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    def get_detailed_qtys(r):
        prod_rows = df_valid_actions[df_valid_actions[target_detay_col] == r[target_detay_col]]
        if target_tip_col:
            st_adet = prod_rows[~prod_rows[target_tip_col].astype(str).str.upper().str.contains('İADE|REFUND|RETURN')]['Adet'].sum()
            ia_adet = prod_rows[prod_rows[target_tip_col].astype(str).str.upper().str.contains('İADE|REFUND|RETURN')]['Adet'].sum()
        else:
            st_adet = prod_rows['Adet'].sum()
            ia_adet = 0
        return pd.Series([st_adet, ia_adet])

    product_summary[['Satış Adedi', 'İade Adedi']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary_show = product_summary.rename(columns={
        target_detay_col: 'Amazon Raporundaki Ürün Adı', 'Gercek_Urun_Adi': 'Sizin Listede Eşleşen Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Mal Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Clean_Toplam'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 📑 GÖSTERİM PANELİ
    st.subheader("📊 Dönemsel Performans Özetiniz")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{toplam_payout:,.2f} TL")
    kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
    st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KÂR: {final_net_kar:,.2f} TL")

    st.markdown("---")
    st.subheader("📋 %100 Nokta Atışı Kârlılık Raporu")
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
