# ============================================================
# ALURA QUANT V4.1
# ============================================================
#
# ARQUITECTURA:
#
# 1. Cada alerta guarda una TESIS ORIGINAL INMUTABLE.
#
# 2. Cada ejecución actualiza únicamente el ESTADO ACTUAL.
#
# 3. La IA compara:
#
#       TESIS ORIGINAL
#             vs
#       SITUACIÓN ACTUAL
#
# 4. Stop Loss y Take Profit originales no se modifican.
#
# 5. Estado:
#
#       ACTIVA
#       STOP_SALTADO
#       OBJETIVO_CUMPLIDO
#
#    representa el estado operativo.
#
# 6. Estado_Estrategia:
#
#       TESIS_REFORZADA
#       TESIS_ESTABLE
#       TESIS_DEBILITADA
#       TESIS_INVALIDADA
#
#    representa exclusivamente la evolución de la tesis.
#
# ============================================================

import csv
import os
import subprocess

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from openai import OpenAI


# ============================================================
# CONFIGURACIÓN
# ============================================================

TZ = ZoneInfo("Europe/Madrid")

MODO_EJECUCION = "AUTO"
# AUTO | 14 | 18

ARCHIVO_HISTORIAL = "historial_alertas.csv"
ARCHIVO_UNIVERSO = "universo_activos.csv"

CAPITAL = 100000.0

RIESGO_POR_OPERACION = 0.005

ATR_MULTIPLICADOR = 1.75

RR_TARGET = 2.5

UMBRAL_SCORE_18 = 55
UMBRAL_SCORE_14 = 50

LIQUIDEZ_MIN_EUR = 500000

CUARENTENA_STOP_DIAS = 15

TAMANO_LOTE = 50


# ============================================================
# IA LOCAL
# ============================================================

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

MODELO_LOCAL = "llama3.2"


# ============================================================
# UNIVERSO BASE
# ============================================================

MAESTRO_ACTIVOS_BASE = {

    "TLGO.MC": (
        "Talgo",
        "Industrial",
        "🚆"
    ),

    "SAN.MC": (
        "Banco Santander",
        "Banca",
        "🏦"
    ),

    "BBVA.MC": (
        "BBVA",
        "Banca",
        "🏦"
    ),

    "ITX.MC": (
        "Inditex",
        "Consumo Cíclico",
        "👗"
    ),
}


def cargar_universo():

    universo = dict(
        MAESTRO_ACTIVOS_BASE
    )

    if os.path.exists(
        ARCHIVO_UNIVERSO
    ):

        try:

            df = pd.read_csv(
                ARCHIVO_UNIVERSO,
                dtype=str
            )

            for _, r in df.iterrows():

                ticker = str(
                    r.get(
                        "Ticker",
                        ""
                    )
                ).strip()

                if ticker:

                    universo[ticker] = (

                        str(
                            r.get(
                                "Empresa",
                                ticker
                            )
                        ),

                        str(
                            r.get(
                                "Sector",
                                "General"
                            )
                        ),

                        str(
                            r.get(
                                "Icono",
                                "📈"
                            )
                        )
                    )

        except Exception as e:

            print(
                f"⚠️ Error cargando universo: {e}"
            )

    return universo


MAESTRO_ACTIVOS = cargar_universo()

activos = list(
    MAESTRO_ACTIVOS.keys()
)


# ============================================================
# CAMPOS DEL HISTORIAL
# ============================================================

CAMPOS_HISTORIAL = [

    # --------------------------------------------------------
    # IDENTIFICACIÓN
    # --------------------------------------------------------

    "Fecha",
    "Ticker",
    "Empresa",
    "Sector",
    "Icono",
    "Modo",

    # --------------------------------------------------------
    # TESIS / SNAPSHOT ORIGINAL
    # --------------------------------------------------------

    "Precio_Alerta",

    "Score_Entrada",
    "RVOL_Entrada",
    "RSI_Entrada",
    "ROC20_Entrada",
    "ATR_Entrada",

    "EMA50_Entrada",
    "EMA200_Entrada",

    "Razones_Entrada",

    "Analisis_IA_Entrada",

    # --------------------------------------------------------
    # ESTRATEGIA ORIGINAL
    # --------------------------------------------------------

    "Stop_Loss",
    "Take_Profit",

    "Ratio_RR",

    "Riesgo_Euros",
    "Acciones",
    "Nominal",

    # --------------------------------------------------------
    # ESTADO ACTUAL
    # --------------------------------------------------------

    "Precio_Actual",

    "Score_Actual",
    "RVOL_Actual",
    "RSI_Actual",
    "ROC20_Actual",
    "ATR_Actual",

    "EMA50_Actual",
    "EMA200_Actual",

    "Razones_Actuales",

    "Distancia_SL_Pct",
    "Distancia_TP_Pct",

    "P&L_Actual_Pct",

    "Estado_Estrategia",

    "Ultima_Actualizacion",

    "Analisis_IA_Actual",

    # --------------------------------------------------------
    # ESTADO OPERATIVO
    # --------------------------------------------------------

    "Estado",

    "Fecha_Salida",

    "Resultado_R",

    "MAE_R",

    "MFE_R"
]


# ============================================================
# TIPOS DE COLUMNAS
# ============================================================

CAMPOS_TEXTO = [

    "Fecha",
    "Ticker",
    "Empresa",
    "Sector",
    "Icono",
    "Modo",

    "Razones_Entrada",
    "Analisis_IA_Entrada",

    "Razones_Actuales",

    "Estado_Estrategia",

    "Ultima_Actualizacion",

    "Analisis_IA_Actual",

    "Estado",

    "Fecha_Salida"
]


CAMPOS_NUMERICOS = [

    "Precio_Alerta",

    "Score_Entrada",
    "RVOL_Entrada",
    "RSI_Entrada",
    "ROC20_Entrada",
    "ATR_Entrada",

    "EMA50_Entrada",
    "EMA200_Entrada",

    "Stop_Loss",
    "Take_Profit",

    "Ratio_RR",

    "Riesgo_Euros",
    "Acciones",
    "Nominal",

    "Precio_Actual",

    "Score_Actual",
    "RVOL_Actual",
    "RSI_Actual",
    "ROC20_Actual",
    "ATR_Actual",

    "EMA50_Actual",
    "EMA200_Actual",

    "Distancia_SL_Pct",
    "Distancia_TP_Pct",

    "P&L_Actual_Pct",

    "Resultado_R",
    "MAE_R",
    "MFE_R"
]


# ============================================================
# UTILIDADES
# ============================================================

def ahora():

    return datetime.now(TZ)


def modo_actual():

    if MODO_EJECUCION in (
        "14",
        "18"
    ):

        return MODO_EJECUCION

    return (
        "14"
        if ahora().hour < 16
        else "18"
    )


def norm(df):

    if isinstance(
        df.columns,
        pd.MultiIndex
    ):

        df.columns = (
            df.columns
            .get_level_values(0)
        )

    return df


# ============================================================
# INDICADORES
# ============================================================

def rsi(
    s,
    n=14
):

    z = s.diff()

    g = z.clip(
        lower=0
    )

    l = -z.clip(
        upper=0
    )

    ag = g.ewm(
        alpha=1 / n,
        adjust=False,
        min_periods=n
    ).mean()

    al = l.ewm(
        alpha=1 / n,
        adjust=False,
        min_periods=n
    ).mean()

    rs = (
        ag
        /
        al.replace(
            0,
            pd.NA
        )
    )

    return (
        100
        -
        100 / (1 + rs)
    )


def atr(
    d,
    n=14
):

    p = d.Close.shift()

    tr = pd.concat(
        [
            d.High - d.Low,
            (d.High - p).abs(),
            (d.Low - p).abs()
        ],
        axis=1
    ).max(axis=1)

    return tr.ewm(
        alpha=1 / n,
        adjust=False,
        min_periods=n
    ).mean()


# ============================================================
# INDICADORES COMPLETOS
# ============================================================

def preparar_indicadores(d):

    d = d.copy()

    d["E20"] = (
        d.Close
        .ewm(
            span=20,
            adjust=False
        )
        .mean()
    )

    d["E50"] = (
        d.Close
        .ewm(
            span=50,
            adjust=False
        )
        .mean()
    )

    d["E200"] = (
        d.Close
        .ewm(
            span=200,
            adjust=False
        )
        .mean()
    )

    d["RSI"] = rsi(
        d.Close
    )

    d["ATR"] = atr(d)

    d["VM20"] = (
        d.Volume
        .rolling(20)
        .mean()
    )

    d["TO20"] = (
        d.Close * d.Volume
    ).rolling(20).mean()

    d["ROC20"] = (
        d.Close
        .pct_change(20)
        * 100
    )

    d["H20"] = (
        d.High
        .rolling(20)
        .max()
        .shift(1)
    )

    d["CLV"] = (

        (
            d.Close - d.Low
        )

        /

        (
            d.High - d.Low
        ).replace(
            0,
            pd.NA
        )

    ).fillna(0)

    return d


# ============================================================
# ESTADO ACTUAL
# ============================================================

def obtener_estado_actual(
    t,
    d
):

    if len(d) < 220:
        return None

    d = preparar_indicadores(d)

    x = d.iloc[-1]

    requeridos = [

        "Close",
        "E50",
        "E200",
        "RSI",
        "ATR",
        "VM20",
        "TO20",
        "ROC20",
        "H20"
    ]

    if any(
        pd.isna(x[k])
        for k in requeridos
    ):

        return None

    price = float(
        x.Close
    )

    e50 = float(
        x.E50
    )

    e200 = float(
        x.E200
    )

    rsi_actual = float(
        x.RSI
    )

    atr_actual = float(
        x.ATR
    )

    rvol = (

        float(
            x.Volume / x.VM20
        )

        if float(x.VM20) > 0

        else 0
    )

    liquidez = float(
        x.TO20
    )

    roc20 = float(
        x.ROC20
    )

    ruptura = (

        price
        >
        float(x.H20)
    )

    clv = float(
        x.CLV
    )

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = 0

    razones = []

    tests = [

        (
            price > e50,
            15,
            "Precio > EMA50"
        ),

        (
            e50 > e200,
            20,
            "EMA50 > EMA200"
        ),

        (
            55 <= rsi_actual <= 75,
            15,
            "RSI 55-75"
        ),

        (
            roc20 > 5,
            10,
            "ROC20 > 5%"
        ),

        (
            rvol >= 1.5,
            15,
            "RVOL >= 1.5x"
        ),

        (
            1.2 <= rvol < 1.5,
            8,
            "RVOL >= 1.2x"
        ),

        (
            clv >= .70,
            5,
            "Cierre cerca de máximos"
        ),

        (
            ruptura,
            15,
            "Ruptura máximo 20 sesiones"
        )
    ]

    for condicion, puntos, texto in tests:

        if condicion:

            score += puntos

            razones.append(
                texto
            )

    info = MAESTRO_ACTIVOS.get(
        t,
        (
            t,
            "General",
            "📈"
        )
    )

    return {

        "ticker":
            t,

        "empresa":
            info[0],

        "sector":
            info[1],

        "icono":
            info[2],

        "precio":
            round(
                price,
                2
            ),

        "score":
            int(score),

        "rvol":
            round(
                rvol,
                2
            ),

        "rsi":
            round(
                rsi_actual,
                2
            ),

        "roc20":
            round(
                roc20,
                2
            ),

        "atr":
            round(
                atr_actual,
                2
            ),

        "e50":
            round(
                e50,
                2
            ),

        "e200":
            round(
                e200,
                2
            ),

        "razones":
            "; ".join(
                razones
            ),

        "soporte":
            round(
                float(
                    d.Low.iloc[-16:-1].min()
                ),
                2
            ),

        "resistencia":
            round(
                float(
                    d.High.iloc[-61:-1].max()
                ),
                2
            ),

        "liquidez":
            round(
                liquidez,
                2
            )
    }


# ============================================================
# PROCESAR NUEVA OPORTUNIDAD
# ============================================================

def procesar_dataframe_activo(
    t,
    d
):

    estado = obtener_estado_actual(
        t,
        d
    )

    if estado is None:
        return None

    modo = modo_actual()

    score = estado["score"]

    rvol = estado["rvol"]

    precio = estado["precio"]

    e50 = estado["e50"]

    e200 = estado["e200"]

    liquidez = estado["liquidez"]

    # --------------------------------------------------------
    # FILTRO LIQUIDEZ
    # --------------------------------------------------------

    if liquidez < LIQUIDEZ_MIN_EUR:

        return None

    # --------------------------------------------------------
    # UMBRAL
    # --------------------------------------------------------

    umbral = (

        UMBRAL_SCORE_14

        if modo == "14"

        else UMBRAL_SCORE_18
    )

    if score < umbral:

        return None

    # --------------------------------------------------------
    # VOLUMEN
    # --------------------------------------------------------

    if rvol < 1.2:

        return None

    # --------------------------------------------------------
    # TENDENCIA
    # --------------------------------------------------------

    if not (
        precio > e50
        and
        e50 > e200
    ):

        return None

    # --------------------------------------------------------
    # STOP
    # --------------------------------------------------------

    soporte = estado["soporte"]

    resistencia = estado["resistencia"]

    atr_actual = estado["atr"]

    stop = min(

        precio
        -
        ATR_MULTIPLICADOR
        *
        atr_actual,

        soporte * .99
    )

    riesgo_unitario = (
        precio
        -
        stop
    )

    if riesgo_unitario <= 0:

        return None

    if riesgo_unitario > precio * .20:

        return None

    # --------------------------------------------------------
    # TAMAÑO
    # --------------------------------------------------------

    acciones = int(

        (
            CAPITAL
            *
            RIESGO_POR_OPERACION
        )

        /

        riesgo_unitario
    )

    if acciones < 1:

        return None

    info = MAESTRO_ACTIVOS.get(
        t,
        (
            t,
            "General",
            "📈"
        )
    )

    take_profit = (

        precio
        +
        RR_TARGET
        *
        riesgo_unitario
    )

    return {

        "ticker":
            t,

        "empresa":
            info[0],

        "sector":
            info[1],

        "icono":
            info[2],

        "modo":
            modo,

        # ----------------------------------------------------
        # SNAPSHOT ORIGINAL
        # ----------------------------------------------------

        "precio":
            precio,

        "score":
            estado["score"],

        "rvol":
            estado["rvol"],

        "rsi":
            estado["rsi"],

        "roc20":
            estado["roc20"],

        "atr":
            estado["atr"],

        "e50":
            estado["e50"],

        "e200":
            estado["e200"],

        "razones":
            estado["razones"],

        "soporte":
            soporte,

        "resistencia":
            resistencia,

        # ----------------------------------------------------
        # ESTRATEGIA
        # ----------------------------------------------------

        "stop":
            round(
                stop,
                2
            ),

        "tp":
            round(
                take_profit,
                2
            ),

        "acciones":
            acciones,

        "nominal":
            round(
                acciones * precio,
                2
            ),

        "riesgo":
            round(
                acciones * riesgo_unitario,
                2
            )
    }


# ============================================================
# IA - NUEVA ENTRADA
# ============================================================

def comentario_entrada(c):

    try:

        system_prompt = """
Eres el analista cuantitativo senior de Alura Quant.

Se acaba de detectar una nueva oportunidad mediante
una estrategia sistemática de tendencia, momentum y volumen.

Explica en 2 o 3 frases por qué la acción ha sido
incluida y cuál es la tesis cuantitativa.

Integra tendencia, momentum y volumen.

No uses listas.
No uses títulos.
No uses lenguaje robótico.
No hagas predicciones categóricas.
"""

        user_prompt = f"""

Activo:
{c['empresa']} ({c['ticker']})

Precio:
{c['precio']}€

Score:
{c['score']}/100

RVOL:
{c['rvol']}x

RSI:
{c['rsi']}

ROC20:
{c['roc20']}%

ATR:
{c['atr']}€

EMA50:
{c['e50']}€

EMA200:
{c['e200']}€

Razones:
{c['razones']}

Stop Loss:
{c['stop']}€

Take Profit:
{c['tp']}€

R:R:
{RR_TARGET}
"""

        respuesta = client.chat.completions.create(

            model=MODELO_LOCAL,

            messages=[

                {
                    "role":
                        "system",

                    "content":
                        system_prompt
                },

                {
                    "role":
                        "user",

                    "content":
                        user_prompt
                }
            ],

            temperature=0.7
        )

        return (
            respuesta
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        print(
            f"⚠️ Error IA entrada: {e}"
        )

        return (

            f"Entrada basada en una estructura "
            f"cuantitativa favorable, con score "
            f"{c['score']}/100 y RVOL de "
            f"{c['rvol']}x."
        )


# ============================================================
# EVALUACIÓN DE EVOLUCIÓN
# ============================================================

def evaluar_evolucion_estrategia(
    original,
    actual
):

    cambios = []

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    delta_score = (

        float(actual["score"])
        -
        float(original["score"])
    )

    if delta_score >= 10:

        cambios.append(
            "score claramente reforzado"
        )

    elif delta_score <= -10:

        cambios.append(
            "score claramente deteriorado"
        )

    else:

        cambios.append(
            "score relativamente estable"
        )

    # --------------------------------------------------------
    # TENDENCIA
    # --------------------------------------------------------

    tendencia_actual = (

        float(actual["precio"])
        >
        float(actual["e50"])

        and

        float(actual["e50"])
        >
        float(actual["e200"])
    )

    if tendencia_actual:

        cambios.append(
            "estructura de tendencia preservada"
        )

    else:

        cambios.append(
            "estructura de tendencia deteriorada"
        )

    # --------------------------------------------------------
    # RVOL
    # --------------------------------------------------------

    rvol_original = float(
        original["rvol"]
    )

    rvol_actual = float(
        actual["rvol"]
    )

    if rvol_actual >= rvol_original * 1.10:

        cambios.append(
            "confirmación por volumen mejorada"
        )

    elif rvol_actual <= rvol_original * .80:

        cambios.append(
            "confirmación por volumen debilitada"
        )

    else:

        cambios.append(
            "volumen relativamente estable"
        )

    # --------------------------------------------------------
    # ROC
    # --------------------------------------------------------

    roc_original = float(
        original["roc20"]
    )

    roc_actual = float(
        actual["roc20"]
    )

    if roc_actual >= roc_original + 2:

        cambios.append(
            "momentum mejorado"
        )

    elif roc_actual <= roc_original - 2:

        cambios.append(
            "momentum debilitado"
        )

    else:

        cambios.append(
            "momentum estable"
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi_actual = float(
        actual["rsi"]
    )

    if rsi_actual > 75:

        cambios.append(
            "RSI actualmente elevado"
        )

    elif rsi_actual < 50:

        cambios.append(
            "RSI por debajo de la zona de fortaleza"
        )

    else:

        cambios.append(
            "RSI compatible con la tesis"
        )

    return "; ".join(
        cambios
    )


# ============================================================
# ESTADO DE LA TESIS
# ============================================================

def estado_estrategia(
    original,
    actual
):

    fuertes = 0

    debiles = 0

    # --------------------------------------------------------
    # TENDENCIA
    # --------------------------------------------------------

    precio = float(
        actual["precio"]
    )

    e50 = float(
        actual["e50"]
    )

    e200 = float(
        actual["e200"]
    )

    if (
        precio > e50
        and
        e50 > e200
    ):

        fuertes += 1

    else:

        debiles += 1

    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score_original = float(
        original["score"]
    )

    score_actual = float(
        actual["score"]
    )

    if score_actual >= score_original + 10:

        fuertes += 1

    elif score_actual <= score_original - 10:

        debiles += 1

    # --------------------------------------------------------
    # VOLUMEN
    # --------------------------------------------------------

    rvol_original = float(
        original["rvol"]
    )

    rvol_actual = float(
        actual["rvol"]
    )

    if rvol_actual >= rvol_original * 1.10:

        fuertes += 1

    elif rvol_actual <= rvol_original * .80:

        debiles += 1

    # --------------------------------------------------------
    # MOMENTUM
    # --------------------------------------------------------

    roc_original = float(
        original["roc20"]
    )

    roc_actual = float(
        actual["roc20"]
    )

    if roc_actual >= roc_original + 2:

        fuertes += 1

    elif roc_actual <= roc_original - 2:

        debiles += 1

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    rsi_actual = float(
        actual["rsi"]
    )

    if 50 <= rsi_actual <= 75:

        fuertes += 1

    elif rsi_actual < 45:

        debiles += 1

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    if debiles >= 3:

        return "TESIS_INVALIDADA"

    if debiles >= 2:

        return "TESIS_DEBILITADA"

    if fuertes >= 3:

        return "TESIS_REFORZADA"

    return "TESIS_ESTABLE"


# ============================================================
# CREAR COLUMNAS / NORMALIZAR HISTÓRICO
# ============================================================

def preparar_historial():

    # --------------------------------------------------------
    # SI NO EXISTE, NO HACER NADA
    # --------------------------------------------------------

    if not os.path.exists(
        ARCHIVO_HISTORIAL
    ):

        return

    try:

        # IMPORTANTÍSIMO:
        #
        # Primero cargamos TODO como texto.
        #
        # Así Pandas nunca decide que una columna de texto
        # como Razones_Actuales es float64.
        #

        df = pd.read_csv(
            ARCHIVO_HISTORIAL,
            dtype=str,
            keep_default_na=False
        )

        # ----------------------------------------------------
        # COLUMNAS ANTIGUAS
        # ----------------------------------------------------

        columnas_originales = set(
            df.columns
        )

        # ----------------------------------------------------
        # CREAR CAMPOS NUEVOS
        # ----------------------------------------------------

        for col in CAMPOS_HISTORIAL:

            if col not in df.columns:

                df[col] = ""

        # ----------------------------------------------------
        # MIGRACIÓN DE HISTÓRICO ANTIGUO
        #
        # Si una alerta fue creada con una versión anterior,
        # sus campos:
        #
        # Score
        # RVOL
        # RSI
        # ROC20
        # ATR
        # etc.
        #
        # representan los datos originales de entrada.
        # ----------------------------------------------------

        MAPEO_ANTIGUO = {

            "Score":
                "Score_Entrada",

            "RVOL":
                "RVOL_Entrada",

            "RSI":
                "RSI_Entrada",

            "ROC20":
                "ROC20_Entrada",

            "ATR":
                "ATR_Entrada",

            "EMA50":
                "EMA50_Entrada",

            "EMA200":
                "EMA200_Entrada",

            "Razones":
                "Razones_Entrada",

            "Analisis_IA":
                "Analisis_IA_Entrada"
        }

        for antiguo, nuevo in MAPEO_ANTIGUO.items():

            if antiguo in columnas_originales:

                mask = (

                    df[nuevo]
                    .astype(str)
                    .str.strip()
                    == ""
                )

                df.loc[
                    mask,
                    nuevo
                ] = (
                    df.loc[
                        mask,
                        antiguo
                    ]
                )

        # ----------------------------------------------------
        # Precio_Alerta
        # ----------------------------------------------------

        if "Precio_Alerta" not in columnas_originales:

            if "Precio_Entrada" in columnas_originales:

                df["Precio_Alerta"] = (
                    df["Precio_Entrada"]
                )

        # ----------------------------------------------------
        # Rellenar ESTADO ACTUAL inicial para históricos
        # ----------------------------------------------------

        # Solo si está vacío.
        #
        # NO sobrescribimos información actual ya existente.

        pares = [

            (
                "Precio_Alerta",
                "Precio_Actual"
            ),

            (
                "Score_Entrada",
                "Score_Actual"
            ),

            (
                "RVOL_Entrada",
                "RVOL_Actual"
            ),

            (
                "RSI_Entrada",
                "RSI_Actual"
            ),

            (
                "ROC20_Entrada",
                "ROC20_Actual"
            ),

            (
                "ATR_Entrada",
                "ATR_Actual"
            ),

            (
                "EMA50_Entrada",
                "EMA50_Actual"
            ),

            (
                "EMA200_Entrada",
                "EMA200_Actual"
            ),

            (
                "Razones_Entrada",
                "Razones_Actuales"
            )
        ]

        for origen, destino in pares:

            mask = (

                df[destino]
                .astype(str)
                .str.strip()
                == ""
            )

            df.loc[
                mask,
                destino
            ] = df.loc[
                mask,
                origen
            ]

        # ----------------------------------------------------
        # Estado estrategia
        # ----------------------------------------------------

        mask_estado = (

            df["Estado_Estrategia"]
            .astype(str)
            .str.strip()
            == ""
        )

        df.loc[
            mask_estado,
            "Estado_Estrategia"
        ] = "TESIS_ESTABLE"

        # ----------------------------------------------------
        # Ratio RR
        # ----------------------------------------------------

        mask_rr = (

            df["Ratio_RR"]
            .astype(str)
            .str.strip()
            == ""
        )

        df.loc[
            mask_rr,
            "Ratio_RR"
        ] = str(
            RR_TARGET
        )

        # ----------------------------------------------------
        # Estado operativo
        # ----------------------------------------------------

        mask_estado_op = (

            df["Estado"]
            .astype(str)
            .str.strip()
            == ""
        )

        df.loc[
            mask_estado_op,
            "Estado"
        ] = "ACTIVA"

        # ----------------------------------------------------
        # ASEGURAR TEXTO
        # ----------------------------------------------------

        for col in CAMPOS_TEXTO:

            if col in df.columns:

                df[col] = (
                    df[col]
                    .fillna("")
                    .astype(str)
                )

        # ----------------------------------------------------
        # ASEGURAR NUMÉRICOS
        # ----------------------------------------------------

        for col in CAMPOS_NUMERICOS:

            if col in df.columns:

                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

        # ----------------------------------------------------
        # ORDEN
        # ----------------------------------------------------

        df = df.reindex(
            columns=CAMPOS_HISTORIAL
        )

        # ----------------------------------------------------
        # GUARDAR
        # ----------------------------------------------------

        df.to_csv(
            ARCHIVO_HISTORIAL,
            index=False
        )

        print(
            "✅ Historial preparado "
            "y columnas normalizadas."
        )

    except Exception as e:

        print(
            f"⚠️ Error preparando historial: {e}"
        )


# ============================================================
# LEER HISTORIAL
# ============================================================

def cargar_historial():

    if not os.path.exists(
        ARCHIVO_HISTORIAL
    ):

        return pd.DataFrame(
            columns=CAMPOS_HISTORIAL
        )

    preparar_historial()

    try:

        df = pd.read_csv(
            ARCHIVO_HISTORIAL,
            dtype=str,
            keep_default_na=False
        )

        # ----------------------------------------------------
        # ASEGURAR COLUMNAS
        # ----------------------------------------------------

        for col in CAMPOS_HISTORIAL:

            if col not in df.columns:

                df[col] = ""

        # ----------------------------------------------------
        # TEXTO
        # ----------------------------------------------------

        for col in CAMPOS_TEXTO:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
            )

        # ----------------------------------------------------
        # NUMÉRICOS
        # ----------------------------------------------------

        for col in CAMPOS_NUMERICOS:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        return df

    except Exception as e:

        print(
            f"⚠️ Error leyendo historial: {e}"
        )

        return pd.DataFrame(
            columns=CAMPOS_HISTORIAL
        )


# ============================================================
# CONSTRUIR SNAPSHOT ORIGINAL
# ============================================================

def construir_original_desde_fila(
    r
):

    def num(
        campo,
        default=0
    ):

        try:

            value = r.get(
                campo,
                default
            )

            if pd.isna(value):

                return default

            return float(value)

        except Exception:

            return default

    return {

        "ticker":
            str(
                r.get(
                    "Ticker",
                    ""
                )
            ),

        "empresa":
            str(
                r.get(
                    "Empresa",
                    ""
                )
            ),

        "precio":
            num(
                "Precio_Alerta"
            ),

        "score":
            num(
                "Score_Entrada"
            ),

        "rvol":
            num(
                "RVOL_Entrada"
            ),

        "rsi":
            num(
                "RSI_Entrada"
            ),

        "roc20":
            num(
                "ROC20_Entrada"
            ),

        "atr":
            num(
                "ATR_Entrada"
            ),

        "e50":
            num(
                "EMA50_Entrada"
            ),

        "e200":
            num(
                "EMA200_Entrada"
            ),

        "razones":
            str(
                r.get(
                    "Razones_Entrada",
                    ""
                )
            )
    }


# ============================================================
# IA - SEGUIMIENTO
# ============================================================

def comentario_seguimiento(
    original,
    actual,
    fila,
    evolucion
):

    try:

        precio_entrada = float(
            fila["Precio_Alerta"]
        )

        precio_actual = float(
            actual["precio"]
        )

        sl = float(
            fila["Stop_Loss"]
        )

        tp = float(
            fila["Take_Profit"]
        )

        # ----------------------------------------------------
        # P&L
        # ----------------------------------------------------

        pnl_pct = (

            (
                precio_actual
                /
                precio_entrada
            )
            - 1

        ) * 100

        # ----------------------------------------------------
        # DISTANCIA SL
        # ----------------------------------------------------

        distancia_sl = (

            (
                precio_actual
                -
                sl
            )
            /
            precio_actual

        ) * 100

        # ----------------------------------------------------
        # DISTANCIA TP
        # ----------------------------------------------------

        distancia_tp = (

            (
                tp
                -
                precio_actual
            )
            /
            precio_actual

        ) * 100

        # ----------------------------------------------------
        # DELTAS
        # ----------------------------------------------------

        delta_score = (

            actual["score"]
            -
            original["score"]
        )

        delta_rvol = (

            actual["rvol"]
            -
            original["rvol"]
        )

        delta_rsi = (

            actual["rsi"]
            -
            original["rsi"]
        )

        delta_roc = (

            actual["roc20"]
            -
            original["roc20"]
        )

        system_prompt = """
Eres el analista cuantitativo senior de Alura Quant.

Estás monitorizando una estrategia YA ABIERTA.

NO estás buscando una nueva entrada.

Tu tarea es comparar la tesis original que justificó
la entrada con los datos actuales y explicar cómo está
evolucionando esa estrategia.

Debes considerar:

- precio desde entrada
- tendencia
- score
- volumen
- momentum
- RSI
- proximidad al Stop Loss
- proximidad al Take Profit

Debes señalar divergencias importantes.

Ejemplo:
si el precio sube pero el RVOL y el score se deterioran,
debes indicarlo.

No debes:

- crear una nueva estrategia
- modificar Stop Loss
- modificar Take Profit
- recomendar una nueva entrada
- cerrar la operación

El Estado_Estrategia es una lectura analítica,
no una orden operativa.

Máximo 3 frases.

Sin listas.
Sin títulos.
Sin lenguaje robótico.
"""

        user_prompt = f"""

========================
ACTIVO
========================

{original['empresa']}
{original['ticker']}


========================
TESIS ORIGINAL
========================

Precio:
{precio_entrada:.2f}€

Score:
{original['score']}

RVOL:
{original['rvol']}x

RSI:
{original['rsi']}

ROC20:
{original['roc20']}%

ATR:
{original['atr']}€

EMA50:
{original['e50']}€

EMA200:
{original['e200']}€

Razones:
{original['razones']}


========================
ESTADO ACTUAL
========================

Precio:
{precio_actual:.2f}€

Score:
{actual['score']}

RVOL:
{actual['rvol']}x

RSI:
{actual['rsi']}

ROC20:
{actual['roc20']}%

ATR:
{actual['atr']}€

EMA50:
{actual['e50']}€

EMA200:
{actual['e200']}€

Razones actuales:
{actual['razones']}


========================
EVOLUCIÓN
========================

P&L:
{pnl_pct:+.2f}%

Cambio Score:
{delta_score:+.0f}

Cambio RVOL:
{delta_rvol:+.2f}x

Cambio RSI:
{delta_rsi:+.2f}

Cambio ROC20:
{delta_roc:+.2f} puntos


Lectura cuantitativa:

{evolucion}


========================
ESTRATEGIA ORIGINAL
========================

Entrada:
{precio_entrada:.2f}€

Stop Loss:
{sl:.2f}€

Take Profit:
{tp:.2f}€

Distancia actual al SL:
{distancia_sl:.2f}%

Distancia actual al TP:
{distancia_tp:.2f}%


INSTRUCCIÓN

Explica cómo está evolucionando la tesis original.

Determina si está:

- reforzada
- estable
- debilitada
- invalidada

y explica brevemente por qué.

Prioriza cambios relevantes frente a repetir
simplemente los datos.
"""

        respuesta = client.chat.completions.create(

            model=MODELO_LOCAL,

            messages=[

                {
                    "role":
                        "system",

                    "content":
                        system_prompt
                },

                {
                    "role":
                        "user",

                    "content":
                        user_prompt
                }
            ],

            temperature=0.65
        )

        return (
            respuesta
            .choices[0]
            .message
            .content
            .strip()
        )

    except Exception as e:

        print(
            f"⚠️ Error IA seguimiento: {e}"
        )

        return (

            f"La posición presenta una evolución "
            f"del {pnl_pct:+.2f}% desde la entrada, "
            f"con un score actual de "
            f"{actual['score']} frente a "
            f"{original['score']} en la entrada."
        )


# ============================================================
# GUARDAR NUEVA ALERTA
# ============================================================

def guardar(
    c,
    comentario
):

    preparar_historial()

    df = cargar_historial()

    nueva_fila = {

        "Fecha":
            ahora().strftime(
                "%Y-%m-%d %H:%M"
            ),

        "Ticker":
            c["ticker"],

        "Empresa":
            c["empresa"],

        "Sector":
            c["sector"],

        "Icono":
            c["icono"],

        "Modo":
            c["modo"],

        # ----------------------------------------------------
        # ORIGINAL
        # ----------------------------------------------------

        "Precio_Alerta":
            c["precio"],

        "Score_Entrada":
            c["score"],

        "RVOL_Entrada":
            c["rvol"],

        "RSI_Entrada":
            c["rsi"],

        "ROC20_Entrada":
            c["roc20"],

        "ATR_Entrada":
            c["atr"],

        "EMA50_Entrada":
            c["e50"],

        "EMA200_Entrada":
            c["e200"],

        "Razones_Entrada":
            c["razones"],

        "Analisis_IA_Entrada":
            comentario.replace(
                "\n",
                " "
            ),

        # ----------------------------------------------------
        # ESTRATEGIA
        # ----------------------------------------------------

        "Stop_Loss":
            c["stop"],

        "Take_Profit":
            c["tp"],

        "Ratio_RR":
            RR_TARGET,

        "Riesgo_Euros":
            c["riesgo"],

        "Acciones":
            c["acciones"],

        "Nominal":
            c["nominal"],

        # ----------------------------------------------------
        # ACTUAL
        # ----------------------------------------------------

        "Precio_Actual":
            c["precio"],

        "Score_Actual":
            c["score"],

        "RVOL_Actual":
            c["rvol"],

        "RSI_Actual":
            c["rsi"],

        "ROC20_Actual":
            c["roc20"],

        "ATR_Actual":
            c["atr"],

        "EMA50_Actual":
            c["e50"],

        "EMA200_Actual":
            c["e200"],

        "Razones_Actuales":
            c["razones"],

        "Distancia_SL_Pct":
            round(
                (
                    (
                        c["precio"]
                        -
                        c["stop"]
                    )
                    /
                    c["precio"]
                )
                * 100,
                2
            ),

        "Distancia_TP_Pct":
            round(
                (
                    (
                        c["tp"]
                        -
                        c["precio"]
                    )
                    /
                    c["precio"]
                )
                * 100,
                2
            ),

        "P&L_Actual_Pct":
            0,

        "Estado_Estrategia":
            "TESIS_ESTABLE",

        "Ultima_Actualizacion":
            ahora().strftime(
                "%Y-%m-%d %H:%M"
            ),

        "Analisis_IA_Actual":
            comentario.replace(
                "\n",
                " "
            ),

        # ----------------------------------------------------
        # OPERATIVO
        # ----------------------------------------------------

        "Estado":
            "ACTIVA",

        "Fecha_Salida":
            "",

        "Resultado_R":
            "",

        "MAE_R":
            "",

        "MFE_R":
            ""
    }

    nueva_df = pd.DataFrame(
        [nueva_fila]
    )

    df = pd.concat(
        [
            df,
            nueva_df
        ],
        ignore_index=True
    )

    # --------------------------------------------------------
    # ASEGURAR TIPOS
    # --------------------------------------------------------

    for col in CAMPOS_TEXTO:

        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
        )

    for col in CAMPOS_NUMERICOS:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.reindex(
        columns=CAMPOS_HISTORIAL
    )

    df.to_csv(
        ARCHIVO_HISTORIAL,
        index=False
    )


# ============================================================
# BLOQUEADOS
# ============================================================

def bloqueados():

    df = cargar_historial()

    if df.empty:

        return set()

    bloqueados_set = set()

    hoy = ahora().date()

    for _, r in df.iterrows():

        estado = str(
            r.get(
                "Estado",
                ""
            )
        )

        if (
            "ACTIVA"
            in estado
        ):

            ticker = str(
                r.get(
                    "Ticker",
                    ""
                )
            ).strip()

            if ticker:

                bloqueados_set.add(
                    ticker
                )

            continue

        if (
            "STOP_SALTADO"
            in estado
        ):

            try:

                fecha_alerta = (
                    pd.to_datetime(
                        r["Fecha"]
                    ).date()
                )

                dias = (
                    hoy
                    -
                    fecha_alerta
                ).days

                if (
                    dias
                    <
                    CUARENTENA_STOP_DIAS
                ):

                    ticker = str(
                        r["Ticker"]
                    ).strip()

                    if ticker:

                        bloqueados_set.add(
                            ticker
                        )

            except Exception:

                continue

    return bloqueados_set


# ============================================================
# ACTUALIZAR ALERTAS ACTIVAS
# ============================================================

def actualizar_alertas_activas():

    df = cargar_historial()

    if df.empty:

        return

    indices = df.index[
        df["Estado"]
        .astype(str)
        == "ACTIVA"
    ]

    if len(indices) == 0:

        print(
            "ℹ️ No hay alertas ACTIVA "
            "para actualizar."
        )

        return

    print(
        f"\n🔄 Actualizando "
        f"{len(indices)} alerta(s) ACTIVA..."
    )

    changed = False

    for i in indices:

        ticker = str(
            df.at[
                i,
                "Ticker"
            ]
        ).strip()

        try:

            # ------------------------------------------------
            # DATOS ACTUALES
            # ------------------------------------------------

            datos = yf.download(

                ticker,

                period="1y",

                interval="1d",

                auto_adjust=True,

                progress=False,

                threads=False
            )

            if datos.empty:

                print(
                    f"⚠️ {ticker}: "
                    f"sin datos."
                )

                continue

            datos = norm(
                datos
            )

            datos = datos.dropna(
                subset=[
                    "Close",
                    "High",
                    "Low",
                    "Volume"
                ]
            )

            actual = obtener_estado_actual(
                ticker,
                datos
            )

            if actual is None:

                print(
                    f"⚠️ {ticker}: "
                    f"no se pudo calcular "
                    f"estado actual."
                )

                continue

            # ------------------------------------------------
            # TESIS ORIGINAL
            # ------------------------------------------------

            original = (
                construir_original_desde_fila(
                    df.loc[i]
                )
            )

            # ------------------------------------------------
            # EVOLUCIÓN
            # ------------------------------------------------

            evolucion = (
                evaluar_evolucion_estrategia(
                    original,
                    actual
                )
            )

            # ------------------------------------------------
            # ESTADO DE TESIS
            # ------------------------------------------------

            estado_tesis = (
                estado_estrategia(
                    original,
                    actual
                )
            )

            # ------------------------------------------------
            # DATOS OPERATIVOS
            # ------------------------------------------------

            entrada = float(
                df.at[
                    i,
                    "Precio_Alerta"
                ]
            )

            precio_actual = float(
                actual["precio"]
            )

            sl = float(
                df.at[
                    i,
                    "Stop_Loss"
                ]
            )

            tp = float(
                df.at[
                    i,
                    "Take_Profit"
                ]
            )

            # ------------------------------------------------
            # P&L
            # ------------------------------------------------

            pnl_pct = (

                (
                    precio_actual
                    /
                    entrada
                )
                - 1

            ) * 100

            # ------------------------------------------------
            # DISTANCIA SL
            # ------------------------------------------------

            distancia_sl = (

                (
                    precio_actual
                    -
                    sl
                )
                /
                precio_actual

            ) * 100

            # ------------------------------------------------
            # DISTANCIA TP
            # ------------------------------------------------

            distancia_tp = (

                (
                    tp
                    -
                    precio_actual
                )
                /
                precio_actual

            ) * 100

            # ------------------------------------------------
            # IA
            # ------------------------------------------------

            comentario = comentario_seguimiento(

                original,
                actual,
                df.loc[i],
                evolucion
            )

            timestamp = (
                ahora().strftime(
                    "%Y-%m-%d %H:%M"
                )
            )

            # =================================================
            # SOLO MODIFICAMOS ESTADO ACTUAL
            # =================================================

            df.at[
                i,
                "Precio_Actual"
            ] = precio_actual

            df.at[
                i,
                "Score_Actual"
            ] = actual["score"]

            df.at[
                i,
                "RVOL_Actual"
            ] = actual["rvol"]

            df.at[
                i,
                "RSI_Actual"
            ] = actual["rsi"]

            df.at[
                i,
                "ROC20_Actual"
            ] = actual["roc20"]

            df.at[
                i,
                "ATR_Actual"
            ] = actual["atr"]

            df.at[
                i,
                "EMA50_Actual"
            ] = actual["e50"]

            df.at[
                i,
                "EMA200_Actual"
            ] = actual["e200"]

            df.at[
                i,
                "Razones_Actuales"
            ] = actual["razones"]

            df.at[
                i,
                "Distancia_SL_Pct"
            ] = round(
                distancia_sl,
                2
            )

            df.at[
                i,
                "Distancia_TP_Pct"
            ] = round(
                distancia_tp,
                2
            )

            df.at[
                i,
                "P&L_Actual_Pct"
            ] = round(
                pnl_pct,
                2
            )

            df.at[
                i,
                "Estado_Estrategia"
            ] = estado_tesis

            df.at[
                i,
                "Ultima_Actualizacion"
            ] = timestamp

            df.at[
                i,
                "Analisis_IA_Actual"
            ] = comentario.replace(
                "\n",
                " "
            )

            changed = True

            icono = {

                "TESIS_REFORZADA":
                    "🟢",

                "TESIS_ESTABLE":
                    "🟡",

                "TESIS_DEBILITADA":
                    "🟠",

                "TESIS_INVALIDADA":
                    "🔴"

            }.get(
                estado_tesis,
                "⚪"
            )

            print(

                f"{icono} "

                f"{ticker} | "

                f"Entrada "
                f"{entrada:.2f} | "

                f"Actual "
                f"{precio_actual:.2f} | "

                f"P&L "
                f"{pnl_pct:+.2f}% | "

                f"Score "
                f"{original['score']:.0f}"
                f"→"
                f"{actual['score']} | "

                f"Tesis: "
                f"{estado_tesis}"
            )

        except Exception as e:

            print(
                f"⚠️ Error actualizando "
                f"{ticker}: {e}"
            )

    # ========================================================
    # GUARDAR
    # ========================================================

    if changed:

        # ----------------------------------------------------
        # MUY IMPORTANTE:
        # normalizamos tipos antes de guardar.
        # ----------------------------------------------------

        for col in CAMPOS_TEXTO:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
            )

        for col in CAMPOS_NUMERICOS:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df = df.reindex(
            columns=CAMPOS_HISTORIAL
        )

        df.to_csv(
            ARCHIVO_HISTORIAL,
            index=False
        )

        print(
            "✅ Seguimiento de alertas "
            "actualizado."
        )


# ============================================================
# AUDITORÍA SL / TP
# ============================================================

def auditar():

    df = cargar_historial()

    if df.empty:

        return

    changed = False

    hoy = ahora().date()

    for i, r in df.iterrows():

        if str(
            r.get(
                "Estado",
                ""
            )
        ) != "ACTIVA":

            continue

        try:

            fecha_alerta = (
                pd.to_datetime(
                    r["Fecha"]
                ).date()
            )

            inicio = (
                fecha_alerta
                +
                timedelta(days=1)
            )

            if inicio > hoy:

                continue

            ticker = str(
                r["Ticker"]
            )

            datos = yf.download(

                ticker,

                start=
                    inicio.isoformat(),

                end=
                    (
                        hoy
                        +
                        timedelta(days=1)
                    ).isoformat(),

                auto_adjust=True,

                progress=False,

                threads=False
            )

            if datos.empty:

                continue

            datos = norm(
                datos
            )

            sl = float(
                r["Stop_Loss"]
            )

            tp = float(
                r["Take_Profit"]
            )

            for fecha, vela in datos.iterrows():

                low = float(
                    vela.Low
                )

                high = float(
                    vela.High
                )

                # ------------------------------------------------
                # CRITERIO CONSERVADOR:
                #
                # Si una vela toca SL y TP simultáneamente,
                # asumimos primero STOP.
                # ------------------------------------------------

                if low <= sl:

                    estado = (
                        "STOP_SALTADO 🔴"
                    )

                    resultado = -1.0

                elif high >= tp:

                    estado = (
                        "OBJETIVO_CUMPLIDO 🟢"
                    )

                    resultado = RR_TARGET

                else:

                    continue

                df.at[
                    i,
                    "Estado"
                ] = estado

                df.at[
                    i,
                    "Fecha_Salida"
                ] = pd.Timestamp(
                    fecha
                ).strftime(
                    "%Y-%m-%d"
                )

                df.at[
                    i,
                    "Resultado_R"
                ] = resultado

                changed = True

                print(

                    f"{'🔴' if resultado < 0 else '🟢'} "

                    f"{ticker} -> "

                    f"{estado} | "

                    f"{pd.Timestamp(fecha):%Y-%m-%d}"
                )

                break

        except Exception as e:

            print(
                f"⚠️ Error auditando "
                f"{r.get('Ticker', '')}: {e}"
            )

            continue

    if changed:

        for col in CAMPOS_TEXTO:

            df[col] = (
                df[col]
                .fillna("")
                .astype(str)
            )

        for col in CAMPOS_NUMERICOS:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            )

        df.to_csv(
            ARCHIVO_HISTORIAL,
            index=False
        )

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    cerradas = df[
        df["Estado"]
        .astype(str)
        .str.contains(
            "OBJETIVO|STOP",
            regex=True,
            na=False
        )
    ]

    if len(cerradas):

        resultados = pd.to_numeric(
            cerradas["Resultado_R"],
            errors="coerce"
        )

        expectancy = (
            resultados
            .dropna()
            .mean()
        )

        if pd.notna(
            expectancy
        ):

            print(
                f"📊 Cerradas "
                f"{len(cerradas)} | "
                f"Expectancy "
                f"{expectancy:.2f} R"
            )


# ============================================================
# GIT
# ============================================================

def git():

    try:

        subprocess.run(
            [
                "git",
                "add",
                "."
            ],
            check=True
        )

        status = subprocess.run(

            [
                "git",
                "status",
                "--porcelain"
            ],

            capture_output=True,

            text=True
        )

        if status.stdout.strip():

            subprocess.run(

                [
                    "git",
                    "commit",
                    "-m",
                    "Alura Quant V4.1 "
                    "seguimiento inteligente"
                ],

                check=True
            )

            subprocess.run(

                [
                    "git",
                    "push",
                    "origin",
                    "main"
                ],

                check=True
            )

    except Exception as e:

        print(
            f"ℹ️ Git: {e}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    modo = modo_actual()

    print(
        "\n"
        "============================================================\n"
        "ALURA QUANT V4.1\n"
        "============================================================"
    )

    print(
        f"Fecha: "
        f"{ahora():%Y-%m-%d %H:%M}"
    )

    print(
        f"Modo: "
        f"{modo}"
    )

    print(
        f"Activos universo: "
        f"{len(activos)}"
    )

    # ========================================================
    # 1. PREPARAR HISTORIAL
    # ========================================================

    print(
        "\n📁 1. PREPARANDO HISTORIAL"
    )

    preparar_historial()

    # ========================================================
    # 2. AUDITORÍA
    #
    # Primero determinamos si alguna activa ya terminó.
    # ========================================================

    print(
        "\n🔎 2. AUDITORÍA SL / TP"
    )

    auditar()

    # ========================================================
    # 3. SEGUIMIENTO DE ACTIVAS
    #
    # Solo siguen aquí las que continúan ACTIVA.
    # ========================================================

    print(
        "\n🧠 3. SEGUIMIENTO DE TESIS ACTIVAS"
    )

    actualizar_alertas_activas()

    # ========================================================
    # 4. BLOQUEADOS
    # ========================================================

    blocked = bloqueados()

    print(
        f"\n🔒 Tickers bloqueados: "
        f"{len(blocked)}"
    )

    # ========================================================
    # 5. NUEVAS OPORTUNIDADES
    # ========================================================

    activos_a_analizar = [

        t

        for t in activos

        if t not in blocked
    ]

    print(
        f"🔍 Tickers a analizar: "
        f"{len(activos_a_analizar)}"
    )

    nuevas_alertas = []

    # ========================================================
    # 6. DESCARGA POR LOTES
    # ========================================================

    for inicio in range(

        0,

        len(activos_a_analizar),

        TAMANO_LOTE
    ):

        lote = activos_a_analizar[
            inicio:
            inicio + TAMANO_LOTE
        ]

        print(

            f"\n📥 Lote "
            f"{inicio // TAMANO_LOTE + 1} "
            f"| "
            f"{len(lote)} activos"
        )

        try:

            datos_lote = yf.download(

                lote,

                period="1y",

                interval="1d",

                auto_adjust=True,

                group_by="ticker",

                progress=False,

                threads=True
            )

            for ticker in lote:

                try:

                    if len(lote) == 1:

                        datos = norm(
                            datos_lote
                        )

                    else:

                        try:

                            datos = (
                                datos_lote[
                                    ticker
                                ]
                            )

                            datos = norm(
                                datos
                            )

                        except Exception:

                            continue

                    datos = datos.dropna(

                        subset=[

                            "Close",
                            "High",
                            "Low",
                            "Volume"
                        ]
                    )

                    resultado = (
                        procesar_dataframe_activo(
                            ticker,
                            datos
                        )
                    )

                    if resultado:

                        nuevas_alertas.append(
                            resultado
                        )

                except Exception as e:

                    print(
                        f"⚠️ Error "
                        f"{ticker}: {e}"
                    )

        except Exception as e:

            print(
                f"⚠️ Error descargando "
                f"lote: {e}"
            )

    # ========================================================
    # 7. ORDENAR
    # ========================================================

    nuevas_alertas.sort(

        key=lambda x: (

            x["score"],
            x["rvol"]
        ),

        reverse=True
    )

    print(
        f"\n📊 Nuevas señales: "
        f"{len(nuevas_alertas)}"
    )

    # ========================================================
    # 8. GUARDAR NUEVAS ALERTAS
    # ========================================================

    for c in nuevas_alertas:

        comentario = (
            comentario_entrada(c)
        )

        guardar(
            c,
            comentario
        )

        print(
            "\n"
            f"{c['icono']} "
            f"{c['empresa']} "
            f"({c['ticker']})"
        )

        print(
            f"Score: "
            f"{c['score']}"
        )

        print(
            f"Entrada: "
            f"{c['precio']:.2f}€"
        )

        print(
            f"SL: "
            f"{c['stop']:.2f}€"
        )

        print(
            f"TP: "
            f"{c['tp']:.2f}€"
        )

        print(
            f"Acciones: "
            f"{c['acciones']}"
        )

        print(
            f"Riesgo: "
            f"{c['riesgo']:.2f}€"
        )

        print(
            f"IA: "
            f"{comentario}"
        )

    # ========================================================
    # 9. GIT
    # ========================================================

    print(
        "\n💾 Guardando cambios..."
    )

    git()

    print(
        "\n============================================================"
    )

    print(
        "✅ ALURA QUANT FINALIZADO"
    )

    print(
        "============================================================"
    )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    main()