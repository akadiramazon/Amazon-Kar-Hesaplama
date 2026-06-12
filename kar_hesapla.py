import streamlit as st
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
    st.info("💡 Paneli canlandırmak için sol taraftan Maliyet Çizelgenizi ve Amazon Finans Raporlarınızı seçin kanka!")
    st.stop()

# DOSYALAR GELDİYSE ANA MOTOR ÇALIŞIR
try:
    # 1. Maliyet Dosyasını Oku
    try:
        df_master = pd.read_csv(maliyet_file)
        df_master.columns = df_master.columns.str.strip()
    except Exception as e:
        st.error(f"Maliyet dosyası okunurken hata: {e}")
        st.stop()
        
    # 2. Amazon Dosyalarını Birleştir ve Oku
    amazon_list = []
    for f in amazon_files:
        try:
            tdf = pd.read_csv(f)
            amazon_list.append(tdf)
        except Exception as e:
            st.warning(f"{f.name} dosyası okunamadı, atlanıyor: {e}")
            
    if not amazon_list:
        st.error("Yüklenen Amazon raporlarından hiçbir veri okunamadı kanka!")
        st.stop()
        
    df_amazon = pd.concat(amazon_list, ignore_index=True)
    df_amazon.columns = df_amazon.columns.str.strip()
    
    # 🌟 KRİTİK TEMİZLİK MOTORU (Orijinal Mantık)
    def clean_amazon_amount(val):
        if pd.isna(val):
            return 0.0
        val_str = str(val).strip()
        val_str = val_str.replace('₺', '').replace('TL', '').strip()
        
        if ',' in val_str and '.' in val_str:
            if val_str.find(',') > val_str.find('.'):
                val_str = val_str.replace('.', '').replace(',', '.')
            else:
                val_str = val_str.replace(',', '')
        elif ',' in val_str and '.' not in val_str:
            val_str = val_str.replace(',', '.')
            
        val_str = re.sub(r'[^\d\.\-]', '', val_str)
        try:
            return float(val_str) if val_str else 0.0
        except:
            return 0.0

    # Tutar sütununu temizle
    tutar_col = None
    for c in ['tutar', 'amount', 'toplam', 'total']:
        for actual_c in df_amazon.columns:
            if c in actual_c.lower():
                tutar_col = actual_c
                break
        if tutar_col:
            break
            
    if not tutar_col:
        st.error("Amazon raporunda 'tutar' veya 'amount' sütunu bulunamadı kanka!")
        st.stop()
        
    df_amazon['Tutar_Clean'] = df_amazon[tutar_col].apply(clean_amazon_amount)
    
    # Açıklama / Tip Sütun tespiti
    tip_col = None
    for c in ['açıklama', 'description', 'tip', 'type']:
        for actual_c in df_amazon.columns:
            if c in actual_c.lower():
                tip_col = actual_c
                break
        if tip_col:
            break
            
    # SKU / Asin Tespiti
    sku_col = None
    for c in ['sku', 'msku', 'ürün', 'item']:
        for actual_c in df_amazon.columns:
            if c in actual_c.lower():
                sku_col = actual_c
                break
        if sku_col:
            break

    # Ürün Adı / Veri Eşleştirme Hazırlığı
    if 'ÜRÜN ADI' in df_master.columns:
        df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].astype(str).str.strip()
    else:
        first_col = df_master.columns[0]
        df_master['ÜRÜN ADI_clean'] = df_master[first_col].astype(str).str.strip()
        
    if 'ASIN' in df_master.columns:
        df_master['ASIN_clean'] = df_master['ASIN'].astype(str).str.strip()
    else:
        df_master['ASIN_clean'] = ""

    def clean_master_maliyet(val):
        if pd.isna(val): return 0.0
        v = str(val).replace('TL','').replace('₺','').strip()
        v = v.replace('.','').replace(',','.')
        try: return float(v) if v else 0.0
        except: return 0.0

    maliyet_col = 'KDV DAHİL MALİYET' if 'KDV DAHİL MALİYET' in df_master.columns else df_master.columns[1]
    df_master['KDV_li_Maliyet_num'] = df_master[maliyet_col].apply(clean_master_maliyet)

    # 📊 FİNANSAL MOTOR HESAPLAMALARI (ORİJİNAL DOKUNULMAZ MOTOR)
    total_revenue = 0.0
    total_amazon_fees = 0.0
    total_product_cost = 0.0
    
    valid_sales_records = []
    
    for idx, row in df_amazon.iterrows():
        ttr = row['Tutar_Clean']
        desc = str(row[tip_col]).lower() if tip_col else ""
        row_sku = str(row[sku_col]).strip() if sku_col else ""
        
        if 'sipariş' in desc or 'order' in desc or ttr > 0:
            if ttr > 0:
                total_revenue += ttr
                
                matched = df_master[
                    (df_master['ÜRÜN ADI_clean'] == row_sku) | 
                    (df_master['ASIN_clean'] == row_sku)
                ]
                
                birim_maliyet = 0.0
                gercek_ad = row_sku
                
                if not matched.empty:
                    birim_maliyet = matched.iloc[0]['KDV_li_Maliyet_num']
                    gercek_ad = matched.iloc[0]['ÜRÜN ADI_clean']
                    total_product_cost += birim_maliyet
                else:
                    partial = df_master[df_master['ÜRÜN ADI_clean'].str.contains(row_sku, case=False, na=False)]
                    if not partial.empty:
                        birim_maliyet = partial.iloc[0]['KDV_li_Maliyet_num']
                        gercek_ad = partial.iloc[0]['ÜRÜN ADI_clean']
                        total_product_cost += birim_maliyet
                
                valid_sales_records.append({
                    'Amazon_Rapor_Sku': row_sku,
                    'Gercek_Urun_Adi': gercek_ad,
                    'Gelen_Para_TL': ttr,
                    'Urun_Maliyeti_TL': birim_maliyet,
                    'Net_Kazanc_TL': ttr - birim_maliyet
                })
        else:
            if ttr < 0:
                total_amazon_fees += abs(ttr)

    net_profit = total_revenue - total_amazon_fees - total_product_cost
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # 🗄️ CANLI STOK ENTEGRASYONU (.txt)
    df_master['Guncel_Stok_num'] = 0
    if live_stock_file is not None:
        try:
            stok_lines = live_stock_file.getvalue().decode("utf-8").splitlines()
            stok_dict = {}
            header_cols = []
            for line in stok_lines:
                if not line.strip(): continue
                parts = line.split('\t')
                if not header_cols:
                    header_cols = [p.strip().lower() for p in parts]
                    continue
                if len(parts) == len(header_cols):
                    row_dict = dict(zip(header_cols, parts))
                    asin_key = row_dict.get('asin', '').strip()
                    fnsku_key = row_dict.get('fnsku', '').strip()
                    
                    sellable = pd.to_numeric(row_dict.get('afn-fulfillable-quantity', 0), errors='coerce')
                    unsellable = pd.to_numeric(row_dict.get('afn-unsellable-quantity', 0), errors='coerce')
                    reserved = pd.to_numeric(row_dict.get('afn-reserved-quantity', 0), errors='coerce')
                    
                    total_stk = 0
                    if not pd.isna(sellable): total_stk += int(sellable)
                    if not pd.isna(unsellable): total_stk += int(unsellable)
                    if not pd.isna(reserved): total_stk += int(reserved)
                    
                    if asin_key: stok_dict[asin_key] = total_stk
                    if fnsku_key: stok_dict[fnsku_key] = total_stk
            
            for idx, row in df_master.iterrows():
                m_asin = str(row['ASIN_clean']).strip()
                m_name = str(row['ÜRÜN ADI_clean']).strip()
                stk_val = 0
                if m_asin in stok_dict: stk_val = stok_dict[m_asin]
                elif m_name in stok_dict: stk_val = stok_dict[m_name]
                df_master.at[idx, 'Guncel_Stok_num'] = stk_val
            st.sidebar.success("✅ Canlı stok senkronize edildi!")
        except Exception as e:
            st.sidebar.error(f"Stok raporu hatası kanka: {e}")

    # 📥 TEK TIKLA FİNANSAL ÖZET OLUŞTURMA METNİ
    su_an = datetime.now().strftime("%Y-%m-%d_%H-%M")
    rapor_metni = f"""==================================================
🎯 AMAZON CEO FINANSAL PERFORMANS RAPORU
==================================================
Rapor Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💰 ANA MALI GÖSTERGELER (TL)
--------------------------------------------------
💵 Toplam Net Ciro         : {total_revenue:,.2f} TL
💸 Amazon Genel Kesintileri : {total_amazon_fees:,.2f} TL
📦 Toplam Ürün Maliyetin   : {total_product_cost:,.2f} TL
🔥 NET TEMİZ KÂRIN         : {net_profit:,.2f} TL
📈 Kâr Marjı               : %{profit_margin:.1f}

==================================================
Satışlarınız daim, dükkanınız bereketli olsun! 🚀
=================================================="""

    # Sidebar İndirme Butonu
    st.sidebar.markdown("---")
    st.sidebar.subheader("📑 Özet Rapor Çıktısı")
    st.sidebar.download_button(
        label="📥 Finansal Özeti İndir (.txt)",
        data=rapor_metni,
        file_name=f"Amazon_Finans_Ozet_{su_an}.txt",
        mime="text/plain"
    )

    # 🚀 KPI METRIKLERI
    st.subheader("📊 Anlık Finansal Durum Raporu")
    kp1, kp2, kp3, kp4 = st.columns(4)
    with kp1:
        st.metric("💵 Toplam Net Ciro", f"{total_revenue:,.2f} TL")
    with kp2:
        st.metric("💸 Amazon Genel Kesintileri", f"{total_amazon_fees:,.2f} TL")
    with kp3:
        st.metric("📦 Toplam Ürün Maliyetin", f"{total_product_cost:,.2f} TL")
    with kp4:
        st.metric("🔥 NET TEMİZ KÂRIN", f"{net_profit:,.2f} TL", delta=f"%{profit_margin:.1f} Kâr Marjı")

    st.markdown("---")

    # 📊 GRAFİKLER
    col_grafik1, col_grafik2 = st.columns(2)
    with col_grafik1:
        st.subheader("📈 Gelir vs Gider Dengesi")
        finans_ozet = pd.DataFrame({
            'Kalem': ['Net Ciro', 'Amazon Kesintisi', 'Ürün Maliyeti', 'Net Kâr'],
            'Tutar (TL)': [total_revenue, total_amazon_fees, total_product_cost, max(0, net_profit)]
        })
        fig1 = px.bar(finans_ozet, x='Kalem', y='Tutar (TL)', color='Kalem', text_auto='.2s',
                      color_discrete_sequence=['#2ecc71', '#e74c3c', '#e67e22', '#3498db'])
        st.plotly_chart(fig1, use_container_width=True)

    with col_grafik2:
        st.subheader("🍩 Gider Yapısı ve Kârlılık Dağılımı")
        fig2 = px.pie(finans_ozet[finans_ozet['Kalem'] != 'Net Ciro'], values='Tutar (TL)', names='Kalem',
                      color_discrete_sequence=['#e74c3c', '#e67e22', '#3498db'], hole=0.4)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # 📋 DETAYLI TABLOLAR
    df_valid_actions = pd.DataFrame(valid_sales_records)
    st.subheader("📦 Ürün Bazlı Finansal Dağılım ve Envanter Analizi")
    tab1, tab2 = st.tabs(["📊 Satış Performans Tablosu", "⚠️ Hiç Satmayan Ölü Stok Analizi"])
    
    with tab1:
        if not df_valid_actions.empty:
            df_disp = df_valid_actions.rename(columns={
                'Amazon_Rapor_Sku': 'Rapordaki SKU / Kod',
                'Gercek_Urun_Adi': 'Eşleşen Gerçek Ürün Adı',
                'Gelen_Para_TL': 'Amazon Gelen Tutar (TL)',
                'Urun_Maliyeti_TL': 'Birim Ürün Maliyeti (TL)',
                'Net_Kazanc_TL': 'Bu Satıştan Kalan Net Kâr (TL)'
            })
            st.dataframe(df_disp, use_container_width=True)
        else:
            st.info("💡 Bu rapor döneminde eşleşen bir satış kaydı bulunamadı kanka.")
            
    with tab2:
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
            if live_stock_file is None:
                st.info("💡 Ölü stok analizi için 3️⃣ numaralı canlı stoku yükle kanka.")
            else:
                st.success("🔥 Sıfır ölü stok! Depodaki her malın çatır çatır satıyor kanka!")

except Exception as main_e:
    st.error(f"🚨 Genel bir uyuşmazlık oluştu kanka: {main_e}")
