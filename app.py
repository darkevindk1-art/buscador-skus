import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Buscador Inteligente de Series", layout="centered", page_icon="📱")

st.title("📱 Buscador Inteligente por Series")

def clasificar_serie_y_modelo(sku, marca):
    """Detecta la Serie exactas (Serie S, Serie A, Redmi Note, Xiaomi T, etc.) y genera el Nombre Comercial."""
    s = str(sku).upper()
    marca_u = str(marca).upper()
    s_clean = re.sub(r'(-EX|\+BDL|BUNDLE|-YA|/A|BE/A|LZ/A|GWW|FLTP|LTP)$', '', s)
    
    # 1. SAMSUNG
    if marca_u == "SAMSUNG":
        if any(x in s for x in ["S942", "S948", "S938", "S936", "S928", "S926", "S25UL", "S24", "S23", "S22", "S21"]):
            if "S25UL" in s: return "Serie S", "Samsung Galaxy S25 Ultra", 2026
            if "S94" in s or "S938" in s: return "Serie S", "Samsung Galaxy S25 / S26 Series", 2026
            if "S92" in s: return "Serie S", "Samsung Galaxy S24 Series", 2024
            return "Serie S", f"Samsung Galaxy {s_clean}", 2023
        elif any(x in s for x in ["A56", "A36", "A26", "A16", "A06", "A55", "A35", "A25", "A15", "A05", "A54", "A34", "A17"]):
            if "A56" in s: return "Serie A", "Samsung Galaxy A56 5G", 2026
            if "A36" in s: return "Serie A", "Samsung Galaxy A36 5G", 2026
            if "A26" in s: return "Serie A", "Samsung Galaxy A26 5G", 2026
            if "A17" in s: return "Serie A", "Samsung Galaxy A17 5G", 2026
            if "A16" in s: return "Serie A", "Samsung Galaxy A16", 2025
            if "A06" in s: return "Serie A", "Samsung Galaxy A06", 2025
            return "Serie A", f"Samsung Galaxy {s_clean}", 2024
        elif "EP-T" in s or "R530" in s or "R630" in s:
            return "Accesorios", f"Samsung Accesorio {s_clean}", 2024
        return "Samsung General", f"Samsung {s_clean}", 2024

    # 2. XIAOMI
    elif marca_u == "XIAOMI":
        if "17TPRO" in s: return "Serie Xiaomi T", "Xiaomi 17T Pro", 2026
        elif "17T" in s: return "Serie Xiaomi T", "Xiaomi 17T", 2026
        elif "NOTE" in s: return "Serie Redmi Note", f"Xiaomi Redmi {s_clean}", 2025
        elif any(x in s for x in ["14C", "A5", "A3", "M1908"]):
            if "14C" in s: return "Serie Redmi Básica", "Xiaomi Redmi 14C", 2025
            if "A5" in s or "A3" in s: return "Serie Redmi Básica", f"Xiaomi Redmi {s_clean}", 2024
            return "Serie Redmi Básica", f"Xiaomi Redmi {s_clean}", 2024
        return "Xiaomi General", f"Xiaomi {s_clean}", 2025

    # 3. APPLE
    elif marca_u == "APPLE":
        if "IPH13" in s or "MTP" in s or "MG6" in s or "MG8" in s or "MFY" in s:
            if "MTP" in s: return "Serie iPhone", "Apple iPhone 15", 2024
            if "MG6" in s or "MG8" in s or "MFY" in s: return "Serie iPhone", "Apple iPhone 16 / 16 Pro", 2025
            return "Serie iPhone", f"Apple iPhone {s_clean}", 2023
        return "Apple General", f"Apple {s_clean}", 2024

    # 4. MOTOROLA
    elif marca_u == "MOTOROLA":
        if "G05" in s or "G15" in s or "G06" in s or "G35" in s or "G24" in s:
            return "Serie Moto G", f"Motorola {s_clean}", 2025
        elif "E22" in s: return "Serie Moto E", "Motorola Moto E22", 2023
        return "Motorola General", f"Motorola {s_clean}", 2024

    # 5. HONOR / ZTE / OTROS
    elif marca_u == "HONOR":
        if "X" in s or "5109" in s: return "Serie Honor X", f"Honor {s_clean}", 2025
        return "Honor General", f"Honor {s_clean}", 2024
    elif marca_u == "ZTE":
        if "V80" in s or "V70" in s or "A35" in s or "A56" in s: return "Serie ZTE Blade / V", f"ZTE {s_clean}", 2025
        return "ZTE General", f"ZTE {s_clean}", 2024

    return "General", f"{marca.title()} {s_clean}", 2024

@st.cache_data
def cargar_datos():
    df = pd.read_excel("PRECIOS CELULARES.xlsx")
    df['Código_Clean'] = df['Código'].astype(str).str.strip().str.rstrip(',')
    df['Marca_Clean'] = df['Marca'].astype(str).str.strip().str.upper()
    
    # Asignar Serie, Nombre Comercial y Año de Generación
    datos_clasificados = df.apply(lambda r: clasificar_serie_y_modelo(r['Código_Clean'], r['Marca_Clean']), axis=1)
    df['Serie'] = [d[0] for d in datos_clasificados]
    df['Nombre Comercial'] = [d[1] for d in datos_clasificados]
    df['Año_Generacion'] = [d[2] for d in datos_clasificados]
    
    # Convertir Fecha Inicial a formato fecha para ordenamiento secundario
    df['Fecha_Inicial_Dt'] = pd.to_datetime(df['Fecha inicial'], errors='coerce')
    
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
        return "Búsqueda web realizada."
    except Exception:
        return "Búsqueda web no disponible."

def mostrar_hermanos_de_serie(df, marca_clean, serie_exacta, sku_excluir=""):
    # Filtra EXCLUSIVAMENTE por la misma Marca y la misma SERIE (ej. solo Serie S o solo Serie A)
    hermanos = df[(df['Marca_Clean'] == marca_clean) & (df['Serie'] == serie_exacta) & (df['Código_Clean'] != sku_excluir)].drop_duplicates(subset=['Código_Clean'])
    
    # ORDENAR: De la generación más cercana/reciente a la más distante
    hermanos = hermanos.sort_values(by=['Año_Generacion', 'Fecha_Inicial_Dt'], ascending=[False, False])
    
    if not hermanos.empty:
        st.markdown("---")
        st.subheader(f"👯 Productos Hermanos de la {serie_exacta} ({marca_clean.title()})")
        st.caption("Ordenados de la generación más reciente a la más distante:")
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

    busqueda_raw = st.text_input("🔍 Ingresa SKU o Modelo (ej: MTP03BE/A, Samsung S26, Samsung A17, Xiaomi 17T):", "").strip()

    if busqueda_raw:
        busqueda = busqueda_raw.upper()
        palabras_clave = busqueda.split()
        
        # 1. Búsqueda por SKU exacto
        resultado_sku = df[df['Código_Clean'].str.upper() == busqueda]
        
        # 2. Búsqueda por coincidencia de serie/modelo
        condiciones = [
            df['Código_Clean'].str.upper().str.contains(p, na=False) | 
            df['Marca_Clean'].str.contains(p, na=False) |
            df['Nombre Comercial'].str.upper().str.contains(p, na=False) |
            df['Serie'].str.upper().str.contains(p, na=False)
            for p in palabras_clave if len(p) > 1
        ]
        
        if condiciones:
            from functools import reduce
            coincidencias_bd = df[reduce(lambda x, y: x & y if len(condiciones)>1 else x, condiciones)]
            if coincidencias_bd.empty:
                # Si la coincidencia estricta con AND no da resultados, usamos OR para no dejar vacíos
                coincidencias_bd = df[reduce(lambda x, y: x | y, condiciones)]
        else:
            coincidencias_bd = pd.DataFrame()

        # Ordenar coincidencia principal de lo más reciente a lo más distante
        if not coincidencias_bd.empty:
            coincidencias_bd = coincidencias_bd.sort_values(by=['Año_Generacion', 'Fecha_Inicial_Dt'], ascending=[False, False])

        if not resultado_sku.empty:
            prod = resultado_sku.iloc[0]
            st.success("✅ SKU Exacto Encontrado")
            
            with st.spinner("🔎 Consultando modelo exacto en la web..."):
                desc_web = buscar_modelo_web(f"{prod['Código_Clean']} {prod['Marca']}")
            
            st.info(f"**Ficha Web:** {desc_web}")
            st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
            st.write(f"**Nombre Comercial:** {prod['Nombre Comercial']}")
            st.write(f"**Serie:** {prod['Serie']}")
            st.write(f"**Código:** `{prod['Código_Clean']}`")
            
            # Mostrar solo hermanos de la misma Serie
            mostrar_hermanos_de_serie(df, prod['Marca_Clean'], prod['Serie'], prod['Código_Clean'])

        elif not coincidencias_bd.empty:
            st.success(f"🔎 Se encontraron {len(coincidencias_bd)} modelos de la misma serie/familia:")
            
            with st.spinner("🔎 Consultando información en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            
            st.info(f"**Información Web para '{busqueda_raw}':**\n\n{desc_web}")
            
            sku_sel = st.selectbox("Selecciona el modelo exacto (ordenado de más reciente a más antiguo):", coincidencias_bd['Código_Clean'].tolist())
            
            if sku_sel:
                prod = coincidencias_bd[coincidencias_bd['Código_Clean'] == sku_sel].iloc[0]
                
                st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
                st.write(f"**Nombre Comercial:** {prod['Nombre Comercial']}")
                st.write(f"**Serie:** {prod['Serie']}")
                st.write(f"**Código / SKU:** `{prod['Código_Clean']}`")
                
                # Mostrar solo hermanos de la misma Serie
                mostrar_hermanos_de_serie(df, prod['Marca_Clean'], prod['Serie'], prod['Código_Clean'])
        else:
            st.warning(f"⚠️ No se encontró en el inventario local. Buscando en la web...")
            with st.spinner("🔎 Buscando en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            st.info(f"**Resultado Web:**\n\n{desc_web}")

except Exception as e:
    st.error(f"Error al procesar la búsqueda: {e}")
