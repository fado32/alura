import pandas as pd
import streamlit as st
import yfinance as yf

# Configuración de página
st.set_page_config(
    page_title="Alura Quant - Dashboard", page_icon="📈", layout="wide"
)

# ==========================================
# CSS PERSONALIZADO (AUMENTAR TAMAÑO MENÚ)
# ==========================================
st.markdown(
    """
    <style>
    /* Aumentar tamaño de letra de la barra lateral (radio buttons / navegación) */
    div[data-testid="stSidebar"] label {
        font-size: 20px !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSidebar"] div[role="radiogroup"] label span {
        font-size: 18px !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

ARCHIVO_HISTORIAL = "historial_alertas.csv"


@st.cache_data(ttl=300)
def cargar_datos():
    try:
        df = pd.read_csv(ARCHIVO_HISTORIAL)
        return df
    except Exception:
        return pd.DataFrame()


def obtener_precio_actual(ticker):
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
    except Exception:
        pass
    return None


df = cargar_datos()

# ==========================================
# BARRA LATERAL (NAVEGACIÓN)
# ==========================================
st.sidebar.title("Alura Quant 📈")
opcion = st.sidebar.radio(
    "Navegación", ["Resumen", "Cartera Activa", "Histórico"]
)

if not df.empty:
    # Filtros por estado
    activas = df[df["Estado"].str.contains("ACTIVA", na=False)]
    cumplidas = df[df["Estado"].str.contains("OBJETIVO_CUMPLIDO", na=False)]
    falladas = df[df["Estado"].str.contains("STOP_SALTADO", na=False)]

    totales_cerradas = len(cumplidas) + len(falladas)
    win_rate = (
        (len(cumplidas) / totales_cerradas * 100) if totales_cerradas > 0 else 0
    )

    # ==========================================
    # PESTAÑA: RESUMEN
    # ==========================================
    if opcion == "Resumen":
        st.header("📊 Métricas Generales")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Alertas Totales", len(df))
        col2.metric("Posiciones Activas ⏳", len(activas))
        col3.metric("Objetivos Cumplidos 🟢", len(cumplidas))
        col4.metric(f"Tasa de Acierto", f"{win_rate:.1f}%")

        st.subheader("🚀 Últimas Alertas Registradas")
        st.dataframe(df.tail(5), use_container_width=True)

    # ==========================================
    # PESTAÑA: CARTERA ACTIVA (CON PRECIO ACTUAL)
    # ==========================================
    elif opcion == "Cartera Activa":
        st.header("💼 Posiciones Activas en Cartera")

        if not activas.empty:
            datos_cartera = []
            for _, row in activas.iterrows():
                precio_entrada = float(row["Precio_Alerta"])
                precio_actual = obtener_precio_actual(row["Ticker"])

                if precio_actual:
                    rendimiento_pct = (
                        (precio_actual - precio_entrada) / precio_entrada
                    ) * 100
                else:
                    precio_actual = precio_entrada
                    rendimiento_pct = 0.0

                datos_cartera.append(
                    {
                        "Icono": row.get("Icono", "📈"),
                        "Empresa": row["Empresa"],
                        "Ticker": row["Ticker"],
                        "Fecha Entrada": row["Fecha"],
                        "Precio Entrada (€)": f"{precio_entrada:.2f}",
                        "Precio Actual (€)": f"{precio_actual:.2f}",
                        "Variación (%)": f"{rendimiento_pct:+.2f}%",
                        "Stop Loss (€)": row["Stop_Loss"],
                        "Take Profit (€)": row["Take_Profit"],
                        "Ratio R/R": row["Ratio_RR"],
                    }
                )

            df_cartera = pd.DataFrame(datos_cartera)
            st.dataframe(df_cartera, use_container_width=True)
        else:
            st.info("No hay posiciones activas en este momento.")

    # ==========================================
    # PESTAÑA: HISTÓRICO
    # ==========================================
    elif opcion == "Histórico":
        st.header("📜 Histórico Completo de Operaciones")
        st.dataframe(df, use_container_width=True)

else:
    st.warning(
        "Aún no hay datos cargados en el historial. Ejecuta `bot.py` para generar las primeras alertas."
    )