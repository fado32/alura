import csv
import os
import random
import subprocess
from datetime import datetime, timedelta

from openai import OpenAI
import pandas as pd
import yfinance as yf


# ============================================================
# BOT 3.0 — MOTOR CUANTITATIVO + RISK ENGINE + AUDITORÍA
# ============================================================
#
# Objetivo:
#   - Detectar oportunidades de momentum con varias señales.
#   - Adaptar el stop a la volatilidad mediante ATR.
#   - Puntuar oportunidades en lugar de usar solo filtros binarios.
#   - Controlar riesgo por operación y exposición sectorial.
#   - Filtrar por régimen del mercado.
#   - Mantener la IA como capa EXPLICATIVA, no como decisor.
#
# IMPORTANTE:
# Este script es un motor de señales, no una garantía de rentabilidad.
# Antes de operar con dinero real debe validarse con backtest,
# walk-forward, costes, slippage y paper trading.
# ============================================================


# ============================================================
# CONFIGURACIÓN
# ============================================================

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

MODELO_LOCAL = "llama3.2"
ARCHIVO_HISTORIAL = "historial_alertas.csv"

# Mercado de referencia para el régimen y Relative Strength.
BENCHMARK = "^IBEX"

# ---- Universo / liquidez ----
PRECIO_MINIMO = 2.0
VOLUMEN_EUR_MEDIO_MIN = 1_000_000

# ---- Factores ----
PER_MAX = 100.0
RSI_MIN = 45.0
RSI_MAX = 82.0

# Los valores se usan como señales de puntuación, no todos como
# filtros absolutos.
VOLUME_RATIO_MIN = 1.20
BREAKOUT_LOOKBACK = 50

# ---- Scoring ----
SCORE_MINIMO = 72
MAX_CANDIDATOS = 5
# BOT 3.1 - diagnóstico completo
MODO_DIAGNOSTICO = True
MOSTRAR_TOP_DESCARTADOS = 15
GUARDAR_DIAGNOSTICO_CSV = True
DIAGNOSTICO_CSV = "diagnostico_bot.csv"


# Pesos del score.
PESO_MOMENTUM = 25
PESO_TENDENCIA = 20
PESO_RELATIVE_STRENGTH = 15
PESO_VOLUMEN = 15
PESO_BREAKOUT = 10
PESO_VOLATILIDAD = 10
PESO_FUNDAMENTAL = 5

# ---- Gestión del riesgo ----
CAPITAL_REFERENCIA = 100_000.0
RIESGO_POR_OPERACION = 0.005       # 0,50% del capital
ATR_MULTIPLICADOR_SL = 1.5
RR_MINIMO = 2.0
RIESGO_MAXIMO_TOTAL = 0.03         # 3% de riesgo teórico abierto
MAX_POSICIONES = 6
MAX_POSICIONES_SECTOR = 2

# ---- Gestión de salidas ----
TRAILING_ACTIVACION_R = 1.5
TRAILING_ATR_MULTIPLIER = 2.0

# ---- Cuarentena ----
DIAS_CUARENTENA_STOP = 15


# ============================================================
# MAESTRO DE ACTIVOS
# ============================================================

MAESTRO_ACTIVOS = {
    "TLGO.MC": ("Talgo", "Industrial", "🚆"),
    "TUB.MC": ("Tubacex", "Industrial", "⚙️"),
    "DOM.MC": ("Global Dominion", "Servicios / Tecnología", "🔌"),
    "EDR.MC": ("eDreams ODIGEO", "Consumo / Turismo", "✈️"),
    "VOC.MC": ("Vocento", "Medios de Comunicación", "📰"),
    "PVA.MC": ("Pescanova", "Alimentación", "🐟"),
    "PRS.MC": ("Prisa", "Medios de Comunicación", "🎙️"),
    "SLR.MC": ("Solaria", "Energías Renovables", "☀️"),
    "CIE.MC": ("CIE Automotive", "Automoción", "🚗"),
    "GRE.MC": ("Grenergy Renovables", "Energías Renovables", "🌱"),
    "MTS.MC": ("ArcelorMittal", "Materiales Básico / Acero", "🏭"),
    "CAF.MC": ("Construcciones y Aux. de Ferrocarriles", "Industrial", "🚆"),
    "ALM.MC": ("Almirall", "Salud / Farmacéutica", "💊"),
    "PHM.MC": ("PharmaMar", "Salud / Biotecnología", "🔬"),
    "ANA.MC": ("Acciona", "Infraestructuras", "🏗️"),
    "ANE.MC": ("Acciona Energía", "Energías Renovables", "⚡"),
    "A3M.MC": ("Atresmedia", "Medios de Comunicación", "📺"),
    "CASH.MC": ("Prosegur Cash", "Servicios Financieros", "💵"),
    "CLR.MC": ("Celeo Redes", "Energía", "🔌"),
    "EBRO.MC": ("Ebro Foods", "Alimentación", "🌾"),
    "ENG.MC": ("Enagás", "Utilities / Gas", "🔥"),
    "FDR.MC": ("Fluidra", "Bienes de Consumo", "🏊"),
    "GEST.MC": ("Gestamp", "Automoción", "🚘"),
    "IDR.MC": ("Indra Sistemas", "Tecnología / Defensa", "💻"),
    "MAP.MC": ("Mapfre", "Aseguradora", "🛡️"),
    "MEL.MC": ("Meliá Hotels", "Consumo / Turismo", "🏨"),
    "MRL.MC": ("Merlin Properties", "Inmobiliario / SOCIMI", "🏢"),
    "NTGY.MC": ("Naturgy", "Utilities / Gas y Elec.", "💡"),
    "RED.MC": ("Redeia", "Utilities / Red Eléctrica", "⚡"),
    "REN.MC": ("Renta 4 Banco", "Banca / Servicios Fin.", "🏦"),
    "SAB.MC": ("Banco Sabadell", "Banca", "🏦"),
    "SAN.MC": ("Banco Santander", "Banca", "🏦"),
    "SCYR.MC": ("Sacyr", "Infraestructuras", "🏗️"),
    "TRE.MC": ("Técnicas Reunidas", "Ingeniería / Energía", "🛠️"),
    "UNI.MC": ("Unicaja Banco", "Banca", "🏦"),
    "VID.MC": ("Vidrala", "Industrial / Envases", "🍾"),
    "MCG.L": ("Grupo San José", "Construcción", "🏗️"),
}

activos = list(MAESTRO_ACTIVOS.keys())


# ============================================================
# UTILIDADES
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default

        # Si por alguna razón llega una Series/array, no es un escalar válido.
        if isinstance(value, (pd.Series, pd.DataFrame)):
            return default

        missing = pd.isna(value)
        if isinstance(missing, (bool,)):
            if missing:
                return default

        return float(value)
    except (TypeError, ValueError):
        return default


def normalizar_columnas(data):
    """
    Normaliza columnas de yfinance tanto si vienen como columnas simples
    como si vienen en MultiIndex. Evita que data["Close"] devuelva una
    Series en vez de un escalar al analizar la última fila.
    """
    data = data.copy()

    if isinstance(data.columns, pd.MultiIndex):
        # Buscar el nivel que contiene OHLCV.
        niveles_validos = {"Open", "High", "Low", "Close", "Volume"}
        elegido = None

        for nivel in range(data.columns.nlevels):
            valores = set(str(x) for x in data.columns.get_level_values(nivel))
            if niveles_validos.intersection(valores):
                elegido = nivel
                break

        if elegido is not None:
            data.columns = data.columns.get_level_values(elegido)
        else:
            data.columns = [
                "_".join(str(x) for x in col if str(x) != "None")
                for col in data.columns
            ]

    # Si por cualquier motivo hay columnas duplicadas, conservar la primera.
    data = data.loc[:, ~data.columns.duplicated(keep="first")]

    return data


def calcular_rsi(close, periodo=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()
    avg_loss = loss.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calcular_atr(data, periodo=14):
    high = data["High"]
    low = data["Low"]
    close = data["Close"]

    prev_close = close.shift(1)

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    return tr.ewm(alpha=1 / periodo, adjust=False, min_periods=periodo).mean()


def calcular_indicadores(data):
    data = data.copy()

    data["EMA_20"] = data["Close"].ewm(span=20, adjust=False).mean()
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()
    data["EMA_200"] = data["Close"].ewm(span=200, adjust=False).mean()

    data["RSI"] = calcular_rsi(data["Close"], 14)
    data["ATR_14"] = calcular_atr(data, 14)

    data["Vol_Mean_20"] = data["Volume"].rolling(20).mean()
    data["Avg_EUR_Vol_20"] = (
        data["Close"] * data["Volume"]
    ).rolling(20).mean()

    # Máximo de las sesiones anteriores, excluyendo el día actual.
    data["Prev_High_50"] = (
        data["High"].rolling(BREAKOUT_LOOKBACK).max().shift(1)
    )

    # Momentum de varias ventanas.
    data["Mom_20"] = data["Close"].pct_change(20) * 100
    data["Mom_60"] = data["Close"].pct_change(60) * 100
    data["Mom_120"] = data["Close"].pct_change(120) * 100

    return data


def calcular_soportes_resistencias(data):
    ultimos_60 = data.tail(60)
    ultimos_15 = data.tail(15)

    soporte_60 = safe_float(ultimos_60["Low"].min(), 0)
    resistencia_60 = safe_float(ultimos_60["High"].max(), 0)
    soporte_15 = safe_float(ultimos_15["Low"].min(), 0)

    return (
        round(soporte_60, 2),
        round(resistencia_60, 2),
        round(soporte_15, 2),
    )


def obtener_rango_score(valor, tramos):
    """
    Devuelve un score entre 0 y 100.
    tramos = [(umbral, score), ...] ordenados de menor a mayor.
    """
    if valor is None:
        return 0

    score = 0
    for umbral, valor_score in tramos:
        if valor >= umbral:
            score = valor_score
    return min(100, max(0, score))


# ============================================================
# RÉGIMEN DE MERCADO
# ============================================================

def obtener_regimen_mercado():
    try:
        bench = yf.download(
            BENCHMARK,
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )

        if bench.empty:
            return {
                "regimen": "NEUTRAL",
                "precio": None,
                "ema50": None,
                "ema200": None,
                "mom60": None,
            }

        bench = normalizar_columnas(bench)

        if "Close" not in bench.columns:
            return {
                "regimen": "NEUTRAL",
                "precio": None,
                "ema50": None,
                "ema200": None,
                "mom60": None,
            }

        close = bench["Close"].dropna()

        if len(close) < 220:
            return {
                "regimen": "NEUTRAL",
                "precio": float(close.iloc[-1]),
                "ema50": None,
                "ema200": None,
                "mom60": None,
            }

        ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
        ema200 = close.ewm(span=200, adjust=False).mean().iloc[-1]
        mom60 = close.pct_change(60).iloc[-1] * 100

        precio = float(close.iloc[-1])

        if precio > ema200 and ema50 > ema200 and mom60 > 0:
            regimen = "RISK_ON"
        elif precio < ema200 and ema50 < ema200 and mom60 < 0:
            regimen = "RISK_OFF"
        else:
            regimen = "NEUTRAL"

        return {
            "regimen": regimen,
            "precio": round(precio, 2),
            "ema50": round(float(ema50), 2),
            "ema200": round(float(ema200), 2),
            "mom60": round(float(mom60), 2),
        }

    except Exception as e:
        print(f"⚠️ No se pudo calcular el régimen de mercado: {e}")
        return {
            "regimen": "NEUTRAL",
            "precio": None,
            "ema50": None,
            "ema200": None,
            "mom60": None,
        }


# ============================================================
# HISTORIAL / BLOQUEOS
# ============================================================

def leer_historial():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return []

    try:
        with open(ARCHIVO_HISTORIAL, mode="r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        print(f"⚠️ Error leyendo historial: {e}")
        return []


def obtener_tickers_bloqueados():
    """
    Bloquea:
      - operaciones activas
      - tickers que hayan sufrido STOP en los últimos N días
    """
    filas = leer_historial()

    bloqueados = set()
    hoy = datetime.now()

    for fila in filas:
        ticker = fila.get("Ticker", "")
        estado = fila.get("Estado", "")

        if not ticker:
            continue

        if "ACTIVA" in estado:
            bloqueados.add(ticker)
            continue

        if "STOP_SALTADO" in estado:
            fecha = fila.get("Fecha", "")
            try:
                fecha_alerta = datetime.strptime(
                    fecha.split()[0], "%Y-%m-%d"
                )
                if (hoy - fecha_alerta).days < DIAS_CUARENTENA_STOP:
                    bloqueados.add(ticker)
            except ValueError:
                continue

    return bloqueados


def obtener_exposicion_historial():
    """
    Estima riesgo teórico abierto a partir del historial.
    Se utiliza como protección adicional para no generar demasiadas señales.
    """
    filas = leer_historial()

    activas = []
    riesgo_total = 0.0
    sectores = {}

    for fila in filas:
        estado = fila.get("Estado", "")
        if "ACTIVA" not in estado:
            continue

        ticker = fila.get("Ticker", "")
        sector = fila.get("Sector", "General")

        precio = safe_float(fila.get("Precio_Alerta"))
        stop = safe_float(fila.get("Stop_Loss"))

        if precio and stop and precio > 0:
            riesgo_pct = max(0, (precio - stop) / precio)
        else:
            riesgo_pct = RIESGO_POR_OPERACION

        riesgo_total += min(riesgo_pct, 1.0)
        activas.append(ticker)
        sectores[sector] = sectores.get(sector, 0) + 1

    return {
        "activas": activas,
        "riesgo_total": riesgo_total,
        "sectores": sectores,
    }


# ============================================================
# SCORING
# ============================================================

def calcular_score(
    precio,
    ema20,
    ema50,
    ema200,
    rsi,
    ratio_volumen,
    mom20,
    mom60,
    mom120,
    relative_strength,
    atr_pct,
    breakout,
    per,
):
    # ---------------- Momentum ----------------
    momentum_raw = (
        0.20 * max(mom20, -20)
        + 0.40 * max(mom60, -50)
        + 0.40 * max(mom120, -80)
    )

    momentum_score = obtener_rango_score(
        momentum_raw,
        [
            (-10, 10),
            (0, 30),
            (5, 50),
            (10, 70),
            (20, 85),
            (30, 100),
        ],
    )

    # ---------------- Tendencia ----------------
    tendencia_score = 0
    if precio > ema50:
        tendencia_score += 45
    if ema20 > ema50:
        tendencia_score += 25
    if ema50 > ema200:
        tendencia_score += 30

    # ---------------- Relative Strength ----------------
    rs_score = obtener_rango_score(
        relative_strength,
        [
            (-10, 10),
            (0, 30),
            (3, 50),
            (7, 70),
            (12, 85),
            (20, 100),
        ],
    )

    # ---------------- Volumen ----------------
    volumen_score = obtener_rango_score(
        ratio_volumen,
        [
            (1.0, 15),
            (1.2, 40),
            (1.5, 70),
            (2.0, 90),
            (3.0, 100),
        ],
    )

    # ---------------- Breakout ----------------
    breakout_score = 90 if breakout else 30

    # ---------------- Volatilidad ----------------
    # Penaliza volatilidades extremas sin penalizar movimientos normales.
    if atr_pct is None:
        volatilidad_score = 40
    elif 1.0 <= atr_pct <= 3.5:
        volatilidad_score = 100
    elif 0.5 <= atr_pct < 1.0 or 3.5 < atr_pct <= 5.0:
        volatilidad_score = 70
    elif atr_pct <= 7:
        volatilidad_score = 40
    else:
        volatilidad_score = 10

    # ---------------- RSI ----------------
    if RSI_MIN <= rsi <= 70:
        rsi_score = 100
    elif 70 < rsi <= RSI_MAX:
        rsi_score = 75
    elif 40 <= rsi < RSI_MIN:
        rsi_score = 55
    else:
        rsi_score = 10

    tendencia_score = tendencia_score * 0.75 + rsi_score * 0.25

    # ---------------- Fundamental ----------------
    if per is None:
        fundamental_score = 50
    elif 0 < per <= 25:
        fundamental_score = 100
    elif 25 < per <= 50:
        fundamental_score = 75
    elif 50 < per <= PER_MAX:
        fundamental_score = 40
    else:
        fundamental_score = 0

    score = (
        momentum_score * PESO_MOMENTUM
        + tendencia_score * PESO_TENDENCIA
        + rs_score * PESO_RELATIVE_STRENGTH
        + volumen_score * PESO_VOLUMEN
        + breakout_score * PESO_BREAKOUT
        + volatilidad_score * PESO_VOLATILIDAD
        + fundamental_score * PESO_FUNDAMENTAL
    ) / 100

    return round(score, 2)


# ============================================================
# ANÁLISIS DE ACTIVO
# ============================================================


# ============================================================
# BOT 3.1 - DIAGNÓSTICO
# ============================================================

DIAGNOSTICO = []

def registrar_diagnostico(ticker, company="", stage="", reason="",
                          score=None, **metrics):
    """Registra por qué un activo continúa o queda descartado."""
    row = {
        "Ticker": ticker,
        "Company": company,
        "Stage": stage,
        "Reason": reason,
        "Score": safe_float(score),
    }
    row.update(metrics)
    DIAGNOSTICO.append(row)

def imprimir_diagnostico():
    if not DIAGNOSTICO:
        print("\n📊 DIAGNÓSTICO: no hubo registros.")
        return

    df = pd.DataFrame(DIAGNOSTICO)

    print("\n" + "=" * 78)
    print("📊 BOT 3.1 — DIAGNÓSTICO DEL ESCÁNER")
    print("=" * 78)

    if "Stage" in df.columns:
        print("\n🔎 ACTIVOS POR ETAPA:")
        print(df["Stage"].value_counts().to_string())

    if "Reason" in df.columns:
        print("\n🚫 PRINCIPALES MOTIVOS DE DESCARTE:")
        print(df["Reason"].fillna("SIN_MOTIVO").value_counts().head(25).to_string())

    # Último registro por ticker para enseñar el estado final.
    if "Ticker" in df.columns:
        ultimo = df.groupby("Ticker", as_index=False).tail(1).copy()
        cols = [c for c in [
            "Ticker", "Company", "Stage", "Reason", "Score",
            "RSI", "Volume_Ratio", "Momentum60", "RelativeStrength60",
            "ATR_pct", "Risk_pct", "RR"
        ] if c in ultimo.columns]
        if cols:
            ultimo = ultimo.sort_values(
                "Score", ascending=False, na_position="last"
            )
            print("\n📋 ESTADO FINAL POR TICKER:")
            print(ultimo[cols].head(MOSTRAR_TOP_DESCARTADOS).to_string(index=False))

    if GUARDAR_DIAGNOSTICO_CSV:
        try:
            df.to_csv(DIAGNOSTICO_CSV, index=False, encoding="utf-8-sig")
            print(f"\n💾 Diagnóstico guardado en: {DIAGNOSTICO_CSV}")
        except Exception as e:
            print(f"⚠️ No se pudo guardar {DIAGNOSTICO_CSV}: {e}")

def diagnostico_filtro(ticker, company, stage, condition, reason, **metrics):
    """Registra un filtro y devuelve la condición sin alterar la estrategia."""
    if condition:
        registrar_diagnostico(
            ticker, company, stage=stage, reason="PASA", **metrics
        )
        return True
    registrar_diagnostico(
        ticker, company, stage=stage, reason=reason, **metrics
    )
    return False

def analizar_activo(ticker_symbol, company, sector, benchmark_ret_60=0.0):
    """
    BOT 3.1:
    Igual que BOT 3.0 en criterios de trading, pero registra cada descarte
    para poder identificar el cuello de botella del sistema.
    """
    try:
        data = yf.download(
            ticker_symbol,
            period="2y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        data = normalizar_columnas(data)

        if data is None or data.empty:
            registrar_diagnostico(
                ticker_symbol, company, "DATA", "SIN_DATOS"
            )
            return None

        data = calcular_indicadores(data)

        if data.empty or len(data) < 200:
            registrar_diagnostico(
                ticker_symbol, company, "DATA",
                f"HISTORIAL_INSUFICIENTE:{len(data)}"
            )
            return None

        ultimo = data.iloc[-1]

        precio = safe_float(ultimo.get("Close"))
        ema20 = safe_float(ultimo.get("EMA_20"))
        ema50 = safe_float(ultimo.get("EMA_50"))
        ema200 = safe_float(ultimo.get("EMA_200"))
        rsi = safe_float(ultimo.get("RSI"))
        atr = safe_float(ultimo.get("ATR_14"))
        volumen = safe_float(ultimo.get("Volume"))
        volumen_medio = safe_float(ultimo.get("Vol_Mean_20"))
        eur_vol_medio = safe_float(ultimo.get("Avg_EUR_Vol_20"))
        mom20 = safe_float(ultimo.get("Mom_20"))
        mom60 = safe_float(ultimo.get("Mom_60"))
        mom120 = safe_float(ultimo.get("Mom_120"))

        if any(x is None for x in [
            precio, ema20, ema50, ema200, rsi, atr, volumen,
            volumen_medio, eur_vol_medio, mom20, mom60, mom120
        ]):
            registrar_diagnostico(
                ticker_symbol, company, "INDICADORES",
                "INDICADOR_NONE",
                RSI=rsi, Volume_Ratio=None, Momentum60=mom60
            )
            return None

        volume_ratio = volumen / volumen_medio if volumen_medio > 0 else None
        atr_pct = (atr / precio) * 100 if precio > 0 else None

        # PER: mantener la lógica del BOT 3.0.
        per = None
        try:
            info = yf.Ticker(ticker_symbol).info
            per = safe_float(info.get("trailingPE"))
        except Exception:
            pass

        # ------------------------------------------------------------
        # FILTROS BÁSICOS
        # ------------------------------------------------------------
        if precio < PRECIO_MINIMO:
            registrar_diagnostico(
                ticker_symbol, company, "PRECIO", "PRECIO_MINIMO",
                Price=precio
            )
            return None

        if eur_vol_medio < VOLUMEN_EUR_MEDIO_MIN:
            registrar_diagnostico(
                ticker_symbol, company, "LIQUIDEZ", "LIQUIDEZ_INSUFICIENTE",
                Avg_EUR_Vol=eur_vol_medio
            )
            return None

        if per is not None and (per <= 0 or per > PER_MAX):
            registrar_diagnostico(
                ticker_symbol, company, "FUNDAMENTAL",
                f"PER_FUERA_RANGO:{per:.2f}",
                PER=per
            )
            return None

        registrar_diagnostico(
            ticker_symbol, company, "BASICOS", "PASA",
            Price=precio, PER=per, Avg_EUR_Vol=eur_vol_medio
        )

        # ------------------------------------------------------------
        # INDICADORES / SCORE
        # ------------------------------------------------------------
        momentum_score = (
            max(0, min(100, 50 + mom20 * 100)) * 0.20 +
            max(0, min(100, 50 + mom60 * 100)) * 0.40 +
            max(0, min(100, 50 + mom120 * 100)) * 0.40
        )

        trend_base = (
            40 if precio > ema50 else 0
        ) + (
            30 if ema20 > ema50 else 0
        ) + (
            30 if ema50 > ema200 else 0
        )

        rsi_score = max(0, min(100, 100 - abs(rsi - 62) * 2.5))
        trend_score = trend_base * 0.75 + rsi_score * 0.25

        benchmark_ret_60 = safe_float(benchmark_ret_60, 0.0)
        relative_strength = mom60 - benchmark_ret_60

        relative_strength_score = max(
            0, min(100, 50 + relative_strength * 150)
        )

        if volume_ratio is None:
            volume_score = 0
        elif volume_ratio >= 2.0:
            volume_score = 100
        elif volume_ratio >= 1.5:
            volume_score = 90
        elif volume_ratio >= 1.2:
            volume_score = 75
        elif volume_ratio >= 1.0:
            volume_score = 55
        else:
            volume_score = 25

        previous_high = data["High"].shift(1).rolling(
            BREAKOUT_LOOKBACK
        ).max().iloc[-1]
        previous_high = safe_float(previous_high)

        if previous_high is not None and precio > previous_high:
            breakout_score = 90
        elif previous_high is not None and precio > previous_high * 0.97:
            breakout_score = 60
        else:
            breakout_score = 30

        if atr_pct is None:
            volatility_score = 0
        elif 1.5 <= atr_pct <= 5:
            volatility_score = 100
        elif 1.0 <= atr_pct < 1.5 or 5 < atr_pct <= 7:
            volatility_score = 75
        elif atr_pct < 1.0:
            volatility_score = 55
        else:
            volatility_score = 25

        if per is None:
            fundamental_score = 50
        elif per <= 20:
            fundamental_score = 100
        elif per <= 35:
            fundamental_score = 80
        elif per <= 60:
            fundamental_score = 60
        elif per <= PER_MAX:
            fundamental_score = 35
        else:
            fundamental_score = 0

        score = (
            momentum_score * 0.25 +
            trend_score * 0.20 +
            relative_strength_score * 0.15 +
            volume_score * 0.15 +
            breakout_score * 0.10 +
            volatility_score * 0.10 +
            fundamental_score * 0.05
        )

        # ------------------------------------------------------------
        # CONDICIONES DE ENTRADA
        # ------------------------------------------------------------
        metrics = dict(
            Price=precio,
            PER=per,
            RSI=rsi,
            Volume_Ratio=volume_ratio,
            Momentum20=mom20,
            Momentum60=mom60,
            Momentum120=mom120,
            RelativeStrength60=relative_strength,
            ATR_pct=atr_pct,
            Score=score,
        )

        if not (precio > ema50):
            registrar_diagnostico(
                ticker_symbol, company, "TENDENCIA",
                "PRECIO_NO_SUPERA_EMA50", **metrics
            )
            return None

        if not (ema50 > ema200):
            registrar_diagnostico(
                ticker_symbol, company, "TENDENCIA",
                "EMA50_NO_SUPERA_EMA200", **metrics
            )
            return None

        if not (RSI_MIN <= rsi <= RSI_MAX):
            registrar_diagnostico(
                ticker_symbol, company, "RSI",
                "RSI_FUERA_RANGO", **metrics
            )
            return None

        if volume_ratio is None or volume_ratio < VOLUME_RATIO_MIN:
            registrar_diagnostico(
                ticker_symbol, company, "VOLUMEN",
                "VOLUMEN_INSUFICIENTE", **metrics
            )
            return None

        # Stop estructural + ATR: conservar el criterio del BOT 3.0.
        soporte_15 = safe_float(data["Low"].rolling(15).min().iloc[-1])

        stop_atr = precio - ATR_MULTIPLICADOR_SL * atr
        stop_estructural = (
            soporte_15 * 0.995
            if soporte_15 is not None
            else stop_atr
        )

        stop_loss = max(stop_atr, stop_estructural)

        riesgo_unitario = precio - stop_loss
        risk_pct = (
            riesgo_unitario / precio
            if precio > 0 and riesgo_unitario > 0
            else None
        )

        if risk_pct is None or risk_pct <= 0:
            registrar_diagnostico(
                ticker_symbol, company, "RIESGO",
                "STOP_INVALIDO", **metrics
            )
            return None

        if risk_pct > 0.10:
            registrar_diagnostico(
                ticker_symbol, company, "RIESGO",
                "RIESGO_POR_OPERACION_DEMASIADO_ALTO",
                Risk_pct=risk_pct,
                **{k: v for k, v in metrics.items() if k != "Risk_pct"}
            )
            return None

        tp = precio + riesgo_unitario * 3.0
        rr = (tp - precio) / riesgo_unitario

        if rr < RR_MINIMO:
            registrar_diagnostico(
                ticker_symbol, company, "RR",
                "RR_INSUFICIENTE", RR=rr, Risk_pct=risk_pct, **metrics
            )
            return None

        if score < SCORE_MINIMO:
            registrar_diagnostico(
                ticker_symbol, company, "SCORE",
                f"SCORE_INSUFICIENTE:{score:.2f}<{SCORE_MINIMO}",
                RR=rr, Risk_pct=risk_pct,
                **{k: v for k, v in metrics.items() if k != "Score"}
            )
            return None

        registrar_diagnostico(
            ticker_symbol, company, "CANDIDATO",
            "PASA_TODOS_LOS_FILTROS",
            RR=rr, Risk_pct=risk_pct,
            **{k: v for k, v in metrics.items() if k != "Score"}
        )

        # Tamaño de posición por riesgo fijo.
        capital_riesgo = CAPITAL_REFERENCIA * RIESGO_POR_OPERACION
        cantidad = capital_riesgo / riesgo_unitario
        posicion_eur = cantidad * precio

        return {
            "ticker": ticker_symbol,
            "empresa": company,
            "sector": sector,
            "icono": "📈",
            "precio": round(precio, 4),
            "stop_loss": round(stop_loss, 4),
            "take_profit": round(tp, 4),
            "ratio_rr": round(rr, 2),
            "riesgo_pct": round(risk_pct * 100, 2),
            "posicion_eur_referencia": round(posicion_eur, 2),
            "score": round(score, 2),
            "rsi": round(rsi, 2),
            "atr_pct": round(atr_pct, 2),
            "ratio_volumen": round(volume_ratio, 2),
            "mom20": round(mom20 * 100, 2),
            "mom60": round(mom60 * 100, 2),
            "mom120": round(mom120 * 100, 2),
            "relative_strength_60": round(relative_strength * 100, 2),
            "breakout_50": round(breakout_score, 2),
            "State": "ACTIVA",
        }

    except Exception as e:
        print(f"⚠️ Error analizando {ticker_symbol}: {type(e).__name__}: {e}")
        registrar_diagnostico(
            ticker_symbol, company, "ERROR", f"{type(e).__name__}: {e}"
        )
        return None


def filtrar_por_riesgo_y_correlacion(candidatos, estado_cartera):
    """
    Selecciona candidatos respetando:
      - máximo de posiciones
      - riesgo agregado
      - concentración sectorial

    No sustituye a un cálculo de correlación real de retornos,
    pero ya evita una parte importante de la concentración.
    """
    activos_actuales = estado_cartera["activas"]
    sectores = dict(estado_cartera["sectores"])
    riesgo_actual = estado_cartera["riesgo_total"]

    seleccionados = []

    if len(activos_actuales) >= MAX_POSICIONES:
        return []

    for candidato in candidatos:
        if len(activos_actuales) + len(seleccionados) >= MAX_POSICIONES:
            break

        sector = candidato["sector"]

        if sectores.get(sector, 0) + 1 > MAX_POSICIONES_SECTOR:
            continue

        riesgo_nuevo = candidato["riesgo_pct"] / 100

        if riesgo_actual + sum(
            x["riesgo_pct"] / 100 for x in seleccionados
        ) + riesgo_nuevo > RIESGO_MAXIMO_TOTAL:
            continue

        seleccionados.append(candidato)
        sectores[sector] = sectores.get(sector, 0) + 1

    return seleccionados


# ============================================================
# IA EXPLICATIVA
# ============================================================

def generar_comentario_ia(candidato, regimen):
    enfoques = [
        (
            "Momentum y fuerza relativa",
            "Explica el momentum multitemporal y la fuerza relativa frente al índice.",
        ),
        (
            "Riesgo y estructura",
            "Explica ATR, distancia al stop, riesgo porcentual y estructura de soporte.",
        ),
        (
            "Volumen y ruptura",
            "Explica volumen relativo y si existe ruptura de máximos de 50 sesiones.",
        ),
        (
            "Tendencia y contexto",
            "Explica EMA20/50/200 y el régimen general del mercado.",
        ),
    ]

    enfoque_nombre, enfoque_instruccion = random.choice(enfoques)

    prompt_sistema = f"""
Eres un analista cuantitativo. Genera una explicación breve de una señal
calculada por reglas matemáticas. No inventes datos, no prometas beneficios
y no conviertas la explicación en una recomendación personalizada.

Enfoque actual: {enfoque_nombre}
Instrucción: {enfoque_instruccion}

Reglas:
- Máximo 4 frases.
- Utiliza números concretos.
- Indica también un riesgo o condición de invalidación.
- La señal la decide el motor cuantitativo; tú solo explicas los datos.
"""

    prompt_datos = f"""
Activo: {candidato['empresa']} ({candidato['ticker']})
Sector: {candidato['sector']}
Score cuantitativo: {candidato['score']}/100
Régimen mercado: {regimen}

Precio: {candidato['precio']} €
Stop: {candidato['stop_loss']} €
Take Profit inicial: {candidato['take_profit']} €
R/R teórico: 1:{candidato['ratio_rr']}
Riesgo hasta stop: {candidato['riesgo_pct']}%

EMA20: {candidato['ema20']}
EMA50: {candidato['ema50']}
EMA200: {candidato['ema200']}
RSI: {candidato['rsi']}
ATR: {candidato['atr']} ({candidato['atr_pct']}%)
Volumen relativo: {candidato['ratio_volumen']}x
Momentum 20d: {candidato['mom20']}%
Momentum 60d: {candidato['mom60']}%
Momentum 120d: {candidato['mom120']}%
Relative Strength 60d vs benchmark: {candidato['relative_strength_60']}%
Ruptura máximo 50d: {candidato['breakout_50']}
Soporte 15d: {candidato['soporte']} €
Resistencia 60d: {candidato['resistencia']} €
PER: {candidato['per']}
"""

    try:
        response = client.chat.completions.create(
            model=MODELO_LOCAL,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_datos},
            ],
            temperature=0.4,
        )

        return response.choices[0].message.content.strip()

    except Exception:
        return (
            f"Score {candidato['score']}/100 con momentum 60d "
            f"de {candidato['mom60']}%, volumen relativo "
            f"x{candidato['ratio_volumen']} y riesgo hasta stop "
            f"del {candidato['riesgo_pct']}%."
        )


# ============================================================
# CSV
# ============================================================

CABECERAS = [
    "Fecha",
    "Ticker",
    "Empresa",
    "Sector",
    "Icono",
    "Precio_Alerta",
    "Stop_Loss",
    "Take_Profit",
    "Ratio_RR",
    "Riesgo_Pct",
    "Position_EUR_Referencia",
    "Score",
    "RSI",
    "ATR_Pct",
    "Ratio_Volumen",
    "Momentum_60",
    "Relative_Strength_60",
    "Breakout_50",
    "Analisis_IA",
    "Estado",
]


def guardar_en_csv(candidato, comentario_ia):
    archivo_existe = os.path.exists(ARCHIVO_HISTORIAL)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    with open(
        ARCHIVO_HISTORIAL,
        mode="a",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        if not archivo_existe:
            writer.writerow(CABECERAS)

        writer.writerow(
            [
                fecha_hoy,
                candidato["ticker"],
                candidato["empresa"],
                candidato["sector"],
                candidato["icono"],
                candidato["precio"],
                candidato["stop_loss"],
                candidato["take_profit"],
                candidato["ratio_rr"],
                candidato["riesgo_pct"],
                candidato["posicion_eur_referencia"],
                candidato["score"],
                candidato["rsi"],
                candidato["atr_pct"],
                candidato["ratio_volumen"],
                candidato["mom60"],
                candidato["relative_strength_60"],
                candidato["breakout_50"],
                comentario_ia.replace("\n", " "),
                "ACTIVA",
            ]
        )


# ============================================================
# AUDITORÍA DE POSICIONES
# ============================================================

def auditar_y_mostrar_estadisticas():
    filas = leer_historial()

    if not filas:
        print("ℹ️ No hay historial de alertas previo.\n")
        return

    filas_actualizadas = []
    cambios_realizados = False

    for fila in filas:
        estado = fila.get("Estado", "")

        if "ACTIVA" not in estado:
            filas_actualizadas.append(fila)
            continue

        ticker = fila.get("Ticker")
        fecha_alerta = fila.get("Fecha")

        precio_alerta = safe_float(fila.get("Precio_Alerta"))
        stop_val = safe_float(fila.get("Stop_Loss"))
        tp_val = safe_float(fila.get("Take_Profit"))

        if not ticker or not fecha_alerta or not precio_alerta:
            filas_actualizadas.append(fila)
            continue

        if stop_val is None:
            stop_val = precio_alerta * 0.96

        if tp_val is None:
            tp_val = precio_alerta * 1.10

        try:
            fecha = datetime.strptime(
                fecha_alerta.split()[0],
                "%Y-%m-%d",
            )

            # La señal se considera generada al cierre.
            # Por tanto, para evitar usar el máximo/mínimo del propio
            # día de señal, la auditoría empieza al día siguiente.
            inicio = (fecha + timedelta(days=1)).strftime("%Y-%m-%d")

            data = yf.download(
                ticker,
                start=inicio,
                progress=False,
                auto_adjust=True,
            )

            data = normalizar_columnas(data)

            if not data.empty:
                max_posterior = safe_float(data["High"].max(), 0)
                min_posterior = safe_float(data["Low"].min(), 0)

                tp_tocado = max_posterior >= tp_val
                sl_tocado = min_posterior <= stop_val

                if tp_tocado and sl_tocado:
                    # Si ambos niveles se tocan durante el período,
                    # con OHLC diario no sabemos cuál ocurrió primero.
                    # No fingimos precisión: lo marcamos como ambiguo.
                    fila["Estado"] = "AMBIGUO_TP_SL"
                    cambios_realizados = True

                elif tp_tocado:
                    fila["Estado"] = "OBJETIVO_CUMPLIDO 🟢"
                    cambios_realizados = True

                elif sl_tocado:
                    fila["Estado"] = "STOP_SALTADO 🔴"
                    cambios_realizados = True

        except Exception as e:
            print(f"⚠️ Error auditando {ticker}: {e}")

        filas_actualizadas.append(fila)

    if cambios_realizados:
        # Conservamos las columnas originales cuando sea posible.
        campos = list(filas_actualizadas[0].keys())

        with open(
            ARCHIVO_HISTORIAL,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(filas_actualizadas)

    total = len(filas_actualizadas)
    exitos = sum(
        1
        for f in filas_actualizadas
        if "OBJETIVO_CUMPLIDO" in f.get("Estado", "")
    )
    fallos = sum(
        1
        for f in filas_actualizadas
        if "STOP_SALTADO" in f.get("Estado", "")
    )
    ambiguas = sum(
        1
        for f in filas_actualizadas
        if "AMBIGUO_TP_SL" in f.get("Estado", "")
    )
    activas = sum(
        1
        for f in filas_actualizadas
        if "ACTIVA" in f.get("Estado", "")
    )

    cerradas = exitos + fallos

    tasa_acierto = (
        exitos / cerradas * 100
        if cerradas > 0
        else 0
    )

    print("=" * 60)
    print("📊 ESTADÍSTICAS DEL HISTORIAL")
    print("=" * 60)
    print(f"• Alertas registradas: {total}")
    print(f"• Objetivos cumplidos: {exitos}")
    print(f"• Stops: {fallos}")
    print(f"• Casos ambiguos TP/SL: {ambiguas}")
    print(f"• Activas: {activas}")

    if cerradas > 0:
        print(f"• Tasa de acierto cerrada: {tasa_acierto:.1f}%")

    print("=" * 60 + "\n")


# ============================================================
# GITHUB
# ============================================================

def subir_a_github():
    try:
        subprocess.run(
            ["git", "add", "."],
            check=True,
        )

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
        )

        if status.stdout.strip():
            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    "Auto-update señales cuantitativas",
                ],
                check=True,
            )

            subprocess.run(
                ["git", "push", "origin", "main"],
                check=True,
            )

            print("🚀 Cambios subidos a GitHub.")

        else:
            print("💤 Sin cambios nuevos.")

    except Exception as e:
        print(f"ℹ️ Nota de Git: {e}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(
        f"🤖 BOT 3.0 — ESCÁNER CUANTITATIVO "
        f"({len(activos)} activos)"
    )
    print("=" * 60 + "\n")

    # 1. Auditar operaciones existentes.
    auditar_y_mostrar_estadisticas()

    # 2. Régimen de mercado.
    regimen_data = obtener_regimen_mercado()

    print(
        f"🌐 Régimen {BENCHMARK}: "
        f"{regimen_data['regimen']}"
    )

    if regimen_data["precio"] is not None:
        print(
            f"   Precio: {regimen_data['precio']} | "
            f"EMA50: {regimen_data['ema50']} | "
            f"EMA200: {regimen_data['ema200']} | "
            f"Momentum 60d: {regimen_data['mom60']}%"
        )

    print()

    # Si el mercado está claramente en risk-off, no se generan nuevas
    # operaciones. La decisión de "no operar" forma parte del sistema.
    if regimen_data["regimen"] == "RISK_OFF":
        print(
            "🔴 RISK_OFF: no se abrirán nuevas señales. "
            "Se mantiene la auditoría de posiciones existentes."
        )
        subir_a_github()
        raise SystemExit(0)

    # 3. Bloqueos.
    tickers_bloqueados = obtener_tickers_bloqueados()

    if tickers_bloqueados:
        print(
            "🔒 Bloqueados:",
            ", ".join(sorted(tickers_bloqueados)),
        )

    # 4. Estado de cartera.
    estado_cartera = obtener_exposicion_historial()

    print(
        f"📦 Posiciones activas: "
        f"{len(estado_cartera['activas'])}/{MAX_POSICIONES}"
    )
    print(
        f"⚠️ Riesgo teórico abierto: "
        f"{estado_cartera['riesgo_total'] * 100:.2f}% "
        f"/ {RIESGO_MAXIMO_TOTAL * 100:.2f}%"
    )

    if len(estado_cartera["activas"]) >= MAX_POSICIONES:
        print("⛔ Máximo de posiciones alcanzado.")
        subir_a_github()
        raise SystemExit(0)

    # 5. Benchmark para Relative Strength.
    try:
        benchmark = yf.download(
            BENCHMARK,
            period="1y",
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
        benchmark = normalizar_columnas(benchmark)

        if not benchmark.empty and "Close" in benchmark.columns:
            bench_close = benchmark["Close"].dropna()
            bench_ret60 = (
                bench_close.pct_change(60).iloc[-1] * 100
                if len(bench_close) > 60
                else 0
            )
        else:
            bench_ret60 = 0

    except Exception:
        bench_ret60 = 0

    benchmark_data = {
        "ret60": float(bench_ret60)
        if bench_ret60 is not None
        else 0
    }

    # 6. Escaneo.
    candidatos_detectados = []

    

    for idx, ticker in enumerate(activos, 1):
        if ticker in tickers_bloqueados:
            continue

        # Extraemos el nombre y sector correspondientes al ticker desde el maestro
        empresa, sector, _ = MAESTRO_ACTIVOS.get(
            ticker, (ticker, "General", "📈")
        )

        print(
            f"[{idx}/{len(activos)}] Analizando {ticker}...",
            end="\r",
        )

        resultado = analizar_activo(
            ticker,
            empresa,
            sector,
            benchmark_data,
        )

        if resultado and resultado["score"] >= SCORE_MINIMO:
            candidatos_detectados.append(resultado)

    print("\n" + "=" * 60)
    print(
        f"🔎 Candidatos con score >= {SCORE_MINIMO}: "
        f"{len(candidatos_detectados)}"
    )

    # 7. Ranking por score.
    candidatos_detectados.sort(
        key=lambda x: (
            x["score"],
            x["relative_strength_60"],
            x["ratio_volumen"],
        ),
        reverse=True,
    )

    # 8. Control de riesgo / sectores.
    candidatos_seleccionados = filtrar_por_riesgo_y_correlacion(
        candidatos_detectados,
        estado_cartera,
    )

    candidatos_seleccionados = candidatos_seleccionados[:MAX_CANDIDATOS]

    print(
        f"🎯 Seleccionados después de risk engine: "
        f"{len(candidatos_seleccionados)}"
    )
    print("=" * 60)

    # 9. Generación y persistencia.
    for candidato in candidatos_seleccionados:
        comentario = generar_comentario_ia(
            candidato,
            regimen_data["regimen"],
        )

        guardar_en_csv(
            candidato,
            comentario,
        )

        print(
            f"\n{candidato['icono']} "
            f"{candidato['empresa']} ({candidato['ticker']})"
        )
        print(
            f"   Score: {candidato['score']}/100 | "
            f"Entrada: {candidato['precio']} €"
        )
        print(
            f"   SL: {candidato['stop_loss']} € "
            f"(-{candidato['riesgo_pct']}%) | "
            f"TP inicial: {candidato['take_profit']} €"
        )
        print(
            f"   R/R: 1:{candidato['ratio_rr']} | "
            f"RSI: {candidato['rsi']} | "
            f"Vol: x{candidato['ratio_volumen']}"
        )
        print(
            f"   Mom60: {candidato['mom60']}% | "
            f"RS vs índice: {candidato['relative_strength_60']}%"
        )
        print(
            f"   Posición teórica para capital de "
            f"{CAPITAL_REFERENCIA:,.0f} €: "
            f"{candidato['posicion_eur_referencia']:,.0f} €"
        )
        print(f"   🤖 {comentario}")
        print("-" * 60)

    if not candidatos_seleccionados:
        print(
            "\n💤 Ninguna oportunidad superó simultáneamente "
            "el score y las restricciones de riesgo."
        )

    print("\n💾 Proceso terminado.")
    subir_a_github()
