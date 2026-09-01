import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import os

st.set_page_config(page_title="Buscador Universal de Tienda", layout="centered", page_icon="🛍️")

st.title("🛍️ Buscador Multiproducto")

@st.cache_data
def cargar_datos():
    # Detecta automáticamente si subiste un CSV o un Excel
    archivo = "PRECIOS CELULARES.xlsx"
    if os.path.exists("CATALOGO_GENERAL.csv"):
        archivo = "CATALOGO_GENERAL.csv"
    elif os.path.exists("PRECIOS CELULARES.csv"):
        archivo = "PRECIOS CELULARES.csv"

    if archivo.endswith(".csv"):
        df = pd.read_csv(archivo)
    else:
        df = pd.read_excel(archivo)
    
    # Limpieza estándar de columnas básicas
    col_sku = [c for c in df.columns if 'COD' in c.upper() or 'SKU' in c.upper()][0]
    col_precio = [c for c in df.columns if 'PRECIO' in c.upper() or 'OFERTA' in c.upper()][0]
    col_marca = [c for c in df.columns if 'MARCA' in c.upper()][0]
    col_linea = [c for c in df.columns if 'LINEA' in c.upper() or 'CATEGORIA' in c.upper()]
    col_nombre = [c for c in df.columns if 'NOMBRE' in c.upper() or 'DESCRIPCION' in c.upper() or 'PRODUCTO' in c.upper()]

    df['SKU_Clean'] = df[col_sku].astype(str).str.strip().str.rstrip(',')
    df['Marca_Clean'] = df[col_marca].astype(str).str.strip().str.upper()
    df['Precio_Clean'] = pd.to_numeric(df[col_precio], errors='coerce')
    
    # Manejar Línea / Categoría
    df['Categoria_Clean'] = df[col_linea[0]].astype(str).str.strip().str.upper() if col_linea else "GENERAL"
    
    # Manejar Nombre Comercial
    if col_nombre:
        df['Nombre_Comercial'] = df[col_nombre[0]].astype(str).str.strip()
    else:
        df['Nombre_Comercial'] = df['Marca_Clean'] + " " + df['SKU_Clean']
        
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
    # Filtra por la misma MARCA y la misma CATEGORÍA/LÍNEA (ej. solo licuadoras Oster o solo congeladoras Indurama)
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

    busqueda_raw = st.text_input("🔍 Ingresa SKU o Nombre del Producto (ej: SKU, Licuadora Oster, Congeladora, etc.):", "").strip()

    if busqueda_raw:
        busqueda = busqueda_raw.upper()
        palabras_clave = busqueda.split()
        
        # 1. Búsqueda directa por SKU exacto
        resultado_sku = df[df['SKU_Clean'].str.upper() == busqueda]
        
        # 2. Búsqueda inteligente por coincidencias de texto
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
            
            st.metric("Precio Actualizado", f"S/ {prod['Precio_Clean']:.2f}" if pd.notnull(prod['Precio_Clean']) else "Sin Precio registrado")
            st.write(f"**Nombre Comercial:** {prod['Nombre_Comercial']}")
            st.write(f"**Categoría / Línea:** {prod['Categoria_Clean']}")
            st.write(f"**Código / SKU:** `{prod['SKU_Clean']}`")
            st.write(f"**Marca:** {prod['Marca_Clean']}")
            
            mostrar_hermanos(df, prod['Marca_Clean'], prod['Categoria_Clean'], prod['SKU_Clean'])

        elif not coincidencias_bd.empty:
            st.success(f"🔎 Se encontraron {len(coincidencias_bd)} productos relacionados:")
            
            sku_sel = st.selectbox("Selecciona un producto para ver detalle:", coincidencias_bd['SKU_Clean'].tolist())
            
            if sku_sel:
                prod = coincidencias_bd[coincidencias_bd['SKU_Clean'] == sku_sel].iloc[0]
                
                st.metric("Precio Actualizado", f"S/ {prod['Precio_Clean']:.2f}" if pd.notnull(prod['Precio_Clean']) else "Sin Precio registrado")
                st.write(f"**Nombre Comercial:** {prod['Nombre_Comercial']}")
                st.write(f"**Categoría / Línea:** {prod['Categoria_Clean']}")
                st.write(f"**Código / SKU:** `{prod['SKU_Clean']}`")
                st.write(f"**Marca:** {prod['Marca_Clean']}")
                
                mostrar_hermanos(df, prod['Marca_Clean'], prod['Categoria_Clean'], prod['SKU_Clean'])
        else:
            st.warning(f"⚠️ Producto no encontrado en inventario local. Consultando web para '{busqueda_raw}'...")
            with st.spinner("🔎 Buscando en la web..."):
                desc_web = buscar_modelo_web(busqueda_raw)
            st.info(f"**Resultado Web:**\n\n{desc_web}")

except Exception as e:
    st.error(f"Error al procesar la búsqueda: {e}")
