import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import yfinance as yf

# ============================================================
# ALURA QUANT — LIGHT FINTECH UI (V5.5 CUSTOM HTML NAV)
# ============================================================
st.set_page_config(
    page_title="Alura Quant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ARCHIVO_HISTORIAL = "historial_alertas.csv"
ARCHIVO_UNIVERSO = "universo_activos.csv"

def obtener_total_activos():
    """Calcula dinámicamente el total de activos desde el CSV del universo."""
    if os.path.exists(ARCHIVO_UNIVERSO):
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(ARCHIVO_UNIVERSO, encoding=encoding)
                if not df.empty:
                    return len(df)
            except Exception:
                continue
    return 37

TOTAL_ACTIVOS_UNIVERSO = obtener_total_activos()

def render_html(content, **kwargs):
    """Renderiza HTML directamente y evita que Markdown rompa el marcado."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)

@st.cache_data(ttl=30)
def cargar_datos():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return pd.DataFrame()
    try:
        return pd.read_csv(ARCHIVO_HISTORIAL, on_bad_lines='skip', encoding='utf-8')
    except Exception:
        try:
            return pd.read_csv(ARCHIVO_HISTORIAL, on_bad_lines='skip', encoding='latin-1')
        except Exception:
            return pd.DataFrame()

@st.cache_data(ttl=300)
def obtener_precio_actual(ticker):
    """Consulta el último precio de cierre registrado para un ticker."""
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None

def formatear_tesis_ia(texto):
    """Limpia la tesis de la IA para que fluya de forma natural y elegante."""
    if not isinstance(texto, str):
        return "Sin análisis disponible."
    import re
    texto = texto.replace("Análisis técnico de", "").replace("Indicadores clave:", "")
    texto_html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', texto)
    return texto_html.strip()

# ============================================================
# DESIGN SYSTEM — PREMIUM FINTECH STYLING
# ============================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wgth@400;500;600&display=swap');

:root {
    --bg-app: #f8fafc;
    --card-bg: #ffffff;
    --border-subtle: #e2e8f0;
    --text-main: #0f172a;
    --text-muted: #64748b;
    --brand-blue: #2563eb;
    --brand-blue-hover: #1d4ed8;
    --brand-blue-light: #eff6ff;
    --success: #16a34a;
    --success-light: #f0fdf4;
    --danger: #dc2626;
    --danger-light: #fef2f2;
    --shadow-card: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
    --shadow-hover: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: var(--bg-app);
    color: var(--text-main);
}

#MainMenu, footer, section[data-testid="stSidebar"] {
    display: none !important;
}

.block-container {
    max-width: 1320px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* HEADER PRINCIPAL */
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 20px;
}
.brand-kicker {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--brand-blue);
    margin-bottom: 4px;
}
.main-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 26px;
    font-weight: 800;
    color: var(--text-main);
    letter-spacing: -0.03em;
    margin: 0;
}
.main-subtitle {
    font-size: 13px;
    color: var(--text-muted);
    margin-top: 2px;
}

/* KPI CARDS */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
}
.kpi-card {
    background: var(--card-bg);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    padding: 16px 20px;
    box-shadow: var(--shadow-card);
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 90px;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
    border-color: #cbd5e1;
}
.kpi-title {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-muted);
    margin-bottom: 4px;
    line-height: 1.3;
}
.kpi-val {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 30px;
    font-weight: 800;
    color: var(--text-main);
    letter-spacing: -0.03em;
    line-height: 1.1;
}

/* CARTERA / ASSET CARDS */
.asset-card {
    background: var(--card-bg);
    border: 1px solid var(--border-subtle);
    border-radius: 18px;
    padding: 24px;
    margin-bottom: 20px;
    box-shadow: var(--shadow-card);
    position: relative;
    transition: all 0.2s ease;
}
.asset-card:hover {
    box-shadow: var(--shadow-hover);
}
.asset-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid #f1f5f9;
}
.asset-info {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    flex: 1;
    min-width: 0;
}
.asset-icon-box {
    width: 44px;
    height: 44px;
    min-width: 44px;
    border-radius: 14px;
    background: var(--brand-blue-light);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
.asset-details-wrapper {
    flex: 1;
    min-width: 0;
}
.asset-name {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 16px;
    font-weight: 800;
    color: var(--text-main);
    display: flex;
    align-items: center;
    gap: 6px;
}
.asset-ticker-tag {
    color: var(--text-muted);
    font-weight: 600;
    font-size: 13px;
}
.asset-sector {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 2px;
}

/* BADGE DE NUEVO */
.badge-new {
    background: #dcfce7;
    color: #15803d;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 9px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 20px;
    display: inline-flex;
    align-items: center;
    gap: 3px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    margin-bottom: 4px;
}

.price-display {
    text-align: right;
    min-width: 90px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
}
.price-val-big {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 19px;
    font-weight: 800;
    color: var(--brand-blue);
    white-space: nowrap;
}
.price-lbl-small {
    font-size: 10px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}

/* PARAMS GRID */
.params-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}
.param-box {
    background: #f8fafc;
    border: 1px solid #f1f5f9;
    border-radius: 12px;
    padding: 12px 14px;
}
.param-lbl {
    font-size: 10px;
    font-weight: 800;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.param-val {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 15px;
    font-weight: 800;
    color: var(--text-main);
    margin-top: 4px;
}

/* AI INSIGHT BOX */
.ai-comment-box {
    background: #f8fafc;
    border-left: 3px solid var(--brand-blue);
    border-radius: 0 12px 12px 0;
    padding: 14px 16px;
    font-size: 13px;
    line-height: 1.6;
    color: #334155;
}

/* ESTILOS PARA LOS BOTONES DE NAVEGACIÓN SUPERIOR */
div[data-testid="stHorizontalBlock"] > div {
    display: flex;
    align-items: center;
}
div.stButton > button {
    width: 100%;
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    height: 42px !important;
    transition: all 0.2s ease !important;
}

/* FOOTER */
.app-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 48px;
    padding-top: 20px;
    border-top: 1px solid var(--border-subtle);
    color: #94a3b8;
    font-size: 11px;
    font-weight: 500;
}

/* MEDIA QUERIES PARA MÓVILES */
@media (max-width: 900px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); gap: 12px; }
    .params-grid { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .block-container { padding-top: 1rem; padding-left: 1rem; padding-right: 1rem; }
}

@media (max-width: 480px) {
    .kpi-val { font-size: 24px !important; }
    .asset-card { padding: 16px; }
    .price-val-big { font-size: 16px; }
    .asset-name { font-size: 15px; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# DATA PREPARATION & LOAD
# ============================================================
def preparar_fecha(df):
    df = df.copy()
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df

def contar_estado(df, texto):
    if "Estado" not in df.columns:
        return 0
    return int(df["Estado"].astype(str).str.contains(texto, na=False).sum())

df_hist = preparar_fecha(cargar_datos())

if df_hist.empty:
    total_alertas, exitos, fallos, activas, win_rate = 0, 0, 0, 0, 0.0
else:
    total_alertas = len(df_hist)
    exitos = contar_estado(df_hist, "OBJETIVO_CUMPLIDO")
    fallos = contar_estado(df_hist, "STOP_SALTADO")
    activas = contar_estado(df_hist, "ACTIVA")
    total_cerradas = exitos + fallos
    win_rate = (exitos / total_cerradas * 100) if total_cerradas else 0

# ============================================================
# CÁLCULO DE BENEFICIOS PARA KPIS
# ============================================================
capital_inicial = 10000.0
capital_por_alerta = 1000.0
beneficio_acumulado_kpi = 0.0

df_kpi_sim = df_hist.copy()
if "Fecha" in df_kpi_sim.columns and not df_kpi_sim.empty:
    df_kpi_sim = df_kpi_sim.dropna(subset=["Fecha"]).sort_values("Fecha")
    for _, row in df_kpi_sim.iterrows():
        estado_op = str(row.get("Estado", ""))
        p_ent = float(row["Precio_Alerta"]) if "Precio_Alerta" in row and pd.notna(row["Precio_Alerta"]) else 100.0
        p_sl = float(row["Stop_Loss"]) if "Stop_Loss" in row and pd.notna(row["Stop_Loss"]) else p_ent * 0.96
        p_tp = float(row["Take_Profit"]) if "Take_Profit" in row and pd.notna(row["Take_Profit"]) else p_ent * 1.10
        pct_g = (p_tp - p_ent) / p_ent if p_ent > 0 else 0.10
        pct_p = (p_ent - p_sl) / p_ent if p_ent > 0 else 0.04
        if "OBJETIVO_CUMPLIDO" in estado_op:
            beneficio_acumulado_kpi += capital_por_alerta * pct_g
        elif "STOP_SALTADO" in estado_op:
            beneficio_acumulado_kpi -= capital_por_alerta * pct_p

rentabilidad_kpi_pct = (beneficio_acumulado_kpi / capital_inicial * 100) if capital_inicial else 0
color_rentabilidad = "var(--success)" if beneficio_acumulado_kpi >= 0 else "var(--danger)"

# ============================================================
# HEADER & KPIS
# ============================================================
render_html(
    """
<div class="header-container">
    <div>
        <div class="brand-kicker">Alura Quant Intelligence</div>
        <h1 class="main-title">Tu Radar de Inversión</h1>
        <div class="main-subtitle">Señales cuantitativas, cartera y resultados</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

render_html(
    f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-title">Acciones monitoreadas</div>
        <div class="kpi-val">{TOTAL_ACTIVOS_UNIVERSO}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Señales</div>
        <div class="kpi-val">{total_alertas}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Objetivos Cumplidos</div>
        <div class="kpi-val">{exitos}</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-title">Beneficio</div>
        <div class="kpi-val" style="font-size: 21px;">{win_rate:.1f}% <span style="font-size: 12px; font-weight: 700; color: {color_rentabilidad}; display:inline-block; margin-top:2px;">({beneficio_acumulado_kpi:+,.0f} € / {rentabilidad_kpi_pct:+.1f}%)</span></div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

if df_hist.empty:
    st.info("No se encontraron registros en el historial de alertas.")
    st.stop()

# ============================================================
# GESTIÓN DE ESTADO PARA LA NAVEGACIÓN LIMPIA
# ============================================================
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "Cartera"

# Barra superior con botones limpios tipo pestaba de software profesional
col_nav1, col_nav2, col_nav3, col_nav_space = st.columns([1.2, 1.2, 1.2, 4])

with col_nav1:
    btn_cartera = st.button("💼 Cartera", use_container_width=True, type="primary" if st.session_state.seccion_activa == "Cartera" else "secondary")
with col_nav2:
    btn_resultados = st.button("📊 Resultados", use_container_width=True, type="primary" if st.session_state.seccion_activa == "Resultados" else "secondary")
with col_nav3:
    btn_historico = st.button("📜 Histórico", use_container_width=True, type="primary" if st.session_state.seccion_activa == "Histórico" else "secondary")

if btn_cartera:
    st.session_state.seccion_activa = "Cartera"
    st.rerun()
elif btn_resultados:
    st.session_state.seccion_activa = "Resultados"
    st.rerun()
elif btn_historico:
    st.session_state.seccion_activa = "Histórico"
    st.rerun()

st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)

# ============================================================
# 1. SECCIÓN CARTERA
# ============================================================
if st.session_state.seccion_activa == "Cartera":
    df_activas = df_hist[
        df_hist["Estado"].astype(str).str.contains("ACTIVA", na=False)
    ].copy()

    if df_activas.empty:
        st.info("No hay posiciones activas en la cartera en este momento.")
    else:
        col_filtro_1, col_filtro_2 = st.columns([2, 2])
        with col_filtro_1:
            sectores_disponibles = ["Todos los sectores"] + sorted(df_activas["Sector"].dropna().unique().tolist()) if "Sector" in df_activas.columns else ["Todos los sectores"]
            filtro_sector = st.selectbox("Filtrar por sector", sectores_disponibles, label_visibility="collapsed")
        with col_filtro_2:
            busqueda_cartera = st.text_input("Buscar en cartera", placeholder="🔍 Filtrar por nombre o ticker...", label_visibility="collapsed")

        df_filtrada = df_activas.copy()
        if filtro_sector != "Todos los sectores":
            df_filtrada = df_filtrada[df_filtrada["Sector"] == filtro_sector]
        if busqueda_cartera:
            mask = df_filtrada.astype(str).apply(lambda col: col.str.contains(busqueda_cartera, case=False, na=False)).any(axis=1)
            df_filtrada = df_filtrada[mask]

        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

        for _, row in df_filtrada.iterrows():
            icono = row.get("Icono", "📈") if pd.notna(row.get("Icono")) else "📈"
            empresa = row.get("Empresa", row.get("Ticker", "Activo"))
            ticker = row.get("Ticker", "")
            sector = row.get("Sector", "Mercado Continuo")
            
            es_nuevo = False
            if "Fecha" in row and pd.notna(row["Fecha"]):
                try:
                    delta_tiempo = datetime.now() - row["Fecha"].to_pydatetime().replace(tzinfo=None)
                    if delta_tiempo <= timedelta(hours=48):
                        es_nuevo = True
                except Exception:
                    pass

            badge_nuevo_html = '<span class="badge-new">✨ NUEVO</span>' if es_nuevo else ''

            precio_actual_val = obtener_precio_actual(ticker)
            precio_actual_str = f"{precio_actual_val:.2f} €" if precio_actual_val else "—"

            precio_ent = f"{row['Precio_Alerta']:.2f} €" if "Precio_Alerta" in row and pd.notna(row["Precio_Alerta"]) else "—"
            stop_loss = f"{row['Stop_Loss']:.2f} €" if "Stop_Loss" in row and pd.notna(row["Stop_Loss"]) else "—"
            take_profit = f"{row['Take_Profit']:.2f} €" if "Take_Profit" in row and pd.notna(row["Take_Profit"]) else "—"
            ratio_rr = f"{row['Ratio_RR']:.1f}x" if "Ratio_RR" in row and pd.notna(row["Ratio_RR"]) else "—"

            analisis_ia = formatear_tesis_ia(row.get("Analisis_IA", ""))

            render_html(
                f"""
            <div class="asset-card">
                <div class="asset-top">
                    <div class="asset-info">
                        <div class="asset-icon-box">{icono}</div>
                        <div class="asset-details-wrapper">
                            <div class="asset-name">{empresa} <span class="asset-ticker-tag">({ticker})</span></div>
                            <div class="asset-sector">{sector}</div>
                        </div>
                    </div>
                    <div class="price-display">
                        {badge_nuevo_html}
                        <div class="price-val-big">{precio_actual_str}</div>
                        <div class="price-lbl-small">Precio Actual</div>
                    </div>
                </div>
                
                <div class="params-grid">
                    <div class="param-box">
                        <div class="param-lbl">Precio Entrada</div>
                        <div class="param-val">{precio_ent}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-lbl">Stop Loss</div>
                        <div class="param-val" style="color: var(--danger);">{stop_loss}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-lbl">Take Profit</div>
                        <div class="param-val" style="color: var(--success);">{take_profit}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-lbl">Ratio Risk/Reward</div>
                        <div class="param-val" style="color: var(--brand-blue);">{ratio_rr}</div>
                    </div>
                </div>
                
                <div class="ai-comment-box">
                    <strong style="color: var(--brand-blue); display:block; margin-bottom:4px; font-size:11px; text-transform:uppercase; letter-spacing:0.05em;">
                        💡 Tesis del Analista Cuantitativo
                    </strong>
                    {analisis_ia}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

# ============================================================
# 2. SECCIÓN RESULTADOS
# ============================================================
elif st.session_state.seccion_activa == "Resultados":
    col_g1, col_g2 = st.columns([1.3, 0.7], gap="large")

    capital_inicial = 10000.0
    capital_por_alerta = 1000.0
    beneficio_acumulado = 0.0
    fechas_curva, beneficios_curva = [], []

    df_sim = df_hist.copy()
    if "Fecha" in df_sim.columns:
        df_sim = df_sim.dropna(subset=["Fecha"]).sort_values("Fecha")
        df_sim["Fecha_Dia"] = df_sim["Fecha"].dt.strftime("%Y-%m-%d")

        for _, grupo in df_sim.groupby("Fecha_Dia"):
            beneficio_dia = 0.0
            for _, row in grupo.iterrows():
                estado_op = str(row.get("Estado", ""))
                p_ent = float(row["Precio_Alerta"]) if "Precio_Alerta" in row and pd.notna(row["Precio_Alerta"]) else 100.0
                p_sl = float(row["Stop_Loss"]) if "Stop_Loss" in row and pd.notna(row["Stop_Loss"]) else p_ent * 0.96
                p_tp = float(row["Take_Profit"]) if "Take_Profit" in row and pd.notna(row["Take_Profit"]) else p_ent * 1.10

                pct_g = (p_tp - p_ent) / p_ent if p_ent > 0 else 0.10
                pct_p = (p_ent - p_sl) / p_ent if p_ent > 0 else 0.04

                if "OBJETIVO_CUMPLIDO" in estado_op:
                    beneficio_dia += capital_por_alerta * pct_g
                elif "STOP_SALTADO" in estado_op:
                    beneficio_dia -= capital_por_alerta * pct_p

            beneficio_acumulado += beneficio_dia
            fechas_curva.append(grupo["Fecha_Dia"].iloc[0])
            beneficios_curva.append(beneficio_acumulado)

    rentabilidad_pct = (beneficio_acumulado / capital_inicial * 100) if capital_inicial else 0

    with col_g1:
        color_rent = "var(--success)" if beneficio_acumulado >= 0 else "var(--danger)"
        render_html(
            f"""
        <div class="asset-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 16px;">
                <div>
                    <div style="font-family:'Plus Jakarta Sans'; font-size:16px; font-weight:800; color:var(--text-main);">Evolución de Beneficios (€)</div>
                    <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Curva de rendimiento histórico simulado</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:'Plus Jakarta Sans'; font-size:22px; font-weight:800; color:{color_rent};">
                        {beneficio_acumulado:+,.2f} €
                    </div>
                    <div style="font-size:11px; color:var(--text-muted); font-weight:700;">
                        {rentabilidad_pct:+.2f}% de retorno
                    </div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if fechas_curva:
            df_beneficio = pd.DataFrame({"Beneficio Neto (€)": beneficios_curva}, index=fechas_curva)
            st.line_chart(df_beneficio, height=300)
        else:
            st.info("Se requieren más puntos en el histórico para trazar la gráfica.")

    with col_g2:
        render_html(
            f"""
        <div class="asset-card">
            <div style="font-family:'Plus Jakarta Sans'; font-size:16px; font-weight:800; color:var(--text-main); margin-bottom: 14px;">Métricas Clave</div>
            <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #f1f5f9;">
                <span style="color:var(--text-muted); font-size:13px; font-weight:600;">Señales activas</span>
                <strong style="color:var(--brand-blue); font-size:14px;">{activas}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #f1f5f9;">
                <span style="color:var(--text-muted); font-size:13px; font-weight:600;">Take Profit alcanzado</span>
                <strong style="color:var(--success); font-size:14px;">{exitos}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #f1f5f9;">
                <span style="color:var(--text-muted); font-size:13px; font-weight:600;">Stop Loss saltado</span>
                <strong style="color:var(--danger); font-size:14px;">{fallos}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding:12px 0 4px;">
                <span style="color:var(--text-muted); font-size:13px; font-weight:600;">Efectividad (Win Rate)</span>
                <strong style="color:var(--text-main); font-size:14px;">{win_rate:.1f}%</strong>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ============================================================
# 3. SECCIÓN HISTÓRICO
# ============================================================
elif st.session_state.seccion_activa == "Histórico":
    render_html(
        """
        <div class="asset-card" style="margin-bottom: 16px;">
            <div style="font-family:'Plus Jakarta Sans'; font-size:16px; font-weight:800; color:var(--text-main);">Registro Histórico General</div>
            <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">Auditoría completa de todas las señales emitidas por el sistema cuantitativo.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    df_cerradas = df_hist.copy()
    if not df_cerradas.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            estados_posibles = sorted(df_cerradas["Estado"].astype(str).unique().tolist())
            filtro_est = st.multiselect("Filtrar por estado operativo", estados_posibles, default=estados_posibles)
        with col_f2:
            busq_hist = st.text_input("Búsqueda general en histórico", placeholder="Escribe para buscar...")

        df_view = df_cerradas.copy()
        if filtro_est:
            df_view = df_view[df_view["Estado"].astype(str).isin(filtro_est)]
        if busq_hist:
            mask_h = df_view.astype(str).apply(lambda col: col.str.contains(busq_hist, case=False, na=False)).any(axis=1)
            df_view = df_view[mask_h]

        st.dataframe(df_view, use_container_width=True, height=450, hide_index=True)
    else:
        st.info("No hay registros en el histórico.")

# ============================================================
# FOOTER
# ============================================================
render_html(
    """
<div class="app-footer">
    <span>ALURA QUANT · INSTITUTIONAL INVESTMENT PLATFORM</span>
    <span>Simulación cuantitativa automatizada · Uso exclusivo interno</span>
</div>
""",
    unsafe_allow_html=True,
)