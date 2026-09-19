import os
from datetime import datetime
import pandas as pd
import streamlit as st
import yfinance as yf

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
TOTAL_ACTIVOS_UNIVERSO = 37


def render_html(content, **kwargs):
    """Renderiza HTML directamente y evita que Markdown rompa el marcado."""
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


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
#MainMenu, footer, section[data-testid="stSidebar"] {
    display: none !important;
}
.block-container {
    max-width: 1380px;
    padding-top: 2rem;
    padding-bottom: 3.5rem;
}

/* PAGE TITLE */
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
    font-size: 32px;
    line-height: 1.12;
    letter-spacing: -.045em;
    color: #151c2b;
    margin: 0;
}
.page-description {
    color: var(--muted);
    font-size: 14px;
    margin-top: 6px;
}

/* KPI CARDS (4 COLUMNAS) */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
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

/* CARDS */
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

/* CARTERA CARDS */
.asset-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 22px;
    margin-bottom: 20px;
    box-shadow: var(--shadow);
}
.asset-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 14px;
    border-bottom: 1px solid #edf1f6;
}
.asset-identity {
    display: flex;
    align-items: center;
    gap: 12px;
}
.asset-icon {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    background: var(--blue-soft);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
.asset-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 17px;
    font-weight: 800;
    color: #182033;
}
.asset-subtitle {
    font-size: 11px;
    color: var(--muted);
    margin-top: 2px;
}
.asset-live-price {
    text-align: right;
}
.asset-live-price .price-val {
    font-family: 'Plus Jakarta Sans';
    font-size: 18px;
    font-weight: 800;
    color: #1557e8;
}
.asset-live-price .price-lbl {
    font-size: 10px;
    font-weight: 700;
    color: #8793a4;
    text-transform: uppercase;
}

.params-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 16px;
}
.param-box {
    background: #f8fafc;
    border: 1px solid #e9eff6;
    border-radius: 12px;
    padding: 10px 12px;
}
.param-label {
    font-size: 9px;
    font-weight: 800;
    color: #8793a4;
    text-transform: uppercase;
    letter-spacing: .06em;
}
.param-value {
    font-family: 'Plus Jakarta Sans';
    font-size: 15px;
    font-weight: 800;
    color: #182033;
    margin-top: 4px;
}
.ai-box {
    background: #f4f8ff;
    border-left: 3px solid var(--blue);
    border-radius: 0 12px 12px 0;
    padding: 12px 16px;
    color: #2c3e55;
    font-size: 12px;
    line-height: 1.6;
}

/* SIGNAL ROWS */
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
    font-size: 15px;
}
.signal-icon.active { background: #eaf1ff; }
.signal-icon.win { background: #eaf8f0; }
.signal-icon.loss { background: #fff0f0; }
.signal-name { color: #20293a; font-size: 12px; font-weight: 800; }
.signal-detail { color: #909cac; font-size: 10px; margin-top: 3px; }
.signal-badge { border-radius: 7px; padding: 5px 8px; font-size: 9px; font-weight: 800; }

/* ============================================================
   UX/UI MODERN SEGMENTED CONTROL TABS
   ============================================================ */
.stTabs {
    margin-top: 15px !important;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 10px !important;
    background: #e2ebf5 !important;
    border-radius: 18px !important;
    padding: 8px !important;
    border: 1px solid #d8e2ee !important;
    margin-bottom: 28px !important;
    display: inline-flex !important;
}

.stTabs button[data-baseweb="tab"] {
    height: auto !important;
    color: #475569 !important;
    background: transparent !important;
    border: 0 !important;
    border-radius: 14px !important;
    padding: 12px 32px !important;
    transition: all 0.2s ease !important;
}

.stTabs button[data-baseweb="tab"] p,
.stTabs button[data-baseweb="tab"] span,
.stTabs [data-baseweb="tab"] * {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 24px !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    margin: 0 !important;
    line-height: 1.2 !important;
}

.stTabs button[data-baseweb="tab"]:hover {
    color: #1557e8 !important;
    background: rgba(255, 255, 255, 0.7) !important;
}

.stTabs button[aria-selected="true"] {
    color: #1557e8 !important;
    background: #ffffff !important;
    box-shadow: 0 4px 18px rgba(21, 87, 232, 0.20) !important;
    border-bottom: 0 !important;
}

.stTabs button[aria-selected="true"] p,
.stTabs button[aria-selected="true"] span,
.stTabs button[aria-selected="true"] * {
    color: #1557e8 !important;
}

/* FOOTER */
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
@media (max-width: 900px) {
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    .params-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# DATA ENGINE
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
    return int(df["Estado"].astype(str).str.contains(texto, na=False).sum())


def estado_visual(estado):
    estado = str(estado).upper()
    if "OBJETIVO_CUMPLIDO" in estado:
        return "win", "🟢", "OBJETIVO"
    if "STOP_SALTADO" in estado:
        return "loss", "🔴", "STOP"
    if "ACTIVA" in estado:
        return "active", "⏳", "ACTIVA"
    return "active", "•", estado[:18]


# ============================================================
# LOAD DATA
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
# PAGE HEADER & KPI STRIP
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
# EMPTY STATE CHECK
# ============================================================
if df_hist.empty:
    render_html(
        """
<div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">Tu radar todavía está vacío</div>
    <div class="empty-text">
        Ejecuta el escáner cuantitativo para empezar a recibir señales.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.stop()


# ============================================================
# NAVEGACIÓN PRINCIPAL (ORDEN: CARTERA -> RESULTADOS -> HISTÓRICO)
# ============================================================
tab_cartera, tab_resultados, tab_historial = st.tabs(
    ["💼  Cartera", "📊  Resultados", "📜  Histórico"]
)


# ============================================================
# 1. PESTAÑA CARTERA (VISTA POR DEFECTO)
# ============================================================
with tab_cartera:
    df_activas = df_hist[
        df_hist["Estado"].astype(str).str.contains("ACTIVA", na=False)
    ].copy()

    if df_activas.empty:
        render_html(
            """
        <div class="empty-state">
            <div class="empty-icon">◌</div>
            <div class="empty-title">No hay posiciones activas en Cartera</div>
            <div class="empty-text">Actualmente el radar no mantiene valores en seguimiento activo.</div>
        </div>
        """,
            unsafe_allow_html=True,
        )
    else:
        for _, row in df_activas.iterrows():
            icono = (
                row.get("Icono", "📈") if pd.notna(row.get("Icono")) else "📈"
            )
            empresa = row.get("Empresa", row.get("Ticker", "Activo"))
            ticker = row.get("Ticker", "")
            sector = row.get("Sector", "Mercado Continuo")

            precio_actual_val = obtener_precio_actual(ticker)
            if precio_actual_val:
                precio_actual_str = f"{precio_actual_val:.2f} €"
            else:
                precio_actual_str = "—"

            precio_ent = (
                f"{row['Precio_Alerta']:.2f} €"
                if "Precio_Alerta" in row and pd.notna(row["Precio_Alerta"])
                else "—"
            )
            stop_loss = (
                f"{row['Stop_Loss']:.2f} €"
                if "Stop_Loss" in row and pd.notna(row["Stop_Loss"])
                else "—"
            )
            take_profit = (
                f"{row['Take_Profit']:.2f} €"
                if "Take_Profit" in row and pd.notna(row["Take_Profit"])
                else "—"
            )
            ratio_rr = (
                f"{row['Ratio_RR']:.1f}x"
                if "Ratio_RR" in row and pd.notna(row["Ratio_RR"])
                else "—"
            )

            analisis_ia = (
                row.get("Analisis_IA", "Sin análisis disponible.")
                if pd.notna(row.get("Analisis_IA"))
                else "Sin análisis disponible."
            )

            render_html(
                f"""
            <div class="asset-card">
                <div class="asset-header">
                    <div class="asset-identity">
                        <div class="asset-icon">{icono}</div>
                        <div>
                            <div class="asset-title">{empresa} <span style="color:#8793a4; font-weight:600;">({ticker})</span></div>
                            <div class="asset-subtitle">{sector}</div>
                        </div>
                    </div>
                    <div class="asset-live-price">
                        <div class="price-val">{precio_actual_str}</div>
                        <div class="price-lbl">Precio Actual</div>
                    </div>
                </div>
                
                <div class="params-grid">
                    <div class="param-box">
                        <div class="param-label">Precio Entrada</div>
                        <div class="param-value">{precio_ent}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-label">Stop Loss</div>
                        <div class="param-value" style="color:#d94343;">{stop_loss}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-label">Take Profit</div>
                        <div class="param-value" style="color:#149447;">{take_profit}</div>
                    </div>
                    <div class="param-box">
                        <div class="param-label">Ratio Risk/Reward</div>
                        <div class="param-value" style="color:#1557e8;">{ratio_rr}</div>
                    </div>
                </div>
                
                <div class="ai-box">
                    <strong style="color:#1557e8; display:block; margin-bottom:4px; font-size:11px; text-transform:uppercase; letter-spacing:.05em;">
                        💡 Tesis del Modelo IA
                    </strong>
                    {analisis_ia}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


# ============================================================
# 2. PESTAÑA RESULTADOS
# ============================================================
with tab_resultados:
    col_grafico, col_desglose = st.columns([1.2, 0.8], gap="large")

    capital_inicial = 10000.0
    capital_por_alerta = 1000.0
    take_profit_pct = 10.0
    stop_loss_pct = 4.0

    df_sim = df_hist.copy()
    if "Fecha" in df_sim.columns:
        df_sim = df_sim.dropna(subset=["Fecha"]).sort_values("Fecha")

    beneficio_acumulado = 0.0
    fechas_curva = []
    beneficios_curva = []

    if not df_sim.empty and "Fecha" in df_sim.columns:
        df_sim["Fecha_Dia"] = df_sim["Fecha"].dt.strftime("%Y-%m-%d")

        for dia, grupo in df_sim.groupby("Fecha_Dia"):
            beneficio_dia = 0.0
            for _, row in grupo.iterrows():
                estado_op = str(row.get("Estado", ""))
                precio_ent = (
                    float(row["Precio_Alerta"])
                    if "Precio_Alerta" in row and pd.notna(row["Precio_Alerta"])
                    else 100.0
                )
                precio_sl = (
                    float(row["Stop_Loss"])
                    if "Stop_Loss" in row and pd.notna(row["Stop_Loss"])
                    else precio_ent * (1 - stop_loss_pct / 100)
                )
                precio_tp = (
                    float(row["Take_Profit"])
                    if "Take_Profit" in row and pd.notna(row["Take_Profit"])
                    else precio_ent * (1 + take_profit_pct / 100)
                )

                pct_ganancia = (
                    (precio_tp - precio_ent) / precio_ent
                    if precio_ent > 0
                    else 0.10
                )
                pct_pérdida = (
                    (precio_ent - precio_sl) / precio_ent
                    if precio_ent > 0
                    else 0.04
                )

                if "OBJETIVO_CUMPLIDO" in estado_op:
                    beneficio_dia += capital_por_alerta * pct_ganancia
                elif "STOP_SALTADO" in estado_op:
                    beneficio_dia -= capital_por_alerta * pct_pérdida

            beneficio_acumulado += beneficio_dia
            fechas_curva.append(dia)
            beneficios_curva.append(beneficio_acumulado)

    rentabilidad_pct = (
        (beneficio_acumulado / capital_inicial * 100) if capital_inicial else 0
    )

    with col_grafico:
        render_html(
            f"""
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div>
                    <div class="card-title">Beneficio Acum. (€)</div>
                    <div class="card-subtitle">Evolución diaria del rendimiento sobre lo invertido</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-family:'Plus Jakarta Sans'; font-size:22px; font-weight:800; color:{'#149447' if beneficio_acumulado >= 0 else '#d94343'};">
                        {beneficio_acumulado:+,.2f} €
                    </div>
                    <div style="font-size:10px; color:#8793a4; font-weight:700;">
                        {rentabilidad_pct:+.2f}% sobre capital
                    </div>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        if fechas_curva:
            df_beneficio = pd.DataFrame(
                {"Día": fechas_curva, "Beneficio Neto (€)": beneficios_curva}
            ).set_index("Día")

            st.line_chart(df_beneficio, height=330)
        else:
            st.info(
                "Se necesitan más fechas registradas para trazar el gráfico de rendimiento."
            )

    with col_desglose:
        render_html(
            f"""
        <div class="card">
            <div class="card-title">Desglose de Alertas</div>
            <div class="card-subtitle">Estado actual de las posiciones detectadas</div>
            <div style="margin-top:16px;">
                <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #edf1f6;">
                    <span style="color:#68768a; font-size:12px; font-weight:600;">Señales activas en radar</span>
                    <strong style="color:#2164db; font-size:13px;">{activas}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #edf1f6;">
                    <span style="color:#68768a; font-size:12px; font-weight:600;">Objetivos alcanzados</span>
                    <strong style="color:#149447; font-size:13px;">{exitos}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:12px 0; border-bottom:1px solid #edf1f6;">
                    <span style="color:#68768a; font-size:12px; font-weight:600;">Stops saltados</span>
                    <strong style="color:#d94343; font-size:13px;">{fallos}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding:12px 0 4px;">
                    <span style="color:#68768a; font-size:12px; font-weight:600;">Tasa de Acierto (Win Rate)</span>
                    <strong style="color:#172033; font-size:13px;">{win_rate:.1f}%</strong>
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        df_recent = df_hist.head(4)
        rows_recent_html = []
        for _, row in df_recent.iterrows():
            tipo, estado_icono, label = estado_visual(row.get("Estado", "—"))
            icono = (
                row.get("Icono", "📈") if pd.notna(row.get("Icono")) else "📈"
            )
            empresa = row.get("Empresa", row.get("Ticker", "Activo"))
            ticker = row.get("Ticker", "")

            badge_style = {
                "active": "background:#eaf1ff;color:#2164db;",
                "win": "background:#eaf8f0;color:#138848;",
                "loss": "background:#fff0f0;color:#cf4040;",
            }[tipo]

            rows_recent_html.append(
                f"""
                <div class="signal">
                    <div class="signal-main">
                        <div class="signal-icon {tipo}">{icono}</div>
                        <div>
                            <div class="signal-name">{empresa} ({ticker})</div>
                            <div class="signal-detail">{row.get('Sector', 'Mercado Continuo')}</div>
                        </div>
                    </div>
                    <div class="signal-badge" style="{badge_style}">{label}</div>
                </div>
                """
            )

        render_html(
            """
        <div class="card">
            <div class="card-title">Últimos movimientos</div>
            <div style="margin-top:8px;">
            """
            + "".join(rows_recent_html)
            + "</div></div>"
        )


# ============================================================
# 3. PESTAÑA HISTÓRICO
# ============================================================
with tab_historial:
    render_html(
        """
<div class="card">
    <div class="card-title">Histórico Operativo</div>
    <div class="card-subtitle">
        Trazabilidad completa de las señales generadas y ejecutadas por el modelo.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    df_cerradas = df_hist[
        ~df_hist["Estado"].astype(str).str.contains("ACTIVA", na=False)
    ].copy()

    if not df_cerradas.empty:
        col1, col2 = st.columns(2)
        with col1:
            estados_disponibles = sorted(
                df_cerradas["Estado"].astype(str).unique().tolist()
            )
            filtro_estado = st.multiselect(
                "Filtrar estado",
                estados_disponibles,
                default=estados_disponibles,
            )
        with col2:
            texto_busqueda = st.text_input(
                "Buscar activo / empresa / sector",
                placeholder="Ej. Bankinter, SAN, Solaria...",
            )

        df_view = df_cerradas.copy()
        if filtro_estado:
            df_view = df_view[df_view["Estado"].astype(str).isin(filtro_estado)]

        if texto_busqueda:
            mask = (
                df_view.astype(str)
                .apply(
                    lambda col: col.str.contains(
                        texto_busqueda, case=False, na=False
                    )
                )
                .any(axis=1)
            )
            df_view = df_view[mask]

        columnas_deseadas_hist = [
            "Fecha",
            "Icono",
            "Ticker",
            "Empresa",
            "Sector",
            "Precio_Alerta",
            "Stop_Loss",
            "Take_Profit",
            "Estado",
            "Analisis_IA",
        ]
        columnas_visibles_hist = [
            c for c in columnas_deseadas_hist if c in df_view.columns
        ]

        if not columnas_visibles_hist:
            columnas_visibles_hist = df_view.columns.tolist()

        st.dataframe(
            df_view[columnas_visibles_hist],
            use_container_width=True,
            height=460,
            hide_index=True,
        )
    else:
        render_html(
            """
<div class="empty-state">
    <div class="empty-icon">▱</div>
    <div class="empty-title">Sin historial de operaciones cerradas</div>
    <div class="empty-text">Las operaciones cerradas se irán acumulando aquí automáticamente.</div>
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
    <span>Simulación cuantitativa · No constituye asesoramiento financiero formal</span>
</div>
""",
    unsafe_allow_html=True,
)