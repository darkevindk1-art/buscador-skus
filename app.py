import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import os

st.set_page_config(page_title="Buscador Multiproducto", layout="centered", page_icon="🛍️")

st.title("🛍️ Buscador Multiproducto")

def obtener_nombre_comercial(sku, marca):
    """Genera un nombre legible a partir del SKU si no hay columna de descripción."""
    s = str(sku).upper()
    import re
    s_clean = re.sub(r'(-EX|\+BDL|BUNDLE|-YA|/A|BE/A|LZ/A|GWW|FLTP|LTP)$', '', s)
    return f"{str(marca).title()} {s_clean}"

@st.cache_data
def cargar_datos():
    # Detectar el archivo disponible
    archivo = "PRECIOS CELULARES.xlsx"
    if os.path.exists("CATALOGO_GENERAL.csv"):
        archivo = "CATALOGO_GENERAL.csv"
    elif os.path.exists("PRECIOS CELULARES.csv"):
        archivo = "PRECIOS CELULARES.csv"

    if archivo.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)
    
    cols = df.columns.tolist()
    
    # 1. Detectar Columna SKU
    col_sku = next((c for c in cols if any(k in c.upper() for k in ['CÓDIGO', 'CODIGO', 'SKU', 'COD'])), cols[0])
    
    # 2. Detectar Columna Precio
    col_precio = next((c for c in cols if any(k in c.upper() for k in ['PRECIO', 'OFERTA', 'VALOR'])), cols[1] if len(cols)>1 else cols[0])
    
    # 3. Detectar Columna Marca
    col_marca = next((c for c in cols if 'MARCA' in c.upper()), None)
    
    # 4. Detectar Columna Línea / Categoría
    col_linea = next((c for c in cols if any(k in c.upper() for k in ['LÍNEA', 'LINEA', 'CATEGORIA', 'CATEGORÍA'])), None)
    
    # 5. Detectar Columna Nombre Comercial / Descripción
    col_nombre = next((c for c in cols if any(k in c.upper() for k in ['NOMBRE', 'DESCRIPCION', 'DESCRIPCIÓN', 'PRODUCTO'])), None)

    # Crear columnas estandarizadas de forma segura
    df['SKU_Clean'] = df[col_sku].astype(str).str.strip().str.rstrip(',')
    df['Precio_Clean'] = pd.to_numeric(df[col_precio], errors='coerce')
    df['Marca_Clean'] = df[col_marca].astype(str).str.strip().str.upper() if col_marca else "GENERAL"
    df['Categoria_Clean'] = df[col_linea].astype(str).str.strip().str.upper() if col_linea else "GENERAL"
    
    if col_nombre:
        df['Nombre_Comercial'] = df[col_nombre].astype(str).str.strip()
    else:
        df['Nombre_Comercial'] = df.apply(lambda r: obtener_nombre_comercial(r['SKU_Clean'], r['Marca_Clean']), axis=1)
        
    return df

def buscar_modelo_web(consulta):
    try:
        query = f"{consulta} precio peru"
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=4).read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')]
        
        if snippets:
            texto = snippets[0].strip()
            return texto[:140] + "..." if len(texto) > 140 else texto
        return "Búsqueda web realizada."
    except Exception:
        return "Búsqueda web no disponible."

def mostrar_hermanos(df, marca_clean, categoria_clean, sku_excluir=""):
    hermanos = df[
        (df['Marca_Clean'] == marca_clean) & 
        (df['Categoria_Clean'] == categoria_clean) & 
        (df['SKU_Clean'] != sku_excluir)
    ].drop_duplicates(subset=['SKU_Clean'])
    
    if not hermanos.empty:
        st.markdown("---")
        st.subheader(f"👯 Productos Hermanos ({categoria_clean.title()} - {marca_clean.title()})")
        st.dataframe(
            hermanos[['Nombre_Comercial', 'SKU_Clean', 'Precio_Clean']],
            column_config={
                "Nombre_Comercial": "Nombre Comercial",
                "SKU_Clean": "Código / SKU",
                "Precio_Clean": st.column_config.NumberColumn("Precio Actualizado", format="S/ %.2f")
            },
            hide_index=True,
            use_container_width=True
        )

try:
    df = cargar_datos()

    busqueda_raw = st.text_input("🔍 Ingresa SKU o Nombre del Producto (ej: MTP03BE/A, Samsung S26, Licuadora, etc.):", "").strip()

    if busqueda_raw:
        busqueda = busqueda_raw.upper()
        palabras_clave = busqueda.split()
        
        # Búsqueda por SKU
        resultado_sku = df[df['SKU_Clean'].str.upper() == busqueda]
        
        # Búsqueda por coincidencias de texto
        condiciones = [
            df['SKU_Clean'].str.upper().str.contains(p, na=False) | 
            df['Marca_Clean'].str.contains(p, na=False) |
            df['Nombre_Comercial'].str.upper().str.contains(p, na=False) |
            df['Categoria_Clean'].str.contains(p, na=False)
            for p in palabras_clave if len(p) > 1
        ]
        
        if condiciones:
            from functools import reduce
            coincidencias_bd = df[reduce(lambda x, y: x & y if len(condiciones)>1 else x, condiciones)]
            if coincidencias_bd.empty:
                coincidencias_bd = df[reduce(lambda x, y: x | y, condiciones)]
        else:
            coincidencias_bd = pd.DataFrame()

        if not resultado_sku.empty:
            prod = resultado_sku.iloc[0]
            st.success("✅ Producto Encontrado por SKU")
            
            st.metric("Precio Actualizado", f"S/ {prod['Precio_Clean']:.2f}" if pd.notnull(prod['Precio_Clean']) else "Sin Precio")
            st.write(f"**Nombre Comercial:** {prod['Nombre_Comercial']}")
            st.write(f"**Categoría / Línea:** {prod['Categoria_Clean']}")
            st.write(f"**Código / SKU:** `{prod['SKU_Clean']}`")
            st.write(f"**Marca:** {prod['Marca_Clean']}")
            
            mostrar_hermanos(df, prod['Marca_Clean'], prod['Categoria_Clean'], prod['SKU_Clean'])

        elif not coincidencias_bd.empty:
            st.success(f"🔎 Se encontraron {len(coincidencias_bd)} productos relacionados:")
            
            sku_sel = st.selectbox("Selecciona un producto de la lista:", coincidencias_bd['SKU_Clean'].tolist())
            
            if sku_sel:
                prod = coincidencias_bd[coincidencias_bd['SKU_Clean'] == sku_sel].iloc[0]
                
                st.metric("Precio Actualizado", f"S/ {prod['Precio_Clean']:.2f}" if pd.notnull(prod['Precio_Clean']) else "Sin Precio")
                st.write(f"**Nombre Comercial:** {prod['Nombre_Comercial']}")
                st.write(f"**Categoría / Línea:** {prod['Categoria_Clean']}")
                st.write(f"**Código / SKU:** `{prod['SKU_Clean']}`")
                st.write(f"**Marca:** {prod['Marca_Clean']}")
                
                mostrar_hermanos(df, prod['Marca_Clean'], prod['Categoria_Clean'], prod['SKU_Clean'])
        else:
            st.warning(f"⚠️ No se encontró en el archivo local. Buscando en la web...")
            with st.spinner("🔎 Buscando en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            st.info(f"**Resultado Web:**\n\n{desc_web}")

except Exception as e:
    st.error(f"Error al procesar la búsqueda: {e}")
