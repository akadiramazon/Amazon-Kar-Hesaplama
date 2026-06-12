import streamlit as st
import pandas as pd
import plotly.express as px

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Kusursuz Finansal Analiz Paneli")
st.markdown("Gelişmiş Kelime Havuzu, Karakter Uzunluğu ve Varyasyon Dengesi Filtresi ile Sapmalar Tamamen Engellenmiştir kanka!")
st.markdown("---")

# 📊 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
st.sidebar.header("📦 Veri Yükleme Merkezi")
maliyet_file = st.sidebar.file_uploader("1️⃣ Maliyet Çizelgesini Seçin (.csv)", type=["csv"], key="maliyet")
amazon_files = st.sidebar.file_uploader("2️⃣ Amazon Finans Raporlarını Seçin (Çoklu Seçilebilir)", type=["csv"], accept_multiple_files=True, key="amazon")

if not maliyet_file or not amazon_files:
    st.info("💡 Paneli canlandırmak için sol taraftaki menüden **Maliyet Çizelgenizi** ve **Amazon Finans Raporlarınızı** seçin kanka!")
    st.stop()

try:
    # 1. Maliyet Dosyasını Oku
    try: df_master = pd.read_csv(maliyet_file, encoding='utf-8')
    except:
        try: df_master = pd.read_csv(maliyet_file, encoding='utf-8-sig')
        except: df_master = pd.read_csv(maliyet_file, encoding='latin1')

    # Sütun isimlerindeki gizli boşlukları ve alt satır karakterlerini temizle
    df_master.columns = df_master.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    
    # ⭐ GÜVENLİ VE SABİT SÜTUN EŞLEŞTİRME MOTORU
    # Eğer sütun bulunamazsa index out of range vermemesi için güvenli kontrol yapıyoruz kanka
    master_urun_col = "ÜRÜN ADI" if "ÜRÜN ADI" in df_master.columns else df_master.columns[0]
    master_maliyet_col = "KDV li Maaliyet" if "KDV li Maaliyet" in df_master.columns else df_master.columns[1]
    master_satis_col = "GERÇEK SATIŞ FİYATI" if "GERÇEK SATIŞ FİYATI" in df_master.columns else master_maliyet_col

    df_master = df_master.dropna(subset=[master_urun_col, master_maliyet_col])
    df_master['ÜRÜN ADI_clean'] = df_master[master_urun_col].astype(str).str.strip()

    # Sayısal Dönüştürme Motoru
    def clean_maliyet_num(val):
        if pd.isna(val): return 0.0
        val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
        if ',' in val_str and '.' in val_str:
            val_str = val_str.replace('.', '').replace(',', '.')
        elif ',' in val_str:
            val_str = val_str.replace(',', '.')
        try: return float(val_str)
        except: return 0.0

    df_master['KDV_li_Maliyet_num'] = df_master[master_maliyet_col].apply(clean_maliyet_num)
    df_master['Gercek_Satis_Fiyati_num'] = df_master[master_satis_col].apply(clean_maliyet_num)

    # 2. Amazon Raporlarını Birleştir
    amazon_df_listesi = []
    for f in amazon_files:
        try: df_temp = pd.read_csv(f, encoding='utf-8')
        except:
            try: df_temp = pd.read_csv(f, encoding='utf-8-sig')
            except: df_temp = pd.read_csv(f, encoding='latin1')
        amazon_df_listesi.append(df_temp)

    df_amazon_all = pd.concat(amazon_df_listesi, ignore_index=True)
    df_amazon_all.columns = df_amazon_all.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()

    # Sütun Sabitleyiciler
    target_toplam_col = "Toplam (TRY)" if "Toplam (TRY)" in df_amazon_all.columns else df_amazon_all.columns[-1]

    df_amazon_all['Toplam (TRY)'] = df_amazon_all[target_toplam_col].apply(clean_maliyet_num)
    if 'Toplam ürün fiyatları' in df_amazon_all.columns:
        df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam ürün fiyatları'].apply(clean_maliyet_num)
    else:
        df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam (TRY)']

    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    # Yardımcı Fonksiyon: Kelimeleri temizler
    def get_words(text):
        text_clean = str(text).lower().replace('...', '').replace('-', ' ').replace(',', ' ').replace('/', ' ')
        return [w for w in text_clean.split() if len(w) > 1]

    # 🎯 SAPMALARI ENGELLEYEN YENİ ULTRA HASSAS EŞLEŞTİRME MOTORU
    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # Kademe 1: Tam Birebir Eşleşme
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        # Kademe 2: Başlangıç Eşleşmesi
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        # Kademe 3: Geliştirilmiş Akıllı Ağırlık ve Uzunluk Dengeli Skorlama
        if matches.empty:
            amz_words = get_words(clean_search)
            best_score = -100.0
            best_row = None
            
            for _, row in df_master.iterrows():
                master_words = get_words(row['ÜRÜN ADI_clean'])
                common_words = set(amz_words).intersection(set(master_words))
                
                if len(common_words) >= 1:
                    score = float(len(common_words))
                    
                    # ⭐ Sapma Kalkanı 1: Karakter uzunluk farkı cezası
                    len_diff = abs(len(row['ÜRÜN ADI_clean']) - len(clean_search))
                    score -= (len_diff * 0.005)
                    
                    # ⭐ Sapma Kalkanı 2: Amazon isminin başı ile uyuşuyorsa ödül ver
                    if row['ÜRÜN ADI_clean'].lower().startswith(clean_search.lower()[:15]):
                        score += 0.5
                    
                    if score > best_score:
                        best_score = score
                        best_row = row
            
            if best_row is not None:
                mapping[name] = {
                    'Master_Name': best_row['ÜRÜN ADI_clean'], 
                    'Maliyet': best_row['KDV_li_Maliyet_num'],
                    'Tekli_Satis': best_row['Gercek_Satis_Fiyati_num']
                }
                continue

        if not matches.empty:
            if len(matches) > 1:
                matches = matches.copy()
                matches['l_diff'] = (matches['ÜRÜN ADI_clean'].str.len() - len(clean_search)).abs()
                matched_row = matches.sort_values(by='l_diff').iloc[0]
            else:
                matched_row = matches.iloc[0]
                
            mapping[name] = {
                'Master_Name': matched_row['ÜRÜN ADI_clean'], 
                'Maliyet': matched_row['KDV_li_Maliyet_num'],
                'Tekli_Satis': matched_row['Gercek_Satis_Fiyati_num']
            }
        else:
            mapping[name] = {'Master_Name': "MALİYET LİSTESİNDE BULUNAMADI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0}

    # Finansal Hesaplamalar
    df_valid_actions = df_amazon_all[df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi'])].copy()
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])

    def detect_quantity(row):
        if row['Tekli_Satis_Fiyati'] > 0 and abs(row['Toplam ürün fiyatları']) > 0:
            return max(1, round(abs(row['Toplam ürün fiyatları']) / row['Tekli_Satis_Fiyati']))
        return 1

    df_valid_actions['Adet'] = df_valid_actions.apply(detect_quantity, axis=1)
    
    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(
        lambda row: (row['Birim_Maliyet'] * row['Adet']) if row['İşlem tipi'] == 'Sipariş Ödemesi' else -(row['Birim_Maliyet'] * row['Adet']), axis=1
    )
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # KÜMÜLATİF TABLO OLUŞTURMA
    product_summary = df_valid_actions.groupby(['Ürün Detayları', 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Toplam (TRY)', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    def get_detailed_qtys(r):
        s_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Sipariş Ödemesi')]['Adet'].sum()
        i_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Para İadesi')]['Adet'].sum()
        return pd.Series([s_adet, i_adet, round((i_adet / s_adet * 100), 2) if s_adet > 0 else 0.0])

    product_summary[['Satış Adedi', 'İade Adedi', 'İade Oranı (%)']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']
    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary_show = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Raporundaki Ürün Adı', 'Gercek_Urun_Adi': 'Sizin Listede Eşleşen Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Mal Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # 📑 SEKMELİ GÖSTERİM MERKEZİ
    sekme1, sekme2 = st.tabs(["💰 Ana Finans Paneli", "📉 İade Analiz Merkezi"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        
        if final_net_kar >= 0:
            st.success(f"🔥 SEÇİLİ DÖNEM NET TEMİZ KÂR: {final_net_kar:,.2f} TL")
        else:
            st.error(f"📉 SEÇİLİ DÖNEM NET ZARAR: {final_net_kar:,.2f} TL")

        st.markdown("---")
        st.subheader("📋 Tüm Ürünlerin Kusursuz Analiz Tablosu")
        st.dataframe(product_summary_show, use_container_width=True)

        csv_data = product_summary_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Kusursuz Kârlılık Raporunu İndir",
            data=csv_data,
            file_name='amazon_kesin_kar_raporu.csv',
            mime='text/csv',
        )

    with sekme2:
        st.subheader("📉 Ürün Bazlı İade Performans Analizi")
        df_iade_grafik = product_summary[product_summary['İade Adedi'] > 0].sort_values(by='İade Adedi', ascending=False)
        
        if not df_iade_grafik.empty:
            fig = px.bar(
                df_iade_grafik.head(15),
                x='Gercek_Urun_Adi',
                y='İade Adedi',
                title='🔥 En Çok İade Alan Top 15 Ürününüz',
                labels={'Gercek_Urun_Adi': 'Ürün Adı', 'İade Adedi': 'İade Edilen Adet'},
                color='İade Oranı (%)',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_iade_grafik[['Ürün Detayları', 'Gercek_Urun_Adi', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']], use_container_width=True)
        else:
            st.success("🎉 Ne güzel kanka! Seçili dönemde hiç iade işleminiz bulunmuyor.")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
