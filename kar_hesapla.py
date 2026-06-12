import streamlit as pd_st
import pandas as pd_pd
import re as pd_re

pd_st.set_page_config(page_title="Amazon Finansal Analiz Paneli", layout="wide")

pd_st.title("📊 Amazon Finansal Analiz ve Kârlılık Paneli")
pd_st.markdown("Maliyet ve Amazon raporlarınızı yükleyerek net kârlılığınızı anında görün.")

pd_st.sidebar.header("📁 Rapor Yükleme Alanı")

# 1. Maliyet Çizelgesi Yükleme
maliyet_dosya = pd_st.sidebar.file_uploader("1️⃣ Güncel Maliyet Çizelgesini Seçin (.xlsx)", type=["xlsx"])

# 2. Amazon Raporu Yükleme
amazon_dosya = pd_st.sidebar.file_uploader("2️⃣ Amazon Aylık Finansal Raporunu Seçin (.csv / .txt)", type=["csv", "txt"])

if maliyet_dosya and amazon_dosya:
    try:
        # --- MALİYET ÇİZELGESİ OKUMA ---
        maliyet_df = pd_pd.read_excel(maliyet_dosya)
        maliyet_df.columns = maliyet_df.columns.str.strip()
        
        required_maliyet = ['MSKU', 'Ürün Adı', 'Birim Maliyet ($)']
        if not all(col in maliyet_df.columns for col in required_maliyet):
            pd_st.error(f"Maliyet çizelgesinde şu sütunlar eksik: {set(required_maliyet) - set(maliyet_df.columns)}")
            pd_st.stop()
            
        maliyet_dict = maliyet_df.set_index('MSKU')['Birim Maliyet ($)'].to_dict()
        urun_adi_dict = maliyet_df.set_index('MSKU')['Ürün Adı'].to_dict()

        # --- AMAZON RAPORU OKUMA ---
        try:
            amazon_df = pd_pd.read_csv(amazon_dosya, sep=None, engine='python', on_bad_lines='skip')
        except Exception:
            amazon_dosya.seek(0)
            amazon_df = pd_pd.read_csv(amazon_dosya, sep='\t', on_bad_lines='skip')

        amazon_df.columns = amazon_df.columns.str.strip()
        
        # Sütun isimlerini normalize etme
        col_mapping = {
            'sku': 'sku', 'msku': 'sku', 'SKU': 'sku', 'MSKU': 'sku',
            'amount': 'amount', 'tutar': 'amount', 'Amount': 'amount', 'Tutar': 'amount',
            'quantity': 'quantity', 'adet': 'quantity', 'Quantity': 'quantity', 'Adet': 'quantity',
            'description': 'description', 'açıklama': 'description', 'Description': 'description', 'Açıklama': 'description',
            'type': 'type', 'tip': 'type', 'Type': 'type', 'Tip': 'type'
        }
        amazon_df = amazon_df.rename(columns=col_mapping)

        required_amazon = ['sku', 'amount', 'quantity', 'description', 'type']
        if not all(col in amazon_df.columns for col in required_amazon):
            pd_st.error(f"Amazon raporunda gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(amazon_df.columns)}")
            pd_st.stop()

        # --- FİNANSAL HESAPLAMALAR ---
        amazon_df['amount'] = pd_pd.to_numeric(amazon_df['amount'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        amazon_df['quantity'] = pd_pd.to_numeric(amazon_df['quantity'], errors='coerce').fillna(0)

        # Ciro ve Sipariş Adetleri (Order tipindeki işlemler)
        order_df = amazon_df[amazon_df['type'].astype(str).str.lower() == 'order']
        
        # Sipariş satırlarından sadece pozitif adetleri (gerçek satışları) alalım
        sales_df = order_df[order_df['quantity'] > 0]
        
        # Satış Adedi ve Ciro Hesaplama
        satilan_adetler = sales_df.groupby('sku')['quantity'].sum().to_dict()
        ciro_dict = order_df.groupby('sku')['amount'].sum().to_dict()

        # İade Adetleri (Quantity negatif olanlar veya description içinde iade/refund geçenler)
        iade_df = amazon_df[
            (amazon_df['quantity'] < 0) | 
            (amazon_df['description'].astype(str).str.lower().str.contains('refund|iade|return', na=False))
        ]
        iade_adetler = iade_df.groupby('sku')['quantity'].sum().abs().to_dict()

        # Tüm benzersiz SKU'ları listeleme
        tum_skular = set(order_df['sku'].dropna().unique()).union(set(maliyet_dict.keys()))

        analiz_verisi = []
        toplam_ciro = 0
        toplam_maliyet = 0
        toplam_satilan_adet = 0

        for sku in tum_skular:
            sku_str = str(sku).strip()
            
            # Ciro ve Satış Adedi
            ciro = ciro_dict.get(sku, 0)
            satis_adedi = satilan_adetler.get(sku, 0)
            iade_adedi = iade_adetler.get(sku, 0)
            
            # Maliyet hesaplama
            birim_maliyet = maliyet_dict.get(sku, 0)
            urun_adi = urun_adi_dict.get(sku, "Maliyet Listesinde Yok")
            
            # Toplam ürün maliyeti (Sadece satılan net adet üzerinden)
            toplam_urun_maliyeti = satis_adedi * birim_maliyet
            
            # Kâr ve ROI
            net_kar = ciro - toplam_urun_maliyeti
            roi = (net_kar / toplam_urun_maliyeti * 100) if toplam_urun_maliyeti > 0 else 0

            if ciro > 0 or satis_adedi > 0 or birim_maliyet > 0:
                analiz_verisi.append({
                    "MSKU": sku,
                    "Ürün Adı": urun_adi,
                    "Satılan Adet": int(sales_df[sales_df['sku'] == sku]['quantity'].sum()),  # Brüt satılan adet
                    "İade Adet": int(iade_adedi),
                    "Net Satış Adedi": int(satis_adedi),
                    "Birim Maliyet ($)": round(birim_maliyet, 2),
                    "Toplam Ürün Maliyeti ($)": round(toplam_urun_maliyeti, 2),
                    "Amazon Brüt Ciro ($)": round(ciro, 2),
                    "Net Kâr ($)": round(net_kar, 2),
                    "ROI (%)": f"%{round(roi, 2)}"
                })
                
                toplam_ciro += ciro
                toplam_maliyet += toplam_urun_maliyeti
                toplam_satilan_adet += satis_adedi

        sonuc_df = pd_pd.DataFrame(analiz_verisi)

        # --- SKOR TABELASI (KPI METRICS) ---
        st1, st2, st3, st4 = pd_st.columns(4)
        st1.metric("💰 Toplam Brüt Ciro", f"${round(toplam_ciro, 2)}")
        st2.metric("📉 Toplam Ürün Maliyeti", f"${round(toplam_maliyet, 2)}")
        
        genel_net_kar = toplam_ciro - toplam_maliyet
        st3.metric("📈 Net Kâr / Zarar", f"${round(genel_net_kar, 2)}", delta=f"{round(genel_net_kar, 2)} $", delta_color="normal")
        
        genel_roi = (genel_net_kar / toplam_maliyet * 100) if toplam_maliyet > 0 else 0
        st4.metric("📊 Genel ROI", f"%{round(genel_roi, 2)}")

        pd_st.markdown("---")
        
        # --- DETAYLI ANALİZ TABLOSU ---
        pd_st.subheader("📋 Ürün Bazlı Finansal Analiz Tablosu")
        pd_st.dataframe(sonuc_df, use_container_width=True)

        # Excel olarak indirme butonu
        @pd_st.cache_data
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')
            
        csv_data = convert_df(sonuc_df)
        pd_st.download_button(
            label="📥 Analiz Raporunu CSV Olarak İndir",
            data=csv_data,
            file_name='amazon_finansal_analiz_raporu.csv',
            mime='text/csv',
        )

    except Exception as e:
        pd_st.error(f"⚠️ Raporlar işlenirken bir hata oluştu: {str(e)}")
else:
    pd_st.info("💡 Lütfen sol menüden **Maliyet Çizelgesini** ve **Amazon Finansal Raporunu** yükleyin.")
