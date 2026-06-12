import streamlit as st
import pandas as pd
import re
import plotly.express as px
from datetime import datetime

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Finansal Analiz Paneli")
st.markdown("---\")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

# TEMEL DOSYALAR YOKSA KILAVUZ GÖSTERİR VE DURUR
if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

# DOSYALAR GELDİYSE ANA MOTOR ÇALIŞIR
try:
    # 1. Maliyet Dosyasını Oku
    try:
        df_master = pd.read_csv(maliyet_file)
        df_master.columns = df_master.columns.str.strip()
    except Exception as e:
        st.error(f"Maliyet dosyası okunurken hata oluştu kanka: {e}")
        st.stop()
        
    # Temizlik ve Standartlaştırma Fonksiyonları
    def temizle_text(val):
        if pd.isna(val): return ""
        text = str(val).strip().upper()
        text = re.sub(r'\s+', ' ', text)
        return text

    def temizle_sayi(val):
        if pd.isna(val): return 0.0
        val_str = str(val).strip()
        val_str = val_str.replace('.', '').replace(',', '.')
        try:
            return float(val_str)
        except:
            try:
                return float(val)
            except:
                return 0.0

    # Master tablonun sütunlarını temizle
    if 'ASIN' in df_master.columns:
        df_master['ASIN_clean'] = df_master['ASIN'].apply(temizle_text)
    elif 'ASIN Kodu' in df_master.columns:
        df_master['ASIN_clean'] = df_master['ASIN Kodu'].apply(temizle_text)
    else:
        st.error("Maliyet çizelgesinde ASIN sütunu bulunamadı!")
        st.stop()

    if 'ÜRÜN ADI' in df_master.columns:
        df_master['ÜRÜN ADI_clean'] = df_master['ÜRÜN ADI'].apply(temizle_text)
    else:
        # Alternatif ürün adı sütunu arayışı
        urun_col = [c for c in df_master.columns if 'ÜRÜN' in c.upper() or 'AD' in c.upper()]
        if urun_col:
            df_master['ÜRÜN ADI_clean'] = df_master[urun_col[0]].apply(temizle_text)
        else:
            df_master['ÜRÜN ADI_clean'] = df_master.index.astype(str)

    # Maliyet sütununu temizle
    maliyet_col = [c for c in df_master.columns if 'KDV' in c.upper() and 'MAAL' in c.upper()]
    if not maliyet_col:
        maliyet_col = [c for c in df_master.columns if 'MALİYET' in c.upper() or 'MAALİYET' in c.upper()]
    
    if maliyet_col:
        df_master['KDV_li_Maliyet_num'] = df_master[maliyet_col[0]].apply(temizle_sayi)
    else:
        st.error("Maliyet çizelgesinde 'KDV li Maaliyet' veya benzeri bir maliyet sütunu bulunamadı!")
        st.stop()

    # 2. Amazon Raporlarını Birleştir ve Oku
    amazon_list = []
    for f in amazon_files:
        try:
            tdf = pd.read_csv(f)
            amazon_list.append(tdf)
        except Exception as e:
            st.warning(f"{f.name} dosyası okunurken atlandı: {e}")
            
    if not amazon_list:
        st.error("Yüklenen Amazon raporlarından hiçbir veri okunamadı!")
        st.stop()
        
    df_amazon = pd.concat(amazon_list, ignore_index=True)
    df_amazon.columns = df_amazon.columns.str.strip()

    # Amazon Raporu Filtreleme ve Hesaplama Süzgeci
    # Sipariş Ödemesi ve Oluşturuldu/Ertelendi durumlarını kapsar
    valid_types = ['Sipariş Ödemesi', 'Sipariþ Ödemesi', 'Order Payment']
    valid_status = ['Oluşturuldu', 'Oluþturuldu', 'Ertelendi', 'Deferred', 'Complete', 'Kapandı']

    type_col = [c for c in df_amazon.columns if 'TİP' in c.upper() or 'TYPE' in c.upper() or 'İŞLEM TİPİ' in c.upper()]
    status_col = [c for c in df_amazon.columns if 'DURUM' in c.upper() or 'STATUS' in c.upper()]
    detail_col = [c for c in df_amazon.columns if 'DETAY' in c.upper() or 'DETAIL' in c.upper() or 'ÜRÜN' in c.upper()]
    price_col = [c for c in df_amazon.columns if 'FİYAT' in c.upper() or 'PRICE' in c.upper() or 'TOPLAM ÜRÜN' in c.upper()]
    fee_col = [c for c in df_amazon.columns if 'ÜCRET' in c.upper() or 'FEE' in c.upper() or 'AMAZON ÜCRET' in c.upper()]

    if not type_col or not status_col or not detail_col or not price_col or not fee_col:
        st.error("Amazon finans raporunun sütun yapıları standartlara uymuyor kanka! Lütfen orijinal raporu yükleyin.")
        st.stop()

    df_amazon['Type_Clean'] = df_amazon[type_col[0]].astype(str).str.strip()
    df_amazon['Status_Clean'] = df_amazon[status_col[0]].astype(str).str.strip()

    df_valid_actions = df_amazon[
        df_amazon['Type_Clean'].isin(valid_types) & 
        df_amazon['Status_Clean'].isin(valid_status)
    ].copy()

    if df_valid_actions.empty:
        st.warning("⚠️ Seçilen filtrelere uygun (Sipariş Ödemesi olan) hiçbir işlem bulunamadı. Raporları kontrol et kanka.")
        st.stop()

    # Finansal Değerleri Temizle
    df_valid_actions['Revenue_Clean'] = df_valid_actions[price_col[0]].apply(temizle_sayi)
    df_valid_actions['Fees_Clean'] = df_valid_actions[fee_col[0]].apply(temizle_sayi)
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions[detail_col[0]].apply(temizle_text)

    # 🎯 EŞLEŞTİRME VE MALİYET BULMA MOTORU
    maliyetler_listesi = []
    
    for idx, row in df_valid_actions.iterrows():
        amazon_urun_adi = row['Gercek_Urun_Adi']
        bulunan_maliyet = 0.0
        
        # 1. Aşama: Tam Eşleşme veya İçerme Kontrolü
        match = df_master[df_master['ÜRÜN ADI_clean'].apply(lambda x: x in amazon_urun_adi or amazon_urun_adi in x if x else False)]
        
        if not match.empty:
            bulunan_maliyet = match.iloc[0]['KDV_li_Maliyet_num']
        else:
            # 2. Aşama: Kelime bazlı akıllı arama
            kelimeler = [k for k in amazon_urun_adi.split() if len(k) > 2]
            best_score = 0
            best_maliyet = 0.0
            for midx, mrow in df_master.iterrows():
                m_name = mrow['ÜRÜN ADI_clean']
                score = sum(1 for k in kelimeler if k in m_name)
                if score > best_score:
                    best_score = score
                    best_maliyet = mrow['KDV_li_Maliyet_num']
            if best_score >= 2:
                bulunan_maliyet = best_maliyet
                
        maliyetler_listesi.append(bulunan_maliyet)

    df_valid_actions['Urun_Maliyeti_Tekil'] = maliyetler_listesi

    # TOPLAM FINANSAL HESAPLAMALAR
    total_revenue = df_valid_actions['Revenue_Clean'].sum()
    total_amazon_fees = abs(df_valid_actions['Fees_Clean'].sum())
    total_product_cost = df_valid_actions['Urun_Maliyeti_Tekil'].sum()
    
    # Net Cirodan Amazon Kesintileri ve Ürün Maliyeti Çıkınca Kalan Net Temiz Kâr
    net_profit = total_revenue - total_amazon_fees - total_product_cost
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0.0

    # 💰 SKORBORD KUTULARI (DÜKKANIN NABZI)
    st.subheader("📊 Anlık Finansal Durum Raporu")
    kp1, kp2, kp3, kp4 = st.columns(4)
    with kp1:
        st.metric("💵 Toplam Brüt Ciro", f"{total_revenue:,.2f} TL")
    with kp2:
        st.metric("💸 Amazon Genel Kesintileri", f"{total_amazon_fees:,.2f} TL")
    with kp3:
        st.metric("📦 Toplam Ürün Maliyetin", f"{total_product_cost:,.2f} TL")
    with kp4:
        st.metric("🔥 NET TEMİZ KÂRIN", f"{net_profit:,.2f} TL", delta=f"%{profit_margin:.1f} Kâr Marjı")

    st.markdown("---\")

    # 📊 GRAFİK VE DETAYLI ANALİZ DENGESİ
    col_grafik1, col_grafik2 = st.columns(2)

    with col_grafik1:
        st.subheader("📈 Gelir vs Gider Dengesi")
        finans_ozet = pd.DataFrame({
            'Kalem': ['Toplam Ciro', 'Amazon Kesintisi', 'Ürün Maliyeti', 'Net Kâr'],
            'Tutar (TL)': [total_revenue, total_amazon_fees, total_product_cost, max(0, net_profit)]
        })
        fig1 = px.bar(finans_ozet, x='Kalem', y='Tutar (TL)', color='Kalem', text_auto='.2s',
                      color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig1, use_container_width=True)

    with col_grafik2:
        st.subheader("🍕 Finansal Pasta Dağılımı")
        gider_pastasi = pd.DataFrame({
            'Gider Kalemi': ['Amazon Kesintileri', 'Ürün Maliyetleri', 'Net Kâr'],
            'Tutar (TL)': [total_amazon_fees, total_product_cost, max(0, net_profit)]
        })
        fig2 = px.pie(gider_pastasi, values='Tutar (TL)', names='Gider Kalemi', hole=0.4,
                      color_discrete_sequence=px.colors.qualitative.Safe)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---\")

    # 🛒 SATILAN ÜRÜNLERİN DETAYLI LİSTESİ VE KALEM KALEM KÂRLILIK
    st.subheader("🛍️ Dönem İçinde Satılan Ürünlerin Kârlılık Analiz Tablosu")
    
    # Gruplayarak hangi üründen kaç adet satıldığını ve ne kadar ciro/maliyet getirdiğini bulalım
    df_summary = df_valid_actions.groupby('Gercek_Urun_Adi').agg(
        Satilan_Adet=('Revenue_Clean', 'count'),
        Toplam_Ciro=('Revenue_Clean', 'sum'),
        Amazon_Kesintisi=('Fees_Clean', lambda x: abs(x.sum())),
        Urun_Maliyeti=('Urun_Maliyeti_Tekil', 'sum')
    ).reset_index()

    df_summary['Net_Kar'] = df_summary['Toplam_Ciro'] - df_summary['Amazon_Kesintisi'] - df_summary['Urun_Maliyeti']
    df_summary['Urun_Kar_Marji_%'] = (df_summary['Net_Kar'] / df_summary['Toplam_Ciro'] * 100).round(1)

    # İsimleri güzelleştirelim
    df_summary = df_summary.rename(columns={
        'Gercek_Urun_Adi': 'Amazon Raporundaki Ürün Adı',
        'Satilan_Adet': 'Satış Adedi (Adet)',
        'Toplam_Ciro': 'Toplam Ciro (TL)',
        'Amazon_Kesintisi': 'Amazon Kesintisi (TL)',
        'Urun_Maliyeti': 'Toplam Ürün Maliyeti (TL)',
        'Net_Kar': 'Net Kâr (TL)',
        'Urun_Kar_Marji_%': 'Kâr Marjı (%)'
    }).sort_values(by='Net Kâr (TL)', ascending=False)

    st.dataframe(df_summary, use_container_width=True, hide_index=True)

except Exception as main_err:
    st.error(f"Sistem çalışırken genel bir hata meydana geldi kanka: {main_err}")
