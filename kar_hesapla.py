import streamlit as st
import pandas as pd

st.set_page_config(page_title="Amazon Gerçek Finansal Analiz", layout="wide")

st.title("📊 Amazon Finansal Analiz ve Kârlılık Paneli")
st.markdown("Amazon raporundaki **açıklama** metni ile Maliyet listesindeki **Ürün Adı** eşleştirilerek hesaplanır.")

st.sidebar.header("📁 Rapor Yükleme Alanı")

# 1. Maliyet Çizelgesi Yükleme (Kullanıcının attığı maliyet.csv formatı)
maliyet_dosya = st.sidebar.file_uploader("1️⃣ Güncel Maliyet Çizelgesini Seçin (.csv)", type=["csv"])

# 2. Amazon Raporu Yükleme (Kullanıcının attığı işlemler raporu)
amazon_dosya = st.sidebar.file_uploader("2️⃣ Amazon İşlemler Raporunu Seçin (.csv)", type=["csv"])

if maliyet_dosya and amazon_dosya:
    try:
        # --- MALİYET ÇİZELGESİ OKUMA ---
        maliyet_df = pd.read_csv(maliyet_dosya, sep=None, engine='python', on_bad_lines='skip')
        maliyet_df.columns = maliyet_df.columns.str.strip()
        
        # Gönderdiğin maliyet.csv dosyasındaki gerçek sütunların kontrolü
        required_maliyet = ['Ürün Adı', 'Toplam Maliyet']
        if not all(col in maliyet_df.columns for col in required_maliyet):
            st.error(f"⚠️ Maliyet çizelgesinde gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(maliyet_df.columns)}")
            st.info("Lütfen dosyada 'Ürün Adı' ve 'Toplam Maliyet' sütunlarının olduğundan emin olun.")
            st.stop()
            
        # Sayısal formata güvenli dönüştürme (virgül/nokta karmaşasını çözer)
        maliyet_df['Toplam Maliyet'] = pd.to_numeric(maliyet_df['Toplam Maliyet'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # Eşleştirme için ürün listesi oluşturma
        maliyet_listesi = []
        for _, row in maliyet_df.iterrows():
            urun_ismi = str(row['Ürün Adı']).strip()
            sku_kodu = str(row['Sku']).strip() if 'Sku' in maliyet_df.columns else "Yok"
            if urun_ismi and urun_ismi != 'nan':
                maliyet_listesi.append({
                    'sku': sku_kodu,
                    'urun_adi': urun_ismi,
                    'toplam_maliyet': float(row['Toplam Maliyet'])
                })

        # --- AMAZON RAPORU OKUMA ---
        amazon_df = pd.read_csv(amazon_dosya, sep=None, engine='python', on_bad_lines='skip')
        amazon_df.columns = amazon_df.columns.str.strip()

        # Amazon işlemler raporundaki gerçek sütunların kontrolü
        required_amazon = ['açıklama', 'tutar', 'miktar', 'tip']
        if not all(col in amazon_df.columns for col in required_amazon):
            st.error(f"⚠️ Amazon raporunda gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(amazon_df.columns)}")
            st.stop()

        # Amazon verilerini temizleme
        amazon_df['tutar'] = pd.to_numeric(amazon_df['tutar'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        amazon_df['miktar'] = pd.to_numeric(amazon_df['miktar'], errors='coerce').fillna(0)
        amazon_df['açıklama'] = amazon_df['açıklama'].astype(str).str.strip()

        analiz_sonuclari = []
        toplam_ciro = 0
        toplam_urun_maliyeti_genel = 0

        # Her bir maliyet listesindeki ürün için Amazon açıklama sütununda arama yapıyoruz
        for urun in maliyet_listesi:
            m_isim = urun['urun_adi']
            m_fiyat = urun['toplam_maliyet']
            m_sku = urun['sku']
            
            # Amazon raporunda bu ürün adının GEÇTİĞİ satırları bul (Büyük/küçük harf duyarsız)
            eslesen_satirlar = amazon_df[amazon_df['açıklama'].str.contains(m_isim, case=False, na=False)]
            
            if len(eslesen_satirlar) > 0:
                # Satış adedi (tip sütununda 'sipariş' veya 'order' geçen ve miktarı pozitif olanlar)
                satis_satirlari = eslesen_satirlar[(eslesen_satirlar['tip'].str.lower().str.contains('sipariş|order|satis|sales', na=False)) & (eslesen_satirlar['miktar'] > 0)]
                satilan_adet = satis_satirlari['miktar'].sum()
                
                # İade adedi (miktarı negatif olan veya tipi iade/refund olanlar)
                iade_satirlari = eslesen_satirlar[(eslesen_satirlar['miktar'] < 0) | (eslesen_satirlar['tip'].str.lower().str.contains('iade|refund|geri ödeme', na=False))]
                iade_adet = iade_satirlari['miktar'].abs().sum()
                
                # Net ciro (Tutar sütunundaki tüm işlemlerin toplamı - komisyonlar düşülmüş net Amazon hakkedişi)
                urun_ciro = eslesen_satirlar['tutar'].sum()
                
                # Toplam ürün maliyeti (Satılan adet * senin listendeki 'Toplam Maliyet')
                toplam_urun_maliyeti = satilan_adet * m_fiyat
                
                # Kâr ve ROI
                net_kar = urun_ciro - toplam_urun_maliyeti
                roi = (net_kar / toplam_urun_maliyeti * 100) if toplam_urun_maliyeti > 0 else 0
                
                if urun_ciro != 0 or satilan_adet > 0:
                    analiz_sonuclari.append({
                        "Sku": m_sku,
                        "Ürün Adı": m_isim,
                        "Satılan Adet": int(satilan_adet),
                        "İade Adet": int(iade_adet),
                        "Ürün Maliyeti ($)": round(m_fiyat, 2),
                        "Toplam Ürün Maliyeti ($)": round(toplam_urun_maliyeti, 2),
                        "Amazon Net Hak Ediş ($)": round(urun_ciro, 2),
                        "Net Kâr ($)": round(net_kar, 2),
                        "ROI (%)": f"%{round(roi, 2)}"
                    })
                    
                    toplam_ciro += urun_ciro
                    toplam_maliyet_genel += toplam_urun_maliyeti

        # Sonuç tablosu oluşturma
        if analiz_sonuclari:
            sonuc_df = pd.DataFrame(analiz_sonuclari)
        else:
            sonuc_df = pd.DataFrame(columns=["Sku", "Ürün Adı", "Satılan Adet", "İade Adet", "Ürün Maliyeti ($)", "Toplam Ürün Maliyeti ($)", "Amazon Net Hak Ediş ($)", "Net Kâr ($)", "ROI (%)"])

        # --- SKOR TABELASI (KPI METRICS) ---
        st1, st2, st3, st4 = st.columns(4)
        st1.metric("💰 Toplam Amazon Hak Edişi", f"${round(toplam_ciro, 2)}")
        st2.metric("📉 Toplam Ürün Maliyeti", f"${round(toplam_maliyet_genel, 2)}")
        
        genel_net_kar = toplam_ciro - toplam_maliyet_genel
        st3.metric("📈 Net Kâr / Zarar", f"${round(genel_net_kar, 2)}", delta=f"{round(genel_net_kar, 2)} $", delta_color="normal")
        
        genel_roi = (genel_net_kar / toplam_maliyet_genel * 100) if toplam_maliyet_genel > 0 else 0
        st4.metric("📊 Genel ROI", f"%{round(genel_roi, 2)}")

        st.markdown("---")
        
        # --- DETAYLI ANALİZ TABLOSU ---
        st.subheader("📋 Ürün Adı Eşleştirmeli Kârlılık Raporu")
        st.dataframe(sonuc_df, use_container_width=True)

        # İndirme butonu
        csv_data = sonuc_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Analiz Raporunu CSV Olarak İndir",
            data=csv_data,
            file_name='amazon_net_karlilik_raporu.csv',
            mime='text/csv',
        )

    except Exception as e:
        st.error(f"⚠️ Raporlar işlenirken bir hata oluştu: {str(e)}")
else:
    st.info("💡 Sol menüden yeni gönderdiğin **maliyet.csv** dosyasını ve **Amazon İşlemler Raporunu** yükle. Sistem isimleri içerikten süzüp eşleştirecektir.")
