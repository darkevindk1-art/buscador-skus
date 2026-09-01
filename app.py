import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Buscador Avanzado SKU", layout="centered", page_icon="📱")

st.title("📱 Buscador de Celulares")

@st.cache_data
def cargar_datos():
    df = pd.read_excel("PRECIOS CELULARES.xlsx")
    df['Código_Clean'] = df['Código'].astype(str).str.strip().str.rstrip(',')
    df['Marca_Clean'] = df['Marca'].astype(str).str.strip().str.upper()
    return df

def buscar_modelo_web(consulta):
    try:
        query = f"{consulta} celular peru"
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')]
        
        if snippets:
            texto = snippets[0].strip()
            return texto[:130] + "..." if len(texto) > 130 else texto
        return "Sin resultado web adicional."
    except Exception:
        return "Búsqueda web no disponible."

def mostrar_hermanos(df, marca_clean, sku_actual):
    hermanos = df[(df['Marca_Clean'] == marca_clean) & (df['Código_Clean'] != sku_actual)].drop_duplicates(subset=['Código_Clean'])
    if not hermanos.empty:
        st.markdown("---")
        st.subheader("👯 Productos Hermanos (Misma Marca / Generación)")
        st.dataframe(
            hermanos[['Código_Clean', 'Nuevo Precio / Oferta', 'Línea']],
            column_config={
                "Código_Clean": "Código / SKU",
                "Nuevo Precio / Oferta": st.column_config.NumberColumn("Precio Oferta", format="S/ %.2f"),
                "Línea": "Línea"
            },
            hide_index=True,
            use_container_width=True
        )

try:
    df = cargar_datos()

    busqueda = st.text_input("🔍 Ingresa SKU o Nombre Comercial (ej: MTP03BE/A o iPhone 15):", "").strip().upper()

    if busqueda:
        # 1. Búsqueda por SKU exacto
        resultado_sku = df[df['Código_Clean'].str.upper() == busqueda]
        
        # 2. Coincidencia por texto/código en BD
        coincidencias_bd = df[
            df['Código_Clean'].str.upper().str.contains(busqueda, na=False) | 
            df['Marca_Clean'].str.contains(busqueda, na=False)
        ]

        if not resultado_sku.empty:
            prod = resultado_sku.iloc[0]
            st.success("✅ SKU Encontrado")
            
            with st.spinner("🔎 Consultando modelo exacto en la web..."):
                desc_web = buscar_modelo_web(f"{prod['Código_Clean']} {prod['Marca']}")
            
            st.info(f"**Modelo Detectado (Web):** {desc_web}")
            st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
            
            st.write(f"**Código:** `{prod['Código_Clean']}`")
            st.write(f"**Marca:** {prod['Marca']}")
            
            mostrar_hermanos(df, prod['Marca_Clean'], prod['Código_Clean'])

        elif not coincidencias_bd.empty:
            st.info(f"🔎 Coincidencias encontradas en la base de datos:")
            
            sku_sel = st.selectbox("Selecciona un SKU de la lista:", coincidencias_bd['Código_Clean'].tolist())
            
            if sku_sel:
                prod = coincidencias_bd[coincidencias_bd['Código_Clean'] == sku_sel].iloc[0]
                
                with st.spinner("🔎 Consultando modelo exacto en la web..."):
                    desc_web = buscar_modelo_web(f"{prod['Código_Clean']} {prod['Marca']}")
                
                st.info(f"**Modelo Detectado (Web):** {desc_web}")
                st.metric("Precio Oferta", f"S/ {prod['Nuevo Precio / Oferta']:.2f}")
                st.write(f"**Marca:** {prod['Marca']}")
                
                mostrar_hermanos(df, prod['Marca_Clean'], prod['Código_Clean'])
        else:
            # Si no está en el Excel por SKU, buscar el término comercial en la web
            st.warning("⚠️ No se encontró el código exacto en el Excel. Buscando por nombre comercial...")
            with st.spinner("🔎 Buscando en la web..."):
                desc_web = buscar_modelo_web(busqueda)
            
            st.info(f"**Resultado de búsqueda web:** {desc_web}")

except Exception as e:
    st.error(f"Error al procesar la búsqueda: {e}")
