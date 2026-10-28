import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =========================================================================
# CONFIGURAÇÃO DA PÁGINA WEB
# =========================================================================
st.set_page_config(
    page_title="Screener Fundamentalista B3",
    page_icon="📈",
    layout="wide"
)

# Customização de CSS para visual Dark Mode estilo Terminal
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .stMetric { background-color: #252526; padding: 10px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# =========================================================================
# FUNÇÕES DE TRATAMENTO E CÁLCULO
# =========================================================================
def tratar_valores_numericos(df):
    df.columns = df.columns.str.strip()
    def clean_num(val):
        if pd.isna(val): return None
        val_str = str(val).strip().replace('.', '').replace(',', '.')
        try: return float(val_str)
        except ValueError: return None

    for col in [c for c in df.columns if c != "TICKER"]:
        df[col] = df[col].apply(clean_num)
    return df

def calcular_indicadores_avancados(df):
    # Graham: sqrt(22.5 * LPA * VPA)
    df["GRAHAM (VI)"] = df.apply(
        lambda r: (22.5 * r["LPA"] * r["VPA"])**0.5 if pd.notna(r.get("LPA")) and pd.notna(r.get("VPA")) and r["LPA"]>0 and r["VPA"]>0 else None, axis=1
    )
    # Bazin: DPA / 0.06
    df["BAZIN (VI)"] = df.apply(
        lambda r: (r["PRECO"] * (r["DY"] / 100.0)) / 0.06 if pd.notna(r.get("PRECO")) and pd.notna(r.get("DY")) and r["DY"]>0 else None, axis=1
    )

    # Score Fundamentalista 0 a 100
    def calc_score(r):
        s = 0
        s += 15 if (r.get("DY") or 0) >= 6.0 else (8 if (r.get("DY") or 0) >= 3.0 else 0)
        s += 15 if (r.get("ROE") or 0) >= 15 else (8 if (r.get("ROE") or 0) >= 10 else 0)
        s += 10 if (r.get("ROIC") or 0) >= 12 else (5 if (r.get("ROIC") or 0) >= 8 else 0)
        pl = r.get("P/L") or 999
        pvp = r.get("P/VP") or 999
        s += 15 if 0 < pl <= 10 else (8 if 10 < pl <= 15 else 0)
        s += 10 if 0 < pvp <= 1.5 else (5 if 1.5 < pvp <= 2.5 else 0)
        s += 15 if (r.get("MARG. LIQUIDA") or 0) >= 15 else (8 if (r.get("MARG. LIQUIDA") or 0) >= 8 else 0)
        d_ebit = r.get("DIVIDA LIQUIDA / EBIT")
        if pd.notna(d_ebit):
            s += 20 if d_ebit <= 2.0 else (10 if d_ebit <= 3.5 else 0)
        return s

    df["SCORE"] = df.apply(calc_score, axis=1)

    # Magic Formula
    df_mf = df[(df["EV/EBIT"] > 0) & (df["ROIC"] > 0) & (df["LIQUIDEZ MEDIA DIARIA"] >= 100000)].copy()
    if not df_mf.empty:
        df_mf["MAGIC_SCORE"] = df_mf["EV/EBIT"].rank(ascending=True) + df_mf["ROIC"].rank(ascending=False)
        df["MAGIC_SCORE"] = df_mf["MAGIC_SCORE"]
    else:
        df["MAGIC_SCORE"] = 9999

    return df

# =========================================================================
# INTERFACE WEB
# =========================================================================
st.title("📊 Screener & Dashboard Fundamentalista B3")

# BARRA LATERAL (CONTROLES E UPLOAD)
st.sidebar.header("⚙️ Controles & Base")
file_uploaded = st.sidebar.file_uploader("Carregue o CSV do StatusInvest", type=["csv"])

preset = st.sidebar.selectbox(
    "Estratégia / Preset:",
    [
        "Todas as Ações",
        "⭐ Top Score Fundamentalista",
        "💰 Método Bazin (Proventos + Preço Teto)",
        "🛡️ Método Graham (Ações Baratas P/L + P/VP)",
        "🧙‍♂️ Magic Formula (Greenblatt)",
    ]
)

liq_min = st.sidebar.number_input("Liquidez Mínima Diária (R$):", value=200000, step=50000)

if file_uploaded is not None:
    try:
        try:
            df_raw = pd.read_csv(file_uploaded, sep=";", encoding="utf-8")
        except Exception:
            df_raw = pd.read_csv(file_uploaded, sep=";", encoding="latin1")

        df_raw = tratar_valores_numericos(df_raw)
        df_base = calcular_indicadores_avancados(df_raw)

        # Aplicação de Filtros
        df = df_base[df_base["LIQUIDEZ MEDIA DIARIA"].fillna(0) >= liq_min].copy()

        if "Top Score" in preset:
            df = df.sort_values(by="SCORE", ascending=False)
        elif "Bazin" in preset:
            df = df[(df["DY"] >= 6.0) & (df["PRECO"] <= df["BAZIN (VI)"])].sort_values(by="DY", ascending=False)
        elif "Graham" in preset:
            df = df[(df["P/L"] > 0) & (df["P/L"] <= 15) & (df["P/VP"] <= 1.5)].sort_values(by="SCORE", ascending=False)
        elif "Magic Formula" in preset:
            df = df[df["MAGIC_SCORE"] < 9000].sort_values(by="MAGIC_SCORE", ascending=True)
        else:
            df = df.sort_values(by="SCORE", ascending=False)

        # KPIS SUPERIORES
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        col_kpi1.metric("Total Filtradas", f"{len(df)} ações")
        col_kpi2.metric("Média Score", f"{df['SCORE'].mean():.1f} pts")
        col_kpi3.metric("Média DY", f"{df['DY'].mean():.2f}%")
        col_kpi4.metric("Média P/L", f"{df['P/L'].mean():.2f}")

        st.divider()

        # ABAS DO PAINEL
        tab1, tab2 = st.tabs(["📊 Screener & Tabela", "📈 Analytics & Raio-X"])

        with tab1:
            cols_exibir = ["TICKER", "SCORE", "PRECO", "DY", "P/L", "P/VP", "EV/EBIT", "ROE", "ROIC", "MARG. LIQUIDA"]
            st.dataframe(
                df[cols_exibir].style.format({
                    "SCORE": "{:.0f} pts",
                    "PRECO": "R$ {:.2f}",
                    "DY": "{:.2f}%",
                    "P/L": "{:.2f}",
                    "P/VP": "{:.2f}",
                    "EV/EBIT": "{:.2f}",
                    "ROE": "{:.2f}%",
                    "ROIC": "{:.2f}%",
                    "MARG. LIQUIDA": "{:.2f}%",
                }),
                use_container_width=True,
                height=500
            )

        with tab2:
            c_left, c_right = st.columns([1, 1])

            with c_left:
                st.subheader("Top 10 - Score Fundamentalista")
                top10 = df.head(10)
                fig_bar = px.bar(
                    top10, x="SCORE", y="TICKER", orientation="h",
                    color="SCORE", color_continuous_scale="Blues"
                )
                fig_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, template="plotly_dark")
                st.plotly_chart(fig_bar, use_container_width=True)

            with c_right:
                st.subheader("Eficiência (ROIC %) vs Valuation (EV/EBIT)")
                df_disp = df[(df["EV/EBIT"] > 0) & (df["EV/EBIT"] < 30) & (df["ROIC"] < 50)]
                fig_scatter = px.scatter(
                    df_disp, x="EV/EBIT", y="ROIC", hover_name="TICKER",
                    color="SCORE", color_continuous_scale="Viridis"
                )
                fig_scatter.update_layout(template="plotly_dark")
                st.plotly_chart(fig_scatter, use_container_width=True)

            st.divider()
            st.subheader("🔍 Raio-X Detalhado")
            ticker_sel = st.selectbox("Selecione um Ticker para analisar:", df["TICKER"].unique())
            row = df[df["TICKER"] == ticker_sel].iloc[0]

            r1, r2, r3 = st.columns(3)
            with r1:
                st.markdown(f"**Valuation:**\n- Score: `{row['SCORE']} pts`\n- P/L: `{row.get('P/L', '-')}`\n- P/VP: `{row.get('P/VP', '-')}`")
            with r2:
                st.markdown(f"**Proventos & Retorno:**\n- DY: `{row.get('DY', '-')}%`\n- ROE: `{row.get('ROE', '-')}%`\n- ROIC: `{row.get('ROIC', '-')}%`")
            with r3:
                graham = f"R$ {row['GRAHAM (VI)']:,.2f}" if pd.notna(row.get('GRAHAM (VI)')) else "-"
                bazin = f"R$ {row['BAZIN (VI)']:,.2f}" if pd.notna(row.get('BAZIN (VI)')) else "-"
                st.markdown(f"**Preços Teto / Intrínsecos:**\n- Graham: `{graham}`\n- Bazin (6%): `{bazin}`")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo CSV: {e}")
else:
    st.info("👈 Por favor, faça o upload do arquivo CSV do StatusInvest na barra lateral para começar.")
