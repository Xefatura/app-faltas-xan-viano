import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. Configuración da páxina e título institucional
st.set_page_config(
    page_title="Xestión de Permisos - CMUS Xan Viaño",
    page_icon="🎼",
    layout="wide"
)

# 2. Conexión segura con Supabase desde os Secrets de Streamlit
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("Erro ao conectar coa base de datos. Comproba os secrets en Streamlit Cloud.")
    st.stop()

# 3. Control de Acceso / Autenticación
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔐 Acceso a Xefatura de Estudos")
        st.subheader("CMUS Xan Viaño")
        
        user_input = st.text_input("Usuario", key="username")
        password_input = st.text_input("Contrasinal", type="password", key="password")
        
        if st.button("Iniciar sesión"):
            # Os credenciais válidos compóranse cos gardados nos Secrets
            if user_input == st.secrets.get("APP_USER", "admin") and password_input == st.secrets.get("APP_PASSWORD", "cmus2026"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Usuario ou contrasinal incorrectos.")
        
        with st.expander("🔑 Esqueciches o contrasinal?"):
            master_key = st.text_input("Clave Mestra de Recuperación", type="password")
            new_pass = st.text_input("Novo contrasinal desexado", type="password")
            if st.button("Restablecer contrasinal"):
                if master_key == st.secrets.get("MASTER_KEY", "chavemestra123"):
                    st.success(f"Clave correcta! Lembra actualizar APP_PASSWORD nos Secrets por: {new_pass}")
                else:
                    st.error("Clave Mestra incorrecta.")
        return False
    return True

if check_password():
    # --- APLICACIÓN PRINCIPAL (Unha vez autenticado) ---
    
    # Botón para pechar sesión na barra lateral
    st.sidebar.button("Pechar sesión", on_click=lambda: st.session_state.update({"authenticated": False}))
    
    st.title("🎼 Parte de Faltas e Permisos")
    st.caption("CMUS Xan Viaño - Xefatura de Estudos (DOG 30/2016 e 41/2016)")
    st.divider()

    # Pestanas principais da app
    tab1, tab2, tab3 = st.tabs(["📝 Rexistrar Permiso/Falta", "📊 Resumo e Alertas Art. 33", "⚙️ Xestión de Profesorado"])

    with tab1:
        st.header("Novo Rexistro")
        
        # Cargar lista de profesores desde Supabase
        res_profes = supabase.table("profesores").select("nombre").execute()
        lista_profes = [p["nombre"] for p in res_profes.data] if res_profes.data else ["Non hai profesores rexistrados"]
        
        with st.form("form_falta", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                profesor = st.selectbox("Docente", options=lista_profes)
                data_falta = st.date_input("Data do permiso/falta")
                horas = st.number_input("Horas afectadas", min_value=0.5, max_value=8.0, step=0.5, value=1.0)
            
            with col2:
                artigo = st.selectbox("Artigo / Motivo (DOG)", [
                    "Artigo 33 (Imprevistos / Indisposición)",
                    "Artigo 9 (Consultas médicas)",
                    "Artigo 14 (Dificultade de desprazamento)",
                    "Outros permisos oficiais"
                ])
                xustificado = st.checkbox("Xustificante entregado", value=True)
                observacions = st.text_area("Observacións", placeholder="Notas adicionais...")
            
            submetido = st.form_submit_button("Gardar Rexistro")
            
            if submetido:
                novo_rexistro = {
                    "profesor": profesor,
                    "data": str(data_falta),
                    "horas": horas,
                    "artigo": artigo,
                    "xustificado": xustificado,
                    "observacions": observacions
                }
                supabase.table("rexistros_faltas").insert(novo_rexistro).execute()
                st.success(f"Rexistro gardado correctamente para {profesor}!")

    with tab2:
        st.header("Histórico e Alertas do Artigo 33")
        
        # Cargar faltas desde Supabase
        res_faltas = supabase.table("rexistros_faltas").select("*").execute()
        
        if res_faltas.data:
            df = pd.DataFrame(res_faltas.data)
            
            # Filtro por profesor para comprobar límite de 20h/24h no Art. 33
            prof_filtro = st.selectbox("Filtrar por profesor para ver cómputo:", options=["Tódolos"] + lista_profes)
            
            if prof_filtro != "Tódolos":
                df_prof = df[df["profesor"] == prof_filtro]
                art33_horas = df_prof[df_prof["artigo"].str.contains("Artigo 33", na=False)]["horas"].sum()
                
                st.metric("Horas consumidas de Artigo 33", f"{art33_horas} h / 20 h")
                
                if art33_horas >= 20:
                    st.error(f"⚠️ **ATENCIÓN:** {prof_filtro} alcanzou ou superou as 20 horas de Artigo 33 ({art33_horas}h). A partir das 24h require xustificación médica formal.")
                elif art33_horas >= 15:
                    st.warning(f"⚡ **AVISO:** {prof_filtro} leva {art33_horas}h consumidas de Artigo 33.")
                else:
                    st.success(f"✅ Estado normal para {prof_filtro}.")
                
                st.dataframe(df_prof, use_container_width=True)
            else:
                st.dataframe(df, use_container_width=True)
        else:
            st.info("Aínda non hai permisos nin faltas rexistradas na base de datos.")

    with tab3:
        st.header("Engadir Profesorado ao Centro")
        with st.form("form_profe"):
            nome_profe = st.text_input("Nome completo do docente")
            especialidade = st.text_input("Especialidade (ex: Violín, Orquestra...)")
            btn_profe = st.form_submit_button("Engadir Docente")
            
            if btn_profe and nome_profe:
                supabase.table("profesores").insert({"nombre": nome_profe, "especialidad": especialidade}).execute()
                st.success(f"Docente {nome_profe} engadido correctamente!")
                st.rerun()
