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
# CONFIGURACIÓN DA PÁXINA E ESTILOS CORPORATIVOS (ESTILO XUNTA)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Xestión de Ausencias - CMUS Xan Viaño",
    page_icon="🎼",
    layout="wide"
)

# Estilo CSS personalizado avanzado (Tarxetas e Paleta Escura Corporativa)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');
    
    /* Fondo xeral e tipografía */
    .main {
        background-color: #f8fafc;
        font-family: 'Open Sans', sans-serif;
    }
    
    /* Barra lateral corporativa */
    [data-testid="stSidebar"] {
        background-color: #0f2e46 !important;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Cabeceira principal */
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
    
    /* Contedores con aspecto de Tarxeta / Cadro enmarcado */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] > div {
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    
    /* Cabeceiras dentro das seccións */
    h1, h2, h3 {
        color: #0f2e46 !important;
        font-weight: 700 !important;
    }
    
    /* Reestilizado das métricas (Cadros de saldo/acumulados) */
    [data-testid="stMetric"] {
        background-color: #f1f5f9 !important;
        border-left: 5px solid #0f2e46 !important;
        border-radius: 6px !important;
        padding: 10px 15px !important;
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
    
    /* Botóns principais estilizados */
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
    
    /* Caixas de texto e selectores */
    .stSelectbox, .stTextInput, .stDateInput, .stNumberInput {
        background-color: #ffffff;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)
# -----------------------------------------------------------------------------
# INICIALIZACIÓN DE SUPABASE
# -----------------------------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Erro ao conectar con Supabase: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# CONTROL DE ACCESO (AUTENTICACIÓN)
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("""
        <div class="main-header">
            <h1>🎼 Conservatorio Profesional de Música Xan Viaño</h1>
            <p>Sistema de Xestión de Ausencias e Licenzas do Profesorado</p>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("Acceso á Xefatura de Estudos")
        user_input = st.text_input("Usuario", help="Usuario de acceso proporcionado pola dirección/xefatura.")
        pass_input = st.text_input("Contrasinal", type="password", help="Contrasinal de seguridade.")
        
        if st.button("Iniciar Sesión", use_container_width=True):
            if user_input == st.secrets["APP_USER"] and pass_input == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Usuario ou contrasinal incorrectos.")
    st.stop()

# -----------------------------------------------------------------------------
# DICCIONARIO DE ARTIGOS E NORMATIVA
# -----------------------------------------------------------------------------
ARTIGOS_DOG = {
    "Art. 33 - Asuntos propios (Horas)": {"tipo": "horas", "max": 35, "desc": "Asembleas, consultas médicas ou asuntos persoais (Máx. 35h/curso)"},
    "Art. 15 - Asuntos particulares (Días)": {"tipo": "dias_lectivos", "max_lectivos": 2, "max_totais": 4, "desc": "4 días/ano (máximo 2 en días lectivos)"},
    "Art. 9 - Enfermidade común / Incapacidade": {"tipo": "libre", "desc": "Baixa médica ou ILT"},
    "Art. 12 - Deber ineludible": {"tipo": "libre", "desc": "Citacións xudiciais, exames oficiais, etc."},
    "Art. 18 - Formación e perfeccionamento": {"tipo": "libre", "desc": "Asistencia a cursos ou actividades formativas autorizadas"},
    "Outros permisos / Licenzas": {"tipo": "libre", "desc": "Outras licenzas recollidas na normativa vixente"}
}

# -----------------------------------------------------------------------------
# FUNCIÓNS AUXILIARES E LÓXICA DE NEGOCIO
# -----------------------------------------------------------------------------
def get_profesores_list():
    res = supabase.table("profesores").select("*").order("nombre").execute()
    return res.data

def get_acumulado_artigo(docente_nombre, artigo, fecha_limite, es_horas=True):
    """Calcula o acumulado acumulado antes dunha data determinada (para retroactividae)."""
    res = supabase.table("partes").select("*").eq("profesor", docente_nombre).eq("motivo", artigo).lt("fecha", fecha_limite.strftime("%Y-%m-%d")).execute()
    total = 0.0
    for r in res.data:
        if es_horas:
            try:
                total += float(r.get("horas", 0))
            except:
                pass
        else:
            total += 1.0
    return total

def enviar_email_resumo(email_destino, docente, contenido_pdf, mes_nome):
    """Envía o resumo por correo electrónico se está configurado o SMTP nos secrets."""
    if "SMTP_SERVER" not in st.secrets:
        return False, "Servidor SMTP non configurado nos Secrets."
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["SMTP_USER"]
        msg['To'] = email_destino
        msg['Subject'] = f"Resumo de Ausencias e Permisos - {docente} ({mes_nome})"
        
        body = f"Estimado/a {docente},\n\nAnéxase o resumo actualizado das túas ausencias e licenzas rexistradas ata a data no CMUS Xan Viaño.\n\nAtentamente,\nXefatura de Estudos"
        msg.attach(MIMEText(body, 'plain'))
        
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
    """Xera un PDF oficial formateado para a Xefatura Territorial / Inspección."""
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
    
    # Cabeceira
    elements.append(Paragraph("CONSERVATORIO PROFESIONAL DE MÚSICA XAN VIAÑO", title_style))
    elements.append(Paragraph(f"PARTE MENSUAL DE FALTAS E LICENZAS - MES: {mes_num}/{ano_num}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#00529B"), spaceAfter=15))
    
    if df_partes.empty:
        elements.append(Paragraph("Non se rexistraron ausencias nin permisos neste período.", styles['Normal']))
    else:
        # Táboa de datos
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
    elements.append(Paragraph(f"Ferrol, a {datetime.now().strftime('%d de %B de %Y')}", styles['Normal']))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>O Xefe de Estudos</b>", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL E NAVEGACIÓN
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="main-header">
        <h1>🎼 CMUS Xan Viaño - Xefatura de Estudos</h1>
        <p>Sistema Integral de Control de Asistencia, Horarios e Permisos</p>
    </div>
""", unsafe_allow_html=True)

menu = st.sidebar.radio(
    "Navegación / Xestión",
    ["📋 Rexistro de Ausencia", "📊 Resumo Mensual e Acumulados", "👨‍🏫 Profesores e Horarios", "⚙️ Configuración e Carga"]
)

# -----------------------------------------------------------------------------
# PESTANA 1: REXISTRO DE AUSENCIA
# -----------------------------------------------------------------------------
if menu == "📋 Rexistro de Ausencia":
    st.subheader("Rexistrar Nova Ausencia ou Licenza")
    
    profesores_data = get_profesores_list()
    if not profesores_data:
        st.warning("Aínda non hai docentes cargados no sistema. Ve á sección 'Configuración e Carga' para engadilos.")
        st.stop()
        
    lista_profes = [p["nombre"] for p in profesores_data]
    
    # Control de versión para reiniciar os widgets sen erro
    if "form_version" not in st.session_state:
        st.session_state.form_version = 0

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
            help="Data na que se produce a falta. Se se entrega con posterioridade, selecciona a data orixinal da ausencia para manter o cómputo retroactivo correcto."
        )
        motivo_sel = st.selectbox(
            "Artigo / Tipo de Permiso", 
            list(ARTIGOS_DOG.keys()),
            key=f"motivo_{version}",
            help="Selecciona o artigo normativo correspondente segundo o DOG 30/2016 e 41/2016."
        )

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
            help="Marcar se a ausencia se produce nun día con actividade lectiva (Especialmente relevante para o Artigo 15)."
        )
        observaciones = st.text_area(
            "Observacións / Xustificación", 
            key=f"obs_{version}",
            help="Anotacións internas da Xefatura de Estudos (p. ex., nº de rexistro, xustificante achegado, etc.)."
        )

    # LÓXICA DE ADVERTENCIAS E CONTROL DE LÍMITES
    st.markdown("---")
    st.subheader("🔍 Comprobación Automática de Saldo")
    
    # Control Artigo 33
    if "Art. 33" in motivo_sel:
        horas_acumuladas = get_acumulado_artigo(docente_sel, motivo_sel, data_falta, es_horas=True)
        try:
            horas_novas = float(horas_input)
        except:
            horas_novas = 0.0
        total_previsto = horas_acumuladas + horas_novas
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Acumulado anterior", f"{horas_acumuladas} h")
        col_b.metric("Solicitadas hoxe", f"{horas_novas} h")
        col_c.metric("Total previsto", f"{total_previsto} / 24 h")
        
        if total_previsto > 24:
            st.error(f"⚠️ ATENCIÓN: Superase o límite anual de 24 horas do Artigo 33! (Total: {total_previsto} h)")
        elif total_previsto >= 20:
            st.warning(f"⚡ ADVERTENCIA: O docente está próximo ao límite de 24 horas (Total: {total_previsto} h)")
        else:
            st.success("✅ Solicitude dentro do marxe permitido para o Artigo 33.")

    # Control Artigo 15
    elif "Art. 15" in motivo_sel:
        dias_lectivos_acum = get_acumulado_artigo(docente_sel, motivo_sel, data_falta, es_horas=False)
        incremento = 1 if es_lectivo else 0
        total_lectivos = dias_lectivos_acum + incremento
        
        col_a, col_b = st.columns(2)
        col_a.metric("Días lectivos xa consumidos", f"{int(dias_lectivos_acum)} días")
        col_b.metric("Lectivos previstos coa solicitude", f"{int(total_lectivos)} / 2 días")
        
        if total_lectivos > 2:
            st.error("⚠️ ALERTA: O Artigo 15 só permite un máximo de 2 DÍAS LECTIVOS por curso escolar!")
        elif total_lectivos == 2:
            st.warning("⚡ ADVERTENCIA: Con esta solicitude o docente consome o seu 2º e ÚLTIMO día lectivo permitido polo Art. 15.")
        else:
            st.success("✅ Solicitude dentro dos marxes do Artigo 15.")

    st.markdown("---")
    if st.button("💾 Gardar Ausencia en Supabase", use_container_width=True):
        nuevo_parte = {
            "profesor": docente_sel,
            "fecha": data_falta.strftime("%Y-%m-%d"),
            "horas": horas_input,
            "motivo": motivo_sel,
            "observaciones": observaciones
        }
        res = supabase.table("partes").insert(nuevo_parte).execute()
        if res.data:
            st.cache_data.clear()
            # Incrementamos a versión para forzar a Streamlit a renderizar un formulario totalmente novo e limpo
            st.session_state.form_version += 1
            st.success("✅ Ausencia rexistrada e gardada correctamente na base de datos!")
            st.rerun()
        else:
            st.error("Erro ao gardar os datos en Supabase.")
# -----------------------------------------------------------------------------
# PESTANA 2: RESUMO MENSUAL E ACUMULADOS
# -----------------------------------------------------------------------------
elif menu == "📊 Resumo Mensual e Acumulados":
    st.subheader("Resumo Mensual e Acumulados por Artigo")
    
    col_m, col_a = st.columns(2)
    mes_sel = col_m.selectbox("Seleccionar Mes", list(range(1, 13)), index=datetime.now().month - 1)
    ano_sel = col_a.number_input("Ano", value=datetime.now().year, step=1)
    
    # Rango de datas do mes seleccionado
    start_date = f"{ano_sel}-{mes_sel:02d}-01"
    if mes_sel == 12:
        end_date = f"{ano_sel+1}-01-01"
    else:
        end_date = f"{ano_sel}-{mes_sel+1:02d}-01"
        
    res = supabase.table("partes").select("*").gte("fecha", start_date).lt("fecha", end_date).execute()
    partes_mes = res.data
    
    if partes_mes:
        df = pd.DataFrame(partes_mes)
        
        # Calcular acumulados anteriores para cada fila
        acum_anteriores = []
        totales_acum = []
        for _, row in df.iterrows():
            fecha_p = datetime.strptime(row["fecha"], "%Y-%m-%d").date()
            es_h = "Art. 33" in row["motivo"]
            ac_ant = get_acumulado_artigo(row["profesor"], row["motivo"], fecha_p, es_horas=es_h)
            acum_anteriores.append(ac_ant)
            try:
                val_actual = float(row["horas"]) if es_h else 1.0
            except (ValueError, TypeError):
                val_actual = 0.0
            totales_acum.append(ac_ant + val_actual)
            
        df["acumulado_anterior"] = acum_anteriores
        df["total_acumulado"] = totales_acum
        
        st.dataframe(
            df[["profesor", "fecha", "motivo", "horas", "acumulado_anterior", "total_acumulado", "observaciones"]],
            use_container_width=True
        )
 
        st.markdown("---")
        st.subheader("⚙️ Xestionar / Eliminar Rexistros")
        
        # Opcions do selector
        opcions_registros = {
            f"ID {row['id']} - {row['profesor']} ({row['fecha']}) - {row['motivo']}": row['id']
            for _, row in df.iterrows()
        }
        
        falta_seleccionada = st.selectbox("Selecciona un rexistro para eliminar:", list(opcions_registros.keys()))
        id_para_eliminar = opcions_registros[falta_seleccionada]
        
        if st.button("🗑️ Eliminar Rexistro da Base de Datos", use_container_width=True):
            # 1. Borrado directo en Supabase por clave primaria ID
            supabase.table("partes").delete().eq("id", id_para_eliminar).execute()
            
            # 2. Borrado de toda a memoria caché de Streamlit (claves e cálculo de acumulados)
            st.cache_data.clear()
            
            # 3. Mensaxe de éxito e reinicio inmediato da interface
            st.success("✅ Rexistro eliminado correctamente de Supabase.")
            st.rerun()
        
        st.markdown("---")
        st.subheader("📄 Exportación de Informes Oficials")
        
        pdf_bytes = generar_pdf_mensual(mes_sel, ano_sel, df)
        st.download_button(
            label="📥 Descargar PDF Mensual para Inspección / Xefatura Territorial",
            data=pdf_bytes,
            file_name=f"Parte_Mensual_Faltas_{mes_sel}_{ano_sel}_CMUS_Xan_Viano.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Non hai faltas rexistradas no mes seleccionado.")

# -----------------------------------------------------------------------------
# PESTANA 3: PROFESORES E HORARIOS
# -----------------------------------------------------------------------------
elif menu == "👨‍🏫 Profesores e Horarios":
    st.subheader("Xestión de Horarios e Resumos Individuais")
    
    profesores_data = get_profesores_list()
    if not profesores_data:
        st.warning("Non hai profesores rexistrados.")
        st.stop()
        
    prof_nombres = [p["nombre"] for p in profesores_data]
    prof_selected = st.selectbox("Seleccionar Docente para consultar/editar", prof_nombres)
    
    # Obtener email del profe
    prof_info = next((p for p in profesores_data if p["nombre"] == prof_selected), None)
    email_prof = prof_info.get("email", "") if prof_info else ""
    
    col_e1, col_e2, col_e3 = st.columns([2, 1, 1])
    with col_e1:
        nuevo_email = st.text_input("Email do docente", value=email_prof if email_prof else "")
    with col_e2:
        st.write("")
        st.write("")
        if st.button("Gardar Email"):
            supabase.table("profesores").update({"email": nuevo_email}).eq("nombre", prof_selected).execute()
            st.success("Email actualizado!")
    with col_e3:
        st.write("")
        st.write("")
        if st.button("🗑️ Dar de baixa Docente", type="primary"):
            # 1. Borramos o seu horario actual (libera o cuadrante)
            supabase.table("horarios").delete().eq("profesor", prof_selected).execute()
            # 2. Borramos o docente da lista de activos
            supabase.table("profesores").delete().eq("nombre", prof_selected).execute()
            # Os partes de faltas históricos en "partes" NON se tocan
            
            st.success(f"Docente '{prof_selected}' dado de baixa. O seu histórico conservase intacto.")
            st.rerun()

    st.markdown("---")
    st.subheader(f"Horario de {prof_selected}")
    
    # Cargar horario
    res_h = supabase.table("horarios").select("*").eq("profesor", prof_selected).execute()
    horario_data = res_h.data
    
    if horario_data:
        df_h = pd.DataFrame(horario_data)
        st.dataframe(df_h[["dia_semana", "hora_inicio", "hora_fin", "materia", "grupo"]], use_container_width=True)
        
        if st.button("🗑️ Eliminar Horario deste Docente"):
            supabase.table("horarios").delete().eq("profesor", prof_selected).execute()
            st.success("Horario eliminado correctamente.")
            st.rerun()
    else:
        st.info("Este docente non ten un horario cargado na base de datos.")

    st.markdown("---")
    st.subheader("✉️ Envío de Resumo Individual ao Docente")
    
    res_p = supabase.table("partes").select("*").eq("profesor", prof_selected).execute()
    if res_p.data:
        df_ind = pd.DataFrame(res_p.data)
        pdf_ind = generar_pdf_mensual(datetime.now().month, datetime.now().year, df_ind)
        
        st.download_button(
            "📥 Descargar Resumo PDF do Docente",
            data=pdf_ind,
            file_name=f"Resumo_{prof_selected}.pdf",
            mime="application/pdf"
        )
        
        if st.button("📧 Enviar Resumo por Correo Electrónico"):
            if not nuevo_email:
                st.error("O docente non ten un correo electrónico gardado.")
            else:
                ok, msg = enviar_email_resumo(nuevo_email, prof_selected, pdf_ind, f"{datetime.now().month}/{datetime.now().year}")
                if ok:
                    st.success(f"Correo enviado con éxito a {nuevo_email}!")
                else:
                    st.error(f"Non se puido enviar o correo: {msg}")

# -----------------------------------------------------------------------------
# PESTANA 4: CONFIGURACIÓN E CARGA
# -----------------------------------------------------------------------------
elif menu == "⚙️ Configuración e Carga":
    st.subheader("Carga Masiva de Datos e Configuración")
    
    st.markdown("### 1. Cargar Lista de Docentes")
    archivo_profes = st.file_uploader(
        "Cargar arquivo de docentes (.xlsx ou .csv)", 
        type=["xlsx", "csv"],
        help="O arquivo debe conter unha columna co nome dos docentes e opcionalmente o email."
    )
    
    if archivo_profes:
        try:
            if archivo_profes.name.endswith(".csv"):
                df_p = pd.read_csv(archivo_profes)
            else:
                df_p = pd.read_excel(archivo_profes)
                
            st.write("Vista previa do arquivo:")
            st.dataframe(df_p.head(), use_container_width=True)
            
            if st.button("Importar Docentes a Supabase"):
                cnt = 0
                
                # Limpar filas/columnas completamente baleiras
                df_clean = df_p.dropna(how='all').dropna(how='all', axis=1)
                
                # Se a primeira fila ten os encabezados reais (caso de filas baleiras superiores)
                cols_lower = [str(col).strip().lower() for col in df_clean.columns]
                if not any('nombre' in c or 'docente' in c for c in cols_lower):
                    df_clean.columns = df_clean.iloc[0]
                    df_clean = df_clean[1:].reset_index(drop=True)

                for _, row in df_clean.iterrows():
                    nom = ""
                    em = ""
                    for col in row.index:
                        col_str = str(col).strip().lower()
                        if "nombre" in col_str or "docente" in col_str or "profesor" in col_str:
                            nom = str(row[col]).strip()
                        elif "email" in col_str or "correo" in col_str:
                            em = str(row[col]).strip()
                    
                    if nom and nom.lower() != 'nan' and nom.lower() != 'nombre':
                        email_val = em if (em and em.lower() != 'nan') else None
                        supabase.table("profesores").insert({"nombre": nom, "email": email_val}).execute()
                        cnt += 1
                        
                st.cache_data.clear()
                st.success(f"Importados {cnt} docentes correctamente a Supabase!")
        except Exception as e:
            st.error(f"Erro ao procesar o arquivo: {e}")

    st.markdown("---")
    st.markdown("### 2. Cargar Horarios Masivos")
    archivo_horarios = st.file_uploader(
        "Cargar arquivo de horarios (.xlsx ou .csv)", 
        type=["xlsx", "csv"],
        help="O arquivo debe ter as seguintes columnas exactas: 'profesor', 'dia_semana', 'hora_inicio', 'hora_fin', 'materia', 'grupo'."
    )
    
    if archivo_horarios:
        try:
            if archivo_horarios.name.endswith(".csv"):
                df_h = pd.read_csv(archivo_horarios)
            else:
                df_h = pd.read_excel(archivo_horarios)
                
            st.write("Vista previa dos horarios:")
            st.dataframe(df_h.head(), use_container_width=True)
            
            if st.button("Importar Horarios a Supabase"):
                records = df_h.to_dict(orient="records")
                supabase.table("horarios").insert(records).execute()
                st.cache_data.clear()
                st.success("Horarios importados e gardados con éxito!")
        except Exception as e:
            st.error(f"Erro ao cargar os horarios: {e}")
