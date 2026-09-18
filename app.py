import os
from datetime import datetime
import pandas as pd
import streamlit as st
# ============================================================
# ALURA QUANT — LIGHT FINTECH UI
# Inspired by modern digital banking / investment products
# ============================================================
st.set_page_config(
    page_title="Alura Quant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)
ARCHIVO_HISTORIAL = "historial_alertas.csv"
TOTAL_ACTIVOS_UNIVERSO = 36


def render_html(content, **kwargs):
    """Renderiza HTML directamente y evita que Markdown rompa el marcado."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)
# ============================================================
# DESIGN SYSTEM — LIGHT / PREMIUM
# ============================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
:root {
    --bg: #f4f8fc;
    --surface: #ffffff;
    --surface-soft: #f8fbff;
    --border: #e6edf5;
    --text: #172033;
    --muted: #718096;
    --muted-2: #9aa7b8;
    --blue: #1557e8;
    --blue-dark: #0e43bd;
    --blue-soft: #eaf1ff;
    --green: #149447;
    --green-soft: #eaf8f0;
    --red: #d94343;
    --red-soft: #fff0f0;
    --yellow: #b77908;
    --yellow-soft: #fff7df;
    --shadow: 0 8px 28px rgba(35, 61, 95, .07);
}
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}
.stApp {
    background:
        radial-gradient(circle at 88% 0%, rgba(21,87,232,.045), transparent 26%),
        var(--bg);
    color: var(--text);
}
#MainMenu, footer, header {
    visibility: hidden;
}
.block-container {
    max-width: 1380px;
    padding-top: 0.8rem;
    padding-bottom: 3.5rem;
}
/* ============================================================
   TOP NAVIGATION
   ============================================================ */
.navbar {
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0 -1rem 28px -1rem;
    padding: 0 28px;
    background: rgba(255,255,255,.94);
    border-bottom: 1px solid var(--border);
    backdrop-filter: blur(12px);
}
.logo {
    display: flex;
    align-items: center;
    gap: 10px;
    min-width: 190px;
}
.logo-mark {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    background: linear-gradient(135deg, #1557e8, #4f7ff0);
    font-family: 'Plus Jakarta Sans';
    font-weight: 800;
    box-shadow: 0 7px 18px rgba(21,87,232,.20);
}
.logo-name {
    font-family: 'Plus Jakarta Sans';
    font-weight: 800;
    font-size: 18px;
    letter-spacing: -.04em;
    color: #182033;
}
.logo-sub {
    color: #8b97a8;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .09em;
    text-transform: uppercase;
}
.nav-copy {
    color: #5f6d80;
    font-size: 13px;
    font-weight: 600;
}
/* ============================================================
   PAGE TITLE
   ============================================================ */
.page-head {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 20px;
}
.page-kicker {
    color: var(--blue);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .12em;
    font-weight: 800;
    margin-bottom: 6px;
}
.page-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 30px;
    line-height: 1.12;
    letter-spacing: -.045em;
    color: #151c2b;
    margin: 0;
}
.page-description {
    color: var(--muted);
    font-size: 13px;
    margin-top: 6px;
}
/* ============================================================
   KPI CARDS
   ============================================================ */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 12px;
    margin-bottom: 22px;
}
.kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 17px;
    padding: 18px 19px;
    box-shadow: var(--shadow);
    transition: .2s ease;
}
.kpi:hover {
    transform: translateY(-2px);
    box-shadow: 0 13px 34px rgba(35,61,95,.10);
    border-color: #d6e2f1;
}
.kpi-label {
    color: #8793a4;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: .08em;
    text-transform: uppercase;
}
.kpi-value {
    color: #172033;
    font-family: 'Plus Jakarta Sans';
    font-size: 25px;
    font-weight: 800;
    letter-spacing: -.045em;
    margin-top: 8px;
}
.kpi-caption {
    color: #9aa6b6;
    font-size: 10px;
    margin-top: 4px;
}
/* ============================================================
   CARDS
   ============================================================ */
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 19px;
    padding: 21px;
    margin-bottom: 15px;
    box-shadow: var(--shadow);
}
.card-title {
    color: #182033;
    font-family: 'Plus Jakarta Sans';
    font-size: 15px;
    font-weight: 800;
    letter-spacing: -.02em;
}
.card-subtitle {
    color: var(--muted);
    font-size: 11px;
    margin-top: 4px;
}
/* ============================================================
   SIGNAL ROWS
   ============================================================ */
.signal {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    padding: 13px 0;
    border-bottom: 1px solid #edf1f6;
}
.signal:last-child {
    border-bottom: 0;
    padding-bottom: 0;
}
.signal-main {
    display: flex;
    align-items: center;
    gap: 11px;
}
.signal-icon {
    width: 36px;
    height: 36px;
    border-radius: 11px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    font-weight: 800;
}
.signal-icon.active {
    color: #2164db;
    background: #eaf1ff;
}
.signal-icon.win {
    color: #138848;
    background: #eaf8f0;
}
.signal-icon.loss {
    color: #cf4040;
    background: #fff0f0;
}
.signal-name {
    color: #20293a;
    font-size: 12px;
    font-weight: 800;
}
.signal-detail {
    color: #909cac;
    font-size: 10px;
    margin-top: 3px;
}
.signal-badge {
    border-radius: 7px;
    padding: 5px 8px;
    font-size: 9px;
    font-weight: 800;
}
/* ============================================================
   STATUS / INFO
   ============================================================ */
.info-strip {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 12px;
    background: var(--blue-soft);
    color: #3f5f98;
    font-size: 11px;
    line-height: 1.5;
    margin-bottom: 15px;
}
.status-live {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    color: #147f43;
    background: #effaf4;
    border: 1px solid #d8f0e2;
    border-radius: 999px;
    padding: 7px 11px;
    font-size: 10px;
    font-weight: 800;
}
.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #18a957;
}
/* ============================================================
   TABS — TOP MENU
   ============================================================ */
.stTabs {
    margin-top: 4px;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
    background: transparent;
    border-bottom: 1px solid #e3eaf3;
    padding: 0;
    margin-bottom: 22px;
}
.stTabs [data-baseweb="tab"] {
    color: #7a8798;
    background: transparent;
    border: 0;
    border-radius: 0;
    font-size: 12px;
    font-weight: 700;
    padding: 10px 16px 12px;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #1c2a40;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--blue) !important;
    background: transparent !important;
    border-bottom: 2px solid var(--blue) !important;
}
/* ============================================================
   STREAMLIT BUTTONS / INPUTS
   ============================================================ */
.stButton > button {
    min-height: 39px;
    border-radius: 10px;
    border: 1px solid #dce5f0;
    background: white;
    color: #1c2b40;
    font-size: 11px;
    font-weight: 800;
    box-shadow: 0 2px 7px rgba(30,50,80,.04);
}
.stButton > button:hover {
    color: var(--blue);
    border-color: #b9cef0;
    background: #f7faff;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 15px;
    overflow: hidden;
    box-shadow: var(--shadow);
}
[data-baseweb="input"] {
    border-radius: 10px !important;
}
.stNumberInput label,
.stTextInput label,
.stMultiSelect label {
    color: #68768a !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    text-transform: uppercase;
    letter-spacing: .06em;
}
.stCaption {
    color: #98a4b4;
}
/* ============================================================
   EMPTY STATE
   ============================================================ */
.empty-state {
    background: white;
    border: 1px dashed #d8e2ed;
    border-radius: 20px;
    padding: 55px 20px;
    text-align: center;
    box-shadow: var(--shadow);
}
.empty-icon {
    width: 48px;
    height: 48px;
    margin: 0 auto 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 15px;
    color: var(--blue);
    background: var(--blue-soft);
    font-size: 21px;
    font-weight: 800;
}
.empty-title {
    color: #20293a;
    font-family: 'Plus Jakarta Sans';
    font-size: 15px;
    font-weight: 800;
}
.empty-text {
    max-width: 450px;
    margin: 7px auto 0;
    color: #8793a4;
    font-size: 11px;
    line-height: 1.65;
}
/* ============================================================
   SIDEBAR
   ============================================================ */
section[data-testid="stSidebar"] {
    background: #fff;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1.8rem;
}
/* ============================================================
   FOOTER
   ============================================================ */
.footer {
    display: flex;
    justify-content: space-between;
    gap: 20px;
    margin-top: 34px;
    padding-top: 16px;
    border-top: 1px solid #e3eaf3;
    color: #a0aab8;
    font-size: 9px;
}
/* ============================================================
   RESPONSIVE
   ============================================================ */
@media (max-width: 900px) {
    .kpi-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .navbar {
        padding: 0 15px;
    }
    .nav-copy {
        display: none;
    }
}
@media (max-width: 600px) {
    .kpi-grid {
        grid-template-columns: 1fr;
    }
    .page-title {
        font-size: 25px;
    }
    .navbar {
        margin-left: -0.5rem;
        margin-right: -0.5rem;
    }
}
</style>
""",
    unsafe_allow_html=True,
)
# ============================================================
# DATA
# ============================================================
@st.cache_data(ttl=30)
def cargar_datos():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return pd.DataFrame()
    try:
        return pd.read_csv(ARCHIVO_HISTORIAL)
    except Exception as exc:
        st.error(f"No se pudo leer el histórico: {exc}")
        return pd.DataFrame()
def preparar_fecha(df):
    df = df.copy()
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df
def contar_estado(df, texto):
    if "Estado" not in df.columns:
        return 0
    return int(
        df["Estado"]
        .astype(str)
        .str.contains(texto, na=False)
        .sum()
    )
def estado_visual(estado):
    estado = str(estado).upper()
    if "OBJETIVO_CUMPLIDO" in estado:
        return "win", "✓", "OBJETIVO"
    if "STOP_SALTADO" in estado:
        return "loss", "↓", "STOP"
    if "ACTIVA" in estado:
        return "active", "↗", "ACTIVA"
    return "active", "•", estado[:18]
def detectar_columna(df, candidatos):
    for col in candidatos:
        if col in df.columns:
            return col
    return None
# ============================================================
# LOAD
# ============================================================
df_hist = preparar_fecha(cargar_datos())
if df_hist.empty:
    total_alertas = 0
    exitos = 0
    fallos = 0
    activas = 0
    win_rate = 0
else:
    total_alertas = len(df_hist)
    exitos = contar_estado(df_hist, "OBJETIVO_CUMPLIDO")
    fallos = contar_estado(df_hist, "STOP_SALTADO")
    activas = contar_estado(df_hist, "ACTIVA")
    total_cerradas = exitos + fallos
    win_rate = (exitos / total_cerradas * 100) if total_cerradas else 0
# ============================================================
# TOP NAV
# ============================================================
render_html(
    f"""
<div class="navbar">
    <div class="logo">
        <div class="logo-mark">A</div>
        <div>
            <div class="logo-name">alura</div>
            <div class="logo-sub">quant intelligence</div>
        </div>
    </div>
    <div class="nav-copy">
        Investment intelligence · Mercado Continuo
    </div>
    <div class="status-live">
        <span class="status-dot"></span>
        SISTEMA ACTIVO
    </div>
</div>
""",
    unsafe_allow_html=True,
)
# ============================================================
# SIDEBAR — SIMULATION CONTROLS
# ============================================================
with st.sidebar:
    st.markdown("### Simulación")
    st.caption("Ajusta el escenario sin modificar tus datos.")
    capital_inicial = st.number_input(
        "Capital inicial (€)",
        min_value=1000.0,
        value=10000.0,
        step=1000.0,
        format="%.0f",
    )
    capital_por_alerta = st.number_input(
        "Capital por alerta (€)",
        min_value=100.0,
        value=1000.0,
        step=100.0,
        format="%.0f",
    )
    take_profit = st.number_input(
        "Take profit (%)",
        min_value=0.0,
        max_value=100.0,
        value=10.0,
        step=0.5,
        format="%.1f",
    )
    stop_loss = st.number_input(
        "Stop loss (%)",
        min_value=0.0,
        max_value=100.0,
        value=4.0,
        step=0.5,
        format="%.1f",
    )
    st.divider()
    if st.button("↻ Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.caption(
        "Simulación hipotética. No constituye asesoramiento ni recomendación de inversión."
    )
# ============================================================
# PAGE HEADER — WITHOUT THE OLD GIANT HERO
# ============================================================
render_html(
    """
<div class="page-head">
    <div>
        <div class="page-kicker">Investment dashboard</div>
        <h1 class="page-title">Tu radar de inversión</h1>
        <div class="page-description">
            Señales cuantitativas, cartera y resultados en un solo lugar.
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)
# ============================================================
# KPI STRIP
# ============================================================
render_html(
    f"""
<div class="kpi-grid">
    <div class="kpi">
        <div class="kpi-label">Universo</div>
        <div class="kpi-value">{TOTAL_ACTIVOS_UNIVERSO}</div>
        <div class="kpi-caption">activos monitorizados</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Alertas</div>
        <div class="kpi-value">{total_alertas}</div>
        <div class="kpi-caption">señales registradas</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">En radar</div>
        <div class="kpi-value">{activas}</div>
        <div class="kpi-caption">señales activas</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Objetivos</div>
        <div class="kpi-value">{exitos}</div>
        <div class="kpi-caption">operaciones positivas</div>
    </div>
    <div class="kpi">
        <div class="kpi-label">Win rate</div>
        <div class="kpi-value">{win_rate:.1f}%</div>
        <div class="kpi-caption">operaciones cerradas</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)
# ============================================================
# EMPTY
# ============================================================
if df_hist.empty:
    render_html(
        """
<div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">Tu radar todavía está vacío</div>
    <div class="empty-text">
        Ejecuta el escáner cuantitativo para empezar a recibir señales.
        Cuando haya actividad, aquí aparecerán el radar, el histórico
        y la simulación de cartera.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()
# ============================================================
# TOP MENU / CONTENT
# ============================================================
tab_resumen, tab_cartera, tab_activas, tab_historial = st.tabs(
    [
        "Resumen",
        "Cartera",
        "Alertas",
        "Histórico",
    ]
)
# ============================================================
# RESUMEN
# ============================================================
with tab_resumen:
    col_left, col_right = st.columns([1.2, .8], gap="large")
    with col_left:
        render_html(
            """
<div class="card">
    <div class="card-title">Cómo está funcionando la estrategia</div>
    <div class="card-subtitle">
        Una lectura rápida antes de entrar al detalle.
    </div>
    <div style="
        margin-top:17px;
        color:#68768a;
        font-size:12px;
        line-height:1.75;
    ">
        El modelo evalúa el Mercado Continuo Español mediante una combinación
        de fortaleza tendencial (EMA 50), momento de volumen relativo y
        control de sobrecompra mediante RSI.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
        df_recent = df_hist.copy()
        if "Fecha" in df_recent.columns:
            df_recent = df_recent.sort_values("Fecha", ascending=False)
        df_recent = df_recent.head(6)
        col_asset = detectar_columna(
            df_recent,
            ["Ticker", "Símbolo", "Simbolo", "Activo", "Nombre", "Valor"],
        )
        rows_html = []
        for _, row in df_recent.iterrows():
            estado = row.get("Estado", "—")
            tipo, icono, label = estado_visual(estado)
            activo = row.get(col_asset, "Activo") if col_asset else "Activo"
            fecha = row.get("Fecha", "")
            fecha_txt = fecha.strftime("%d %b %Y") if isinstance(fecha, pd.Timestamp) else str(fecha)[:16]
            badge_style = {
                "active": "background:#eaf1ff;color:#2164db;",
                "win": "background:#eaf8f0;color:#138848;",
                "loss": "background:#fff0f0;color:#cf4040;",
            }[tipo]
            rows_html.append(f"""<div class="signal"><div class="signal-main"><div class="signal-icon {tipo}">{icono}</div><div><div class="signal-name">{activo}</div><div class="signal-detail">{fecha_txt}</div></div></div><div class="signal-badge" style="{badge_style}">{label}</div></div>""")

        render_html(
            """
<div class="card">
    <div class="card-title">Últimas señales</div>
    <div class="card-subtitle">Lo último que ha detectado el motor.</div>
"""
            + "".join(rows_html)
            + "</div>",
        )
    with col_right:
        render_html(
            """
<div class="card">
    <div class="card-title">Distribución de resultados</div>
    <div class="card-subtitle">
        Estado actual del histórico.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
        chart_data = pd.DataFrame(
            {
                "Estado": [
                    "Objetivos",
                    "Stops",
                    "Activas",
                ],
                "Cantidad": [
                    exitos,
                    fallos,
                    activas,
                ],
            }
        ).set_index("Estado")
        st.bar_chart(
            chart_data,
            height=270,
        )
        render_html(
            f"""
<div class="card">
    <div class="card-title">Snapshot</div>
    <div style="
        display:flex;
        justify-content:space-between;
        padding:11px 0;
        border-bottom:1px solid #edf1f6;
    ">
        <span style="color:#8793a4;font-size:11px;">
            Señales activas
        </span>
        <strong style="color:#2164db;">
            {activas}
        </strong>
    </div>
    <div style="
        display:flex;
        justify-content:space-between;
        padding:11px 0;
        border-bottom:1px solid #edf1f6;
    ">
        <span style="color:#8793a4;font-size:11px;">
            Objetivos
        </span>
        <strong style="color:#138848;">
            {exitos}
        </strong>
    </div>
    <div style="
        display:flex;
        justify-content:space-between;
        padding:11px 0;
        border-bottom:1px solid #edf1f6;
    ">
        <span style="color:#8793a4;font-size:11px;">
            Stops
        </span>
        <strong style="color:#cf4040;">
            {fallos}
        </strong>
    </div>
    <div style="
        display:flex;
        justify-content:space-between;
        padding:11px 0 2px;
    ">
        <span style="color:#8793a4;font-size:11px;">
            Win rate
        </span>
        <strong style="color:#182033;">
            {win_rate:.1f}%
        </strong>
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
# ============================================================
# CARTERA
# ============================================================
with tab_cartera:
    render_html(
        """
<div class="card">
    <div class="card-title">Cartera simulada</div>
    <div class="card-subtitle">
        Explora cómo habría evolucionado el capital bajo el escenario seleccionado.
    </div>
</div>
<div class="info-strip">
    <strong>Escenario:</strong>
    inversión fija por señal con take profit y stop loss configurables.
    No incluye comisiones, slippage, impuestos ni restricciones de ejecución.
</div>
""",
        unsafe_allow_html=True,
    )
    df_sim = df_hist.copy()
    if "Fecha" in df_sim.columns:
        df_sim = (
            df_sim
            .dropna(subset=["Fecha"])
            .sort_values("Fecha")
        )
    capital_acumulado = float(capital_inicial)
    curva_capital = [capital_acumulado]
    if not df_sim.empty and "Fecha" in df_sim.columns:
        fechas_curva = [
            df_sim["Fecha"].min() - pd.Timedelta(days=1)
        ]
    else:
        fechas_curva = []
    for _, row in df_sim.iterrows():
        estado_op = str(row.get("Estado", ""))
        rendimiento = 0.0
        if "OBJETIVO_CUMPLIDO" in estado_op:
            rendimiento = (
                capital_por_alerta *
                (take_profit / 100)
            )
        elif "STOP_SALTADO" in estado_op:
            rendimiento = -(
                capital_por_alerta *
                (stop_loss / 100)
            )
        capital_acumulado += rendimiento
        curva_capital.append(capital_acumulado)
        fechas_curva.append(row["Fecha"])
    df_equity = pd.DataFrame(
        {
            "Fecha": fechas_curva,
            "Equity (€)": curva_capital,
        }
    ).set_index("Fecha")
    rendimiento_total = (
        capital_acumulado -
        capital_inicial
    )
    rentabilidad = (
        rendimiento_total /
        capital_inicial *
        100
        if capital_inicial
        else 0
    )
    eq1, eq2, eq3 = st.columns(3)
    eq1.metric(
        "Valor final",
        f"{capital_acumulado:,.0f} €",
        f"{rendimiento_total:+,.0f} €",
    )
    eq2.metric(
        "Rentabilidad acumulada",
        f"{rentabilidad:+.2f}%",
    )
    eq3.metric(
        "Capital por señal",
        f"{capital_por_alerta:,.0f} €",
    )
    st.write("")
    if len(df_equity) > 1:
        st.area_chart(
            df_equity,
            height=360,
        )
    else:
        st.info(
            "Se necesitan más datos históricos para visualizar la curva."
        )
# ============================================================
# ALERTAS
# ============================================================
with tab_activas:
    render_html(
        """
<div class="card">
    <div class="card-title">Radar de oportunidades</div>
    <div class="card-subtitle">
        Señales que el sistema mantiene actualmente en vigilancia.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    df_activas = df_hist[
        df_hist["Estado"]
        .astype(str)
        .str.contains(
            "ACTIVA",
            na=False,
        )
    ].copy()
    if not df_activas.empty:
        a, b = st.columns([.75, 2.25], gap="large")
        with a:
            render_html(
                f"""
<div class="card" style="text-align:center;">
    <div style="
        color:#8793a4;
        font-size:10px;
        font-weight:800;
        text-transform:uppercase;
        letter-spacing:.08em;
    ">
        En radar
    </div>
    <div style="
        color:#172033;
        font-family:'Plus Jakarta Sans';
        font-size:44px;
        font-weight:800;
        letter-spacing:-.05em;
        margin-top:7px;
    ">
        {len(df_activas)}
    </div>
    <div style="
        color:#2164db;
        font-size:10px;
        margin-top:2px;
        font-weight:700;
    ">
        señales activas
    </div>
</div>
""",
                unsafe_allow_html=True,
            )
            render_html(
                """
<div class="card">
    <div class="card-title">Metodología</div>
    <div class="card-subtitle">
        Qué está buscando el motor.
    </div>
    <div style="
        margin-top:13px;
        color:#758296;
        font-size:11px;
        line-height:1.75;
    ">
        Tendencia<br>
        Volumen relativo<br>
        Momentum<br>
        Control de riesgo
    </div>
</div>
""",
                unsafe_allow_html=True,
            )
        with b:
            st.dataframe(
                df_activas,
                use_container_width=True,
                height=420,
                hide_index=True,
            )
    else:
        render_html(
            """
<div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">No hay señales activas</div>
    <div class="empty-text">
        El radar está tranquilo. El sistema continúa monitorizando
        el universo configurado y mostrará nuevas señales cuando
        cumplan las condiciones.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
# ============================================================
# HISTÓRICO
# ============================================================
with tab_historial:
    render_html(
        """
<div class="card">
    <div class="card-title">Histórico de operaciones</div>
    <div class="card-subtitle">
        Trazabilidad de las señales generadas por el sistema.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    df_cerradas = df_hist[
        ~df_hist["Estado"]
        .astype(str)
        .str.contains(
            "ACTIVA",
            na=False,
        )
    ].copy()
    if not df_cerradas.empty:
        col1, col2 = st.columns(2)
        with col1:
            estados_disponibles = sorted(
                df_cerradas["Estado"]
                .astype(str)
                .unique()
                .tolist()
            )
            filtro_estado = st.multiselect(
                "Filtrar estado",
                estados_disponibles,
                default=estados_disponibles,
            )
        with col2:
            texto_busqueda = st.text_input(
                "Buscar activo / ticker",
                placeholder="Ej. SAN, IBE, BBVA...",
            )
        df_view = df_cerradas.copy()
        if filtro_estado:
            df_view = df_view[
                df_view["Estado"]
                .astype(str)
                .isin(filtro_estado)
            ]
        if texto_busqueda:
            mask = (
                df_view
                .astype(str)
                .apply(
                    lambda col: col.str.contains(
                        texto_busqueda,
                        case=False,
                        na=False,
                    )
                )
                .any(axis=1)
            )
            df_view = df_view[mask]
        st.caption(
            f"{len(df_view)} registros mostrados"
        )
        st.dataframe(
            df_view,
            use_container_width=True,
            height=460,
            hide_index=True,
        )
    else:
        render_html(
            """
<div class="empty-state">
    <div class="empty-icon">▱</div>
    <div class="empty-title">Todavía no hay operaciones cerradas</div>
    <div class="empty-text">
        Las operaciones aparecerán aquí cuando terminen,
        permitiendo analizar el histórico de la estrategia.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )
# ============================================================
# FOOTER
# ============================================================
render_html(
    """
<div class="footer">
    <span>ALURA QUANT · INVESTMENT INTELLIGENCE</span>
    <span>Información y simulación hipotética · No constituye asesoramiento financiero</span>
</div>
""",
    unsafe_allow_html=True,
)
