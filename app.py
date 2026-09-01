import pandas as pd
import streamlit as st
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Buscador SKU con Web", layout="centered", page_icon="📱")

st.title("📱 Buscador SKU con Búsqueda Web")

@st.cache_data
def cargar_datos():
    df = pd.read_excel("PRECIOS CELULARES.xlsx")
    df['Código_Clean'] = df['Código'].astype(str).str.strip().str.rstrip(',')
    df['Marca_Clean'] = df['Marca'].astype(str).str.strip().str.upper()
    return df

def buscar_nombre_comercial_web(sku, marca):
    try:
        # Petición a DuckDuckGo para obtener el modelo exacto
        query = f"{sku} {marca} celular peru"
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        
        soup = BeautifulSoup(html, 'html.parser')
        snippets = [a.get_text() for a in soup.find_all('a', class_='result__snippet')]
        
        if snippets:
            # Retornar el texto relevante encontrado en la web
            texto = snippets[0].strip()
            return texto[:120] + "..." if len(texto) > 120 else texto
        return "No se encontró descripción en la web."
    except Exception:
        return "Búsqueda web no disponible en este momento."

try:
    df = cargar_datos()

    sku_input = st.text_input("🔍 Ingresa el código SKU:", "").strip().upper()

    if sku_input:
        resultado = df[df['Código_Clean'].str.upper() == sku_input]
        
        if not resultado.empty:
            producto = resultado.iloc[0]
            st.success("✅ Código Encontrado")
            
            # 1. Traer nombre comercial desde la WEB
            with st.spinner("🔎 Buscando modelo exacto en la web..."):
                descripcion_web = buscar_nombre_comercial_web(producto['Código_Clean'], producto['Marca'])
            
            st.subheader(f"📱 Modelo Sugerido (Web):")
            st.info(descripcion_web)
            
            st.metric("Precio Oferta", f"S/ {producto['Nuevo Precio / Oferta']:.2f}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Código:** `{producto['Código_Clean']}`")
                st.write(f"**Marca:** {producto['Marca']}")
            with col2:
                f_inicio = str(producto['Fecha inicial']).split()[0] if pd.notnull(producto['Fecha inicial']) else "N/A"
                f_fin = str(producto['Fecha final']).split()[0] if pd.notnull(producto['Fecha final']) else "N/A"
                st.write(f"**Vigencia:** {f_inicio} al {f_fin}")

            st.markdown("---")
            st.subheader("👯 Productos Hermanos de la misma marca")
            
            hermanos = df[(df['Marca_Clean'] == producto['Marca_Clean']) & (df['Código_Clean'] != producto['Código_Clean'])].drop_duplicates(subset=['Código_Clean'])
            
            if not hermanos.empty:
                st.dataframe(
                    hermanos[['Código_Clean', 'Nuevo Precio / Oferta', 'Línea']],
                    column_config={
                        "Código_Clean": "Código / SKU",
                        "Nuevo Precio / Oferta": st.column_config.NumberColumn("Precio", format="S/ %.2f"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
        else:
            st.error("❌ Código no encontrado en la base de datos local.")

except Exception as e:
    st.error(f"Error: {e}")
