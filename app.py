import streamlit as st
import pandas as pd
import numpy as np

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Gestión de Cartera y Trading",
    page_icon="📈",
    layout="wide"
)

# =========================================================
# ESTILOS CSS PERSONALIZADOS
# =========================================================
st.markdown("""
<style>
    /* Estilos generales y variables de color */
    :root {
        --surface-soft: #1e293b;
        --border-soft: #334155;
        --text: #f8fafc;
        --text-secondary: #94a3b8;
    }

    /* Contenedor principal de la tarjeta de posición */
    .position-wrapper {
        background: var(--surface-soft);
        border: 1px solid var(--border-soft);
        border-radius: 16px;
        padding: 16px;
        margin-bottom: 16px;
    }

    /* Etiquetas superiores */
    .position-labels {
        display: flex;
        justify-content: space-between;
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 6px;
    }

    /* Barra gráfica de progreso/rango */
    .position-track {
        position: relative;
        height: 8px;
        background: #0f172a;
        border-radius: 4px;
        margin-bottom: 14px;
        overflow: hidden;
    }

    .position-risk {
        position: absolute;
        height: 100%;
        background: rgba(239, 68, 68, 0.3);
    }

    .position-reward {
        position: absolute;
        height: 100%;
        background: rgba(34, 197, 94, 0.3);
    }

    /* Marcadores en la barra */
    .position-marker {
        position: absolute;
        top: 0;
        width: 3px;
        height: 100%;
        z-index: 2;
    }
    .marker-sl { background: #ef4444; }
    .marker-entry { background: #38bdf8; }
    .marker-current { background: #facc15; width: 4px; }
    .marker-tp { background: #22c55e; }

    /* =========================================================
       POSITION TRACKER VALUES (MODIFICADO)
       ========================================================= */
    .position-values {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        margin-top: 12px;
        background: rgba(15, 23, 42, 0.6);
        padding: 10px 14px;
        border-radius: 12px;
        border: 1px solid var(--border-soft);
    }

    .position-value {
        font-size: 10px;
        color: var(--text-secondary);
        text-align: center;
        flex: 1;
    }

    .position-value strong {
        display: block;
        color: var(--text);
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 11px;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def formatear_numero(valor, decimales=2):
    try:
        return f"{float(valor):,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(valor)

# =========================================================
# INTERFAZ PRINCIPAL (EJEMPLO DE CARTERA)
# =========================================================
st.title("📊 Seguimiento de Cartera")

st.markdown("### Posiciones Activas")

# Datos de ejemplo para renderizar la tarjeta optimizada
stop_loss = 95.0
precio_entrada = 100.0
precio_actual = 107.5
take_profit = 120.0

# Cálculo de porcentajes para la barra (ejemplo normalizado entre SL y TP)
min_val = min(stop_loss, precio_actual, precio_entrada, take_profit)
max_val = max(stop_loss, precio_actual, precio_entrada, take_profit)
rango = max_val - min_val if max_val != min_val else 1.0

def calc_pct(val):
    return max(0.0, min(100.0, ((val - min_val) / rango) * 100))

sl_pct = calc_pct(stop_loss)
entry_pct = calc_pct(precio_entrada)
current_pct = calc_pct(precio_actual)
tp_pct = calc_pct(take_profit)

risk_width = abs(entry_pct - sl_pct)
reward_width = abs(tp_pct - entry_pct)

# Renderizado del componente visual actualizado
position_tracker = f"""
<div class="position-wrapper">
    <div class="position-labels">
        <span class="position-label">Stop</span>
        <span class="position-label">Entrada</span>
        <span class="position-label">Actual</span>
        <span class="position-label">Take Profit</span>
    </div>

    <div class="position-track">
        <div class="position-risk" style="left:{min(sl_pct, entry_pct):.2f}%; width:{risk_width:.2f}%;"></div>
        <div class="position-reward" style="left:{min(entry_pct, tp_pct):.2f}%; width:{reward_width:.2f}%;"></div>

        <div class="position-marker marker-sl" style="left:{sl_pct:.2f}%;"></div>
        <div class="position-marker marker-entry" style="left:{entry_pct:.2f}%;"></div>
        <div class="position-marker marker-current" style="left:{current_pct:.2f}%;"></div>
        <div class="position-marker marker-tp" style="left:{tp_pct:.2f}%;"></div>
    </div>

    <div class="position-values">
        <div class="position-value">
            Stop Loss
            <strong>{formatear_numero(stop_loss, 2)}</strong>
        </div>
        <div class="position-value">
            Entrada
            <strong>{formatear_numero(precio_entrada, 2)}</strong>
        </div>
        <div class="position-value">
            Actual
            <strong>{formatear_numero(precio_actual, 2)}</strong>
        </div>
        <div class="position-value">
            Take Profit
            <strong>{formatear_numero(take_profit, 2)}</strong>
        </div>
    </div>
</div>
"""

st.markdown(position_tracker, unsafe_allow_html=True)