import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Amazon Finansal Analiz", layout="wide")

st.title("🎯 Amazon Finansal Analiz ve Net Kâr Paneli")
st.markdown("---")

# 📊 YAN MENÜ
st.sidebar.header("📦 Rapor Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgenizi Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Tarih Raporlarını Seçin (.csv)", type=["csv"], accept_multiple_files=True, key="amazon")

if maliyet_file is None or not amazon_files:
    st.info("💡 Kanka, kâr durumunu anında canlı görmek için sol taraftan Maliyet Çizelgeni ve Amazon Raporlarını yüklemen yeterli!")
    st.stop()

# 1. Maliyet Excelini Oku
try:
    df_mst = pd.read_csv(maliyet_file)
    df_mst.columns = df_mst.columns.str.strip()
except Exception as e:
    st.error(f"Maliyet dosyası okunurken hata oluştu: {e}")
    st.stop()

# 2. Amazon Tarih Raporlarını Oku ve Birleştir
amazon_df_list = []
for f in amazon_files:
    try:
        temp_df = pd.read_csv(f)
        temp_df.columns = temp_df.columns.str.strip()
        amazon_df_list.append(temp_df)
    except Exception as e:
        pass

if not amazon_df_list:
    st.warning("Yüklenen Amazon raporları okunamadı kanka.")
    st.stop()

combined_amazon = pd.concat(amazon_df_list, ignore_index=True)

# 🧮 SENİN GERÇEK RAPORUNA GÖRE AYARLANMIŞ MATEMATİK MOTORU
total_revenue = 0.0
total_amazon_fees = 0.0
total_product_cost = 0.0

# Sipariş satırları üzerinde dönüp kârı hesaplayalım
for index, row in combined_amazon.iterrows():
    # 🎯 SENİN RAPORUNDAKİ GERÇEK SÜTUN: 'toplam'
    amount_val = row.get('toplam', row.get('amount', row.get('Tutar', 0)))
    try:
        # Para formatındaki nokta ve virgülleri temizleyelim
        amount_str = str(amount_val).replace('.', '').replace(',', '.')
        amount_clean = re.sub(r'[^\d.-]', '', amount_str)
        amount = float(amount_clean)
    except:
        amount = 0.0
        
    # 🎯 SENİN RAPORUNDAKİ GERÇEK SÜTUNLAR: 'Tür', 'Sku', 'Açıklama'
    type_str = str(row.get('Tür', row.get('type', ''))).lower()
    sku_str = str(row.get('Sku', row.get('seller-sku', ''))).strip().upper()
    description_str = str(row.get('Açıklama', row.get('description', ''))).strip().upper()
    
    # Sipariş ve Satışları yakalayan filtre
    if 'order' in type_str or 'satış' in type_str or 'sipariş' in type_str:
        if amount > 0:
            total_revenue += amount
            
            # Ürünün bizim excel listesindeki maliyetini bul (İlk sütun SKU)
            if df_mst is not None:
                sku_col_mst = df_mst.columns[0]
                maliyet_row = df_mst[df_mst[sku_col_mst].astype(str).str.strip().str.upper() == sku_str]
                
                if not maliyet_row.empty:
                    # 3. sütun maliyet sütunudur
                    cost_col_mst = df_mst.columns[2] if len(df_mst.columns) > 2 else df_mst.columns[-1]
                    val_cost = str(maliyet_row.iloc[0].get(cost_col_mst, 0)).replace('.', '').replace(',', '.')
                    val_cost = re.sub(r'[^\d.]', '', val_cost)
                    try:
                        total_product_cost += float(val_cost)
                    except:
                        pass
        else:
            total_amazon_fees += abs(amount)
    else:
        if amount < 0:
            total_amazon_fees += abs(amount)

# Net Kâr Hesaplama
net_profit = total_revenue - total_amazon_fees - total_product_cost
profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

# 📈 NET KÂR VE FİNANS ÖZET KUTULARI
st.subheader("💰 Bu Dönemin Finansal Net Raporu")
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

# 📊 GELİR GİDER GRAFİKLERİ
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
st.subheader("📋 Yüklediğiniz Gerçek Rapor İzleme Tablosu")
st.dataframe(combined_amazon, use_container_width=True)
