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
# CONFIGURACIÓN Y ESTILOS VISUALES (UI PREMIUM)
# =====================================================================
st.set_page_config(page_title="Coach de Ajedrez Élite", page_icon="♟️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    .stApp { background: #f8fafc; }
    .main-title {
        text-align: center; font-size: 2.5rem; font-weight: 800;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem; letter-spacing: -0.5px;
    }
    .sub-title {
        text-align: center; color: #64748b; font-size: 1rem;
        margin-bottom: 2rem; font-weight: 300; letter-spacing: 1px;
    }
    .card-error {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px;
        padding: 24px; margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: all 0.2s ease;
    }
    .card-error:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08); }
    .badge-blunder { background: #fee2e2; color: #991b1b; font-weight: 700; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; border: 1px solid #fecaca; display: inline-block; }
    .badge-mistake { background: #fef3c7; color: #92400e; font-weight: 700; padding: 6px 14px; border-radius: 8px; font-size: 0.8rem; border: 1px solid #fde68a; display: inline-block; }
    .board-container { display: flex; justify-content: center; align-items: center; width: 100%; }
    .board-container img { max-width: 100%; height: auto; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07); border: 1px solid #e2e8f0; }
    .stProgress > div > div > div > div { background: linear-gradient(90deg, #3b82f6, #8b5cf6); }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">♟️ COACH DE AJEDREZ ÉLITE</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Análisis Posicional Avanzado • Grau • Dorfman • Nunn • Stockfish</div>', unsafe_allow_html=True)

# =====================================================================
# MOTORES DE DIAGNÓSTICO
# =====================================================================

def pv_a_san(tablero_origen, lista_movimientos, limite_jugadas=6):
    t = tablero_origen.copy()
    secuencia = []
    for m in lista_movimientos[:limite_jugadas]:
        try:
            secuencia.append(t.san(m))
            t.push(m)
        except Exception: break
    return " → ".join(secuencia)

def detectar_outposts(tablero, color):
    outposts = []
    enemy_pawns = tablero.pieces(chess.PAWN, not color)
    attacked_by_pawns = set()
    for pawn in enemy_pawns:
        attacked_by_pawns.update(tablero.attacks(pawn))
    
    for square in chess.SQUARES:
        row, col = chess.square_rank(square), chess.square_file(square)
        if (color == chess.WHITE and row < 4) or (color == chess.BLACK and row > 3): continue
        if square not in attacked_by_pawns and not tablero.piece_at(square):
            outposts.append(square)
    return outposts[:6]

def generar_tablero_svg(tablero, jugada_jugada=None, mejor_jugada=None, color_usuario=chess.WHITE, size=310):
    flechas = []
    if jugada_jugada: flechas.append(chess.svg.Arrow(jugada_jugada.from_square, jugada_jugada.to_square, color="#dc2626", opacity=0.8))
    if mejor_jugada: flechas.append(chess.svg.Arrow(mejor_jugada.from_square, mejor_jugada.to_square, color="#16a34a", opacity=0.8))
    
    outposts = detectar_outposts(tablero, color_usuario)
    svg_data = chess.svg.board(board=tablero, orientation=color_usuario, arrows=flechas, size=size, squares=chess.SquareSet(outposts))
    b64 = base64.b64encode(svg_data.encode("utf-8")).decode("utf-8")
    return f'<div class="board-container"><img src="data:image/svg+xml;base64,{b64}" style="width:100%; max-width:{size}px;"/></div>'

def calcular_elo_precision(lista_cpl):
    if not lista_cpl: return 100, 100.0
    acpl = sum(lista_cpl) / len(lista_cpl)
    return max(100, int(3000 - (acpl * 14.5))), round(max(0.0, min(100.0, 100 - (acpl / 2.3))), 1)

def evaluar_material(tablero, color):
    v = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    return sum(len(tablero.pieces(p, color)) * v.get(p, 0) for p in v)

def fase_del_juego(tablero, turno):
    if turno <= 10: return "Apertura"
    if not tablero.pieces(chess.QUEEN, chess.WHITE) and not tablero.pieces(chess.QUEEN, chess.BLACK): return "Final"
    return "Medio Juego"

def obtener_conceptos_grau(tablero, tablero_antes, color, jugada, san_jugada, cpl, turno, es_captura):
    conceptos = []
    pieza = tablero_antes.piece_at(jugada.from_square)
    ptype = pieza.piece_type if pieza else None
    
    if ptype == chess.KNIGHT and chess.square_file(jugada.to_square) in [0, 7] and cpl > 30:
        conceptos.append("Caballo marginado en la banda (Tarrasch / Grau).")
    if ptype == chess.BISHOP and turno <= 6 and sum(1 for sq in ([chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8]) if tablero_antes.piece_at(sq) and tablero_antes.piece_at(sq).piece_type == chess.KNIGHT) == 2:
        conceptos.append("Orden defectuoso: Alfil antes que caballos (Grau Tomo I).")
    if turno > 5 and cpl > 150:
        conceptos.append("Error de Persistencia: Cálculo basado en el tablero pasado, ignorando cambios (Tomo III).")
    if es_captura and cpl > 200:
        conceptos.append("Excesiva Gula: Celada material que ignora el colapso posicional (Tomo II).")
    if ptype == chess.PAWN and turno <= 8 and chess.square_file(jugada.to_square) in [0, 7]:
        conceptos.append("Jugada Anodina: Empuje lateral temprano sin plan central.")
    if turno == 10 and sum(1 for sq in ([chess.B1, chess.C1, chess.F1, chess.G1] if color == chess.WHITE else [chess.B8, chess.C8, chess.F8, chess.G8]) if tablero.piece_at(sq) and tablero.piece_at(sq).piece_type in [chess.KNIGHT, chess.BISHOP]) >= 3:
        conceptos.append("Mal Desarrollo Crónico: Mayoría de piezas menores en origen en T10.")
    if ptype == chess.QUEEN and turno <= 10 and jugada.to_square in [chess.B7, chess.B2]:
        conceptos.append("Tentación del Peón B: Dama expuesta al encierro por codicia (Tomo III).")
    
    sueltas = [chess.square_name(s).upper() for s in chess.SQUARES if (p := tablero.piece_at(s)) and p.color == color and p.piece_type not in [chess.KING, chess.PAWN] and not tablero.is_attacked_by(color, s)]
    if len(sueltas) >= 2: conceptos.append(f"Peligro LPDO (Nunn): Piezas sueltas facilitan tácticas ({', '.join(sueltas)}).")
    
    return conceptos

# =====================================================================
# ENTRADA DE DATOS Y UI
# =====================================================================
col_izq, col_der = st.columns([1, 2])
with col_izq:
    MI_COLOR = chess.WHITE if st.selectbox("Tus piezas:", ["Blancas", "Negras"]) == "Blancas" else chess.BLACK
    modo = st.radio("Entrada:", ["Pegar PGN", "Subir .pgn"], horizontal=True)

with col_der:
    pgn_content = st.text_area("PGN:", height=110) if modo == "Pegar PGN" else (f.getvalue().decode() if (f := st.file_uploader("PGN", type=["pgn"])) else "")

if st.button("🚀 Iniciar Auditoría Implacable", type="primary", use_container_width=True):
    if not pgn_content.strip():
        st.warning("Introduce un PGN válido.")
        st.stop()

    sf_path = "stockfish-windows-x86-64-avx2.exe" if os.path.exists("stockfish-windows-x86-64-avx2.exe") else (shutil.which("stockfish") or "/usr/games/stockfish")
    try:
        engine = chess.engine.SimpleEngine.popen_uci(sf_path)
    except Exception as e:
        st.error(f"Error Stockfish: {e}"); st.stop()

    partida = chess.pgn.read_game(io.StringIO(pgn_content.strip()))
    if not partida:
        st.error("PGN inválido."); engine.quit(); st.stop()

    tablero = partida.board()
    lista_movimientos = list(partida.mainline_moves())
    total_moves = len(lista_movimientos)
    jugador = partida.headers.get("White" if MI_COLOR == chess.WHITE else "Black", "Tú")

    mi_cpl, perdidas, celadas = [], [], []
    stats = {"att": 0, "def": 0, "neu": 0, "err": 0}
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, move in enumerate(lista_movimientos):
        status_text.text(f"Analizando jugada {idx + 1} de {total_moves}...")
        progress_bar.progress((idx + 1) / total_moves)
        
        is_my_turn = (tablero.turn == MI_COLOR)
        turn_num = (idx // 2) + 1
        san_move = tablero.san(move)
        b_before = tablero.copy()
        
        # Optimización de Motor: Limitar tiempo si hay desequilibrio masivo
        limit_time = 0.15
        
        info_b = engine.analyse(tablero, chess.engine.Limit(time=limit_time))
        eval_b = info_b["score"].pov(tablero.turn).score(mate_score=10000) or 0
        best_move = info_b.get("pv", [None])[0]
        opt_line = pv_a_san(tablero, info_b.get("pv", []))
        
        # MultiPV para celadas (solo apertura)
        if is_my_turn and turn_num <= 18:
            try:
                for alt in engine.analyse(tablero, chess.engine.Limit(depth=12), multipv=2):
                    if (pv := alt.get("pv")) and pv[0] != move:
                        t_test = tablero.copy(); t_test.push(pv[0])
                        if t_test.is_check() or t_test.is_attacked_by(MI_COLOR, chess.F7 if MI_COLOR == chess.WHITE else chess.F2):
                            celadas.append({"turn": turn_num, "san": tablero.san(pv[0]), "line": pv_a_san(tablero, pv), "b": b_before, "m": pv[0]})
            except: pass

        es_capt = tablero.is_capture(move)
        tablero.push(move)
        
        info_a = engine.analyse(tablero, chess.engine.Limit(time=limit_time))
        eval_a = info_a["score"].pov(not tablero.turn).score(mate_score=10000) or 0
        punish_line = pv_a_san(tablero, info_a.get("pv", []))
        
        cpl = max(0, eval_b - eval_a)
        
        if is_my_turn:
            mi_cpl.append(cpl)
            if cpl > 150: stats["err"] += 1
            elif tablero.is_check() or es_capt: stats["att"] += 1
            else: stats["neu"] += 1

            if cpl >= 75 and best_move and move != best_move:
                perdidas.append({
                    "turn": turn_num, "cpl": cpl, "played": san_move, "best": b_before.san(best_move),
                    "opt": opt_line, "punish": punish_line, "b": b_before, "move": move, "best_m": best_move,
                    "diag": obtener_conceptos_grau(tablero, b_before, MI_COLOR, move, san_move, cpl, turn_num, es_capt)
                })

    engine.quit()
    status_text.empty()
    progress_bar.empty()

    # =====================================================================
    # DASHBOARD DE RESULTADOS
    # =====================================================================
    elo, prec = calcular_elo_precision(mi_cpl)
    
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👤 Jugador", jugador)
    m2.metric("🎯 Precisión", f"{prec}%")
    m3.metric("🏆 Elo Rendimiento", elo)
    m4.metric("🚨 Fallos Graves", len(perdidas))

    t_err, t_cel = st.tabs([f"🚨 Errores y Castigos ({len(perdidas)})", f"⚡ Celadas Omitidas ({len(celadas)})"])
    
    with t_err:
        if not perdidas: st.success("¡Partida impecable! No hay imprecisiones graves.")
        perdidas.sort(key=lambda x: x["cpl"], reverse=True)
        for i, p in enumerate(perdidas, 1):
            badge = f'<span class="badge-blunder">💥 Blunder (-{p["cpl"]/100:.1f})</span>' if p["cpl"] > 180 else f'<span class="badge-mistake">⚠️ Error (-{p["cpl"]/100:.1f})</span>'
            st.markdown(f'<div class="card-error"><div style="display:flex; justify-content:space-between; margin-bottom:15px;"><b>#{i} • Turno {p["turn"]}</b>{badge}</div>', unsafe_allow_html=True)
            
            c_svg, c_txt = st.columns([1, 1.8])
            with c_svg:
                st.markdown(generar_tablero_svg(p["b"], p["move"], p["best_m"], MI_COLOR), unsafe_allow_html=True)
                st.caption("<center>🔴 Tu jugada | 🟢 Alternativa | 🟦 Casillas Fuertes</center>", unsafe_allow_html=True)
            with c_txt:
                st.write(f"**Tu jugada:** :red[{p['played']}]")
                st.code(p["punish"] or "Sin castigo forzado.")
                st.write(f"**Mejor jugada:** :green[{p['best']}]")
                st.code(p["opt"])
                for d in p["diag"]: st.info(f"💡 {d}")
            st.markdown('</div>', unsafe_allow_html=True)

    with t_cel:
        if not celadas: st.info("No hubo tácticas agudas omitidas en la apertura.")
        seen = set()
        for c in [x for x in celadas if not (x["turn"] in seen or seen.add(x["turn"]))][:4]:
            st.markdown(f'<div class="card-error"><b>Turno {c["turn"]} • Oportunidad: {c["san"]}</b>', unsafe_allow_html=True)
            cs, ct = st.columns([1, 1.8])
            with cs: st.markdown(generar_tablero_svg(c["b"], mejor_jugada=c["m"], color_usuario=MI_COLOR), unsafe_allow_html=True)
            with ct:
                st.write("**Secuencia táctica ganadora:**")
                st.code(c["line"])
            st.markdown('</div>', unsafe_allow_html=True)
