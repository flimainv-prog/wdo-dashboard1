# app.py
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Dashboard WDO Macro", layout="wide")

brt = pytz.timezone("America/Sao_Paulo")

@st.cache_data(ttl=300)
def fetch_data(ticker, period="30d", interval="5m"):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
        if data.empty:
            return pd.DataFrame()
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        data.index = data.index.tz_convert(brt) if data.index.tz is None else data.index.tz_convert(brt)
        return data
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_vix():
    try:
        vix = fetch_data("^VIX", period="2d", interval="1h")
        if vix.empty:
            return None
        return float(vix["Close"].dropna().iloc[-1])
    except:
        return None

def calcular_linha_azul(usdmxn, dxy, vix):
    if usdmxn.empty or dxy.empty or vix.empty:
        return pd.Series(dtype=float)
    
    try:
        usdmxn_norm = (usdmxn - usdmxn.mean()) / usdmxn.std()
        dxy_norm = (dxy - dxy.mean()) / dxy.std()
        vix_norm = (vix - vix.mean()) / vix.std()
        
        linha_azul = (usdmxn_norm * 0.5 + dxy_norm * 0.3 + vix_norm * 0.2)
        linha_azul = linha_azul.ewm(span=20, adjust=False).mean()
        
        return linha_azul * 100
    except:
        return pd.Series(dtype=float)

st.title("🟢🔴 Dashboard WDO Macro")

col1, col2 = st.columns([3, 1])

with col2:
    end_date = datetime.now(brt).date()
    opcoes_dias = [(end_date - timedelta(days=i)) for i in range(30)]
    target_date = st.selectbox("📅 Data:", opcoes_dias, format_func=lambda d: d.strftime("%d/%m/%y"), index=1)
    
    hora_inicio = st.selectbox("🕐 Hora:", list(range(0, 24)), format_func=lambda h: f"{h:02d}:00", index=9)

vix_atual = get_vix()
if vix_atual:
    regime = "🟢 Calmo" if vix_atual < 15 else "🟡 Normal" if vix_atual < 20 else "🟠 Moderado" if vix_atual < 25 else "🔴 Alto" if vix_atual < 30 else "🚨 Extremo"
    st.sidebar.info(f"📊 VIX: **{vix_atual:.1f}** — {regime}")

with st.spinner("Carregando dados..."):
    usdmxn = fetch_data("USDMXN=X", period="30d", interval="5m")
    dxy = fetch_data("DX-Y.NYB", period="30d", interval="5m")
    vix = fetch_data("^VIX", period="30d", interval="1h")
    
    if not usdmxn.empty and not dxy.empty and not vix.empty:
        usdmxn_target = usdmxn[usdmxn.index.date == target_date]["Close"]
        dxy_target = dxy[dxy.index.date == target_date]["Close"]
        vix_target = vix[vix.index.date == target_date]["Close"]
        
        if not usdmxn_target.empty and not dxy_target.empty and not vix_target.empty:
            linha_azul = calcular_linha_azul(usdmxn_target, dxy_target, vix_target)
            
            hora_filtro = pd.Timestamp(f"{target_date} {hora_inicio:02d}:00", tz=brt)
            linha_azul = linha_azul[linha_azul.index >= hora_filtro]
            
            if not linha_azul.empty:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=linha_azul.index,
                    y=linha_azul.values,
                    mode="lines",
                    name="🔵 Aceleração",
                    line=dict(color="#0066FF", width=3),
                    fill="tozeroy",
                    fillcolor="rgba(0, 102, 255, 0.2)"
                ))
                
                fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                
                fig.update_layout(
                    title=f"📈 Dashboard WDO Macro | {target_date.strftime('%d/%m/%Y')} | a partir das {hora_inicio:02d}:00",
                    height=600,
                    xaxis_title="Hora",
                    yaxis_title="Aceleração (pts)",
                    template="plotly_white",
                    hovermode="x unified",
                    margin=dict(l=20, r=20, t=50, b=20)
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info(f"🔵 Aceleração Atual: **{linha_azul.iloc[-1]:+.0f} pts**")
            else:
                st.warning("⚠️ Sem dados para este horário.")
        else:
            st.warning("⚠️ Sem dados para esta data.")
    else:
        st.warning("⚠️ Erro ao carregar dados.")
