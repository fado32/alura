import csv
import os
import random
import subprocess
from datetime import datetime, timedelta
from openai import OpenAI
import pandas as pd
import yfinance as yf

# ==========================================
# CONFIGURACIÓN Y MAESTRO DE ACTIVOS
# ==========================================
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODELO_LOCAL = "llama3.2"
ARCHIVO_HISTORIAL = "historial_alertas.csv"
UMBRAL_VOLUMEN = 1.2

# Diccionario Maestro: Ticker -> (Nombre, Sector, Icono)
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


# ==========================================
# GESTIÓN DE HISTORIAL Y FILTROS DE MEMORIA
# ==========================================
def obtener_tickers_bloqueados():
    """Devuelve los tickers activos o en cuarentena para evitar duplicidades."""
    if not os.path.exists(ARCHIVO_HISTORIAL):
        return set()

    bloqueados = set()
    hoy = datetime.now()

    with open(ARCHIVO_HISTORIAL, mode="r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if len(reader) <= 1:
            return bloqueados

        for fila in reader[1:]:
            if len(fila) >= 2:
                fecha_alerta_str = fila[0]
                ticker = fila[1]
                estado = fila[-1] if len(fila) >= 8 else ""

                try:
                    fecha_alerta = datetime.strptime(
                        fecha_alerta_str.split()[0], "%Y-%m-%d"
                    )
                except ValueError:
                    continue

                if "ACTIVA" in estado:
                    bloqueados.add(ticker)
                elif "STOP_SALTADO" in estado:
                    if (hoy - fecha_alerta).days < 15:
                        bloqueados.add(ticker)

    return bloqueados


# ==========================================
# CÁLCULO MATEMÁTICO PURO (PYTHON)
# ==========================================
def calcular_soportes_resistencias(data):
    """Calcula matemáticamente soportes y resistencias usando mínimos y máximos locales."""
    ultimos_60 = data.tail(60)
    soporte_matematico = float(ultimos_60["Low"].min())
    resistencia_matematica = float(ultimos_60["High"].max())

    ultimos_15 = data.tail(15)
    soporte_corto = float(ultimos_15["Low"].min())

    return (
        round(soporte_matematico, 2),
        round(resistencia_matematica, 2),
        round(soporte_corto, 2),
    )


def analizar_activo(ticker_symbol):
    ticker_obj = yf.Ticker(ticker_symbol)
    data = ticker_obj.history(period="6mo", auto_adjust=True)

    if data.empty:
        return None

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns or "Volume" not in data.columns:
        return None

    info = ticker_obj.info
    per = info.get("trailingPE", None)
    cap_mercado = info.get("marketCap", 0)

    if per is not None and (per < 0 or per > 100):
        return None

    # Indicadores técnicos en Python
    data["EMA_50"] = data["Close"].ewm(span=50, adjust=False).mean()

    delta = data["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data["RSI"] = 100 - (100 / (1 + rs))

    data["Vol_Mean_20"] = data["Volume"].rolling(window=20).mean()

    ultimo_precio = float(data["Close"].iloc[-1])
    ultima_ema = float(data["EMA_50"].iloc[-1])
    ultimo_rsi = float(data["RSI"].iloc[-1])
    volumen_hoy = float(data["Volume"].iloc[-1])
    volumen_medio = float(data["Vol_Mean_20"].iloc[-1])

    ratio_volumen = volumen_hoy / volumen_medio if volumen_medio > 0 else 1.0
    distancia_ema = ((ultimo_precio - ultima_ema) / ultima_ema) * 100

    soporte_3m, resistencia_3m, soporte_reciente = (
        calcular_soportes_resistencias(data)
    )

    distancia_al_soporte = (
        (ultimo_precio - soporte_reciente) / soporte_reciente
    ) * 100
    cerca_de_soporte = 0 <= distancia_al_soporte <= 3.5

    tendencia_alcista = ultimo_precio > ultima_ema
    rsi_valido = 45 <= ultimo_rsi <= 75
    volumen_ok = ratio_volumen >= UMBRAL_VOLUMEN

    if volumen_ok and tendencia_alcista and rsi_valido:
        precio_entrada = round(ultimo_precio, 2)
        stop_loss = round(soporte_reciente * 0.98, 2)
        take_profit = round(precio_entrada * 1.10, 2)

        # Cálculo explícito del Ratio Riesgo / Beneficio (R/R)
        riesgo = precio_entrada - stop_loss
        beneficio = take_profit - precio_entrada
        ratio_rr = round(beneficio / riesgo, 2) if riesgo > 0 else 1.0

        # Obtener metadatos del maestro
        nombre, sector, icono = MAESTRO_ACTIVOS.get(
            ticker_symbol, (ticker_symbol, "General", "📈")
        )

        return {
            "ticker": ticker_symbol,
            "empresa": nombre,
            "sector": sector,
            "icono": icono,
            "precio": precio_entrada,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "ratio_rr": ratio_rr,
            "per": round(per, 2) if per else "N/D",
            "cap_mercado_millones": (
                round(cap_mercado / 1e6, 1) if cap_mercado else "N/D"
            ),
            "distancia_ema_pct": round(distancia_ema, 2),
            "rsi": round(ultimo_rsi, 2),
            "ratio_volumen": round(ratio_volumen, 1),
            "soporte": soporte_reciente,
            "resistencia": resistencia_3m,
            "cerca_soporte": cerca_de_soporte,
            "distancia_soporte_pct": round(distancia_al_soporte, 2),
        }

    return None


# ==========================================
# MOTOR DE COMENTARIOS DE IA DINÁMICOS Y VARIADOS
# ==========================================
def generar_comentario_ia_variado(candidato):
    """Genera análisis variados cambiando estilo, estructura y tono del prompt."""
    enfoques = [
        (
            "Análisis centrado en Volumen e Impulso",
            "Destaca el pico de volumen relativo frente a la media y cómo la presión compradora valida la entrada.",
        ),
        (
            "Análisis centrado en la Estructura de Soporte y Riesgo",
            "Concéntrate en la cercanía al soporte técnico, el nivel de Stop Loss y la protección del capital.",
        ),
        (
            "Análisis de Relación Riesgo/Beneficio (R/R)",
            "Enfócate en la asimetría favorable de la operación (Ratio R/R) y el objetivo de Take Profit.",
        ),
        (
            "Análisis Táctico de Ruptura y Tendencia",
            "Menciona la posición respecto a la EMA 50, el valor del RSI y el comportamiento sectorial.",
        ),
    ]

    enfoque_nombre, enfoque_instruccion = random.choice(enfoques)

    prompt_sistema = (
        f"Eres un analista cuantitativo de mercados en Alura Quant. Tu objetivo es hacer comentarios breves, "
        f"directos y variados. Hoy debes redactar el comentario usando este estilo específico: {enfoque_nombre}.\n"
        f"Instrucción de estilo: {enfoque_instruccion}\n\n"
        f"Reglas estrictas:\n"
        f"- Escribe en un único párrafo conciso (máximo 3 frases).\n"
        f"- No uses siempre la misma estructura formal o saludos prefabricados.\n"
        f"- Incluye números concretos (volumen, entradas o ratios) en tu argumento."
    )

    prompt_datos = (
        f"Activo: {candidato['empresa']} ({candidato['ticker']}) | Sector: {candidato['sector']}\n"
        f"Precio Entrada: {candidato['precio']} € | Stop Loss: {candidato['stop_loss']} € | Take Profit: {candidato['take_profit']} €\n"
        f"Ratio R/R: {candidato['ratio_rr']} | Ratio Volumen: {candidato['ratio_volumen']}x | RSI: {candidato['rsi']}\n"
        f"Soporte Reciente: {candidato['soporte']} € | Resistencia 3M: {candidato['resistencia']} €"
    )

    try:
        response = client.chat.completions.create(
            model=MODELO_LOCAL,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_datos},
            ],
            temperature=0.75,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Señal alcista con ratio R/R de 1:{candidato['ratio_rr']} y repunte de volumen x{candidato['ratio_volumen']}."


# ==========================================
# GUARDADO DE DATOS (CON FORMATO DE FECHA DIARIO)
# ==========================================
def guardar_en_csv(candidato, comentario_ia):
    archivo_existe = os.path.exists(ARCHIVO_HISTORIAL)
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    cabeceras = [
        "Fecha",
        "Ticker",
        "Empresa",
        "Sector",
        "Icono",
        "Precio_Alerta",
        "Stop_Loss",
        "Take_Profit",
        "Ratio_RR",
        "Ratio_Volumen",
        "Analisis_IA",
        "Estado",
    ]

    with open(ARCHIVO_HISTORIAL, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not archivo_existe:
            writer.writerow(cabeceras)

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
                candidato["ratio_volumen"],
                comentario_ia.replace("\n", " "),
                "ACTIVA",
            ]
        )


# ==========================================
# AUDITORÍA Y ESTADÍSTICAS
# ==========================================
def auditar_y_mostrar_estadisticas():
    if not os.path.exists(ARCHIVO_HISTORIAL):
        print("ℹ️ No hay historial de alertas previo todavía.\n")
        return

    filas_actualizadas = []
    with open(ARCHIVO_HISTORIAL, mode="r", encoding="utf-8") as f:
        reader = list(csv.reader(f))
        if len(reader) <= 1:
            return
        cabecera = reader[0]
        filas = reader[1:]

    cambios_realizados = False
    for fila in filas:
        if len(fila) < 8:
            filas_actualizadas.append(fila)
            continue

        fecha_alerta = fila[0]
        ticker = fila[1]
        estado = fila[-1]

        idx_precio = 5 if len(fila) >= 12 else 2
        idx_sl = 6 if len(fila) >= 12 else 3
        idx_tp = 7 if len(fila) >= 12 else 4

        precio_alerta = float(fila[idx_precio]) if fila[idx_precio] else 0.0
        stop_val = (
            float(fila[idx_sl])
            if fila[idx_sl]
            else round(precio_alerta * 0.96, 2)
        )
        tp_val = (
            float(fila[idx_tp])
            if fila[idx_tp]
            else round(precio_alerta * 1.10, 2)
        )

        if "ACTIVA" in estado:
            data = yf.download(
                ticker,
                start=fecha_alerta.split()[0],
                progress=False,
                auto_adjust=True,
            )
            if not data.empty and len(data) > 1:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                max_posterior = float(data["High"].max())
                min_posterior = float(data["Low"].min())

                if max_posterior >= tp_val:
                    fila[-1] = "OBJETIVO_CUMPLIDO 🟢"
                    cambios_realizados = True
                elif min_posterior <= stop_val:
                    fila[-1] = "STOP_SALTADO 🔴"
                    cambios_realizados = True

        filas_actualizadas.append(fila)

    if cambios_realizados:
        with open(
            ARCHIVO_HISTORIAL, mode="w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(cabecera)
            writer.writerows(filas_actualizadas)

    total = len(filas_actualizadas)
    exitos = sum(
        1 for f in filas_actualizadas if "OBJETIVO_CUMPLIDO" in f[-1]
    )
    fallos = sum(1 for f in filas_actualizadas if "STOP_SALTADO" in f[-1])
    activas = sum(1 for f in filas_actualizadas if "ACTIVA" in f[-1])

    tasa_acierto = (
        (exitos / (exitos + fallos) * 100) if (exitos + fallos) > 0 else 0
    )

    print("=" * 50)
    print("📊 ESTADÍSTICAS DEL HISTORIAL DE ALERTAS")
    print("=" * 50)
    print(f"• Total Alertas Registradas: {total}")
    print(f"• Objetivos Cumplidos (🟢): {exitos}")
    print(f"• Stops Saltados (🔴): {fallos}")
    print(f"• Aún Activas (⏳): {activas}")
    if (exitos + fallos) > 0:
        print(f"• Tasa de Acierto Histórica: {tasa_acierto:.1f}%")
    print("=" * 50 + "\n")


# ==========================================
# SUBIDA AUTOMÁTICA A GITHUB Y STREAMLIT
# ==========================================
def subir_a_github():
    try:
        # 1. Añadimos todos los archivos modificados en la carpeta (app.py, bot.py, CSV, etc.)
        subprocess.run(["git", "add", "."], check=True)

        # 2. Comprobamos si existen cambios pendientes de commit
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True
        )

        if status.stdout.strip():
            # Hay cambios pendientes: realizamos commit y push
            subprocess.run(
                ["git", "commit", "-m", "Auto-update alertas y codigo desde local"],
                check=True,
            )
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("🚀 ¡Cambios y datos subidos con éxito a GitHub y Streamlit Cloud!")
        else:
            print("💤 Sin cambios nuevos. Todo al día.")

    except Exception as e:
        print(f"ℹ️ Nota de Git: {e}")


# ==========================================
# EJECUCIÓN PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print(
        f" ESCANEANDO UNIVERSO CON METADATOS Y NIVELES EXACTOS ({len(activos)} VALORES)"
    )
    print("=" * 50 + "\n")

    auditar_y_mostrar_estadisticas()

    tickers_bloqueados = obtener_tickers_bloqueados()
    if tickers_bloqueados:
        print(
            f"🔒 Tickers excluidos por estar activos o en cuarentena: {list(tickers_bloqueados)}\n"
        )

    candidatos_detectados = []
    for idx, ticker in enumerate(activos, 1):
        if ticker in tickers_bloqueados:
            continue
        print(f"[{idx}/{len(activos)}] Analizando {ticker}...", end="\r")
        resultado = analizar_activo(ticker)
        if resultado:
            candidatos_detectados.append(resultado)

    print("\n" + "=" * 50)
    print(
        f" Escaneo completado. Candidatos válidos: {len(candidatos_detectados)}"
    )

    if candidatos_detectados:
        candidatos_detectados = sorted(
            candidatos_detectados,
            key=lambda x: x["ratio_volumen"],
            reverse=True,
        )

        print(
            "\n Generando comentarios variados con motor LLM dinámico...\n"
        )
        print("=" * 50)

        for candidato in candidatos_detectados:
            comentario = generar_comentario_ia_variado(candidato)
            guardar_en_csv(candidato, comentario)

            print(
                f"\n{candidato['icono']} {candidato['empresa']} ({candidato['ticker']}) - {candidato['sector']}"
            )
            print(
                f"    Entrada: {candidato['precio']} € | SL: {candidato['stop_loss']} € | TP: {candidato['take_profit']} € | R/R: 1:{candidato['ratio_rr']}"
            )
            print(f"   🤖 Comentario IA: {comentario}")
            print("-" * 50)

        print("\n💾 Nuevas alertas guardadas exitosamente en el historial.")
    else:
        print(
            "💤 Ningún valor nuevo disponible (o todos los candidatos están en seguimiento)."
        )

    # SUBIDA AUTOMÁTICA TRAS AUDITAR Y GUARDAR
    subir_a_github()