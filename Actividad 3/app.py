#Creamos el archivo de la APP (Dashboard GAC Motor - Etapa I: Extracción de Características)
#####################################################
#Importamos librerias
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
import os
import re
import io
import math
import numpy as np
import base64
from PIL import Image
######################################################
#Configuración de la página (pantalla ancha)
st.set_page_config(page_title="GAC Motor | Dashboard", layout="wide")

#PALETA (teoría del color): el rojo GAC es el ACENTO y solo marca lo que pide atención;
#los neutros (carbón y grises) son el contexto. Así el ojo va directo a lo importante.
ROJO = "#C8102E"        #Acento: lo más importante / alerta
ROJO_OSCURO = "#8E0B20" #Extremo de la escala de intensidad
CARBON = "#2F3640"      #Serie principal neutra (texto blanco encima se lee bien)
GRIS = "#9AA1AB"        #Contexto: lo que no necesita atención
GRIS_CLARO = "#D5D9DE"  #Contexto muy suave (siempre con etiqueta oscura)
VERDE = "#2E7D4F"       #Estado: cumple / bien (siempre con texto, nunca color solo)
TINTA = "#1F2328"       #Texto principal
TINTA_2 = "#5B6370"     #Texto secundario
FONDO_APP = "#F4F5F7"   #Fondo de la página
SUPERFICIE = "#FFFFFF"  #Tarjetas y gráficas
BORDE = "#E3E6EA"       #Bordes suaves

#Escala de intensidad (un solo tono, de claro a oscuro) para treemap y mapa de calor
ESCALA_ROJA = ["#FCE8EB", "#F4B3BD", "#E2647A", ROJO, ROJO_OSCURO]
#Colores con significado propio para los niveles de asesor
METALES = {"Oro": "#B8901F", "Plata": GRIS, "Bronce": "#A0582C"}

LOGO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_gac.png")
FONDO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto fondo.jpeg")
DISCO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "disco_freno.png")
CARBONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fibra_carbono.png")
BRILLO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brillo_dona.png")
FUENTE = "Inter, 'Segoe UI', system-ui, -apple-system, sans-serif"

pio.templates["gac"] = go.layout.Template(layout=dict(
    font=dict(family=FUENTE, color=TINTA, size=13),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=[ROJO, CARBON, GRIS],
    xaxis=dict(gridcolor="#EDEFF2", linecolor=BORDE, zeroline=False,
               tickfont=dict(color=TINTA_2), title_font=dict(color=TINTA_2)),
    yaxis=dict(gridcolor="#EDEFF2", linecolor=BORDE, zeroline=False,
               tickfont=dict(color=TINTA_2), title_font=dict(color=TINTA_2)),
    legend=dict(font=dict(color=TINTA_2)),
    barcornerradius=4,
    hoverlabel=dict(bgcolor=SUPERFICIE, font=dict(color=TINTA, family=FUENTE), bordercolor=BORDE)))
pio.templates.default = "plotly_white+gac"

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

#Etapas del embudo en orden (de la primera a la última)
#Leads generados/efectivos NO se usan: vienen rellenados con la media (83.06 se repite)
ETAPAS = ["Cita programada", "Cita efectiva", "Prueba de manejo",
          "Solicitud de crédito generada", "Solicitud de crédito aprobada",
          "Ventas", "Formalizado"]

#Lista de las 15 variables: nombre en el dashboard -> (base, columna, tipo, medida)
#Medida = columna que se SUMA por categoría. Si es None, se cuentan registros.
VARIABLES = {
    "Canal (Funnel)":            ("Funnel", "Canal", "Categórica", "Real"),
    "Indicador del embudo":      ("Funnel", "Indicador", "Categórica", "Real"),
    "Campaña digital":           ("MKT_Digital", "Campaña", "Categórica", "Leads"),
    "Canal principal":           ("Principales_Canales", "Canal", "Categórica", "Ventas"),
    "Asesor de piso":            ("Analisis_de_Piso", "Asesor", "Categórica", "Ventas"),
    "Vendedor":                  ("Ventas_por_Asesor", "Vendedor", "Categórica", "Ventas"),
    "Ventas por asesor de piso": ("Analisis_de_Piso", "Ventas", "Numérica discreta", None),
    "Ventas por vendedor":       ("Ventas_por_Asesor", "Ventas", "Numérica discreta", None),
    "Bono de marketing":         ("Marketing", "Bono_Marketing", "Numérica discreta", None),
    "Bajas de personal":         ("TOPS_TDH", "Bajas", "Numérica discreta", None),
    "Vacantes":                  ("TOPS_TDH", "Vacantes", "Numérica discreta", None),
    "APVS Oro":                  ("TOPS_TDH", "APVS_Oro", "Numérica discreta", None),
    "APVS Plata":                ("TOPS_TDH", "APVS_Plata", "Numérica discreta", None),
    "APVS Bronce":               ("TOPS_TDH", "APVS_Bronce", "Numérica discreta", None),
    "Clima laboral":             ("TOPS_TDH", "Clima_Laboral", "Numérica discreta", None),
}

#Busca el CSV en la carpeta de app.py aunque tenga " 1", "(1)" o "_1" al final del nombre
CARPETA = os.path.dirname(os.path.abspath(__file__))
def leer(nombre):
    base = nombre[:-4]
    for variante in [nombre, f"{base} 1.csv", f"{base} (1).csv", f"{base}_1.csv", f"{base}(1).csv"]:
        ruta = os.path.join(CARPETA, variante)
        if os.path.exists(ruta):
            return pd.read_csv(ruta)
    st.error(f"No encuentro **{nombre}**. Ponlo en la misma carpeta que app.py: {CARPETA}")
    st.stop()

######################################################
#Definimos la instancia
@st.cache_resource
######################################################
#Creamos la función de carga de datos
def load_data():
    #Lectura de los archivos csv (una por una). Deben estar en la misma carpeta que app.py
    #No rellenamos nulos con bfill/ffill: un dato faltante no es igual al del mes vecino
    bases = {}
    bases["Analisis_de_Piso"] = leer("Analisis_de_Piso_Limpio.csv")
    bases["Funnel"] = leer("Funnel_Limpio.csv")
    bases["Leads_Reales"] = leer("Leads_Reales_Limpio.csv")
    bases["Marketing"] = leer("Marketing_Limpio.csv")
    bases["MKT_Digital"] = leer("MKT_Digital_Limpio.csv")
    bases["Principales_Canales"] = leer("Principales_Canales_Limpio.csv")
    bases["SDC"] = leer("SDC_Limpio.csv")
    bases["TOPS_TDH"] = leer("TOPS_TDH_Limpio.csv")
    bases["Ventas"] = leer("Ventas_Limpio.csv")
    bases["Ventas_por_Asesor"] = leer("Ventas_por_Asesor_Limpio.csv")
    #Bases nuevas de la Etapa II (una fila por mes)
    bases["Funnel_Ventas_Mensual"] = leer("Funnel_Ventas_Mensual.csv")
    bases["MKT_Digital_Mensual"] = leer("MKT_Digital_Mensual.csv")
    bases["Ventas_por_Asesor_Mensual"] = leer("Ventas_por_Asesor_Mensual.csv")

    #Unificamos nombres repetidos del mismo canal en Funnel
    bases["Funnel"]["Canal"] = bases["Funnel"]["Canal"].replace({
        "Plaza Ange": "Plaza Angelopólis",
        "Gran Patio": "Gran Patio Tlaxcala",
        "Prospeccion": "Estrategia de Prospeccion",
        "Plaza Pachuca (2)": "Plaza Pachuca",
        "Otros / Cartera / Casa": "Otros",
        "Otros / Custom": "Otros",
    })
    return bases

###############################################################################
#Cargo los datos obtenidos de la función "load_data"
bases = load_data()

###############################################################################
#FUNCIONES DE APOYO
#Escribe las categorías sin decimales de sobra: 2.0 -> "2"
def como_texto(valor):
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)

#Prepara los datos de Funnel para que no se cuente doble
def preparar(df, variable):
    if variable == "Canal (Funnel)":
        #"GAC Angelopolis" es el TOTAL de la agencia (suma de los demás canales): lo quitamos
        #y medimos cada canal por sus ventas reales
        return df[(df["Indicador"] == "Ventas") & (df["Canal"] != "GAC Angelopolis")]
    if variable == "Indicador del embudo":
        #Usamos solo la fila del total para ver el embudo completo de la agencia
        return df[(df["Canal"] == "GAC Angelopolis") & (df["Indicador"].isin(ETAPAS))]
    return df

#Arma las frecuencias (o sumas) de cada categoría con su porcentaje
def frecuencias(df, columna, medida, tipo, variable=""):
    if medida:
        Datos = df.groupby(columna)[medida].sum().reset_index()
        if variable == "Canal (Funnel)":
            nombre = "Ventas"
        elif variable == "Indicador del embudo":
            nombre = "Clientes"
        else:
            nombre = medida
    else:
        Datos = df[columna].value_counts().reset_index()
        nombre = "Registros"
    Datos.columns = ["Categoría", nombre]
    #Las numéricas se ordenan 0, 1, 2...; las de texto de mayor a menor
    if tipo == "Numérica discreta":
        Datos = Datos.sort_values("Categoría")
    else:
        Datos = Datos.sort_values(nombre, ascending=False)
    Datos["Categoría"] = Datos["Categoría"].apply(como_texto)
    Datos[nombre] = Datos[nombre].round(0).astype(int)
    Datos["Porcentaje"] = (Datos[nombre] / max(Datos[nombre].sum(), 1) * 100).round(1)
    return Datos.reset_index(drop=True), nombre

#Datos del embudo (etapas en orden, real vs objetivo)
def datos_embudo(df):
    Embudo = (df.groupby("Indicador")[["Real", "Objetivo"]].sum()
              .reindex(ETAPAS).fillna(0).reset_index())
    Embudo["Real"] = Embudo["Real"].round(0).astype(int)
    Embudo["Cumplimiento"] = (Embudo["Real"] / Embudo["Objetivo"].replace(0, 1) * 100).round(0)
    Embudo["Pasa"] = (Embudo["Real"] / Embudo["Real"].shift(1) * 100).round(0)
    return Embudo

#Colores por barra: la(s) categoría(s) a destacar en rojo y el resto en gris (contexto)
def resaltar(categorias, destacar, base=GRIS):
    return [ROJO if c in destacar else base for c in categorias]

@st.cache_data
def imagen_b64(ruta, ancho=None):
    if not os.path.exists(ruta):
        return None
    imagen = Image.open(ruta)
    if ancho:
        imagen.thumbnail((ancho, ancho))
    buffer = io.BytesIO()
    formato = "JPEG" if imagen.mode == "RGB" else "PNG"
    imagen.save(buffer, format=formato, quality=88)
    return f"data:image/{formato.lower()};base64," + base64.b64encode(buffer.getvalue()).decode()

#Estilos generales (UX): se conservan los elementos de marca (auto de fondo, fibra de carbono,
#disco de freno, acabados metálicos) pero en segundo plano, para que los datos sean lo primero
def aplicar_estilos():
    fondo, carbono = imagen_b64(FONDO, 1600), imagen_b64(CARBONO)
    icono = imagen_b64(DISCO, 64)
    capa_fondo = f", url('{fondo}')" if fondo else ""
    capa_carbono = f", url('{carbono}')" if carbono else ""
    vineta = f"background: url('{icono}') no-repeat 0 0.62em / 1.05em;" if icono else ""
    st.markdown(f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, .stApp, p, li, label, input, h1, h2, h3 {{ font-family: {FUENTE}; }}

    /* Fondo: el auto GAC se queda, aclarado con el gris de la página para no competir con las tarjetas */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(rgba(244,245,247,0.55), rgba(244,245,247,0.55)){capa_fondo};
        background-size: cover; background-position: right bottom; background-attachment: fixed;
        background-color: {FONDO_APP};
    }}
    [data-testid="stHeader"] {{ background: transparent; }}
    .stMain .block-container {{ padding-top: 2.2rem; max-width: 1280px; }}

    /* Barra lateral de fibra de carbono, oscurecida para que el texto claro se lea bien */
    [data-testid="stSidebar"] {{
        background: linear-gradient(rgba(18,20,24,0.78), rgba(18,20,24,0.88)){capa_carbono};
        background-color: #16181D;
        border-right: 3px solid {ROJO};
        border-radius: 0 22px 22px 0;
        box-shadow: 4px 0 16px rgba(200,16,46,0.22);
    }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #C9CED6 !important; }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        color: #FFFFFF !important; font-weight: 600; font-size: 0.82rem;
        text-transform: uppercase; letter-spacing: 0.06em;
    }}
    /* Controles con acabado metálico suave (plata clara, texto oscuro con buen contraste) */
    [data-testid="stSidebar"] :is([data-testid="stSelectbox"], [data-testid="stMultiSelect"]) > div:last-child > div {{
        background: linear-gradient(180deg, #FFFFFF 0%, #EEF0F3 55%, #E1E4E8 100%);
        border: 1px solid #8A9099; border-radius: 8px;
        box-shadow: inset 0 1px 0 #FFFFFF, 0 2px 6px rgba(0,0,0,0.35);
    }}
    [data-testid="stSidebar"] :is([data-testid="stSelectbox"], [data-testid="stMultiSelect"]) > div:last-child * {{ color: {TINTA} !important; }}
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span {{
        background: linear-gradient(180deg, #D8213D, {ROJO} 60%, #A80D27) !important;
        border: 1px solid {ROJO_OSCURO}; border-radius: 6px;
    }}
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span,
    [data-testid="stSidebar"] [data-testid="stMultiSelect"] [data-testid="stMultiSelectTagsContainer"] [role="group"] > span * {{ color: #FFFFFF !important; }}
    [data-testid="stSidebar"] hr {{ border-color: #2A2E35; }}

    /* Título con acabado metálico oscuro (alto contraste) y barra roja de acento */
    .stMain h1 {{
        font-weight: 800; letter-spacing: -0.02em;
        background: linear-gradient(180deg, #4A515C 0%, {TINTA} 50%, #3A4049 100%);
        -webkit-background-clip: text; background-clip: text; color: transparent;
        border-left: 6px solid {ROJO}; padding-left: 14px;
    }}
    .stMain h3 {{ color: {TINTA}; font-weight: 700; font-size: 1.2rem; }}
    .stMain [data-testid="stMarkdownContainer"] p {{ color: #3A4049; line-height: 1.6; }}
    .stMain [data-testid="stCaptionContainer"] p {{ color: {TINTA_2}; }}
    .stMain hr {{ border-color: rgba(31,35,40,0.12); }}

    /* Cada sección es una tarjeta blanca sobre el fondo del auto */
    .stMain [class*="st-key-seccion_"] {{
        background: rgba(255,255,255,0.94); backdrop-filter: blur(4px);
        border: 1px solid {BORDE} !important; border-radius: 14px;
        box-shadow: 0 1px 2px rgba(16,24,40,0.05), 0 6px 16px rgba(16,24,40,0.07);
    }}

    /* Puntos clave: el disco de freno como viñeta */
    .c-card {{ background: {SUPERFICIE}; border: 1px solid #E3E6EA; border-top: 4px solid {ROJO}; border-radius: 14px;
        padding: 14px 16px; margin: 6px 0 12px; min-height: 118px; box-shadow: 0 3px 12px rgba(0,0,0,0.03); }}
    .c-label {{ font-size: 0.8rem; color: {TINTA_2}; font-weight: 700; }}
    .c-value {{ font-size: 1.35rem; color: {TINTA}; font-weight: 800; margin: 6px 0; }}
    .c-detail {{ font-size: 0.88rem; color: {TINTA_2}; line-height: 1.4; }}
    .tabla-gac {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; background: {SUPERFICIE};
        border-radius: 12px; overflow: hidden; }}
    .tabla-gac th {{ background: #FCE8EB; color: {ROJO}; font-weight: 700; font-size: 0.75rem; letter-spacing: 0.02em;
        text-align: right; padding: 10px 12px; border-bottom: 2px solid {ROJO}; }}
    .tabla-gac td {{ color: {TINTA}; text-align: right; padding: 9px 12px; border-bottom: 1px solid #F0F2F4; }}
    .tabla-gac th:first-child, .tabla-gac td:first-child {{ text-align: left; font-weight: 600; }}
    .tabla-gac tbody tr:nth-child(even) td {{ background: #FAFAFB; }}
    .tabla-gac tbody tr:hover td {{ background: #FDF3F5; }}
    .chip-si {{ background: {ROJO}; color: #FFFFFF; padding: 2px 10px; border-radius: 999px; font-weight: 600; font-size: 0.8rem; }}
    .chip-no {{ background: {GRIS_CLARO}; color: {TINTA}; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; }}
    .puntos-titulo {{ font-size: 0.75rem; font-weight: 700; color: {ROJO};
                      text-transform: uppercase; letter-spacing: 0.08em; margin: 0.4em 0 0.6em;
                      border-bottom: 2px solid {ROJO}; display: inline-block; padding-bottom: 2px; }}
    .stMain [data-testid="stMarkdownContainer"] ul {{ list-style: none; padding-left: 0; }}
    .stMain [data-testid="stMarkdownContainer"] li {{
        padding: 0.55em 0 0.55em 1.6em; margin: 0; {vineta}
        border-bottom: 1px solid #F0F2F4; color: #3A4049; line-height: 1.5;
    }}
    .stMain [data-testid="stMarkdownContainer"] li:last-child {{ border-bottom: none; }}
    .stMain [data-testid="stMarkdownContainer"] strong {{ color: {TINTA}; }}

    /* Tarjetas de indicadores (semitransparentes sobre el fondo) */
    [data-testid="stMetric"] {{
        background: rgba(255,255,255,0.88); backdrop-filter: blur(4px);
        border: 1px solid {BORDE}; border-top: 3px solid {ROJO};
        border-radius: 12px; padding: 14px 18px;
        box-shadow: 0 3px 10px rgba(16,24,40,0.10);
    }}
    [data-testid="stMetricLabel"] p {{ color: {TINTA_2} !important; font-weight: 600; }}
    [data-testid="stMetricValue"] {{ color: {TINTA}; font-weight: 700; }}
    </style>""", unsafe_allow_html=True)

#Donas: se conservan el brillo metálico, el disco de freno al centro y las etiquetas con flecha;
#las etiquetas ahora son blancas con borde del color de la rebanada y texto oscuro (se leen siempre)
def decorar_dona(fig):
    traza = fig.data[0]
    etiquetas, valores = list(traza.labels), list(traza.values)
    colores = list(traza.marker.colors or [ROJO, CARBON, GRIS])
    total = max(sum(valores), 1)
    fig.update_layout(height=400, margin=dict(t=50, b=50, l=20, r=20))
    radio = 150
    #Texto dentro de la rebanada: blanco sobre colores oscuros, oscuro sobre grises claros
    texto = ["white" if c in (ROJO, CARBON, ROJO_OSCURO) else TINTA for c in colores]
    fig.update_traces(sort=False, direction="clockwise", rotation=0, textinfo="label+percent",
                      textposition="inside", textfont=dict(size=14, color=texto),
                      marker=dict(colors=colores, line=dict(color=SUPERFICIE, width=2)))
    if os.path.exists(BRILLO):
        fig.add_layout_image(source=Image.open(BRILLO), xref="paper", yref="paper", x=0.5, y=0.5,
                             sizex=1, sizey=1, xanchor="center", yanchor="middle", layer="above",
                             opacity=0.6)
    if os.path.exists(DISCO):
        fig.add_layout_image(source=Image.open(DISCO), xref="paper", yref="paper", x=0.5, y=0.5,
                             sizex=0.5, sizey=0.5, xanchor="center", yanchor="middle", layer="above")
    acumulado = 0
    for i, (etiqueta, valor) in enumerate(zip(etiquetas, valores)):
        angulo = math.radians(90 - (acumulado + valor / 2) / total * 360)
        acumulado += valor
        color = colores[i % len(colores)]
        fig.add_annotation(x=0.5, y=0.5, xref="paper", yref="paper",
                           xshift=radio * 0.92 * math.cos(angulo), yshift=radio * 0.92 * math.sin(angulo),
                           ax=95 * math.cos(angulo), ay=-45 * math.sin(angulo),
                           text=f"{etiqueta} ({valor / total * 100:.1f}%)", showarrow=True,
                           arrowhead=0, arrowwidth=1.5, arrowcolor=TINTA_2,
                           bgcolor=SUPERFICIE, bordercolor=color, borderwidth=2, borderpad=6,
                           font=dict(color=TINTA, size=13))
    return fig

#Muestra una sección: pregunta arriba, gráfica a la izquierda y puntos clave a la derecha
#Con abajo=True la gráfica usa todo el ancho y los puntos clave van debajo (para gráficas grandes)
def seccion(pregunta, figura, puntos, alto=400, abajo=False, antes=None):
    with st.container(border=True, key="seccion_" + re.sub(r"\W", "_", pregunta)):
        st.subheader(pregunta)
        if antes:  #widgets que van entre el título y la gráfica
            antes()
        if abajo:
            Contenedor_Graf, Contenedor_Texto = st.container(), st.container()
        else:
            Contenedor_Graf, Contenedor_Texto = st.columns([2, 1], gap="large")
        with Contenedor_Graf:
            figura.update_layout(height=alto, margin=dict(t=20, b=20), title=None,
                                 paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            #Números junto a las barras en texto oscuro, nunca del color de la barra
            figura.update_traces(outsidetextfont_color=TINTA, selector=dict(type="bar"))
            if figura.data and figura.data[0].type == "pie":
                decorar_dona(figura)
            st.plotly_chart(figura, width="stretch", key=pregunta, theme=None)
        with Contenedor_Texto:
            st.markdown('<div class="puntos-titulo">Puntos clave</div>', unsafe_allow_html=True)
            if abajo:  #los puntos clave en fila, uno por columna
                for col, p in zip(st.columns(len(puntos), gap="medium"), puntos):
                    col.markdown(f"- {p}")
            else:
                st.markdown("\n".join(f"- {p}" for p in puntos))

#Suma (o valor) de la variable en cada mes, ordenado en el tiempo
def serie_mensual(df, columna, medida):
    numero_mes = {m: f"{i:02d}" for i, m in enumerate(MESES, 1)}
    datos = df.copy()
    datos["Mes del año"] = datos["Año"].astype(str) + "-" + datos["Mes"].map(numero_mes)
    datos["Valor"] = datos[medida] if medida else datos[columna]
    return datos.groupby("Mes del año", as_index=False)["Valor"].sum().sort_values("Mes del año")

###############################################################################
#FUNCIONES DE LA ETAPA II (REGRESIÓN)
#Bases que se pueden modelar: nombre en el menú -> base
BASES_REG = {
    "Mensual combinada (todas las bases)": "Mensual_Combinada",
    "Marketing": "Marketing",
    "Leads reales": "Leads_Reales",
    "Solicitudes de crédito (SDC)": "SDC",
    "Principales canales": "Principales_Canales",
    "Funnel (embudo por canal)": "Funnel",
    "Análisis de piso (asesor por mes)": "Analisis_de_Piso",
    "TOPS / TDH (personal)": "TOPS_TDH",
    "Funnel: ventas vs objetivo mensual": "Funnel_Ventas_Mensual",
}
#X sugeridas al abrir la vista (el usuario las puede cambiar)
DEFAULT_X = {"Mensual_Combinada": "Citas_Efectivas", "Marketing": "Leads_Total",
             "Principales_Canales": "Citas_Efectivas", "Funnel": "Cita efectiva",
             "Analisis_de_Piso": "Leads", "Funnel_Ventas_Mensual": "Objetivo"}
DEFAULT_XS = {"Mensual_Combinada": ["Leads_Total", "Citas_Efectivas", "PDM", "Aprobadas"],
              "Marketing": ["Leads_Total", "Provision", "Bono_Marketing"],
              "Principales_Canales": ["Leads", "Citas_Efectivas", "PDM"],
              "Funnel": ["Cita efectiva", "Prueba de manejo", "Solicitud de crédito aprobada"],
              "SDC": ["Generadas", "Aprobadas", "Formalizadas"]}

#Nombre legible de una columna: Citas_Efectivas -> Citas Efectivas
def bonito(columna):
    return str(columna).replace("_", " ").replace("PDM", "Pruebas de manejo").replace("APVS", "asesores")

#Formato de números según su tamaño
def num(v):
    v = float(v)
    if abs(v) >= 1000:
        return f"{v:,.0f}"
    if abs(v) >= 1:
        return f"{v:,.2f}"
    return f"{v:.4f}"

#Fuerza de la relación según |r|
def fuerza(r):
    return "Fuerte" if abs(r) >= 0.7 else ("Moderada" if abs(r) >= 0.4 else "Débil")

#p-valor de dos colas con la t de Student (si no hay scipy, aproximación normal)
def p_valor(t, gl):
    try:
        from scipy import stats
        return 2 * stats.t.sf(np.abs(t), gl)
    except ImportError:
        return np.array([math.erfc(abs(x) / math.sqrt(2)) for x in np.atleast_1d(t)])

#Mínimos cuadrados ordinarios (OLS): Y = b0 + b1*X1 + ... + bk*Xk
def ols(df, y, xs):
    d = df.dropna(subset=[y] + xs)
    n, k = len(d), len(xs) + 1
    if n <= k:
        return None
    X = np.column_stack([np.ones(n)] + [d[x].to_numpy(float) for x in xs])
    Yv = d[y].to_numpy(float)
    beta = np.linalg.lstsq(X, Yv, rcond=None)[0]
    pred = X @ beta
    res = Yv - pred
    sse, sst = (res ** 2).sum(), ((Yv - Yv.mean()) ** 2).sum()
    gl = n - k
    r2 = 1 - sse / sst if sst > 0 else 0.0
    se = np.sqrt(np.diag(sse / gl * np.linalg.pinv(X.T @ X))) if gl > 0 else np.full(k, np.nan)
    t = np.divide(beta, se, out=np.zeros(k), where=se > 0)
    return {"d": d, "beta": beta, "se": se, "t": t, "p": p_valor(t, gl), "pred": pred, "res": res,
            "r2": r2, "r2a": 1 - (1 - r2) * (n - 1) / gl if gl > 0 else np.nan,
            "rmse": math.sqrt(sse / n), "n": n, "gl": gl}

#VIF: qué tanto se explica cada X con las demás X (mayor a 10 = multicolinealidad)
def vif(d, xs):
    salida = []
    for x in xs:
        m = ols(d, x, [o for o in xs if o != x])
        salida.append(np.inf if m is None or m["r2"] >= 0.9999 else 1 / (1 - m["r2"]))
    return salida

#Líneas punteadas entre cada dato real y su predicción (el error de cada punto)
def lineas_error(x, y_real, y_pred):
    sx, sy = [], []
    for xi, yr, yp in zip(x, y_real, y_pred):
        sx += [xi, xi, None]
        sy += [yr, yp, None]
    return go.Scatter(x=sx, y=sy, mode="lines", name="Error de predicción", hoverinfo="skip",
                      line=dict(color=GRIS, width=1, dash="dot"))

#Número con signo para la ecuación en LaTeX (+ 0.1424 / - 2.31)
def con_signo(v):
    return ("+ " if v >= 0 else "- ") + num(abs(v))

#Texto seguro para LaTeX: \text{Citas Efectivas}
def tx(nombre):
    return "\\text{" + bonito(nombre).replace("%", "\\%").replace("&", "\\&") + "}"

#APARTADO "ECUACIÓN ESTIMADA": la ecuación con los coeficientes y cómo se lee cada uno
def bloque_ecuacion(Y, xs, modelo, clave):
    beta, pv = modelo["beta"], modelo["p"]
    k = len(xs)
    with st.container(border=True, key="seccion_ecuacion_" + clave):
        st.subheader("Ecuación estimada")
        st.markdown('<div class="puntos-titulo">Ecuación con los datos</div>', unsafe_allow_html=True)
        #Un término por renglón cuando hay varias X, para que no se salga de la pantalla
        terminos = [f"{con_signo(b)} \\cdot {tx(x)}" for b, x in zip(beta[1:], xs)]
        if k <= 2:
            st.latex(r"\widehat{" + tx(Y) + "} = " + num(beta[0]) + " " + " ".join(terminos))
        else:
            st.latex(r"\begin{aligned} \widehat{" + tx(Y) + "} = \\; & " + num(beta[0]) + " \\\\ & "
                     + " \\\\ & ".join(terminos) + r" \end{aligned}")
        st.caption(f"Estimada por mínimos cuadrados ordinarios (MCO) · R² = {modelo['r2']:.2f} · n = {modelo['n']} registros")
        #Cómo se lee cada coeficiente (en palabras)
        st.markdown('<div class="puntos-titulo">Cómo se lee</div>', unsafe_allow_html=True)
        lectura = [f"**β₀ = {num(beta[0])}** (intercepto): valor estimado de {bonito(Y)} cuando "
                   + ("la X vale 0." if k == 1 else "todas las X valen 0; sirve para ajustar la recta, no siempre tiene sentido práctico.")]
        for i, (b, x, p) in enumerate(zip(beta[1:], xs, pv[1:]), 1):
            resto = "" if k == 1 else ", manteniendo las demás X igual"
            lectura.append(f"**β{str(i).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉'))} = {num(b)}**: por cada 1 más de "
                           f"**{bonito(x)}**, {bonito(Y)} {'sube' if b >= 0 else 'baja'} en promedio {num(abs(b))}{resto} · "
                           + ("**significativa** (p = " if p < 0.05 else "no significativa (p = ") + f"{p:.3f})")
        st.markdown("\n".join(f"- {t}" for t in lectura))

#Dibuja una figura de plotly con el estilo del dashboard (fondo transparente, texto oscuro)
def dibujar(figura, alto, clave):
    figura.update_layout(height=alto, margin=dict(t=10, b=20), title=None,
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(figura, width="stretch", key=clave, theme=None)

#Puntos clave en una fila (uno por columna), debajo de la gráfica
def puntos_en_fila(puntos):
    st.markdown('<div class="puntos-titulo">Puntos clave</div>', unsafe_allow_html=True)
    for col, p in zip(st.columns(len(puntos), gap="medium"), puntos):
        col.markdown(f"- {p}")

###############################################################################
#FUNCIONES DE LA ETAPA III (CLASIFICACIÓN CON REGRESIÓN LOGÍSTICA)
#Bases de clasificación: nombre en el menú -> clave interna
BASES_CLAS = {
    "Leads Plaza Angelópolis": "Leads_Ange",
    "Leads Galerías Tlaxcala": "Leads_Tlax",
    "Plazas (embudo por lead)": "Plazas",
    "Citas digitales (BDC)": "Citas_Digital",
    "Bitácora de piso": "Bitacora_Piso",
    "Leads reales (mensual)": "Leads_Reales",
}
#Archivo de cada base (se aceptan varios nombres por si se descargó con otro nombre)
ARCHIVOS_CLAS = {
    "Leads_Ange": ["Base_Leads_Procesada.csv"],
    "Leads_Tlax": ["Base_Tlaxcala_Procesada.csv"],
    "Plazas": ["Plazas_Procesada.csv"],
    "Citas_Digital": ["Citas_Digital_Procesada.csv"],
    "Bitacora_Piso": ["Bitacora_Piso_Dicotomica.csv"],
    "Leads_Reales": ["Leads_Reales_Dicotomica.csv"],
}

#Como leer(), pero si el archivo no está regresa None (así la Etapa I y II siguen funcionando)
def leer_opcional(nombres):
    for nombre in nombres:
        base = nombre[:-4]
        for variante in [nombre, f"{base} 1.csv", f"{base} (1).csv", f"{base}_1.csv", f"{base}(1).csv"]:
            ruta = os.path.join(CARPETA, variante)
            if os.path.exists(ruta):
                try:
                    return pd.read_csv(ruta, encoding="utf-8-sig", low_memory=False)
                except UnicodeDecodeError:
                    return pd.read_csv(ruta, encoding="latin-1", low_memory=False)
    return None

#Convierte una columna a número (True/False, "1", 1.0 -> 1)
def a_numero(serie):
    return pd.to_numeric(serie.replace({"True": 1, "False": 0, True: 1, False: 0}), errors="coerce")

#Prepara cada base: solo columnas numéricas 0/1 (o numéricas) que sirven para el modelo
#ys = variables dicotómicas que se pueden predecir
#orden = pasos del embudo: para predecir un paso solo se usan los pasos ANTERIORES
#        (usar un paso posterior sería "hacer trampa": si hubo crédito, ya hubo prueba)
#extras = X que no son parte del embudo y se sugieren al abrir la vista
@st.cache_data
def preparar_clasificacion(clave):
    d = leer_opcional(ARCHIVOS_CLAS[clave])
    if d is None:
        return None
    d.columns = [str(c).strip() for c in d.columns]
    if clave in ("Leads_Ange", "Leads_Tlax"):
        temp = d["Temperatura"].fillna("")
        df = pd.DataFrame({
            "Venta_Confirmada": a_numero(d["Venta_Confirmada"]),
            "Temp_Muy_Interesado": (temp == "Lead Muy Interesado").astype(int),
            "Temp_Interes_Medio": (temp == "Lead Interes Medio").astype(int),
            "Temp_Interes_Bajo": (temp == "Lead Interes Bajo").astype(int),
            "Es_Return": d["Titulo"].astype(str).str.contains("Return").astype(int)})
        producto = d["Producto"].astype(str).str.upper().str.strip()
        for p in ["EMZOOM", "EMKOO", "GS8"]:
            df[f"Producto_{p}"] = (producto == p).astype(int)
        #Interés medio queda como referencia (no se incluyen las 3 temperaturas a la vez)
        cfg = dict(ys=["Venta_Confirmada"], orden=[], extras=["Temp_Muy_Interesado", "Temp_Interes_Bajo"])
    elif clave == "Plazas":
        df = pd.DataFrame({
            "Seguimiento": a_numero(d["Seguimiento"]),
            "Cita_Efectiva": a_numero(d["Cita efetiva"]),
            "PDM": a_numero(d["PDM"]),
            "SDC": a_numero(d["SDC"]),
            "Venta_Facturada": a_numero(d["Facturado_Confirmado"])})
        df["Plaza_Angelopolis"] = d["Origen"].astype(str).str.upper().str.contains("ANGELOPOLIS").astype(int)
        producto = d["Producto"].astype(str).str.upper().str.strip()
        for p in ["EMZOOM", "EMKOO", "GS8"]:
            df[f"Producto_{p}"] = (producto == p).astype(int)
        cfg = dict(ys=["Venta_Facturada", "SDC", "PDM", "Cita_Efectiva"],
                   orden=["Seguimiento", "Cita_Efectiva", "PDM", "SDC", "Venta_Facturada"],
                   extras=["Plaza_Angelopolis"])
    elif clave == "Citas_Digital":
        bdc = d["BDC"].astype(str).str.strip().str.title().replace({"Igancio": "Ignacio"})
        df = pd.DataFrame({
            "PDM": a_numero(d["PDM"]),
            "SDC": a_numero(d["SDC"]),
            "Venta": a_numero(d["Venta"]),
            #En porcentaje (0-100) para que el coeficiente se lea "por cada punto de potencial"
            "Potencial_de_compra": a_numero(d["Potencial_Compra_Num"]) * 100})
        for a in ["Ana", "Antonio", "Ignacio"]:
            df[f"BDC_{a}"] = (bdc == a).astype(int)
        cfg = dict(ys=["Venta", "SDC", "PDM"], orden=["PDM", "SDC", "Venta"], extras=["Potencial_de_compra"])
    elif clave == "Bitacora_Piso":
        d = d[d["Nombre Cliente"].notna()]
        df = pd.DataFrame({
            "PDM": a_numero(d["PDM"]),
            "SDC": a_numero(d["SDC"]),
            "Venta": a_numero(d["Venta"]),
            "Intervencion_Gerente": a_numero(d["Inter Gerente"])})
        cfg = dict(ys=["Venta", "SDC", "PDM"], orden=["PDM", "SDC", "Venta"], extras=["Intervencion_Gerente"])
    else:  #Leads reales: una fila por mes
        #Para predecir si un mes tendrá alta conversión o alta efectividad usamos lo que pasó el MES ANTERIOR
        #(los datos del mismo mes ya traen la respuesta: conversión = ventas / efectivos)
        orden_mes = {m: i for i, m in enumerate(MESES, 1)}
        d = d.assign(_mes=d["Mes"].map(orden_mes)).sort_values(["Año", "_mes"]).reset_index(drop=True)
        df = pd.DataFrame({
            "Alta_Conversion": a_numero(d["Alta_Conversion"]),
            "Alta_Efectividad": a_numero(d["Alta_Efectividad"])})
        for origen, nombre in [("Total", "Leads_mes_anterior"), ("No Contesta", "No_contesta_mes_anterior"),
                               ("Ilocalizable", "Ilocalizables_mes_anterior"), ("Abiertos", "Abiertos_mes_anterior"),
                               ("Ventas", "Ventas_mes_anterior")]:
            df[nombre] = a_numero(d[origen]).shift(1)
        df["Alta_conversion_mes_anterior"] = df["Alta_Conversion"].shift(1)
        df["Alta_efectividad_mes_anterior"] = df["Alta_Efectividad"].shift(1)
        df = df.iloc[1:]   #el primer mes no tiene mes anterior
        cfg = dict(ys=["Alta_Conversion", "Alta_Efectividad"], orden=[],
                   extras={"Alta_Conversion": ["Alta_conversion_mes_anterior", "Abiertos_mes_anterior", "Ventas_mes_anterior"],
                           "Alta_Efectividad": ["Alta_efectividad_mes_anterior", "No_contesta_mes_anterior",
                                                "Ilocalizables_mes_anterior"]},
                   prohibidas={"Alta_Conversion": ["Alta_Efectividad"], "Alta_Efectividad": ["Alta_Conversion"]})
    df = df.reset_index(drop=True)
    return dict(df=df, **cfg)

#X permitidas para una Y: todo menos la Y y los pasos del embudo que van DESPUÉS de ella
def candidatas_clas(cfg, Y):
    df, orden = cfg["df"], cfg["orden"]
    prohibidas = set(orden[orden.index(Y):]) if Y in orden else {Y}
    prohibidas |= set(cfg.get("prohibidas", {}).get(Y, []))
    return [c for c in df.columns if c not in prohibidas and df[c].nunique(dropna=True) > 1]

#X sugeridas: los (hasta 3) pasos anteriores del embudo + las extras de la base
def x_sugeridas(cfg, Y, candidatas):
    orden = cfg["orden"]
    previas = orden[:orden.index(Y)][-3:] if Y in orden else []
    extras = cfg["extras"].get(Y, []) if isinstance(cfg["extras"], dict) else cfg["extras"]
    xs = [c for c in previas + extras if c in candidatas]
    return xs or candidatas[:3]

#Probabilidad con la función logística: p = 1 / (1 + e^(-z))
def sigmoide(z):
    return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

#REGRESIÓN LOGÍSTICA por máxima verosimilitud (método de Newton), igual que LogisticRegression
#Lleva una penalización muy pequeña (lam) para que los coeficientes no se disparen cuando una
#variable separa perfectamente los Sí de los No (pasa con bases chicas)
def logit(df, y, xs, lam=0.1):
    d = df.dropna(subset=[y] + xs)
    Yv = d[y].to_numpy(float)
    if len(d) < 10 or Yv.min() == Yv.max():
        return None
    X0 = d[xs].to_numpy(float)
    n, k = X0.shape
    #Se ajusta con X estandarizadas (más estable) y luego se regresa a las unidades originales
    media, desv = X0.mean(0), X0.std(0)
    desv[desv == 0] = 1
    Z = np.column_stack([np.ones(n), (X0 - media) / desv])
    pen = np.diag([1e-6] + [lam] * k)
    b = np.zeros(k + 1)
    for _ in range(100):
        p = sigmoide(Z @ b)
        H = Z.T @ (Z * (p * (1 - p))[:, None]) + pen
        paso = np.linalg.solve(H, Z.T @ (Yv - p) - pen @ b)
        b += paso
        if np.abs(paso).max() < 1e-8:
            break
    beta = np.r_[b[0] - np.sum(b[1:] * media / desv), b[1:] / desv]
    X = np.column_stack([np.ones(n), X0])
    prob = sigmoide(X @ beta)
    #Errores estándar y p-valores (prueba z de Wald)
    H = X.T @ (X * (prob * (1 - prob))[:, None]) + np.diag([1e-6] + list(lam / desv ** 2))
    se = np.sqrt(np.abs(np.diag(np.linalg.pinv(H))))
    z = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    pv = np.array([math.erfc(abs(v) / math.sqrt(2)) for v in z])
    #Pseudo R² de McFadden: qué tanto mejora el modelo contra no usar ninguna X
    pc = np.clip(prob, 1e-12, 1 - 1e-12)
    ll = np.sum(Yv * np.log(pc) + (1 - Yv) * np.log(1 - pc))
    m = Yv.mean()
    ll0 = len(Yv) * (m * np.log(m) + (1 - m) * np.log(1 - m))
    return {"d": d, "beta": beta, "se": se, "z": z, "p": pv, "prob": prob, "y": Yv,
            "n": n, "pseudo_r2": 1 - ll / ll0}

#Probabilidad que da el modelo a nuevos datos
def probabilidad(d, xs, beta):
    return sigmoide(beta[0] + d[xs].to_numpy(float) @ beta[1:])

#Curva ROC: sensibilidad vs (1 - especificidad) para todos los umbrales posibles
def roc(y, prob):
    y, prob = np.asarray(y, float), np.asarray(prob, float)
    P, N = y.sum(), len(y) - y.sum()
    if P == 0 or N == 0:
        return np.array([0, 1]), np.array([0, 1]), np.array([np.inf, 0])
    orden = np.argsort(-prob, kind="mergesort")
    ys, ps = y[orden], prob[orden]
    vp, fp = np.cumsum(ys), np.cumsum(1 - ys)
    cortes = np.r_[np.where(np.diff(ps) != 0)[0], len(ps) - 1]
    return np.r_[0, fp[cortes] / N], np.r_[0, vp[cortes] / P], np.r_[np.inf, ps[cortes]]

#Área bajo la curva ROC: 0.5 = como lanzar una moneda, 1 = clasifica perfecto
def auc(y, prob):
    fpr, tpr, _ = roc(y, prob)
    return float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))

#Umbral óptimo (índice de Youden): el que hace más grande sensibilidad + especificidad
def umbral_optimo(y, prob):
    fpr, tpr, cortes = roc(y, prob)
    if len(cortes) <= 2 and np.isinf(cortes[0]) and cortes[-1] == 0:
        return 0.5
    i = int(np.argmax((tpr - fpr)[1:])) + 1
    return float(min(cortes[i], 1.0))

#Matriz de confusión y métricas con un umbral
def metricas(y, prob, umbral):
    y = np.asarray(y, int)
    pred = (np.asarray(prob) >= umbral).astype(int)
    vp = int(((pred == 1) & (y == 1)).sum())
    fp = int(((pred == 1) & (y == 0)).sum())
    fn = int(((pred == 0) & (y == 1)).sum())
    vn = int(((pred == 0) & (y == 0)).sum())
    div = lambda a, b: a / b if b else np.nan
    return {"VP": vp, "FP": fp, "FN": fn, "VN": vn, "n": len(y),
            "Exactitud": div(vp + vn, len(y)), "Precisión": div(vp, vp + fp),
            "Sensibilidad": div(vp, vp + fn), "Especificidad": div(vn, vn + fp),
            "Precisión (Sí)": div(vp, vp + fp), "Precisión (No)": div(vn, vn + fn),
            "Sensibilidad (Sí)": div(vp, vp + fn), "Sensibilidad (No)": div(vn, vn + fp)}

#Separa 30% de los datos para PRUEBA, manteniendo la misma proporción de Sí y No (estratificado)
def separar_prueba(d, y, proporcion=0.3, semilla=42):
    rng = np.random.default_rng(semilla)
    prueba = np.zeros(len(d), dtype=bool)
    for clase in (0, 1):
        idx = np.where(d[y].to_numpy() == clase)[0]
        rng.shuffle(idx)
        cuantos = int(round(len(idx) * proporcion))
        if clase == 1 and len(idx) >= 2:
            cuantos = max(cuantos, 1)
        prueba[idx[:cuantos]] = True
    return prueba

MODOS_UMBRAL = ["0.50 (estándar)"]
MODOS_EVAL = ["Todos los datos", "Datos de prueba (30%)"]
MODOS_BALANCEO = ["Sobremuestreo (igualar Sí y No)", "Sin balanceo"]

#SOBREMUESTREO: duplica al azar casos de la clase con menos registros hasta igualar a la otra
#Solo se aplica a los datos de ENTRENAMIENTO; las métricas se miden con los datos originales
def sobremuestrear(d, y, semilla=42):
    conteo = d[y].value_counts()
    if len(conteo) < 2 or conteo.min() == conteo.max():
        return d
    minoritaria = conteo.idxmin()
    faltan = int(conteo.max() - conteo.min())
    extra = d[d[y] == minoritaria].sample(n=faltan, replace=True, random_state=semilla)
    return pd.concat([d, extra], ignore_index=True)

#Ajusta el modelo y lo evalúa con el umbral elegido
def evaluar_clasificacion(df, y, xs, modo_umbral, umbral_manual=0.5, modo_eval=MODOS_EVAL[0],
                          balanceo=MODOS_BALANCEO[0]):
    d = df.dropna(subset=[y] + xs).reset_index(drop=True)
    if len(d) < 10 or d[y].nunique() < 2:
        return None
    mascara = separar_prueba(d, y) if modo_eval == MODOS_EVAL[1] else np.zeros(len(d), dtype=bool)
    entrena = d[~mascara] if mascara.any() else d
    evalua = d[mascara] if mascara.any() else d
    antes = entrena[y].value_counts().reindex([0, 1], fill_value=0)
    if balanceo == MODOS_BALANCEO[0]:
        entrena = sobremuestrear(entrena, y)
    despues = entrena[y].value_counts().reindex([0, 1], fill_value=0)
    M = logit(entrena, y, xs)
    if M is None:
        return None
    umbral = 0.50  # Estándar fijo para todos los modelos.
    prob = probabilidad(evalua, xs, M["beta"])
    yv = evalua[y].to_numpy(int)
    met = metricas(yv, prob, umbral)
    met["AUC"] = auc(yv, prob)
    return {"M": M, "umbral": umbral, "y": yv, "prob": prob, "evalua": evalua, "met": met,
            "met_05": metricas(yv, prob, 0.5), "n_entrena": len(entrena),
            "antes": antes, "despues": despues, "balanceo": balanceo}

#Tarjeta sencilla con título, valor y explicación (para la guía y los conteos)
def tarjeta_c(titulo, valor, detalle="", color=None):
    st.markdown(f'<div class="c-card" style="border-top-color:{color or ROJO}"><div class="c-label">{titulo}</div>'
                f'<div class="c-value">{valor}</div><div class="c-detail">{detalle}</div></div>', unsafe_allow_html=True)

def fila_tarjetas(items):
    for col, item in zip(st.columns(len(items)), items):
        with col:
            tarjeta_c(*item)

#GUÍA: cómo leer los resultados (para explicar el dashboard sin tecnicismos)
def guia_clasificacion():
    with st.expander("Guía rápida · Sí y No"):
        g1, g2, g3 = st.tabs(["Métricas", "Matriz de confusión", "Sobremuestreo"])
        with g1:
            fila_tarjetas([("Precisión (Sí)", "Sí correctos", "Entre los Sí predichos, cuántos eran Sí.", ROJO),
                           ("Precisión (No)", "No correctos", "Entre los No predichos, cuántos eran No.", CARBON)])
            fila_tarjetas([("Sensibilidad (Sí)", "Sí detectados", "De los Sí reales, cuántos encontró.", ROJO),
                           ("Sensibilidad (No)", "No detectados", "De los No reales, cuántos encontró.", CARBON)])
            st.caption("Exactitud = aciertos totales. Sensibilidad (No) equivale a especificidad. — = no calculable.")
        with g2:
            fila_tarjetas([("Verdaderos positivos (Sí)", "Acierto", "Predijo Sí · era Sí", CARBON),
                           ("Verdaderos negativos (No)", "Acierto", "Predijo No · era No", CARBON)])
            fila_tarjetas([("Falsos positivos (Sí predicho)", "Error", "Predijo Sí · era No", ROJO),
                           ("Falsos negativos (No predicho)", "Error", "Predijo No · era Sí", ROJO)])
            st.caption("Filas = resultado real · columnas = predicción. Sí = 1 · No = 0.")
        with g3:
            fila_tarjetas([("Sobremuestreo", "Repite la minoría", "Iguala Sí y No solo al entrenar.", ROJO),
                           ("Evaluación", "Sin sobremuestreo", "Conserva los registros originales.", CARBON)])
            st.caption("Puede aumentar la detección y las falsas alarmas. No aporta clientes nuevos.")

#Corre un modelo por CADA variable dicotómica de CADA base (para el resumen)
def todos_los_modelos(modo_umbral, balanceo):
    filas = []
    for nombre_b, clave_b in BASES_CLAS.items():
        cfg_b = preparar_clasificacion(clave_b)
        if cfg_b is None:
            continue
        for y_b in cfg_b["ys"]:
            cand_b = candidatas_clas(cfg_b, y_b)
            xs_b = x_sugeridas(cfg_b, y_b, cand_b)
            R = evaluar_clasificacion(cfg_b["df"], y_b, xs_b, modo_umbral, balanceo=balanceo)
            if R is None:
                continue
            m = R["met"]
            positivos = int(R["y"].sum())
            filas.append({"Base": nombre_b, "Y (Sí/No)": bonito(y_b), "Modelo": f"{nombre_b} · {bonito(y_b)}",
                          "X": ", ".join(bonito(x) for x in xs_b), "Exactitud": m["Exactitud"],
                          **{k: m[k] for k in ["Precisión (Sí)", "Precisión (No)", "Sensibilidad (Sí)", "Sensibilidad (No)"]},
                          "AUC": m["AUC"],
                          "Base sin modelo": max(R["y"].mean(), 1 - R["y"].mean()),
                          "Positivos": positivos, "Registros (Sí)": positivos, "Registros (No)": m["n"] - positivos, "n": m["n"],
                          "Nota": "Pocos Sí: exploratorio" if positivos < 10 else
                                  ("No supera a la base" if m["Exactitud"] <= max(R["y"].mean(), 1 - R["y"].mean()) else "OK")})
    return pd.DataFrame(filas)

#Porcentaje bonito (o "—" si no se puede calcular, por ejemplo precisión sin ningún Sí predicho)
def pct(v):
    return "—" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v * 100:.1f}%"

def nombre_negocio_clas(variable):
    nombres = {"Temp_Muy_Interesado": "Interés alto", "Temp_Interes_Medio": "Interés medio",
               "Temp_Interes_Bajo": "Interés bajo", "Es_Return": "Cliente que regresa",
               "Venta_Confirmada": "Venta confirmada", "Venta_Facturada": "Venta facturada",
               "Venta": "Venta", "PDM": "Prueba de manejo", "SDC": "Solicitud de crédito",
               "Cita_Efectiva": "Asistencia a la cita", "Seguimiento": "Seguimiento al cliente",
               "Intervencion_Gerente": "Intervención del gerente", "Potencial_de_compra": "Potencial de compra",
               "Alta_Conversion": "Conversión alta", "Alta_Efectividad": "Efectividad alta"}
    if variable.startswith("Producto_"):
        return "Modelo de interés: " + variable.removeprefix("Producto_")
    if variable.startswith("BDC_"):
        return "Asesor: " + variable.removeprefix("BDC_")
    return nombres.get(variable, bonito(variable))

#MATRIZ DE CONFUSIÓN como mapa de calor: aciertos en carbón, errores en rojo
def fig_confusion(met, etiqueta):
    filas_no, filas_si = met["VN"] + met["FP"], met["FN"] + met["VP"]
    def celda(nombre, valor, total):
        parte = f"{valor / total * 100:.0f}% de los reales" if total else ""
        return f"<span style='font-size:30px'><b>{valor:,}</b></span><br><br><b>{nombre}</b><br>{parte}"
    texto = [[celda("Verdaderos negativos (No)", met["VN"], filas_no), celda("Falsos positivos (Sí predicho)", met["FP"], filas_no)],
             [celda("Falsos negativos (No predicho)", met["FN"], filas_si), celda("Verdaderos positivos (Sí)", met["VP"], filas_si)]]
    fig = go.Figure(go.Heatmap(
        z=[[1, 0], [0, 1]], x=[f"Predicho: No · {met['VN'] + met['FN']:,}", f"Predicho: Sí · {met['VP'] + met['FP']:,}"],
        y=[f"Real: No · {filas_no:,}", f"Real: Sí · {filas_si:,}"],
        text=texto, texttemplate="%{text}", textfont=dict(color="#FFFFFF", size=14),
        colorscale=[[0, ROJO], [1, CARBON]], showscale=False, xgap=6, ygap=6,
        hovertemplate="%{y} · %{x}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", showgrid=False, title=f"Real ({etiqueta})")
    fig.update_xaxes(side="top", showgrid=False, title="")
    return fig

#Arma la tabla numérica que usa el modelo según la base elegida
def tabla_regresion(base, canal=None):
    k = ["Año", "Mes"]
    if base == "Mensual_Combinada":
        #Una fila por mes uniendo las bases mensuales (solo meses que existen en Marketing)
        d = bases["Marketing"][k + ["Leads_Total", "Ventas", "Provision", "Reembolso_Total",
                                    "Bono_Marketing", "Aportacion_Agencia"]]
        piezas = [bases["Leads_Reales"][k + ["Efectivos", "No_Contesta", "Ilocalizable", "Abiertos"]],
                  bases["SDC"][k + ["Generadas", "Aprobadas", "Rechazadas", "Formalizadas"]],
                  bases["Principales_Canales"].groupby(k, as_index=False)[["Citas_Programadas",
                                                                           "Citas_Efectivas", "PDM"]].sum(),
                  bases["Funnel_Ventas_Mensual"][k + ["Objetivo"]].rename(columns={"Objetivo": "Objetivo_Ventas"}),
                  bases["Ventas_por_Asesor_Mensual"],
                  bases["MKT_Digital_Mensual"],
                  bases["TOPS_TDH"][k + ["Plantilla", "Operando", "Bajas", "Vacantes", "Productividad_APVS"]]]
        for p in piezas:
            d = d.merge(p, on=k, how="left")
    elif base == "Principales_Canales":
        d = bases[base].drop(columns=["Fecha", "Conversion", "Aporte"], errors="ignore")
        if canal and canal != "Todos (suma)":
            d = d[d["Canal"] == canal].drop(columns="Canal")
        else:
            d = d.groupby(k, as_index=False).sum(numeric_only=True)
    elif base == "Funnel":
        #Cada etapa del embudo pasa a ser una columna (valor real del canal en el mes)
        f = bases["Funnel"][bases["Funnel"]["Canal"] == canal]
        d = f.pivot_table(index=k, columns="Indicador", values="Real", aggfunc="sum").reset_index()
        d = d[k + [e for e in ETAPAS if e in d.columns]]
    elif base == "Analisis_de_Piso":
        d = bases[base][k + ["Asesor", "Leads", "Ventas"]]
    else:
        #Quitamos columnas que se calculan CON las ventas (p. ej. Conversion = Ventas / Leads):
        #usarlas como X sería "hacer trampa" porque ya traen la respuesta adentro
        d = bases[base].drop(columns=["Fecha", "Conversion", "Cumplimiento_Ventas",
                                      "CAP_General", "CAP_GAC", "CAC_General", "CAC_GAC"], errors="ignore")
    d = d.copy()
    numero_mes = {m: f"{i:02d}" for i, m in enumerate(MESES, 1)}
    d["Periodo"] = d["Año"].astype(str) + "-" + d["Mes"].map(numero_mes)
    if "Asesor" in d.columns:
        d["Periodo"] = d["Periodo"] + " · " + d["Asesor"]
    return d.sort_values("Periodo").reset_index(drop=True)

###############################################################################
#CATÁLOGO DE GRÁFICAS DEL ANÁLISIS UNIVARIADO
#Cada función regresa: (figura, pregunta, puntos clave)

#BARRAS HORIZONTALES: las 10 categorías más grandes
def g_barras(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(10)
    fig = px.bar(d.iloc[::-1], x=nombre, y="Categoría", orientation="h", text="Porcentaje")
    fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False,
                      marker_color=resaltar(d["Categoría"].iloc[::-1], [Datos["Categoría"].iloc[0]]))
    fig.update_yaxes(type="category", title="")
    fig.update_xaxes(range=[0, d[nombre].max() * 1.2])
    top3 = Datos["Porcentaje"].head(3).sum()
    return fig, "¿Cuáles son las más grandes?", [
        f"**{Datos['Categoría'].iloc[0]}** es la primera con **{Datos['Porcentaje'].iloc[0]}%**.",
        f"Las 3 primeras juntan **{top3:.0f}%** del total.",
        f"Hay **{len(Datos)}** categorías en total."]

#LOLLIPOP (paleta): como barras pero más limpio para nombres de personas
def g_lollipop(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(10).iloc[::-1]
    colores = resaltar(d["Categoría"], [Datos["Categoría"].iloc[0]])
    fig = px.scatter(d, x=nombre, y="Categoría", text=nombre)
    for (_, fila), color in zip(d.iterrows(), colores):
        fig.add_shape(type="line", x0=0, x1=fila[nombre], y0=fila["Categoría"], y1=fila["Categoría"],
                      line=dict(color=color, width=3), layer="below")
    fig.update_traces(marker=dict(size=16, color=colores, line=dict(color=SUPERFICIE, width=2)),
                      textposition="middle right", textfont_color=TINTA)
    fig.update_yaxes(type="category", title="")
    fig.update_xaxes(range=[0, d[nombre].max() * 1.2])
    lider, segundo = Datos.iloc[0], Datos.iloc[1]
    quienes = "personas" if variable in ("Asesor de piso", "Vendedor") else "canales"
    puntos = [f"**{lider['Categoría']}** lidera con **{lider[nombre]}** ventas ({lider['Porcentaje']}%).",
              f"Le sigue **{segundo['Categoría']}** con **{segundo[nombre]}**."]
    if len(Datos) > 10 and Datos["Porcentaje"].head(10).sum() < 99.5:
        puntos.append(f"El top 10 junta **{Datos['Porcentaje'].head(10).sum():.0f}%** de las ventas "
                      f"de {len(Datos)} {quienes}.")
    else:
        ceros = (Datos[nombre] == 0).sum()
        if ceros:
            puntos.append(f"**{ceros}** {quienes} no tuvieron ninguna venta.")
    pregunta = "¿Quiénes venden más?" if quienes == "personas" else "¿Qué canales venden más?"
    return fig, pregunta, puntos

#TREEMAP: cada cuadro es una categoría; su tamaño es lo que aporta
def g_treemap(df, Datos, nombre, columna, medida, variable):
    d = Datos.head(15)
    fig = px.treemap(d, path=[px.Constant("Total"), "Categoría"], values=nombre,
                     color=nombre, color_continuous_scale=ESCALA_ROJA)
    fig.update_traces(texttemplate="%{label}<br>%{value}", root_color=FONDO_APP,
                      marker_line=dict(color=SUPERFICIE, width=2))
    fig.update_layout(coloraxis_showscale=False)
    return fig, "¿Cuánto aporta cada uno?", [
        f"El cuadro más grande es **{Datos['Categoría'].iloc[0]}**: **{Datos['Porcentaje'].iloc[0]}%** del total.",
        f"Los 3 cuadros más grandes juntan **{Datos['Porcentaje'].head(3).sum():.0f}%**.",
        "Mientras más grande y oscuro el cuadro, más aporta."]

#DONA: pocas categorías
def g_dona(df, Datos, nombre, columna, medida, variable):
    Datos = Datos.copy()
    if variable == "Bono de marketing":
        Datos["Categoría"] = Datos["Categoría"].replace({"0": "Sin bono", "50000": "Con bono de $50,000"})
    fig = px.pie(Datos, names="Categoría", values=nombre, hole=0.5,
                 color_discrete_sequence=[ROJO, CARBON, GRIS])
    fig.update_traces(textinfo="label+percent", textfont_size=14, sort=False)
    fig.update_layout(showlegend=False)
    p = Datos.sort_values(nombre, ascending=False)
    if VARIABLES[variable][2] == "Numérica discreta":
        #Variables numéricas: hablamos de "registros" (meses), no de "parte del total"
        donde = "de los meses" if VARIABLES[variable][0] in ("TOPS_TDH", "Marketing") else "de los registros"
        puntos = [f"**{p['Categoría'].iloc[0]}** aparece en **{p['Porcentaje'].iloc[0]:.0f}%** {donde}."]
        if len(p) > 1:
            puntos.append(f"**{p['Categoría'].iloc[1]}** aparece en **{p['Porcentaje'].iloc[1]:.0f}%**.")
        pregunta = "¿Qué tan seguido aparece cada valor?"
    else:
        puntos = [f"**{p['Categoría'].iloc[0]}** ocupa **{p['Porcentaje'].iloc[0]}%** del total."]
        if len(p) > 1:
            puntos.append(f"Le sigue **{p['Categoría'].iloc[1]}** con **{p['Porcentaje'].iloc[1]}%**.")
        pregunta = "¿Qué parte del total es cada una?"
    return fig, pregunta, puntos

#DONA TOP 5 VS EL RESTO: muchas categorías
def g_top5(df, Datos, nombre, columna, medida, variable):
    resto = f"Las otras {len(Datos) - 5}"
    d = pd.DataFrame({"Grupo": ["Las 5 más grandes", resto],
                      "Valor": [Datos[nombre].head(5).sum(), Datos[nombre].iloc[5:].sum()]})
    fig = px.pie(d, names="Grupo", values="Valor", hole=0.5, color="Grupo",
                 color_discrete_map={"Las 5 más grandes": ROJO, resto: GRIS})
    fig.update_traces(textinfo="label+percent", textfont_size=14)
    fig.update_layout(showlegend=False)
    pct5 = Datos["Porcentaje"].head(5).sum()
    return fig, "¿Se concentra en pocas?", [
        f"Solo **5 de {len(Datos)}** juntan **{pct5:.0f}%** del total.",
        "Está **muy concentrado** en pocas." if pct5 >= 50 else "Está **repartido** entre muchas."]

#BARRA AL 100%: "de cada 100..."
def g_barra100(df, Datos, nombre, columna, medida, variable):
    d = Datos.copy()
    d["Total"] = "Ventas"
    fig = px.bar(d, x="Porcentaje", y="Total", color="Categoría", orientation="h", text="Categoría",
                 color_discrete_sequence=[ROJO, CARBON, GRIS_CLARO])
    fig.update_traces(texttemplate="%{text}<br>%{x:.0f}%", textposition="inside",
                      insidetextanchor="middle", textfont_size=16,
                      marker_line=dict(color=SUPERFICIE, width=2))
    #Texto blanco sobre colores oscuros y oscuro sobre el gris claro (contraste legible)
    for traza in fig.data:
        traza.insidetextfont = dict(color=TINTA if traza.marker.color == GRIS_CLARO else "white")
    fig.update_layout(showlegend=False, barmode="stack")
    fig.update_yaxes(visible=False)
    fig.update_xaxes(title="% de las ventas", range=[0, 100])
    partes = ", ".join(f"**{r['Porcentaje']:.0f}** de {r['Categoría']}" for _, r in d.iterrows())
    return fig, "De cada 100 ventas, ¿de dónde vienen?", [
        f"De cada 100 ventas: {partes}.",
        f"**{d['Categoría'].iloc[0]}** es el canal más fuerte, pero ninguno pasa de la mitad."]

#HISTOGRAMA: cuántas personas venden poco, regular o mucho
def g_histograma(df, Datos, nombre, columna, medida, variable):
    fig = px.histogram(Datos, x=nombre, nbins=10, color_discrete_sequence=[CARBON])
    fig.update_traces(marker_line_color="white", marker_line_width=2)
    fig.update_xaxes(title="Ventas totales por vendedor")
    fig.update_yaxes(title="Número de vendedores")
    mediana = Datos[nombre].median()
    altos = (Datos[nombre] >= 20).sum()
    return fig, "¿Cuántos vendedores venden poco y cuántos mucho?", [
        f"La mitad de los vendedores tiene **{mediana:.0f} ventas o menos** en total.",
        f"Solo **{altos} de {len(Datos)}** llegan a 20 ventas o más.",
        "Cada barra agrupa vendedores con ventas parecidas; la barra más alta es lo más común."]

#BARRAS VERTICALES: valores numéricos en orden 0, 1, 2...
def g_barras_v(df, Datos, nombre, columna, medida, variable):
    moda = Datos.sort_values(nombre, ascending=False)["Categoría"].iloc[0]
    fig = px.bar(Datos, x="Categoría", y=nombre, text="Porcentaje")
    fig.update_traces(texttemplate="%{text}%", textposition="outside", cliponaxis=False,
                      marker_color=resaltar(Datos["Categoría"], [moda]))
    fig.update_xaxes(type="category", title=variable)
    fig.update_yaxes(range=[0, Datos[nombre].max() * 1.2])
    p = Datos.sort_values(nombre, ascending=False).iloc[0]
    return fig, "¿Qué valor se repite más?", [
        f"El valor más común es **{p['Categoría']}** (**{p['Porcentaje']}%** de los registros).",
        f"Los valores van de **{Datos['Categoría'].iloc[0]}** a **{Datos['Categoría'].iloc[-1]}**."]

#DONA VENDIÓ / NO VENDIÓ
def g_vendio(df, Datos, nombre, columna, medida, variable):
    d = df[columna].apply(lambda v: "Vendió" if v > 0 else "No vendió").value_counts().reset_index()
    d.columns = ["Resultado", "Registros"]
    fig = px.pie(d, names="Resultado", values="Registros", hole=0.5, color="Resultado",
                 color_discrete_map={"Vendió": CARBON, "No vendió": ROJO})
    fig.update_traces(textinfo="label+percent", textfont_size=15)
    fig.update_layout(showlegend=False)
    sin = (df[columna] <= 0).mean() * 100
    return fig, "¿En cuántos meses hubo venta?", [
        f"En **{sin:.0f}%** de los registros no hubo ninguna venta.",
        f"Solo **{100 - sin:.0f} de cada 100** registros tienen al menos una venta."]

#VELOCÍMETRO: % de meses con al menos una venta
def g_gauge_venta(df, Datos, nombre, columna, medida, variable):
    pct = (df[columna] > 0).mean() * 100
    fig = go.Figure(go.Indicator(mode="gauge+number", value=pct, number={"suffix": "%"},
                                 gauge={"axis": {"range": [0, 100]}, "bar": {"color": ROJO}, "bgcolor": "#EEF0F3",
                                        "borderwidth": 0}))
    fig.update_traces(number_font=dict(color=TINTA, size=56))
    return fig, "¿Qué tan seguido vende un vendedor?", [
        f"Un vendedor cierra al menos una venta en **{pct:.0f}%** de sus meses.",
        f"En **{100 - pct:.0f}%** de los meses no vende nada.",
        "La aguja llena significaría que todos venden todos los meses."]

#VELOCÍMETRO DEL CLIMA LABORAL (escala de 1 a 5)
def g_gauge_clima(df, Datos, nombre, columna, medida, variable):
    prom = df[columna].mean()
    fig = go.Figure(go.Indicator(mode="gauge+number", value=prom, number={"valueformat": ".2f"},
                                 gauge={"axis": {"range": [0, 5]}, "bar": {"color": CARBON},
                                        "borderwidth": 0,
                                        #Zonas de lectura: bajo (rojo suave), medio, bueno (verde suave)
                                        "steps": [{"range": [0, 3], "color": "#F8D7DC"},
                                                  {"range": [3, 4], "color": "#EEF0F3"},
                                                  {"range": [4, 5], "color": "#D5EBDD"}]}))
    fig.update_traces(number_font=dict(color=TINTA, size=56))
    return fig, "¿Cómo está el clima laboral?", [
        f"El promedio es **{prom:.2f} de 5**: el equipo califica bien su ambiente de trabajo.",
        f"La calificación más baja fue **{df[columna].min()}** y la más alta **{df[columna].max()}**."]

#BOXPLOT: rango de un mes normal
def g_box(df, Datos, nombre, columna, medida, variable):
    fig = px.box(df, x=columna, points="all", hover_data=["Año", "Mes"], color_discrete_sequence=[CARBON])
    fig.update_xaxes(title=variable)
    q1, med, q3 = df[columna].quantile([0.25, 0.5, 0.75])
    peor = df.loc[df[columna].idxmax()]
    return fig, "¿Cuántos hay en un mes normal?", [
        f"En un mes normal hay **entre {como_texto(float(q1))} y {como_texto(float(q3))}** (la caja).",
        f"El valor de en medio es **{como_texto(float(med))}**.",
        f"El mes más alto fue **{peor['Mes']} {peor['Año']}** con **{como_texto(float(peor[columna]))}**."]

#VIOLÍN: forma de la distribución
def g_violin(df, Datos, nombre, columna, medida, variable):
    fig = px.violin(df, x=columna, box=True, points="all", hover_data=["Año", "Mes"],
                    color_discrete_sequence=[CARBON])
    fig.update_xaxes(title=variable)
    med = df[columna].median()
    return fig, "¿Dónde se concentran los meses?", [
        f"La mayoría de los meses tiene alrededor de **{como_texto(float(med))}**.",
        f"Va de **{como_texto(float(df[columna].min()))}** a **{como_texto(float(df[columna].max()))}** por mes.",
        "La parte más ancha de la figura es donde caen más meses."]

#LÍNEA MES A MES
def g_linea(df, Datos, nombre, columna, medida, variable):
    s = serie_mensual(df, columna, medida)
    fig = px.line(s, x="Mes del año", y="Valor", markers=True, color_discrete_sequence=[CARBON],
                  labels={"Valor": variable})
    fig.update_xaxes(type="category", title="")
    alto, bajo = s.loc[s["Valor"].idxmax()], s.loc[s["Valor"].idxmin()]
    #El punto más alto se marca en rojo (es el primer punto clave)
    fig.update_traces(line_width=2, marker=dict(size=9, line=dict(color=SUPERFICIE, width=2),
                      color=resaltar(s["Mes del año"], [alto["Mes del año"]], base=CARBON)))
    return fig, "¿Cómo se movió mes a mes?", [
        f"El punto más alto fue **{alto['Mes del año']}** con **{como_texto(float(alto['Valor']))}**.",
        f"El más bajo fue **{bajo['Mes del año']}** con **{como_texto(float(bajo['Valor']))}**.",
        f"Empezó en **{como_texto(float(s['Valor'].iloc[0]))}** y terminó en "
        f"**{como_texto(float(s['Valor'].iloc[-1]))}**."]

#BARRAS POR MES: en qué meses hubo bono
def g_bono_mes(df, Datos, nombre, columna, medida, variable):
    s = serie_mensual(df, columna, None)
    s["Bono"] = s["Valor"].apply(lambda v: "Con bono" if v > 0 else "Sin bono")
    s["Altura"] = 1
    fig = px.bar(s, x="Mes del año", y="Altura", color="Bono",
                 color_discrete_map={"Con bono": ROJO, "Sin bono": GRIS_CLARO})
    fig.update_xaxes(type="category", title="")
    fig.update_yaxes(visible=False)
    fig.update_layout(legend_title="", legend=dict(orientation="h", y=-0.3, x=0), bargap=0.1)
    con = s[s["Bono"] == "Con bono"]
    puntos = [f"Hubo bono en **{len(con)} de {len(s)}** meses."]
    if len(con):
        puntos.append(f"El primer bono llegó en **{con['Mes del año'].iloc[0]}**; antes nunca hubo.")
    return fig, "¿En qué meses hubo bono?", puntos

#Qué dos gráficas lleva cada variable
GRAFICAS = {
    "Canal (Funnel)":            [g_treemap, g_lollipop],
    "Campaña digital":           [g_barras, g_top5],
    "Canal principal":           [g_barra100, g_dona],
    "Asesor de piso":            [g_lollipop, g_top5],
    "Vendedor":                  [g_treemap, g_histograma],
    "Ventas por asesor de piso": [g_barras_v, g_vendio],
    "Ventas por vendedor":       [g_barras_v, g_gauge_venta],
    "Bono de marketing":         [g_dona, g_bono_mes],
    "Bajas de personal":         [g_barras_v, g_linea],
    "Vacantes":                  [g_box, g_linea],
    "APVS Oro":                  [g_dona, g_linea],
    "APVS Plata":                [g_barras_v, g_box],
    "APVS Bronce":               [g_violin, g_linea],
    "Clima laboral":             [g_gauge_clima, g_dona],
}

###############################################################################
#CREACIÓN DEL DASHBOARD
#Generamos los encabezados para la barra lateral (sidebar)
aplicar_estilos()
#Si el equipo guarda el logo como logo_gac.png junto a app.py, aparece aquí
if os.path.exists(LOGO):
    st.sidebar.image(LOGO, width=200)
else:
    st.sidebar.title("GAC MOTOR")

#Widget 0: Radio para elegir la etapa del proyecto
Etapa = st.sidebar.radio("Etapa", ["Etapa I · Extracción de características",
                                   "Etapa II · Modelado predictivo",
                                   "Etapa III · Clasificación"])
#Widget 1: Selectbox
#Menu desplegable de las vistas de cada etapa
if Etapa.startswith("Etapa I ·"):
    View = st.sidebar.selectbox(label="Vista", options=["Hallazgos principales",
                                                        "Análisis univariado",
                                                        "Comparación por periodo"])
elif Etapa.startswith("Etapa II ·"):
    View = st.sidebar.selectbox(label="Vista", options=["Resumen de modelos (todas las bases)",
                                                        "a) Análisis de correlaciones",
                                                        "Regresión lineal simple",
                                                        "Regresión lineal múltiple"])
else:
    View = st.sidebar.selectbox(label="Vista", options=["Resumen de clasificación (todas las bases)",
                                                        "a) Análisis de clasificación"])

###############################################################################
# CONTENIDO DE LA VISTA 1: HALLAZGOS PRINCIPALES
if View == "Hallazgos principales":
    st.title("Hallazgos principales")
    st.write("Las cinco respuestas más importantes que salen de las 15 variables. "
             "Para ver cualquier variable a detalle, elige **Análisis univariado** en el menú.")
    st.divider()

    #HALLAZGO 1: ventas por canal principal
    Canales, _ = frecuencias(bases["Principales_Canales"], "Canal", "Ventas", "Categórica")
    figure1 = px.pie(Canales, names="Categoría", values="Ventas", hole=0.5,
                     color_discrete_sequence=[ROJO, CARBON, GRIS])
    figure1.update_traces(textinfo="label+percent", textfont_size=15, sort=False)
    figure1.update_layout(showlegend=False)
    seccion("1. ¿Por dónde llegan las ventas?", figure1, [
        f"**{Canales['Categoría'].iloc[0]}** es el canal que más vende: "
        f"**{Canales['Porcentaje'].iloc[0]:.0f}%** de {Canales['Ventas'].sum():,} ventas.",
        f"**{Canales['Categoría'].iloc[1]}** sigue con **{Canales['Porcentaje'].iloc[1]:.0f}%**.",
        "Ningún canal pasa de la mitad: las ventas están repartidas."])

    #HALLAZGO 2: embudo de venta
    Embudo = datos_embudo(preparar(bases["Funnel"], "Indicador del embudo"))
    citas = Embudo["Real"].iloc[0]
    ventas = Embudo.loc[Embudo["Indicador"] == "Ventas", "Real"].iloc[0]
    fuga = Embudo.iloc[1:].sort_values("Pasa").iloc[0]
    figure2 = px.funnel(Embudo, x="Real", y="Indicador")
    figure2.update_traces(textinfo="value", textfont_color="white",
                          marker_color=resaltar(Embudo["Indicador"], [fuga["Indicador"]], base=CARBON))
    figure2.update_yaxes(title="")
    seccion("2. ¿Cuántos clientes llegan hasta la venta?", figure2, [
        f"De **{citas:,}** citas se cierran **{ventas:,}** ventas.",
        f"**{ventas / citas * 100:.0f} de cada 100** citas terminan en venta.",
        f"La mayor pérdida es al llegar a **{fuga['Indicador']}**: solo pasa el **{fuga['Pasa']:.0f}%**."])

    #HALLAZGO 3: campañas que traen más leads
    Campanas, _ = frecuencias(bases["MKT_Digital"], "Campaña", "Leads", "Categórica")
    Top5 = Campanas.head(5)
    figure3 = px.bar(Top5.iloc[::-1], x="Leads", y="Categoría", orientation="h", text="Leads")
    figure3.update_traces(textposition="outside", cliponaxis=False,
                          marker_color=resaltar(Top5["Categoría"].iloc[::-1], [Top5["Categoría"].iloc[0]]))
    figure3.update_yaxes(title="")
    figure3.update_xaxes(range=[0, Top5["Leads"].max() * 1.2])
    seccion("3. ¿Qué campañas digitales traen más leads?", figure3, [
        f"Las 5 campañas juntan **{Top5['Porcentaje'].sum():.0f}%** de los leads.",
        f"**{Top5['Categoría'].iloc[0]}** trae sola el **{Top5['Porcentaje'].iloc[0]:.0f}%**.",
        "Las campañas de WhatsApp dominan el top."])

    #HALLAZGO 4: vendedores con y sin venta en el mes
    Vendedores = bases["Ventas_por_Asesor"]
    figure4, _, _ = g_vendio(Vendedores, None, None, "Ventas", None, "")
    sin_venta = (Vendedores["Ventas"] <= 0).mean() * 100
    seccion("4. ¿Los vendedores venden cada mes?", figure4, [
        f"En **{sin_venta:.0f}%** de los meses el vendedor no cerró ninguna venta.",
        "Las ventas dependen de pocos vendedores."])

    #HALLAZGO 5: nivel de los asesores (personal)
    Niveles = pd.DataFrame({
        "Nivel": ["Oro", "Plata", "Bronce"],
        "Asesores al mes": [bases["TOPS_TDH"]["APVS_Oro"].mean(),
                            bases["TOPS_TDH"]["APVS_Plata"].mean(),
                            bases["TOPS_TDH"]["APVS_Bronce"].mean()]}).round(1)
    figure5 = px.bar(Niveles, x="Nivel", y="Asesores al mes", text="Asesores al mes",
                     color="Nivel", color_discrete_map=METALES)
    figure5.update_traces(textposition="outside", cliponaxis=False)
    figure5.update_layout(showlegend=False)
    figure5.update_yaxes(range=[0, Niveles["Asesores al mes"].max() * 1.25])
    seccion("5. ¿Qué nivel tienen los asesores?", figure5, [
        f"En un mes promedio hay **{Niveles['Asesores al mes'].iloc[2]:.0f} Bronce** y solo "
        f"**{Niveles['Asesores al mes'].iloc[0]:.0f} Oro**.",
        "La mayoría del equipo está en el nivel más bajo."])

    st.caption("El conjunto incluye 6 variables categóricas y 9 numéricas discretas. "
               "Confirmen con el profesor si las 15 deben ser estrictamente categóricas.")

###############################################################################
# FILTROS DE LAS VISTAS 2 Y 3 (en la barra lateral)
elif View in ("Análisis univariado", "Comparación por periodo"):
    #Separamos visualmente la vista de los filtros
    st.sidebar.divider()
    #Widget 2: Selectbox de base de datos
    Base = st.sidebar.selectbox(label="Base de datos",
                                options=sorted({b for b, _, _, _ in VARIABLES.values()}))
    #Widget 3: Selectbox de variable (solo las de la base elegida)
    Variable_Cat = st.sidebar.selectbox(label="Variable",
                                        options=[v for v, d in VARIABLES.items() if d[0] == Base])
    _, columna, tipo, medida = VARIABLES[Variable_Cat]

    #Widget 4 y 5: años y meses (solo los que existen en la base elegida)
    df = bases[Base]
    anios = sorted(df["Año"].unique())
    Anio_sel = st.sidebar.multiselect("Año", options=anios, default=anios)
    meses = [m for m in MESES if m in df.loc[df["Año"].isin(Anio_sel), "Mes"].unique()]
    Mes_sel = st.sidebar.multiselect("Mes", options=meses, default=meses)
    df = df[df["Año"].isin(Anio_sel) & df["Mes"].isin(Mes_sel)]
    df = preparar(df, Variable_Cat)

    if df.empty:
        st.warning("No hay datos con esos filtros. Elige al menos un año y un mes.")
        st.stop()

    #Frecuencias de la variable seleccionada (se usan en las gráficas)
    Datos, nombre = frecuencias(df, columna, medida, tipo, Variable_Cat)
    Principal = Datos.sort_values(nombre, ascending=False).iloc[0]

    ###########################################################################
    # CONTENIDO DE LA VISTA 2: ANÁLISIS UNIVARIADO
    if View == "Análisis univariado":
        st.title(Variable_Cat)

        #-------------------------------------------------------------------
        #CASO ESPECIAL: INDICADOR DEL EMBUDO
        if Variable_Cat == "Indicador del embudo":
            st.write("Cuántos clientes avanzan en cada paso del proceso de venta, "
                     "desde que agendan una cita hasta que se formaliza la compra.")
            st.divider()
            Embudo = datos_embudo(df)
            fuga = Embudo.iloc[1:].sort_values("Pasa").iloc[0]
            anterior = ETAPAS[ETAPAS.index(fuga["Indicador"]) - 1]
            citas = Embudo["Real"].iloc[0]
            ventas = Embudo.loc[Embudo["Indicador"] == "Ventas", "Real"].iloc[0]

            #GRAPH 1: EMBUDO (FUNNEL)
            figure1 = px.funnel(Embudo, x="Real", y="Indicador")
            figure1.update_traces(textinfo="value+percent previous", textfont_color="white",
                                  marker_color=resaltar(Embudo["Indicador"], [fuga["Indicador"]], base=CARBON))
            figure1.update_yaxes(title="")
            seccion("¿Cuántos clientes llegan a cada paso?", figure1, [
                f"De **{citas:,}** citas se cierran **{ventas:,}** ventas "
                f"(**{ventas / max(citas, 1) * 100:.0f} de cada 100**).",
                f"La mayor pérdida: de **{anterior}** a **{fuga['Indicador']}** solo pasa el "
                f"**{fuga['Pasa']:.0f}%**.",
                "El % de cada barra es cuántos avanzaron desde el paso anterior."])

            #GRAPH 2: CUMPLIMIENTO DEL OBJETIVO POR ETAPA
            Embudo["Estado"] = Embudo["Cumplimiento"].apply(
                lambda c: "Cumple la meta" if c >= 100 else "No cumple la meta")
            figure2 = px.bar(Embudo.iloc[::-1], x="Cumplimiento", y="Indicador", orientation="h",
                             text="Cumplimiento", color="Estado",
                             color_discrete_map={"Cumple la meta": VERDE, "No cumple la meta": ROJO})
            figure2.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
            figure2.add_vline(x=100, line_dash="dash", line_color=TINTA, line_width=1.5,  #Meta = 100%
                              annotation_text="Meta", annotation_position="top",
                              annotation_font_color=TINTA)
            figure2.update_yaxes(title="")
            figure2.update_xaxes(title="Cumplimiento (%)",
                                 range=[0, max(Embudo["Cumplimiento"].max(), 100) * 1.2])
            figure2.update_layout(legend_title="", legend=dict(orientation="h", y=-0.2, x=0))
            peor = Embudo.sort_values("Cumplimiento").iloc[0]
            cumplen = (Embudo["Cumplimiento"] >= 100).sum()
            seccion("¿Qué pasos alcanzan su meta?", figure2, [
                f"Solo **{cumplen} de {len(Embudo)}** pasos llegan a su meta (línea punteada).",
                f"El más lejos es **{peor['Indicador']}**, con **{peor['Cumplimiento']:.0f}%**.",
                "Los primeros pasos cumplen; el problema está al final del proceso."])

            st.caption("Nota: no se incluyen Leads generados ni Leads efectivos porque vienen rellenados "
                       "con la media (83.06 se repite en varios meses), ni Cerrador (solo aparece un mes).")

        #-------------------------------------------------------------------
        #RESTO DE LAS VARIABLES: cada una con sus dos gráficas del catálogo
        else:
            if Variable_Cat == "Canal (Funnel)":
                st.write("Ventas de cada canal. Se quitó GAC Angelopolis porque es el total de la agencia.")
            elif tipo == "Numérica discreta":
                st.write(f"Cómo se reparten los valores de **{Variable_Cat}** en la base {Base}.")
            else:
                st.write(f"Cuánto aporta cada categoría al total de **{nombre.lower()}** en la base {Base}.")

            #Fila de tarjetas (solo 3)
            Contenedor_A, Contenedor_B, Contenedor_C = st.columns(3)
            Contenedor_A.metric("Número de categorías", len(Datos))
            Contenedor_B.metric("Valor más común" if tipo == "Numérica discreta" else "La más grande",
                                Principal["Categoría"])
            Contenedor_C.metric("Su parte del total", f"{Principal['Porcentaje']}%")
            st.divider()

            #GRAPH 1 y GRAPH 2: las que le tocan a esta variable
            usadas = []
            for grafica in GRAFICAS[Variable_Cat]:
                #Si una gráfica necesita más categorías de las que dejan los filtros, usamos barras
                if grafica in (g_top5, g_lollipop) and len(Datos) <= 5:
                    grafica = g_barras
                if grafica in (g_box, g_violin, g_linea) and len(df) < 3:
                    grafica = g_barras_v
                if grafica in usadas:  #No repetir la misma gráfica dos veces
                    continue
                usadas.append(grafica)
                figura, pregunta, puntos = grafica(df, Datos, nombre, columna, medida, Variable_Cat)
                seccion(pregunta, figura, puntos)

            #Notas que solo aparecen cuando aplican
            if columna == "Ventas" and not medida:
                st.caption("Nota: los valores con decimales (0.18 y 0.53) vienen así en la base limpia; "
                           "son promedios usados para rellenar datos faltantes, no ventas reales.")
            if Base == "TOPS_TDH":
                st.caption("Nota: TOPS_TDH tiene un registro por mes (19 en total); tómalo como referencia, "
                           "no como tendencia firme.")

    ###########################################################################
    # CONTENIDO DE LA VISTA 3: COMPARACIÓN POR PERIODO
    elif View == "Comparación por periodo":
        st.title(f"{Variable_Cat}: cambio en el tiempo")
        st.write("Compara cómo cambia la variable de un periodo a otro.")

        #Widget 6: Radio para comparar por año o por mes
        Periodo = st.radio("Comparar por", ["Año", "Mes"], horizontal=True)
        st.divider()
        datos = df.copy()
        #Año-mes para no juntar, por ejemplo, febrero 2024 con febrero 2025
        numero_mes = {m: f"{i:02d}" for i, m in enumerate(MESES, 1)}
        datos["AñoMes"] = datos["Año"].astype(str) + "-" + datos["Mes"].map(numero_mes)
        datos["Categoría"] = datos[columna].apply(como_texto)
        datos["Valor"] = datos[medida] if medida else 1
        #Primero sumamos cada categoría por mes (un renglón por categoría y mes)
        datos = datos.groupby(["Año", "AñoMes", "Categoría"], as_index=False)["Valor"].sum()
        if Periodo == "Año":
            #Los años no tienen los mismos meses (2026 llega solo a medio año), así que
            #comparamos el PROMEDIO POR MES de cada año y no el total
            meses_por_anio = datos.groupby("Año")["AñoMes"].nunique()
            datos = datos.groupby(["Año", "Categoría"], as_index=False)["Valor"].sum()
            datos["Valor"] = (datos["Valor"] / datos["Año"].map(meses_por_anio)).round(1)
            datos["Periodo"] = datos["Año"].astype(str)
            etiqueta = f"{nombre} (promedio por mes)"
            st.caption("Por año se compara el promedio por mes, porque no todos los años tienen "
                       "los mismos meses: " + ", ".join(f"{a} tiene {n} meses"
                                                       for a, n in meses_por_anio.items()) + ".")
        else:
            datos["Periodo"] = datos["AñoMes"]
            etiqueta = nombre
        #Formato de los números: con un decimal si son promedios
        fmt = ",.1f" if Periodo == "Año" else ",.0f"

        #Categorías a mostrar: etapas en orden para el embudo; las 8 más grandes para lo demás
        if Variable_Cat == "Indicador del embudo":
            top8 = [e for e in ETAPAS if e in set(datos["Categoría"])]
        else:
            top8 = list(Datos.sort_values(nombre, ascending=False).head(8)["Categoría"])

        #GRAPH 3: BARRAS de una categoría en cada periodo
        #Widget 7: elegir una categoría para ver cómo cambia
        Categoria_sel = st.selectbox("Elige una categoría", options=top8)
        Serie = (datos[datos["Categoría"] == Categoria_sel]
                 .groupby("Periodo")["Valor"].sum().reset_index())
        figure3 = px.bar(Serie, x="Periodo", y="Valor", text="Valor", labels={"Valor": etiqueta})
        #El periodo más alto en rojo; el resto en carbón
        pico = Serie.loc[Serie["Valor"].idxmax(), "Periodo"]
        figure3.update_traces(texttemplate="%{text:" + fmt + "}", textposition="outside", cliponaxis=False,
                              marker_color=resaltar(Serie["Periodo"], [pico], base=CARBON))
        figure3.update_xaxes(type="category")
        figure3.update_yaxes(range=[0, max(Serie["Valor"].max(), 1) * 1.2])
        puntos = []
        if len(Serie) > 1 and Serie["Valor"].iloc[0] > 0:
            cambio = (Serie["Valor"].iloc[-1] / Serie["Valor"].iloc[0] - 1) * 100
            puntos.append(f"De {Serie['Periodo'].iloc[0]} a {Serie['Periodo'].iloc[-1]} "
                          f"{'subió' if cambio >= 0 else 'bajó'} **{abs(cambio):.0f}%**.")
        alto = Serie.loc[Serie["Valor"].idxmax()]
        puntos.append(f"El periodo más alto fue **{alto['Periodo']}** con **{alto['Valor']:{fmt}}**.")
        if len(Serie) > 2:
            bajo = Serie.loc[Serie["Valor"].idxmin()]
            puntos.append(f"El más bajo fue **{bajo['Periodo']}** con **{bajo['Valor']:{fmt}}**.")
        seccion(f"¿Cómo cambió {Categoria_sel}?", figure3, puntos)

        #GRAPH 4: HEATMAP (categorías principales x periodo)
        Heat = datos.pivot_table(index="Categoría", columns="Periodo", values="Valor",
                                 aggfunc="sum", fill_value=0)
        Heat = Heat.reindex(top8, fill_value=0)
        figure4 = px.imshow(Heat, text_auto=fmt.replace(",", ""), aspect="auto", color_continuous_scale=ESCALA_ROJA,
                            labels={"color": etiqueta, "x": "Periodo", "y": ""})
        figure4.update_xaxes(type="category")
        mejor = Heat.stack().idxmax()
        #Categoría que más creció entre el primer y el último periodo
        puntos = [f"El cuadro más oscuro es **{mejor[0]}** en **{mejor[1]}**."]
        if Heat.shape[1] > 1:
            crecimiento = (Heat.iloc[:, -1] - Heat.iloc[:, 0])
            puntos.append(f"La que más creció fue **{crecimiento.idxmax()}** y la que más bajó "
                          f"**{crecimiento.idxmin()}**.")
        puntos.append("Lee cada fila de izquierda a derecha: si se oscurece, va subiendo.")
        seccion("Mapa de calor: todas las categorías a la vez", figure4, puntos)

###############################################################################
# ETAPA II: MODELADO PREDICTIVO (resumen, correlaciones, regresión simple y múltiple)
elif View == "Resumen de modelos (todas las bases)":
    #Corre una regresión simple y una múltiple en CADA base para comparar de un vistazo
    st.title("Etapa II · Resumen de modelos")
    st.write("Para cada base se predice su variable principal con la **mejor regresión lineal simple** "
             "(la X con mayor R²) y con una **regresión lineal múltiple**. Para ver cada modelo a detalle, "
             "elige *Regresión lineal simple* o *Regresión lineal múltiple* en el menú.")
    st.divider()
    filas = []
    for nombre_b, clave in BASES_REG.items():
        canal_b = "GAC Angelopolis" if clave == "Funnel" else ("Todos (suma)" if clave == "Principales_Canales" else None)
        t = tabla_regresion(clave, canal_b)
        nums = [c for c in t.select_dtypes("number").columns if c != "Año" and t[c].nunique() > 1]
        y_b = next((p for p in ["Ventas", "Real", "Productividad_APVS"] if p in nums), nums[0])
        cand = [c for c in nums if c != y_b]
        cy = t[cand].corrwith(t[y_b]).dropna()
        cy = cy.reindex(cy.abs().sort_values(ascending=False).index)
        simples = {c: ols(t, y_b, [c]) for c in cand}
        simples = {c: m for c, m in simples.items() if m}
        x_mejor = max(simples, key=lambda c: simples[c]["r2"])
        xs_b = [x for x in DEFAULT_XS.get(clave, []) if x in cand] or list(cy.index[:3])
        mm = ols(t, y_b, xs_b) if len(xs_b) >= 2 else None
        filas.append({"Base": nombre_b, "Y (a predecir)": bonito(y_b),
                      "Mejor X (simple)": bonito(x_mejor), "R² simple": simples[x_mejor]["r2"],
                      "X del modelo múltiple": ", ".join(bonito(x) for x in xs_b) if mm else "— (solo hay 1 X)",
                      "R² múltiple": mm["r2"] if mm else np.nan,
                      "R² ajustado": mm["r2a"] if mm else np.nan,
                      "n": simples[x_mejor]["n"]})
    Resumen = pd.DataFrame(filas)

    #GRAPH E2-1: BARRAS R² simple vs múltiple por base
    Larga = Resumen.melt(id_vars="Base", value_vars=["R² simple", "R² múltiple"],
                         var_name="Modelo", value_name="R²").dropna()
    figE1 = px.bar(Larga, x="R²", y="Base", color="Modelo", barmode="group", orientation="h",
                   text="R²", color_discrete_map={"R² simple": GRIS, "R² múltiple": ROJO})
    figE1.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
    figE1.update_xaxes(range=[0, 1.15])
    figE1.update_yaxes(title="", categoryorder="array", categoryarray=list(Resumen["Base"])[::-1])
    figE1.update_layout(legend_title="", legend=dict(orientation="h", y=-0.12, x=0))
    mejor_b = Resumen.sort_values("R² múltiple", ascending=False).iloc[0]
    seccion("¿Qué tan bien se puede predecir cada base?", figE1, [
        f"El modelo más fuerte es **{mejor_b['Base']}**: explica **{mejor_b['R² múltiple'] * 100:.0f}%** "
        f"de {mejor_b['Y (a predecir)']}.",
        "En casi todas las bases el modelo múltiple (rojo) supera a la mejor X sola (gris).",
        "R² = qué parte de los cambios de Y explica el modelo (0 = nada, 1 = todo)."], alto=560)

    #GRAPH E2-2: TABLA con el detalle de cada modelo
    with st.container(border=True, key="seccion_resumen_modelos"):
        st.subheader("Detalle de los modelos por base")
        st.dataframe(Resumen, hide_index=True, width="stretch",
                     column_config={c: st.column_config.ProgressColumn(c, min_value=0, max_value=1, format="%.2f")
                                    for c in ["R² simple", "R² múltiple"]}
                     | {"R² ajustado": st.column_config.NumberColumn(format="%.2f")})
        st.caption("Funnel usa el canal GAC Angelopolis (total) y Principales canales la suma de los 3 canales. "
                   "Análisis de piso solo tiene una X (Leads), por eso no tiene modelo múltiple.")

elif Etapa.startswith("Etapa II ·"):
    st.sidebar.divider()
    #Widget R1: base de datos para el modelo
    Base_Nombre = st.sidebar.selectbox("Base de datos", options=list(BASES_REG))
    Base_R = BASES_REG[Base_Nombre]

    #Widget R2: filtro de canal (solo en las bases que tienen canal)
    Canal_R = None
    if Base_R == "Principales_Canales":
        Canal_R = st.sidebar.selectbox("Canal", ["Todos (suma)"] + sorted(bases[Base_R]["Canal"].unique()))
    elif Base_R == "Funnel":
        canales_f = sorted(bases["Funnel"]["Canal"].unique())
        Canal_R = st.sidebar.selectbox("Canal", canales_f, index=canales_f.index("GAC Angelopolis"))

    datos_r = tabla_regresion(Base_R, Canal_R)

    #Widget R3: años incluidos en el modelo
    anios_r = sorted(datos_r["Año"].unique())
    Anio_r = st.sidebar.multiselect("Año", options=anios_r, default=anios_r)
    datos_r = datos_r[datos_r["Año"].isin(Anio_r)]

    #Solo variables numéricas que cambian (una constante no explica nada)
    numericas = [c for c in datos_r.select_dtypes("number").columns
                 if c != "Año" and datos_r[c].nunique() > 1]
    if len(datos_r) < 5 or len(numericas) < 2:
        st.title(View.replace("a) ", ""))
        st.warning("Con estos filtros quedan muy pocos datos para ajustar un modelo. Agrega más años.")
        st.stop()

    #Widget R4: variable a predecir (Y)
    #En correlaciones va en la barra lateral; en las regresiones va junto a la gráfica principal
    preferidas = ["Ventas", "Real", "Productividad_APVS"]
    y_default = next((p for p in preferidas if p in numericas), numericas[0])
    clave_y = f"y_{Base_R}_{Canal_R}"
    if clave_y not in st.session_state or st.session_state[clave_y] not in numericas:
        st.session_state[clave_y] = y_default

    st.title(View.replace("a) ", ""))
    st.write(f"Base: **{Base_Nombre}**" + (f" · Canal: **{Canal_R}**" if Canal_R else "")
             + f" · {len(datos_r)} registros.")

    if View == "a) Análisis de correlaciones":
        Y = st.sidebar.selectbox("Variable a predecir (Y)", numericas, format_func=bonito, key=clave_y)
    elif View in ("Regresión lineal simple", "Regresión lineal múltiple"):
        #Tarjeta principal, en este orden: 1) KPIs en fila, 2) gráfica, 3) selectores de Y y X, 4) puntos clave
        Caja_Principal = st.container(border=True, key="seccion_modelo_principal")
        with Caja_Principal:
            Zona_KPI = st.container()
            Col_Graf = st.container()
            Col_Ctrl = st.container()
            with Col_Ctrl:
                st.markdown('<div class="puntos-titulo">Variables del modelo</div>', unsafe_allow_html=True)
                Col_Y, Col_X = st.columns([1, 2], gap="large")
        with Col_Y:
            Y = st.selectbox("Variable a predecir (Y)", numericas, format_func=bonito, key=clave_y)
    candidatas = [c for c in numericas if c != Y]
    #Correlación de cada candidata con Y, de la más fuerte a la más débil
    corr_y = datos_r[candidatas].corrwith(datos_r[Y]).dropna()
    corr_y = corr_y.reindex(corr_y.abs().sort_values(ascending=False).index)


    #-------------------------------------------------------------------------
    #VISTA E2-1: CORRELACIONES
    if View == "a) Análisis de correlaciones":
        #GRAPH R1: MAPA DE CALOR de correlaciones (rojo = se mueven juntas, carbón = al revés)
        #Widget R5: elegir qué variables entran al mapa (por defecto Y + las 9 más relacionadas)
        def elegir_variables():
            st.multiselect("Variables del mapa de calor (Y siempre se incluye)", candidatas,
                           format_func=bonito, key=f"heat_{Base_R}_{Canal_R}_{Y}")
        st.session_state.setdefault(f"heat_{Base_R}_{Canal_R}_{Y}", list(corr_y.index[:9]))
        en_mapa = [Y] + [c for c in st.session_state[f"heat_{Base_R}_{Canal_R}_{Y}"] if c != Y]
        Matriz = datos_r[en_mapa].corr().round(2)
        Matriz.index = Matriz.columns = [bonito(c) for c in Matriz.columns]
        #Solo la mitad de abajo: la de arriba es el espejo y repetirla amontona el mapa
        mascara = np.triu(np.ones(Matriz.shape, dtype=bool), k=1)
        Matriz = Matriz.mask(mascara)
        figR1 = px.imshow(Matriz, aspect="auto", zmin=-1, zmax=1,
                          color_continuous_scale=[CARBON, "#FFFFFF", ROJO])
        figR1.update_traces(text=Matriz.map(lambda v: "" if pd.isna(v) else f"{v:.2f}").values,
                            texttemplate="%{text}", textfont_size=13 if len(en_mapa) <= 12 else 10,
                            hovertemplate="%{y} vs %{x}<br>r = %{z:.2f}<extra></extra>")
        figR1.update_xaxes(tickangle=-40, side="bottom", showgrid=False)
        figR1.update_yaxes(showgrid=False)
        figR1.update_layout(coloraxis_colorbar=dict(title="r", thickness=14))
        mas = corr_y.index[0]
        seccion("¿Qué variables se mueven juntas?", figR1, [
            f"La variable más relacionada con **{bonito(Y)}** es **{bonito(mas)}** (r = **{corr_y.iloc[0]:.2f}**).",
            "Rojo intenso: cuando una sube, la otra también.\n\n- Carbón: cuando una sube, la otra baja.",
            "Blanco: casi no hay relación.\n\n- Correlación no significa que una cause la otra."],
            alto=max(480, 48 * len(en_mapa) + 160), abajo=True, antes=elegir_variables)

        #GRAPH R2: BARRAS con la correlación de cada variable contra Y
        top_c = corr_y.head(12).iloc[::-1]
        figR2 = px.bar(x=top_c.values, y=[bonito(c) for c in top_c.index], orientation="h",
                       text=[f"{v:.2f}" for v in top_c.values], labels={"x": f"Correlación con {bonito(Y)}", "y": ""})
        figR2.update_traces(textposition="outside", cliponaxis=False,
                            marker_color=[ROJO if abs(v) >= 0.7 else GRIS for v in top_c.values])
        figR2.update_xaxes(range=[min(0, top_c.min()) * 1.2 - 0.05, 1.15])
        fuertes = (corr_y.abs() >= 0.7).sum()
        seccion(f"¿Qué tan fuerte se relaciona cada variable con {bonito(Y)}?", figR2, [
            f"**{fuertes}** variables tienen relación **fuerte** (|r| ≥ 0.7, en rojo).",
            f"La más débil es **{bonito(corr_y.index[-1])}** (r = {corr_y.iloc[-1]:.2f}).",
            "Las barras rojas son las mejores candidatas para la regresión."])

    #-------------------------------------------------------------------------
    #VISTA E2-2: REGRESIÓN LINEAL SIMPLE (una X)
    if View == "Regresión lineal simple":
        x_def = DEFAULT_X.get(Base_R)
        x_def = x_def if x_def in candidatas else corr_y.index[0]
        with Col_X:
            #Widget R6: variable explicativa (X), debajo de la gráfica para ver el cambio al instante
            X1 = st.selectbox("Variable explicativa (X)", candidatas, index=candidatas.index(x_def),
                              format_func=bonito, key=f"x_simple_{Base_R}_{Canal_R}_{Y}")
        M = ols(datos_r, Y, [X1])
        b0, b1 = M["beta"]
        r = M["d"][[X1, Y]].corr().iloc[0, 1]
        with Zona_KPI:  #KPIs en fila horizontal arriba de la gráfica
            K1, K2, K3, K4 = st.columns(4)
            K1.metric("Correlación (r)", f"{r:.2f}", fuerza(r), delta_color="off")
            K2.metric("R²", f"{M['r2']:.2f}", f"explica {M['r2'] * 100:.0f}% de {bonito(Y)}", delta_color="off")
            K3.metric("Pendiente (b₁)", num(b1))
            K4.metric("Datos usados (n)", M["n"])

        #GRAPH R3: DISPERSIÓN REAL + RECTA + DISPERSIÓN DE LOS DATOS PREDICHOS
        d = M["d"]
        figR3 = go.Figure()
        figR3.add_trace(lineas_error(d[X1], d[Y], M["pred"]))
        figR3.add_scatter(x=d[X1], y=d[Y], mode="markers", name="Datos reales",
                          marker=dict(color=CARBON, size=10, opacity=0.8, line=dict(color=SUPERFICIE, width=1)),
                          customdata=d["Periodo"], hovertemplate="%{customdata}<br>X: %{x}<br>Real: %{y}<extra></extra>")
        xs = np.linspace(d[X1].min(), d[X1].max(), 50)
        figR3.add_scatter(x=xs, y=b0 + b1 * xs, mode="lines", name="Recta de regresión",
                          line=dict(color=ROJO, width=3), hoverinfo="skip")
        figR3.add_scatter(x=d[X1], y=M["pred"], mode="markers", name="Datos predichos",
                          marker=dict(color=ROJO, symbol="diamond", size=9, line=dict(color=SUPERFICIE, width=1)),
                          customdata=d["Periodo"], hovertemplate="%{customdata}<br>X: %{x}<br>Predicho: %{y:.1f}<extra></extra>")
        figR3.update_xaxes(title=bonito(X1))
        figR3.update_yaxes(title=bonito(Y))
        figR3.update_layout(legend=dict(orientation="h", y=-0.18, x=0))
        with Col_Graf:
            st.subheader(f"¿Cómo predice {bonito(X1)} a {bonito(Y)}?")
            dibujar(figR3, 480, "graf_simple")
        with Caja_Principal:
            puntos_en_fila([
                f"Por cada **1** de {bonito(X1)} más, {bonito(Y)} {'sube' if b1 >= 0 else 'baja'} en promedio **{num(abs(b1))}**.",
                f"La relación es **{fuerza(r).lower()}**: el modelo explica **{M['r2'] * 100:.0f}%** de los cambios.",
                f"La pendiente {'sí' if M['p'][1] < 0.05 else 'no'} es significativa (p = {M['p'][1]:.3f})."])

        #GRAPH R4: TABLA con todas las regresiones simples posibles (ranking por R²)
        filas = []
        for c in candidatas:
            m_c = ols(datos_r, Y, [c])
            if m_c:
                filas.append({"Variable X": bonito(c), "R²": m_c["r2"], "Pendiente": m_c["beta"][1],
                              "p-valor": m_c["p"][1], "n": m_c["n"]})
        Ranking = pd.DataFrame(filas).sort_values("R²", ascending=False).reset_index(drop=True)
        with st.container(border=True, key="seccion_ranking_simple"):
            st.subheader("¿Cuál X sola predice mejor?")
            st.dataframe(Ranking.style.apply(
                             lambda fila: ["background-color: #FFF2F3" if fila["p-valor"] >= 0.05 else ""] * len(fila),
                             axis=1), hide_index=True, width="stretch",
                         column_config={"R²": st.column_config.ProgressColumn("R²", min_value=0, max_value=1, format="%.2f"),
                                        "Pendiente": st.column_config.NumberColumn(format="%.4f"),
                                        "p-valor": st.column_config.NumberColumn(format="%.3f")})
            st.caption(f"La mejor regresión simple es con **{Ranking['Variable X'].iloc[0]}** "
                       f"(R² = {Ranking['R²'].iloc[0]:.2f}). p-valor < 0.05 = relación significativa.")

        #Widget R7: simulador de la regresión simple
        with st.container(border=True, key="seccion_simulador_simple"):
            st.subheader("Simulador")
            valor = st.number_input(f"Si {bonito(X1)} fuera…", value=float(round(d[X1].mean(), 2)), key=f"sim_simple_{Base_R}_{Canal_R}_{Y}")
            st.metric(f"{bonito(Y)} predicho", num(b0 + b1 * valor))

        #Apartado final: ecuación estimada de la regresión simple
        bloque_ecuacion(Y, [X1], M, "simple")

    #-------------------------------------------------------------------------
    #VISTA E2-3: REGRESIÓN LINEAL MÚLTIPLE (varias X)
    #(va dentro de una función para poder salir con return sin detener el resto)
    def pestana_multiple():
        if len(candidatas) < 2:
            with Col_Graf:
                st.info(f"La base **{Base_Nombre}** solo tiene una variable X ({bonito(candidatas[0])}), así que no "
                        "admite regresión múltiple. Elige otra base, por ejemplo *Mensual combinada*.")
            return
        xs_def = [x for x in DEFAULT_XS.get(Base_R, []) if x in candidatas] or list(corr_y.index[:3])
        with Col_X:
            #Widget R8: variables explicativas (varias X), debajo de la gráfica
            XS = st.multiselect("Variables explicativas (X)", candidatas, default=xs_def,
                                format_func=bonito, key=f"x_multiple_{Base_R}_{Canal_R}_{Y}")
        if len(XS) < 2:
            with Col_Graf:
                st.info("Elige al menos 2 variables X para la regresión múltiple.")
            return
        MM = ols(datos_r, Y, XS)
        if not MM or MM["gl"] < 2:
            with Col_Graf:
                st.warning("Hay muy pocos datos para tantas variables X. Quita alguna o agrega más años.")
            return
        d = MM["d"]
        with Zona_KPI:  #KPIs en fila horizontal arriba de la gráfica
            K1, K2, K3, K4 = st.columns(4)
            K1.metric("R²", f"{MM['r2']:.2f}", f"explica {MM['r2'] * 100:.0f}%", delta_color="off")
            K2.metric("R² ajustado", f"{MM['r2a']:.2f}")
            K3.metric("Error típico", num(MM["rmse"]))
            K4.metric("Datos usados (n)", MM["n"])

        #GRAPH R5: REAL VS PREDICHO (si el modelo fuera perfecto, todo caería sobre la línea)
        figR5 = go.Figure()
        lim = [min(d[Y].min(), MM["pred"].min()), max(d[Y].max(), MM["pred"].max())]
        figR5.add_scatter(x=lim, y=lim, mode="lines", name="Predicción perfecta",
                          line=dict(color=GRIS, dash="dash", width=2), hoverinfo="skip")
        figR5.add_scatter(x=d[Y], y=MM["pred"], mode="markers", name="Cada registro",
                          marker=dict(color=ROJO, size=11, opacity=0.85, line=dict(color=SUPERFICIE, width=1)),
                          customdata=d["Periodo"], hovertemplate="%{customdata}<br>Real: %{x}<br>Predicho: %{y:.1f}<extra></extra>")
        figR5.update_xaxes(title=f"{bonito(Y)} real")
        figR5.update_yaxes(title=f"{bonito(Y)} predicho")
        figR5.update_layout(legend=dict(orientation="h", y=-0.18, x=0))
        peor = int(np.argmax(np.abs(MM["res"])))
        with Col_Graf:
            st.subheader("¿Qué tan cerca queda la predicción del valor real?")
            dibujar(figR5, 480, "graf_real_pred")
        with Caja_Principal:
            puntos_en_fila([
                f"Juntas, las {len(XS)} variables explican **{MM['r2'] * 100:.0f}%** de {bonito(Y)}.",
                f"En promedio el modelo se equivoca por **±{num(MM['rmse'])}**.",
                f"El error más grande fue en **{d['Periodo'].iloc[peor]}** "
                f"(real {num(d[Y].iloc[peor])}, predicho {num(MM['pred'][peor])})."])

        #GRAPH R6: DISPERSIÓN REAL Y PREDICHA contra una X elegida (selector al lado de la gráfica)
        with st.container(border=True, key="seccion_dispersion_multiple"):
            Col_Ctrl2, Col_Graf2 = st.columns([1.2, 2.6], gap="large")
            with Col_Ctrl2:
                st.markdown('<div class="puntos-titulo">Ver contra</div>', unsafe_allow_html=True)
                #Widget R9: elegir contra qué X se dibuja
                Xver = st.radio("Variable X del eje horizontal", XS, format_func=bonito,
                                key=f"x_ver_{Base_R}_{Canal_R}_{Y}")
                st.markdown('<div class="puntos-titulo">Puntos clave</div>', unsafe_allow_html=True)
                st.markdown("- Los rombos rojos no forman una recta porque cada predicción usa **todas** las X a la vez.\n"
                            "- Mientras más cortas las líneas punteadas, mejor predice el modelo.")
            figR6 = go.Figure()
            figR6.add_trace(lineas_error(d[Xver], d[Y], MM["pred"]))
            figR6.add_scatter(x=d[Xver], y=d[Y], mode="markers", name="Datos reales",
                              marker=dict(color=CARBON, size=10, opacity=0.8, line=dict(color=SUPERFICIE, width=1)),
                              customdata=d["Periodo"], hovertemplate="%{customdata}<br>X: %{x}<br>Real: %{y}<extra></extra>")
            figR6.add_scatter(x=d[Xver], y=MM["pred"], mode="markers", name="Datos predichos (modelo múltiple)",
                              marker=dict(color=ROJO, symbol="diamond", size=9, line=dict(color=SUPERFICIE, width=1)),
                              customdata=d["Periodo"], hovertemplate="%{customdata}<br>X: %{x}<br>Predicho: %{y:.1f}<extra></extra>")
            figR6.update_xaxes(title=bonito(Xver))
            figR6.update_yaxes(title=bonito(Y))
            figR6.update_layout(legend=dict(orientation="h", y=-0.18, x=0))
            with Col_Graf2:
                st.subheader(f"Dispersión real vs predicha según {bonito(Xver)}")
                dibujar(figR6, 480, "graf_disp_multiple")

        #Widget R10: simulador de la regresión múltiple
        with st.container(border=True, key="seccion_simulador_multiple"):
            st.subheader("Simulador: ¿qué pasaría si…?")
            cols = st.columns(min(len(XS), 4))
            valores = [cols[i % len(cols)].number_input(bonito(x), value=float(round(d[x].mean(), 2)),
                                                        key=f"sim_{x}_{Base_R}_{Canal_R}_{Y}") for i, x in enumerate(XS)]
            st.metric(f"{bonito(Y)} predicho", num(MM["beta"][0] + float(np.dot(MM["beta"][1:], valores))))
            st.caption("Empieza con el promedio de cada variable. Predecir muy fuera del rango de los datos es poco confiable.")

        #Apartado final: ecuación estimada de la regresión múltiple
        bloque_ecuacion(Y, XS, MM, "multiple")

    if View == "Regresión lineal múltiple":
        pestana_multiple()

    st.caption("Nota: los modelos usan solo los registros que tienen todas las variables elegidas (n). "
               "Con pocos meses los resultados son una referencia, no una regla.")

###############################################################################
# ETAPA III: MODELADO PREDICTIVO Y CLASIFICACIÓN (regresión logística)
elif Etapa.startswith("Etapa III"):
    #-------------------------------------------------------------------------
    #VISTA E3-1: RESUMEN DE CLASIFICACIÓN (todas las bases a la vez)
    if View == "Resumen de clasificación (todas las bases)":
        st.title("Etapa III · Resumen de clasificación")
        st.caption("6 bases · Regresión logística · Precisión y sensibilidad por etiqueta: Sí / No")
        Modo_Res = MODOS_UMBRAL[0]
        Bal_Res = st.radio("Balanceo de clases", MODOS_BALANCEO, horizontal=True, key="balanceo_resumen")
        faltan = [ARCHIVOS_CLAS[c][0] for c in BASES_CLAS.values() if preparar_clasificacion(c) is None]
        if faltan:
            st.warning("No encuentro estos archivos en la carpeta de app.py: " + ", ".join(faltan))
        Resumen_C = todos_los_modelos(Modo_Res, Bal_Res)
        if Resumen_C.empty:
            st.stop()

        #GRAPH C1: MAPA DE CALOR con las 3 métricas de cada modelo
        with st.container(border=True, key="seccion_mapa_modelos"):
            st.subheader("¿Qué tan bien clasifica cada modelo?")
            #Widget C0c: filtro por base
            Filtro_B = st.selectbox("Ver modelos de", ["Todas las bases"] + list(Resumen_C["Base"].unique()), key="filtro_resumen")
            Ver = Resumen_C if Filtro_B == "Todas las bases" else Resumen_C[Resumen_C["Base"] == Filtro_B]
            medidas = ["Exactitud", "Precisión (Sí)", "Precisión (No)", "Sensibilidad (Sí)", "Sensibilidad (No)"]
            valores = Ver[medidas].to_numpy(dtype=float)
            figC1 = go.Figure(go.Heatmap(
                z=np.nan_to_num(valores, nan=0), x=medidas, y=Ver["Modelo"],
                text=[[pct(v) for v in fila] for fila in valores], texttemplate="%{text}", textfont=dict(size=13, color=TINTA),
                zmin=0, zmax=1, colorscale=[[0, "#FFFFFF"], [0.5, "#F9D3DA"], [1, "#EE7C90"]], showscale=False, xgap=3, ygap=3,
                hovertemplate="%{y}<br>%{x}: %{text}<extra></extra>"))
            figC1.update_xaxes(side="top", showgrid=False)
            figC1.update_yaxes(autorange="reversed", showgrid=False)
            dibujar(figC1, max(260, 42 * len(Ver) + 70), "graf_mapa_modelos")
            mejor_c = Ver.sort_values("Sensibilidad (Sí)", ascending=False).iloc[0]
            poca = Ver[Ver["Positivos"] < 10]
            C_destacado, C_pocos = st.columns([1, 2], gap="large")
            with C_destacado:
                st.markdown("**Mayor detección de Sí**")
                st.markdown(f"{mejor_c['Modelo']} · **{pct(mejor_c['Sensibilidad (Sí)'])}**")
            with C_pocos:
                if len(poca):
                    st.markdown("**Modelos con menos de 10 casos Sí**")
                    for _, fila_poca in poca.iterrows():
                        st.markdown(f"- **{fila_poca['Base']} · {fila_poca['Y (Sí/No)']}**: {int(fila_poca['Positivos'])} casos Sí.")
                else:
                    st.caption("Todos los modelos mostrados tienen al menos 10 casos Sí.")


        st.download_button("Descargar métricas (CSV)", Resumen_C.drop(columns="Modelo").to_csv(index=False).encode("utf-8-sig"),
                           "Metricas_Etapa_III.csv", "text/csv")

    #-------------------------------------------------------------------------
    #VISTA E3-2: ANÁLISIS DE CLASIFICACIÓN (una base a detalle)
    else:
        st.sidebar.divider()
        #Widget C1: base de datos
        Base_C_Nombre = st.sidebar.selectbox("Base de datos", options=list(BASES_CLAS), key="base_clas")
        Base_C = BASES_CLAS[Base_C_Nombre]
        cfg = preparar_clasificacion(Base_C)
        st.title("Análisis de clasificación")
        if cfg is None:
            st.error(f"No encuentro **{ARCHIVOS_CLAS[Base_C][0]}**. Ponlo en la misma carpeta que app.py: {CARPETA}")
            st.stop()
        df_c = cfg["df"]
        st.write(f"Base: **{Base_C_Nombre}** · {len(df_c)} registros · modelo: **regresión logística**.")

        #Tarjeta principal, en este orden: 1) KPIs en fila, 2) matriz de confusión, 3) selectores, 4) puntos clave
        Caja_C = st.container(border=True, key="seccion_clasificacion_principal")
        with Caja_C:
            Zona_KPI_C = st.container()
            Zona_Graf_C = st.container()
            Zona_Ctrl_C = st.container()
            Zona_Puntos_C = st.container()
        with Zona_Ctrl_C:
            st.markdown('<div class="puntos-titulo">Variables del modelo</div>', unsafe_allow_html=True)
            Col_Yc, Col_Xc = st.columns([1, 2], gap="large")
            #Widget C2: variable dicotómica a predecir (Y)
            with Col_Yc:
                Yc = st.selectbox("Variable a predecir (Y, Sí/No)", cfg["ys"], format_func=bonito,
                                  key=f"yc_{Base_C}")
            cand_c = candidatas_clas(cfg, Yc)
            #Widget C3: variables explicativas (X)
            with Col_Xc:
                XSc = st.multiselect("Variables explicativas (X)", cand_c, default=x_sugeridas(cfg, Yc, cand_c),
                                     format_func=bonito, key=f"xc_{Base_C}_{Yc}")
            Modo_U, Umbral_M = MODOS_UMBRAL[0], 0.50
            Col_E, Col_B = st.columns(2, gap="large")
            with Col_E:
                Modo_E = st.radio("Evaluar con", MODOS_EVAL, key=f"eval_{Base_C}")
            with Col_B:
                Balanceo = st.radio("Balanceo de clases", MODOS_BALANCEO, key=f"bal_{Base_C}")
        if not XSc:
            with Zona_Graf_C:
                st.info("Elige al menos una variable X.")
            st.stop()
        R = evaluar_clasificacion(df_c, Yc, XSc, Modo_U, Umbral_M, Modo_E, Balanceo)
        if R is None:
            with Zona_Graf_C:
                st.warning("Con estas variables no hay suficientes datos o todos los casos son iguales. Cambia la Y o las X.")
            st.stop()
        met, M = R["met"], R["M"]
        etiqueta = bonito(Yc)
        base_ingenua = max(R["y"].mean(), 1 - R["y"].mean())

        #KPIs en fila horizontal
        with Zona_KPI_C:
            K1, K2, K3, K4, K5 = st.columns(5)
            K1.metric("Exactitud", pct(met["Exactitud"]), help="Aciertos entre todos los registros evaluados.")
            K2.metric("Precisión (Sí)", pct(met["Precisión (Sí)"]), help="Sí correctos / todos los Sí predichos.")
            K3.metric("Precisión (No)", pct(met["Precisión (No)"]), help="No correctos / todos los No predichos.")
            K4.metric("Sensibilidad (Sí)", pct(met["Sensibilidad (Sí)"]), help="Sí detectados / todos los Sí reales.")
            K5.metric("Sensibilidad (No)", pct(met["Sensibilidad (No)"]), help="No detectados / todos los No reales. También se llama especificidad.")
            fila_tarjetas([("Registros reales (Sí)", f"{met['VP'] + met['FN']:,}", "Etiqueta Sí = 1", ROJO),
                           ("Registros reales (No)", f"{met['VN'] + met['FP']:,}", "Etiqueta No = 0", CARBON),
                           ("Total evaluado", f"{met['n']:,}", f"Umbral {R['umbral']:.2f}", GRIS)])
            st.caption("— = métrica no calculable. Sensibilidad (No) = especificidad.")

        #GRAPH C3: MATRIZ DE CONFUSIÓN
        with Zona_Graf_C:
            st.subheader(f"Matriz de confusión: ¿{etiqueta}?")
            dibujar(fig_confusion(met, etiqueta), 430, "graf_confusion")
            sin_dato = int(df_c[Yc].isna().sum())
            avisos = []
            if met["VP"] + met["FN"] < 10:
                avisos.append(f"Solo hay **{met['VP'] + met['FN']}** casos Sí evaluados: los resultados son exploratorios.")
            if sin_dato:
                avisos.append(f"**{sin_dato}** registros no tienen dato de {etiqueta}: se excluyen (no se cuentan como No).")
            if avisos:
                st.caption(" · ".join(avisos))

        with Zona_Puntos_C:
            st.caption(f"{met['VP'] + met['VN']:,} aciertos · {met['FP'] + met['FN']:,} errores · "
                       f"Referencia mayoritaria: {base_ingenua:.1%}")

        with st.expander("Ver cómo se equilibró el entrenamiento"):
            #GRAPH C3b: CLASES ANTES Y DESPUÉS DEL SOBREMUESTREO (datos de entrenamiento)
            Clases = pd.DataFrame({"Momento": ["Antes"] * 2 + ["Después del sobremuestreo"] * 2,
                                   "Clase": ["No", "Sí"] * 2,
                                   "Registros": [R["antes"][0], R["antes"][1], R["despues"][0], R["despues"][1]]})
            figC3b = px.bar(Clases, x="Momento", y="Registros", color="Clase", barmode="group", text="Registros",
                            color_discrete_map={"No": GRIS, "Sí": ROJO})
            figC3b.update_traces(textposition="outside", cliponaxis=False)
            figC3b.update_xaxes(title="")
            figC3b.update_layout(legend_title="", legend=dict(orientation="h", y=-0.15, x=0))
            seccion("¿Cómo quedaron las clases para entrenar el modelo?", figC3b, [
                f"Antes: **{R['antes'][1]:,}** Sí contra **{R['antes'][0]:,}** No en los datos de entrenamiento.",
                ("Sobremuestreo: repite la clase minoritaria solo al entrenar."
                 if Balanceo == MODOS_BALANCEO[0] else "Sin balanceo: el modelo aprende sobre todo de la clase con más casos."),
                "Evaluación sin sobremuestreo."], alto=360)

        #SIMULADOR: controles agrupados, dos columnas y un resultado común.
        with st.container(border=True, key="seccion_simulador_logit"):
            st.subheader("Simulador · Describe un caso")
            st.caption("Elige sus características. El resultado estima " + nombre_negocio_clas(Yc).lower() + ".")
            entradas = {}
            cols_s = st.columns(2, gap="large")
            for i, x in enumerate(XSc):
                with cols_s[i % 2]:
                    serie = df_c[x].dropna()
                    if set(serie.unique()) <= {0, 1}:
                        entradas[x] = float(st.selectbox(bonito(x), ["No", "Sí"], key=f"simc_{x}_{Base_C}_{Yc}") == "Sí")
                    else:
                        minimo, maximo = float(serie.min()), float(serie.max())
                        entradas[x] = st.number_input(bonito(x), min_value=minimo, max_value=maximo,
                                                     value=float(serie.mean()), key=f"simc_{x}_{Base_C}_{Yc}")
            valores_s = [entradas[x] for x in XSc]
            p_sim = float(sigmoide(M["beta"][0] + np.dot(M["beta"][1:], valores_s)))
            st.divider()
            S1, S2 = st.columns(2)
            S1.metric("Probabilidad estimada de " + nombre_negocio_clas(Yc).lower(), pct(p_sim))
            S2.metric("Clasificación del caso", "Sí" if p_sim >= .50 else "No")
            st.progress(float(np.clip(p_sim, 0, 1)))
            st.caption("50% o más = Sí · Menos de 50% = No. Es una estimación del modelo.")

        #Widget C7: descargar las predicciones evaluadas
        Pred_df = R["evalua"][XSc + [Yc]].copy()
        Pred_df["Probabilidad"] = R["prob"]
        Pred_df["Predicción"] = (R["prob"] >= R["umbral"]).astype(int)
        st.download_button("⬇️ Descargar predicciones (CSV)", Pred_df.to_csv(index=False).encode("utf-8-sig"),
                           f"Predicciones_{Base_C}_{Yc}.csv", "text/csv")



    st.caption("Sí = 1 · No = 0 · Sobremuestreo solo al entrenar · Pocos casos: resultados exploratorios.")
