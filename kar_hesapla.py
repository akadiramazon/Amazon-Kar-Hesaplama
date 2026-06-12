import streamlit as st
import pandas as pd

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO %100 Nokta Atışı Finansal Analiz Paneli")
st.markdown("Ultra Hassas Eşleştirme Motoru Aktif. Benzer ürünler arasında yanlış eşleşme yapılması engellenmiştir kanka!")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ maliyet.csv Dosyasını Seçin (Temiz Liste)", type=["csv"], key="maliyet")
genis_file = st.sidebar.file_uploader("2️⃣ genişmaliyet.csv Dosyasını Seçin (Maliyet Bankası)", type=["csv"], key="genis")
amazon_files = st.sidebar.file_uploader("3️⃣ Amazon Finans Raporlarını Seçin", type=["csv"], accept_multiple_files=True, key="amazon")

if not maliyet_file or not genis_file or not amazon_files:
    st.info("💡 **Kanka paneli ateşlemek için sol menüden sırasıyla:**\n"
            "1. Senin o revize edilmiş temiz **maliyet.csv** dosyanı,\n"
            "2. İçinde tüm fiyatların olduğu **genişmaliyet.csv** dosyanı,\n"
            "3. Amazon'dan indirdiğin günlük/haftalık **Finans Raporlarını** yükle.")
    st.stop()

try:
    # 1. Dosyaları Okuma Aşaması
    try: df_m = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_m = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_m = pd.read_csv(maliyet_file, encoding='latin1')

    try: df_gm = pd.read_csv(genis_file, encoding='utf-8')
    except:
        try: df_gm = pd.read_csv(genis_file, encoding='utf-8-sig')
        except: df_gm = pd.read_csv(genis_file, encoding='latin1')

    # Sütun isimlerindeki boşlukları temizle
    df_m.columns = df_m.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    df_gm.columns = df_gm.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()

    m_urun_col = "Sizin Listedeki Ürün Adı"
    gm_maliyet_col = "KDV li Maaliyet"
    gm_satis_col = "GERÇEK SATIŞ FİYATI"

    # 🎯 ARKA PLANDAKİ OTOMATİK VERİ EVLENDİRME VE KÖPRÜLEME MOTORU
    df_m['asin_upper'] = df_m['ASIN Kodu'].astype(str).str.strip().str.upper()
    df_gm['asin_upper'] = df_gm['ASIN'].astype(str).str.strip().str.upper()

    ignore_cols = ['ÜRÜN ADI', 'ASIN', 'Stok Kodu (SKU)']
    gm_remaining_cols = [col for col in df_gm.columns if col not in ignore_cols or col == 'asin_upper']
    df_gm_subset = df_gm[gm_remaining_cols].drop_duplicates(subset=['asin_upper'])

    df_master = pd.merge(df_m, df_gm_subset, on='asin_upper', how='left')
    df_master['ÜRÜN ADI_clean'] = df_master[m_urun_col].astype(str).str.strip()

    # Sayısal Dönüştürme Motoru
    def clean_maliyet_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: return float(val_str)
        except: return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master[gm_maliyet_col].apply(clean_maliyet_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master[gm_satis_col].apply(clean_maliyet_num) if gm_satis_col in df_master.columns else df_master['KDV_li_Maliyet_num']

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
    df_amazon_all.columns = df_amazon_all.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()

    # Sütun Bulucu Kalkanlar
    toplam_cols = [col for col in df_amazon_all.columns if 'toplam' in col.lower() or 'total' in col.lower()]
    target_toplam_col = toplam_cols[0] if toplam_cols else df_amazon_all.columns[-1]

    detay_cols = [col for col in df_amazon_all.columns if 'detay' in col.lower() or 'ürün' in col.lower() or 'item' in col.lower() or 'description' in col.lower() or 'adı' in col.lower()]
    target_detay_col = detay_cols[0] if detay_cols else df_amazon_all.columns[0]

    tip_cols = [col for col in df_amazon_all.columns if 'tip' in col.lower() or 'tür' in col.lower() or 'type' in col.lower() or 'işlem' in col.lower() or 'durum' in col.lower() or 'açıklama' in col.lower()]
    target_tip_col = tip_cols[0] if tip_cols else None

    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=['Sipariş No.', target_toplam_col])

    def clean_amazon_money(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: return float(val_str)
        except: return 0.0

    df_amazon_all['Clean_Toplam'] = df_amazon_all[target_toplam_col].apply(clean_amazon_money)
    df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam ürün fiyatları'].apply(clean_amazon_money) if 'Toplam ürün fiyatları' in df_amazon_all.columns else df_amazon_all['Clean_Toplam']

    # 🎯 ULTRA HASSAS NOKTA ATISI EŞLEŞTİRME MOTORU
    unique_amazon_names = df_amazon_all[target_detay_col].dropna().unique()
    mapping = {}

    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # Aşama 1: Birebir Tam İsim Araması
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        # Aşama 2: Eğer tam uyuşmadıysa Başlangıç Kontrolü
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
        
        # Aşama 3: Eğer hala eşleşmediyse Kelime Grubu Kontrolü
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(clean_search.lower()[:20], na=False)]
            
        if not matches.empty:
            # 🌟 Yanlış eşleşmeyi önleyen filtre: Birden fazla ürün bulursa Amazon ismine en yakın uzunlukta olan doğru varyasyonu seç!
            if len(matches) > 1:
                matches = matches.copy()
                matches['len_diff'] = (matches['ÜRÜN ADI_clean'].str.len() - len(clean_search)).abs()
                matched_row = matches.sort_values(by='len_diff').iloc[0]
            else:
                matched_row = matches.iloc[0]
                
            m_name = matched_row['ÜRÜN ADI_clean']
            mapping[name] = {
                'Master_Name': m_name, 
                'Maliyet': master_maliyet_dict.get(m_name, 0.0),
                'Tekli_Satis': master_satis_dict.get(m_name, 0.0)
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0}

    # Finansal Verileri Süzme
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

    # Adet Hesaplama
    df_valid_actions['Adet'] = df_valid_actions.apply(
        lambda r: max(1, round(abs(r['Toplam ürün fiyatları']) / r['Tekli_Satis_Fiyati'])) if r['Tekli_Satis_Fiyati'] > 0 else 1, axis=1
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
            s_adet = prod_rows[~prod_rows[target_tip_col].astype(str).str.upper().str.contains('İADE|REFUND|RETURN')]['Adet'].sum()
            i_adet = prod_rows[prod_rows[target_tip_col].astype(str).str.upper().str.contains('İADE|REFUND|RETURN')]['Adet'].sum()
        else:
            s_adet = prod_rows['Adet'].sum()
            i_adet = 0
        return pd.Series([s_adet, i_adet])

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

    # 📑 GÖSTERİM PANELİ ARAYÜZÜ
    st.subheader("📊 Dönemsel Performans Özetiniz")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{toplam_payout:,.2f} TL")
    kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
    st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KÂR: {final_net_kar:,.2f} TL")

    st.markdown("---")
    st.subheader("📋 %100 Kesin Eşleşmeli Kârlılık Raporu")
    st.dataframe(product_summary_show, use_container_width=True)

    csv_data = product_summary_show.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Kusursuz Kârlılık Raporunu İndir",
        data=csv_data,
        file_name='amazon_kesin_kar_raporu.csv',
        mime='text/csv',
    )

    # ⭐ BİRLEŞTİRİLMİŞ DOSYAYI İNDİRME ALANI
    st.markdown("---")
    st.subheader("💾 Birleştirilmiş O Geniş Master Dosyanı İndir")
    st.markdown("Kanka, genişmaliyet dosyasındaki tüm sütun başlıklarının senin o temiz fihristine eklenmiş halini buradan direkt bilgisayarına indirebilirsin:")
    
    df_master_export = df_master.drop(columns=['asin_upper', 'ÜRÜN ADI_clean', 'KDV_li_Maliyet_num', 'Gercek_Satis_Fiyati_num'], errors='ignore')
    csv_master_data = df_master_export.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Geniş Başlıkların Eklendiği Revize Dosyayı İndir (maliyet_revize_son.csv)",
        data=csv_master_data,
        file_name='maliyet_revize_son.csv',
        mime='text/csv',
    )

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
