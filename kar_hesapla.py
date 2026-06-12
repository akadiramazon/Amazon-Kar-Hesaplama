import streamlit as pd_st
import pandas as pd_pd

pd_st.set_page_config(page_title="Amazon Finansal Analiz Paneli", layout="wide")

pd_st.title("📊 Amazon Finansal Analiz ve Kârlılık Paneli")
pd_st.markdown("Amazon raporundaki **Ürün İsimleri** ile Maliyet listesindeki **Ürün Adı** eşleştirilerek hesaplanır.")

pd_st.sidebar.header("📁 Rapor Yükleme Alanı")

# 1. Maliyet Çizelgesi Yükleme (CSV)
maliyet_dosya = pd_st.sidebar.file_uploader("1️⃣ Güncel Maliyet Çizelgesini Seçin (.csv)", type=["csv"])

# 2. Amazon Raporu Yükleme
amazon_dosya = pd_st.sidebar.file_uploader("2️⃣ Amazon Günlük/Aylık Raporunu Seçin (.csv / .txt)", type=["csv", "txt"])

if maliyet_dosya and amazon_dosya:
    try:
        # --- MALİYET ÇİZELGESİ OKUMA (Gelişmiş Ayırıcı Tespiti) ---
        try:
            # Hem virgül hem noktalı virgül uyumu için sep=None
            maliyet_df = pd_pd.read_csv(maliyet_dosya, sep=None, engine='python', on_bad_lines='skip')
        except Exception:
            maliyet_dosya.seek(0)
            maliyet_df = pd_pd.read_csv(maliyet_dosya, sep='\t', on_bad_lines='skip')
            
        maliyet_df.columns = maliyet_df.columns.str.strip()
        
        # Artık MSKU zorunlu değil, sadece İsim ve Maliyet yeterli!
        required_maliyet = ['Ürün Adı', 'Birim Maliyet ($)']
        if not all(col in maliyet_df.columns for col in required_maliyet):
            pd_st.error(f"⚠️ Maliyet çizelgesinde şu sütunlar eksik: {set(required_maliyet) - set(maliyet_df.columns)}")
            pd_st.info("Lütfen CSV dosyanızda 'Ürün Adı' ve 'Birim Maliyet ($)' sütunlarının olduğundan emin olun.")
            pd_st.stop()
            
        # Sayısal formata güvenli dönüştürme
        maliyet_df['Birim Maliyet ($)'] = pd_pd.to_numeric(maliyet_df['Birim Maliyet ($)'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        # İsim tabanlı sözlük oluşturma (Gereksiz boşlukları temizliyoruz)
        maliyet_df['Ürün Adı'] = maliyet_df['Ürün Adı'].astype(str).str.strip()
        maliyet_dict = maliyet_df.set_index('Ürün Adı')['Birim Maliyet ($)'].to_dict()

        # --- AMAZON RAPORU OKUMA ---
        try:
            amazon_df = pd_pd.read_csv(amazon_dosya, sep=None, engine='python', on_bad_lines='skip')
        except Exception:
            amazon_dosya.seek(0)
            amazon_df = pd_pd.read_csv(amazon_dosya, sep='\t', on_bad_lines='skip')

        amazon_df.columns = amazon_df.columns.str.strip()
        
        # Sütun isimlerini normalize etme
        col_mapping = {
            'amount': 'amount', 'tutar': 'amount', 'Amount': 'amount', 'Tutar': 'amount',
            'quantity': 'quantity', 'adet': 'quantity', 'Quantity': 'quantity', 'Adet': 'quantity',
            'description': 'description', 'açıklama': 'description', 'Description': 'description', 'Açıklama': 'description',
            'type': 'type', 'tip': 'type', 'Type': 'type', 'Tip': 'type',
            'title': 'description', 'product title': 'description' # Alternatif isimler için
        }
        amazon_df = amazon_df.rename(columns=col_mapping)

        required_amazon = ['amount', 'quantity', 'description', 'type']
        if not all(col in amazon_df.columns for col in required_amazon):
            pd_st.error(f"⚠️ Amazon raporunda gerekli sütunlar bulunamadı. (Açıklama/Description, Tutar/Amount, Adet/Quantity, Tip/Type eksik)")
            pd_st.stop()

        # Finansal verileri temizleme
        amazon_df['amount'] = pd_pd.to_numeric(amazon_df['amount'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        amazon_df['quantity'] = pd_pd.to_numeric(amazon_df['quantity'], errors='coerce').fillna(0)
        amazon_df['description'] = amazon_df['description'].astype(str).str.strip()

        # Sipariş satırları
        order_df = amazon_df[amazon_df['type'].astype(str).str.lower() == 'order']
        sales_df = order_df[order_df['quantity'] > 0]
        
        # İsim bazlı gruplama (SKU yerine artık Description/Ürün Adı kullanıyoruz)
        satilan_adetler = sales_df.groupby('description')['quantity'].sum().to_dict()
        ciro_dict = order_df.groupby('description')['amount'].sum().to_dict()

        # İadeler
        iade_df = amazon_df[
            (amazon_df['quantity'] < 0) | 
            (amazon_df['description'].str.lower().str.contains('refund|iade|return', na=False))
        ]
        iade_adetler = iade_df.groupby('description')['quantity'].sum().abs().to_dict()

        # Tüm benzersiz ürün isimleri
        tum_urunler = set(order_df['description'].dropna().unique()).union(set(maliyet_dict.keys()))

        analiz_verisi = []
        toplam_ciro = 0
        toplam_maliyet = 0

        for urun in tum_urunler:
            if not urun or urun == "nan":
                continue
                
            ciro = ciro_dict.get(urun, 0)
            satis_adedi = satilan_adetler.get(urun, 0)
            iade_adedi = iade_adetler.get(urun, 0)
            
            # Maliyeti isim üzerinden çekiyoruz
            birim_maliyet = maliyet_dict.get(urun, 0)
            
            # Eğer birebir uyuşmadıysa, açıklama içinde geçiyor mu kontrolü (Gelişmiş Eşleştirme)
            if birim_maliyet == 0:
                for m_isim, m_fiyat in maliyet_dict.items():
                    if m_isim in urun or urun in m_isim:
                        birim_maliyet = m_fiyat
                        break

            toplam_urun_maliyeti = satis_adedi * birim_maliyet
            net_kar = ciro - toplam_urun_maliyeti
            roi = (net_kar / toplam_urun_maliyeti * 100) if toplam_urun_maliyeti > 0 else 0

            if ciro != 0 or satis_adedi > 0 or birim_maliyet > 0:
                analiz_verisi.append({
                    "Ürün Adı / Açıklama": urun,
                    "Satılan Adet": int(satis_adedi),
                    "İade Adet": int(iade_adedi),
                    "Birim Maliyet ($)": round(birim_maliyet, 2),
                    "Toplam Ürün Maliyeti ($)": round(toplam_urun_maliyeti, 2),
                    "Amazon Brüt Ciro ($)": round(ciro, 2),
                    "Net Kâr ($)": round(net_kar, 2),
                    "ROI (%)": f"%{round(roi, 2)}"
                })
                
                toplam_ciro += ciro
                toplam_maliyet += toplam_urun_maliyeti

        sonuc_df = pd_pd.DataFrame(analiz_verisi)

        # --- SKOR TABELASI ---
        st1, st2, st3, st4 = pd_st.columns(4)
        st1.metric("💰 Toplam Brüt Ciro", f"${round(toplam_ciro, 2)}")
        st2.metric("📉 Toplam Ürün Maliyeti", f"${round(toplam_maliyet, 2)}")
        
        genel_net_kar = toplam_ciro - toplam_maliyet
        st3.metric("📈 Net Kâr / Zarar", f"${round(genel_net_kar, 2)}", delta=f"{round(genel_net_kar, 2)} $", delta_color="normal")
        
        genel_roi = (genel_net_kar / toplam_maliyet * 100) if toplam_maliyet > 0 else 0
        st4.metric("📊 Genel ROI", f"%{round(genel_roi, 2)}")

        pd_st.markdown("---")
        
        # --- TABLO ---
        pd_st.subheader("📋 İsim Eşleştirmeli Finansal Analiz Tablosu")
        pd_st.dataframe(sonuc_df, use_container_width=True)

        # İndirme Butonu
        csv_data = sonuc_df.to_csv(index=False).encode('utf-8')
        pd_st.download_button(
            label="📥 Analiz Raporunu CSV Olarak İndir",
            data=csv_data,
            file_name='amazon_isim_eslesmeli_analiz.csv',
            mime='text/csv',
        )

    except Exception as e:
        pd_st.error(f"⚠️ Raporlar işlenirken bir hata oluştu: {str(e)}")
else:
    pd_st.info("💡 Sol menüden **Maliyet Çizelgesini (.csv)** ve limitli **Amazon Raporunu** yükleyin. Sistem isimleri otomatik eşleştirecektir.")
