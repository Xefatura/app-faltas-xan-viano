import streamlit as st
from supabase import create_client

st.title("🧪 Proba de Conexión CMUS Xan Viaño")

# 1. Comprobar Secrets
st.subheader("1. Estado dos Secrets")
has_url = "SUPABASE_URL" in st.secrets
has_key = "SUPABASE_KEY" in st.secrets

st.write(f"SUPABASE_URL detectada: {'✅ SI' if has_url else '❌ NON'}")
st.write(f"SUPABASE_KEY detectada: {'✅ SI' if has_key else '❌ NON'}")

if not (has_url and has_key):
    st.error("Faltan as claves nos 'Secrets' de Streamlit Cloud!")
    st.stop()

# 2. Comprobar Conexión Supabase
st.subheader("2. Conexión con Supabase")
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
    
    # Intento de consulta cun tempo límite
    res = supabase.table("profesores").select("*").limit(1).execute()
    st.success("✅ Conexión con Supabase CORRECTA!")
    st.write("Datos recibidos:", res.data)
except Exception as e:
    st.error(f"❌ Erro ao conectar con Supabase: {e}")
