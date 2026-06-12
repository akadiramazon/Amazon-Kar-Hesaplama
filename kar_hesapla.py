import streamlit as st
import pandas as pd
import plotly.express as px

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

st.title("🎯 Amazon CEO Kusursuz Finansal Analiz Paneli")
st.markdown("🧠 **Yapay Zekâ Tabanlı Varyasyon ve İsim Eşleştirme Motoru (AI Fuzzy Match) Aktif.** Sapmalar engellenmiştir kanka!")
st.markdown("---")

# 📊 GLOBAL PARA VE SAYISAL TEMİZLEME MOTORU
def clean_maliyet_num(val):
    if pd.isna(val): return 0.0
    val_str = str(val).replace('TRY','').replace('TL','').replace(' ','').strip()
    if ',' in val_str and '.' in val_str:
        val_str = val_str.replace('.', '').replace(',', '.')
    elif ',' in val_str:
        val_str = val_str.replace(',', '.')
    try: return float(val_str)
    except: return 0.0

# 📦 DOSYA YÜKLEME ALANLARI (SOL MENÜ)
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

    # Sütun isimlerindeki gizli boşlukları temizle
    df_master.columns = df_master.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    
    # Güvenli Sütun Eşleştirme Motoru
    master_urun_col = "ÜRÜN ADI" if "ÜRÜN ADI" in df_master.columns else df_master.columns[0]
    master_maliyet_col = "KDV li Maaliyet" if "KDV li Maaliyet" in df_master.columns else df_master.columns[1]
    master_satis_col = "GERÇEK SATIŞ FİYATI" if "GERÇEK SATIŞ FİYATI" in df_master.columns else df_master.columns[1]

    df_master = df_master.dropna(subset=[master_urun_col, master_maliyet_col])
    df_master['ÜRÜN ADI_clean'] = df_master[master_urun_col].astype(str).str.strip()

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
    df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam ürün fiyatları'].apply(clean_maliyet_num) if 'Toplam ürün fiyatları' in df_amazon_all.columns else df_amazon_all['Toplam (TRY)']

    # Amazon Harici Kesintiler ve Promosyonlar
    harici_gider_toplami = 0.0
    if 'Amazon ücretleri' in df_amazon_all.columns:
        harici_gider_toplami += df_amazon_all['Amazon ücretleri'].apply(clean_maliyet_num).sum()
    if 'Toplam promosyon indirimleri' in df_amazon_all.columns:
        harici_gider_toplami += df_amazon_all['Toplam promosyon indirimleri'].apply(clean_maliyet_num).sum()

    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    # 🧠 YAPAY ZEKÂ DESTEKLİ METİN VE KELİME ANALİZ FONKSİYONLARI
    def clean_text_for_ai(text):
        return str(text).lower().replace('...', '').replace('-', ' ').replace(',', ' ').replace('/', ' ').strip()

    def calculate_jaccard_distance(set1, set2):
        if not set1 or not set2: return 0.0
        return float(len(set1.intersection(set2))) / float(len(set1.union(set2)))

    # 🎯 4. PLAN: YAPAY ZEKÂ TABANLI AKILLI EŞLEŞTİRME DÖNGÜSÜ
    for name in unique_amazon_names:
        search_name = str(name).strip()
        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        # 1. Aşama: Birebir Tam Metin Kilidi
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        
        # 2. Aşama: Başlangıç Köprü Kilidi
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        # 3. Aşama: Yapay Zekâ Benzerlik ve Karakter Ağırlıklı Uzaklık Algoritması (AI Fuzzy Match)
        if matches.empty:
            amz_words = set(clean_text_for_ai(clean_search).split())
            best_ai_score = -1.0
            best_ai_row = None
            
            for _, row in df_master.iterrows():
                master_words = set(clean_text_for_ai(row['ÜRÜN ADI_clean']).split())
                
                # Kelime bazlı Jaccard Benzerlik Skoru hesapla
                word_similarity = calculate_jaccard_distance(amz_words, master_words)
                
                if word_similarity > 0:
                    # Karakter uzunluğu ve yapısal benzerlik ağırlığı ekle (Sapmayı önler kanka)
                    len_ratio = min(len(clean_search), len(row['ÜRÜN ADI_clean'])) / max(len(clean_search), len(row['ÜRÜN ADI_clean']))
                    ai_score = (word_similarity * 0.7) + (len_ratio * 0.3)
                    
                    # Eğer ürün adı doğrudan Amazon isminin ön ekiyle başlıyorsa yapay zekâya ödül skoru ver
                    if clean_text_for_ai(row['ÜRÜN ADI_clean']).startswith(clean_text_for_ai(clean_search)[:15]):
                        ai_score += 0.2
                    
                    if ai_score > best_ai_score:
                        best_ai_score = ai_score
                        best_ai_row = row
            
            # Yapay zekâ güven eşiği (En azından mantıklı bir yakınlık bulduysa bağla kanka)
            if best_ai_row is not None and best_ai_score > 0.15:
                mapping[name] = {
                    'Master_Name': best_ai_row['ÜRÜN ADI_clean'], 
                    'Maliyet': best_ai_row['KDV_li_Maliyet_num'],
                    'Tekli_Satis': best_ai_row['Gercek_Satis_Fiyati_num']
                }
                continue

        # Eğer 1. veya 2. aşamada pürüzsüz bulunduysa
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

    # 📈 Dynamic ROI ve Kâr Marjı Enjeksiyonu
    product_summary['Kâr Marjı (%)'] = product_summary.apply(
        lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Net_Gelen'] * 100), 2) if r['Toplam_Net_Gelen'] > 0 else 0.0, axis=1
    )
    product_summary['ROI (%)'] = product_summary.apply(
        lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Mal_Maliyeti'] * 100), 2) if r['Toplam_Mal_Maliyeti'] > 0 else 0.0, axis=1
    )

    product_summary = product_summary.sort_values(by='Net_Temiz_Kar', ascending=False)

    product_summary_show = product_summary.rename(columns={
        'Ürün Detayları': 'Amazon Raporundaki Ürün Adı', 'Gercek_Urun_Adi': 'Sizin Listede Eşleşen Adı',
        'Toplam_Net_Gelen': 'Net Hak Ediş (TRY)', 'Toplam_Mal_Maliyeti': 'Toplam Mal Maliyeti (TRY)',
        'Net_Temiz_Kar': 'Net Temiz Kâr (TRY)'
    })

    toplam_payout = df_amazon_all['Toplam (TRY)'].sum()
    total_mal_maliyeti = df_valid_actions['Toplam_Urun_Maliyeti'].sum()
    final_net_kar = toplam_payout - total_mal_maliyeti

    # ⭐ SAF CSS TABLO RENKLENDİRME STYLERS (Hatasız ve Hızlı kanka)
    def hakedis_renklendir(val):
        return 'background-color: #e1f5fe; color: #0277bd;' if val > 0 else ''

    def kar_ve_roi_renklendir(val):
        if val > 0:
            return 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
        elif val < 0:
            return 'background-color: #ffebee; color: #c62828; font-weight: bold;'
        return ''

    # 📑 SEKMELİ GÖSTERİM MERKEZİ (Senin Orijinal Yapın)
    sekme1, sekme2 = st.tabs(["💰 Ana Finans Paneli", "📉 İade Analiz Merkezi"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("💰 Net Hak Ediş (Amazon Pay)", f"{toplam_payout:,.2f} TL")
        kpi2.metric("📦 Toplam Ürün Geliş Maliyeti", f"{total_mal_maliyeti:,.2f} TL")
        kpi3.metric("🧾 Amazon Kesinti & Promosyon", f"{abs(harici_gider_toplami):,.2f} TL", delta="-Harici Kesinti", delta_color="inverse")
        
        if final_net_kar >= 0:
            kpi4.metric("🔥 DÖNEM NET TEMİZ KÂR", f"{final_net_kar:,.2f} TL", delta="KÂRDAYIZ KANKA!")
            st.success(f"🎉 Muazzam! Bu dönemi başarıyla temiz kârla kapattık.")
        else:
            kpi4.metric("📉 DÖNEM NET ZARAR", f"{final_net_kar:,.2f} TL", delta="İÇERİDEYİZ!", delta_color="inverse")
            st.error(f"🚨 Giderler bu dönem hakediş miktarını aşmış durumda kanka.")

        st.markdown("---")
        st.subheader("📋 Tüm Ürünlerin Kusursuz Analiz Tablosu")
        
        # Saf CSS tabanlı ısı haritası tablosu
        try:
            styled_df = product_summary_show.style.map(kar_ve_roi_renklendir, subset=["Net Temiz Kâr (TRY)", "ROI (%)", "Kâr Marjı (%)"]).map(hakedis_renklendir, subset=["Net Hak Ediş (TRY)"]).format(precision=2)
        except:
            styled_df = product_summary_show.style.applymap(kar_ve_roi_renklendir, subset=["Net Temiz Kâr (TRY)", "ROI (%)", "Kâr Marjı (%)"]).applymap(hakedis_renklendir, subset=["Net Hak Ediş (TRY)"]).format(precision=2)

        st.dataframe(styled_df, use_container_width=True)

        csv_data = product_summary_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Kusursuz Kârlılık Raporunu İndir",
            data=csv_data,
            file_name='amazon_kesin_kar_raporu.csv',
            mime='text/csv',
        )

        df_bulunamayanlar = product_summary_show[product_summary_show['Sizin Listede Eşleşen Adı'] == "MALİYET LİSTESİNDE BULUNAMADI"]
        if not df_bulunamayanlar.empty:
            st.markdown("---")
            st.warning("🚨 **Kanka Gözden Kaçanlar Var! Aşağıdaki ürünler maliyet çizelgende tam eşleşmediği için kâr haneleri sıfır kaldı:**")
            st.dataframe(df_bulunamayanlar[['Amazon Raporundaki Ürün Adı', 'Net Hak Ediş (TRY)']], use_container_width=True)

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
