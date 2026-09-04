# =====================================================================
# CONFIGURACIÓN Y ESTILOS VISUALES (UI PREMIUM)
# =====================================================================
st.set_page_config(
    page_title="Analizador del Club - Club Ajedrez Camas",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Personalizado - Diseño SaaS Premium
st.markdown("""
<style>
    /* Reset y estilos base */
    .stApp {
        background: #f8fafc;
    }
    
    /* Header con logo */
    .header-container {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 10px 0 0 0;
        margin-bottom: 10px;
    }
    
    .logo-container {
        flex-shrink: 0;
        width: 80px;
        height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .logo-container img {
        width: 100%;
        height: auto;
        border-radius: 50%;
        object-fit: contain;
        border: 2px solid #e2e8f0;
        padding: 4px;
        background: white;
    }
    
    .title-container {
        flex: 1;
    }
    
    .main-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    
    .sub-title {
        color: #64748b;
        font-size: 1rem;
        font-weight: 300;
        letter-spacing: 1px;
        margin-top: 0;
    }
    
    .sub-title strong {
        color: #1e293b;
        font-weight: 600;
    }
    
    /* Resto del CSS igual... */
    ... (aquí va el resto de tu CSS sin cambios)
</style>
""", unsafe_allow_html=True)

# --- ENCABEZADO CON LOGO ---
# Determinar la ruta del logo (puedes usar URL o archivo local)
LOGO_PATH = "assets/logo_club_camas.png"  # Ruta relativa en el repositorio
# Si prefieres usar una URL, descomenta la siguiente línea y comenta la anterior:
# LOGO_PATH = "https://ejemplo.com/logo_club.png"

# Verificar si el logo existe localmente; si no, mostrar un placeholder
try:
    with open(LOGO_PATH, "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{logo_base64}" alt="Logo Club Ajedrez Camas" />'
except Exception:
    # Si no se encuentra el archivo, usamos un emoji o texto
    logo_html = '<span style="font-size:3rem;">♟️</span>'

st.markdown(f"""
<div class="header-container">
    <div class="logo-container">
        {logo_html}
    </div>
    <div class="title-container">
        <div class="main-title">ANALIZADOR DEL CLUB</div>
        <div class="sub-title"><strong>Club de Ajedrez de Camas</strong> • Sistema Grau • Dorfman • Nunn • Stockfish</div>
    </div>
</div>
""", unsafe_allow_html=True)
