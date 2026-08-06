import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, date
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Importacións para xeración de PDF con ReportLab
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. CONFIGURACIÓN ÚNICA DA PÁXINA E ESTILOS
st.set_page_config(
    page_title="Xestión de Ausencias - CMUS Xan Viaño",
    page_icon="🎼",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');
    
    .stApp {
        background-color: #f8fafc;
        font-family: 'Open Sans', sans-serif;
    }
    
    /* MODIFICADO: Ancho fixo e espazado interno (padding) para evitar cortes no menú */
    [data-testid="stSidebar"] {
        background-color: #0f2e46 !important;
        min-width: 340px !important;
        max-width: 340px !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-left: 1.2rem !important;
        padding-right: 1rem !important;
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    .main-header {
        background-color: #0f2e46;
        color: white;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .main-header p {
        color: #e2e8f0;
        margin: 0.3rem 0 0 0;
        font-size: 0.95rem;
    }
    
    h1, h2, h3 {
        color: #0f2e46 !important;
        font-weight: 700 !important;
    }
    
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-left: 5px solid #0f2e46 !important;
        border-radius: 6px !important;
        padding: 12px 15px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #0f2e46 !important;
        font-weight: 800 !important;
    }
    
    .stButton > button {
        background-color: #0f2e46 !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        border: none !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #1e40af !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
    }

    /* Estilo do botón de pechar sesión (vermello permanente e ben aliñado) */
    [data-testid="stSidebar"] .stButton > button {
        background-color: #c0392b !important;
        color: #ffffff !important;
        border: 1px solid #962d22 !important;
        font-weight: bold !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button * {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #e74c3c !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. CONEXIÓN CON SUPABASE
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro ao inicializar Supabase: {e}")
        return None

supabase = init_supabase()

# 3. CONTROL DE SESIÓN E AUTENTICACIÓN
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if not st.session_state.authenticated:
    st.markdown("""
        <div class="main-header" style="text-align: center;">
            <h1>🎼 Conservatorio Profesional de Música "Xan Viaño"</h1>
            <p>Sistema de Xestión de Ausencias e Licenzas do Profesorado | Xefatura de Estudos</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("🔒 Acceso á Xefatura de Estudos")
        
        user_input = st.text_input("Usuario", key="login_user")
        pass_input = st.text_input("Contrasinal", type="password", key="login_pass")
        
        if st.button("Iniciar Sesión", use_container_width=True):
            correct_user = st.secrets.get("APP_USER", "admin")
            correct_pass = st.secrets.get("APP_PASSWORD", st.secrets.get("PASSWORD", "admin"))
            master_pass = st.secrets.get("MASTER_KEY", "")
            
            if (user_input == correct_user and pass_input == correct_pass) or (pass_input != "" and pass_input == master_pass):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Usuario ou contrasinal incorrectos.")
    st.stop()

# 4. FUNCIÓNS DE CONSULTA A BASE DE DATOS
def get_profesores_list():
    try:
        res = supabase.table("profesores".strip()).select("*").order("nombre").execute()
        if res and hasattr(res, 'data') and len(res.data) > 0:
            return res.data
        return [{"id": 0, "nombre": "Docente de Proba"}]
    except Exception:
        return [{"id": 0, "nombre": "Docente de Proba"}]

def get_acumulado_artigo(docente_nombre: str, artigo: str, fecha_limite, es_horas: bool = True):
    try:
        fecha_str = fecha_limite.strftime("%Y-%m-%d") if hasattr(fecha_limite, "strftime") else str(fecha_limite)
        res = supabase.table("partes".strip()).select("*")\
            .eq("profesor", docente_nombre)\
            .eq("motivo", artigo)\
            .lt("fecha", fecha_str)\
            .execute()

        total = 0.0
        if res and hasattr(res, 'data') and res.data:
            for r in res.data:
                if es_horas:
                    try:
                        total += float(r.get("horas", 0))
                    except (ValueError, TypeError):
                        pass
                else:
                    total += 1.0
        return total
    except Exception:
        return 0.0

ARTIGOS_DOG = {
    "Art. 33 - Asuntos propios (Horas)": {"tipo": "horas", "max": 24},
    "Art. 15 - Asuntos particulares (Días)": {"tipo": "dias_lectivos", "max_lectivos": 2},
    "Art. 9 - Enfermidade común / Incapacidade": {"tipo": "libre"},
    "Art. 12 - Deber ineludible": {"tipo": "libre"},
    "Art. 18 - Formación e perfeccionamento": {"tipo": "libre"},
    "Outros permisos / Licenzas": {"tipo": "libre"}
}

def enviar_email_resumo(email_destino, docente, contenido_pdf, mes_nome):
    if "SMTP_SERVER" not in st.secrets or "SMTP_USER" not in st.secrets:
        return False, "Servidor SMTP non configurado nos Secrets."
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["SMTP_USER"]
        msg['To'] = email_destino
        msg['Subject'] = f"Resumo de Ausencias e Permisos - {docente} ({mes_nome})"
        
        body = f"Estimado/a {docente},\n\nAnéxase o resumo das túas ausencias e licenzas no CMUS Xan Viaño.\n\nAtentamente,\nXefatura de Estudos"
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        att = MIMEApplication(contenido_pdf, _subtype="pdf")
        att.add_header('Content-Disposition', 'attachment', filename=f"Resumo_Ausencias_{docente}.pdf")
        msg.attach(att)
        
        server = smtplib.SMTP(st.secrets["SMTP_SERVER"], int(st.secrets.get("SMTP_PORT", 587)))
        server.starttls()
        server.login(st.secrets["SMTP_USER"], st.secrets["SMTP_PASSWORD"])
        server.send_message(msg)
        server.quit()
        return True, "Correo enviado correctamente."
    except Exception as e:
        return False, str(e)

def generar_pdf_mensual(mes_num, ano_num, df_partes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=14, leading=16, textColor=colors.HexColor("#00529B"), alignment=1, spaceAfter=10)
    subtitle_style = ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontSize=10, leading=12, alignment=1, textColor=colors.HexColor("#475569"), spaceAfter=15)
    
    elements = [
        Paragraph("CONSERVATORIO PROFESIONAL DE MÚSICA XAN VIAÑO", title_style),
        Paragraph(f"PARTE MENSUAL DE FALTAS E LICENZAS - MES: {mes_num}/{ano_num}", subtitle_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#00529B"), spaceAfter=15)
    ]
    
    if df_partes is None or df_partes.empty:
        elements.append(Paragraph("Non se rexistraron ausencias nin permisos neste período.", styles['Normal']))
    else:
        data = [["Docente", "Data", "Artigo / Permiso", "Horas/Días", "Acum. Anterior", "Total Acum."]]
        for _, row in df_partes.iterrows():
            data.append([
                str(row.get("profesor", "")),
                str(row.get("fecha", "")),
                str(row.get("motivo", ""))[:30],
                str(row.get("horas", "")),
                str(row.get("acumulado_anterior", "0.0")),
                str(row.get("total_acumulado", "0.0"))
            ])
            
        t = Table(data, colWidths=[120, 65, 150, 60, 65, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#00529B")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (_,0), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('ALIGN', (3,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t)
        
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# 5. BARRA LATERAL E NAVEGACIÓN
st.sidebar.title("📌 Xestión CMUS")

menu = st.sidebar.radio(
    "Selecciona unha opción:",
    ["📋 Rexistro de Ausencia", "📊 Resumo Mensual e Acumulados", "👨‍🏫 Profesores e Horarios", "⚙️ Configuración e Carga"]
)

st.sidebar.markdown("---")
user_activos = st.secrets.get("APP_USER", "Xefatura de Estudos")
st.sidebar.caption(f"👤 Conectado como: **{user_activos}**")

if st.sidebar.button("🚪 Pechar sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()

st.markdown("""
    <div class="main-header">
        <h1>🎼 CMUS Xan Viaño - Xefatura de Estudos</h1>
        <p>Sistema Integral de Control de Asistencia, Horarios e Permisos</p>
    </div>
""", unsafe_allow_html=True)

# 6. PESTANAS DA APLICACIÓN
if menu == "📋 Rexistro de Ausencia":
    st.subheader("Rexistrar Nova Ausencia ou Licenza")
    
    profesores_data = get_profesores_list()
    lista_profes = [p["nombre"] for p in profesores_data]
    version = st.session_state.form_version

    col1, col2 = st.columns(2)
    
    with col1:
        docente_sel = st.selectbox("Docente", lista_profes, key=f"docente_{version}")
        data_falta = st.date_input("Data da ausencia", value=date.today(), key=f"data_{version}")
        
        opcions_artigos = list(ARTIGOS_DOG.keys()) + ["Outro / Especificar..."]
        motivo_sel = st.selectbox("Artigo / Tipo de Permiso", opcions_artigos, key=f"motivo_{version}")

        if motivo_sel == "Outro / Especificar...":
            motivo_final = st.text_input("Escribe o artigo ou motivo personalizado:", key=f"motivo_custom_{version}")
        else:
            motivo_final = motivo_sel

    with col2:
        horas_input = st.text_input("Horas lectivas afectadas", value="1", key=f"horas_{version}")
        es_lectivo = st.checkbox("É día lectivo?", value=True, key=f"lectivo_{version}")
        observaciones = st.text_area("Observacións / Xustificación", key=f"obs_{version}")

    try:
        horas_novas = float(horas_input.replace(",", "."))
    except Exception:
        horas_novas = 0.0

    st.markdown("---")
    st.subheader("🔍 Comprobación Automática de Saldo")
    
    acum_previo = 0.0
    total_previsto = 0.0

    if "33" in motivo_sel or "Art. 33" in str(motivo_final):
        horas_acumuladas = get_acumulado_artigo(docente_sel, motivo_final, data_falta, es_horas=True)
        acum_previo = horas_acumuladas
        total_previsto = horas_acumuladas + horas_novas
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Acumulado xa gardado", f"{horas_acumuladas:.2f} h")
        col_b.metric("Pendente neste formulario", f"{horas_novas:.2f} h")
        col_c.metric("Total previsto", f"{total_previsto:.2f} / 24 h")

        if total_previsto > 24:
            st.error(f"⛔ **SÚPERASE O LÍMITE ANUAL:** Con este rexistro alcanzas {total_previsto:.2f} h. O máximo permitido polo Artigo 33 son 24.00 h.")
        elif total_previsto >= 20:
            st.warning(f"⚠️ **ATENCIÓN (PRÓXIMO AO LÍMITE):** Con este rexistro sumarás {total_previsto:.2f} h das 24.00 h anuais permitidas.")
        else:
            st.success(f"✅ Dispoñible: Réstanse {(24 - total_previsto):.2f} h antes de acadar o límite anual de 24 h.")

    elif "15" in motivo_sel or "Art. 15" in str(motivo_final):
        # Recuperamos o número de días/solicitudes xa gardadas previamente para este artigo
        dias_acumulados = get_acumulado_artigo(docente_sel, motivo_final, data_falta, es_horas=False)
        
        # A nova solicitude sumará 1 día se é día lectivo
        incremento = 1 if es_lectivo else 0
        total_dias = int(dias_acumulados + incremento)
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Días lectivos xa consumidos", f"{int(dias_acumulados)} d")
        col_b.metric("Horas lectivas deste día", f"{horas_novas:.2f} h")
        col_c.metric("Total días previstos", f"{total_dias} / 2 d")
        
        if not es_lectivo:
            st.info("ℹ️ **Día non lectivo:** Rexístranse as observacións pero non computa para o límite de 2 días do Artigo 15.")
        else:
            if total_dias == 1:
                st.warning(f"⚠️ **1º DÍA CONSUMIDO (AMARELO):** Con este rexistro ({horas_novas:.2f} h lectivas) consúmese o primeiro dos 2 días permitidos no Artigo 15.")
            elif total_dias >= 2:
                st.error(f"⛔ **2º DÍA ALCANZADO / EXCEDIDO (VERMELLO):** Con este rexistro ({horas_novas:.2f} h lectivas) alcánzase ou supérase o límite máximo de 2 días do Artigo 15.")
            else:
                st.success("✅ Sen días lectivos consumidos previamente neste artigo.")
    else:
        st.info(f"ℹ️ O permiso **'{motivo_final}'** rexistrarase sen restrición de horas automatizada.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💾 Gardar Rexistro de Ausencia", use_container_width=True, type="primary"):
        if not motivo_final or str(motivo_final).strip() == "":
            st.error("Especifica un artigo ou motivo válido.")
        else:
            # FIX: Soamente enviamos campos que existen na táboa 'partes' de Supabase
            nuevo_parte = {
                "profesor": docente_sel,
                "fecha": data_falta.strftime("%Y-%m-%d"),
                "horas": horas_novas,
                "motivo": motivo_final,
                "es_lectivo": es_lectivo,
                "observaciones": observaciones
            }
            try:
                res = supabase.table("partes").insert(nuevo_parte).execute()
                if res and hasattr(res, 'data') and res.data:
                    st.session_state.form_version += 1
                    st.success(f"✅ Ausencia gardada para **{docente_sel}**!")
                    st.rerun()
                else:
                    st.error("Erro ao gardar en Supabase.")
            except Exception as e:
                st.error(f"Erro na operación: {e}")

elif menu == "📊 Resumo Mensual e Acumulados":
    st.subheader("Resumo Mensual e Acumulados por Artigo")
    
    meses_gal = ["Xaneiro", "Febreiro", "Marzo", "Abril", "Maio", "Xuño", "Xullo", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    
    col_m, col_a = st.columns(2)
    mes_sel_idx = col_m.selectbox("Seleccionar Mes", range(1, 13), format_func=lambda x: meses_gal[x-1], index=datetime.now().month - 1)
    ano_sel = col_a.number_input("Ano", value=datetime.now().year, step=1)
    
    start_date = f"{ano_sel}-{mes_sel_idx:02d}-01"
    end_date = f"{ano_sel+1}-01-01" if mes_sel_idx == 12 else f"{ano_sel}-{mes_sel_idx+1:02d}-01"
        
    try:
        res = supabase.table("partes").select("*").gte("fecha", start_date).lt("fecha", end_date).order("fecha", desc=False).execute()
        partes_mes = res.data if res and hasattr(res, 'data') and res.data else []
    except Exception as e:
        st.error(f"Erro ao consultar Supabase: {e}")
        partes_mes = []
    
    if partes_mes:
        df = pd.DataFrame(partes_mes)
        
        # Calculamos os acumulados dinamicamente para cada rexistro da táboa
        acum_anteriores = []
        totales_acum = []
        
        for _, r in df.iterrows():
            prof = r.get("profesor", "")
            mot = r.get("motivo", "")
            fec_str = r.get("fecha", "")
            fec_obj = datetime.strptime(fec_str, "%Y-%m-%d").date() if isinstance(fec_str, str) else fec_str
            es_h = "15" not in str(mot)
            
            ant = get_acumulado_artigo(prof, mot, fec_obj, es_horas=es_h)
            try:
                val_actual = float(r.get("horas", 0)) if es_h else (1.0 if r.get("es_lectivo", True) else 0.0)
            except Exception:
                val_actual = 0.0
            
            acum_anteriores.append(ant)
            totales_acum.append(ant + val_actual)

        df["acumulado_anterior"] = acum_anteriores
        df["total_acumulado"] = totales_acum

        for col in ["id", "profesor", "fecha", "motivo", "horas", "observaciones"]:
            if col not in df.columns:
                df[col] = 0.0 if col == "horas" else ""

        df_display = df[["profesor", "fecha", "motivo", "horas", "acumulado_anterior", "total_acumulado", "observaciones"]].copy()
        df_display.columns = ["Docente", "Data", "Artigo / Motivo", "Horas", "Acum. Anterior", "Total Acumulado", "Observacións"]
        
        st.dataframe(df_display, use_container_width=True)

        st.markdown("---")
        st.subheader("⚙️ Eliminar Rexistros")
        
        opcions_registros = {f"ID {row.get('id')} - {row.get('profesor')} ({row.get('fecha')})": row.get('id') for _, row in df.iterrows()}
        
        if opcions_registros:
            falta_seleccionada = st.selectbox("Selecciona un rexistro para eliminar:", list(opcions_registros.keys()))
            id_para_eliminar = opcions_registros[falta_seleccionada]
            
            if st.button("🗑️ Eliminar Rexistro da Base de Datos", use_container_width=True):
                try:
                    supabase.table("partes").delete().eq("id", id_para_eliminar).execute()
                    st.success("✅ Rexistro eliminado.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao eliminar: {e}")

        st.markdown("---")
        st.subheader("📄 Exportación de Informes")
        
        try:
            pdf_bytes = generar_pdf_mensual(mes_sel_idx, ano_sel, df)
            st.download_button(
                label=f"📥 Descargar PDF Mensual ({meses_gal[mes_sel_idx-1]} {ano_sel})",
                data=pdf_bytes,
                file_name=f"Parte_Mensual_{meses_gal[mes_sel_idx-1]}_{ano_sel}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Erro ao xerar o PDF: {e}")
    else:
        st.info(f"Non hai ausencias rexistradas para {meses_gal[mes_sel_idx-1]} de {ano_sel}.")

elif menu == "👨‍🏫 Profesores e Horarios":
    st.subheader("👨‍🏫 Xestión de Profesores e Horarios")
    st.info("Módulo de xestión de profesorado activo.")

elif menu == "⚙️ Configuración e Carga":
    st.subheader("⚙️ Configuración do Sistema")
    st.info("Módulo de axustes da base de datos activo.")
