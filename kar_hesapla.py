import streamlit as st
import pandas as pd
import plotly.express as px
import re

# 🌟 TEMA VE SAYFA AYARI
st.set_page_config(page_title="Amazon Finansal Analiz", layout="wide")

st.title("🎯 Amazon Finansal Analiz ve Gerçek Net Kâr Paneli")
st.markdown("---")

# 📊 YAN MENÜ (SADECE MALIYET VE AMAZON FINANS RAPORLARI)
st.sidebar.header("📦 Rapor Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgenizi Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Tarih Raporlarını Seçin (.csv)", type=["csv"], accept_multiple_files=True, key="amazon")

if maliyet_file is None or not amazon_files:
    st.info("💡 Kanka, maliyetleri karşılaştırıp kârı görmek için sol taraftan iki dosyayı da yüklemen lazım!")
    st.stop()

# 1. Maliyet Excelini Oku ve Sütunlarını Temizle
try:
    df_mst = pd.read_csv(maliyet_file)
    df_mst.columns = df_mst.columns.str.strip()
except Exception as e:
    st.error(f"Maliyet dosyası okunurken hata oluştu kanka: {e}")
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

# 🧮 Gelişmiş Dinamik Sütun Yakalama (Senin Dosyalarındaki Başlıklara Göre)
# Maliyet listendeki sütunlar:
sku_col_mst = next((c for c in ['Stok Kodu (SKU)', 'BARKOD_SKU', 'SKU', 'Stok Kodu', 'Sku'] if c in df_mst.columns), df_mst.columns[0])
asin_col_mst = next((c for c in ['ASIN', 'ASIN Kodu', 'Asin'] if c in df_mst.columns), None)
cost_col_mst = next((c for c in ['KDV li Maaliyet', 'KDV DAHİL MALİYET', 'TOPLAM MALİYET', 'KDV li Maliyet', 'KDV\'li Maliyet', 'Maliyet'] if c in df_mst.columns), None)

# Eğer maliyet sütunu bulunamazsa mecburen 3. sütunu alıyoruz
if not cost_col_mst and len(df_mst.columns) > 2:
    cost_col_mst = df_mst.columns[2]

# Matematik Sayıcıları
total_revenue = 0.0
total_amazon_fees = 0.0
total_product_cost = 0.0

# 🚀 TABLOLARI KARŞILAŞTIRAN VE MATEMATİĞİ DÖNDÜREN ANA MOTOR
for index, row in combined_amazon.iterrows():
    # Parayı 'toplam' sütunundan çek
    amount_val = row.get('toplam', row.get('amount', row.get('Tutar', 0)))
    try:
        amount_str = str(amount_val).replace('.', '').replace(',', '.')
        amount_clean = re.sub(r'[^\d.-]', '', amount_str)
        amount = float(amount_clean)
    except:
        amount = 0.0
        
    type_str = str(row.get('Tür', row.get('type', ''))).lower()
    sku_str = str(row.get('Sku', row.get('seller-sku', ''))).strip().upper()
    description_str = str(row.get('Açıklama', row.get('description', ''))).strip().upper()
    
    # Açıklamanın içinden ASIN kodunu (B0... veya JBM...) cımbızla çekelim
    found_asin = None
    asin_match = re.search(r'(B0[A-Z0-9]{8}|JBM[A-Z0-9]*)', description_str)
    if asin_match:
        found_asin = asin_match.group(1)

    if amount != 0:
        # Eğer para pozitifse ve bir satış/sipariş işlemiyse: BU CİRODUR
        if amount > 0 and (any(x in type_str for x in ['order', 'satış', 'sipariş', 'deal', 'reklam']) or type_str == ''):
            total_revenue += amount
            
            # 🎯 İŞTE BURASI KARŞILAŞTIRMA YAPTIĞIMIZ YER KANKA:
            maliyet_row = pd.DataFrame()
            if df_mst is not None:
                # 1. Yol: Eğer açıklamadan ASIN bulduysak, maliyet listesindeki ASIN sütunuyla karşılaştır
                if found_asin and asin_col_mst and asin_col_mst in df_mst.columns:
                    maliyet_row = df_mst[df_mst[asin_col_mst].astype(str).str.strip().str.upper() == found_asin]
                
                # 2. Yol: ASIN ile bulamadıysak, Amazon'daki SKU'yu bizim listedeki SKU ile karşılaştır
                if maliyet_row.empty and sku_str and sku_col_mst in df_mst.columns:
                    maliyet_row = df_mst[df_mst[sku_col_mst].astype(str).str.strip().str.upper() == sku_str]
                
                # Karşılaştırma başarılıysa, o ürünün kendi maliyetini toplam maliyete ekle
                if not maliyet_row.empty and cost_col_mst:
                    val_cost = str(maliyet_row.iloc[0].get(cost_col_mst, 0)).replace('.', '').replace(',', '.')
                    val_cost = re.sub(r'[^\d.]', '', val_cost)
                    try:
                        total_product_cost += float(val_cost)
                    except:
                        pass
        else:
            # Negatif olan her şey Amazon'un komisyon, kargo, reklam kesintisidir
            total_amazon_fees += abs(amount)

# Nihai Kâr Hesapları
net_profit = total_revenue - total_amazon_fees - total_product_cost
profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

# 📈 NET KÂR VE FINANS ÖZET KUTULARI
st.subheader("💰 Bu Dönemin Finansal Net Raporu")
kp1, kp2, kp3, kp4 = st.columns(4)
with kp1:
    st.metric("💵 Toplam Net Ciro (Satışlar)", f"{total_revenue:,.2f} TL")
with kp2:
    st.metric("💸 Amazon Genel Kesintileri", f"{total_amazon_fees:,.2f} TL")
with kp3:
    st.metric("📦 Karşılaştırılan Toplam Ürün Maliyeti", f"{total_product_cost:,.2f} TL")
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
