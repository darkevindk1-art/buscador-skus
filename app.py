import pandas as pd
import streamlit as st

st.set_page_config(page_title="Buscador SKU", layout="centered", page_icon="📱")

st.title("📱 Buscador de Celulares por SKU")

@st.cache_data
def cargar_datos():
    df = pd.read_excel("PRECIOS CELULARES.xlsx")
    df['Código_Clean'] = df['Código'].astype(str).str.strip().str.rstrip(',')
    return df

try:
    df = cargar_datos()

    sku_input = st.text_input("Ingresa el código SKU:", "").strip().upper()

    if sku_input:
        resultado = df[df['Código_Clean'].str.upper() == sku_input]
        
        if not resultado.empty:
            row = resultado.iloc[0]
            st.success("✅ Producto Encontrado")
            
            st.metric("Precio Oferta", f"S/ {row['Nuevo Precio / Oferta']:.2f}")
            
            st.write(f"**Marca:** {row['Marca']}")
            st.write(f"**Línea:** {row['Línea']}")
            
            f_inicio = str(row['Fecha inicial']).split()[0] if pd.notnull(row['Fecha inicial']) else "N/A"
            f_fin = str(row['Fecha final']).split()[0] if pd.notnull(row['Fecha final']) else "N/A"
            st.write(f"**Vigencia:** {f_inicio} al {f_fin}")
        else:
            st.error("❌ Código no encontrado en la base de datos.")
            
    with st.expander("🔍 Ver todos los productos"):
        st.dataframe(df[['Código_Clean', 'Marca', 'Línea', 'Nuevo Precio / Oferta']])

except Exception as e:
    st.error(f"Error al cargar el archivo Excel: {e}")

