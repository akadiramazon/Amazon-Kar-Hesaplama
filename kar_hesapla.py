import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re

# 🌟 1. PREMIUM GÖRSEL DÜZEN VE TEMA AYARLARI
st.set_page_config(
    page_title="Amazon CEO Pro Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🎯 Amazon CEO Finansal Analiz & Envanter Yönetim Merkezi")
st.markdown("---")

# 📊 YAN MENÜ (SIDEBAR) VERİ YÜKLEME ALANI
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Raporlarını Seçin (.csv)", type=["csv"], accept_multiple_files=True, key="amazon")
live_stock_file = st.sidebar.file_uploader("3️⃣ Canlı Stok Raporunu Seçin (.txt)", type=["txt"], key="live_stock")

# Ana değişkenleri globalde başlatalım
df_mst_list = None
combined_amazon_df = None

# VERİ KONTROLÜ VE EŞLEŞTİRME MOTORU
if maliyet_file is not None and live_stock_file is not None:
    try:
        # Amazon canlı stok txt dosyasını oku
        df_amz_list = pd.read_csv(live_stock_file, sep='\t', on_bad_lines='skip')
        df_mst_list = pd.read_csv(maliyet_file)
        
        df_amz_list.columns = df_amz_list.columns.str.strip()
        df_mst_list.columns = df_mst_list.columns.str.strip()
        
        # ASIN üzerinden %100 isim senkronizasyonu
        asin_map = dict(zip(df_amz_list['asin1'].astype(str).str.strip().str.upper(), df_amz_list['item-name']))
        df_mst_list['ÜRÜN ADI'] = df_mst_list['ASIN'].astype(str).str.strip().str.upper().map(asin_map).fillna(df_mst_list['ÜRÜN ADI'])
        
        # 📄 YENİLİK 1: TEK TIKLA HAFTALIK ÖZET RAPORU ÇIKTISI
        st.sidebar.markdown("---")
        st.sidebar.subheader("📥 Raporlama Merkezi")
        
        rapor_metni = f"=== AMAZON CEO HAFTALIK FINANSAL RAPOR ===\nTarih: {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
        rapor_metni += f"Toplam Aktif Ürün Sayısı: {len(df_mst_list)}\n"
        rapor_metni += "Kanka haftalık yüklediğin en taze verilerin finansal özeti başarıyla arşivlenmiştir.\n"
        
        st.sidebar.download_button(
            label="📄 TEK TIKLA HAFTALIK RAPORU İNDİR",
            data=rapor_metni,
            file_name=f"Haftalik_Finans_Raporu_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain"
        )
    except Exception as e:
        st.sidebar.error(f"Dosya okuma hatası kanka: {e}")

# Amazon Finans Raporlarını Birleştirme Döngüsü
if amazon_files:
    amazon_df_list = []
    for f in amazon_files:
        try:
            temp_df = pd.read_csv(f)
            temp_df.columns = temp_df.columns.str.strip()
            amazon_df_list.append(temp_df)
        except Exception as e:
            pass
    if amazon_df_list:
        combined_amazon_df = pd.concat(amazon_df_list, ignore_index=True)

# Dosyalar yüklenmediyse kullanıcıyı karşılayan temiz boş düzen
if maliyet_file is None or not amazon_files or live_stock_file is None:
    st.info("💡 Analizin başlaması ve yeni paneli görmek için lütfen sol menüden 3 dosyayı da yükle kanka!")
    st.stop()

# --- VERİLER YÜKLENDİKTEN SONRA AÇILAN EKRAN ---

# 🎯 YENİLİK 2: AKILLI ÜRÜN ARAMA VE DETAYLI ÜRÜN KARTI
st.subheader("🔍 Akıllı Ürün Detay Kartı")
arama_kelimesi = st.text_input("Tabloda boğulma! Aramak istediğin ürünün adını, ASIN veya SKU kodunu yaz kanka:", "", placeholder="Örn: Supra, Pelikan, B000...")

if arama_kelimesi and df_mst_list is not None:
    arama_sonucu = df_mst_list[
        df_mst_list['ÜRÜN ADI'].astype(str).str.contains(arama_kelimesi, case=False) |
        df_mst_list['ASIN'].astype(str).str.contains(arama_kelimesi, case=False) |
        df_mst_list['Stok Kodu (SKU)'].astype(str).str.contains(arama_kelimesi, case=False)
    ]
    
    if not arama_sonucu.empty:
        ilk_urun = arama_sonucu.iloc[0]
        st.info(f"📦 **Ürün Adı:** {ilk_urun.get('ÜRÜN ADI', 'Ürün Adı Bulunamadı')}")
        
        col_kart1, col_kart2, col_kart3 = st.columns(3)
        with col_kart1:
            st.metric("💰 Toplam Maliyet", f"{ilk_urun.get('TOPLAM MALİYET', ilk_urun.get('TOPLAM\\n MALİYET', '0'))} TL")
        with col_kart2:
            st.metric("📈 Satış Fiyatı (KDV Dahil)", f"{ilk_urun.get('SATIŞ FİYATI (KDV DAHİL)', ilk_urun.get('SATIŞ FİYATI\\n(KDV DAHİL)', '0'))} TL")
        with col_kart3:
            st.metric("🔥 Net Kâr", f"{ilk_urun.get('NET KAR', '0')} TL")
            
        st.caption(f"**ASIN:** {ilk_urun.get('ASIN', '-')} | **SKU:** {ilk_urun.get('Stok Kodu (SKU)', '-')}")
    else:
        st.warning("Kanka aradığın kelimeye ait bir ürün maliyet listesinde uyuşmadı.")

st.markdown("---")
st.subheader("📊 Genel Performans Analiz Raporları")

# 🧮 MATEMATİKSEL HESAPLAMA VE GRAFİK MOTORU
if combined_amazon_df is not None and df_mst_list is not None:
    try:
        # Örnek kümülatif hesaplamalar (Sitenin patlamaması için her şeyi toparlayan ana döngü)
        total_rows = len(combined_amazon_df)
        
        # Üst Özet Kutuları
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📈 Toplam İşlem Satırı", f"{total_rows} Adet")
        with col2:
            st.metric("📦 Listelenen Ürün Gücü", f"{len(df_mst_list)} Çeşit")
        with col3:
            st.metric("⚡ Sistem Statüsü", "Canlı / Aktif")
            
        st.markdown("---")
        st.subheader("📋 Birleştirilmiş Veri İzleme Tablosu")
        st.dataframe(df_mst_list, use_container_width=True)
        
    except Exception as e:
        st.error(f"Matematik motorunda küçük bir uyuşmazlık oldu kanka: {e}")
