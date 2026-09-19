import os
import re
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# ALURA QUANT V6
# LIGHT FINTECH / INVESTMENT APP UI
# ============================================================

st.set_page_config(
    page_title="Alura Quant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONFIG
# ============================================================

ARCHIVO_HISTORIAL = "historial_alertas.csv"
ARCHIVO_UNIVERSO = "universo_activos.csv"

CAPITAL_INICIAL = 10_000.0
CAPITAL_POR_ALERTA = 1_000.0


# ============================================================
# HELPERS
# ============================================================

def render_html(content):
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


def obtener_total_activos():
    if os.path.exists(ARCHIVO_UNIVERSO):
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(ARCHIVO_UNIVERSO, encoding=encoding)
                if not df.empty:
                    return len(df)
            except Exception:
                continue

    return 37


@st.cache_data(ttl=30)
def cargar_datos():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return pd.DataFrame()

    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            return pd.read_csv(
                ARCHIVO_HISTORIAL,
                on_bad_lines="skip",
                encoding=encoding
            )
        except Exception:
            pass

    return pd.DataFrame()


@st.cache_data(ttl=120)
def obtener_precio_actual(ticker):
    try:
        data = yf.Ticker(ticker).history(period="5d")

        if data.empty:
            return None

        return float(data["Close"].iloc[-1])

    except Exception:
        return None


def preparar_fecha(df):
    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce"
        )

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


def formatear_tesis_ia(texto):
    if not isinstance(texto, str) or not texto.strip():
        return "No hay análisis disponible para esta señal."

    texto = texto.replace(
        "Análisis técnico de",
        ""
    ).replace(
        "Indicadores clave:",
        ""
    )

    texto = re.sub(
        r"\*\*(.*?)\*\*",
        r"<strong>\1</strong>",
        texto
    )

    return texto.strip()


def calcular_resultados(df):
    beneficio = 0.0

    if df.empty or "Fecha" not in df.columns:
        return 0.0

    df_sim = (
        df.copy()
        .dropna(subset=["Fecha"])
        .sort_values("Fecha")
    )

    for _, row in df_sim.iterrows():

        estado = str(row.get("Estado", ""))

        try:
            entrada = float(
                row.get("Precio_Alerta", 100)
            )
        except Exception:
            entrada = 100.0

        try:
            stop = float(
                row.get("Stop_Loss", entrada * 0.96)
            )
        except Exception:
            stop = entrada * 0.96

        try:
            take = float(
                row.get("Take_Profit", entrada * 1.10)
            )
        except Exception:
            take = entrada * 1.10

        if entrada <= 0:
            continue

        ganancia_pct = (
            (take - entrada) / entrada
        )

        perdida_pct = (
            (entrada - stop) / entrada
        )

        if "OBJETIVO_CUMPLIDO" in estado:
            beneficio += (
                CAPITAL_POR_ALERTA *
                ganancia_pct
            )

        elif "STOP_SALTADO" in estado:
            beneficio -= (
                CAPITAL_POR_ALERTA *
                perdida_pct
            )

    return beneficio


def calcular_curva(df):

    fechas = []
    valores = []

    acumulado = 0.0

    if df.empty or "Fecha" not in df.columns:
        return fechas, valores

    df_sim = (
        df.copy()
        .dropna(subset=["Fecha"])
        .sort_values("Fecha")
    )

    df_sim["Fecha_Dia"] = (
        df_sim["Fecha"]
        .dt.strftime("%Y-%m-%d")
    )

    for dia, grupo in df_sim.groupby("Fecha_Dia"):

        beneficio_dia = 0.0

        for _, row in grupo.iterrows():

            estado = str(row.get("Estado", ""))

            try:
                entrada = float(
                    row.get("Precio_Alerta", 100)
                )
            except Exception:
                entrada = 100.0

            try:
                stop = float(
                    row.get(
                        "Stop_Loss",
                        entrada * 0.96
                    )
                )
            except Exception:
                stop = entrada * 0.96

            try:
                take = float(
                    row.get(
                        "Take_Profit",
                        entrada * 1.10
                    )
                )
            except Exception:
                take = entrada * 1.10

            if entrada <= 0:
                continue

            gain = (
                (take - entrada) / entrada
            )

            loss = (
                (entrada - stop) / entrada
            )

            if "OBJETIVO_CUMPLIDO" in estado:
                beneficio_dia += (
                    CAPITAL_POR_ALERTA * gain
                )

            elif "STOP_SALTADO" in estado:
                beneficio_dia -= (
                    CAPITAL_POR_ALERTA * loss
                )

        acumulado += beneficio_dia

        fechas.append(dia)
        valores.append(acumulado)

    return fechas, valores


# ============================================================
# DATA
# ============================================================

TOTAL_ACTIVOS = obtener_total_activos()

df_hist = preparar_fecha(
    cargar_datos()
)

if df_hist.empty:

    total_alertas = 0
    exitos = 0
    fallos = 0
    activas = 0
    win_rate = 0.0

else:

    total_alertas = len(df_hist)

    exitos = contar_estado(
        df_hist,
        "OBJETIVO_CUMPLIDO"
    )

    fallos = contar_estado(
        df_hist,
        "STOP_SALTADO"
    )

    activas = contar_estado(
        df_hist,
        "ACTIVA"
    )

    cerradas = exitos + fallos

    win_rate = (
        exitos / cerradas * 100
        if cerradas
        else 0
    )


beneficio_acumulado = calcular_resultados(
    df_hist
)

rentabilidad_pct = (
    beneficio_acumulado /
    CAPITAL_INICIAL *
    100
)

capital_actual = (
    CAPITAL_INICIAL +
    beneficio_acumulado
)


# ============================================================
# DESIGN SYSTEM
# ============================================================

st.markdown(
    """
<style>

@import url(
'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap'
);


/* ==========================================================
   VARIABLES
========================================================== */

:root {

    --bg:
        #f7f8fa;

    --surface:
        #ffffff;

    --surface-soft:
        #f8fafc;

    --border:
        #eaedf1;

    --border-dark:
        #dfe3e8;

    --text:
        #111827;

    --text-secondary:
        #667085;

    --text-light:
        #98a2b3;

    --brand:
        #2563eb;

    --brand-soft:
        #eff6ff;

    --green:
        #16a34a;

    --green-soft:
        #ecfdf3;

    --red:
        #dc2626;

    --red-soft:
        #fef2f2;

    --yellow:
        #d97706;

    --yellow-soft:
        #fffbeb;

    --radius:
        18px;

    --shadow:
        0 1px 3px rgba(16,24,40,.04),
        0 8px 24px rgba(16,24,40,.035);

}


/* ==========================================================
   GLOBAL
========================================================== */

html,
body,
[class*="css"] {

    font-family:
        'Inter',
        sans-serif;

}


.stApp {

    background:
        var(--bg);

    color:
        var(--text);

}


#MainMenu,
footer,
section[data-testid="stSidebar"] {

    display:
        none !important;

}


.block-container {

    max-width:
        1280px;

    padding-top:
        28px;

    padding-bottom:
        80px;

}


/* ==========================================================
   HEADER
========================================================== */

.app-header {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    margin-bottom:
        34px;

}


.brand-wrapper {

    display:
        flex;

    align-items:
        center;

    gap:
        12px;

}


.brand-logo {

    width:
        40px;

    height:
        40px;

    border-radius:
        12px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    background:
        #111827;

    color:
        white;

    font-size:
        18px;

    font-weight:
        800;

}


.brand-name {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        15px;

    font-weight:
        800;

    letter-spacing:
        -.02em;

}


.brand-caption {

    font-size:
        11px;

    color:
        var(--text-secondary);

    margin-top:
        2px;

}


.market-status {

    display:
        inline-flex;

    align-items:
        center;

    gap:
        7px;

    padding:
        7px 11px;

    border:
        1px solid #dcefe3;

    background:
        #f3fbf6;

    border-radius:
        999px;

    font-size:
        11px;

    font-weight:
        700;

    color:
        #16803b;

}


.status-dot {

    width:
        6px;

    height:
        6px;

    border-radius:
        50%;

    background:
        #22c55e;

}


/* ==========================================================
   HERO
========================================================== */

.hero {

    margin-bottom:
        28px;

}


.hero-eyebrow {

    font-size:
        11px;

    font-weight:
        800;

    text-transform:
        uppercase;

    letter-spacing:
        .10em;

    color:
        var(--brand);

    margin-bottom:
        8px;

}


.hero-title {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        34px;

    line-height:
        1.15;

    font-weight:
        800;

    letter-spacing:
        -.045em;

    margin:
        0;

}


.hero-subtitle {

    margin-top:
        7px;

    font-size:
        14px;

    color:
        var(--text-secondary);

}


/* ==========================================================
   PORTFOLIO SUMMARY
========================================================== */

.portfolio-summary {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        22px;

    padding:
        24px 26px;

    box-shadow:
        var(--shadow);

    margin-bottom:
        18px;

}


.portfolio-label {

    color:
        var(--text-secondary);

    font-size:
        12px;

    font-weight:
        600;

}


.portfolio-value {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        34px;

    line-height:
        1.1;

    font-weight:
        800;

    letter-spacing:
        -.04em;

    margin-top:
        5px;

}


.portfolio-change {

    font-size:
        13px;

    font-weight:
        700;

    margin-top:
        7px;

}


.change-positive {

    color:
        var(--green);

}


.change-negative {

    color:
        var(--red);

}


/* ==========================================================
   KPI GRID
========================================================== */

.kpi-grid {

    display:
        grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:
        12px;

    margin-bottom:
        30px;

}


.kpi {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        16px;

    padding:
        17px 18px;

}


.kpi-label {

    font-size:
        11px;

    color:
        var(--text-secondary);

    font-weight:
        600;

}


.kpi-value {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        24px;

    font-weight:
        800;

    letter-spacing:
        -.035em;

    margin-top:
        7px;

}


.kpi-meta {

    font-size:
        11px;

    color:
        var(--text-light);

    margin-top:
        3px;

}


/* ==========================================================
   TABS
========================================================== */

.stTabs {

    margin-top:
        10px;

}


.stTabs [data-baseweb="tab-list"] {

    background:
        transparent !important;

    gap:
        25px !important;

    border-bottom:
        1px solid var(--border) !important;

    padding:
        0 !important;

}


.stTabs button[data-baseweb="tab"] {

    background:
        transparent !important;

    border:
        0 !important;

    height:
        48px !important;

    padding:
        0 2px !important;

    color:
        var(--text-secondary) !important;

}


.stTabs button[data-baseweb="tab"] p {

    font-size:
        13px !important;

    font-weight:
        700 !important;

}


.stTabs button[aria-selected="true"] {

    color:
        var(--text) !important;

    border-bottom:
        2px solid var(--text) !important;

}


.stTabs button[aria-selected="true"] p {

    color:
        var(--text) !important;

}


/* ==========================================================
   SECTION HEADER
========================================================== */

.section-header {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    margin:
        26px 0 15px;

}


.section-title {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        18px;

    font-weight:
        800;

    letter-spacing:
        -.025em;

}


.section-description {

    color:
        var(--text-secondary);

    font-size:
        12px;

    margin-top:
        3px;

}


/* ==========================================================
   ASSET CARD
========================================================== */

.asset-card {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        20px;

    padding:
        20px;

    margin-bottom:
        12px;

    transition:
        transform .18s ease,
        box-shadow .18s ease,
        border-color .18s ease;

}


.asset-card:hover {

    transform:
        translateY(-2px);

    box-shadow:
        0 10px 30px rgba(16,24,40,.06);

    border-color:
        var(--border-dark);

}


.asset-header {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    gap:
        15px;

}


.asset-left {

    display:
        flex;

    align-items:
        center;

    gap:
        13px;

    min-width:
        0;

}


.asset-icon {

    width:
        44px;

    height:
        44px;

    min-width:
        44px;

    border-radius:
        13px;

    display:
        flex;

    align-items:
        center;

    justify-content:
        center;

    background:
        #f3f6fa;

    font-size:
        19px;

}


.asset-name {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        15px;

    font-weight:
        800;

    white-space:
        nowrap;

    overflow:
        hidden;

    text-overflow:
        ellipsis;

}


.asset-ticker {

    color:
        var(--text-secondary);

    font-size:
        12px;

    font-weight:
        600;

    margin-left:
        4px;

}


.asset-sector {

    color:
        var(--text-light);

    font-size:
        11px;

    margin-top:
        3px;

}


.asset-right {

    text-align:
        right;

}


.asset-price {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        18px;

    font-weight:
        800;

    letter-spacing:
        -.02em;

}


.asset-price-label {

    font-size:
        10px;

    color:
        var(--text-light);

    margin-top:
        2px;

}


.new-badge {

    display:
        inline-flex;

    align-items:
        center;

    padding:
        3px 7px;

    border-radius:
        999px;

    background:
        var(--green-soft);

    color:
        var(--green);

    font-size:
        9px;

    font-weight:
        800;

    margin-bottom:
        5px;

}


/* ==========================================================
   TRADE METRICS
========================================================== */

.trade-grid {

    display:
        grid;

    grid-template-columns:
        repeat(4,1fr);

    gap:
        8px;

    margin-top:
        18px;

}


.trade-item {

    background:
        var(--surface-soft);

    border-radius:
        12px;

    padding:
        11px 12px;

}


.trade-label {

    font-size:
        9px;

    text-transform:
        uppercase;

    letter-spacing:
        .06em;

    color:
        var(--text-light);

    font-weight:
        800;

}


.trade-value {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        14px;

    font-weight:
        800;

    margin-top:
        4px;

}


/* ==========================================================
   AI INSIGHT
========================================================== */

.ai-insight {

    margin-top:
        14px;

    padding:
        13px 15px;

    border-radius:
        12px;

    background:
        #f8faff;

    border:
        1px solid #edf2ff;

}


.ai-title {

    color:
        var(--brand);

    font-size:
        10px;

    font-weight:
        800;

    text-transform:
        uppercase;

    letter-spacing:
        .07em;

    margin-bottom:
        4px;

}


.ai-text {

    color:
        #475467;

    font-size:
        12px;

    line-height:
        1.55;

}


/* ==========================================================
   FILTER BAR
========================================================== */

.filter-bar {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        15px;

    padding:
        8px 12px;

    margin:
        18px 0;

}


/* ==========================================================
   RESULTS CARD
========================================================== */

.result-card {

    background:
        var(--surface);

    border:
        1px solid var(--border);

    border-radius:
        20px;

    padding:
        22px;

    box-shadow:
        var(--shadow);

}


.result-header {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        flex-start;

    margin-bottom:
        20px;

}


.result-title {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        16px;

    font-weight:
        800;

}


.result-subtitle {

    font-size:
        11px;

    color:
        var(--text-secondary);

    margin-top:
        3px;

}


.result-number {

    font-family:
        'Plus Jakarta Sans';

    font-size:
        23px;

    font-weight:
        800;

    text-align:
        right;

}


.result-percent {

    font-size:
        11px;

    font-weight:
        700;

    text-align:
        right;

    margin-top:
        2px;

}


/* ==========================================================
   METRIC LIST
========================================================== */

.metric-row {

    display:
        flex;

    justify-content:
        space-between;

    align-items:
        center;

    padding:
        14px 0;

    border-bottom:
        1px solid #f0f2f5;

}


.metric-row:last-child {

    border-bottom:
        none;

}


.metric-label {

    font-size:
        12px;

    color:
        var(--text-secondary);

    font-weight:
        600;

}


.metric-value {

    font-size:
        13px;

    font-weight:
        800;

}


/* ==========================================================
   TABLE
========================================================== */

[data-testid="stDataFrame"] {

    border:
        1px solid var(--border);

    border-radius:
        16px;

    overflow:
        hidden;

}


/* ==========================================================
   FOOTER
========================================================== */

.app-footer {

    display:
        flex;

    justify-content:
        space-between;

    margin-top:
        60px;

    padding-top:
        20px;

    border-top:
        1px solid var(--border);

    color:
        var(--text-light);

    font-size:
        10px;

}


/* ==========================================================
   MOBILE
========================================================== */

@media (max-width: 800px) {

    .block-container {

        padding:
            18px 14px 50px;

    }

    .hero-title {

        font-size:
            28px;

    }

    .kpi-grid {

        grid-template-columns:
            repeat(2,1fr);

    }

    .trade-grid {

        grid-template-columns:
            repeat(2,1fr);

    }

}


@media (max-width: 480px) {

    .app-header {

        margin-bottom:
            25px;

    }

    .market-status {

        display:
            none;

    }

    .portfolio-value {

        font-size:
            30px;

    }

    .asset-card {

        padding:
            16px;

    }

    .asset-header {

        align-items:
            flex-start;

    }

    .asset-price {

        font-size:
            16px;

    }

    .asset-name {

        font-size:
            14px;

    }

    .trade-value {

        font-size:
            13px;

    }

    .stTabs [data-baseweb="tab-list"] {

        gap:
            18px !important;

        overflow-x:
            auto;

    }

    .app-footer {

        flex-direction:
            column;

        gap:
            6px;

    }

}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

render_html(
    """
<div class="app-header">

    <div class="brand-wrapper">

        <div class="brand-logo">
            ◈
        </div>

        <div>
            <div class="brand-name">
                ALURA QUANT
            </div>

            <div class="brand-caption">
                Quantitative Investment Intelligence
            </div>
        </div>

    </div>

    <div class="market-status">
        <span class="status-dot"></span>
        Mercado monitorizado
    </div>

</div>
"""
)


# ============================================================
# HERO
# ============================================================

render_html(
    """
<div class="hero">

    <div class="hero-eyebrow">
        Investment dashboard
    </div>

    <h1 class="hero-title">
        Tu radar de inversión
    </h1>

    <div class="hero-subtitle">
        Señales cuantitativas, cartera activa y rendimiento histórico.
    </div>

</div>
"""
)


# ============================================================
# PORTFOLIO SUMMARY
# ============================================================

color_resultado = (
    "change-positive"
    if beneficio_acumulado >= 0
    else "change-negative"
)

signo = "+" if beneficio_acumulado >= 0 else ""

render_html(
    f"""
<div class="portfolio-summary">

    <div class="portfolio-label">
        Capital simulado
    </div>

    <div class="portfolio-value">
        {capital_actual:,.2f} €
    </div>

    <div class="portfolio-change {color_resultado}">
        {signo}{beneficio_acumulado:,.2f} €
        ·
        {signo}{rentabilidad_pct:.2f}%
        desde el inicio
    </div>

</div>
"""
)


# ============================================================
# KPI GRID
# ============================================================

render_html(
    f"""
<div class="kpi-grid">

    <div class="kpi">
        <div class="kpi-label">
            Activos monitorizados
        </div>
        <div class="kpi-value">
            {TOTAL_ACTIVOS}
        </div>
        <div class="kpi-meta">
            Universo cuantitativo
        </div>
    </div>

    <div class="kpi">
        <div class="kpi-label">
            Señales activas
        </div>
        <div class="kpi-value">
            {activas}
        </div>
        <div class="kpi-meta">
            En cartera
        </div>
    </div>

    <div class="kpi">
        <div class="kpi-label">
            Rentabilidad
        </div>
        <div class="kpi-value"
             style="color:{'var(--green)' if rentabilidad_pct >= 0 else 'var(--red)'}">
            {rentabilidad_pct:+.1f}%
        </div>
        <div class="kpi-meta">
            Resultado acumulado
        </div>
    </div>

    <div class="kpi">
        <div class="kpi-label">
            Win rate
        </div>
        <div class="kpi-value">
            {win_rate:.1f}%
        </div>
        <div class="kpi-meta">
            {exitos} objetivos · {fallos} stops
        </div>
    </div>

</div>
"""
)


# ============================================================
# EMPTY STATE
# ============================================================

if df_hist.empty:

    render_html(
        """
        <div class="asset-card">

            <div class="section-title">
                Sin actividad todavía
            </div>

            <div class="section-description">
                No se encontraron señales en el histórico.
            </div>

        </div>
        """
    )

    st.stop()


# ============================================================
# TABS
# ============================================================

tab_cartera, tab_resultados, tab_historial = st.tabs(
    [
        "Cartera",
        "Resultados",
        "Histórico"
    ]
)


# ============================================================
# CARTERA
# ============================================================

with tab_cartera:

    render_html(
        """
        <div class="section-header">

            <div>

                <div class="section-title">
                    Tu cartera
                </div>

                <div class="section-description">
                    Señales cuantitativas actualmente activas.
                </div>

            </div>

        </div>
        """
    )

    df_activas = df_hist[
        df_hist["Estado"]
        .astype(str)
        .str.contains(
            "ACTIVA",
            na=False
        )
    ].copy()

    if df_activas.empty:

        render_html(
            """
            <div class="asset-card">

                <div class="section-title">
                    No hay posiciones activas
                </div>

                <div class="section-description">
                    El sistema no tiene señales abiertas en este momento.
                </div>

            </div>
            """
        )

    else:

        col1, col2 = st.columns(
            [1, 2],
            gap="small"
        )

        with col1:

            sectores = (
                ["Todos"]
                +
                sorted(
                    df_activas["Sector"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                if "Sector" in df_activas.columns
                else ["Todos"]
            )

            filtro_sector = st.selectbox(
                "Sector",
                sectores,
                label_visibility="collapsed"
            )

        with col2:

            busqueda = st.text_input(
                "Buscar",
                placeholder="Buscar empresa o ticker...",
                label_visibility="collapsed"
            )

        df_view = df_activas.copy()

        if filtro_sector != "Todos":

            df_view = df_view[
                df_view["Sector"]
                == filtro_sector
            ]

        if busqueda:

            mask = (
                df_view
                .astype(str)
                .apply(
                    lambda col:
                    col.str.contains(
                        busqueda,
                        case=False,
                        na=False
                    )
                )
                .any(axis=1)
            )

            df_view = df_view[mask]


        for _, row in df_view.iterrows():

            icono = row.get(
                "Icono",
                "📈"
            )

            if pd.isna(icono):
                icono = "📈"

            empresa = row.get(
                "Empresa",
                row.get(
                    "Ticker",
                    "Activo"
                )
            )

            ticker = row.get(
                "Ticker",
                ""
            )

            sector = row.get(
                "Sector",
                "Mercado"
            )

            # --------------------------------------------
            # NUEVO
            # --------------------------------------------

            es_nuevo = False

            if (
                "Fecha" in row
                and pd.notna(row["Fecha"])
            ):

                try:

                    fecha_row = (
                        row["Fecha"]
                        .to_pydatetime()
                        .replace(
                            tzinfo=None
                        )
                    )

                    delta = (
                        datetime.now()
                        -
                        fecha_row
                    )

                    es_nuevo = (
                        delta <=
                        timedelta(hours=48)
                    )

                except Exception:
                    pass


            # --------------------------------------------
            # PRECIO
            # --------------------------------------------

            precio_actual = obtener_precio_actual(
                ticker
            )

            if precio_actual is not None:

                precio_actual_str = (
                    f"{precio_actual:,.2f} €"
                )

            else:

                precio_actual_str = "—"


            # --------------------------------------------
            # PARAMETROS
            # --------------------------------------------

            entrada = (
                f"{float(row['Precio_Alerta']):,.2f} €"
                if (
                    "Precio_Alerta" in row
                    and pd.notna(row["Precio_Alerta"])
                )
                else "—"
            )

            stop = (
                f"{float(row['Stop_Loss']):,.2f} €"
                if (
                    "Stop_Loss" in row
                    and pd.notna(row["Stop_Loss"])
                )
                else "—"
            )

            take = (
                f"{float(row['Take_Profit']):,.2f} €"
                if (
                    "Take_Profit" in row
                    and pd.notna(row["Take_Profit"])
                )
                else "—"
            )

            ratio = (
                f"{float(row['Ratio_RR']):.1f}x"
                if (
                    "Ratio_RR" in row
                    and pd.notna(row["Ratio_RR"])
                )
                else "—"
            )


            tesis = formatear_tesis_ia(
                row.get(
                    "Analisis_IA",
                    ""
                )
            )


            badge = (
                '<div class="new-badge">NEW</div>'
                if es_nuevo
                else ""
            )


            # --------------------------------------------
            # CARD
            # --------------------------------------------

            render_html(
                f"""
<div class="asset-card">

    <div class="asset-header">

        <div class="asset-left">

            <div class="asset-icon">
                {icono}
            </div>

            <div style="min-width:0;">

                <div class="asset-name">
                    {empresa}
                    <span class="asset-ticker">
                        {ticker}
                    </span>
                </div>

                <div class="asset-sector">
                    {sector}
                </div>

            </div>

        </div>


        <div class="asset-right">

            {badge}

            <div class="asset-price">
                {precio_actual_str}
            </div>

            <div class="asset-price-label">
                Precio actual
            </div>

        </div>

    </div>


    <div class="trade-grid">

        <div class="trade-item">

            <div class="trade-label">
                Entrada
            </div>

            <div class="trade-value">
                {entrada}
            </div>

        </div>


        <div class="trade-item">

            <div class="trade-label">
                Stop Loss
            </div>

            <div class="trade-value"
                 style="color:var(--red);">
                {stop}
            </div>

        </div>


        <div class="trade-item">

            <div class="trade-label">
                Take Profit
            </div>

            <div class="trade-value"
                 style="color:var(--green);">
                {take}
            </div>

        </div>


        <div class="trade-item">

            <div class="trade-label">
                Risk / Reward
            </div>

            <div class="trade-value"
                 style="color:var(--brand);">
                {ratio}
            </div>

        </div>

    </div>


    <div class="ai-insight">

        <div class="ai-title">
            ◈ Tesis cuantitativa
        </div>

        <div class="ai-text">
            {tesis}
        </div>

    </div>

</div>
"""
            )


# ============================================================
# RESULTADOS
# ============================================================

with tab_resultados:

    render_html(
        """
        <div class="section-header">

            <div>

                <div class="section-title">
                    Rendimiento
                </div>

                <div class="section-description">
                    Evolución histórica del sistema.
                </div>

            </div>

        </div>
        """
    )

    fechas, valores = calcular_curva(
        df_hist
    )

    col_chart, col_metrics = st.columns(
        [1.65, .85],
        gap="large"
    )


    with col_chart:

        color_resultado = (
            "var(--green)"
            if beneficio_acumulado >= 0
            else "var(--red)"
        )

        render_html(
            f"""
<div class="result-card">

    <div class="result-header">

        <div>

            <div class="result-title">
                Beneficio acumulado
            </div>

            <div class="result-subtitle">
                Simulación sobre capital de 10.000 €
            </div>

        </div>

        <div>

            <div class="result-number"
                 style="color:{color_resultado};">
                {beneficio_acumulado:+,.2f} €
            </div>

            <div class="result-percent"
                 style="color:{color_resultado};">
                {rentabilidad_pct:+.2f}%
            </div>

        </div>

    </div>

</div>
"""
        )


        if fechas:

            df_chart = pd.DataFrame(
                {
                    "Beneficio neto (€)":
                        valores
                },
                index=fechas
            )

            st.line_chart(
                df_chart,
                height=320
            )

        else:

            st.info(
                "Todavía no hay suficientes datos para mostrar la curva."
            )


    with col_metrics:

        render_html(
            f"""
<div class="result-card">

    <div class="result-title"
         style="margin-bottom:5px;">
        Métricas
    </div>

    <div class="result-subtitle">
        Resumen operativo
    </div>


    <div class="metric-row">

        <span class="metric-label">
            Señales
        </span>

        <span class="metric-value">
            {total_alertas}
        </span>

    </div>


    <div class="metric-row">

        <span class="metric-label">
            Activas
        </span>

        <span class="metric-value"
              style="color:var(--brand);">
            {activas}
        </span>

    </div>


    <div class="metric-row">

        <span class="metric-label">
            Objetivos
        </span>

        <span class="metric-value"
              style="color:var(--green);">
            {exitos}
        </span>

    </div>


    <div class="metric-row">

        <span class="metric-label">
            Stops
        </span>

        <span class="metric-value"
              style="color:var(--red);">
            {fallos}
        </span>

    </div>


    <div class="metric-row">

        <span class="metric-label">
            Win rate
        </span>

        <span class="metric-value">
            {win_rate:.1f}%
        </span>

    </div>

</div>
"""
        )


# ============================================================
# HISTÓRICO
# ============================================================

with tab_historial:

    render_html(
        """
        <div class="section-header">

            <div>

                <div class="section-title">
                    Histórico
                </div>

                <div class="section-description">
                    Registro completo de señales generadas.
                </div>

            </div>

        </div>
        """
    )


    col1, col2 = st.columns(
        [1, 2],
        gap="small"
    )


    with col1:

        estados = sorted(
            df_hist["Estado"]
            .astype(str)
            .unique()
            .tolist()
        )

        filtro_estado = st.multiselect(
            "Estado",
            estados,
            default=estados,
            label_visibility="collapsed"
        )


    with col2:

        busqueda_hist = st.text_input(
            "Buscar",
            placeholder="Buscar empresa, ticker, estado...",
            label_visibility="collapsed"
        )


    df_view = df_hist.copy()


    if filtro_estado:

        df_view = df_view[
            df_view["Estado"]
            .astype(str)
            .isin(filtro_estado)
        ]


    if busqueda_hist:

        mask = (
            df_view
            .astype(str)
            .apply(
                lambda col:
                col.str.contains(
                    busqueda_hist,
                    case=False,
                    na=False
                )
            )
            .any(axis=1)
        )

        df_view = df_view[mask]


    st.dataframe(
        df_view,
        use_container_width=True,
        height=480,
        hide_index=True
    )


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
<div class="app-footer">

    <span>
        ALURA QUANT · INVESTMENT INTELLIGENCE
    </span>

    <span>
        Simulación cuantitativa · Uso interno
    </span>

</div>
"""
)