import csv
import os
import subprocess
from datetime import datetime, timedelta

from openai import OpenAI
import pandas as pd
import yfinance as yf


# ============================================================
# BOT 4.0 — QUANT MOMENTUM + RANKING + RISK ENGINE
# ============================================================
#
# Arquitectura:
#
# DATA
#   ↓
# INDICADORES
#   ↓
# FILTROS DE LIQUIDEZ / TENDENCIA
#   ↓
# FACTORES
#   ↓
# RANKING CROSS-SECTIONAL
#   ↓
# REGIME FILTER
#   ↓
# POSITION SIZING
#   ↓
# SECTOR + CORRELATION RISK
#   ↓
# ALERTA
#   ↓
# AUDITORÍA / TRAILING
#
# La IA solo explica la señal.
# Nunca decide si comprar o vender.
#
# IMPORTANTE:
# Este bot NO garantiza rentabilidad.
# Antes de utilizar capital real:
#   1. Backtest
#   2. Walk-forward
#   3. Costes
#   4. Slippage
#   5. Paper trading
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
ARCHIVO_DIAGNOSTICO = "diagnostico_bot.csv"

BENCHMARK = "^IBEX"


# ============================================================
# UNIVERSO / LIQUIDEZ
# ============================================================

PRECIO_MINIMO = 2.0

VOLUMEN_EUR_MEDIO_MIN = 1_000_000

HISTORIAL_PERIOD = "2y"


# ============================================================
# INDICADORES
# ============================================================

RSI_MIN = 45.0
RSI_MAX = 82.0

BREAKOUT_LOOKBACK = 50

MOMENTUM_WINDOWS = [20, 60, 120, 252]


# ============================================================
# RANKING
# ============================================================

MAX_CANDIDATOS = 5

SCORE_MINIMO = 68.0

# Pesos del ranking final.
#
# Momentum y fuerza relativa tienen mayor importancia porque
# la estrategia es principalmente de momentum/swing.
#
# El PER tiene poco peso deliberadamente.
#
PESO_MOMENTUM = 30
PESO_RELATIVE_STRENGTH = 25
PESO_TENDENCIA = 20
PESO_BREAKOUT = 10
PESO_VOLUMEN = 7
PESO_VOLATILIDAD = 5
PESO_FUNDAMENTAL = 3


# ============================================================
# RIESGO
# ============================================================

CAPITAL_REFERENCIA = 100_000.0

# Riesgo base por operación.
RIESGO_POR_OPERACION = 0.005       # 0,50%

# Riesgo máximo agregado.
RIESGO_MAXIMO_TOTAL = 0.03         # 3%

MAX_POSICIONES = 6

MAX_POSICIONES_SECTOR = 2

# Ninguna posición puede superar este % del capital.
MAX_POSICION_NOMINAL = 0.20        # 20%

# Correlación máxima permitida.
CORRELACION_MAXIMA = 0.85

# Mínimo histórico para correlación.
CORRELACION_LOOKBACK = 90


# ============================================================
# STOP / TAKE PROFIT
# ============================================================

ATR_MULTIPLICADOR_SL = 1.5

TP_MULTIPLICADOR_R = 3.0

RR_MINIMO = 2.0

# Break-even.
BREAK_EVEN_ACTIVACION_R = 1.0

# Trailing.
TRAILING_ACTIVACION_R = 1.5

TRAILING_ATR_MULTIPLIER = 2.0


# ============================================================
# RÉGIMEN
# ============================================================

# Riesgo base modificado por régimen.

MULTIPLICADOR_RIESGO_RISK_ON = 1.00

MULTIPLICADOR_RIESGO_NEUTRAL = 0.50

MULTIPLICADOR_RIESGO_RISK_OFF = 0.00


# ============================================================
# CUARENTENA
# ============================================================

DIAS_CUARENTENA_STOP = 15


# ============================================================
# DIAGNÓSTICO
# ============================================================

MODO_DIAGNOSTICO = True

MOSTRAR_TOP_DESCARTADOS = 20

GUARDAR_DIAGNOSTICO_CSV = True

DIAGNOSTICO = []


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
    "MTS.MC": ("ArcelorMittal", "Materiales Básicos / Acero", "🏭"),
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

    # Revisar este ticker antes de utilizarlo:
    # ".L" corresponde al mercado de Londres.
    # Se mantiene fuera por seguridad.
    # "MCG.L": ("Grupo San José", "Construcción", "🏗️"),
}

activos = list(MAESTRO_ACTIVOS.keys())


# ============================================================
# UTILIDADES
# ============================================================

def safe_float(value, default=None):
    try:
        if value is None:
            return default

        if isinstance(value, (pd.Series, pd.DataFrame)):
            return default

        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def normalizar_columnas(data):
    """
    Normaliza columnas de yfinance.

    Compatible con DataFrames normales y MultiIndex.
    """

    if data is None:
        return pd.DataFrame()

    data = data.copy()

    if isinstance(data.columns, pd.MultiIndex):

        niveles_validos = {
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        }

        elegido = None

        for nivel in range(data.columns.nlevels):

            valores = set(
                str(x)
                for x in data.columns.get_level_values(nivel)
            )

            if niveles_validos.intersection(valores):

                elegido = nivel
                break

        if elegido is not None:

            data.columns = data.columns.get_level_values(
                elegido
            )

        else:

            data.columns = [
                "_".join(
                    str(x)
                    for x in col
                    if str(x) != "None"
                )
                for col in data.columns
            ]

    data = data.loc[
        :,
        ~data.columns.duplicated(keep="first")
    ]

    return data


# ============================================================
# INDICADORES
# ============================================================

def calcular_rsi(close, periodo=14):

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / periodo,
        adjust=False,
        min_periods=periodo,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / periodo,
        adjust=False,
        min_periods=periodo,
    ).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)

    rsi = 100 - (
        100 / (1 + rs)
    )

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

    return tr.ewm(
        alpha=1 / periodo,
        adjust=False,
        min_periods=periodo,
    ).mean()


def calcular_indicadores(data):

    data = data.copy()

    close = data["Close"]

    data["EMA_20"] = close.ewm(
        span=20,
        adjust=False,
    ).mean()

    data["EMA_50"] = close.ewm(
        span=50,
        adjust=False,
    ).mean()

    data["EMA_200"] = close.ewm(
        span=200,
        adjust=False,
    ).mean()

    data["RSI"] = calcular_rsi(
        close,
        14,
    )

    data["ATR_14"] = calcular_atr(
        data,
        14,
    )

    data["Vol_Mean_20"] = (
        data["Volume"]
        .rolling(20)
        .mean()
    )

    data["Avg_EUR_Vol_20"] = (
        data["Close"] * data["Volume"]
    ).rolling(20).mean()

    # Máximo previo.
    data["Prev_High_50"] = (
        data["High"]
        .rolling(BREAKOUT_LOOKBACK)
        .max()
        .shift(1)
    )

    # Máximo de 52 semanas.
    data["High_252"] = (
        data["High"]
        .rolling(252)
        .max()
        .shift(1)
    )

    # Momentum.
    data["Mom_20"] = (
        close.pct_change(20) * 100
    )

    data["Mom_60"] = (
        close.pct_change(60) * 100
    )

    data["Mom_120"] = (
        close.pct_change(120) * 100
    )

    data["Mom_252"] = (
        close.pct_change(252) * 100
    )

    return data


# ============================================================
# SCORE FACTORIAL
# ============================================================

def clamp(value, minimum=0, maximum=100):

    return max(
        minimum,
        min(maximum, value),
    )


def score_momentum(
    mom20,
    mom60,
    mom120,
    mom252,
):

    valores = [
        (mom20, 0.15),
        (mom60, 0.30),
        (mom120, 0.30),
        (mom252, 0.25),
    ]

    total = 0
    peso_total = 0

    for valor, peso in valores:

        if valor is None:
            continue

        # Conversión suave.
        #
        # 0% => 50
        # +10% => 65
        # +30% => 95
        # -20% => 20
        #
        factor = clamp(
            50 + valor * 1.5
        )

        total += factor * peso

        peso_total += peso

    if peso_total == 0:
        return 0

    return total / peso_total


def score_tendencia(
    precio,
    ema20,
    ema50,
    ema200,
    rsi,
):

    score = 0

    if precio > ema50:
        score += 35

    if ema20 > ema50:
        score += 25

    if ema50 > ema200:
        score += 30

    # RSI ideal para momentum.
    if 55 <= rsi <= 70:
        score += 10

    elif 70 < rsi <= 78:
        score += 7

    elif 45 <= rsi < 55:
        score += 5

    return clamp(score)


def score_relative_strength(
    relative_strength
):

    if relative_strength is None:
        return 0

    return clamp(
        50 + relative_strength * 4
    )


def score_volumen(
    volume_ratio
):

    if volume_ratio is None:
        return 0

    if volume_ratio >= 3:
        return 100

    if volume_ratio >= 2:
        return 90

    if volume_ratio >= 1.5:
        return 80

    if volume_ratio >= 1.2:
        return 70

    if volume_ratio >= 1:
        return 55

    if volume_ratio >= 0.8:
        return 40

    return 20


def score_breakout(
    precio,
    previous_high,
):

    if previous_high is None:
        return 30

    distancia = (
        precio / previous_high - 1
    ) * 100

    if distancia >= 0:
        return 100

    if distancia >= -1:
        return 90

    if distancia >= -2:
        return 75

    if distancia >= -4:
        return 55

    if distancia >= -7:
        return 35

    return 15


def score_volatilidad(
    atr_pct
):

    if atr_pct is None:
        return 30

    # Para esta estrategia buscamos una volatilidad suficiente
    # para producir movimiento, pero evitamos extremos.
    if 1.5 <= atr_pct <= 4.5:
        return 100

    if 1.0 <= atr_pct < 1.5:
        return 80

    if 4.5 < atr_pct <= 6:
        return 80

    if 0.7 <= atr_pct < 1:
        return 55

    if 6 < atr_pct <= 8:
        return 50

    if atr_pct < 0.7:
        return 30

    return 15


def score_fundamental(per):

    if per is None:
        # No penalizamos excesivamente información ausente.
        return 50

    if per <= 0:
        return 20

    if per <= 15:
        return 100

    if per <= 20:
        return 90

    if per <= 30:
        return 75

    if per <= 45:
        return 60

    if per <= 70:
        return 40

    if per <= 100:
        return 25

    return 10


# ============================================================
# RÉGIMEN DE MERCADO
# ============================================================

def obtener_regimen_mercado():

    try:

        bench = yf.download(
            BENCHMARK,
            period="3y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        bench = normalizar_columnas(bench)

        if (
            bench.empty
            or "Close" not in bench.columns
        ):

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
                "precio": safe_float(
                    close.iloc[-1]
                ),
                "ema50": None,
                "ema200": None,
                "mom60": None,
            }

        ema50 = (
            close
            .ewm(
                span=50,
                adjust=False,
            )
            .mean()
            .iloc[-1]
        )

        ema200 = (
            close
            .ewm(
                span=200,
                adjust=False,
            )
            .mean()
            .iloc[-1]
        )

        mom60 = (
            close
            .pct_change(60)
            .iloc[-1]
            * 100
        )

        precio = float(
            close.iloc[-1]
        )

        if (
            precio > ema200
            and ema50 > ema200
            and mom60 > 0
        ):

            regimen = "RISK_ON"

        elif (
            precio < ema200
            and ema50 < ema200
            and mom60 < 0
        ):

            regimen = "RISK_OFF"

        else:

            regimen = "NEUTRAL"

        return {
            "regimen": regimen,
            "precio": round(precio, 2),
            "ema50": round(
                float(ema50),
                2,
            ),
            "ema200": round(
                float(ema200),
                2,
            ),
            "mom60": round(
                float(mom60),
                2,
            ),
        }

    except Exception as e:

        print(
            f"⚠️ Error calculando régimen: {e}"
        )

        return {
            "regimen": "NEUTRAL",
            "precio": None,
            "ema50": None,
            "ema200": None,
            "mom60": None,
        }


def multiplicador_riesgo_regimen(
    regimen
):

    if regimen == "RISK_ON":
        return MULTIPLICADOR_RIESGO_RISK_ON

    if regimen == "RISK_OFF":
        return MULTIPLICADOR_RIESGO_RISK_OFF

    return MULTIPLICADOR_RIESGO_NEUTRAL


# ============================================================
# HISTORIAL
# ============================================================

def leer_historial():

    if not os.path.exists(
        ARCHIVO_HISTORIAL
    ):
        return []

    try:

        with open(
            ARCHIVO_HISTORIAL,
            mode="r",
            encoding="utf-8",
        ) as f:

            return list(
                csv.DictReader(f)
            )

    except Exception as e:

        print(
            f"⚠️ Error leyendo historial: {e}"
        )

        return []


def obtener_tickers_bloqueados():

    filas = leer_historial()

    bloqueados = set()

    hoy = datetime.now()

    for fila in filas:

        ticker = fila.get(
            "Ticker",
            "",
        )

        estado = fila.get(
            "Estado",
            "",
        )

        if not ticker:
            continue

        # Operación activa.
        if estado == "ACTIVA":
            bloqueados.add(ticker)
            continue

        # Cuarentena tras stop.
        if estado.startswith(
            "STOP_SALTADO"
        ):

            fecha = fila.get(
                "Fecha",
                "",
            )

            try:

                fecha_alerta = datetime.strptime(
                    fecha.split()[0],
                    "%Y-%m-%d",
                )

                dias = (
                    hoy - fecha_alerta
                ).days

                if dias < DIAS_CUARENTENA_STOP:
                    bloqueados.add(ticker)

            except ValueError:
                continue

    return bloqueados


# ============================================================
# RIESGO HISTÓRICO
# ============================================================

def obtener_exposicion_historial():

    filas = leer_historial()

    activas = []

    riesgo_total = 0.0

    sectores = {}

    posiciones = {}

    for fila in filas:

        estado = fila.get(
            "Estado",
            "",
        )

        if estado != "ACTIVA":
            continue

        ticker = fila.get(
            "Ticker",
            "",
        )

        sector = fila.get(
            "Sector",
            "General",
        )

        precio = safe_float(
            fila.get("Precio_Alerta")
        )

        stop = safe_float(
            fila.get("Stop_Loss")
        )

        cantidad = safe_float(
            fila.get("Cantidad")
        )

        posicion_eur = safe_float(
            fila.get(
                "Position_EUR_Referencia"
            )
        )

        # Compatibilidad con historial antiguo.
        if (
            cantidad is None
            and precio
            and posicion_eur
        ):

            cantidad = (
                posicion_eur / precio
            )

        if (
            cantidad
            and precio
            and stop
        ):

            riesgo_eur = max(
                0,
                cantidad * (
                    precio - stop
                ),
            )

        else:

            # Fallback conservador para registros antiguos.
            riesgo_eur = (
                CAPITAL_REFERENCIA
                * RIESGO_POR_OPERACION
            )

        riesgo_pct = (
            riesgo_eur
            / CAPITAL_REFERENCIA
        )

        riesgo_total += riesgo_pct

        activas.append(ticker)

        sectores[sector] = (
            sectores.get(sector, 0)
            + 1
        )

        posiciones[ticker] = {
            "cantidad": cantidad,
            "precio": precio,
            "stop": stop,
            "riesgo_eur": riesgo_eur,
        }

    return {
        "activas": activas,
        "riesgo_total": riesgo_total,
        "sectores": sectores,
        "posiciones": posiciones,
    }


# ============================================================
# DIAGNÓSTICO
# ============================================================

def registrar_diagnostico(
    ticker,
    company="",
    stage="",
    reason="",
    score=None,
    **metrics
):

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
        return

    df = pd.DataFrame(
        DIAGNOSTICO
    )

    print("\n" + "=" * 78)
    print(
        "📊 BOT 4.0 — DIAGNÓSTICO"
    )
    print("=" * 78)

    if "Stage" in df.columns:

        print(
            "\n🔎 ACTIVOS POR ETAPA:"
        )

        print(
            df["Stage"]
            .value_counts()
            .to_string()
        )

    if "Reason" in df.columns:

        print(
            "\n🚫 PRINCIPALES MOTIVOS:"
        )

        print(
            df["Reason"]
            .fillna("SIN_MOTIVO")
            .value_counts()
            .head(25)
            .to_string()
        )

    if GUARDAR_DIAGNOSTICO_CSV:

        try:

            df.to_csv(
                ARCHIVO_DIAGNOSTICO,
                index=False,
                encoding="utf-8-sig",
            )

            print(
                f"\n💾 Diagnóstico: "
                f"{ARCHIVO_DIAGNOSTICO}"
            )

        except Exception as e:

            print(
                f"⚠️ Error guardando diagnóstico: {e}"
            )


# ============================================================
# INFORMACIÓN FUNDAMENTAL
# ============================================================

def obtener_per(ticker):

    try:

        info = yf.Ticker(
            ticker
        ).info

        per = safe_float(
            info.get(
                "trailingPE"
            )
        )

        if per is None:

            per = safe_float(
                info.get(
                    "forwardPE"
                )
            )

        return per

    except Exception:

        return None


# ============================================================
# ANÁLISIS INDIVIDUAL
# ============================================================

def analizar_activo(
    ticker_symbol,
    company,
    sector,
    benchmark_ret_60=0.0,
):

    try:

        data = yf.download(
            ticker_symbol,
            period=HISTORIAL_PERIOD,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        data = normalizar_columnas(
            data
        )

        if data.empty:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "DATA",
                "SIN_DATOS",
            )

            return None

        required = {
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        }

        if not required.issubset(
            set(data.columns)
        ):

            registrar_diagnostico(
                ticker_symbol,
                company,
                "DATA",
                "COLUMNAS_INCOMPLETAS",
            )

            return None

        data = calcular_indicadores(
            data
        )

        if len(data) < 260:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "DATA",
                f"HISTORIAL_INSUFICIENTE:{len(data)}",
            )

            return None

        ultimo = data.iloc[-1]

        precio = safe_float(
            ultimo.get("Close")
        )

        ema20 = safe_float(
            ultimo.get("EMA_20")
        )

        ema50 = safe_float(
            ultimo.get("EMA_50")
        )

        ema200 = safe_float(
            ultimo.get("EMA_200")
        )

        rsi = safe_float(
            ultimo.get("RSI")
        )

        atr = safe_float(
            ultimo.get("ATR_14")
        )

        volumen = safe_float(
            ultimo.get("Volume")
        )

        volumen_medio = safe_float(
            ultimo.get(
                "Vol_Mean_20"
            )
        )

        eur_vol_medio = safe_float(
            ultimo.get(
                "Avg_EUR_Vol_20"
            )
        )

        mom20 = safe_float(
            ultimo.get("Mom_20")
        )

        mom60 = safe_float(
            ultimo.get("Mom_60")
        )

        mom120 = safe_float(
            ultimo.get("Mom_120")
        )

        mom252 = safe_float(
            ultimo.get("Mom_252")
        )

        previous_high = safe_float(
            ultimo.get(
                "Prev_High_50"
            )
        )

        high_252 = safe_float(
            ultimo.get(
                "High_252"
            )
        )

        if any(
            x is None
            for x in [
                precio,
                ema20,
                ema50,
                ema200,
                rsi,
                atr,
                volumen,
                volumen_medio,
                eur_vol_medio,
                mom20,
                mom60,
                mom120,
                mom252,
            ]
        ):

            registrar_diagnostico(
                ticker_symbol,
                company,
                "INDICADORES",
                "INDICADOR_NONE",
            )

            return None

        volume_ratio = (
            volumen / volumen_medio
            if volumen_medio > 0
            else None
        )

        atr_pct = (
            atr / precio * 100
            if precio > 0
            else None
        )

        benchmark_ret_60 = safe_float(
            benchmark_ret_60,
            0.0,
        )

        # ====================================================
        # RELATIVE STRENGTH
        # ====================================================

        relative_strength = (
            mom60
            - benchmark_ret_60
        )

        # ====================================================
        # FILTROS BÁSICOS
        # ====================================================

        if precio < PRECIO_MINIMO:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "PRECIO",
                "PRECIO_MINIMO",
                Price=precio,
            )

            return None

        if (
            eur_vol_medio
            < VOLUMEN_EUR_MEDIO_MIN
        ):

            registrar_diagnostico(
                ticker_symbol,
                company,
                "LIQUIDEZ",
                "LIQUIDEZ_INSUFICIENTE",
                Avg_EUR_Vol=eur_vol_medio,
            )

            return None

        # ====================================================
        # TENDENCIA
        # ====================================================

        if precio <= ema50:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "TENDENCIA",
                "PRECIO_NO_SUPERA_EMA50",
                Price=precio,
                EMA50=ema50,
            )

            return None

        if ema50 <= ema200:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "TENDENCIA",
                "EMA50_NO_SUPERA_EMA200",
                EMA50=ema50,
                EMA200=ema200,
            )

            return None

        # ====================================================
        # RSI
        # ====================================================

        if not (
            RSI_MIN
            <= rsi
            <= RSI_MAX
        ):

            registrar_diagnostico(
                ticker_symbol,
                company,
                "RSI",
                "RSI_FUERA_RANGO",
                RSI=rsi,
            )

            return None

        # ====================================================
        # PER
        # ====================================================

        per = obtener_per(
            ticker_symbol
        )

        # NO bloqueamos por PER.
        #
        # Es únicamente un factor.
        #
        # Esto evita eliminar empresas de momentum
        # simplemente porque tienen un múltiplo alto.
        # ====================================================

        # ====================================================
        # FACTORES
        # ====================================================

        momentum_score = score_momentum(
            mom20,
            mom60,
            mom120,
            mom252,
        )

        trend_score = score_tendencia(
            precio,
            ema20,
            ema50,
            ema200,
            rsi,
        )

        rs_score = score_relative_strength(
            relative_strength
        )

        volume_score = score_volumen(
            volume_ratio
        )

        breakout_score = score_breakout(
            precio,
            previous_high,
        )

        volatility_score = score_volatilidad(
            atr_pct
        )

        fundamental_score = score_fundamental(
            per
        )

        # ====================================================
        # SCORE BRUTO
        # ====================================================

        score_bruto = (
            momentum_score
            * PESO_MOMENTUM
            + rs_score
            * PESO_RELATIVE_STRENGTH
            + trend_score
            * PESO_TENDENCIA
            + breakout_score
            * PESO_BREAKOUT
            + volume_score
            * PESO_VOLUMEN
            + volatility_score
            * PESO_VOLATILIDAD
            + fundamental_score
            * PESO_FUNDAMENTAL
        ) / 100

        # ====================================================
        # STOP
        # ====================================================

        soporte_15 = safe_float(
            data["Low"]
            .rolling(15)
            .min()
            .iloc[-1]
        )

        soporte_60 = safe_float(
            data["Low"]
            .rolling(60)
            .min()
            .iloc[-1]
        )

        resistencia_60 = safe_float(
            data["High"]
            .rolling(60)
            .max()
            .iloc[-1]
        )

        stop_atr = (
            precio
            - ATR_MULTIPLICADOR_SL
            * atr
        )

        if soporte_15 is not None:

            stop_estructural = (
                soporte_15 * 0.995
            )

        else:

            stop_estructural = stop_atr

        # Se utiliza el stop más alto de los dos:
        # el stop queda más ajustado, siempre por debajo
        # del precio.
        stop_loss = max(
            stop_atr,
            stop_estructural,
        )

        # Seguridad.
        if stop_loss >= precio:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "RIESGO",
                "STOP_ENCIMA_PRECIO",
                Score=score_bruto,
            )

            return None

        riesgo_unitario = (
            precio - stop_loss
        )

        risk_pct = (
            riesgo_unitario
            / precio
        )

        if risk_pct <= 0:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "RIESGO",
                "RIESGO_INVALIDO",
            )

            return None

        # Evitamos posiciones con stops absurdamente alejados.
        if risk_pct > 0.10:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "RIESGO",
                "STOP_DEMASIADO_ALEJADO",
                Risk_pct=risk_pct,
            )

            return None

        # ====================================================
        # TAKE PROFIT
        # ====================================================

        take_profit = (
            precio
            + riesgo_unitario
            * TP_MULTIPLICADOR_R
        )

        rr = (
            take_profit - precio
        ) / riesgo_unitario

        if rr < RR_MINIMO:

            registrar_diagnostico(
                ticker_symbol,
                company,
                "RR",
                "RR_INSUFICIENTE",
                RR=rr,
            )

            return None

        # ====================================================
        # DISTANCIA AL MÁXIMO 52 SEMANAS
        # ====================================================

        if high_252:

            distancia_high_252 = (
                precio / high_252 - 1
            ) * 100

        else:

            distancia_high_252 = None

        # ====================================================
        # RETURNS PARA CORRELACIÓN
        # ====================================================

        returns = (
            data["Close"]
            .pct_change()
            .tail(CORRELACION_LOOKBACK)
            .dropna()
        )

        # ====================================================
        # RESULTADO
        # ====================================================

        resultado = {

            "ticker": ticker_symbol,

            "empresa": company,

            "sector": sector,

            "icono": MAESTRO_ACTIVOS.get(
                ticker_symbol,
                (
                    company,
                    sector,
                    "📈",
                ),
            )[2],

            "precio": round(
                precio,
                4,
            ),

            "ema20": round(
                ema20,
                4,
            ),

            "ema50": round(
                ema50,
                4,
            ),

            "ema200": round(
                ema200,
                4,
            ),

            "stop_loss": round(
                stop_loss,
                4,
            ),

            "take_profit": round(
                take_profit,
                4,
            ),

            "riesgo_unitario": round(
                riesgo_unitario,
                4,
            ),

            "ratio_rr": round(
                rr,
                2,
            ),

            "riesgo_pct": round(
                risk_pct * 100,
                2,
            ),

            "score_bruto": round(
                score_bruto,
                2,
            ),

            "score": round(
                score_bruto,
                2,
            ),

            "momentum_score": round(
                momentum_score,
                2,
            ),

            "trend_score": round(
                trend_score,
                2,
            ),

            "rs_score": round(
                rs_score,
                2,
            ),

            "volume_score": round(
                volume_score,
                2,
            ),

            "breakout_score": round(
                breakout_score,
                2,
            ),

            "volatility_score": round(
                volatility_score,
                2,
            ),

            "fundamental_score": round(
                fundamental_score,
                2,
            ),

            "rsi": round(
                rsi,
                2,
            ),

            "atr": round(
                atr,
                4,
            ),

            "atr_pct": round(
                atr_pct,
                2,
            ),

            "ratio_volumen": round(
                volume_ratio,
                2,
            ),

            # IMPORTANTE:
            # mom60 ya está expresado en %.
            "mom20": round(
                mom20,
                2,
            ),

            "mom60": round(
                mom60,
                2,
            ),

            "mom120": round(
                mom120,
                2,
            ),

            "mom252": round(
                mom252,
                2,
            ),

            # También ya está expresado en puntos porcentuales.
            "relative_strength_60": round(
                relative_strength,
                2,
            ),

            "distancia_high_252": (
                round(
                    distancia_high_252,
                    2,
                )
                if distancia_high_252
                is not None
                else None
            ),

            "breakout_50": round(
                breakout_score,
                2,
            ),

            "per": (
                round(per, 2)
                if per is not None
                else None
            ),

            "soporte": (
                round(
                    soporte_15,
                    4,
                )
                if soporte_15
                is not None
                else None
            ),

            "soporte_60": (
                round(
                    soporte_60,
                    4,
                )
                if soporte_60
                is not None
                else None
            ),

            "resistencia": (
                round(
                    resistencia_60,
                    4,
                )
                if resistencia_60
                is not None
                else None
            ),

            "avg_eur_volume": round(
                eur_vol_medio,
                2,
            ),

            # No se escribe al CSV.
            "_returns": returns,
        }

        registrar_diagnostico(
            ticker_symbol,
            company,
            "ELEGIBLE",
            "PASA_FILTROS",
            Score=score_bruto,
            RSI=rsi,
            Volume_Ratio=volume_ratio,
            Momentum60=mom60,
            RelativeStrength60=relative_strength,
            ATR_pct=atr_pct,
            Risk_pct=risk_pct,
        )

        return resultado

    except Exception as e:

        print(
            f"⚠️ Error analizando "
            f"{ticker_symbol}: "
            f"{type(e).__name__}: {e}"
        )

        registrar_diagnostico(
            ticker_symbol,
            company,
            "ERROR",
            f"{type(e).__name__}: {e}",
        )

        return None


# ============================================================
# RANKING CROSS-SECTIONAL
# ============================================================

def aplicar_ranking_cross_sectional(
    candidatos
):

    if not candidatos:
        return []

    df = pd.DataFrame(
        candidatos
    )

    factores = [
        "momentum_score",
        "rs_score",
        "trend_score",
        "breakout_score",
        "volume_score",
        "volatility_score",
        "fundamental_score",
    ]

    for factor in factores:

        if factor not in df.columns:
            continue

        # Percentil dentro del universo analizado.
        df[
            f"{factor}_rank"
        ] = (
            df[factor]
            .rank(
                pct=True,
                method="average",
            )
            * 100
        )

    df["score"] = (
        df["momentum_score_rank"]
        * PESO_MOMENTUM
        + df["rs_score_rank"]
        * PESO_RELATIVE_STRENGTH
        + df["trend_score_rank"]
        * PESO_TENDENCIA
        + df["breakout_score_rank"]
        * PESO_BREAKOUT
        + df["volume_score_rank"]
        * PESO_VOLUMEN
        + df["volatility_score_rank"]
        * PESO_VOLATILIDAD
        + df["fundamental_score_rank"]
        * PESO_FUNDAMENTAL
    ) / 100

    df["score"] = df[
        "score"
    ].round(2)

    resultados = []

    for _, row in df.iterrows():

        candidato = row.to_dict()

        # Convertimos NaN a None.
        for key, value in list(
            candidato.items()
        ):

            if pd.isna(value):
                candidato[key] = None

        resultados.append(
            candidato
        )

    return resultados


# ============================================================
# POSITION SIZING
# ============================================================

def calcular_position_size(
    candidato,
    regimen,
):

    precio = candidato["precio"]

    stop = candidato["stop_loss"]

    riesgo_unitario = (
        precio - stop
    )

    if riesgo_unitario <= 0:
        return candidato

    multiplicador_regimen = (
        multiplicador_riesgo_regimen(
            regimen
        )
    )

    # Score-dependent risk.
    #
    # 70 => 70% del riesgo base.
    # 100 => 100%.
    #
    multiplicador_score = max(
        0.70,
        min(
            1.00,
            candidato["score"] / 100,
        ),
    )

    riesgo_objetivo_eur = (
        CAPITAL_REFERENCIA
        * RIESGO_POR_OPERACION
        * multiplicador_regimen
        * multiplicador_score
    )

    cantidad = (
        riesgo_objetivo_eur
        / riesgo_unitario
    )

    posicion_eur = (
        cantidad
        * precio
    )

    # Cap de nominal.
    max_posicion_eur = (
        CAPITAL_REFERENCIA
        * MAX_POSICION_NOMINAL
    )

    if posicion_eur > max_posicion_eur:

        posicion_eur = (
            max_posicion_eur
        )

        cantidad = (
            posicion_eur
            / precio
        )

    riesgo_real_eur = (
        cantidad
        * riesgo_unitario
    )

    riesgo_real_pct = (
        riesgo_real_eur
        / CAPITAL_REFERENCIA
        * 100
    )

    candidato["cantidad"] = round(
        cantidad,
        4,
    )

    candidato[
        "posicion_eur_referencia"
    ] = round(
        posicion_eur,
        2,
    )

    candidato[
        "riesgo_objetivo_eur"
    ] = round(
        riesgo_objetivo_eur,
        2,
    )

    candidato[
        "riesgo_real_eur"
    ] = round(
        riesgo_real_eur,
        2,
    )

    candidato[
        "riesgo_real_pct"
    ] = round(
        riesgo_real_pct,
        3,
    )

    candidato[
        "multiplicador_regimen"
    ] = multiplicador_regimen

    return candidato


# ============================================================
# CORRELACIÓN
# ============================================================

def obtener_returns_ticker(
    ticker
):

    try:

        data = yf.download(
            ticker,
            period="6mo",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        data = normalizar_columnas(
            data
        )

        if (
            data.empty
            or "Close"
            not in data.columns
        ):
            return None

        return (
            data["Close"]
            .pct_change()
            .dropna()
            .tail(
                CORRELACION_LOOKBACK
            )
        )

    except Exception:

        return None


def correlacion_con_cartera(
    candidato,
    candidatos_seleccionados,
    retornos_cartera,
):

    ticker = candidato[
        "ticker"
    ]

    candidate_returns = candidato.get(
        "_returns"
    )

    if candidate_returns is None:
        return False, None, None

    for seleccionado in (
        candidatos_seleccionados
    ):

        other_returns = seleccionado.get(
            "_returns"
        )

        if other_returns is None:
            continue

        df = pd.concat(
            [
                candidate_returns.rename(
                    "candidate"
                ),
                other_returns.rename(
                    "other"
                ),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(df) < 30:
            continue

        corr = df[
            "candidate"
        ].corr(
            df["other"]
        )

        if (
            corr is not None
            and corr >= CORRELACION_MAXIMA
        ):

            return (
                True,
                seleccionado[
                    "ticker"
                ],
                corr,
            )

    # Comprobamos también posiciones activas.
    for (
        active_ticker,
        active_returns,
    ) in retornos_cartera.items():

        if active_ticker == ticker:
            continue

        if active_returns is None:
            continue

        df = pd.concat(
            [
                candidate_returns.rename(
                    "candidate"
                ),
                active_returns.rename(
                    "active"
                ),
            ],
            axis=1,
            join="inner",
        ).dropna()

        if len(df) < 30:
            continue

        corr = df[
            "candidate"
        ].corr(
            df["active"]
        )

        if (
            corr is not None
            and corr >= CORRELACION_MAXIMA
        ):

            return (
                True,
                active_ticker,
                corr,
            )

    return False, None, None


# ============================================================
# RISK ENGINE
# ============================================================

def filtrar_por_riesgo_y_correlacion(
    candidatos,
    estado_cartera,
):

    activos_actuales = (
        estado_cartera[
            "activas"
        ]
    )

    sectores = dict(
        estado_cartera[
            "sectores"
        ]
    )

    riesgo_actual = (
        estado_cartera[
            "riesgo_total"
        ]
    )

    if (
        len(activos_actuales)
        >= MAX_POSICIONES
    ):
        return []

    # Ranking principal.
    candidatos = sorted(
        candidatos,
        key=lambda x: (
            x["score"],
            x["relative_strength_60"],
            x["mom60"],
        ),
        reverse=True,
    )

    # Returns de posiciones activas.
    retornos_cartera = {}

    for ticker in activos_actuales:

        retornos_cartera[
            ticker
        ] = obtener_returns_ticker(
            ticker
        )

    seleccionados = []

    for candidato in candidatos:

        if (
            len(activos_actuales)
            + len(seleccionados)
            >= MAX_POSICIONES
        ):
            break

        if (
            candidato["score"]
            < SCORE_MINIMO
        ):
            continue

        sector = candidato[
            "sector"
        ]

        # Sector cap.
        if (
            sectores.get(
                sector,
                0,
            )
            + 1
            > MAX_POSICIONES_SECTOR
        ):
            continue

        # Position sizing.
        riesgo_nuevo = (
            candidato.get(
                "riesgo_real_pct",
                0,
            )
            / 100
        )

        riesgo_proyectado = (
            riesgo_actual
            + sum(
                x.get(
                    "riesgo_real_pct",
                    0,
                ) / 100
                for x in seleccionados
            )
            + riesgo_nuevo
        )

        if (
            riesgo_proyectado
            > RIESGO_MAXIMO_TOTAL
        ):
            continue

        # Correlación.
        bloqueado, ticker_corr, corr = (
            correlacion_con_cartera(
                candidato,
                seleccionados,
                retornos_cartera,
            )
        )

        if bloqueado:

            registrar_diagnostico(
                candidato["ticker"],
                candidato["empresa"],
                "CORRELACION",
                f"CORRELACION_ALTA:{ticker_corr}:{corr:.2f}",
                Score=candidato[
                    "score"
                ],
            )

            continue

        seleccionados.append(
            candidato
        )

        sectores[sector] = (
            sectores.get(
                sector,
                0,
            )
            + 1
        )

    return seleccionados


# ============================================================
# IA EXPLICATIVA
# ============================================================

def generar_comentario_ia(
    candidato,
    regimen,
):

    prompt_sistema = """
Eres un analista cuantitativo.

Tu trabajo es EXPLICAR una señal que ya ha sido calculada por
un motor matemático.

No decides si comprar.
No modificas el score.
No inventas datos.
No prometes beneficios.
No hagas predicciones sobre el precio.

Máximo 5 frases.

Debes explicar:
1. Qué factores están impulsando la señal.
2. Momentum y fuerza relativa.
3. Tendencia.
4. Riesgo/stop.
5. Principal condición de invalidación.

Utiliza números concretos.
"""

    prompt_datos = f"""
Activo: {candidato['empresa']}
Ticker: {candidato['ticker']}
Sector: {candidato['sector']}

Score cuantitativo:
{candidato['score']}/100

Régimen:
{regimen}

Precio:
{candidato['precio']} €

EMA20:
{candidato['ema20']} €

EMA50:
{candidato['ema50']} €

EMA200:
{candidato['ema200']} €

RSI:
{candidato['rsi']}

ATR:
{candidato['atr']} €

ATR:
{candidato['atr_pct']} %

Momentum 20d:
{candidato['mom20']} %

Momentum 60d:
{candidato['mom60']} %

Momentum 120d:
{candidato['mom120']} %

Momentum 252d:
{candidato['mom252']} %

Relative Strength 60d:
{candidato['relative_strength_60']} %

Volumen relativo:
x{candidato['ratio_volumen']}

Distancia máximo 252d:
{candidato['distancia_high_252']} %

Stop:
{candidato['stop_loss']} €

Take Profit:
{candidato['take_profit']} €

R/R:
1:{candidato['ratio_rr']}

Riesgo real:
{candidato.get('riesgo_real_pct', 0)} %

Soporte 15d:
{candidato['soporte']} €

Resistencia 60d:
{candidato['resistencia']} €

PER:
{candidato['per']}

Momentum score:
{candidato['momentum_score']}

Trend score:
{candidato['trend_score']}

Relative Strength score:
{candidato['rs_score']}

Breakout score:
{candidato['breakout_score']}
"""

    try:

        response = client.chat.completions.create(
            model=MODELO_LOCAL,
            messages=[
                {
                    "role": "system",
                    "content": prompt_sistema,
                },
                {
                    "role": "user",
                    "content": prompt_datos,
                },
            ],
            temperature=0.2,
        )

        return (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception:

        return (
            f"Score {candidato['score']}/100. "
            f"Momentum 60d {candidato['mom60']}%, "
            f"fuerza relativa {candidato['relative_strength_60']}%, "
            f"volumen x{candidato['ratio_volumen']}. "
            f"El riesgo hasta el stop es "
            f"{candidato.get('riesgo_real_pct', 0)}%."
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
    "Riesgo_Real_Pct",
    "Riesgo_Real_EUR",
    "Cantidad",
    "Position_EUR_Referencia",
    "Score",
    "Score_Bruto",
    "RSI",
    "ATR",
    "ATR_Pct",
    "Ratio_Volumen",
    "Momentum_20",
    "Momentum_60",
    "Momentum_120",
    "Momentum_252",
    "Relative_Strength_60",
    "Distancia_High_252",
    "Breakout_50",
    "PER",
    "EMA20",
    "EMA50",
    "EMA200",
    "Soporte_15",
    "Soporte_60",
    "Resistencia_60",
    "Regimen",
    "Analisis_IA",
    "Estado",
]


def guardar_en_csv(
    candidato,
    comentario_ia,
    regimen,
):

    fila = {
        "Fecha": datetime.now().strftime(
            "%Y-%m-%d"
        ),
        "Ticker": candidato[
            "ticker"
        ],
        "Empresa": candidato[
            "empresa"
        ],
        "Sector": candidato[
            "sector"
        ],
        "Icono": candidato[
            "icono"
        ],
        "Precio_Alerta": candidato[
            "precio"
        ],
        "Stop_Loss": candidato[
            "stop_loss"
        ],
        "Take_Profit": candidato[
            "take_profit"
        ],
        "Ratio_RR": candidato[
            "ratio_rr"
        ],
        "Riesgo_Pct": candidato[
            "riesgo_pct"
        ],
        "Riesgo_Real_Pct": candidato.get(
            "riesgo_real_pct",
            0,
        ),
        "Riesgo_Real_EUR": candidato.get(
            "riesgo_real_eur",
            0,
        ),
        "Cantidad": candidato.get(
            "cantidad",
            0,
        ),
        "Position_EUR_Referencia": candidato.get(
            "posicion_eur_referencia",
            0,
        ),
        "Score": candidato[
            "score"
        ],
        "Score_Bruto": candidato[
            "score_bruto"
        ],
        "RSI": candidato[
            "rsi"
        ],
        "ATR": candidato[
            "atr"
        ],
        "ATR_Pct": candidato[
            "atr_pct"
        ],
        "Ratio_Volumen": candidato[
            "ratio_volumen"
        ],
        "Momentum_20": candidato[
            "mom20"
        ],
        "Momentum_60": candidato[
            "mom60"
        ],
        "Momentum_120": candidato[
            "mom120"
        ],
        "Momentum_252": candidato[
            "mom252"
        ],
        "Relative_Strength_60": candidato[
            "relative_strength_60"
        ],
        "Distancia_High_252": candidato[
            "distancia_high_252"
        ],
        "Breakout_50": candidato[
            "breakout_50"
        ],
        "PER": candidato[
            "per"
        ],
        "EMA20": candidato[
            "ema20"
        ],
        "EMA50": candidato[
            "ema50"
        ],
        "EMA200": candidato[
            "ema200"
        ],
        "Soporte_15": candidato[
            "soporte"
        ],
        "Soporte_60": candidato[
            "soporte_60"
        ],
        "Resistencia_60": candidato[
            "resistencia"
        ],
        "Regimen": regimen,
        "Analisis_IA": comentario_ia.replace(
            "\n",
            " ",
        ),
        "Estado": "ACTIVA",
    }

    # ========================================================
    # Si el CSV antiguo existe, migramos sus columnas.
    # ========================================================

    if os.path.exists(
        ARCHIVO_HISTORIAL
    ):

        filas_antiguas = leer_historial()

        columnas_antiguas = []

        if filas_antiguas:

            columnas_antiguas = list(
                filas_antiguas[0].keys()
            )

        columnas = list(
            dict.fromkeys(
                columnas_antiguas
                + CABECERAS
            )
        )

        with open(
            ARCHIVO_HISTORIAL,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=columnas,
                extrasaction="ignore",
            )

            writer.writeheader()

            for antigua in filas_antiguas:

                writer.writerow(
                    antigua
                )

            writer.writerow(
                fila
            )

    else:

        with open(
            ARCHIVO_HISTORIAL,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=CABECERAS,
            )

            writer.writeheader()

            writer.writerow(
                fila
            )


# ============================================================
# AUDITORÍA + BREAK EVEN + TRAILING
# ============================================================

def auditar_y_mostrar_estadisticas():

    filas = leer_historial()

    if not filas:

        print(
            "ℹ️ No hay historial."
        )

        return

    filas_actualizadas = []

    cambios = False

    for fila in filas:

        if fila.get(
            "Estado",
            "",
        ) != "ACTIVA":

            filas_actualizadas.append(
                fila
            )

            continue

        ticker = fila.get(
            "Ticker"
        )

        fecha_alerta = fila.get(
            "Fecha"
        )

        precio_entrada = safe_float(
            fila.get(
                "Precio_Alerta"
            )
        )

        stop = safe_float(
            fila.get(
                "Stop_Loss"
            )
        )

        tp = safe_float(
            fila.get(
                "Take_Profit"
            )
        )

        atr_inicial = safe_float(
            fila.get(
                "ATR"
            )
        )

        if (
            not ticker
            or not fecha_alerta
            or not precio_entrada
        ):

            filas_actualizadas.append(
                fila
            )

            continue

        if stop is None:

            stop = (
                precio_entrada
                * 0.96
            )

        if tp is None:

            tp = (
                precio_entrada
                + (
                    precio_entrada
                    - stop
                ) * TP_MULTIPLICADOR_R
            )

        try:

            fecha = datetime.strptime(
                fecha_alerta.split()[0],
                "%Y-%m-%d",
            )

            inicio = (
                fecha
                + timedelta(days=1)
            ).strftime(
                "%Y-%m-%d"
            )

            data = yf.download(
                ticker,
                start=inicio,
                auto_adjust=True,
                progress=False,
                threads=False,
            )

            data = normalizar_columnas(
                data
            )

            if data.empty:

                filas_actualizadas.append(
                    fila
                )

                continue

            # =================================================
            # RIESGO ORIGINAL
            # =================================================

            riesgo_original = (
                precio_entrada
                - stop
            )

            if riesgo_original <= 0:

                filas_actualizadas.append(
                    fila
                )

                continue

            # =================================================
            # Estado inicial
            # =================================================

            stop_actual = stop

            resultado = None

            fecha_salida = None

            precio_salida = None

            max_r = 0

            for fecha_dia, dia in data.iterrows():

                high = safe_float(
                    dia.get("High")
                )

                low = safe_float(
                    dia.get("Low")
                )

                close = safe_float(
                    dia.get("Close")
                )

                if (
                    high is None
                    or low is None
                    or close is None
                ):
                    continue

                # R alcanzado según máximo intradía.
                r_actual = (
                    high
                    - precio_entrada
                ) / riesgo_original

                max_r = max(
                    max_r,
                    r_actual,
                )

                # =================================================
                # PRIMERO comprobamos SL / TP actuales.
                #
                # Esto evita utilizar el trailing generado
                # al cierre de la misma sesión para la sesión
                # que ya ha terminado.
                # =================================================

                tp_tocado = (
                    high >= tp
                )

                sl_tocado = (
                    low <= stop_actual
                )

                if (
                    tp_tocado
                    and sl_tocado
                ):

                    resultado = (
                        "AMBIGUO_TP_SL"
                    )

                    fecha_salida = (
                        fecha_dia
                    )

                    cambios = True

                    break

                if tp_tocado:

                    resultado = (
                        "OBJETIVO_CUMPLIDO 🟢"
                    )

                    fecha_salida = (
                        fecha_dia
                    )

                    precio_salida = tp

                    cambios = True

                    break

                if sl_tocado:

                    resultado = (
                        "STOP_SALTADO 🔴"
                    )

                    fecha_salida = (
                        fecha_dia
                    )

                    precio_salida = (
                        stop_actual
                    )

                    cambios = True

                    break

                # =================================================
                # BREAK EVEN
                # =================================================

                if (
                    max_r
                    >= BREAK_EVEN_ACTIVACION_R
                ):

                    stop_actual = max(
                        stop_actual,
                        precio_entrada,
                    )

                # =================================================
                # TRAILING
                # =================================================

                if (
                    max_r
                    >= TRAILING_ACTIVACION_R
                ):

                    atr_dia = safe_float(
                        dia.get("ATR_14")
                    )

                    if atr_dia is None:
                        atr_dia = atr_inicial

                    if atr_dia:

                        trailing = (
                            close
                            - (
                                TRAILING_ATR_MULTIPLIER
                                * atr_dia
                            )
                        )

                        stop_actual = max(
                            stop_actual,
                            trailing,
                        )

            # =================================================
            # Actualización del registro.
            # =================================================

            if resultado:

                fila["Estado"] = (
                    resultado
                )

                if fecha_salida is not None:

                    fila[
                        "Fecha_Salida"
                    ] = fecha_salida.strftime(
                        "%Y-%m-%d"
                    )

                if precio_salida is not None:

                    fila[
                        "Precio_Salida"
                    ] = round(
                        precio_salida,
                        4,
                    )

                fila[
                    "Max_R_Alcanzado"
                ] = round(
                    max_r,
                    2,
                )

            else:

                # Sigue abierta.
                #
                # Guardamos el trailing para que la siguiente
                # ejecución continúe desde el nuevo stop.
                if stop_actual > stop:

                    fila[
                        "Stop_Loss"
                    ] = round(
                        stop_actual,
                        4,
                    )

                    fila[
                        "Trailing_Activo"
                    ] = "SI"

                    fila[
                        "Max_R_Alcanzado"
                    ] = round(
                        max_r,
                        2,
                    )

                    cambios = True

            filas_actualizadas.append(
                fila
            )

        except Exception as e:

            print(
                f"⚠️ Error auditando "
                f"{ticker}: {e}"
            )

            filas_actualizadas.append(
                fila
            )

    # ========================================================
    # Reescribir CSV
    # ========================================================

    if cambios and filas_actualizadas:

        columnas = []

        for fila in filas_actualizadas:

            for key in fila.keys():

                if key not in columnas:

                    columnas.append(key)

        with open(
            ARCHIVO_HISTORIAL,
            mode="w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=columnas,
                extrasaction="ignore",
            )

            writer.writeheader()

            writer.writerows(
                filas_actualizadas
            )

    # ========================================================
    # Estadísticas
    # ========================================================

    total = len(
        filas_actualizadas
    )

    exitos = sum(
        1
        for fila in filas_actualizadas
        if fila.get(
            "Estado",
            "",
        ).startswith(
            "OBJETIVO_CUMPLIDO"
        )
    )

    stops = sum(
        1
        for fila in filas_actualizadas
        if fila.get(
            "Estado",
            "",
        ).startswith(
            "STOP_SALTADO"
        )
    )

    ambiguas = sum(
        1
        for fila in filas_actualizadas
        if fila.get(
            "Estado",
            "",
        ).startswith(
            "AMBIGUO"
        )
    )

    activas = sum(
        1
        for fila in filas_actualizadas
        if fila.get(
            "Estado",
            "",
        ) == "ACTIVA"
    )

    cerradas = (
        exitos
        + stops
    )

    tasa = (
        exitos
        / cerradas
        * 100
        if cerradas
        else 0
    )

    print("\n" + "=" * 65)
    print(
        "📊 AUDITORÍA DEL HISTORIAL"
    )
    print("=" * 65)

    print(
        f"• Alertas: {total}"
    )

    print(
        f"• Objetivos: {exitos}"
    )

    print(
        f"• Stops: {stops}"
    )

    print(
        f"• Ambiguos: {ambiguas}"
    )

    print(
        f"• Activas: {activas}"
    )

    if cerradas:

        print(
            f"• Win rate cerrado: "
            f"{tasa:.1f}%"
        )

    print("=" * 65 + "\n")


# ============================================================
# GITHUB
# ============================================================

def subir_a_github():

    try:

        subprocess.run(
            [
                "git",
                "add",
                ".",
            ],
            check=True,
        )

        status = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
            ],
            capture_output=True,
            text=True,
        )

        if status.stdout.strip():

            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    "BOT 4.0 - quantitative engine update",
                ],
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "push",
                    "origin",
                    "main",
                ],
                check=True,
            )

            print(
                "🚀 Cambios enviados a GitHub."
            )

        else:

            print(
                "💤 Sin cambios para GitHub."
            )

    except Exception as e:

        print(
            f"ℹ️ Git: {e}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)

    print(
        f"🤖 BOT 4.0 — QUANT MOMENTUM ENGINE "
        f"({len(activos)} activos)"
    )

    print("=" * 70)

    # ========================================================
    # 1. AUDITORÍA
    # ========================================================

    auditar_y_mostrar_estadisticas()

    # ========================================================
    # 2. RÉGIMEN
    # ========================================================

    regimen_data = (
        obtener_regimen_mercado()
    )

    regimen = (
        regimen_data[
            "regimen"
        ]
    )

    print(
        f"🌐 Régimen {BENCHMARK}: "
        f"{regimen}"
    )

    if regimen_data[
        "precio"
    ] is not None:

        print(
            f"   Precio: "
            f"{regimen_data['precio']} | "
            f"EMA50: "
            f"{regimen_data['ema50']} | "
            f"EMA200: "
            f"{regimen_data['ema200']} | "
            f"Momentum60: "
            f"{regimen_data['mom60']}%"
        )

    print()

    # ========================================================
    # RISK OFF
    # ========================================================

    if regimen == "RISK_OFF":

        print(
            "🔴 RISK_OFF: "
            "no se generan nuevas operaciones."
        )

        imprimir_diagnostico()

        subir_a_github()

        raise SystemExit(0)

    # ========================================================
    # 3. BLOQUEOS
    # ========================================================

    tickers_bloqueados = (
        obtener_tickers_bloqueados()
    )

    if tickers_bloqueados:

        print(
            "🔒 Bloqueados:",
            ", ".join(
                sorted(
                    tickers_bloqueados
                )
            ),
        )

    # ========================================================
    # 4. ESTADO DE CARTERA
    # ========================================================

    estado_cartera = (
        obtener_exposicion_historial()
    )

    print(
        f"📦 Posiciones activas: "
        f"{len(estado_cartera['activas'])}"
        f"/{MAX_POSICIONES}"
    )

    print(
        f"⚠️ Riesgo real abierto: "
        f"{estado_cartera['riesgo_total'] * 100:.2f}% "
        f"/ "
        f"{RIESGO_MAXIMO_TOTAL * 100:.2f}%"
    )

    if (
        len(
            estado_cartera["activas"]
        )
        >= MAX_POSICIONES
    ):

        print(
            "⛔ Máximo de posiciones alcanzado."
        )

        subir_a_github()

        raise SystemExit(0)

    # ========================================================
    # 5. BENCHMARK RELATIVE STRENGTH
    # ========================================================

    try:

        benchmark = yf.download(
            BENCHMARK,
            period="2y",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )

        benchmark = normalizar_columnas(
            benchmark
        )

        if (
            not benchmark.empty
            and "Close"
            in benchmark.columns
        ):

            bench_close = (
                benchmark[
                    "Close"
                ]
                .dropna()
            )

            if len(
                bench_close
            ) > 60:

                bench_ret60 = (
                    bench_close
                    .pct_change(60)
                    .iloc[-1]
                    * 100
                )

            else:

                bench_ret60 = 0.0

        else:

            bench_ret60 = 0.0

    except Exception:

        bench_ret60 = 0.0

    bench_ret60 = safe_float(
        bench_ret60,
        0.0,
    )

    print(
        f"📈 Benchmark 60d: "
        f"{bench_ret60:.2f}%"
    )

    # ========================================================
    # 6. ESCANEO
    # ========================================================

    candidatos = []

    for idx, ticker in enumerate(
        activos,
        1,
    ):

        if ticker in tickers_bloqueados:
            continue

        empresa, sector, icono = (
            MAESTRO_ACTIVOS.get(
                ticker,
                (
                    ticker,
                    "General",
                    "📈",
                ),
            )
        )

        print(
            f"[{idx}/{len(activos)}] "
            f"Analizando {ticker}...",
            end="\r",
        )

        resultado = analizar_activo(
            ticker,
            empresa,
            sector,
            bench_ret60,
        )

        if resultado:

            candidatos.append(
                resultado
            )

    print(
        "\n"
    )

    print("=" * 70)

    print(
        f"🔎 Activos elegibles: "
        f"{len(candidatos)}"
    )

    print("=" * 70)

    if not candidatos:

        print(
            "💤 No hay activos elegibles."
        )

        imprimir_diagnostico()

        subir_a_github()

        raise SystemExit(0)

    # ========================================================
    # 7. RANKING CROSS-SECTIONAL
    # ========================================================

    candidatos = (
        aplicar_ranking_cross_sectional(
            candidatos
        )
    )

    # ========================================================
    # 8. POSITION SIZING
    # ========================================================

    candidatos_con_riesgo = []

    for candidato in candidatos:

        candidato = (
            calcular_position_size(
                candidato,
                regimen,
            )
        )

        candidatos_con_riesgo.append(
            candidato
        )

    # ========================================================
    # 9. FILTRO SCORE
    # ========================================================

    candidatos_score = [
        c
        for c in candidatos_con_riesgo
        if c["score"]
        >= SCORE_MINIMO
    ]

    candidatos_score.sort(
        key=lambda x: (
            x["score"],
            x["relative_strength_60"],
            x["mom60"],
        ),
        reverse=True,
    )

    print(
        f"🏆 Score >= "
        f"{SCORE_MINIMO}: "
        f"{len(candidatos_score)}"
    )

    # ========================================================
    # 10. RISK ENGINE
    # ========================================================

    seleccionados = (
        filtrar_por_riesgo_y_correlacion(
            candidatos_score,
            estado_cartera,
        )
    )

    seleccionados = (
        seleccionados[
            :MAX_CANDIDATOS
        ]
    )

    print(
        f"🎯 Seleccionados por Risk Engine: "
        f"{len(seleccionados)}"
    )

    print("=" * 70)

    # ========================================================
    # 11. ALERTAS
    # ========================================================

    for candidato in seleccionados:

        comentario = (
            generar_comentario_ia(
                candidato,
                regimen,
            )
        )

        guardar_en_csv(
            candidato,
            comentario,
            regimen,
        )

        print(
            f"\n"
            f"{candidato['icono']} "
            f"{candidato['empresa']} "
            f"({candidato['ticker']})"
        )

        print(
            f"   Score: "
            f"{candidato['score']}/100 "
            f"(bruto {candidato['score_bruto']})"
        )

        print(
            f"   Entrada: "
            f"{candidato['precio']} €"
        )

        print(
            f"   SL: "
            f"{candidato['stop_loss']} € "
            f"(-{candidato['riesgo_pct']}%)"
        )

        print(
            f"   TP: "
            f"{candidato['take_profit']} €"
        )

        print(
            f"   R/R: "
            f"1:{candidato['ratio_rr']}"
        )

        print(
            f"   RSI: "
            f"{candidato['rsi']} | "
            f"ATR: "
            f"{candidato['atr_pct']}%"
        )

        print(
            f"   Volumen: "
            f"x{candidato['ratio_volumen']}"
        )

        print(
            f"   Mom20: "
            f"{candidato['mom20']}% | "
            f"Mom60: "
            f"{candidato['mom60']}% | "
            f"Mom120: "
            f"{candidato['mom120']}%"
        )

        print(
            f"   Mom252: "
            f"{candidato['mom252']}%"
        )

        print(
            f"   RS vs benchmark: "
            f"{candidato['relative_strength_60']}%"
        )

        print(
            f"   Distancia máximo 252d: "
            f"{candidato['distancia_high_252']}%"
        )

        print(
            f"   Posición: "
            f"{candidato['posicion_eur_referencia']:,.0f} €"
        )

        print(
            f"   Cantidad: "
            f"{candidato['cantidad']:,.2f}"
        )

        print(
            f"   Riesgo real: "
            f"{candidato['riesgo_real_eur']:,.2f} € "
            f"({candidato['riesgo_real_pct']:.3f}%)"
        )

        print(
            f"   🤖 {comentario}"
        )

        print(
            "-" * 70
        )

    # ========================================================
    # 12. DIAGNÓSTICO
    # ========================================================

    if MODO_DIAGNOSTICO:

        imprimir_diagnostico()

    # ========================================================
    # FINAL
    # ========================================================

    if not seleccionados:

        print(
            "\n💤 Ninguna oportunidad "
            "superó simultáneamente "
            "ranking + score + riesgo "
            "+ concentración."
        )

    else:

        print(
            f"\n✅ {len(seleccionados)} "
            f"señal(es) generada(s)."
        )

    print(
        "\n💾 BOT 4.0 terminado."
    )

    subir_a_github()