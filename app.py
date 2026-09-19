# ============================================================
# ALURA QUANT — INVESTMENT INTELLIGENCE UI (VERSIÓN CORREGIDA)
# ============================================================
import os
import re
import html
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

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
    if hasattr(st, "html"):
        st.html(content)
    else:
        st.markdown(content, unsafe_allow_html=True)


def safe_text(value, default="—"):
    if value is None or pd.isna(value):
        return default
    value = str(value).strip()
    return html.escape(value) if value else default


def safe_float(value, default=None):
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


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


TOTAL_ACTIVOS_UNIVERSO = obtener_total_activos()


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data(ttl=30)
def cargar_datos():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return pd.DataFrame()
    try:
        return pd.read_csv(ARCHIVO_HISTORIAL, on_bad_lines="skip", encoding="utf-8")
    except Exception:
        try:
            return pd.read_csv(ARCHIVO_HISTORIAL, on_bad_lines="skip", encoding="latin-1")
        except Exception:
            return pd.DataFrame()


@st.cache_data(ttl=300)
def obtener_precio_actual(ticker):
    if not ticker:
        return None
    try:
        data = yf.Ticker(str(ticker)).history(period="1d", auto_adjust=False)
        if not data.empty:
            close = data["Close"].iloc[-1]
            if pd.notna(close):
                return float(close)
    except Exception:
        pass
    return None


def obtener_precios_activos(df):
    precios = {}
    if df.empty or "Ticker" not in df.columns:
        return precios
    tickers = df["Ticker"].dropna().astype(str).str.strip().unique().tolist()
    for ticker in tickers:
        if not ticker:
            continue
        precios[ticker] = obtener_precio_actual(ticker)
    return precios


def formatear_numero(value, decimals=2, suffix=""):
    if value is None:
        return "—"
    try:
        return f"{value:,.{decimals}f}{suffix}"
    except Exception:
        return "—"


def formatear_tesis_ia(texto):
    if not isinstance(texto, str):
        return "Sin análisis disponible."
    texto = texto.strip()
    if not texto:
        return "Sin análisis disponible."
    texto = texto.replace("Análisis técnico de", "").replace("Indicadores clave:", "")
    texto_html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", texto)
    return texto_html.replace("\n", "<br>").strip()


def preparar_fecha(df):
    df = df.copy()
    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    return df


def contar_estado(df, texto):
    if "Estado" not in df.columns:
        return 0
    return int(df["Estado"].astype(str).str.contains(texto, na=False, regex=False).sum())


def calcular_metricas(df):
    if df.empty:
        return {"total_alertas": 0, "exitos": 0, "fallos": 0, "activas": 0, "win_rate": 0.0}
    total_alertas = len(df)
    exitos = contar_estado(df, "OBJETIVO_CUMPLIDO")
    fallos = contar_estado(df, "STOP_SALTADO")
    activas = contar_estado(df, "ACTIVA")
    total_cerradas = exitos + fallos
    win_rate = (exitos / total_cerradas * 100) if total_cerradas else 0.0
    return {"total_alertas": total_alertas, "exitos": exitos, "fallos": fallos, "activas": activas, "win_rate": win_rate}


def calcular_pnl_posicion(precio_actual, precio_entrada, capital=CAPITAL_POR_ALERTA):
    if precio_actual is None or precio_entrada is None:
        return None, None
    try:
        precio_actual = float(precio_actual)
        precio_entrada = float(precio_entrada)
        if precio_entrada <= 0:
            return None, None
        porcentaje = ((precio_actual - precio_entrada) / precio_entrada) * 100
        beneficio = capital * porcentaje / 100
        return beneficio, porcentaje
    except Exception:
        return None, None


def calcular_beneficio_realizado(df):
    beneficio = 0.0
    if df.empty:
        return beneficio
    for _, row in df.iterrows():
        estado = str(row.get("Estado", ""))
        precio_entrada = safe_float(row.get("Precio_Alerta"), 100.0)
        stop_loss = safe_float(row.get("Stop_Loss"), precio_entrada * 0.96 if precio_entrada else None)
        take_profit = safe_float(row.get("Take_Profit"), precio_entrada * 1.10 if precio_entrada else None)
        
        if precio_entrada is None or precio_entrada <= 0:
            continue
        pct_ganancia = (take_profit - precio_entrada) / precio_entrada
        pct_perdida = (precio_entrada - stop_loss) / precio_entrada

        if "OBJETIVO_CUMPLIDO" in estado:
            beneficio += (CAPITAL_POR_ALERTA * pct_ganancia)
        elif "STOP_SALTADO" in estado:
            beneficio -= (CAPITAL_POR_ALERTA * pct_perdida)
    return beneficio


def calcular_beneficio_no_realizado(df_activas, precios_actuales):
    beneficio_total = 0.0
    posiciones_ganadoras = 0
    posiciones_perdedoras = 0
    if df_activas.empty:
        return 0.0, 0, 0

    for _, row in df_activas.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        if not ticker:
            continue
        precio_actual = precios_actuales.get(ticker)
        precio_entrada = safe_float(row.get("Precio_Alerta"))
        beneficio, _ = calcular_pnl_posicion(precio_actual, precio_entrada)
        
        if beneficio is None:
            continue
        beneficio_total += beneficio
        if beneficio > 0:
            posiciones_ganadoras += 1
        elif beneficio < 0:
            posiciones_perdedoras += 1
    return beneficio_total, posiciones_ganadoras, posiciones_perdedoras


def calcular_resultados(df, beneficio_no_realizado=0.0):
    beneficio_realizado = 0.0
    fechas_curva, beneficios_curva = [], []
    if df.empty or "Fecha" not in df.columns:
        return beneficio_realizado, fechas_curva, beneficios_curva

    df_sim = df.dropna(subset=["Fecha"]).sort_values("Fecha").copy()
    if df_sim.empty:
        return beneficio_realizado, fechas_curva, beneficios_curva

    df_sim["Fecha_Dia"] = df_sim["Fecha"].dt.strftime("%Y-%m-%d")
    for fecha, grupo in df_sim.groupby("Fecha_Dia"):
        beneficio_dia = 0.0
        for _, row in grupo.iterrows():
            estado = str(row.get("Estado", ""))
            precio_entrada = safe_float(row.get("Precio_Alerta"), 100.0)
            stop_loss = safe_float(row.get("Stop_Loss"), precio_entrada * 0.96 if precio_entrada else None)
            take_profit = safe_float(row.get("Take_Profit"), precio_entrada * 1.10 if precio_entrada else None)
            
            if precio_entrada is None or precio_entrada <= 0:
                continue
            pct_ganancia = (take_profit - precio_entrada) / precio_entrada
            pct_perdida = (precio_entrada - stop_loss) / precio_entrada

            if "OBJETIVO_CUMPLIDO" in estado:
                beneficio_dia += (CAPITAL_POR_ALERTA * pct_ganancia)
            elif "STOP_SALTADO" in estado:
                beneficio_dia -= (CAPITAL_POR_ALERTA * pct_perdida)

        beneficio_realizado += beneficio_dia
        fechas_curva.append(fecha)
        beneficios_curva.append(beneficio_realizado)

    beneficio_total_actual = beneficio_realizado + beneficio_no_realizado
    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    
    if fechas_curva and fechas_curva[-1] == fecha_actual:
        beneficios_curva[-1] = beneficio_total_actual
    else:
        fechas_curva.append(fecha_actual)
        beneficios_curva.append(beneficio_total_actual)

    return beneficio_realizado, fechas_curva, beneficios_curva


def calcular_position_percentages(stop_loss, entrada, actual, take_profit):
    values = [v for v in [stop_loss, entrada, actual, take_profit] if v is not None]
    if len(values) < 2:
        return None
    minimum, maximum = min(values), max(values)
    rango = maximum - minimum
    if rango <= 0:
        return None
    margen = rango * 0.08
    minimum -= margen
    maximum += margen
    rango = maximum - minimum

    def position(value):
        if value is None:
            return None
        pct = ((value - minimum) / rango) * 100
        return max(3, min(97, pct))

    return {
        "sl": position(stop_loss),
        "entry": position(entrada),
        "current": position(actual),
        "tp": position(take_profit),
    }

# ============================================================
# ESTilos CSS (Omitido por brevedad, usa el mismo de tu bloque)
# ============================================================

df_hist = preparar_fecha(cargar_datos())
metricas = calcular_metricas(df_hist)
activas = metricas["activas"]
exitos = metricas["exitos"]
fallos = metricas["fallos"]
win_rate = metricas["win_rate"]

df_activas_global = df_hist[df_hist["Estado"].astype(str).str.contains("ACTIVA", na=False, regex=False)].copy() if not df_hist.empty and "Estado" in df_hist.columns else pd.DataFrame()
precios_actuales = obtener_precios_activos(df_activas_global)

beneficio_realizado = calcular_beneficio_realizado(df_hist)
beneficio_no_realizado, posiciones_con_beneficio, posiciones_con_perdida = calcular_beneficio_no_realizado(df_activas_global, precios_actuales)
beneficio_acumulado = beneficio_realizado + beneficio_no_realizado

# MEJORA: Capital inicial dinámico basado en las posiciones totales operadas o activas para evitar distorsiones de porcentaje
total_operaciones_historicas = max(1, len(df_hist))
CAPITAL_INICIAL = max(3600.0, total_operaciones_historicas * CAPITAL_POR_ALERTA)

rentabilidad_pct = (beneficio_acumulado / CAPITAL_INICIAL * 100) if CAPITAL_INICIAL else 0
color_resultado = "#16a34a" if beneficio_acumulado >= 0 else "#dc2626"

beneficio_realizado_curva, fechas_curva, beneficios_curva = calcular_resultados(df_hist, beneficio_no_realizado)