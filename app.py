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

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN ÚNICA DA PÁXINA E ESTILOS (ESTILO XUNTA / CMUS)
# -----------------------------------------------------------------------------
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
    
    [data-testid="stSidebar"] {
        background-color: #0f2e46 !important;
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

    [data-testid="stSidebar"] .stButton > button {
        background-color: #ffffff !important;
        color: #0f2e46 !important;
        border: 1px solid #cbd5e1 !important;
        width: 100%;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: #ef4444 !important;
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. CONEXIÓN SEGURA CON SUPABASE
# -----------------------------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        return None
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase = init_supabase()

if supabase is None:
    st.error("⚠️ Erro crítico: Non se puido conectar con Supabase.")
    st.info("Revisa o apartado 'Secrets' en Streamlit Cloud e asegura que os nomes sexan exactamente 'SUPABASE_URL' e 'SUPABASE_KEY'.")
    st.stop()

# -----------------------------------------------------------------------------
# 3. XESTIÓN DE ESTADO E AUTENTICACIÓN
# -----------------------------------------------------------------------------
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
        <div class="main-header" style="text-align: center;">
            <h1>🎼 Conservatorio Profesional de Música "Xan Viaño"</h1>
            <p>Sistema de Xestión de Ausencias e Licenzas do Profesorado | Xefatura de Estudos</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_img, col_info = st.columns([1.1, 1])
    
    with col_img:
        st.image(
            "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=1200&q=80",
            caption="CMUS Xan Viaño - Ferrol",
            width="stretch"
        )

    with col_info:
        st.markdown(
            """
            <div style="background-color: #ffffff; border-left: 5px solid #0f2e46; padding: 20px; border-radius: 8px; border: 1px solid #cbd5e1;">
                <h3 style="margin-top: 0; color: #0f2e46;">Portal de Xestión Interna</h3>
                <p style="color: #334155; font-size: 0.95rem; line-height: 1.6;">
                    Benvido/a ao sistema dixital do centro para o rexistro automatizado de partes de falta e control normativo.
                </p>
                <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 15px 0;">
                <ul style="color: #475569; font-size: 0.9rem; line-height: 1.7; padding-left: 20px;">
                    <li><strong>Artigo 33:</strong> Cómputo automatizado da bolsa de horas.</li>
                    <li><strong>Artigo 15:</strong> Control de días lectivos con avisos de cores.</li>
                    <li><strong>Informes:</strong> Emisión e exportación de partes oficiais.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("🔒 Acceso á Xefatura de Estudos")
        
        with st.form("login_form_portal"):
            user_input = st.text_input("Usuario", help="Usuario de acceso proporcionado pola dirección/xefatura.")
            pass_input = st.text_input("Contrasinal", type="password", help="Contrasinal de seguridade.")
            btn_login = st.form_submit_button("Iniciar Sesión", width="stretch")
            
            if btn_login:
                correct_user = st.secrets.get("APP_USER", "admin")
                correct_pass = st.secrets.get("APP_PASSWORD", st.secrets.get("PASSWORD", "admin"))
                master_pass = st.secrets.get("MASTER_KEY", "")
                
                if (user_input == correct_user and pass_input == correct_pass) or (pass_input == master_pass and master_pass != ""):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Usuario ou contrasinal incorrectos.")
    
    st.stop()

# -----------------------------------------------------------------------------
# 4. FUNCIÓNS DE CONSULTA CON CACHÉ SEGURA E FALLBACKS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def get_profesores_list():
    try:
        res = supabase.table("profesores").select("*").order("nombre").execute()
        if res and hasattr(res, 'data') and res.data:
            return res.data
        return [{"id": 0, "nombre": "Docente de Proba (Cargar na Configuración)"}]
    except Exception:
        return [{"id": 0, "nombre": "Docente de Proba (Cargar na Configuración)"}]

@st.cache_data(ttl=30, show_spinner=False)
def get_partes_profesor(nombre_profesor: str):
    try:
        res = supabase.table("partes").select("*").eq("profesor", nombre_profesor).execute()
        return res.data if res and hasattr(res, 'data') and res.data else []
    except Exception:
        return []

@st.cache_data(ttl=30, show_spinner=False)
def get_todos_partes():
    try:
        res = supabase.table("partes").select("*").order("fecha", desc=True).execute()
        return res.data if res and hasattr(res, 'data') and res.data else []
    except Exception:
        return []

@st.cache_data(ttl=30, show_spinner=False)
def get_horarios_profesor(nombre_profesor: str):
    try:
        res = supabase.table("horarios").select("*").eq("profesor", nombre_profesor).execute()
        return res.data if res and hasattr(res, 'data') and res.data else []
    except Exception:
        return []

@st.cache_data(ttl=30, show_spinner=False)
def get_acumulado_artigo(docente_nombre: str, artigo: str, fecha_limite, es_horas: bool = True):
    try:
        fecha_str = fecha_limite.strftime("%Y-%m-%d") if hasattr(fecha_limite, "strftime") else str(fecha_limite)
        res = supabase.table("partes").select("*")\
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

# -----------------------------------------------------------------------------
# 5. DICCIONARIO DE ARTIGOS E XERACIÓN DE PDF / EMAIL
# -----------------------------------------------------------------------------
ARTIGOS_DOG = {
    "Art. 33 - Asuntos propios (Horas)": {"tipo": "horas", "max": 35, "desc": "Asembleas, consultas médicas ou asuntos persoais (Máx. 35h/curso)"},
    "Art. 15 - Asuntos particulares (Días)": {"tipo": "dias_lectivos", "max_lectivos": 2, "max_totais": 4, "desc": "4 días/ano (máximo 2 en días lectivos)"},
    "Art. 9 - Enfermidade común / Incapacidade": {"tipo": "libre", "desc": "Baixa médica ou ILT"},
    "Art. 12 - Deber ineludible": {"tipo": "libre", "desc": "Citacións xudiciais, exames oficiais, etc."},
    "Art. 18 - Formación e perfeccionamento": {"tipo": "libre", "desc": "Asistencia a cursos ou actividades formativas autorizadas"},
    "Outros permisos / Licenzas": {"tipo": "libre", "desc": "Outras licenzas recollidas na normativa vixente"}
}

def enviar_email_resumo(email_destino, docente, contenido_pdf, mes_nome):
    if "SMTP_SERVER" not in st.secrets or "SMTP_USER" not in st.secrets:
        return False, "Servidor SMTP non configurado correctamente nos Secrets."
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["SMTP_USER"]
        msg['To'] = email_destino
        msg['Subject'] = f"Resumo de Ausencias e Permisos - {docente} ({mes_nome})"
        
        body = f"Estimado/a {docente},\n\nAnéxase o resumo actualizado das túas ausencias e licenzas rexistradas ata a data no CMUS Xan Viaño.\n\nAtentamente,\nXefatura de Estudos"
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
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=14,
        leading=16,
        textColor=colors.HexColor("#00529B"),
        alignment=1,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        alignment=1,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15
    )
    
    elements = []
    
    elements.append(Paragraph("CONSERVATORIO PROFESIONAL DE MÚSICA XAN VIAÑO", title_style))
    elements.append(Paragraph(f"PARTE MENSUAL DE FALTAS E LICENZAS - MES: {mes_num}/{ano_num}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#00529B"), spaceAfter=15))
    
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
                str(row.get("acumulado_anterior", "0")),
                str(row.get("total_acumulado", "0"))
            ])
            
        t = Table(data, colWidths=[120, 65, 150, 60, 65, 60])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#00529B")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 8),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('ALIGN', (3,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(t)
        
    elements.append(Spacer(1, 30))
    
    hoxe = datetime.now()
    meses_galego = ["xaneiro", "febreiro", "marzo", "abril", "maio", "xuño", "xullo", "agosto", "setembro", "outubro", "novembro", "decembro"]
    data_str = f"{hoxe.day} de {meses_galego[hoxe.month - 1]} de {hoxe.year}"
    
    elements.append(Paragraph(f"Ferrol, a {data_str}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>O Xefe de Estudos</b>", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# 6. BARRA LATERAL E BOTÓN DE APAGADO (PECHAR SESIÓNS)
# -----------------------------------------------------------------------------
st.sidebar.title("📌 Xestión CMUS")

menu = st.sidebar.radio(
    "Selecciona unha opción:",
    ["📋 Rexistro de Ausencia", "📊 Resumo Mensual e Acumulados", "👨‍🏫 Profesores e Horarios", "⚙️ Configuración e Carga"],
    key="navigation_menu"
)

st.sidebar.markdown("---")

user_activos = st.secrets.get("APP_USER", "Xefatura de Estudos")
st.sidebar.caption(f"👤 Conectado como: **{user_activos}**")

# Botón de Apagado / Pechar Sesión con limpeza de estado completa
if st.sidebar.button("🚪 Pechar sesión", width="stretch", type="secondary"):
    st.session_state.authenticated = False
    st.session_state.clear()
    st.rerun()

st.markdown("""
    <div class="main-header">
        <h1>🎼 CMUS Xan Viaño - Xefatura de Estudos</h1>
        <p>Sistema Integral de Control de Asistencia, Horarios e Permisos</p>
    </div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. PESTANA 1: REXISTRO DE AUSENCIA
# -----------------------------------------------------------------------------
if menu == "📋 Rexistro de Ausencia":
    st.subheader("Rexistrar Nova Ausencia ou Licenza")
    
    profesores_data = get_profesores_list()
    lista_profes = [p["nombre"] for p in profesores_data]
    version = st.session_state.form_version

    col1, col2 = st.columns(2)
    
    with col1:
        docente_sel = st.selectbox(
            "Docente", 
            lista_profes, 
            key=f"docente_{version}",
            help="Selecciona o nome do docente que solicita a ausencia."
        )
        data_falta = st.date_input(
            "Data da ausencia", 
            value=date.today(),
            key=f"data_{version}",
            help="Data na que se produce a falta. Mantén o cómputo retroactivo correcto."
        )
        
        opcions_artigos = list(ARTIGOS_DOG.keys()) + ["Outro / Especificar..."]
        
        motivo_sel = st.selectbox(
            "Artigo / Tipo de Permiso", 
            opcions_artigos,
            key=f"motivo_{version}",
            help="Selecciona o artigo normativo correspondente."
        )

        if motivo_sel == "Outro / Especificar...":
            motivo_final = st.text_input(
                "Escribe o artigo, apartado ou motivo personalizado:",
                key=f"motivo_custom_{version}",
                placeholder="Ex: Artigo 12.b - Exame oficial"
            )
        else:
            motivo_final = motivo_sel

    with col2:
        horas_input = st.text_input(
            "Horas lectivas afectadas", 
            value="1",
            key=f"horas_{version}",
            help="Indica o número de horas lectivas das que se ausenta o docente nesa xornada."
        )
        es_lectivo = st.checkbox(
            "É día lectivo?", 
            value=True, 
            key=f"lectivo_{version}",
            help="Marcar se a ausencia se produce nun día con actividade lectiva."
        )
        observaciones = st.text_area(
            "Observacións / Xustificación", 
            key=f"obs_{version}",
            help="Anotacións internas da Xefatura de Estudos."
        )

    try:
        horas_novas = float(horas_input.replace(",", "."))
    except (ValueError, AttributeError):
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
        col_c.metric("Total previsto", f"{total_previsto:.2f} / 35 h")
        
        if total_previsto > 35:
            st.error(f"🚫 **ALERTA CRÍTICA:** Superase o límite anual de 35 horas do Artigo 33! (Total previsto: {total_previsto:.2f} h)")
        elif total_previsto >= 30:
            st.warning(f"⚡ **ADVERTENCIA:** O docente está moi próximo ao límite de 35 horas (Total previsto: {total_previsto:.2f} h)")
        else:
            st.success("✅ Solicitude dentro do marxe permitido para o Artigo 33.")

    elif "15" in motivo_sel or "Art. 15" in str(motivo_final):
        dias_lectivos_acum = get_acumulado_artigo(docente_sel, motivo_final, data_falta, es_horas=False)
        incremento = 1 if es_lectivo else 0
        acum_previo = dias_lectivos_acum
        total_lectivos = int(dias_lectivos_acum + incremento)
        total_previsto = float(total_lectivos)
        
        col_a, col_b = st.columns(2)
        col_a.metric("Días lectivos xa consumidos", f"{int(dias_lectivos_acum)} días")
        col_b.metric("Lectivos previstos coa solicitude", f"{total_lectivos} / 2 días")
        
        if total_lectivos == 1:
            st.warning("⚠️ **1ª Solicitude Lectiva:** O docente consome o seu primeiro día lectivo do curso.")
        elif total_lectivos == 2:
            st.error("🚫 **2ª Solicitude Lectiva (ÚLTIMO PERMITIDO):** Coa entrada deste parte o docente esgota o límite de 2 días lectivos.")
        elif total_lectivos > 2:
            st.error("⛔ **ALERTA CRÍTICA - LÍMITE SUPERADO:** A normativa prohibe conceder máis de 2 días lectivos por curso.")
        else:
            st.success("✅ Solicitude en día non lectivo (sen afectación ao cómputo de 2 días).")
    else:
        st.info(f"ℹ️ O artigo ou motivo **'{motivo_final}'** rexistrarase sen restricións de bolsa de horas automática.")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("💾 Gardar Rexistro de Ausencia", width="stretch", type="primary"):
        if not motivo_final or str(motivo_final).strip() == "":
            st.error("Por favor, especifica un artigo ou motivo válido antes de gardar.")
        else:
            nuevo_parte = {
                "profesor": docente_sel,
                "fecha": data_falta.strftime("%Y-%m-%d"),
                "horas": horas_novas,
                "motivo": motivo_final,
                "es_lectivo": es_lectivo,
                "observaciones": observaciones,
                "acumulado_anterior": acum_previo,
                "total_acumulado": total_previsto
            }
            
            try:
                res = supabase.table("partes").insert(nuevo_parte).execute()
                if res and hasattr(res, 'data') and res.data:
                    st.cache_data.clear()
                    st.session_state.form_version += 1
                    st.success(f"✅ Ausencia rexistrada e gardada correctamente para **{docente_sel}**!")
                    st.balloons()
                else:
                    st.error("Erro ao gardar os datos en Supabase.")
            except Exception as e:
                st.error(f"Ocorreu un erro ao conectar con Supabase: {e}")

# -----------------------------------------------------------------------------
# 8. PESTANA 2: RESUMO MENSUAL E ACUMULADOS
# -----------------------------------------------------------------------------
elif menu == "📊 Resumo Mensual e Acumulados":
    st.subheader("Resumo Mensual e Acumulados por Artigo")
    
    meses_gal = [
        "Xaneiro", "Febreiro", "Marzo", "Abril", "Maio", "Xuño",
        "Xullo", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    col_m, col_a = st.columns(2)
    mes_actual_idx = datetime.now().month - 1
    ano_actual = datetime.now().year

    mes_sel_idx = col_m.selectbox("Seleccionar Mes", range(1, 13), format_func=lambda x: meses_gal[x-1], index=mes_actual_idx)
    ano_sel = col_a.number_input("Ano", value=ano_actual, step=1)
    
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
        
        for col in ["id", "profesor", "fecha", "motivo", "horas", "observaciones", "acumulado_anterior", "total_acumulado"]:
            if col not in df.columns:
                df[col] = 0.0 if "acumulado" in col or col == "horas" else ""

        df_display = df[[
            "profesor", "fecha", "motivo", "horas", 
            "acumulado_anterior", "total_acumulado", "observaciones"
        ]].copy()
        
        df_display.columns = [
            "Docente", "Data", "Artigo / Motivo", "Horas", 
            "Acum. Anterior", "Total Acumulado", "Observacións"
        ]
        
        st.dataframe(df_display, width="stretch")

        st.markdown("---")
        st.subheader("⚙️ Xestionar / Eliminar Rexistros")
        
        opcions_registros = {}
        for _, row in df.iterrows():
            reg_id = row.get('id', '')
            label = f"ID {reg_id} - {row.get('profesor', '')} ({row.get('fecha', '')}) - {row.get('motivo', '')}"
            opcions_registros[label] = reg_id
        
        if opcions_registros:
            falta_seleccionada = st.selectbox("Selecciona un rexistro para eliminar:", list(opcions_registros.keys()))
            id_para_eliminar = opcions_registros[falta_seleccionada]
            
            if st.button("🗑️ Eliminar Rexistro da Base de Datos", width="stretch", type="secondary"):
                try:
                    supabase.table("partes").delete().eq("id", id_para_eliminar).execute()
                    st.cache_data.clear()
                    st.session_state.form_version += 1
                    st.success("✅ Rexistro eliminado correctamente de Supabase.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ocorreu un erro ao eliminar o rexistro: {e}")

        st.markdown("---")
        st.subheader("📄 Exportación de Informes Oficiais")
        
        try:
            pdf_bytes = generar_pdf_mensual(mes_sel_idx, ano_sel, df)
            
            col_pdf1, col_pdf2 = st.columns(2)
            
            with col_pdf1:
                st.download_button(
                    label=f"📥 Descargar PDF Mensual ({meses_gal[mes_sel_idx-1]} {ano_sel})",
                    data=pdf_bytes,
                    file_name=f"Parte_Mensual_Faltas_{meses_gal[mes_sel_idx-1]}_{ano_sel}_CMUS_Xan_Viano.pdf",
                    mime="application/pdf",
                    width="stretch"
                )
            
            with col_pdf2:
                email_dest = st.text_input("Correo do docente para envío directo:", placeholder="docente@edu.xunta.gal")
                if st.button("✉️ Enviar PDF por Correo", width="stretch"):
                    if email_dest and "@" in email_dest:
                        ok, msg = enviar_email_resumo(email_dest, "Docente", pdf_bytes, meses_gal[mes_sel_idx-1])
                        if ok:
                            st.success(msg)
                        else:
                            st.warning(msg)
                    else:
                        st.error("Introduce un correo electrónico válido antes de enviar.")
        except Exception as e:
            st.error(f"Erro ao xerar o informe PDF: {e}")
    else:
        st.info(f"Non hai ausencias rexistradas para o mes de {meses_gal[mes_sel_idx-1]} de {ano_sel}.")

# -----------------------------------------------------------------------------
# 9. PESTANAS RESTANTES (PROFESORES E CONFIGURACIÓN)
# -----------------------------------------------------------------------------
elif menu == "👨‍🏫 Profesores e Horarios":
    st.subheader("👨‍🏫 Xestión de Profesores e Horarios")
    st.info("Sección preparada para a xestión individual de horarios e asignaturas.")

elif menu == "⚙️ Configuración e Carga":
    st.subheader("⚙️ Configuración do Sistema e Carga Masiva")
    st.info("Sección para realizar cargas masivas de profesorado e axustes da base de datos.")
