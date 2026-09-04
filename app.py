import os
import io
import shutil
import base64
import streamlit as st
import chess
import chess.pgn
import chess.svg
import chess.engine
import time
from datetime import datetime

# =====================================================================
# CONFIGURACIÓN DE PÁGINA
# =====================================================================
st.set_page_config(
    page_title="Analizador del Club de Ajedrez de Camas",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================================
# ESTILOS CSS PERSONALIZADOS
# =====================================================================
st.markdown("""
<style>
    .stApp { background: #f8fafc; }
    .main-title {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }
    .sub-title {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 2rem;
        font-weight: 300;
        letter-spacing: 1px;
    }
    .card-error {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }
    .card-error:hover {
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.03);
        transform: translateY(-2px);
    }
    .badge-blunder {
        background: #fee2e2;
        color: #991b1b;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.8rem;
        border: 1px solid #fecaca;
        display: inline-block;
    }
    .badge-mistake {
        background: #fef3c7;
        color: #92400e;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.8rem;
        border: 1px solid #fde68a;
        display: inline-block;
    }
    .badge-inaccuracy {
        background: #e0f2fe;
        color: #075985;
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 0.8rem;
        border: 1px solid #bae6fd;
        display: inline-block;
    }
    .metric-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1.2; }
    .metric-label { font-size: 0.85rem; color: #64748b; margin-top: 4px; font-weight: 500; }
    .metric-icon { font-size: 1.5rem; margin-bottom: 4px; }
    .board-container { display: flex; justify-content: center; align-items: center; width: 100%; }
    .board-container img {
        max-width: 100%;
        height: auto;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07);
        border: 1px solid #e2e8f0;
    }
    .info-box {
        background: #f1f5f9;
        border-radius: 10px;
        padding: 12px 16px;
        margin: 8px 0;
        border-left: 4px solid #3b82f6;
    }
    .stProgress > div > div { background: linear-gradient(90deg, #3b82f6, #8b5cf6); }
    @media (max-width: 768px) {
        .metric-value { font-size: 1.5rem; }
        .main-title { font-size: 1.8rem; }
        .card-error { padding: 16px; }
    }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# CABECERA CON LOGO Y TÍTULO PERSONALIZADO
# =====================================================================
col_logo, col_titulo = st.columns([1, 5])
with col_logo:
    # Intenta cargar el logo local; si no existe, muestra un emoji
    try:
        st.image("logo_club.png", width=80)  # Cambia el nombre si es necesario
    except:
        st.markdown("♟️")
with col_titulo:
    st.markdown('<div class="main-title">♟️ ANALIZADOR DEL CLUB DE AJEDREZ DE CAMAS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Sistema de Análisis Posicional Avanzado • Grau • Dorfman • Nunn • Stockfish</div>', unsafe_allow_html=True)

# =====================================================================
# FUNCIONES DE ANÁLISIS (sin cambios)
# =====================================================================

def pv_a_san(tablero_origen, lista_movimientos, limite_jugadas=6):
    t = tablero_origen.copy()
    secuencia = []
    for m in lista_movimientos[:limite_jugadas]:
        try:
            secuencia.append(t.san(m))
            t.push(m)
        except Exception:
            break
    return " → ".join(secuencia)

def generar_tablero_svg(tablero, jugada_jugada=None, mejor_jugada=None, color_usuario=chess.WHITE, size=310):
    flechas = []
    if isinstance(jugada_jugada, chess.Move):
        try:
            flechas.append(chess.svg.Arrow(jugada_jugada.from_square, jugada_jugada.to_square, color="#dc2626", opacity=0.8))
        except Exception:
            pass
    if isinstance(mejor_jugada, chess.Move):
        try:
            flechas.append(chess.svg.Arrow(mejor_jugada.from_square, mejor_jugada.to_square, color="#16a34a", opacity=0.8))
        except Exception:
            pass
    outposts = detectar_outposts(tablero, color_usuario)
    lastmove = jugada_jugada if isinstance(jugada_jugada, chess.Move) else None
    try:
        svg_data = chess.svg.board(
            board=tablero,
            orientation=color_usuario,
            arrows=flechas,
            size=size,
            squares=outposts,
            lastmove=lastmove
        )
    except Exception:
        svg_data = chess.svg.board(board=tablero, orientation=color_usuario, size=size)
    b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
    return f'<div class="board-container"><img src="data:image/svg+xml;base64,{b64}" style="width:100%; max-width:{size}px;"/></div>'

def evaluar_material(tablero, color):
    valores = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    return sum(len(tablero.pieces(p, color)) * v for p, v in valores.items())

def fase_del_juego(tablero, turno):
    if turno <= 10:
        return "Apertura"
    hay_damas = len(tablero.pieces(chess.QUEEN, chess.WHITE)) > 0 or len(tablero.pieces(chess.QUEEN, chess.BLACK)) > 0
    mat_total = evaluar_material(tablero, chess.WHITE) + evaluar_material(tablero, chess.BLACK)
    if not hay_damas or mat_total < 28:
        return "Final"
    return "Medio Juego"

def detectar_outposts(tablero, color):
    outposts = []
    enemy_color = not color
    enemy_pawns = tablero.pieces(chess.PAWN, enemy_color)
    attacked_by_pawns = set()
    for pawn in enemy_pawns:
        attacked_by_pawns.update(tablero.attacks(pawn))
    for square in chess.SQUARES:
        row = chess.square_rank(square)
        if color == chess.WHITE and row < 4:
            continue
        if color == chess.BLACK and row > 3:
            continue
        if square not in attacked_by_pawns and not tablero.piece_at(square):
            outposts.append(square)
    return outposts[:6]

def detectar_peon_pasado(tablero, color):
    peones_pasados = []
    peones = tablero.pieces(chess.PAWN, color)
    enemy_peones = tablero.pieces(chess.PAWN, not color)
    for peon in peones:
        file = chess.square_file(peon)
        rank = chess.square_rank(peon)
        bloqueado = False
        for f in [file - 1, file, file + 1]:
            if 0 <= f <= 7:
                for ep in enemy_peones:
                    if chess.square_file(ep) == f:
                        if color == chess.WHITE and chess.square_rank(ep) > rank:
                            bloqueado = True
                            break
                        if color == chess.BLACK and chess.square_rank(ep) < rank:
                            bloqueado = True
                            break
            if bloqueado:
                break
        if not bloqueado:
            peones_pasados.append(peon)
    return peones_pasados

def detectar_debilidades_estructurales(tablero, color):
    debilidades = []
    peones = tablero.pieces(chess.PAWN, color)
    for col in range(8):
        peones_col = [p for p in peones if chess.square_file(p) == col]
        if len(peones_col) >= 2:
            debilidades.append(f"Peones doblados en columna {chess.FILE_NAMES[col].upper()}")
        if len(peones_col) == 1:
            hay_adyacentes = False
            for adj_col in [col - 1, col + 1]:
                if 0 <= adj_col <= 7:
                    if any(chess.square_file(p) == adj_col for p in peones):
                        hay_adyacentes = True
                        break
            if not hay_adyacentes:
                debilidades.append(f"Peón aislado en columna {chess.FILE_NAMES[col].upper()}")
    return debilidades

def caballo_en_el_borde(jugada, pieza_movida):
    if pieza_movida == chess.KNIGHT:
        col = chess.square_file(jugada.to_square)
        return col == 0 or col == 7
    return False

def torre_en_septima(jugada, pieza_movida, color):
    if pieza_movida == chess.ROOK:
        fila = chess.square_rank(jugada.to_square)
        return (color == chess.WHITE and fila == 6) or (color == chess.BLACK and fila == 1)
    return False

def detectar_alfil_malo(tablero, color):
    alfiles = tablero.pieces(chess.BISHOP, color)
    peones = tablero.pieces(chess.PAWN, color)
    for alfil in alfiles:
        color_casilla = (chess.square_rank(alfil) + chess.square_file(alfil)) % 2
        peones_mismo_color = sum(1 for p in peones if (chess.square_rank(p) + chess.square_file(p)) % 2 == color_casilla)
        if peones_mismo_color >= 4:
            return True
    return False

def evaluar_estrategia_torres(tablero, color, jugada, pieza_movida):
    logros = []
    if pieza_movida != chess.ROOK:
        return logros
    to_square = jugada.to_square
    col = chess.square_file(to_square)
    row = chess.square_rank(to_square)
    col_name = chess.FILE_NAMES[col].upper()
    peones_propios = tablero.pieces(chess.PAWN, color)
    peones_rivales = tablero.pieces(chess.PAWN, not color)
    hay_propio = any(chess.square_file(p) == col for p in peones_propios)
    hay_rival = any(chess.square_file(p) == col for p in peones_rivales)
    if not hay_propio and not hay_rival:
        logros.append(f"Torre en columna abierta ({col_name}): Dominio absoluto de una vía libre (Fernández Siles).")
    elif not hay_propio and hay_rival:
        logros.append(f"Torre en columna semiabierta ({col_name}): Presión activa sobre debilidades del rival.")
    torres_en_col = [sq for sq in tablero.pieces(chess.ROOK, color) if chess.square_file(sq) == col]
    if len(torres_en_col) >= 2 and not hay_propio:
        logros.append(f"Torres dobladas en la columna {col_name}: Maniobra activa estrangulando la defensa enemiga.")
    es_octava = (color == chess.WHITE and row == 7) or (color == chess.BLACK and row == 0)
    if es_octava:
        logros.append("Torre en octava fila: Penetración en la retaguardia enemiga contra las bases de peones.")
    return logros

def comprobar_orden_desarrollo(tablero, color, pieza_movida, turno_real):
    advertencias = []
    if turno_real <= 6 and pieza_movida == chess.BISHOP:
        casillas_caballos = [chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8]
        caballos_en_origen = sum(1 for sq in casillas_caballos if tablero.piece_at(sq) and tablero.piece_at(sq).piece_type == chess.KNIGHT)
        if caballos_en_origen == 2:
            advertencias.append("Orden de desarrollo defectuoso: Desarrollaste el alfil antes que los caballos (Grau Tomo I).")
    return advertencias

def comprobar_perdida_tiempo_apertura(tablero, color, jugada, san_jugada, pieza_movida, turno_real, casillas_visitadas):
    advertencias = []
    if turno_real <= 10 and pieza_movida not in [chess.PAWN, chess.KING]:
        if jugada.from_square in casillas_visitadas:
            advertencias.append(f"Pérdida de tiempos ('Tempos') en la apertura con {san_jugada}: Mover dos veces la misma pieza menor cede la iniciativa.")
    return advertencias

def comprobar_error_persistencia(tablero, color, jugada, san_jugada, cpl, turno_real):
    advertencias = []
    if turno_real > 5 and cpl > 150:
        advertencias.append(f"Error de Persistencia (Grau Tomo III, Cap 18) en {san_jugada}: Calculaste asumiendo el estado previo del tablero, olvidando cómo la última jugada abrió líneas o desvió defensores.")
    return advertencias

def comprobar_excesiva_gula(tablero, color, jugada, san_jugada, cpl, turno_real, es_captura):
    advertencias = []
    if es_captura and cpl > 200:
        advertencias.append(f"Excesiva Gula (Grau Tomo II) al capturar con {san_jugada} en T{turno_real}: Caíste en una celada por codicia material inmediata, ignorando las consecuencias posicionales.")
    return advertencias

def comprobar_jugada_anodina_apertura(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if turno_real <= 8 and pieza_movida == chess.PAWN:
        col = chess.square_file(jugada.to_square)
        if col in [0, 7]:
            advertencias.append(f"Jugada Anodina Lateral (Grau Tomo I) con {san_jugada}: Empujes marginales de peón de flanco sin plan centralizado.")
    return advertencias

def comprobar_mal_desarrollo_cronico(tablero, color, turno_real):
    advertencias = []
    if turno_real == 10:
        casillas_inicio = [chess.B1, chess.C1, chess.F1, chess.G1] if color == chess.WHITE else [chess.B8, chess.C8, chess.F8, chess.G8]
        sin_desarrollo = sum(1 for sq in casillas_inicio if tablero.piece_at(sq) and tablero.piece_at(sq).piece_type in [chess.KNIGHT, chess.BISHOP])
        if sin_desarrollo >= 3:
            advertencias.append("Mal Desarrollo Crónico (Grau Tomo I): Movimiento 10 alcanzado con la mayoría de piezas menores inactivas en origen.")
    return advertencias

def comprobar_peon_aislado_central(tablero, color):
    advertencias = []
    peones_propios = tablero.pieces(chess.PAWN, color)
    for col in [3, 4]:
        peon_sqs = [sq for sq in peones_propios if chess.square_file(sq) == col]
        if peon_sqs:
            hay_adyacentes = any(any(chess.square_file(p) == adj_col for p in peones_propios) for adj_col in [col - 1, col + 1] if 0 <= adj_col <= 7)
            if not hay_adyacentes:
                col_name = chess.FILE_NAMES[col].upper()
                advertencias.append(f"Peón Central Aislado (Grau Tomo III, Cap 7) en columna {col_name}: Blanco crónico de bloqueo y asedio en el final.")
    return advertencias

def comprobar_jugada_precaucion_exitosa(tablero, color, jugada, san_jugada, cpl, turno_real, es_de_defensa):
    logros = []
    if turno_real > 5 and cpl < 15 and es_de_defensa and not tablero.is_capture(jugada):
        logros.append(f"Jugada de Precaución Exitosa (Grau Tomo III, Cap 16) con {san_jugada} en T{turno_real}: Prevención estratégica exacta.")
    return logros

def evaluar_conformacion_peones_grau(tablero, color):
    advertencias = []
    peones = tablero.pieces(chess.PAWN, color)
    peones_f = [p for p in peones if chess.square_file(p) == 5]
    if len(peones_f) >= 2:
        advertencias.append("Estructura Defectuosa (Grau Tomo III): Peones doblados en la columna F, desarticulando el enroque.")
    peones_g = [p for p in peones if chess.square_file(p) == 6]
    if len(peones_g) >= 2:
        advertencias.append("Estructura Crítica (Grau Tomo III): Peones doblados en columna G con falta de sostén lateral.")
    return advertencias

def detectar_peon_en_germen(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if pieza_movida == chess.PAWN and turno_real <= 15:
        from_file = chess.square_file(jugada.from_square)
        to_rank = chess.square_rank(jugada.to_square)
        es_avance = (color == chess.WHITE and from_file in [5, 6, 7] and to_rank > 2) or \
                    (color == chess.BLACK and from_file in [5, 6, 7] and to_rank < 5)
        if es_avance:
            advertencias.append(f"Debilidad en Germen (Grau Tomo III) con {san_jugada}: El avance prematuro del peón lateral crea casillas débiles irreversibles.")
    return advertencias

def detectar_dama_prematura_peon_b(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if pieza_movida == chess.QUEEN and turno_real <= 10:
        to_square = jugada.to_square
        if (color == chess.WHITE and to_square == chess.B7) or (color == chess.BLACK and to_square == chess.B2):
            advertencias.append(f"Tentación del Peón B (Grau Tomo III, Cap 12) con {san_jugada}: Desviar la Dama a capturar el peón b expone a tu pieza al encierro.")
    return advertencias

def detectar_dama_prematura(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if turno_real <= 6 and pieza_movida == chess.QUEEN:
        advertencias.append(f"Exposición prematura de la Dama con {san_jugada}: La convierte en blanco de desarrollo de piezas menores enemigas.")
    return advertencias

def detectar_sosten_insuficiente(tablero, color):
    advertencias = []
    valores = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
    for square in chess.SQUARES:
        piece = tablero.piece_at(square)
        if piece and piece.color == color and piece.piece_type != chess.KING:
            atacantes = tablero.attackers(not color, square)
            defensores = tablero.attackers(color, square)
            if atacantes and defensores:
                v_min_at = min(valores[tablero.piece_at(atk).piece_type] for atk in atacantes if tablero.piece_at(atk))
                v_min_df = min(valores[tablero.piece_at(df).piece_type] for df in defensores if tablero.piece_at(df))
                if v_min_df > v_min_at and valores[piece.piece_type] > v_min_at:
                    coord = chess.square_name(square).upper()
                    advertencias.append(f"Sostén Insuficiente en {coord} (Grau Tomo III): Pieza agredida por menor valor y defendida por mayor valor.")
    return advertencias

def evaluar_peones_doblados_c(tablero, color):
    advertencias = []
    peones = tablero.pieces(chess.PAWN, color)
    peones_c = [p for p in peones if chess.square_file(p) == 2]
    if len(peones_c) >= 2:
        peones_d = [p for p in peones if chess.square_file(p) == 3]
        if not peones_d:
            advertencias.append("Estructura de Nottingham Colapsada (Capablanca 1936): Peones doblados en columna C sin soporte del peón D.")
        else:
            for p in peones_d:
                rank = chess.square_rank(p)
                if (color == chess.WHITE and rank > 1) or (color == chess.BLACK and rank < 6):
                    advertencias.append("Debilidad Nottingham-Capablanca: Avanzaste el peón D teniendo peones doblados en C, inmovilizando la estructura.")
                    break
    return advertencias

def evaluar_lpdo(tablero, color, turno_real):
    advertencias = []
    if turno_real > 8:
        piezas_sueltas = [chess.square_name(s).upper() for s in chess.SQUARES if (p := tablero.piece_at(s)) and p.color == color and p.piece_type not in [chess.KING, chess.PAWN] and not tablero.is_attacked_by(color, s)]
        if len(piezas_sueltas) >= 2:
            advertencias.append(f"Peligro LPDO (John Nunn): Múltiples piezas sueltas ({', '.join(piezas_sueltas)}) facilitan tácticas y dobles ataques.")
    return advertencias

def evaluar_profilaxis_descuidada(cpl, turno_real, san_jugada):
    advertencias = []
    if turno_real > 8 and cpl > 150:
        advertencias.append(f"Negligencia Profiláctica (Nimzowitsch) con {san_jugada}: Ignoraste la amenaza rival para ejecutar un plan egoísta ineficaz.")
    return advertencias

def evaluar_alfil_vs_caballo(tablero, color, fase):
    consejos = []
    if fase == "Final":
        mis_alfiles = len(tablero.pieces(chess.BISHOP, color))
        rival_caballos = len(tablero.pieces(chess.KNIGHT, not color))
        if mis_alfiles > 0 and rival_caballos > 0:
            peones_bloqueados = 0
            for square in chess.SQUARES:
                piece = tablero.piece_at(square)
                if piece and piece.piece_type == chess.PAWN:
                    col = chess.square_file(square)
                    row = chess.square_rank(square)
                    next_row = row + 1 if piece.color == chess.WHITE else row - 1
                    if 0 <= next_row <= 7:
                        front_sq = chess.square(col, next_row)
                        fp = tablero.piece_at(front_sq)
                        if fp and fp.piece_type == chess.PAWN:
                            peones_bloqueados += 1
            if peones_bloqueados >= 4:
                consejos.append("Dialéctica Alfil vs Caballo (Grau Tomo IV): Final bloqueado favorece a los caballos. Intenta abrir diagonales.")
    return consejos

def evaluar_centralizacion_dama(tablero, color, jugada, pieza_movida, fase, turno_real):
    logros = []
    if pieza_movida == chess.QUEEN and fase in ["Medio Juego", "Final"]:
        if jugada.to_square in [chess.D4, chess.E4, chess.D5, chess.E5]:
            logros.append(f"Centralización de Dama en T{turno_real} (Grau Tomo IV): Dominio neurálgico del tablero.")
    return logros

def calcular_elo_precision(lista_cpl):
    if not lista_cpl:
        return 100, 100.0
    acpl = sum(lista_cpl) / len(lista_cpl)
    return max(100, int(3000 - (acpl * 14.5))), round(max(0.0, min(100.0, 100 - (acpl / 2.3))), 1)

# =====================================================================
# ENTRADA DE DATOS Y REFLEXIÓN PREVIA
# =====================================================================

with st.expander("📝 Cuestionario de Auto-Reflexión Intelectual (Pedagogía de Grau)", expanded=False):
    st.write("Exige tu honestidad antes de evaluar los datos computacionales:")
    st.text_input("1. ¿En qué fase del juego sientes que colapsó la armonía de tus piezas?")
    st.selectbox("2. ¿Fue tu mayor error de juicio un fallo táctico o de planificación?", 
                 ["Selecciona...", "Fallo táctico (Visión Inmediata)", "Fallo de planificación (Visión Mediata)"])
    st.text_input("3. ¿Colocaste tus peones de acuerdo con la base de planes estáticos de Grau?")

col_izq, col_der = st.columns([1, 2])
with col_izq:
    color_usuario_str = st.selectbox("Tus piezas:", ["Blancas", "Negras"])
    MI_COLOR = chess.WHITE if color_usuario_str == "Blancas" else chess.BLACK
    color_rival = not MI_COLOR
    modo = st.radio("Entrada de la partida:", ["Pegar texto PGN", "Subir archivo .pgn"], horizontal=True)

with col_der:
    pgn_content = ""
    if modo == "Pegar texto PGN":
        pgn_content = st.text_area("Pega aquí el PGN de Chess.com o Lichess:", height=110, placeholder="1. e4 e5 2. Nf3 Nc6...")
    else:
        uploaded_file = st.file_uploader("Sube el archivo .pgn", type=["pgn"])
        if uploaded_file:
            pgn_content = uploaded_file.getvalue().decode("utf-8", errors="replace")

btn_analizar = st.button("🚀 Iniciar Auditoría Implacable", type="primary", use_container_width=True)

# =====================================================================
# EJECUCIÓN DEL ANÁLISIS (con optimizaciones y manejo de errores)
# =====================================================================

if btn_analizar:
    if not pgn_content.strip():
        st.warning("⚠️ Introduce o pega una partida en formato PGN antes de continuar.")
        st.stop()

    RUTA_STOCKFISH = "stockfish-windows-x86-64-avx2.exe"
    if not os.path.exists(RUTA_STOCKFISH):
        RUTA_STOCKFISH = shutil.which("stockfish") or "/usr/games/stockfish"

    try:
        engine = chess.engine.SimpleEngine.popen_uci(RUTA_STOCKFISH)
        engine.configure({"Skill Level": 20})
    except Exception as e:
        st.error(f"Error al iniciar Stockfish: {e}. Ruta intentada: {RUTA_STOCKFISH}")
        st.stop()

    partida = chess.pgn.read_game(io.StringIO(pgn_content.strip()))
    if not partida:
        st.error("No se pudo interpretar el PGN. Verifica el texto.")
        engine.quit()
        st.stop()

    tablero = partida.board()
    jugador = partida.headers.get("White" if MI_COLOR == chess.WHITE else "Black", "Tú")

    mi_cpl, rival_cpl = [], []
    mis_errores_estrategicos = []
    mis_logros = []
    perdidas_analizadas = []
    celadas_tricky = []
    
    estadisticas = {
        "jugadas_attack": 0, "jugadas_defense": 0, "jugadas_neutral": 0, "jugadas_errores": 0,
        "vision_inmediata_fallos": 0, "vision_mediata_fallos": 0
    }

    jugada_contador = 1
    casillas_visitadas_propias = set()
    rey_atascado_advertido = False

    total_moves = sum(1 for _ in partida.mainline())
    progress_bar = st.progress(0, text="Iniciando auditoría...")
    status_text = st.empty()
    
    with st.spinner("Auditoría implacable: calculando variantes de castigo, teoremas de Grau y celadas..."):
        for idx, nodo in enumerate(partida.mainline()):
            progress = (idx + 1) / total_moves
            progress_bar.progress(progress, text=f"Analizando jugada {idx+1} de {total_moves}...")
            status_text.info(f"🔍 Procesando turno {(idx+1)//2 + 1}...")

            jugada = nodo.move
            es_mi_turno = (tablero.turn == MI_COLOR)
            turno_num = (jugada_contador + 1) // 2
            fase = fase_del_juego(tablero, turno_num)
            
            piece = tablero.piece_at(jugada.from_square)
            pieza_tipo = piece.piece_type if piece else None
            san_jugada = tablero.san(jugada)
            tablero_antes = tablero.copy()
            
            limite_actual = chess.engine.Limit(time=0.15)
            info_antes = engine.analyse(tablero, limite_actual)
            eval_antes = 0
            if "score" in info_antes and info_antes["score"]:
                sc = info_antes["score"].pov(tablero.turn).score(mate_score=10000)
                eval_antes = sc if sc is not None else 0
                if abs(eval_antes) > 500:
                    limite_actual = chess.engine.Limit(time=0.05)
                    info_antes = engine.analyse(tablero, limite_actual)
            
            pv_antes = info_antes.get("pv", [])
            mejor_jugada = pv_antes[0] if pv_antes else None
            linea_optima = pv_a_san(tablero, pv_antes, 6)
            
            es_captura = tablero.is_capture(jugada)
            da_jaque = tablero.gives_check(jugada)
            es_de_defensa = (tablero.is_attacked_by(not tablero.turn, jugada.from_square) or tablero.is_check()) if es_mi_turno else False

            if es_mi_turno and turno_num <= 18 and abs(eval_antes) < 300:
                try:
                    for info_alt in engine.analyse(tablero, chess.engine.Limit(time=0.1), multipv=2):
                        pv_alt = info_alt.get("pv", [])
                        if pv_alt and pv_alt[0] != jugada:
                            t_test = tablero.copy()
                            t_test.push(pv_alt[0])
                            if t_test.is_check() or t_test.is_attacked_by(MI_COLOR, chess.F7 if MI_COLOR == chess.WHITE else chess.F2):
                                celadas_tricky.append({
                                    "turno": turno_num,
                                    "jugada_trampa": tablero.san(pv_alt[0]),
                                    "linea": pv_a_san(tablero, pv_alt, 6),
                                    "tablero": tablero_antes,
                                    "movimiento_trampa": pv_alt[0]
                                })
                except Exception:
                    pass

            tablero.push(jugada)
            
            es_de_ataque = False
            if es_mi_turno:
                for sq in tablero.attacks(jugada.to_square):
                    opp_piece = tablero.piece_at(sq)
                    if opp_piece and opp_piece.color == color_rival:
                        es_de_ataque = True
                        break
                es_de_ataque = es_de_ataque or da_jaque or es_captura

            info_despues = engine.analyse(tablero, limite_actual)
            eval_despues = 0
            if "score" in info_despues and info_despues["score"]:
                sc_d = info_despues["score"].pov(not tablero.turn).score(mate_score=10000)
                eval_despues = sc_d if sc_d is not None else 0
                
            pv_castigo = info_despues.get("pv", [])
            linea_castigo = pv_a_san(tablero, pv_castigo, 6)
            cpl = max(0, eval_antes - eval_despues)

            if es_mi_turno:
                mi_cpl.append(cpl)
                
                if cpl > 150:
                    estadisticas["jugadas_errores"] += 1
                elif es_de_ataque:
                    estadisticas["jugadas_attack"] += 1
                elif es_de_defensa:
                    estadisticas["jugadas_defense"] += 1
                else:
                    estadisticas["jugadas_neutral"] += 1

                if cpl > 200:
                    estadisticas["vision_inmediata_fallos"] += 1
                elif cpl > 60:
                    estadisticas["vision_mediata_fallos"] += 1

                turn_concepts = []
                
                outposts = detectar_outposts(tablero_antes, MI_COLOR)
                if outposts and cpl > 30:
                    turn_concepts.append(f"Outpost disponible en {chess.square_name(outposts[0]).upper()} para un caballo. Posibilidad de dominio posicional.")
                
                if fase == "Final":
                    peones_pasados = detectar_peon_pasado(tablero, MI_COLOR)
                    if peones_pasados:
                        turn_concepts.append(f"Peón pasado en {chess.square_name(peones_pasados[0]).upper()} - factor decisivo en el final.")
                
                debilidades = detectar_debilidades_estructurales(tablero, MI_COLOR)
                if debilidades:
                    turn_concepts.extend(debilidades)
                
                if caballo_en_el_borde(jugada, pieza_tipo) and cpl > 30:
                    turn_concepts.append("Caballo marginado en la banda: Pérdida de influencia central (Tarrasch / Grau).")
                if detectar_alfil_malo(tablero, MI_COLOR) and cpl > 40 and fase == "Medio Juego":
                    turn_concepts.append("Alfil aprisionado ('Alfil Malo'): Bloqueado tras tus propias cadenas de peones fijadas.")
                
                turn_concepts.extend(comprobar_orden_desarrollo(tablero_antes, MI_COLOR, pieza_tipo, turno_num))
                turn_concepts.extend(comprobar_perdida_tiempo_apertura(tablero_antes, MI_COLOR, jugada, san_jugada, pieza_tipo, turno_num, casillas_visitadas_propias))
                turn_concepts.extend(comprobar_error_persistencia(tablero_antes, MI_COLOR, jugada, san_jugada, cpl, turno_num))
                turn_concepts.extend(comprobar_excesiva_gula(tablero_antes, MI_COLOR, jugada, san_jugada, cpl, turno_num, es_captura))
                turn_concepts.extend(comprobar_jugada_anodina_apertura(tablero_antes, MI_COLOR, jugada, san_jugada, pieza_tipo, turno_num))
                turn_concepts.extend(comprobar_mal_desarrollo_cronico(tablero, MI_COLOR, turno_num))
                turn_concepts.extend(comprobar_peon_aislado_central(tablero, MI_COLOR))
                turn_concepts.extend(evaluar_conformacion_peones_grau(tablero, MI_COLOR))
                turn_concepts.extend(detectar_peon_en_germen(tablero_antes, MI_COLOR, jugada, san_jugada, pieza_tipo, turno_num))
                turn_concepts.extend(detectar_dama_prematura_peon_b(tablero_antes, MI_COLOR, jugada, san_jugada, pieza_tipo, turno_num))
                turn_concepts.extend(detectar_dama_prematura(tablero_antes, MI_COLOR, jugada, san_jugada, pieza_tipo, turno_num))
                turn_concepts.extend(detectar_sosten_insuficiente(tablero, MI_COLOR))
                turn_concepts.extend(evaluar_peones_doblados_c(tablero, MI_COLOR))
                turn_concepts.extend(evaluar_lpdo(tablero, MI_COLOR, turno_num))
                turn_concepts.extend(evaluar_profilaxis_descuidada(cpl, turno_num, san_jugada))
                turn_concepts.extend(evaluar_alfil_vs_caballo(tablero, MI_COLOR, fase))

                rey_sq_init = chess.E1 if MI_COLOR == chess.WHITE else chess.E8
                if turno_num == 12 and tablero.king(MI_COLOR) == rey_sq_init and not rey_atascado_advertido:
                    turn_concepts.append("Negligencia de Enroque (Grau Tomo I): Medio juego alcanzado con el rey vulnerable en el centro.")
                    rey_atascado_advertido = True

                for tc in turn_concepts:
                    if tc not in mis_errores_estrategicos:
                        mis_errores_estrategicos.append(tc)

                if torre_en_septima(jugada, pieza_tipo, MI_COLOR):
                    mis_logros.append(f"Torre en séptima fila en T{turno_num}: Dominio activo según Fernández Siles.")
                mis_logros.extend(evaluar_estrategia_torres(tablero, MI_COLOR, jugada, pieza_tipo))
                mis_logros.extend(evaluar_centralizacion_dama(tablero, MI_COLOR, jugada, pieza_tipo, fase, turno_num))
                mis_logros.extend(comprobar_jugada_precaucion_exitosa(tablero_antes, MI_COLOR, jugada, san_jugada, cpl, turno_num, es_de_defensa))

                casillas_visitadas_propias.add(jugada.to_square)

                if cpl >= 75 and mejor_jugada and jugada != mejor_jugada:
                    tipo_fallo = "Error Grave (Blunder)" if cpl >= 180 else "Imprecisión / Error"
                    perdidas_analizadas.append({
                        "turno": turno_num,
                        "tipo": tipo_fallo,
                        "cpl": cpl,
                        "jugada_hecha": san_jugada,
                        "mejor_jugada_san": tablero_antes.san(mejor_jugada),
                        "linea_optima": linea_optima,
                        "linea_castigo": linea_castigo,
                        "tablero_antes": tablero_antes,
                        "jugada_obj": jugada,
                        "mejor_obj": mejor_jugada,
                        "conceptos": turn_concepts
                    })
            else:
                rival_cpl.append(cpl)

            jugada_contador += 1

    progress_bar.empty()
    status_text.empty()
    engine.quit()

    elo_est, prec_est = calcular_elo_precision(mi_cpl)
    total_moves = max(1, len(mi_cpl))
    p_att = round((estadisticas["jugadas_attack"] / total_moves) * 100, 1)
    p_def = round((estadisticas["jugadas_defense"] / total_moves) * 100, 1)
    p_neu = round((estadisticas["jugadas_neutral"] / total_moves) * 100, 1)
    p_err = round((estadisticas["jugadas_errores"] / total_moves) * 100, 1)

    # =====================================================================
    # PANEL DE RESULTADOS (DASHBOARD)
    # =====================================================================
    st.markdown("---")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">👤</div>
            <div class="metric-value">{jugador}</div>
            <div class="metric-label">Jugador auditado</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-value">{prec_est}%</div>
            <div class="metric-label">Precisión Analítica</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">🏆</div>
            <div class="metric-value">{elo_est}</div>
            <div class="metric-label">Elo Estimado</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon">⚠️</div>
            <div class="metric-value">{len(perdidas_analizadas)}</div>
            <div class="metric-label">Errores Graves</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("📊 Perfil de Decisiones de Grau (Tomo I)", expanded=False):
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        c_p1.metric("⚔️ Iniciativa / Ataque", f"{p_att}%")
        c_p2.metric("🛡️ Defensa / Reacción", f"{p_def}%")
        c_p3.metric("🔄 Desarrollo / Neutras", f"{p_neu}%")
        c_p4.metric("🛑 Jugadas Defectuosas", f"{p_err}%")
        st.caption(f"Fallas de Visión Inmediata (Táctica): **{estadisticas['vision_inmediata_fallos']}** | Desvíos de Visión Mediata (Estrategia): **{estadisticas['vision_mediata_fallos']}**")

    tab_errores, tab_trucos, tab_estrategia, tab_retos = st.tabs([
        f"🚨 Errores y Pérdidas ({len(perdidas_analizadas)})", 
        f"⚡ Celadas Omitidas ({len(celadas_tricky)})", 
        f"🧠 Diagnóstico Grau ({len(mis_errores_estrategicos)})",
        "🎯 Retos de Maestría"
    ])

    with tab_errores:
        if not perdidas_analizadas:
            st.success("✨ ¡Partida formidable! No se detectaron errores tácticos graves ni imprecisiones mayores a 0.75 peones.")
        else:
            perdidas_analizadas.sort(key=lambda x: x["cpl"], reverse=True)
            for i, item in enumerate(perdidas_analizadas, 1):
                badge = f'<span class="badge-blunder">💥 Error Grave (-{item["cpl"]/100:.1f})</span>' if "Grave" in item["tipo"] else f'<span class="badge-mistake">⚠️ Imprecisión (-{item["cpl"]/100:.1f})</span>'
                
                st.markdown(f"""
                <div class="card-error">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <span style="font-size:1.15rem; font-weight:700;">#{i} • Turno {item['turno']}</span>
                        {badge}
                    </div>
                """, unsafe_allow_html=True)
                
                col_tablero, col_lineas = st.columns([1.1, 1.9])
                with col_tablero:
                    svg_html = generar_tablero_svg(item["tablero_antes"], item["jugada_obj"], item["mejor_obj"], MI_COLOR)
                    st.markdown(svg_html, unsafe_allow_html=True)
                    st.caption("<center>🔴 Tu jugada | 🟢 Alternativa sugerida</center>", unsafe_allow_html=True)
                
                with col_lineas:
                    st.markdown(f"**Tu jugada:** :red[**{item['jugada_hecha']}**]")
                    st.markdown("**Castigo del rival a 6 jugadas:**")
                    st.code(item["linea_castigo"] if item["linea_castigo"] else "Sin castigo directo forzado.", language="text")
                    
                    st.markdown(f"**Mejor jugada Stockfish:** :green[**{item['mejor_jugada_san']}**]")
                    st.markdown("**Línea óptima completa:**")
                    st.code(item["linea_optima"], language="text")
                    
                    if item["conceptos"]:
                        st.markdown("**Diagnóstico teórico:**")
                        for c in item["conceptos"]:
                            st.info(f"💡 {c}")

                st.markdown("</div>", unsafe_allow_html=True)

    with tab_trucos:
        if not celadas_tricky:
            st.info("La partida discurrió por cauces estrictamente sólidos; no hubo celadas tácticas omitidas.")
        else:
            vistos = set()
            unicas = [c for c in celadas_tricky if not (c["turno"] in vistos or vistos.add(c["turno"]))][:4]
            for t_item in unicas:
                st.markdown(f"""
                <div class="card-error">
                    <span style="font-weight:700; font-size:1.05rem;">Turno {t_item['turno']} • Celada Táctica: {t_item['jugada_trampa']}</span>
                """, unsafe_allow_html=True)
                c_tab, c_det = st.columns([1.1, 1.9])
                with c_tab:
                    svg_t = generar_tablero_svg(t_item["tablero"], mejor_jugada=t_item["movimiento_trampa"], color_usuario=MI_COLOR)
                    st.markdown(svg_t, unsafe_allow_html=True)
                with c_det:
                    st.markdown("**Secuencia táctica calculada:**")
                    st.code(t_item["linea"], language="text")
                    st.caption("Ataque directo a debilidades inmediatas o presión sobre casillas sensibles (f7/f2).")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_estrategia:
        col_err, col_log = st.columns(2)
        with col_err:
            st.subheader("🛑 Puntos Ciegos y Debilidades Estructurales")
            if not mis_errores_estrategicos:
                st.success("No se detectaron infracciones estructurales según los tomos de Grau.")
            else:
                for err_str in list(set(mis_errores_estrategicos)):
                    st.warning(f"• {err_str}")
        with col_log:
            st.subheader("🎖 Logros Posicionales y Profilaxis")
            if not mis_logros:
                st.info("No se registraron maniobras activas de torre ni centralización destacada.")
            else:
                for logro in list(set(mis_logros)):
                    st.success(f"• {logro}")

    with tab_retos:
        st.subheader("🧠 Preguntas Pedagógicas para Auto-Auditoría")
        st.write("Roberto Grau sostenía que la maestría nace de la autocrítica profunda. Responde mentalmente:")
        
        if perdidas_analizadas:
            peor = perdidas_analizadas[0]
            st.markdown(f"""
            **1. El Dilema del Cálculo:**  
            Tu mayor imprecisión ocurrió en el **Turno {peor['turno']}** jugando `{peor['jugada_hecha']}`.  
            *¿Por qué tu visión inmediata no detectó el castigo? ¿Fue fatiga cognitiva, Síndrome de Kotov (calcular muchas variantes y elegir la equivocada), o simple impulsividad?*
            """)
        else:
            st.markdown("**1. El Dilema del Cálculo:** Jugaste con notable pulcritud táctica. ¿Calculaste activamente atacantes y defensores o tu rival no te presionó?")

        st.markdown("""
        **2. El Enigma de la Estructura de Peones:**  
        *Como explica Grau, una debilidad estática (peón retrasado, aislado o doblado) condena al final pasivo. Si provocaste debilidades en tus cadenas, ¿qué compensación dinámica inmediata creíste tener a cambio?*
        """)

        st.markdown("""
        **3. La Activación de las Torres:**  
        *Luis Fernández Siles enseña que una torre pasiva es una pieza inexistente. ¿Disputaste las columnas abiertas del tablero con anticipación o permitiste que el rival las colonizara primero?*
        """)
