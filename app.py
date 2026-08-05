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

# Estilo CSS personalizado seguro (Corporativo Xunta)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;600;700&display=swap');
    
    /* Fondo xeral e tipografía */
    .stApp {
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
    
    /* Cabeceiras dentro das seccións */
    h1, h2, h3 {
        color: #0f2e46 !important;
        font-weight: 700 !important;
    }
    
    /* Reestilizado das métricas (Cadros de saldo/acumulados) */
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

    /* Estilo específico para o botón na barra lateral (Pechar Sesión) */
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
# CONTROL DE ACCESO (AUTENTICACIÓN E PORTADA INSTITUCIONAL)
# -----------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    # 1. CABECEIRA PRINCIPAL
    st.markdown("""
        <div class="main-header" style="text-align: center;">
            <h1>🎼 Conservatorio Profesional de Música "Xan Viaño"</h1>
            <p>Sistema de Xestión de Ausencias e Licenzas do Profesorado | Xefatura de Estudos</p>
        </div>
    """, unsafe_allow_html=True)
    
    # 2. SECCIÓN VISUAL (Imaxe temática + Resumo de servizos)
    col_img, col_info = st.columns([1.1, 1])
    
    with col_img:
        st.image(
            "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=1200&q=80",
            caption="CMUS Xan Viaño - Ferrol",
            use_container_width=True
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

    # 3. FORMULARIO DE ACCESO
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.subheader("🔒 Acceso á Xefatura de Estudos")
        user_input = st.text_input("Usuario", help="Usuario de acceso proporcionado pola dirección/xefatura.")
        pass_input = st.text_input("Contrasinal", type="password", help="Contrasinal de seguridade.")
        
        if st.button("Iniciar Sesión", use_container_width=True):
            # Obtención segura dos secretos
            correct_user = st.secrets.get("APP_USER", "admin")
            correct_pass = st.secrets.get("APP_PASSWORD", "admin")
            
            if user_input == correct_user and pass_input == correct_pass:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Usuario ou contrasinal incorrectos.")
    
    st.stop()  # Impide que se cargue a barra lateral e o resto da app sen validar
    
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

# Menú lateral de navegación
menu = st.sidebar.radio(
    "Navegación / Xestión",
    ["📋 Rexistro de Ausencia", "📊 Resumo Mensual e Acumulados", "👨‍🏫 Profesores e Horarios", "⚙️ Configuración e Carga"]
)

# Separador e Botón de Pechar Sesión na barra lateral
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Pechar sesión", use_container_width=True):
    st.session_state.authenticated = False
    st.rerun()
    
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
        
        # Opcións de artigos incluindo a nova opción manual
        opcions_artigos = list(ARTIGOS_DOG.keys()) + ["Outro / Especificar..."] if 'ARTIGOS_DOG' in globals() else ["Artigo 33", "Artigo 15", "Outro / Especificar..."]
        
        motivo_sel = st.selectbox(
            "Artigo / Tipo de Permiso", 
            opcions_artigos,
            key=f"motivo_{version}",
            help="Selecciona o artigo normativo correspondente segundo o DOG ou escolle 'Outro' para escribir un personalizado."
        )

        # Campo dinámico se se elixe "Outro / Especificar..."
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
            help="Marcar se a ausencia se produce nun día con actividade lectiva (Especialmente relevante para o Artigo 15)."
        )
        observaciones = st.text_area(
            "Observacións / Xustificación", 
            key=f"obs_{version}",
            help="Anotacións internas da Xefatura de Estudos (p. ex., nº de rexistro, xustificante achegado, etc.)."
        )

    st.markdown("<br>", unsafe_allow_html=True)
    
    # Botón de gardado e lóxica con Supabase
    if st.button("💾 Gardar Rexistro de Ausencia", use_container_width=True):
        if not motivo_final or motivo_final.strip() == "":
            st.error("Por favor, especifica un artigo ou motivo válido.")
        else:
            try:
                horas_val = float(horas_input.replace(",", "."))
            except ValueError:
                horas_val = 1.0

            # Cálculo de acumulados para retroactividade
            acum_previo = get_acumulado_artigo(docente_sel, motivo_final, data_falta)
            total_acum = acum_previo + horas_val

            # Inserción en Supabase
            payload = {
                "profesor": docente_sel,
                "fecha": data_falta.strftime("%Y-%m-%d"),
                "motivo": motivo_final,
                "horas": horas_val,
                "es_lectivo": es_lectivo,
                "observaciones": observaciones,
                "acumulado_anterior": acum_previo,
                "total_acumulado": total_acum
            }
            
            try:
                supabase.table("partes").insert(payload).execute()
                st.success(f"Rexistro gardado correctamente para **{docente_sel}** ({motivo_final}).")
                
                # Incrementamos a versión para limpar o formulario
                st.session_state.form_version += 1
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao gardar en Supabase: {e}")
                
   # -------------------------------------------------------------------------
    # LÓXICA DE ADVERTENCIAS E CONTROL DE LÍMITES
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("🔍 Comprobación Automática de Saldo")
    
    # Tratamento seguro das horas introducidas
    try:
        horas_novas = float(horas_input.replace(",", "."))
    except (ValueError, AttributeError):
        horas_novas = 0.0

    acum_previo = 0.0
    total_previsto = 0.0

    # Control Artigo 33 (Enfermidade común / Asistencia médica / Horas)
    if "33" in motivo_sel or "Art. 33" in motivo_final:
        horas_acumuladas = get_acumulado_artigo(docente_sel, motivo_final, data_falta, es_horas=True)
        acum_previo = horas_acumuladas
        total_previsto = horas_acumuladas + horas_novas
        
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Acumulado xa gardado", f"{horas_acumuladas:.2f} h")
        col_b.metric("Pendente neste formulario", f"{horas_novas:.2f} h")
        col_c.metric("Total previsto", f"{total_previsto:.2f} / 24 h")
        
        if total_previsto > 24:
            st.error(f"🚫 **ALERTA CRÍTICA:** Superase o límite anual de 24 horas do Artigo 33! (Total previsto: {total_previsto:.2f} h)")
        elif total_previsto >= 20:
            st.warning(f"⚡ **ADVERTENCIA:** O docente está moi próximo ao límite de 24 horas (Total previsto: {total_previsto:.2f} h)")
        else:
            st.success("✅ Solicitude dentro do marxe permitido para o Artigo 33.")

    # Control Artigo 15 (Asuntos Propios / Particulares)
    elif "15" in motivo_sel or "Art. 15" in motivo_final:
        dias_lectivos_acum = get_acumulado_artigo(docente_sel, motivo_final, data_falta, es_horas=False)
        incremento = 1 if es_lectivo else 0
        acum_previo = dias_lectivos_acum
        total_lectivos = int(dias_lectivos_acum + incremento)
        total_previsto = float(total_lectivos)
        
        col_a, col_b = st.columns(2)
        col_a.metric("Días lectivos xa consumidos", f"{int(dias_lectivos_acum)} días")
        col_b.metric("Lectivos previstos coa solicitude", f"{total_lectivos} / 2 días")
        
        if total_lectivos == 1:
            st.warning("⚠️ **1ª Solicitude Lectiva:** O docente consome o seu primeiro día lectivo do curso. Restaralle **1 día** dispoñible.")
        elif total_lectivos == 2:
            st.error("🚫 **2ª Solicitude Lectiva (ÚLTIMO PERMITIDO):** Coa entrada deste parte o docente esgota o límite de 2 días lectivos. **Non ten dereito a solicitar máis días lectivos no curso.**")
        elif total_lectivos > 2:
            st.error(f"⛔ **ALERTA CRÍTICA - LÍMITE SUPERADO:** O docente xa consumiu os {int(dias_lectivos_acum)} días lectivos permitidos do Art. 15. A normativa prohibe conceder máis de 2 días lectivos por curso.")
        else:
            st.success("✅ Solicitude en día non lectivo (sen afectación ao cómputo de 2 días).")
    else:
        # Outros artigos sen límites automatizados
        st.info(f"ℹ️ O artigo ou motivo **'{motivo_final}'** rexistrarase sen restricións de bolsa de horas automática.")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # BOTÓN DE GARDADO EN SUPABASE
    # -------------------------------------------------------------------------
    if st.button("💾 Gardar Ausencia en Supabase", use_container_width=True):
        if not motivo_final or motivo_final.strip() == "":
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
                if res.data:
                    st.cache_data.clear()  # Limpeza de caché xeral de Streamlit
                    st.session_state.form_version += 1
                    st.success("✅ Ausencia rexistrada e gardada correctamente na base de datos!")
                    st.rerun()
                else:
                    st.error("Erro ao gardar os datos en Supabase.")
            except Exception as e:
                st.error(f"Ocorreu un erro ao conectar con Supabase: {e}")
                
# -----------------------------------------------------------------------------
# PESTANA 2: RESUMO MENSUAL E ACUMULADOS
# -----------------------------------------------------------------------------
elif menu == "📊 Resumo Mensual e Acumulados":
    st.subheader("Resumo Mensual e Acumulados por Artigo")
    
    # Nomes dos meses en galego para os seletores e informes
    meses_gal = [
        "Xaneiro", "Febreiro", "Marzo", "Abril", "Maio", "Xuño",
        "Xullo", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    
    col_m, col_a = st.columns(2)
    mes_sel_idx = col_m.selectbox("Seleccionar Mes", range(1, 13), format_func=lambda x: meses_gal[x-1], index=datetime.now().month - 1)
    ano_sel = col_a.number_input("Ano", value=datetime.now().year, step=1)
    
    # Rango de datas do mes seleccionado
    start_date = f"{ano_sel}-{mes_sel_idx:02d}-01"
    if mes_sel_idx == 12:
        end_date = f"{ano_sel+1}-01-01"
    else:
        end_date = f"{ano_sel}-{mes_sel_idx+1:02d}-01"
        
    try:
        res = supabase.table("partes").select("*").gte("fecha", start_date).lt("fecha", end_date).order("fecha", desc=False).execute()
        partes_mes = res.data
    except Exception as e:
        st.error(f"Erro ao consultar Supabase: {e}")
        partes_mes = []
    
    if partes_mes:
        df = pd.DataFrame(partes_mes)
        
        # Asignación segura de acumulados (prioriza o gardado en BD, senón calcula)
        if "acumulado_anterior" not in df.columns:
            df["acumulado_anterior"] = 0.0
        if "total_acumulado" not in df.columns:
            df["total_acumulado"] = df["horas"]

        # Copia para amosar na interface cos nomes de columnas limpos
        df_display = df[[
            "profesor", "fecha", "motivo", "horas", 
            "acumulado_anterior", "total_acumulado", "observaciones"
        ]].copy()
        
        df_display.columns = [
            "Docente", "Data", "Artigo / Motivo", "Horas", 
            "Acum. Anterior", "Total Acumulado", "Observacións"
        ]
        
        st.dataframe(df_display, use_container_width=True)

        # ---------------------------------------------------------------------
        # SECCIÓN 1: XESTIÓN E ELIMINACIÓN DE REXISTROS
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.subheader("⚙️ Xestionar / Eliminar Rexistros")
        
        opcions_registros = {
            f"ID {row['id']} - {row['profesor']} ({row['fecha']}) - {row['motivo']}": row['id']
            for _, row in df.iterrows()
        }
        
        falta_seleccionada = st.selectbox("Selecciona un rexistro para eliminar:", list(opcions_registros.keys()))
        id_para_eliminar = opcions_registros[falta_seleccionada]
        
        if st.button("🗑️ Eliminar Rexistro da Base de Datos", use_container_width=True):
            try:
                # 1. Borrado directo en Supabase por clave primaria ID
                supabase.table("partes").delete().eq("id", id_para_eliminar).execute()
                
                # 2. Borrado da memoria caché de Streamlit
                st.cache_data.clear()
                
                # 3. Incremento da versión para resetear os formularios
                if "form_version" in st.session_state:
                    st.session_state.form_version += 1
                
                st.success("✅ Rexistro eliminado correctamente de Supabase.")
                st.rerun()
            except Exception as e:
                st.error(f"Ocorreu un erro ao eliminar o rexistro: {e}")
        
        # ---------------------------------------------------------------------
        # SECCIÓN 2: EXPORTACIÓN DE INFORMES OFICIAIS
        # ---------------------------------------------------------------------
        st.markdown("---")
        st.subheader("📄 Exportación de Informes Oficiais")
        
        try:
            pdf_bytes = generar_pdf_mensual(mes_sel_idx, ano_sel, df)
            
            st.download_button(
                label=f"📥 Descargar PDF Mensual de {meses_gal[mes_sel_idx-1]} {ano_sel}",
                data=pdf_bytes,
                file_name=f"Parte_Mensual_Faltas_{meses_gal[mes_sel_idx-1]}_{ano_sel}_CMUS_Xan_Viano.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Non se puido xerar o informe PDF: {e}")
            
    else:
        st.info(f"Non hai faltas rexistradas en **{meses_gal[mes_sel_idx-1]} de {ano_sel}**.")
# -----------------------------------------------------------------------------
# PESTANA 3: PROFESORES E HORARIOS
# -----------------------------------------------------------------------------
elif menu == "👨‍🏫 Profesores e Horarios":
    st.subheader("Xestión de Horarios e Resumos Individuais")
    
    profesores_data = get_profesores_list()
    if not profesores_data:
        st.warning("Non hai profesores rexistrados na base de datos.")
        st.stop()
        
    prof_nombres = sorted([p["nombre"] for p in profesores_data])
    prof_selected = st.selectbox("Seleccionar Docente para consultar/editar", prof_nombres)
    
    # Obter email actual do docente
    prof_info = next((p for p in profesores_data if p["nombre"] == prof_selected), None)
    email_prof = prof_info.get("email", "") if prof_info else ""
    
    col_e1, col_e2 = st.columns([3, 1])
    with col_e1:
        nuevo_email = st.text_input("Email do docente", value=email_prof if email_prof else "", placeholder="exemplo@edu.xunta.gal")
    with col_e2:
        st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("💾 Gardar Email", use_container_width=True):
            try:
                supabase.table("profesores").update({"email": nuevo_email}).eq("nombre", prof_selected).execute()
                st.cache_data.clear()
                st.success("Email actualizado correctamente!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao actualizar o email: {e}")
                
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # HORARIO DO DOCENTE
    # -------------------------------------------------------------------------
    st.subheader(f"📅 Horario de {prof_selected}")
    
    try:
        res_h = supabase.table("horarios").select("*").eq("profesor", prof_selected).execute()
        horario_data = res_h.data
    except Exception as e:
        st.error(f"Erro ao consultar horarios: {e}")
        horario_data = []
    
    if horario_data:
        df_h = pd.DataFrame(horario_data)
        
        # Filtramos e renomeamos as columnas máis relevantes para a vista
        cols_mostrar = [c for c in ["dia_semana", "hora_inicio", "hora_fin", "materia", "grupo"] if c in df_h.columns]
        st.dataframe(df_h[cols_mostrar], use_container_width=True)
        
        if st.button("🗑️ Eliminar Horario deste Docente", use_container_width=True):
            try:
                supabase.table("horarios").delete().eq("profesor", prof_selected).execute()
                st.cache_data.clear()
                st.success("Horario eliminado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao eliminar o horario: {e}")
    else:
        st.info("Este docente non ten un horario cargado na base de datos.")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # RESUMO INDIVIDUAL E ENVÍO DE CORREO
    # -------------------------------------------------------------------------
    st.subheader("✉️ Envío de Resumo Individual ao Docente")
    
    try:
        res_p = supabase.table("partes").select("*").eq("profesor", prof_selected).order("fecha", desc=True).execute()
        partes_docente = res_p.data
    except Exception as e:
        st.error(f"Erro ao obter o histórico de ausencias: {e}")
        partes_docente = []

    if partes_docente:
        df_ind = pd.DataFrame(partes_docente)
        
        col_pdf, col_mail = st.columns(2)
        
        with col_pdf:
            try:
                pdf_ind = generar_pdf_mensual(datetime.now().month, datetime.now().year, df_ind)
                st.download_button(
                    "📥 Descargar Resumo PDF do Docente",
                    data=pdf_ind,
                    file_name=f"Resumo_{prof_selected.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Non se puido xerar o PDF individual: {e}")
                pdf_ind = None
        
        with col_mail:
            if st.button("📧 Enviar Resumo por Correo Electrónico", use_container_width=True):
                destinatario = nuevo_email.strip() if nuevo_email else email_prof.strip()
                if not destinatario:
                    st.error("O docente non ten un correo electrónico asignado. Asigna un email arriba primeiro.")
                elif not pdf_ind:
                    st.error("Non se puido xerar o documento PDF para adxuntar.")
                else:
                    ok, msg = enviar_email_resumo(destinatario, prof_selected, pdf_ind, f"{datetime.now().month}/{datetime.now().year}")
                    if ok:
                        st.success(f"Correo enviado con éxito a {destinatario}!")
                    else:
                        st.error(f"Non se puido enviar o correo: {msg}")
    else:
        st.info("Este docente non ten ausencias rexistradas no histórico.")

    # -------------------------------------------------------------------------
    # ZONA DE PERIGO: BAIXA DO DOCENTE
    # -------------------------------------------------------------------------
    st.markdown("---")
    with st.expander("⚠️ Zona de Perigo: Dar de baixa Docente"):
        st.write("Esta acción borrará o docente da lista activa e liberará o seu horario. O seu histórico de ausencias conservarase na base de datos.")
        confirmar = st.checkbox(f"Confirmo que quero dar de baixa a {prof_selected}")
        
        if st.button("🗑️ Confirmar e Dar de baixa Docente", type="primary", disabled=not confirmar):
            try:
                # 1. Borramos o seu horario actual (libera o cuadrante)
                supabase.table("horarios").delete().eq("profesor", prof_selected).execute()
                # 2. Borramos o docente da lista de activos
                supabase.table("profesores").delete().eq("nombre", prof_selected).execute()
                
                # Limpeza de caché e actualización de versión
                st.cache_data.clear()
                if "form_version" in st.session_state:
                    st.session_state.form_version += 1
                
                st.success(f"Docente '{prof_selected}' dado de baixa con éxito.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao procesar a baixa: {e}")

# -----------------------------------------------------------------------------
# PESTANA 4: CONFIGURACIÓN E CARGA
# -----------------------------------------------------------------------------
elif menu == "⚙️ Configuración e Carga":
    st.subheader("Carga Masiva de Datos e Configuración")
    
    # -------------------------------------------------------------------------
    # 1. CARGAR LISTA DE DOCENTES
    # -------------------------------------------------------------------------
    st.markdown("### 1. Cargar Lista de Docentes")
    archivo_profes = st.file_uploader(
        "Cargar arquivo de docentes (.xlsx ou .csv)", 
        type=["xlsx", "csv"],
        key="uploader_profes",
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
            
            if st.button("Importar Docentes a Supabase", use_container_width=True):
                cnt = 0
                
                # Limpar filas/columnas completamente baleiras
                df_clean = df_p.dropna(how='all').dropna(how='all', axis=1)
                
                # axuste se a primeira fila contén os encabezados reais
                cols_lower = [str(col).strip().lower() for col in df_clean.columns]
                if not any('nombre' in c or 'docente' in c or 'profesor' in c for c in cols_lower) and len(df_clean) > 0:
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
                        
                        # Inserción con UPSERT para evitar duplicados
                        try:
                            supabase.table("profesores").upsert(
                                {"nombre": nom, "email": email_val}, 
                                on_conflict="nombre"
                            ).execute()
                            cnt += 1
                        except Exception:
                            # Se a táboa non ten restrición UNIQUE en 'nombre', usamos insert seguro
                            supabase.table("profesores").insert({"nombre": nom, "email": email_val}).execute()
                            cnt += 1
                        
                # Limpeza de caché xeral e reinicio
                st.cache_data.clear()
                if "form_version" in st.session_state:
                    st.session_state.form_version += 1
                
                st.success(f"Importados/actualizados {cnt} docentes correctamente en Supabase!")
                st.rerun()
        except Exception as e:
            st.error(f"Erro ao procesar o arquivo de docentes: {e}")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. CARGAR HORARIOS MASIVOS
    # -------------------------------------------------------------------------
    st.markdown("### 2. Cargar Horarios Masivos")
    archivo_horarios = st.file_uploader(
        "Cargar arquivo de horarios (.xlsx ou .csv)", 
        type=["xlsx", "csv"],
        key="uploader_horarios",
        help="O arquivo debe ter as seguintes columnas: 'profesor', 'dia_semana', 'hora_inicio', 'hora_fin', 'materia', 'grupo'."
    )
    
    if archivo_horarios:
        try:
            if archivo_horarios.name.endswith(".csv"):
                df_h = pd.read_csv(archivo_horarios)
            else:
                df_h = pd.read_excel(archivo_horarios)
                
            st.write("Vista previa dos horarios:")
            st.dataframe(df_h.head(), use_container_width=True)
            
            if st.button("Importar Horarios a Supabase", use_container_width=True):
                # Limpeza de valores nulos/NaN para evitar erros de JSON en Supabase
                df_h_clean = df_h.where(pd.notnull(df_h), None)
                records = df_h_clean.to_dict(orient="records")
                
                # Inserción por lotes (chunks) de 100 para evitar saturar o payload
                chunk_size = 100
                total_inserted = 0
                for i in range(0, len(records), chunk_size):
                    chunk = records[i:i + chunk_size]
                    supabase.table("horarios").insert(chunk).execute()
                    total_inserted += len(chunk)
                
                # Limpeza de caché e reinicio
                st.cache_data.clear()
                st.success(f"Horarios importados e gardados con éxito ({total_inserted} rexistros)!")
                st.rerun()
            
        except Exception as e:
            st.error(f"Erro ao cargar o arquivo de horarios: {e}")
