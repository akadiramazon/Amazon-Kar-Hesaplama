import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime

# 🌟 SADELİK VE NETLİK AYARI
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
    try:
        df_master = pd.read_csv(maliyet_file)
    except Exception as e:
        st.error(f"Maliyet dosyası (.csv) okunurken sistemsel hata oluştu: {e}")
        st.stop()
        
    # Sütun isimlerini temizle
    df_master.columns = df_master.columns.str.strip()
    
    # Gerekli ana sütunların varlığını kontrol et
    required_master_cols = ['ASIN', 'ÜRÜN ADI', 'KDV\'li Maliyet']
    for col in required_master_cols:
        if col not in df_master.columns:
            st.error(f"Maliyet dosyasında '{col}' sütunu bulunamadı! Lütfen excel sütun isimlerini kontrol et kanka.")
            st.stop()
            
    # Temizlik ve Sayısallaştırma Modülleri (SENİN ORİJİNAL MANTIĞIN)
    df_master['ASIN_clean'] = df_master['ASIN'].astype(str).str.strip().str.upper()
    df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()
    
    def clean_currency(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip().replace('.', '').replace(',', '.')
        val_clean = re.sub(r'[^\d.]', '', val_str)
        try:
            return float(val_clean)
        except:
            return 0.0
            
    df_master['KDV_li_Maliyet_num'] = df_master['KDV\'li Maliyet'].apply(clean_currency)
    
    # GÜNCEL STOK SÜTUNUNU BULMA
    guncel_stok_col = next((c for c in ['Güncel Stok', 'GÜNCEL STOK', 'Stok', 'STOK', 'FBA Stok'] if c in df_master.columns), None)
    if guncel_stok_col:
        df_master['Guncel_Stok_num'] = pd.to_numeric(df_master[guncel_stok_col], errors='coerce').fillna(0).astype(int)
    else:
        df_master['Guncel_Stok_num'] = 0

    # 2. Amazon Finans Raporlarını Birleştir
    amazon_df_list = []
    for f in amazon_files:
        try:
            temp_df = pd.read_csv(f)
            temp_df.columns = temp_df.columns.str.strip()
            amazon_df_list.append(temp_df)
        except Exception as e:
            st.warning(f"{f.name} dosyası okunurken atlandı: {e}")
            
    if not amazon_df_list:
        st.error("Yüklenen Amazon finans raporlarından hiçbiri geçerli bir veri içermiyor!")
        st.stop()
        
    df_amazon_raw = pd.concat(amazon_df_list, ignore_index=True)
    
    # Amazon Raporu Sütun Standartlaştırma (SENİN ORİJİNAL MANTIĞIN)
    amz_cols = df_amazon_raw.columns.tolist()
    type_col = next((c for c in amz_cols if c.lower() in ['type', 'tür', 'işlem türü', 'transaction type', 'event_type']), None)
    amount_col = next((c for c in amz_cols if c.lower() in ['amount', 'tutar', 'total', 'toplam', 'fiyat', 'price']), None)
    sku_col = next((c for c in amz_cols if c.lower() in ['seller-sku', 'stok kodu', 'sku', 'ürün kodu']), None)
    desc_col = next((c for c in amz_cols if c.lower() in ['description', 'ürün detayları', 'açıklama', 'product details']), None)
    
    if not type_col or not amount_col:
        st.error("Amazon finans raporunda 'Tür' (Type) veya 'Tutar' (Amount) sütunları tespit edilemedi kanka!")
        st.stop()
        
    # Amazon Sayı Temizliği (SENİN ORİJİNAL MANTIĞIN)
    def clean_amazon_amount(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        if ',' in val_str and '.' in val_str:
            if val_str.find('.') < val_str.find(','):
                val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str and '.' not in val_str:
            val_str = val_str.replace(',', '.')
        val_clean = re.sub(r'[^\d.-]', '', val_str)
        try:
            return float(val_clean)
        except:
            return 0.0
            
    df_amazon_raw['Amount_num'] = df_amazon_raw[amount_col].apply(clean_amazon_amount)
    
    # 🕵️‍♂️ REKOR KIRAN ASIN CIMBIZLAMA ALGORİTMASI (SENİN ORİJİNAL MANTIĞIN)
    def extract_asin_or_sku(row):
        desc = str(row.get(desc_col, '')).strip().upper() if desc_col else ''
        sku = str(row.get(sku_col, '')).strip().upper() if sku_col else ''
        
        match_asin = re.search(r'B0[A-Z0-9]{8}', desc)
        if match_asin:
            return match_asin.group(0)
            
        match_jbm = re.search(r'JBM[A-Z0-9]+', desc)
        if match_jbm:
            return match_jbm.group(0)
            
        if sku and sku != 'NAN':
            return sku
            
        return None
        
    df_amazon_raw['Key_Code'] = df_amazon_raw.apply(extract_asin_or_sku, axis=1)
    
    # 🎯 HESAPLAMA MOTORU VE KÂR-ZARAR AYRIŞTIRMASI (%100 SENİN KODUNUN KALBİ)
    total_revenue = 0.0
    total_amazon_fees = 0.0
    total_product_cost = 0.0
    
    valid_records = []
    
    for idx, row in df_amazon_raw.iterrows():
        t_type = str(row[type_col]).lower()
        amt = row['Amount_num']
        k_code = row['Key_Code']
        
        if amt == 0:
            continue
            
        if amt > 0 and (any(x in t_type for x in ['order', 'satış', 'sipariş', 'deal', 'payment']) or t_type == 'nan' or t_type == ''):
            total_revenue += amt
            
            maliyet_row = pd.DataFrame()
            if k_code:
                maliyet_row = df_master[df_master['ASIN_clean'] == k_code]
                if maliyet_row.empty:
                    maliyet_row = df_master[df_master['ASIN_clean'].str.contains(k_code, regex=False)]
                    
            if not maliyet_row.empty:
                b_maliyet = maliyet_row.iloc[0]['KDV_li_Maliyet_num']
                u_adi = maliyet_row.iloc[0]['ÜRÜN ADI_clean']
                total_product_cost += b_maliyet
                
                valid_records.append({
                    'İşlem Türü': row[type_col],
                    'Kod (ASIN/SKU)': k_code,
                    'Gercek_Urun_Adi': u_adi,
                    'Satış Tutarı (TL)': amt,
                    'Ürün Maliyeti (TL)': b_maliyet
                })
            else:
                valid_records.append({
                    'İşlem Türü': row[type_col],
                    'Kod (ASIN/SKU)': k_code if k_code else 'Tanımsız Ürün',
                    'Gercek_Urun_Adi': 'Maliyet Listesinde Bulunamadı',
                    'Satış Tutarı (TL)': amt,
                    'Ürün Maliyeti (TL)': 0.0
                })
        else:
            total_amazon_fees += abs(amt)
            
    df_valid_actions = pd.DataFrame(valid_records)
    
    # Finansal Sonuçların Bağlanması
    net_profit = total_revenue - total_amazon_fees - total_product_cost
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0
    
    # 📥 YENİ GELİŞTİRME: TEK TIKLA FİNANSAL ÖZET İNDİRME SİHİRBAZI
    # Arka plandaki hiçbir hesabı bozmadan sadece en son sonuçları çeker kanka
    su_an = datetime.now().strftime("%Y-%m-%d_%H-%M")
    rapor_metni = f"""==================================================
🎯 AMAZON CEO FINANSAL PERFORMANS RAPORU
==================================================
Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 ANA MALİ GÖSTERGELER (TL)
--------------------------------------------------
💵 Toplam Net Ciro          : {total_revenue:,.2f} TL
💸 Amazon Genel Kesintileri  : {total_amazon_fees:,.2f} TL
📦 Karşılaştırılan Maliyet  : {total_product_cost:,.2f} TL
🔥 NET TEMİZ KÂRIN          : {net_profit:,.2f} TL
📈 Kâr Marjı                : %{profit_margin:.1f}

==================================================
Satışlarınız daim, dükkanınız bereketli olsun! 🚀
=================================================="""

    # Sol menünün en altına şık indirme butonunu ekliyoruz
    st.sidebar.markdown("---")
    st.sidebar.subheader("📑 Özet Rapor Çıktısı")
    st.sidebar.download_button(
        label="📥 Finansal Özeti İndir (.txt)",
        data=rapor_metni,
        file_name=f"Amazon_Finans_Ozet_{su_an}.txt",
        mime="text/plain"
    )
    
    # 📈 DEV METRİK KUTULARI (FİNANSAL ÖZET PANELİ)
    st.subheader("💰 Bu Dönemin Finansal Rapor Özeti")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 Toplam Net Ciro", f"{total_revenue:,.2f} TL")
    with col2:
        st.metric("💸 Amazon Genel Kesintileri", f"{total_amazon_fees:,.2f} TL")
    with col3:
        st.metric("📦 Karşılaştırılan Toplam Maliyet", f"{total_product_cost:,.2f} TL")
    with col4:
        st.metric("🔥 NET TEMİZ KÂRIN", f"{net_profit:,.2f} TL", delta=f"%{profit_margin:.1f} Kâr Marjı")
        
    st.markdown("---")
    
    # 📊 GRAFİKSEL ANALİZ ALANI
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📈 Gelir vs Gider Dengesi")
        finans_ozet = pd.DataFrame({
            'Finansal Kalem': ['Net Ciro', 'Amazon Kesintileri', 'Ürün Maliyetleri', 'Net Temiz Kâr'],
            'Tutar (TL)': [total_revenue, total_amazon_fees, total_product_cost, max(0, net_profit)]
        })
        fig1 = px.bar(finans_ozet, x='Finansal Kalem', y='Tutar (TL)', color='Finansal Kalem', text_auto='.2s',
                      color_discrete_sequence=px.colors.qualitative.Set2)
        st.plotly_chart(fig1, use_container_width=True)
        
    with g2:
        st.subheader("🎯 Kârlılık Dağılım Röntgeni")
        fig2 = px.pie(values=[total_amazon_fees, total_product_cost, max(0, net_profit)],
                      names=['Amazon Kesinti ve Giderleri', 'Ürün Ana Maliyetleri', 'Dönem Net Kârı'],
                      color_discrete_sequence=['#ff6b6b', '#4dadf7', '#2ecc71'], hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)
        
    st.markdown("---")
    
    # 🔍 ÖLÜ STOK HESAPLAMA VE ENENVANTER ANALİZİ
    st.subheader("🚨 Depoda Atıl Kalan (Hiç Satmayan) Ölü Stok Analizi")
    if live_stock_file is not None:
        try:
            df_amz_stock = pd.read_csv(live_stock_file, sep='\t', on_bad_lines='skip')
            df_amz_stock.columns = df_amz_stock.columns.str.strip()
            
            if 'asin1' in df_amz_stock.columns and 'quantity-available' in df_amz_stock.columns:
                stock_map = dict(zip(df_amz_stock['asin1'].astype(str).str.strip().str.upper(), df_amz_stock['quantity-available']))
                df_master['Guncel_Stok_num'] = df_master['ASIN_clean'].map(stock_map).fillna(0).astype(int)
            else:
                st.sidebar.warning("Canlı stok dosyasında 'asin1' veya 'quantity-available' sütunları eşleşmedi kanka!")
        except Exception as e:
            st.sidebar.error(f"Canlı stok txt dosyası işlenirken hata: {e}")
            
    if not df_valid_actions.empty:
        satilan_urunler = set(df_valid_actions['Gercek_Urun_Adi'].dropna().unique())
        
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
            
            st.dataframe(olu_stoklar, use_container_width=True)
        else:
            st.success("Tebrikler kanka! Maliyet listendeki tüm aktif stoklu ürünler bu dönemde en az 1 adet satmış. Ölü stok yok! 🔥")
    else:
        st.info("Ölü stok analizi için finans raporunda işlenmiş satış kaydı aranıyor...")

    st.markdown("---")
    st.subheader("📋 Detaylı Ürün Takip Tablosu")
    st.dataframe(df_master[['ASIN_clean', 'ÜRÜN ADI_clean', 'Guncel_Stok_num', 'KDV_li_Maliyet_num']], use_container_width=True)

except Exception as main_e:
    st.error(f"Sistem ana motorunda beklenmeyen bir uyuşmazlık çıktı kanka: {main_e}")
