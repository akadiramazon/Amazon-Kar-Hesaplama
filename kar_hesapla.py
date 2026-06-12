import streamlit as st
import pandas as pd
import plotly.express as px

# 🌟 SAYFA AYARLARI VE GENİŞ EKRAN
st.set_page_config(page_title="Amazon CEO Pro Dashboard", layout="wide")

# 🎨 PREMIUM GÖZ YORMAYAN GECELER TEMASI (SAF CSS DARK MODE)
st.markdown("""
    <style>
    /* Global Karanlık Arka Plan ve Yazı Rengi */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #121212 !important;
        color: #e0e0e0 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Sol Kenar Menüsünün (Sidebar) Karanlığa Gömülmesi */
    [data-testid="stSidebar"] {
        background-color: #1e1e1e !important;
        border-right: 1px solid #2d2d2d;
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    
    /* Sekme (Tabs) Renklerinin Karanlık Mod Ayarı */
    button[data-testid="stMarkdownContainer"] {
        color: #e0e0e0 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1e1e1e !important;
        border-radius: 8px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        color: #888888 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* Minimalist ve Şık Gece Modu KPI Kartları kanka */
    .kpi-container {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        border: 1px solid #2d2d2d;
        margin-bottom: 15px;
    }
    .border-hakedis { border-top: 4px solid #1e88e5; }
    .border-maliyet { border-top: 4px solid #fb8c00; }
    .border-kesinti { border-top: 4px solid #e53935; }
    .border-kar { border-top: 4px solid #43a047; }
    .border-zarar { border-top: 4px solid #e53935; }
    
    .kpi-title {
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #aaaaaa;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #ffffff;
    }
    
    /* Karanlık Tablo Çerçeve Düzenlemesi */
    [data-testid="stDataFrame"] {
        border: 1px solid #2d2d2d !important;
        border-radius: 10px;
        padding: 5px;
        background-color: #1e1e1e !important;
    }
    
    /* Bilgilendirme Kutularının Rengini Yumuşatma */
    .stAlert {
        background-color: #1e1e1e !important;
        color: #e0e0e0 !important;
        border: 1px solid #2d2d2d !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Amazon CEO %100 Nokta Atışı Finansal Analiz Paneli")
st.markdown("🧠 **Yapay Zekâ Tabanlı Eşleştirme & Envanter Tazminat Takip Motoru Aktif.** Finansal Kokpite Hoş Geldin kanka!")
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

    df_master.columns = df_master.columns.str.replace('\n', ' ').str.replace('\r', '').str.strip()
    
    master_urun_col = "ÜRÜN ADI" if "ÜRÜN ADI" in df_master.columns else df_master.columns[0]
    master_maliyet_col = "KDV li Maaliyet" if "KDV li Maaliyet" in df_master.columns else df_master.columns[1]
    master_satis_col = "GERÇEK SATIŞ FİYATI" if "GERÇEK SATIŞ FİYATI" in df_master.columns else df_master.columns[1]

    df_master = df_master.dropna(subset=[master_urun_col, master_maliyet_col])
    df_master['ÜRÜN ADI_clean'] = df_master[master_urun_col].astype(str).str.strip()

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

    target_toplam_col = "Toplam (TRY)" if "Toplam (TRY)" in df_amazon_all.columns else df_amazon_all.columns[-1]

    df_amazon_all['Toplam (TRY)'] = df_amazon_all[target_toplam_col].apply(clean_maliyet_num)
    df_amazon_all['Toplam ürün fiyatları'] = df_amazon_all['Toplam ürün fiyatları'].apply(clean_maliyet_num) if 'Toplam ürün fiyatları' in df_amazon_all.columns else df_amazon_all['Toplam (TRY)']

    harici_gider_toplami = 0.0
    if 'Amazon ücretleri' in df_amazon_all.columns:
        harici_gider_toplami += df_amazon_all['Amazon ücretleri'].apply(clean_maliyet_num).sum()
    if 'Toplam promosyon indirimleri' in df_amazon_all.columns:
        harici_gider_toplami += df_amazon_all['Toplam promosyon indirimleri'].apply(clean_maliyet_num).sum()

    unique_amazon_names = df_amazon_all['Ürün Detayları'].dropna().unique()
    mapping = {}

    def clean_text_for_ai(text):
        return str(text).lower().replace('...', '').replace('-', ' ').replace(',', ' ').replace('/', ' ').strip()

    def calculate_jaccard_distance(set1, set2):
        if not set1 or not set2: return 0.0
        return float(len(set1.intersection(set2))) / float(len(set1.union(set2)))

    # YAPAY ZEKÂ MOTORU
    for name in unique_amazon_names:
        search_name = str(name).strip()
        
        if "ENVANTER ÜCRET İADESİ" in clean_text_for_ai(search_name) or "REIMBURSEMENT" in clean_text_for_ai(search_name):
            mapping[name] = {'Master_Name': "AMAZON LOJİSTİK ENVANTER TAZMİNATI", 'Maliyet': 0.0, 'Tekli_Satis': 0.0}
            continue

        clean_search = search_name[:-3].strip() if search_name.endswith('...') else search_name
        
        matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower() == search_name.lower()]
        if matches.empty:
            matches = df_master[df_master['ÜRÜN ADI_clean'].str.lower().str.startswith(clean_search.lower(), na=False)]
            
        if matches.empty:
            amz_words = set(clean_text_for_ai(clean_search).split())
            best_ai_score = -1.0
            best_ai_row = None
            
            for _, row in df_master.iterrows():
                master_words = set(clean_text_for_ai(row['ÜRÜN ADI_clean']).split())
                word_similarity = calculate_jaccard_distance(amz_words, master_words)
                
                if word_similarity > 0:
                    len_ratio = min(len(clean_search), len(row['ÜRÜN ADI_clean'])) / max(len(clean_search), len(row['ÜRÜN ADI_clean']))
                    ai_score = (word_similarity * 0.7) + (len_ratio * 0.3)
                    
                    if clean_text_for_ai(row['ÜRÜN ADI_clean']).startswith(clean_text_for_ai(clean_search)[:15]):
                        ai_score += 0.2
                    
                    if ai_score > best_ai_score:
                        best_ai_score = ai_score
                        best_ai_row = row
            
            if best_ai_row is not None and best_ai_score > 0.15:
                mapping[name] = {
                    'Master_Name': best_ai_row['ÜRÜN ADI_clean'], 
                    'Maliyet': best_ai_row['KDV_li_Maliyet_num'],
                    'Tekli_Satis': best_ai_row['Gercek_Satis_Fiyati_num']
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
    valid_actions_mask = df_amazon_all['İşlem tipi'].isin(['Sipariş Ödemesi', 'Para İadesi', 'Envanter Ücret İadesi', 'FBA Inventory Reimbursement'])
    df_valid_actions = df_amazon_all[valid_actions_mask].copy()
    
    df_valid_actions['Gercek_Urun_Adi'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Master_Name'])
    df_valid_actions['Birim_Maliyet'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Maliyet'])
    df_valid_actions['Tekli_Satis_Fiyati'] = df_valid_actions['Ürün Detayları'].map(lambda x: mapping[x]['Tekli_Satis'])

    def detect_quantity(row):
        if row['Gercek_Urun_Adi'] == "AMAZON LOJİSTİK ENVANTER TAZMİNATI": return 1
        if row['Tekli_Satis_Fiyati'] > 0 and abs(row['Toplam ürün fiyatları']) > 0:
            return max(1, round(abs(row['Toplam ürün fiyatları']) / row['Tekli_Satis_Fiyati']))
        return 1

    df_valid_actions['Adet'] = df_valid_actions.apply(detect_quantity, axis=1)
    
    def calc_row_maliyet(row):
        if row['Gercek_Urun_Adi'] == "AMAZON LOJİSTİK ENVANTER TAZMİNATI": return 0.0
        if row['İşlem tipi'] == 'Para İadesi': return -(row['Birim_Maliyet'] * row['Adet'])
        return row['Birim_Maliyet'] * row['Adet']

    df_valid_actions['Toplam_Urun_Maliyeti'] = df_valid_actions.apply(calc_row_maliyet, axis=1)
    df_valid_actions['Net_Kar'] = df_valid_actions['Toplam (TRY)'] - df_valid_actions['Toplam_Urun_Maliyeti']

    # KÜMÜLATİF TABLO OLUŞTURMA
    product_summary = df_valid_actions.groupby(['Ürün Detayları', 'Gercek_Urun_Adi']).agg(
        Toplam_Net_Gelen=('Toplam (TRY)', 'sum'),
        Toplam_Mal_Maliyeti=('Toplam_Urun_Maliyeti', 'sum'),
        Net_Temiz_Kar=('Net_Kar', 'sum')
    ).reset_index()

    def get_detailed_qtys(r):
        if r['Gercek_Urun_Adi'] == "AMAZON LOJİSTİK ENVANTER TAZMİNATI": return pd.Series([0, 0, 0.0])
        s_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Sipariş Ödemesi')]['Adet'].sum()
        i_adet = df_valid_actions[(df_valid_actions['Ürün Detayları'] == r['Ürün Detayları']) & (df_valid_actions['İşlem tipi'] == 'Para İadesi')]['Adet'].sum()
        return pd.Series([s_adet, i_adet, round((i_adet / s_adet * 100), 2) if s_adet > 0 else 0.0])

    product_summary[['Satış Adedi', 'İade Adedi', 'İade Oranı (%)']] = product_summary.apply(get_detailed_qtys, axis=1)
    product_summary['Net Satış Adedi'] = product_summary['Satış Adedi'] - product_summary['İade Adedi']

    # ROI ve Kâr Marjı Sütunları
    product_summary['Kâr Marjı (%)'] = product_summary.apply(
        lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Net_Gelen'] * 100), 2) if r['Toplam_Net_Gelen'] > 0 else 0.0, axis=1
    )
    product_summary['ROI (%)'] = product_summary.apply(
        lambda r: round((r['Net_Temiz_Kar'] / r['Toplam_Mal_Maliyeti'] * 100), 2) if r['Toplam_Mal_Maliyeti'] > 0 else 100.0, axis=1
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

    # ⭐ SOFT VE ELİT YAZI STİLLERİ (Gözü asla yormayan kurumsal tonlar)
    def hakedis_stil(val):
        return 'color: #90caf9; font-weight: 600;' if val > 0 else '' # Soft Pastel Mavi

    def kar_ve_roi_stil(val):
        if val > 0:
            return 'color: #a5d6a7; font-weight: bold;' # Yumuşak Pastel Yeşil
        elif val < 0:
            return 'color: #ef9a9a; font-weight: bold;' # Yumuşak Pastel Kırmızı
        return ''

    # 📑 SEKMELİ GÖSTERİM MERKEZİ
    sekme1, sekme2 = st.tabs(["💰 Ana Finans Paneli", "📉 İade Analiz Merkezi"])

    with sekme1:
        st.subheader("📊 Dönemsel Performans Özetiniz")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="kpi-container border-hakedis"><div class="kpi-title">💰 Net Hak Ediş</div><div class="kpi-value">{toplam_payout:,.2f} TL</div></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="kpi-container border-maliyet"><div class="kpi-title">📦 Mal Maliyeti</div><div class="kpi-value">{total_mal_maliyeti:,.2f} TL</div></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="kpi-container border-kesinti"><div class="kpi-title">🧾 Amazon Kesintileri</div><div class="kpi-value">{abs(harici_gider_toplami):,.2f} TL</div></div>', unsafe_allow_html=True)
        
        kar_sinifi = "border-kar" if final_net_kar >= 0 else "border-zarar"
        k4.markdown(f'<div class="kpi-container {kar_sinifi}"><div class="kpi-title">🔥 Net Temiz Kâr</div><div class="kpi-value">{final_net_kar:,.2f} TL</div></div>', unsafe_allow_html=True)

        if final_net_kar >= 0:
            st.success("🎉 Tebrikler kanka! Amazon lojistik tazminatları dahil dönemi kârla tamamladık.")
        else:
            st.error("🚨 Giderler bu dönem hakediş miktarını aşmış durumda kanka.")

        st.markdown("---")
        st.subheader("📋 Kurumsal Finans Raporu Tablosu")
        
        # Arka planda sayıları renklendiren minimalist motorumuz kanka
        try:
            styled_df = product_summary_show.style.map(kar_ve_roi_stil, subset=["Net Temiz Kâr (TRY)", "ROI (%)", "Kâr Marjı (%)"]).map(hakedis_stil, subset=["Net Hak Ediş (TRY)"]).format(precision=2)
        except:
            styled_df = product_summary_show.style.applymap(kar_ve_roi_stil, subset=["Net Temiz Kâr (TRY)", "ROI (%)", "Kâr Marjı (%)"]).applymap(hakedis_stil, subset=["Net Hak Ediş (TRY)"]).format(precision=2)

        # 👑 EN KRAL GÖRSEL ÖZELLİK: ROI ve Kâr Marjı arkasına soft veri barları çakıyoruz!
        # Hem ayırt edici hem de gözü sıfır yoran elit SaaS görüntüsü kanka
        st.dataframe(
            styled_df,
            column_config={
                "Kâr Marjı (%)": st.column_config.ProgressColumn("Kâr Marjı (%)", help="Ürünün Kârlılık Oranı", format="%.2f%%", min_value=0, max_value=100, color="green"),
                "ROI (%)": st.column_config.ProgressColumn("ROI (%)", help="Yatırımın Geri Dönüş Oranı", format="%.2f%%", min_value=0, max_value=200, color="green")
            },
            use_container_width=True
        )

        # CSV İndirme Butonu
        csv_data = product_summary_show.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Kusursuz Kârlılık Raporunu İndir",
            data=csv_data,
            file_name='amazon_kesin_kar_raporu.csv',
            mime='text/csv',
        )

        df_bulunamayanlar = product_summary_show[(product_summary_show['Sizin Listede Eşleşen Adı'] == "MALİYET LİSTESİNDE BULUNAMADI")]
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
                color_continuous_scale='Reds',
                template='plotly_dark'
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_iade_grafik[['Ürün Detayları', 'Gercek_Urun_Adi', 'Satış Adedi', 'İade Adedi', 'İade Oranı (%)']], use_container_width=True)
        else:
            st.success("🎉 Ne güzel kanka! Seçili dönemde hiç iade işleminiz bulunmuyor.")

except Exception as e:
    st.error(f"🚨 Sistem Hatası: {e}")
