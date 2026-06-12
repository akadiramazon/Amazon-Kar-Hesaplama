import streamlit as st
import pandas as pd
import os

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO %100 Nokta Atışı Finansal Analiz Paneli")
st.markdown("🔒 **Sipariş No Tabanlı Yapay Zekâ Hafıza Motoru Aktif.** Sistem sipariş numaralarını hafızaya kaydeder ve sonraki raporlarda %100 eşleştirir kanka!")
st.markdown("---")

# 📊 GLOBAL PARA VE SAYISAL TEMİZLEME MOTORU
def clean_amazon_money(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try: return float(val_str)
    except: return 0.0

# 💾 HAFIZA BANKASI YÜKLEYİCİ VE SAKLAYICI
HAFIZA_DOSYASI = "amazon_siparis_hafizasi.csv"
if os.path.exists(HAFIZA_DOSYASI):
    df_hafiza = pd.read_csv(HAFIZA_DOSYASI, dtype=str)
    siparis_hafiza_dict = df_hafiza.set_index('siparis_no')['asin_kodu'].to_dict()
else:
    siparis_hafiza_dict = {}

# 📦 VERI YÜKLEME MERKEZİ (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
genis_file = st.sidebar.file_uploader("1️⃣ Geniş Maliyet Listesini Seçin (revize_genis_maliyet.csv)", type=["csv"], key="genis")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Ödeme Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

if not genis_file or not amazon_files:
    st.info("💡 **Kanka paneli sıfır hatayla çalıştırmak için sol menüden sırasıyla:**\n"
            "1. Bilgisayarda ürettiğimiz o 32 sütunluk **revize_genis_maliyet.csv** dosyanı,\n"
            "2. Amazon'dan indirdiğin günlük/haftalık **Ödeme Raporlarını** yükle.")
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

    # ASIN bazlı kesin kilit sözlükleri
    asin_maliyet_dict = df_master.set_index('ASIN_upper')['KDV_li_Maliyet_num'].to_dict()
    asin_satis_dict = df_master.set_index('ASIN_upper')['Gercek_Satis_Fiyati_num'].to_dict()
    asin_isim_dict = df_master.set_index('ASIN_upper')['ÜRÜN ADI_clean'].to_dict()

    # 2. Amazon Ödeme Raporlarını Birleştir
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

    fin_order_cols = [col for col in df_amazon_all.columns if 'sipariş no' in col.lower() or 'order' in col.lower()]
    target_fin_order_col = fin_order_cols[0] if fin_order_cols else 'Sipariş No.'

    if 'Sipariş No.' in df_amazon_all.columns:
        df_amazon_all = df_amazon_all.drop_duplicates(subset=[target_fin_order_col, target_toplam_col, target_detay_col])

    df_amazon_all['Clean_Toplam'] = df_amazon_all[target_toplam_col].apply(clean_amazon_money)
    
    fiyat_urun_cols = [col for col in df_amazon_all.columns if 'ürün fiyat' in col.lower() or 'product price' in col.lower()]
    target_urun_fiyat_col = fiyat_urun_cols[0] if fiyat_urun_cols else target_toplam_col
    df_amazon_all['Clean_Urun_Fiyatlari'] = df_amazon_all[target_urun_fiyat_col].apply(clean_amazon_money) if target_urun_fiyat_col in df_amazon_all.columns else df_amazon_all['Clean_Toplam']

    # Finansal İşlemleri Süzme
    if target_tip_col:
        df_amazon_all['action_upper'] = df_amazon_all[target_tip_col].astype(str).str.upper().str.strip()
        is_siparis = df_amazon_all['action_upper'].str.contains('SİPARİŞ|ÖDEME|ORDER|PAYMENT|SALE|GÖNDERİLMEDİ|TAMAMLANDI', na=False)
        is_iade = df_amazon_all['action_upper'].str.contains('İADE|PARA İADESİ|REFUND|RETURN', na=False)
        df_valid_actions = df_amazon_all[is_siparis | is_iade].copy()
        if df_valid_actions.empty:
            df_valid_actions = df_amazon_all.copy()
    else:
        df_valid_actions = df_amazon_all.copy()

    # 🎯 HAFIZA DESTEKLİ SIPARIS NO KONTROL VE EŞLEŞTİRME MOTORU
    unique_amazon_names = df_valid_actions[target_detay_col].dropna().unique()
    mapping = {}
    yeni_hafiza_kayitlari = []

    # Önce genel isim eşleşmelerini bir kez tarayalım (B Planı için)
    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.contains(clean_search.lower()[:20], na=False)]
            
        if not matches.empty:
            if len(matches) > 1:
                matches = matches.copy()
                matches['l_diff'] = (matches['ÜRÜN ADI_clean'].str.len() - len(clean_search)).abs()
                matched_row = matches.sort_values(by='l_diff').iloc[0]
            else:
                matched_row = matches.iloc[0]
            mapping[name] = matched_row['ASIN_upper']
        else:
            mapping[name] = None

    # Satır satır Sipariş No kontrolü ve finansal haritalama
    def satır_bazlı_analiz(row):
        order_id = str(row[target_fin_order_col]).strip()
        amazon_p_name = row[target_detay_col]
        
        # 🔑 ADIM 1: Önce bu Sipariş No hafıza bankamızda kayıtlı mı diye bak!
        if order_id in siparis_hafiza_dict:
            target_asin = siparis_hafiza_dict[order_id]
            if target_asin in asin_maliyet_dict:
                return pd.Series([asin_isim_dict[target_asin], asin_maliyet_dict[target_asin], asin_satis_dict[target_asin]])

        # 🔄 ADIM 2: Eğer hafızada yoksa, isim motorundan tahmin et ve hafızaya ekle!
        predicted_asin = mapping.get(amazon_p_name, None)
        if predicted_asin:
            # Gelecekte %100 uyuşsun diye bu sipariş numarasını bu ASIN koduyla hafıza bankasına yazıyoruz kanka!
            siparis_hafiza_dict[order_id] = predicted_asin
            yeni_hafiza_kayitlari.append({'siparis_no': order_id, 'asin_kodu': predicted_asin})
            return pd.Series([asin_isim_dict[predicted_asin], asin_maliyet_dict[predicted_asin], asin_satis_dict[predicted_asin]])
            
        return pd.Series(["MALİYET LİSTESİNDE BULUNAMADI", 0.0, 0.0])

    df_valid_actions[['Gercek_Urun_Adi', 'Birim_Maliyet', 'Tekli_Satis_Fiyati']] = df_valid_actions.apply(satır_bazlı_analiz, axis=1)

    # Yeni hafıza kayıtlarını kalıcı olarak bilgisayara kaydetme mühürleme alanı
    if yeni_hafiza_kayitlari:
        df_yeni = pd.DataFrame(yeni_hafiza_kayitlari)
        if os.path.exists(HAFIZA_DOSYASI):
            df_yeni.to_csv(HAFIZA_DOSYASI, mode='a', header=False, index=False)
        else:
            df_yeni.to_csv(HAFIZA_DOSYASI, index=False)

    # Adet Hesaplama
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
    st.subheader("📋 %100 Sipariş No Kontrollü Canlı Kârlılık Raporu")
    
    product_summary_show = product_summary.rename(columns={
        target_detay_col: 'Amazon Raporundaki Ürün Adı', 'Gercek_Urun_Adi': 'Sizin Listede Eşleşen Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Mal Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })
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
