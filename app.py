import os
import io
import shutil
import base64
import streamlit as st
import chess
import chess.pgn
import chess.svg
import chess.engine

# =====================================================================
# CONFIGURACIÓN Y ESTILOS VISUALES MINIMALISTAS
# =====================================================================
st.set_page_config(page_title="Coach Ajedrez Élite", page_icon="♟️", layout="wide")

st.markdown("""
<style>
    .main-title {
        text-align: center;
        font-size: 2.1rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        text-align: center;
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .card-error {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 18px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .badge-blunder {
        background-color: #fee2e2;
        color: #b91c1c;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
    .badge-mistake {
        background-color: #fef3c7;
        color: #b45309;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">♟️ COACH DE AJEDREZ ÉLITE</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Auditoría implacable: evaluación posicional, castigos tácticos y líneas completas.</div>', unsafe_allow_html=True)

# =====================================================================
# MOTORES DE DIAGNÓSTICO ESTRUCTURAL Y TÁCTICO
# =====================================================================

def pv_a_san(tablero_origen, lista_movimientos, limite_jugadas=6):
    """Convierte una lista de movimientos UCI en notación SAN legible."""
    t = tablero_origen.copy()
    secuencia = []
    for m in lista_movimientos[:limite_jugadas]:
        try:
            secuencia.append(t.san(m))
            t.push(m)
        except Exception:
            break
    return " → ".join(secuencia)

def generar_tablero_svg(tablero, jugada_jugada=None, mejor_jugada=None, color_usuario=chess.WHITE):
    """Crea la imagen del tablero con flechas indicativas."""
    flechas = []
    if jugada_jugada:
        flechas.append(chess.svg.Arrow(jugada_jugada.from_square, jugada_jugada.to_square, color="#dc2626"))  # Flecha roja
    if mejor_jugada:
        flechas.append(chess.svg.Arrow(mejor_jugada.from_square, mejor_jugada.to_square, color="#16a34a"))  # Flecha verde
    
    svg_data = chess.svg.board(
        board=tablero,
        orientation=color_usuario,
        arrows=flechas,
        size=310
    )
    b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
    return f'<div style="display:flex; justify-content:center;"><img src="data:image/svg+xml;base64,{b64}" style="width:100%; max-width:310px; border-radius:8px; box-shadow:0 3px 6px rgba(0,0,0,0.12);"/></div>'

def detectar_diagnostico_conceptual(tablero, color, jugada, pieza_movida, turno_real, cpl):
    conceptos = []
    # Alfil malo
    alfiles = tablero.pieces(chess.BISHOP, color)
    peones = tablero.pieces(chess.PAWN, color)
    for a in alfiles:
        c_casilla = (chess.square_rank(a) + chess.square_file(a)) % 2
        if sum(1 for p in peones if (chess.square_rank(p) + chess.square_file(p)) % 2 == c_casilla) >= 4 and cpl > 50:
            conceptos.append("Alfil Malo: Bloqueado tras tu propia cadena de peones.")
            break
    # Caballo en banda
    if pieza_movida == chess.KNIGHT and chess.square_file(jugada.to_square) in [0, 7] and cpl > 40:
        conceptos.append("Caballo Marginado: En la banda ('Knight on the rim is dim').")
    # LPDO John Nunn
    piezas_sin_defensa = sum(1 for s in chess.SQUARES if tablero.piece_at(s) and tablero.piece_at(s).color == color and tablero.piece_at(s).piece_type not in [chess.KING, chess.PAWN] and not tablero.is_attacked_by(color, s))
    if piezas_sin_defensa >= 2:
        conceptos.append("Peligro LPDO (Nunn): Demasiadas piezas desprotegidas en el tablero.")
    # Tiempos de apertura
    if turno_real <= 7 and pieza_movida == chess.BISHOP:
        caballos = [chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8]
        if sum(1 for sq in caballos if tablero.piece_at(sq) and tablero.piece_at(sq).piece_type == chess.KNIGHT) == 2:
            conceptos.append("Fallo de Desarrollo (Grau): Desarrollaste alfiles antes que caballos.")
    return conceptos

def calcular_elo_precision(lista_cpl):
    if not lista_cpl: return 100, 100.0
    acpl = sum(lista_cpl) / len(lista_cpl)
    return max(100, int(3000 - (acpl * 14.5))), round(max(0.0, min(100.0, 100 - (acpl / 2.3))), 1)

# =====================================================================
# ENTRADA DE DATOS
# =====================================================================

col_izq, col_der = st.columns([1, 2])

with col_izq:
    color_usuario_str = st.selectbox("Tus piezas:", ["Blancas", "Negras"])
    MI_COLOR = chess.WHITE if color_usuario_str == "Blancas" else chess.BLACK
    modo = st.radio("Entrada de la partida:", ["Pegar texto PGN", "Subir archivo .pgn"], horizontal=True)

with col_der:
    pgn_content = ""
    if modo == "Pegar texto PGN":
        pgn_content = st.text_area("Pega el PGN de Chess.com o Lichess aquí:", height=110, placeholder="[Event ...]\n1. e4 e5 2. Nf3 ...")
    else:
        uploaded_file = st.file_uploader("Sube el archivo PGN", type=["pgn"])
        if uploaded_file:
            pgn_content = uploaded_file.getvalue().decode("utf-8", errors="replace")

btn_analizar = st.button("🚀 Iniciar Auditoría Implacable", type="primary", use_container_width=True)

# =====================================================================
# EJECUCIÓN DEL ANÁLISIS
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
        st.error(f"Error al iniciar el motor Stockfish: {e}")
        st.stop()

    partida = chess.pgn.read_game(io.StringIO(pgn_content.strip()))
    if not partida:
        st.error("No se pudo interpretar el PGN. Verifica el texto ingresado.")
        engine.quit()
        st.stop()

    tablero = partida.board()
    limite = chess.engine.Limit(time=0.15)
    jugador = partida.headers.get("White" if MI_COLOR == chess.WHITE else "Black", "Tú")

    lista_cpl = []
    perdidas_analizadas = []
    celadas_tricky = []
    
    with st.spinner("Auditoría en curso: analizando variantes tácticas y posiciones críticas..."):
        jugada_contador = 1
        for nodo in partida.mainline():
            jugada = nodo.move
            es_mi_turno = (tablero.turn == MI_COLOR)
            turno_num = (jugada_contador + 1) // 2
            
            piece = tablero.piece_at(jugada.from_square)
            pieza_tipo = piece.piece_type if piece else None
            san_jugada = tablero.san(jugada)
            
            tablero_antes = tablero.copy()
            
            # 1. Análisis antes de la jugada
            info_antes = engine.analyse(tablero, limite)
            eval_antes = 0
            if "score" in info_antes and info_antes["score"]:
                eval_score = info_antes["score"].pov(tablero.turn).score(mate_score=10000)
                eval_antes = eval_score if eval_score is not None else 0
            
            pv_antes = info_antes.get("pv", [])
            mejor_jugada = pv_antes[0] if pv_antes else None
            linea_optima = pv_a_san(tablero, pv_antes, 6)
            
            # Celadas / Oportunidades tácticas
            if es_mi_turno and turno_num <= 18:
                try:
                    multipv = engine.analyse(tablero, limite, multipv=2)
                    for info_alt in multipv:
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
            
            # 2. Análisis después de la jugada
            info_despues = engine.analyse(tablero, limite)
            eval_despues = 0
            if "score" in info_despues and info_despues["score"]:
                eval_score_d = info_despues["score"].pov(not tablero.turn).score(mate_score=10000)
                eval_despues = eval_score_d if eval_score_d is not None else 0
                
            pv_castigo = info_despues.get("pv", [])
            linea_castigo = pv_a_san(tablero, pv_castigo, 6)
            
            cpl = max(0, eval_antes - eval_despues)
            
            if es_mi_turno:
                lista_cpl.append(cpl)
                # Detección de errores notables (pérdida >= 0.75 peones)
                if cpl >= 75 and mejor_jugada and jugada != mejor_jugada:
                    conceptos = detectar_diagnostico_conceptual(tablero_antes, MI_COLOR, jugada, pieza_tipo, turno_num, cpl)
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
                        "conceptos": conceptos
                    })
            
            jugada_contador += 1

    engine.quit()

    elo_est, prec_est = calcular_elo_precision(lista_cpl)

    # =====================================================================
    # PANEL DE RESULTADOS
    # =====================================================================
    st.markdown("---")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Jugador auditado", jugador)
    m2.metric("Precisión Analítica", f"{prec_est}%")
    m3.metric("Elo Rendimiento", elo_est)
    m4.metric("Errores detectados", len(perdidas_analizadas))

    tab_errores, tab_trucos, tab_resumen = st.tabs([
        f"🚨 Errores y Pérdidas ({len(perdidas_analizadas)})", 
        f"⚡ Celadas Omitidas ({len(celadas_tricky)})", 
        "🧠 Diagnóstico Estructural"
    ])

    with tab_errores:
        if not perdidas_analizadas:
            st.success("✨ ¡Partida limpia! No se detectaron errores graves ni pérdidas tácticas superiores a 0.75 puntos.")
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
                    st.caption("<center>🔴 Jugada hecha | 🟢 Alternativa recomendada</center>", unsafe_allow_html=True)
                
                with col_lineas:
                    st.markdown(f"**Tu jugada:** :red[**{item['jugada_hecha']}**]")
                    st.markdown("**Línea de castigo del rival:**")
                    st.code(item["linea_castigo"] if item["linea_castigo"] else "Sin castigo directo forzado.", language="text")
                    
                    st.markdown(f"**Mejor jugada Stockfish:** :green[**{item['mejor_jugada_san']}**]")
                    st.markdown("**Línea óptima completa:**")
                    st.code(item["linea_optima"], language="text")
                    
                    if item["conceptos"]:
                        st.markdown("**Diagnóstico conceptual:**")
                        for c in item["conceptos"]:
                            st.info(f"💡 {c}")

                st.markdown("</div>", unsafe_allow_html=True)

    with tab_trucos:
        if not celadas_tricky:
            st.info("La partida fue sólida; no surgieron celadas tácticas sorpresivas en la apertura.")
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
                    st.markdown("**Secuencia táctica a 6 jugadas:**")
                    st.code(t_item["linea"], language="text")
                    st.caption("Ataque directo a debilidades tácticas inmediatas (jaques o presión f7/f2).")
                st.markdown("</div>", unsafe_allow_html=True)

    with tab_resumen:
        st.subheader("Patrones Posicionales Detectados")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🛡️ Seguridad del Rey y Estructura")
            st.write("- **Fórmula de Dorfman:** La ventaja estática no compensa un rey desprotegido.")
            st.write("- **Apertura:** Cuida el orden de piezas menores (caballos antes de alfiles según Grau).")
        with c2:
            st.markdown("#### 🎯 Dinámica de Piezas")
            st.write("- **Regla de John Nunn (LPDO):** Evita tener 2 o más piezas sueltas sin defensa.")
            st.write("- **Torres:** Ocupa columnas abiertas o semiabiertas activamente.")
