import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Buscador Inteligente SKU", layout="centered", page_icon="📱")

st.title("📱 Buscador de Celulares")

def obtener_nombre_comercial(sku, marca):
    """Convierte códigos técnicos de SKU en nombres comerciales legibles."""
    s = str(sku).upper()
    s_clean = re.sub(r'(-EX|\+BDL|BUNDLE|-YA|/A|BE/A|LZ/A|GWW|FLTP|LTP)$', '', s)
    
    # Mapeo especial para códigos de Samsung
    if "S942" in s or "S948" in s:
        return f"{marca.title()} Galaxy S Series Ultra"
    elif "S938" in s or "S936" in s:
        return f"{marca.title()} Galaxy S Series Plus/Ultra"
    elif "S928" in s or "S926" in s:
        return f"{marca.title()} Galaxy S24 Series"
    elif "S25UL" in s:
        return f"{marca.title()} Galaxy S25 Ultra"
    elif "A56" in s:
        return f"{marca.title()} Galaxy A56 5G"
    elif "A36" in s:
        return f"{marca.title()} Galaxy A36 5G"
    elif "17TPRO" in s:
        return f"{marca.title()} 17T Pro"
    elif "17T" in s:
        return f"{marca.title()} 17T"
    elif "14C" in s:
        return f"{marca.title()} Redmi 14C"
    else:
        return f"{marca.title()} {s_clean}"

@st.cache_data
def cargar_datos():
    df = pd.read_excel("PRECIOS CELULARES.xlsx")
    df['Código_Clean'] = df['Código'].astype(str).str.strip().str.rstrip(',')
    df['Marca_Clean'] = df['Marca'].astype(str).str.strip().str.upper()
    df['Nombre Comercial'] = df.apply(lambda r: obtener_nombre_comercial(r['Código_Clean'], r['Marca']), axis=1)
    return df

def buscar_modelo_web(consulta):
    try:
        query = f"{consulta} celular peru precio"
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')]
        
        if snippets:
            texto = snippets[0].strip()
            return texto[:140] + "..." if len(texto) > 140 else texto
        return "Búsqueda web completada sin resumen específico."
    except Exception:
        return "Búsqueda web no disponible."

def mostrar_hermanos(df, marca_clean, sku_excluir=""):
    hermanos = df[(df['Marca_Clean'] == marca_clean) & (df['Código_Clean'] != sku_excluir)].drop_duplicates(subset=['Código_Clean'])
    if not hermanos.empty:
        st.markdown("---")
        st.subheader(f"👯 Productos Hermanos ({marca_clean.title()})")
        st.dataframe(
            hermanos[['Nombre Comercial', 'Código_Clean', 'Nuevo Precio / Oferta']],
            column_config={
                "Nombre Comercial": "Nombre Comercial",
                "Código_Clean": "Código / SKU",
                "Nuevo Precio / Oferta": st.column_config.NumberColumn("Precio Oferta", format="S/ %.2f")
            },
            hide_index=True,
            use_container_width=True
        )

try:
    df = cargar_datos()

    busqueda_raw = st.text_input("🔍 Ingresa SKU o Nombre (ej: MTP03BE/A o Samsung S26 256GB):", "").strip()

    if busqueda_raw:
        busqueda = busqueda_raw.upper()
        palabras_clave = busqueda.split()
        
        # 1. Búsqueda exacta por SKU
        resultado_sku = df[df['Código_Clean'].str.upper() == busqueda]
        
        # 2. Búsqueda flexible por palabras clave (ej: SAMSUNG y S26 o S25)
        # Filtra filas que coincidan con al menos una de las palabras clave principales
        condiciones = [
            df['Código_Clean'].str.upper().str.contains(p, na=False) | 
            df['Marca_Clean'].str.contains(p, na=False) |
            df['Nombre Comercial'].str.upper().str.contains(p, na=False)
            for p in palabras_clave if len(p) > 2
        ]
        
        if condiciones:
            # Coincidencia con al menos una palabra clave relevante (ej: SAMSUNG)
            from functools import reduce
            coincidencias_bd = df[reduce(lambda x, y: x | y, condiciones)]
        else:
            coincidencias_bd = pd.DataFrame()

        if not resultado_sku.empty:
            prod = resultado_sku.iloc[0]
            st.success("✅ SKU Exacto Encontrado")
            
            with st.spinner("🔎 Consultando modelo en la web..."):
                desc_web = buscar_modelo_web(f"{prod['Código_Clean']} {prod['Marca']}")
            
            st.info(f"**Resultado Web:** {desc_web}")
            st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
            st.write(f"**Nombre Comercial:** {prod['Nombre Comercial']}")
            st.write(f"**Código:** `{prod['Código_Clean']}`")
            st.write(f"**Marca:** {prod['Marca']}")
            
            mostrar_hermanos(df, prod['Marca_Clean'], prod['Código_Clean'])

        elif not coincidencias_bd.empty:
            st.success(f"🔎 Se encontraron {len(coincidencias_bd)} modelos relacionados en la base de datos:")
            
            # Consultar en la web el término específico ingresado
            with st.spinner("🔎 Consultando información comercial en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            
            st.info(f"**Información Web de '{busqueda_raw}':**\n\n{desc_web}")
            
            # Selector para ver la lista de productos relacionados
            sku_sel = st.selectbox("Selecciona un SKU de la lista para ver precio exacto:", coincidencias_bd['Código_Clean'].tolist())
            
            if sku_sel:
                prod = coincidencias_bd[coincidencias_bd['Código_Clean'] == sku_sel].iloc[0]
                
                st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
                st.write(f"**Nombre Comercial:** {prod['Nombre Comercial']}")
                st.write(f"**Código / SKU:** `{prod['Código_Clean']}`")
                st.write(f"**Marca:** {prod['Marca']}")
                
                mostrar_hermanos(df, prod['Marca_Clean'], prod['Código_Clean'])
        else:
            st.warning(f"⚠️ No se encontró el código en el Excel. Consultando web para '{busqueda_raw}'...")
            with st.spinner("🔎 Buscando en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            st.info(f"**Resultado Búsqueda Web:**\n\n{desc_web}")

except Exception as e:
    st.error(f"Error al procesar la búsqueda: {e}")
