import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da Página no Streamlit
st.set_page_config(
    page_title="Dashboard Fundamentalista B3",
    page_icon="📊",
    layout="wide"
)

# Estilização Customizada Dark
st.markdown("""
    <style>
        .main { background-color: #1e1e1e; }
        .stMetric { background-color: #252526; padding: 10px; border-radius: 5px; }
        .stButton>button { background-color: #007acc; color: white; border-radius: 5px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FUNÇÕES DE TRATAMENTO E PROCESSAMENTO
# -----------------------------------------------------------------------------
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
        lambda r: (22.5 * r["LPA"] * r["VPA"])**0.5 if pd.notna(r.get("LPA")) and pd.notna(r.get("VPA")) and r["LPA"] > 0 and r["VPA"] > 0 else None, axis=1
    )
    # Bazin: DPA / 0.06
    df["BAZIN (VI)"] = df.apply(
        lambda r: (r["PRECO"] * (r["DY"] / 100.0)) / 0.06 if pd.notna(r.get("PRECO")) and pd.notna(r.get("DY")) and r["DY"] > 0 else None, axis=1
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

    # Magic Formula Rank
    df_mf = df[(df["EV/EBIT"] > 0) & (df["ROIC"] > 0) & (df["LIQUIDEZ MEDIA DIARIA"] >= 100000)].copy()
    if not df_mf.empty:
        df_mf["MAGIC_SCORE"] = df_mf["EV/EBIT"].rank(ascending=True) + df_mf["ROIC"].rank(ascending=False)
