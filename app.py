import os
import re
import html
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf


# ============================================================
# ALURA QUANT — INVESTMENT INTELLIGENCE UI
# ============================================================

st.set_page_config(
    page_title="Alura Quant",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

ARCHIVO_HISTORIAL = "historial_alertas.csv"
ARCHIVO_UNIVERSO = "universo_activos.csv"

CAPITAL_POR_ALERTA = 300.0


# ============================================================
# UTILIDADES
# ============================================================

def render_html(content, **kwargs):
    """
    Renderiza HTML directamente cuando la versión de Streamlit
    lo permite y utiliza markdown como fallback.
    """
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


def safe_text(value, default="—"):
    """
    Escapa texto para evitar problemas cuando los datos vienen
    directamente desde CSV.
    """
    if value is None or pd.isna(value):
        return default

    value = str(value).strip()

    if not value:
        return default

    return html.escape(value)


def safe_float(value, default=None):
    """
    Conversión segura a float.
    """
    try:
        if value is None or pd.isna(value):
            return default

        return float(value)

    except Exception:
        return default


def normalizar_estado(value):
    """
    Normaliza el estado de una operación para que toda la lógica
    financiera utilice exactamente las mismas reglas.
    """
    if value is None or pd.isna(value):
        return ""

    return str(value).strip().upper()


def obtener_total_activos():
    """
    Calcula dinámicamente el total de activos desde el CSV
    del universo.
    """
    if os.path.exists(ARCHIVO_UNIVERSO):

        for encoding in [
            "utf-8",
            "latin-1",
            "cp1252"
        ]:

            try:

                df = pd.read_csv(
                    ARCHIVO_UNIVERSO,
                    encoding=encoding
                )

                if not df.empty:
                    return len(df)

            except Exception:
                continue

    return 37


TOTAL_ACTIVOS_UNIVERSO = obtener_total_activos()


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data(ttl=30)
def cargar_datos():

    if not os.path.exists(ARCHIVO_HISTORIAL):
        return pd.DataFrame()

    try:

        return pd.read_csv(
            ARCHIVO_HISTORIAL,
            on_bad_lines="skip",
            encoding="utf-8"
        )

    except Exception:

        try:

            return pd.read_csv(
                ARCHIVO_HISTORIAL,
                on_bad_lines="skip",
                encoding="latin-1"
            )

        except Exception:

            return pd.DataFrame()


@st.cache_data(ttl=300)
def obtener_precio_actual(ticker):

    if not ticker:
        return None

    try:

        data = yf.Ticker(
            str(ticker)
        ).history(
            period="1d",
            auto_adjust=False
        )

        if not data.empty:

            close = data["Close"].iloc[-1]

            if pd.notna(close):
                return float(close)

    except Exception:
        pass

    return None


# ============================================================
# PRECIOS ACTUALES DE POSICIONES
# ============================================================

def obtener_precios_activos(df):
    """
    Obtiene una única vez el precio actual de cada ticker activo.

    Si existen varias posiciones activas sobre el mismo ticker,
    todas utilizan exactamente el mismo precio de mercado.
    """

    precios = {}

    if df.empty or "Ticker" not in df.columns:
        return precios

    tickers = (
        df["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    for ticker in tickers:

        if not ticker:
            continue

        precios[ticker] = obtener_precio_actual(
            ticker
        )

    return precios


# ============================================================
# FORMATEADORES
# ============================================================

def formatear_numero(
    value,
    decimals=2,
    suffix=""
):

    if value is None:
        return "—"

    try:

        if pd.isna(value):
            return "—"

        return (
            f"{value:,.{decimals}f}"
            f"{suffix}"
        )

    except Exception:

        return "—"


def formatear_tesis_ia(texto):
    """
    Limpia y formatea la tesis generada por IA.
    """

    if not isinstance(texto, str):
        return "Sin análisis disponible."

    texto = texto.strip()

    if not texto:
        return "Sin análisis disponible."

    texto = texto.replace(
        "Análisis técnico de",
        ""
    ).replace(
        "Indicadores clave:",
        ""
    )

    texto_html = re.sub(
        r"\*\*(.*?)\*\*",
        r"<strong>\1</strong>",
        texto
    )

    texto_html = texto_html.replace(
        "\n",
        "<br>"
    )

    return texto_html.strip()


# ============================================================
# DATA PREPARATION
# ============================================================

def preparar_fecha(df):

    df = df.copy()

    if "Fecha" in df.columns:

        df["Fecha"] = pd.to_datetime(
            df["Fecha"],
            errors="coerce"
        )

    return df


def contar_estado(
    df,
    texto
):

    if "Estado" not in df.columns:
        return 0

    texto_normalizado = str(texto).strip().upper()

    return int(
        df["Estado"]
        .map(normalizar_estado)
        .eq(texto_normalizado)
        .sum()
    )


def calcular_metricas(df):

    if df.empty:

        return {
            "total_alertas": 0,
            "exitos": 0,
            "fallos": 0,
            "activas": 0,
            "win_rate": 0.0,
        }

    total_alertas = len(df)

    exitos = contar_estado(
        df,
        "OBJETIVO_CUMPLIDO"
    )

    fallos = contar_estado(
        df,
        "STOP_SALTADO"
    )

    activas = contar_estado(
        df,
        "ACTIVA"
    )

    total_cerradas = (
        exitos +
        fallos
    )

    win_rate = (
        exitos /
        total_cerradas *
        100
        if total_cerradas
        else 0
    )

    return {
        "total_alertas": total_alertas,
        "exitos": exitos,
        "fallos": fallos,
        "activas": activas,
        "win_rate": win_rate,
    }


# ============================================================
# BENEFICIO DE UNA POSICIÓN ABIERTA
# ============================================================

def calcular_pnl_posicion(
    precio_actual,
    precio_entrada,
    capital=CAPITAL_POR_ALERTA
):
    """
    Calcula el P&L no realizado de una posición basándose
    en el capital asignado por alerta.
    """

    if (
        precio_actual is None
        or precio_entrada is None
    ):
        return None, None

    try:

        precio_actual = float(
            precio_actual
        )

        precio_entrada = float(
            precio_entrada
        )

        if precio_entrada <= 0:
            return None, None

        porcentaje = (
            (
                precio_actual -
                precio_entrada
            )
            /
            precio_entrada
        ) * 100

        beneficio = (
            capital *
            porcentaje /
            100
        )

        return (
            beneficio,
            porcentaje
        )

    except Exception:

        return None, None


# ============================================================
# P&L REALIZADO DE UNA POSICIÓN CERRADA
# ============================================================

def calcular_pnl_cerrada(
    row
):
    """
    Calcula el resultado realizado de UNA posición cerrada.

    OBJETIVO_CUMPLIDO:
        Entrada -> Take Profit

    STOP_SALTADO:
        Entrada -> Stop Loss

    ACTIVA:
        No se considera realizada.

    Cualquier otro estado:
        No genera P&L.
    """

    estado = normalizar_estado(
        row.get("Estado", "")
    )

    # IMPORTANTE:
    # Una posición activa jamás entra aquí como resultado realizado.
    if estado not in {
        "OBJETIVO_CUMPLIDO",
        "STOP_SALTADO"
    }:
        return 0.0, None

    precio_entrada = safe_float(
        row.get("Precio_Alerta")
    )

    if (
        precio_entrada is None
        or precio_entrada <= 0
    ):
        return 0.0, None

    stop_loss = safe_float(
        row.get("Stop_Loss")
    )

    take_profit = safe_float(
        row.get("Take_Profit")
    )

    # Mantiene la lógica original:
    # SL = -4% si no existe
    # TP = +10% si no existe
    if stop_loss is None:
        stop_loss = (
            precio_entrada *
            0.96
        )

    if take_profit is None:
        take_profit = (
            precio_entrada *
            1.10
        )

    if estado == "OBJETIVO_CUMPLIDO":

        if take_profit is None:
            return 0.0, None

        porcentaje = (
            (
                take_profit -
                precio_entrada
            )
            /
            precio_entrada
        ) * 100

        beneficio = (
            CAPITAL_POR_ALERTA *
            porcentaje /
            100
        )

        return beneficio, porcentaje

    if estado == "STOP_SALTADO":

        if stop_loss is None:
            return 0.0, None

        porcentaje = (
            (
                stop_loss -
                precio_entrada
            )
            /
            precio_entrada
        ) * 100

        beneficio = (
            CAPITAL_POR_ALERTA *
            porcentaje /
            100
        )

        return beneficio, porcentaje

    return 0.0, None


# ============================================================
# P&L ABIERTO DE UNA POSICIÓN
# ============================================================

def calcular_pnl_abierto(
    row,
    precios_actuales
):
    """
    Calcula el P&L actual de UNA posición activa.
    """

    estado = normalizar_estado(
        row.get("Estado", "")
    )

    if estado != "ACTIVA":
        return None, None

    ticker = str(
        row.get(
            "Ticker",
            ""
        )
    ).strip()

    if not ticker:
        return None, None

    precio_actual = precios_actuales.get(
        ticker
    )

    precio_entrada = safe_float(
        row.get("Precio_Alerta")
    )

    return calcular_pnl_posicion(
        precio_actual,
        precio_entrada,
        CAPITAL_POR_ALERTA
    )


# ============================================================
# FUENTE ÚNICA DE VERDAD DEL P&L
# ============================================================

def construir_desglose_pnl(
    df,
    precios_actuales
):
    """
    Construye una tabla de auditoría donde CADA FILA del histórico
    tiene una única contribución al resultado acumulado.

    Reglas:

        CERRADA + TP
            -> P&L realizado positivo

        CERRADA + SL
            -> P&L realizado negativo

        ACTIVA
            -> P&L abierto actual

        Cualquier otro estado
            -> 0 €

    El resultado acumulado se obtiene SIEMPRE de:

        P&L TOTAL DE CADA FILA
        --------------------------------
        = P&L REALIZADO + P&L ABIERTO

    De esta forma no existen dos cálculos diferentes
    para la misma cifra.
    """

    columnas = [
        "Indice",
        "Fecha",
        "Empresa",
        "Ticker",
        "Estado",
        "Precio Entrada",
        "Precio Actual",
        "Stop Loss",
        "Take Profit",
        "Tipo Resultado",
        "P&L Realizado",
        "P&L Abierto",
        "P&L Total",
        "% Resultado",
    ]

    if df.empty:
        return pd.DataFrame(
            columns=columnas
        )

    registros = []

    for indice, row in df.iterrows():

        estado = normalizar_estado(
            row.get("Estado", "")
        )

        precio_entrada = safe_float(
            row.get("Precio_Alerta")
        )

        precio_actual = None

        ticker_raw = str(
            row.get(
                "Ticker",
                ""
            )
        ).strip()

        if ticker_raw:
            precio_actual = precios_actuales.get(
                ticker_raw
            )

        stop_loss = safe_float(
            row.get("Stop_Loss")
        )

        take_profit = safe_float(
            row.get("Take_Profit")
        )

        pnl_realizado = 0.0
        pnl_abierto = 0.0
        porcentaje_resultado = None
        tipo_resultado = "SIN RESULTADO"

        # ----------------------------------------------------
        # POSICIÓN ACTIVA
        # ----------------------------------------------------

        if estado == "ACTIVA":

            (
                pnl_abierto_calculado,
                porcentaje_resultado
            ) = calcular_pnl_abierto(
                row,
                precios_actuales
            )

            if pnl_abierto_calculado is not None:

                pnl_abierto = (
                    pnl_abierto_calculado
                )

                tipo_resultado = "ABIERTO"

            else:

                tipo_resultado = "ABIERTO · SIN PRECIO"

        # ----------------------------------------------------
        # POSICIÓN CERRADA
        # ----------------------------------------------------

        elif estado in {
            "OBJETIVO_CUMPLIDO",
            "STOP_SALTADO"
        }:

            (
                pnl_realizado_calculado,
                porcentaje_resultado
            ) = calcular_pnl_cerrada(
                row
            )

            pnl_realizado = (
                pnl_realizado_calculado
            )

            if estado == "OBJETIVO_CUMPLIDO":
                tipo_resultado = "REALIZADO · TP"

            elif estado == "STOP_SALTADO":
                tipo_resultado = "REALIZADO · SL"

        # ----------------------------------------------------
        # RESULTADO TOTAL DE ESTA POSICIÓN
        # ----------------------------------------------------

        pnl_total = (
            pnl_realizado +
            pnl_abierto
        )

        fecha = row.get(
            "Fecha"
        )

        empresa = row.get(
            "Empresa",
            ""
        )

        registros.append(
            {
                "Indice": indice,
                "Fecha": fecha,
                "Empresa": empresa,
                "Ticker": ticker_raw,
                "Estado": estado,
                "Precio Entrada": precio_entrada,
                "Precio Actual": precio_actual,
                "Stop Loss": stop_loss,
                "Take Profit": take_profit,
                "Tipo Resultado": tipo_resultado,
                "P&L Realizado": pnl_realizado,
                "P&L Abierto": pnl_abierto,
                "P&L Total": pnl_total,
                "% Resultado": porcentaje_resultado,
            }
        )

    if not registros:

        return pd.DataFrame(
            columns=columnas
        )

    return pd.DataFrame(
        registros
    )


# ============================================================
# TOTALES DESDE LA ÚNICA FUENTE DE VERDAD
# ============================================================

def calcular_totales_pnl(
    desglose_pnl
):
    """
    Suma exclusivamente el desglose calculado por
    construir_desglose_pnl().
    """

    if desglose_pnl.empty:

        return {
            "beneficio_realizado": 0.0,
            "beneficio_no_realizado": 0.0,
            "beneficio_acumulado": 0.0,
            "posiciones_con_beneficio": 0,
            "posiciones_con_perdida": 0,
        }

    beneficio_realizado = (
        pd.to_numeric(
            desglose_pnl["P&L Realizado"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    beneficio_no_realizado = (
        pd.to_numeric(
            desglose_pnl["P&L Abierto"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    beneficio_acumulado = (
        pd.to_numeric(
            desglose_pnl["P&L Total"],
            errors="coerce"
        )
        .fillna(0)
        .sum()
    )

    abiertas_validas = desglose_pnl[
        desglose_pnl["Tipo Resultado"].isin(
            [
                "ABIERTO",
                "ABIERTO · SIN PRECIO"
            ]
        )
    ]

    posiciones_con_beneficio = int(
        (
            abiertas_validas["P&L Abierto"]
            > 0
        ).sum()
    )

    posiciones_con_perdida = int(
        (
            abiertas_validas["P&L Abierto"]
            < 0
        ).sum()
    )

    return {
        "beneficio_realizado": float(
            beneficio_realizado
        ),
        "beneficio_no_realizado": float(
            beneficio_no_realizado
        ),
        "beneficio_acumulado": float(
            beneficio_acumulado
        ),
        "posiciones_con_beneficio": posiciones_con_beneficio,
        "posiciones_con_perdida": posiciones_con_perdida,
    }


# ============================================================
# RESULTADOS HISTÓRICOS + POSICIONES ABIERTAS
# ============================================================

def calcular_resultados(
    desglose_pnl
):
    """
    Construye la curva acumulada.

    IMPORTANTE:

    La parte histórica contiene únicamente posiciones cerradas.

    Las posiciones activas NO se consideran cerradas históricamente.
    Su P&L actual se incorpora al último punto de la curva.

    Por tanto, el último punto de la curva es exactamente:

        HISTÓRICO REALIZADO
        +
        P&L ACTUAL ABIERTO
        =
        BENEFICIO ACUMULADO REAL
    """

    fechas_curva = []
    beneficios_curva = []

    if desglose_pnl.empty:

        return (
            fechas_curva,
            beneficios_curva
        )

    df_realizado = desglose_pnl[
        desglose_pnl["Tipo Resultado"].isin(
            [
                "REALIZADO · TP",
                "REALIZADO · SL"
            ]
        )
    ].copy()

    beneficio_realizado = 0.0

    # --------------------------------------------------------
    # CURVA HISTÓRICA REALIZADA
    # --------------------------------------------------------

    if (
        not df_realizado.empty
        and "Fecha" in df_realizado.columns
    ):

        df_realizado = (
            df_realizado
            .dropna(subset=["Fecha"])
            .sort_values("Fecha")
        )

        if not df_realizado.empty:

            df_realizado["Fecha_Dia"] = (
                df_realizado["Fecha"]
                .dt.strftime("%Y-%m-%d")
            )

            for fecha, grupo in (
                df_realizado
                .groupby("Fecha_Dia")
            ):

                beneficio_dia = (
                    grupo["P&L Realizado"]
                    .fillna(0)
                    .sum()
                )

                beneficio_realizado += (
                    beneficio_dia
                )

                fechas_curva.append(
                    fecha
                )

                beneficios_curva.append(
                    beneficio_realizado
                )

    # --------------------------------------------------------
    # P&L ABIERTO ACTUAL
    # --------------------------------------------------------

    beneficio_abierto = (
        desglose_pnl["P&L Abierto"]
        .fillna(0)
        .sum()
    )

    beneficio_acumulado = (
        beneficio_realizado +
        beneficio_abierto
    )

    # --------------------------------------------------------
    # ÚLTIMO PUNTO = ACUMULADO REAL
    # --------------------------------------------------------

    fecha_actual = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if fechas_curva:

        if fechas_curva[-1] == fecha_actual:

            beneficios_curva[-1] = (
                beneficio_acumulado
            )

        else:

            fechas_curva.append(
                fecha_actual
            )

            beneficios_curva.append(
                beneficio_acumulado
            )

    elif beneficio_acumulado != 0:

        fechas_curva.append(
            fecha_actual
        )

        beneficios_curva.append(
            beneficio_acumulado
        )

    return (
        fechas_curva,
        beneficios_curva
    )


# ============================================================
# POSITION METRICS
# ============================================================

def calcular_position_percentages(
    stop_loss,
    entrada,
    actual,
    take_profit
):
    """
    Calcula la posición relativa de SL / Entrada / Actual / TP
    dentro de una escala visual.
    """

    values = [
        v
        for v in [
            stop_loss,
            entrada,
            actual,
            take_profit
        ]
        if v is not None
    ]

    if len(values) < 2:
        return None

    minimum = min(values)
    maximum = max(values)

    rango = (
        maximum -
        minimum
    )

    if rango <= 0:
        return None

    margen = rango * 0.08

    minimum -= margen
    maximum += margen

    rango = (
        maximum -
        minimum
    )

    def position(value):

        if value is None:
            return None

        pct = (
            (
                value -
                minimum
            )
            /
            rango
            *
            100
        )

        return max(
            3,
            min(
                97,
                pct
            )
        )

    return {
        "sl": position(stop_loss),
        "entry": position(entrada),
        "current": position(actual),
        "tp": position(take_profit),
    }


# ============================================================
# DESIGN SYSTEM (CSS)
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

:root {
    --bg: #f6f8fb;
    --surface: #ffffff;
    --surface-soft: #f8fafc;
    --border: #e7ebf2;
    --border-soft: #eef1f5;
    --text: #111827;
    --text-secondary: #64748b;
    --text-tertiary: #94a3b8;
    --blue: #2563eb;
    --green: #16a34a;
    --green-soft: #ecfdf3;
    --red: #dc2626;
    --shadow: 0 1px 2px rgba(15,23,42,.02), 0 8px 30px rgba(15,23,42,.035);
    --shadow-hover: 0 12px 35px rgba(15,23,42,.07);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: var(--bg);
    color: var(--text);
}

#MainMenu, footer, section[data-testid="stSidebar"] {
    display: none !important;
}

.block-container {
    max-width: 1380px;
    padding-top: 30px;
    padding-bottom: 60px;
    padding-left: 38px;
    padding-right: 38px;
}

.hero {
    margin-bottom: 25px;
}

.hero-title {
    margin: 0;
    font-family: 'Plus Jakarta Sans';
    font-size: 32px;
    line-height: 1.1;
    letter-spacing: -.045em;
    font-weight: 800;
    color: var(--text);
}

.hero-subtitle {
    margin-top: 8px;
    color: var(--text-secondary);
    font-size: 13px;
}

.portfolio-summary {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 32px;
}

.summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 17px 18px;
    box-shadow: var(--shadow);
    transition: .2s ease;
}

.summary-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
}

.summary-label {
    color: var(--text-tertiary);
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: .07em;
    font-weight: 800;
    margin-bottom: 8px;
}

.summary-value {
    font-family: 'Plus Jakarta Sans';
    font-size: 21px;
    line-height: 1.05;
    font-weight: 800;
    letter-spacing: -.035em;
    color: var(--text);
}

.summary-detail {
    margin-top: 6px;
    color: var(--text-secondary);
    font-size: 10px;
    font-weight: 600;
}

.section-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin: 4px 0 16px;
}

.section-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 18px;
    font-weight: 800;
    letter-spacing: -.025em;
    color: var(--text);
}

.section-subtitle {
    font-size: 11px;
    color: var(--text-tertiary);
    margin-top: 3px;
}

.asset-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 22px;
    margin-bottom: 15px;
    box-shadow: var(--shadow);
    transition: all .22s ease;
}

.asset-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-hover);
    border-color: #dce3ed;
}

.asset-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 16px;
}

.asset-identity {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
}

.asset-icon {
    width: 46px;
    height: 46px;
    min-width: 46px;
    border-radius: 14px;
    background: #eff6ff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}

.asset-company {
    font-family: 'Plus Jakarta Sans';
    font-size: 16px;
    font-weight: 800;
    color: var(--text);
    line-height: 1.2;
}

.asset-ticker {
    color: var(--text-tertiary);
    font-size: 11px;
    font-weight: 700;
    margin-left: 5px;
}

.asset-sector {
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 3px;
}

.asset-right {
    text-align: right;
}

.new-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--green-soft);
    color: #15803d;
    border: 1px solid #dcfce7;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 8px;
    font-weight: 800;
    letter-spacing: .07em;
    margin-bottom: 5px;
}

.current-price {
    font-family: 'Plus Jakarta Sans';
    font-size: 22px;
    font-weight: 800;
    color: var(--text);
    letter-spacing: -.03em;
}

.price-label {
    font-size: 9px;
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: .08em;
    font-weight: 800;
}

.performance-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    background: var(--surface-soft);
    border-radius: 11px;
    margin-bottom: 17px;
}

.performance-label {
    font-size: 10px;
    color: var(--text-secondary);
    font-weight: 700;
}

.performance-value {
    font-family: 'Plus Jakarta Sans';
    font-size: 13px;
    font-weight: 800;
}

.performance-positive {
    color: var(--green);
}

.performance-negative {
    color: var(--red);
}

.performance-neutral {
    color: var(--text-secondary);
}

.position-wrapper {
    margin: 3px 3px 22px;
}

.position-labels {
    display: flex;
    justify-content: space-between;
    margin-bottom: 9px;
}

.position-label {
    font-size: 8px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .06em;
    color: var(--text-tertiary);
}

.position-track {
    height: 6px;
    background: #e8edf4;
    border-radius: 999px;
    position: relative;
}

.position-risk {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    background: #fecaca;
    border-radius: 999px;
}

.position-reward {
    position: absolute;
    top: 0;
    bottom: 0;
    background: #bbf7d0;
    border-radius: 999px;
}

.position-marker {
    position: absolute;
    top: 50%;
    width: 12px;
    height: 12px;
    transform: translate(-50%, -50%);
    border-radius: 50%;
    background: white;
    border: 3px solid;
    box-shadow: 0 1px 5px rgba(15,23,42,.15);
}

.marker-sl {
    border-color: var(--red);
}

.marker-entry {
    border-color: var(--blue);
}

.marker-current {
    width: 16px;
    height: 16px;
    border: 4px solid white;
    background: var(--blue);
    box-shadow: 0 0 0 2px var(--blue), 0 2px 7px rgba(37,99,235,.3);
}

.marker-tp {
    border-color: var(--green);
}

.position-values {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 10px;
}

.position-value {
    font-size: 10px;
    color: var(--text-secondary);
}

.position-value strong {
    display: block;
    color: var(--text);
    font-family: 'Plus Jakarta Sans';
    font-size: 11px;
    margin-top: 2px;
}

.params-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
    margin-bottom: 17px;
}

.param {
    background: var(--surface-soft);
    border: 1px solid var(--border-soft);
    border-radius: 12px;
    padding: 11px 12px;
}

.param-label {
    color: var(--text-tertiary);
    font-size: 8px;
    text-transform: uppercase;
    letter-spacing: .07em;
    font-weight: 800;
}

.param-value {
    margin-top: 4px;
    font-family: 'Plus Jakarta Sans';
    font-size: 13px;
    font-weight: 800;
    color: var(--text);
}

.ai-box {
    background: linear-gradient(135deg, #f7faff, #f8fafc);
    border: 1px solid #e6edff;
    border-radius: 14px;
    padding: 14px 16px;
}

.ai-header {
    display: flex;
    align-items: center;
    gap: 7px;
    color: var(--blue);
    font-size: 9px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .08em;
    margin-bottom: 6px;
}

.ai-text {
    color: #475569;
    font-size: 12px;
    line-height: 1.65;
}

.result-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 22px;
    box-shadow: var(--shadow);
}

.result-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 20px;
}

.result-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 16px;
    font-weight: 800;
}

.result-subtitle {
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 3px;
}

.result-number {
    font-family: 'Plus Jakarta Sans';
    font-size: 23px;
    font-weight: 800;
    text-align: right;
}

.result-percent {
    font-size: 10px;
    color: var(--text-secondary);
    text-align: right;
    margin-top: 2px;
}

.metric-list {
    display: flex;
    flex-direction: column;
}

.metric-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 0;
    border-bottom: 1px solid var(--border-soft);
}

.metric-row:last-child {
    border-bottom: 0;
}

.metric-name {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 600;
}

.metric-value {
    font-family: 'Plus Jakarta Sans';
    font-size: 13px;
    font-weight: 800;
}

.empty-state {
    background: var(--surface);
    border: 1px dashed #dce3ed;
    border-radius: 18px;
    padding: 45px 20px;
    text-align: center;
}

.empty-icon {
    font-size: 28px;
    margin-bottom: 10px;
}

.empty-title {
    font-family: 'Plus Jakarta Sans';
    font-weight: 800;
    font-size: 15px;
}

.empty-text {
    color: var(--text-secondary);
    font-size: 12px;
    margin-top: 5px;
}

.history-header {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: var(--shadow);
}

.history-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 16px;
    font-weight: 800;
}

.history-subtitle {
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 4px;
}

.app-footer {
    display: flex;
    justify-content: space-between;
    gap: 15px;
    margin-top: 48px;
    padding-top: 18px;
    border-top: 1px solid var(--border);
    color: var(--text-tertiary);
    font-size: 9px;
    font-weight: 600;
}

.audit-total {
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 14px;
    margin-bottom: 12px;
}

.audit-title {
    font-family: 'Plus Jakarta Sans';
    font-size: 12px;
    font-weight: 800;
    color: var(--text);
}

.audit-subtitle {
    color: var(--text-secondary);
    font-size: 10px;
    margin-top: 3px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# CARGAR HISTÓRICO
# ============================================================

df_hist = preparar_fecha(
    cargar_datos()
)

metricas = calcular_metricas(
    df_hist
)

total_alertas = metricas["total_alertas"]
exitos = metricas["exitos"]
fallos = metricas["fallos"]
activas = metricas["activas"]
win_rate = metricas["win_rate"]


# ============================================================
# POSICIONES ACTIVAS
# ============================================================

if (
    not df_hist.empty
    and "Estado" in df_hist.columns
):

    # IMPORTANTE:
    # Exactamente ACTIVA.
    #
    # Antes utilizábamos contains("ACTIVA"), que podía incluir
    # estados que simplemente contuvieran esa palabra.
    df_activas_global = df_hist[
        df_hist["Estado"]
        .map(normalizar_estado)
        .eq("ACTIVA")
    ].copy()

else:

    df_activas_global = pd.DataFrame()


# ============================================================
# PRECIOS ACTUALES
# ============================================================

precios_actuales = obtener_precios_activos(
    df_activas_global
)


# ============================================================
# DESGLOSE ÚNICO DEL P&L
# ============================================================

desglose_pnl = construir_desglose_pnl(
    df_hist,
    precios_actuales
)


# ============================================================
# TOTALES DEFINITIVOS
# ============================================================

totales_pnl = calcular_totales_pnl(
    desglose_pnl
)

beneficio_realizado = (
    totales_pnl[
        "beneficio_realizado"
    ]
)

beneficio_no_realizado = (
    totales_pnl[
        "beneficio_no_realizado"
    ]
)

beneficio_acumulado = (
    totales_pnl[
        "beneficio_acumulado"
    ]
)

posiciones_con_beneficio = (
    totales_pnl[
        "posiciones_con_beneficio"
    ]
)

posiciones_con_perdida = (
    totales_pnl[
        "posiciones_con_perdida"
    ]
)


# ============================================================
# VALIDACIÓN INTERNA
# ============================================================

# Esta comprobación garantiza que el total que mostramos
# sea matemáticamente igual a:
#
# HISTÓRICO + ABIERTO

total_recalculado = (
    beneficio_realizado +
    beneficio_no_realizado
)

if abs(
    beneficio_acumulado -
    total_recalculado
) > 0.000001:

    beneficio_acumulado = (
        total_recalculado
    )


# ============================================================
# CAPITAL Y RENTABILIDAD
# ============================================================

total_operaciones_historicas = max(
    1,
    len(df_hist)
)

CAPITAL_INICIAL = max(
    3600.0,
    total_operaciones_historicas *
    CAPITAL_POR_ALERTA
)

rentabilidad_pct = (
    beneficio_acumulado
    /
    CAPITAL_INICIAL
    *
    100
    if CAPITAL_INICIAL
    else 0
)

color_resultado = (
    "#16a34a"
    if beneficio_acumulado >= 0
    else "#dc2626"
)


# ============================================================
# CURVA DE RESULTADOS
# ============================================================

(
    fechas_curva,
    beneficios_curva
) = calcular_resultados(
    desglose_pnl
)


# ============================================================
# HERO
# ============================================================

render_html(
    """
<div class="hero">
    <h1 class="hero-title">Tu radar de inversión</h1>
    <div class="hero-subtitle">
        Señales cuantitativas, cartera y resultados en un solo lugar.
    </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# PORTFOLIO SUMMARY
# ============================================================

render_html(
    f"""
<div class="portfolio-summary">

    <div class="summary-card">
        <div class="summary-label">
            Beneficio total acumulado
        </div>

        <div class="summary-value"
             style="color:{color_resultado};">
            {beneficio_acumulado:+,.2f} €
        </div>

        <div class="summary-detail">
            Histórico + posiciones abiertas
        </div>
    </div>

    <div class="summary-card">

        <div class="summary-label">
            Rentabilidad
        </div>

        <div class="summary-value"
             style="color:{color_resultado};">
            {rentabilidad_pct:+.2f}%
        </div>

        <div class="summary-detail">
            Sobre {CAPITAL_INICIAL:,.0f} € simulados
        </div>

    </div>

    <div class="summary-card">

        <div class="summary-label">
            Posiciones activas
        </div>

        <div class="summary-value">
            {activas}
        </div>

        <div class="summary-detail">
            {TOTAL_ACTIVOS_UNIVERSO} activos monitorizados
        </div>

    </div>

    <div class="summary-card">

        <div class="summary-label">
            Win Rate
        </div>

        <div class="summary-value">
            {win_rate:.1f}%
        </div>

        <div class="summary-detail">
            {exitos} TP · {fallos} SL
        </div>

    </div>

</div>
""",
    unsafe_allow_html=True,
)


if df_hist.empty:

    render_html(
        """
<div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">
        Todavía no hay señales registradas
    </div>
    <div class="empty-text">
        Cuando Alura Quant genere señales aparecerán aquí.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.stop()


# ============================================================
# NAVEGACIÓN
# ============================================================

tab_cartera, tab_resultados, tab_historial = st.tabs(
    [
        "Cartera",
        "Resultados",
        "Histórico",
    ]
)


# ============================================================
# 1. CARTERA
# ============================================================

with tab_cartera:

    render_html(
        """
<div class="section-header">
    <div>
        <div class="section-title">
            Posiciones activas
        </div>
        <div class="section-subtitle">
            Señales actualmente monitorizadas por el sistema cuantitativo.
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    df_activas = df_activas_global.copy()

    if df_activas.empty:

        render_html(
            """
<div class="empty-state">
    <div class="empty-icon">◌</div>
    <div class="empty-title">
        No hay posiciones activas
    </div>
    <div class="empty-text">
        Las nuevas señales aparecerán automáticamente en esta sección.
    </div>
</div>
""",
            unsafe_allow_html=True,
        )

    else:

        col_filtro_1, col_filtro_2 = st.columns(
            [1, 1],
            gap="small"
        )

        with col_filtro_1:

            if "Sector" in df_activas.columns:

                sectores = sorted(
                    df_activas[
                        "Sector"
                    ]
                    .dropna()
                    .astype(str)
                    .unique()
                    .tolist()
                )

            else:

                sectores = []

            sectores_disponibles = [
                "Todos los sectores"
            ] + sectores

            filtro_sector = st.selectbox(
                "Sector",
                sectores_disponibles,
                label_visibility="collapsed"
            )

        with col_filtro_2:

            busqueda_cartera = st.text_input(
                "Buscar",
                placeholder="⌕  Buscar empresa o ticker...",
                label_visibility="collapsed"
            )

        df_filtrada = df_activas.copy()

        if (
            filtro_sector != "Todos los sectores"
            and "Sector" in df_filtrada.columns
        ):

            df_filtrada = df_filtrada[
                df_filtrada[
                    "Sector"
                ].astype(str) == filtro_sector
            ]

        if busqueda_cartera:

            mask = (
                df_filtrada
                .astype(str)
                .apply(
                    lambda col: col.str.contains(
                        busqueda_cartera,
                        case=False,
                        na=False,
                        regex=False
                    )
                )
                .any(axis=1)
            )

            df_filtrada = df_filtrada[
                mask
            ]

        render_html(
            f"""
<div style="margin:8px 0 14px; color:#94a3b8; font-size:10px; font-weight:700;">
    MOSTRANDO {len(df_filtrada)} POSICIONES
</div>
""",
            unsafe_allow_html=True,
        )

        for indice, row in df_filtrada.iterrows():

            icono = safe_text(
                row.get("Icono"),
                "📈"
            )

            empresa = safe_text(
                row.get(
                    "Empresa",
                    row.get(
                        "Ticker",
                        "Activo"
                    )
                ),
                "Activo"
            )

            ticker = safe_text(
                row.get(
                    "Ticker"
                ),
                ""
            )

            ticker_raw = str(
                row.get(
                    "Ticker",
                    ""
                )
            ).strip()

            sector = safe_text(
                row.get(
                    "Sector"
                ),
                "Mercado Continuo"
            )

            es_nuevo = False

            if (
                "Fecha" in row
                and pd.notna(row["Fecha"])
            ):

                try:

                    fecha_alerta = (
                        row["Fecha"]
                        .to_pydatetime()
                        .replace(
                            tzinfo=None
                        )
                    )

                    if (
                        datetime.now() -
                        fecha_alerta
                        <=
                        timedelta(hours=48)
                    ):

                        es_nuevo = True

                except Exception:
                    pass

            badge_nuevo = (
                '<div class="new-badge">✦ NUEVO</div>'
                if es_nuevo
                else ""
            )

            precio_actual = (
                precios_actuales.get(
                    ticker_raw
                )
                if ticker_raw
                else None
            )

            precio_entrada = safe_float(
                row.get(
                    "Precio_Alerta"
                )
            )

            stop_loss = safe_float(
                row.get(
                    "Stop_Loss"
                )
            )

            take_profit = safe_float(
                row.get(
                    "Take_Profit"
                )
            )

            ratio_rr = safe_float(
                row.get(
                    "Ratio_RR"
                )
            )

            # ------------------------------------------------
            # IMPORTANTE:
            # El P&L de la tarjeta sale de la MISMA función
            # utilizada por el total acumulado.
            # ------------------------------------------------

            (
                beneficio_posicion,
                porcentaje_posicion
            ) = calcular_pnl_abierto(
                row,
                precios_actuales
            )

            if (
                beneficio_posicion is None
                or porcentaje_posicion is None
            ):

                performance_text = "—"
                performance_class = (
                    "performance-neutral"
                )

            else:

                performance_text = (
                    f"{porcentaje_posicion:+.2f}% · "
                    f"{beneficio_posicion:+,.2f} €"
                )

                performance_class = (
                    "performance-positive"
                    if beneficio_posicion >= 0
                    else "performance-negative"
                )

            positions = calcular_position_percentages(
                stop_loss,
                precio_entrada,
                precio_actual,
                take_profit
            )

            if positions:

                sl_pct = (
                    positions["sl"]
                    if positions["sl"] is not None
                    else 0
                )

                entry_pct = (
                    positions["entry"]
                    if positions["entry"] is not None
                    else 25
                )

                current_pct = (
                    positions["current"]
                    if positions["current"] is not None
                    else entry_pct
                )

                tp_pct = (
                    positions["tp"]
                    if positions["tp"] is not None
                    else 100
                )

                risk_left = (
                    min(
                        entry_pct,
                        current_pct
                    )
                    -
                    sl_pct
                )

                reward_left = (
                    tp_pct
                    -
                    max(
                        entry_pct,
                        current_pct
                    )
                )

                risk_width = max(
                    0,
                    risk_left
                )

                reward_width = max(
                    0,
                    reward_left
                )

                position_tracker = f"""
<div class="position-wrapper">

    <div class="position-labels">
        <span class="position-label">Stop</span>
        <span class="position-label">Entrada</span>
        <span class="position-label">Actual</span>
        <span class="position-label">Take Profit</span>
    </div>

    <div class="position-track">

        <div class="position-risk"
             style="
                left:{sl_pct:.2f}%;
                width:{risk_width:.2f}%;
             ">
        </div>

        <div class="position-reward"
             style="
                left:{current_pct:.2f}%;
                width:{reward_width:.2f}%;
             ">
        </div>

        <div class="position-marker marker-sl"
             style="left:{sl_pct:.2f}%;"></div>

        <div class="position-marker marker-entry"
             style="left:{entry_pct:.2f}%;"></div>

        <div class="position-marker marker-current"
             style="left:{current_pct:.2f}%;"></div>

        <div class="position-marker marker-tp"
             style="left:{tp_pct:.2f}%;"></div>

    </div>

    <div class="position-values">

        <div class="position-value">
            Stop Loss
            <strong>
                {formatear_numero(stop_loss, 2)}
            </strong>
        </div>

        <div class="position-value">
            Entrada
            <strong>
                {formatear_numero(precio_entrada, 2)}
            </strong>
        </div>

        <div class="position-value">
            Actual
            <strong>
                {formatear_numero(precio_actual, 2)}
            </strong>
        </div>

        <div class="position-value">
            Take Profit
            <strong>
                {formatear_numero(take_profit, 2)}
            </strong>
        </div>

    </div>

</div>
"""

            else:

                position_tracker = ""


            ratio_rr_text = (
                f"{ratio_rr:.1f}x"
                if ratio_rr is not None
                else "—"
            )

            precio_actual_text = (
                f"{precio_actual:,.2f}"
                if precio_actual is not None
                else "—"
            )

            analisis_ia = formatear_tesis_ia(
                row.get(
                    "Analisis_IA",
                    ""
                )
            )

            render_html(
                f"""
<div class="asset-card">

    <div class="asset-header">

        <div class="asset-identity">

            <div class="asset-icon">
                {icono}
            </div>

            <div>

                <div class="asset-company">
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

            {badge_nuevo}

            <div class="current-price">
                {precio_actual_text}
            </div>

            <div class="price-label">
                Precio actual
            </div>

        </div>

    </div>

    <div class="performance-row">

        <div class="performance-label">
            Rendimiento desde entrada
        </div>

        <div class="performance-value {performance_class}">
            {performance_text}
        </div>

    </div>

    {position_tracker}

    <div class="params-grid">

        <div class="param">

            <div class="param-label">
                Precio entrada
            </div>

            <div class="param-value">
                {formatear_numero(precio_entrada, 2)}
            </div>

        </div>

        <div class="param">

            <div class="param-label">
                Stop Loss
            </div>

            <div class="param-value"
                 style="color:#dc2626;">
                {formatear_numero(stop_loss, 2)}
            </div>

        </div>

        <div class="param">

            <div class="param-label">
                Take Profit
            </div>

            <div class="param-value"
                 style="color:#16a34a;">
                {formatear_numero(take_profit, 2)}
            </div>

        </div>

        <div class="param">

            <div class="param-label">
                Risk / Reward
            </div>

            <div class="param-value"
                 style="color:#2563eb;">
                {ratio_rr_text}
            </div>

        </div>

    </div>

    <div class="ai-box">

        <div class="ai-header">
            ✦ Tesis del analista cuantitativo
        </div>

        <div class="ai-text">
            {analisis_ia}
        </div>

    </div>

</div>
""",
                unsafe_allow_html=True,
            )


# ============================================================
# 2. RESULTADOS
# ============================================================

with tab_resultados:

    render_html(
        """
<div class="section-header">
    <div>
        <div class="section-title">
            Rendimiento
        </div>

        <div class="section-subtitle">
            Resultado acumulado real:
            histórico realizado + posiciones abiertas.
        </div>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    col_g1, col_g2 = st.columns(
        [1.55, 0.75],
        gap="large"
    )

    with col_g1:

        render_html(
            f"""
<div class="result-card">

    <div class="result-header">

        <div>

            <div class="result-title">
                Evolución de beneficios
            </div>

            <div class="result-subtitle">
                Resultado acumulado real de la cartera
            </div>

        </div>

        <div>

            <div class="result-number"
                 style="color:{color_resultado};">

                {beneficio_acumulado:+,.2f} €

            </div>

            <div class="result-percent">
                {rentabilidad_pct:+.2f}% de retorno
            </div>

        </div>

    </div>

    <div style="
        display:flex;
        gap:16px;
        font-size:10px;
        color:#94a3b8;
        font-weight:600;
        margin-bottom:3px;
        flex-wrap:wrap;
    ">

        <span>
            ● Realizado:
            {beneficio_realizado:+,.2f} €
        </span>

        <span>
            ● Abierto:
            {beneficio_no_realizado:+,.2f} €
        </span>

        <span>
            ● Acumulado:
            {beneficio_acumulado:+,.2f} €
        </span>

    </div>

</div>
""",
            unsafe_allow_html=True,
        )

        if fechas_curva:

            df_beneficio = pd.DataFrame(
                {
                    "Beneficio Neto (€)":
                        beneficios_curva
                },
                index=fechas_curva
            )

            st.line_chart(
                df_beneficio,
                height=320
            )

        else:

            render_html(
                """
<div class="empty-state">

    <div class="empty-title">
        Sin suficientes datos
    </div>

    <div class="empty-text">
        Se requieren registros históricos para construir la curva.
    </div>

</div>
""",
                unsafe_allow_html=True,
            )


    with col_g2:

        render_html(
            f"""
<div class="result-card">

    <div class="result-title">
        Métricas clave
    </div>

    <div class="result-subtitle">
        Estado operativo del sistema
    </div>

    <div class="metric-list">

        <div class="metric-row">
            <span class="metric-name">
                Señales activas
            </span>

            <span class="metric-value"
                  style="color:#2563eb;">
                {activas}
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Posiciones en beneficio
            </span>

            <span class="metric-value"
                  style="color:#16a34a;">
                {posiciones_con_beneficio}
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Take Profit alcanzado
            </span>

            <span class="metric-value"
                  style="color:#16a34a;">
                {exitos}
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Stop Loss saltado
            </span>

            <span class="metric-value"
                  style="color:#dc2626;">
                {fallos}
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Win Rate
            </span>

            <span class="metric-value">
                {win_rate:.1f}%
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Beneficio realizado
            </span>

            <span class="metric-value"
                  style="color:{
                    '#16a34a'
                    if beneficio_realizado >= 0
                    else '#dc2626'
                  };">
                {beneficio_realizado:+,.2f} €
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                P&L posiciones abiertas
            </span>

            <span class="metric-value"
                  style="color:{
                    '#16a34a'
                    if beneficio_no_realizado >= 0
                    else '#dc2626'
                  };">
                {beneficio_no_realizado:+,.2f} €
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Beneficio total acumulado
            </span>

            <span class="metric-value"
                  style="color:{color_resultado};">
                {beneficio_acumulado:+,.2f} €
            </span>
        </div>

        <div class="metric-row">
            <span class="metric-name">
                Capital simulado
            </span>

            <span class="metric-value">
                {CAPITAL_INICIAL:,.0f} €
            </span>
        </div>

    </div>

</div>
""",
            unsafe_allow_html=True,
        )


    # ========================================================
    # AUDITORÍA DEL RESULTADO
    # ========================================================

    st.markdown("")

    with st.expander(
        "Auditoría del P&L · comprobar posición por posición"
    ):

        render_html(
            f"""
<div class="audit-total">

    <div class="audit-title">
        Resultado acumulado real
    </div>

    <div class="audit-subtitle">
        {beneficio_realizado:+,.2f} €
        histórico
        +
        {beneficio_no_realizado:+,.2f} €
        posiciones abiertas
        =
        <strong>
            {beneficio_acumulado:+,.2f} €
        </strong>
    </div>

</div>
""",
            unsafe_allow_html=True,
        )

        if not desglose_pnl.empty:

            df_auditoria = desglose_pnl.copy()

            df_auditoria = df_auditoria[
                [
                    "Fecha",
                    "Empresa",
                    "Ticker",
                    "Estado",
                    "Precio Entrada",
                    "Precio Actual",
                    "Tipo Resultado",
                    "P&L Realizado",
                    "P&L Abierto",
                    "P&L Total",
                    "% Resultado",
                ]
            ]

            df_auditoria["Fecha"] = (
                pd.to_datetime(
                    df_auditoria["Fecha"],
                    errors="coerce"
                )
                .dt.strftime("%Y-%m-%d")
            )

            st.dataframe(
                df_auditoria,
                use_container_width=True,
                height=500,
                hide_index=True
            )

            # ------------------------------------------------
            # Comprobación matemática visible
            # ------------------------------------------------

            suma_filas = (
                df_auditoria["P&L Total"]
                .fillna(0)
                .sum()
            )

            diferencia = (
                beneficio_acumulado -
                suma_filas
            )

            if abs(diferencia) < 0.01:

                st.success(
                    f"✓ Auditoría correcta. "
                    f"La suma de todas las posiciones es "
                    f"{suma_filas:+,.2f} € y coincide con "
                    f"el acumulado."
                )

            else:

                st.error(
                    f"⚠ Diferencia detectada: "
                    f"{diferencia:+,.4f} €"
                )

        else:

            st.info(
                "No hay datos suficientes para construir la auditoría."
            )


# ============================================================
# 3. HISTÓRICO
# ============================================================

with tab_historial:

    render_html(
        """
<div class="history-header">

    <div class="history-title">
        Registro histórico
    </div>

    <div class="history-subtitle">
        Auditoría completa de las señales generadas por Alura Quant.
    </div>

</div>
""",
        unsafe_allow_html=True,
    )

    df_cerradas = df_hist.copy()

    if not df_cerradas.empty:

        col_f1, col_f2 = st.columns(
            [1, 1],
            gap="small"
        )

        with col_f1:

            if "Estado" in df_cerradas.columns:

                estados_posibles = sorted(
                    df_cerradas[
                        "Estado"
                    ]
                    .astype(str)
                    .unique()
                    .tolist()
                )

            else:

                estados_posibles = []

            filtro_est = st.multiselect(
                "Estado operativo",
                estados_posibles,
                default=estados_posibles,
                label_visibility="collapsed"
            )

        with col_f2:

            busq_hist = st.text_input(
                "Buscar histórico",
                placeholder="⌕  Buscar empresa, ticker o estado...",
                label_visibility="collapsed"
            )

        df_view = df_cerradas.copy()

        if (
            filtro_est
            and "Estado" in df_view.columns
        ):

            df_view = df_view[
                df_view[
                    "Estado"
                ]
                .astype(str)
                .isin(filtro_est)
            ]

        if busq_hist:

            mask_h = (
                df_view
                .astype(str)
                .apply(
                    lambda col: col.str.contains(
                        busq_hist,
                        case=False,
                        na=False,
                        regex=False
                    )
                )
                .any(axis=1)
            )

            df_view = df_view[
                mask_h
            ]

        render_html(
            f"""
<div style="
    margin:8px 0 10px;
    color:#94a3b8;
    font-size:10px;
    font-weight:700;
">
    {len(df_view)} REGISTROS
</div>
""",
            unsafe_allow_html=True,
        )

        st.dataframe(
            df_view,
            use_container_width=True,
            height=480,
            hide_index=True
        )

    else:

        render_html(
            """
<div class="empty-state">

    <div class="empty-title">
        No hay registros históricos
    </div>

    <div class="empty-text">
        Las señales cerradas aparecerán aquí.
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
<div class="app-footer">

    <span>
        ALURA QUANT · INVESTMENT INTELLIGENCE
    </span>

    <span>
        Simulación cuantitativa automatizada · Uso interno
    </span>

</div>
""",
    unsafe_allow_html=True,
)