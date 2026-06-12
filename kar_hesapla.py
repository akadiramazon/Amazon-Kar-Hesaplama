import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 🌟 SADELİK VE NETLİK AYARI
st.set_page_config(page_title="Amazon CEO Kâr Dashboard", layout="wide")

st.title("🎯 Amazon CEO Net Kâr ve Finansal Analiz Paneli")
st.markdown("---")

# 📊 SADECE GEREKLİ İKİ KUTU (YAN MENÜDE)
st.sidebar.header("📦 Rapor Yükleme Alanı")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgenizi Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Hesap Raporlarını Seçin (.csv)", type=["csv"], accept_multiple_files=True, key="amazon")

if maliyet_file is None or not amazon_files:
    st.info("💡 Kanka, kâr durumunu anında canlı görmek için sol taraftan Maliyet Çizelgeni ve Amazon Raporlarını yüklemen yeterli! Bekliyorum.")
    st.stop()

# Verileri okuma adımları
try:
    df_mst = pd.read_csv(maliyet_file)
    df_mst.columns = df_mst.columns.str.strip()
except Exception as e:
    st.error(f"Maliyet dosyası okunurken bir hata oluştu kanka: {e}")
    st.stop()

amazon_df_list = []
for f in amazon_files:
    try:
        temp_df = pd.read_csv(f)
        temp_df.columns = temp_df.columns.str.strip()
        amazon_df_list.append(temp_df)
    except Exception as e:
        pass

if not amazon_df_list:
    st.warning("Yüklenen Amazon raporları tam okunamadı kanka.")
    st.stop()

combined_amazon = pd.concat(amazon_df_list, ignore_index=True)

# 🧮 SÜTUN İSİMLERİNİ SABİTLEME VE TEMİZLEME MOTORU (DÖNGÜ ÖNCESİ)
sku_col = next((c for c in ['Stok Kodu (SKU)', 'BARKOD_SKU', 'SKU', 'Stok Kodu'] if c in df_mst.columns), df_mst.columns[0])
asin_col = next((c for c in ['ASIN', 'ASIN Kodu'] if c in df_mst.columns), None)
cost_col = next((c for c in ['KDV li Maaliyet', 'KDV DAHİL MALİYET', 'TOPLAM MALİYET', 'KDV li Maliyet'] if c in df_mst.columns), None)

if not cost_col and len(df_mst.columns) > 2:
    cost_col = df_mst.columns[2]

# Amazon Raporu sütunlarını döngüye girmeden ÖNCE tam olarak keşfedelim (Hata önleyici)
amz_cols = combined_amazon.columns.tolist()
amount_col_name = next((c for c in ['toplam', 'amount', 'Tutar', 'amount_description', 'Total', 'total'] if c in amz_cols), None)
type_col_name = next((c for c in ['Tür', 'type', 'event_type', 'Transaction Type'] if c in amz_cols), None)
sku_col_amz = next((c for c in ['Sku', 'seller-sku', 'Stok Kodu', 'sku'] if c in amz_cols), None)
desc_col_amz = next((c for c in ['Açıklama', 'description', 'Ürün Detayları', 'product_details'] if c in amz_cols), None)

total_revenue = 0.0
total_amazon_fees = 0.0
total_product_cost = 0.0

# Sipariş satırları üzerinde dönüp karşılaştırmalı kârı hesaplayalım
for index, row in combined_amazon.iterrows():
    # Tutar değerini güvenli şekilde alalım
    amount_val = row.get(amount_col_name, 0) if amount_col_name else 0.0
    try:
        # Sayıların içindeki nokta/virgül ve TL simgesi gibi karmaşaları temizle
        amount_str = str(amount_val).replace('.', '').replace(',', '.')
        amount_clean = re.sub(r'[^\d.-]', '', amount_str)
        amount = float(amount_clean)
    except:
        amount = 0.0
        
    type_str = str(row.get(type_col_name, '')).lower() if type_col_name else ''
    sku_str = str(row.get(sku_col_amz, '')).strip().upper() if sku_col_amz else ''
    description_str = str(row.get(desc_col_amz, '')).strip().upper() if desc_col_amz else ''
    
    # 🕵️‍♂️ ASIN Cımbızlama Motoru (Açıklamanın içinden ASIN'i çeker)
    found_asin = None
    asin_match = re.search(r'(B0[A-Z0-9]{8}|JBM[A-Z0-9]*)', description_str)
    if asin_match:
        found_asin = asin_match.group(1)

    if amount != 0:
        # ESNEK FİLTRE: Eğer pozitif bir para hareketiyse cirodur ve maliyet tetikler
        if amount > 0 and (any(x in type_str for x in ['order', 'satış', 'sipariş', 'deal', 'payment']) or type_str == ''):
            total_revenue += amount
            
            # 🎯 GERÇEK KARŞILAŞTIRMA ALANI: Amazon verisini senin 4300'lük maliyet listene bağlıyoruz
            maliyet_row = pd.DataFrame()
            if df_mst is not None:
                # 1. Öncelik: Açıklamadan bulduğun ASIN'i maliyet çizelgesindeki ASIN ile tokuştur
                if found_asin and asin_col and asin_col in df_mst.columns:
                    maliyet_row = df_mst[df_mst[asin_col].astype(str).str.strip().str.upper() == found_asin]
                
                # 2. Öncelik: ASIN uyuşmadıysa SKU kodlarını tokuştur (Toyota Supra çözümü)
                if maliyet_row.empty and sku_str and sku_col in df_mst.columns:
                    maliyet_row = df_mst[df_mst[sku_col].astype(str).str.strip().str.upper() == sku_str]
                
                # Karşılaştırma başarılıysa KDV'li maliyeti çek ve kümülatif topla kanka
                if not maliyet_row.empty and cost_col:
                    val_cost = str(maliyet_row.iloc[0].get(cost_col, 0)).replace('.', '').replace(',', '.')
                    val_cost = re.sub(r'[^\d.]', '', val_cost)
                    try:
                        total_product_cost += float(val_cost)
                    except:
                        pass
        else:
            # Negatif tutarlar Amazon'un kestiği komisyon, kargo, reklam vb. giderleridir
            total_amazon_fees += abs(amount)

# Nihai Kâr Denklemi
net_profit = total_revenue - total_amazon_fees - total_product_cost
profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

# 📈 DEV GÖRSEL ÖZET KUTULARI
st.subheader("💰 Bu Dönemin Finansal Net Raporu")
kp1, kp2, kp3, kp4 = st.columns(4)
with kp1:
    st.metric("💵 Toplam Net Ciro", f"{total_revenue:,.2f} TL")
with kp2:
    st.metric("💸 Amazon Genel Kesintileri", f"{total_amazon_fees:,.2f} TL")
with kp3:
    st.metric("📦 Karşılaştırılan Toplam Maliyet", f"{total_product_cost:,.2f} TL")
with kp4:
    st.metric("🔥 NET TEMİZ KÂRIN", f"{net_profit:,.2f} TL", delta=f"%{profit_margin:.1f} Kâr Marjı")

st.markdown("---")

# 📊 YENİDEN CANLANAN GRAFİK ŞOVU
col_grafik1, col_grafik2 = st.columns(2)

with col_grafik1:
    st.subheader("📈 Gelir vs Gider Dengesi")
    finans_ozet = pd.DataFrame({
        'Kalem': ['Net Ciro', 'Amazon Kesintisi', 'Ürün Maliyeti', 'Net Kâr'],
        'Tutar (TL)': [total_revenue, total_amazon_fees, total_product_cost, max(0, net_profit)]
    })
    fig1 = px.bar(finans_ozet, x='Kalem', y='Tutar (TL)', color='Kalem', text_auto='.2s',
                  color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig1, use_container_width=True)

with col_grafik2:
    st.subheader("🎯 Kârlılık Dağılım Röntgeni")
    fig2 = px.pie(values=[total_amazon_fees, total_product_cost, max(0, net_profit)], 
                  names=['Amazon Giderleri', 'Ürün Ana Maliyetleri', 'Net Kâr Semeresi'],
                  color_discrete_sequence=['#ff6b6b', '#4dadf7', '#2ecc71'])
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# 🔍 TABLO İÇİ ARAMA KUTUSU
st.subheader("📋 Detaylı Ürün Takip Tablosu")
arama_metni = st.text_input("💡 Tablo içinde arama yapmak için buraya Stok Kodu (SKU) veya kelime yaz kanka:", "")

if arama_metni:
    filtreli_df = df_mst[df_mst.astype(str).apply(lambda x: x.str.contains(arama_metni, case=False)).any(axis=1)]
    st.dataframe(filtreli_df, use_container_width=True)
else:
    st.dataframe(df_mst, use_container_width=True)
