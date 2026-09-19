# ALURA QUANT V3 (Sin IBEX y con Umbrales Flexibles)
import csv, os, subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
from openai import OpenAI

TZ=ZoneInfo("Europe/Madrid")
MODO_EJECUCION="AUTO"  # AUTO | 14 | 18
ARCHIVO_HISTORIAL="historial_alertas.csv"
ARCHIVO_UNIVERSO="universo_activos.csv"
CAPITAL=100000.0
RIESGO_POR_OPERACION=0.005
ATR_MULTIPLICADOR=1.75
RR_TARGET=2.5
UMBRAL_SCORE_18=55   # Reducido para más flexibilidad
UMBRAL_SCORE_14=50   # Reducido para más flexibilidad
LIQUIDEZ_MIN_EUR=500000
CUARENTENA_STOP_DIAS=15
client=OpenAI(base_url="http://localhost:11434/v1",api_key="ollama")
MODELO_LOCAL="llama3.2"

MAESTRO_ACTIVOS_BASE = {
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


def cargar_universo():
    universo=dict(MAESTRO_ACTIVOS_BASE)
    if os.path.exists(ARCHIVO_UNIVERSO):
        try:
            df=pd.read_csv(ARCHIVO_UNIVERSO)
            for _,r in df.iterrows():
                t=str(r.get("Ticker","")).strip()
                if t: universo[t]=(str(r.get("Empresa",t)),str(r.get("Sector","General")),str(r.get("Icono","📈")))
        except Exception as e: print(f"⚠️ Error cargando universo: {e}")
    return universo

MAESTRO_ACTIVOS=cargar_universo(); activos=list(MAESTRO_ACTIVOS)

def ahora(): return datetime.now(TZ)
def modo_actual(): return MODO_EJECUCION if MODO_EJECUCION in ("14","18") else ("14" if ahora().hour<16 else "18")
def norm(df):
    if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
    return df
def diario(t,period="1y"):
    try: return norm(yf.download(t,period=period,interval="1d",auto_adjust=True,progress=False,threads=False)).dropna(subset=["Close","High","Low","Volume"])
    except Exception: return pd.DataFrame()
def intra(t):
    try: return norm(yf.download(t,period="5d",interval="15m",auto_adjust=True,progress=False,threads=False)).dropna(subset=["Close","High","Low","Volume"])
    except Exception: return pd.DataFrame()
def datos(t,modo):
    d=diario(t)
    if d.empty or modo!="14": return d
    x=intra(t)
    if x.empty: return d
    idx=pd.to_datetime(x.index); idx=idx.tz_convert(TZ).tz_localize(None) if getattr(idx,"tz",None) is not None else idx
    x.index=idx; hoy=ahora().date(); x=x[x.index.date==hoy]
    if x.empty:return d
    p=pd.DataFrame({"Open":[float(x.Open.iloc[0])],"High":[float(x.High.max())],"Low":[float(x.Low.min())],"Close":[float(x.Close.iloc[-1])],"Volume":[float(x.Volume.sum())]},index=[pd.Timestamp(hoy)])
    d=norm(d.copy()); d.index=pd.to_datetime(d.index).tz_localize(None); d=d[d.index.date!=hoy]
    inicio=ahora().replace(hour=9,minute=0,second=0,microsecond=0); mins=max(30,min(510,int((ahora()-inicio).total_seconds()/60))); p.loc[p.index[0],"Volume"]*=510/mins
    return pd.concat([d,p]).sort_index()
def rsi(s,n=14):
    z=s.diff(); g=z.clip(lower=0); l=-z.clip(upper=0); ag=g.ewm(alpha=1/n,adjust=False,min_periods=n).mean(); al=l.ewm(alpha=1/n,adjust=False,min_periods=n).mean(); rs=ag/al.replace(0,pd.NA); return 100-100/(1+rs)
def atr(d,n=14):
    p=d.Close.shift(); tr=pd.concat([d.High-d.Low,(d.High-p).abs(),(d.Low-p).abs()],axis=1).max(axis=1); return tr.ewm(alpha=1/n,adjust=False,min_periods=n).mean()

def bloqueados():
    if not os.path.exists(ARCHIVO_HISTORIAL):return set()
    out=set(); hoy=ahora().date()
    try:
        for r in csv.DictReader(open(ARCHIVO_HISTORIAL,encoding="utf-8")):
            try:f=datetime.strptime(r.get("Fecha","").split()[0],"%Y-%m-%d").date()
            except:continue
            if "ACTIVA" in r.get("Estado","") or ("STOP_SALTADO" in r.get("Estado","") and (hoy-f).days<CUARENTENA_STOP_DIAS):out.add(r.get("Ticker"))
    except:pass
    return out

def analizar(t,modo):
    d=datos(t,modo)
    if len(d)<220:return None
    d=d.copy(); d["E20"]=d.Close.ewm(span=20,adjust=False).mean(); d["E50"]=d.Close.ewm(span=50,adjust=False).mean(); d["E200"]=d.Close.ewm(span=200,adjust=False).mean(); d["RSI"]=rsi(d.Close); d["ATR"]=atr(d); d["VM20"]=d.Volume.rolling(20).mean(); d["TO20"]=(d.Close*d.Volume).rolling(20).mean(); d["ROC20"]=d.Close.pct_change(20)*100; d["H20"]=d.High.rolling(20).max().shift(1); d["CLV"]=((d.Close-d.Low)/(d.High-d.Low).replace(0,pd.NA)).fillna(0)
    x=d.iloc[-1]; req=["Close","E50","E200","RSI","ATR","VM20","TO20","ROC20","H20"]
    if any(pd.isna(x[k]) for k in req):return None
    price=float(x.Close); e50=float(x.E50); e200=float(x.E200); R=float(x.RSI); A=float(x.ATR); rv=float(x.Volume/x.VM20); to=float(x.TO20); roc=float(x.ROC20); br=price>float(x.H20); clv=float(x.CLV)
    if to<LIQUIDEZ_MIN_EUR:return None
    
    score=0; why=[]
    # Eliminados los criterios del IBEX y ajustados factores técnicos puros
    tests=[
        (price>e50, 15, "Precio > EMA50"),
        (e50>e200, 20, "EMA50 > EMA200"),
        (55<=R<=75, 15, "RSI 55-75"),
        (roc>5, 10, "ROC20 > 5%"),
        (rv>=1.5, 15, "RVOL >= 1.5x"),
        (rv>=1.2 and rv<1.5, 8, "RVOL >= 1.2x"),
        (clv>=.70, 5, "Cierre cerca de máximos"),
        (br, 15, "Ruptura máximo 20 sesiones")
    ]
    
    for ok,pts,txt in tests:
        if ok:score+=pts;why.append(txt)
        
    if score<(UMBRAL_SCORE_14 if modo=="14" else UMBRAL_SCORE_18) or rv<1.2 or not(price>e50 and e50>e200):return None
    
    support=float(d.Low.iloc[-16:-1].min()); resistance=float(d.High.iloc[-61:-1].max()); stop=min(price-ATR_MULTIPLICADOR*A,support*.99); risk=price-stop
    if risk<=0 or risk>price*.20:return None
    shares=int((CAPITAL*RIESGO_POR_OPERACION)/risk)
    if shares<1:return None
    
    return {
        "ticker":t,
        "empresa":MAESTRO_ACTIVOS[t][0],
        "sector":MAESTRO_ACTIVOS[t][1],
        "icono":MAESTRO_ACTIVOS[t][2],
        "modo":modo,
        "precio":round(price,2),
        "stop":round(stop,2),
        "tp":round(price+RR_TARGET*risk,2),
        "acciones":shares,
        "nominal":round(shares*price,2),
        "riesgo":round(shares*risk,2),
        "score":score,
        "rvol":round(rv,2),
        "rsi":round(R,2),
        "roc20":round(roc,2),
        "atr":round(A,2),
        "regimen":"N/A",
        "razones":"; ".join(why),
        "soporte":round(support,2),
        "resistencia":round(resistance,2)
    }

def comentario(c):
    try:
        q=f"{c['empresa']} ({c['ticker']}): precio {c['precio']}€, SL {c['stop']}€, TP {c['tp']}€, score {c['score']}/100, RVOL {c['rvol']}x, RSI {c['rsi']}, ROC20 {c['roc20']}%. Razones: {c['razones']}. Redacta 2 frases técnicas en español. No modifiques niveles y no prometas rentabilidad."
        r=client.chat.completions.create(model=MODELO_LOCAL,messages=[{"role":"system","content":"La IA solo explica una señal cuantitativa; no modifica la señal."},{"role":"user","content":q}],temperature=.4); return r.choices[0].message.content.strip()
    except:return f"Señal cuantitativa score {c['score']}/100, RVOL {c['rvol']}x y R/R 1:{RR_TARGET}. No garantiza rentabilidad."

def guardar(c,txt):
    fields=["Fecha","Ticker","Empresa","Sector","Icono","Modo","Precio_Alerta","Stop_Loss","Take_Profit","Ratio_RR","Riesgo_Euros","Acciones","Nominal","Score","RVOL","RSI","ROC20","ATR","Regimen","Razones","Analisis_IA","Estado","Fecha_Salida","Resultado_R","MAE_R","MFE_R"]; new=not os.path.exists(ARCHIVO_HISTORIAL)
    with open(ARCHIVO_HISTORIAL,"a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader() if new else None; w.writerow({"Fecha":ahora().strftime("%Y-%m-%d %H:%M"),"Ticker":c["ticker"],"Empresa":c["empresa"],"Sector":c["sector"],"Icono":c["icono"],"Modo":c["modo"],"Precio_Alerta":c["precio"],"Stop_Loss":c["stop"],"Take_Profit":c["tp"],"Ratio_RR":RR_TARGET,"Riesgo_Euros":c["riesgo"],"Acciones":c["acciones"],"Nominal":c["nominal"],"Score":c["score"],"RVOL":c["rvol"],"RSI":c["rsi"],"ROC20":c["roc20"],"ATR":c["atr"],"Regimen":c["regimen"],"Razones":c["razones"],"Analisis_IA":txt.replace("\n"," "),"Estado":"ACTIVA","Fecha_Salida":"","Resultado_R":"","MAE_R":"","MFE_R":""})

def auditar():
    if not os.path.exists(ARCHIVO_HISTORIAL):return
    try:df=pd.read_csv(ARCHIVO_HISTORIAL)
    except:return
    changed=False
    for i,r in df.iterrows():
        if str(r.get("Estado"))!="ACTIVA":continue
        try:
            f=pd.to_datetime(r.Fecha).date(); d=norm(yf.download(r.Ticker,start=(f+timedelta(days=1)).isoformat(),auto_adjust=True,progress=False,threads=False));
            if d.empty:continue
            sl,tp=float(r.Stop_Loss),float(r.Take_Profit)
            for idx,v in d.iterrows():
                lo,hi=float(v.Low),float(v.High)
                if lo<=sl: state,res="STOP_SALTADO 🔴",-1.0
                elif hi>=tp: state,res="OBJETIVO_CUMPLIDO 🟢",RR_TARGET
                else:continue
                df.at[i,"Estado"]=state; df.at[i,"Fecha_Salida"]=pd.Timestamp(idx).strftime("%Y-%m-%d"); df.at[i,"Resultado_R"]=res; changed=True; break
        except:continue
    if changed:df.to_csv(ARCHIVO_HISTORIAL,index=False)
    closed=df[df.Estado.astype(str).str.contains("OBJETIVO|STOP",regex=True,na=False)]
    if len(closed):print(f"📊 Cerradas {len(closed)} | Expectancy {pd.to_numeric(closed.Resultado_R,errors='coerce').mean():.2f} R")

def git():
    try:
        subprocess.run(["git","add","."],check=True); s=subprocess.run(["git","status","--porcelain"],capture_output=True,text=True)
        if s.stdout.strip():subprocess.run(["git","commit","-m","Alura Quant V3 sin IBEX y umbrales relajados"],check=True); subprocess.run(["git","push","origin","main"],check=True)
    except Exception as e:print(f"ℹ️ Git: {e}")

def main():
    modo=modo_actual(); print(f"ALURA QUANT V3 | {ahora():%Y-%m-%d %H:%M} Madrid | {modo} | {len(activos)} valores"); auditar(); blocked=bloqueados(); print(f"Bloqueados: {len(blocked)}")
    out=[]
    for n,t in enumerate(activos,1):
        if t in blocked:continue
        print(f"[{n}/{len(activos)}] {t}",end="\r")
        try:
            c=analizar(t,modo)
            if c:out.append(c)
        except Exception as e:print(f"\n⚠️ {t}: {e}")
    out.sort(key=lambda x:(x["score"],x["rvol"]),reverse=True); print(f"\nSeñales: {len(out)}")
    for c in out:
        txt=comentario(c); guardar(c,txt); print(f"\n{c['icono']} {c['empresa']} | Score {c['score']} | Entrada {c['precio']} | SL {c['stop']} | TP {c['tp']} | {c['acciones']} acciones\n{txt}")
    git()

if __name__=="__main__":main()