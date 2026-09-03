import os
import tempfile
import streamlit as st
import chess
import chess.pgn
import chess.engine

# =====================================================================
# CONFIGURACIÓN DE LA PÁGINA WEB
# =====================================================================
st.set_page_config(page_title="Coach de Ajedrez Élite", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1f77b4;'>COACH DE AJEDREZ ELITE - SISTEMA IMPLACABLE</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Desafiando tu visión mediata y tu precisión estratégica bajo los marcos de Grau, Dorfman y Siles.</p>", unsafe_allow_html=True)

# =====================================================================
# 1. MOTORES DE DIAGNÓSTICO POSICIONAL Y TÁCTICO
# =====================================================================

def evaluar_material(tablero, color):
    valores = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    return sum(len(tablero.pieces(p, color)) * v for p, v in valores.items())

def evaluar_balance_dorfman_nivel(tablero, color):
    seguridad_rey = 0
    king_sq = tablero.king(color)
    if king_sq is not None:
        defensores = len([sq for sq in tablero.attacks(king_sq) if tablero.piece_type_at(sq) == chess.PAWN and tablero.piece_at(sq).color == color])
        seguridad_rey = defensores
        if not tablero.has_castling_rights(color) and chess.square_rank(king_sq) in [0, 7]:
            seguridad_rey -= 2

    peones = tablero.pieces(chess.PAWN, color)
    malos_peones = 0
    for col in range(8):
        if bin(peones & chess.BB_FILES[col]).count('1') > 1:
            malos_peones += 1
    estructura_peones = 10 - (malos_peones * 3)

    tablero_temp = tablero.copy()
    tablero_temp.turn = color
    actividad = len(list(tablero_temp.legal_moves))
    material = evaluar_material(tablero, color)

    return (seguridad_rey, estructura_peones, actividad, material)

def caballo_en_el_borde(jugada, pieza_movida):
    if pieza_movida == chess.KNIGHT:
        columna = chess.square_file(jugada.to_square)
        return columna == 0 or columna == 7
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
        logros.append(f"Torre en columna abierta ({col_name}): Dominio absoluto (Fernández Siles).")
    elif not hay_propio and hay_rival:
        logros.append(f"Torre en columna semiabierta ({col_name}): Presión activa sobre peones retrasados.")
    return logros

def comprobar_orden_desarrollo(tablero, color, pieza_movida, turno_real):
    advertencias = []
    if turno_real <= 6 and pieza_movida == chess.BISHOP:
        casillas_caballos = [chess.B1, chess.G1] if color == chess.WHITE else [chess.B8, chess.G8]
        caballos_en_origen = sum(1 for sq in casillas_caballos if tablero.piece_at(sq) and tablero.piece_at(sq).piece_type == chess.KNIGHT)
        if caballos_en_origen == 2:
            advertencias.append(("Orden de Desarrollo Defectuoso", "Desarrollaste alfil antes de caballo (Grau Tomo I)."))
    return advertencias

def comprobar_perdida_tiempo_apertura(jugada, san_jugada, pieza_movida, turno_real, casillas_visitadas):
    advertencias = []
    if turno_real <= 10 and pieza_movida not in [chess.PAWN, chess.KING]:
        if jugada.from_square in casillas_visitadas:
            advertencias.append(("Pérdida de Tiempos ('Tempos')", f"Mover dos veces la misma pieza en apertura con {san_jugada} cede la iniciativa."))
    return advertencias

def explicar_motivo_tricky(t_copia, color):
    motivos = []
    if t_copia.is_check():
        motivos.append("Genera un jaque sorpresivo bajo fuerte tensión.")
    oponente = not color
    rey_rival_sq = t_copia.king(oponente)
    if rey_rival_sq and t_copia.is_attacked_by(color, rey_rival_sq):
        motivos.append("Presión directa sobre el monarca enemigo.")
    f7_f2 = chess.F7 if oponente == chess.BLACK else chess.F2
    if t_copia.is_attacked_by(color, f7_f2):
        motivos.append("Amenaza letal sobre el talón de Aquiles (f7/f2).")
    if not motivos:
        motivos.append("Mina terrestre psicológica que desestabiliza la defensa.")
    return " ".join(motivos)

def detectar_celada_tricky(tablero, color, engine, limite_analisis):
    celadas_encontradas = []
    try:
        multipv_analisis = engine.analyse(tablero, limite_analisis, multipv=3)
    except Exception:
        return celadas_encontradas

    for pv_info in multipv_analisis:
        if "pv" not in pv_info or not pv_info["pv"]:
            continue
        variante_movimientos = pv_info["pv"]
        jugada_alt = variante_movimientos[0]
        score_alt = pv_info["score"].pov(color).score(mate_score=10000)
        
        t_temp = tablero.copy()
        linea_san = []
        for m in variante_movimientos[:6]:
            try:
                linea_san.append(t_temp.san(m))
                t_temp.push(m)
            except Exception:
                break
        secuencia_str = " -> ".join(linea_san)
        
        t_copia = tablero.copy()
        san_alt = t_copia.san(jugada_alt)
        t_copia.push(jugada_alt)
        
        es_jaque = t_copia.is_check()
        presion_f7_f2 = (color == chess.WHITE and t_copia.is_attacked_by(chess.WHITE, chess.F7)) or \
                        (color == chess.BLACK and t_copia.is_attacked_by(chess.BLACK, chess.F2))
        
        if score_alt > -100 and (es_jaque or presion_f7_f2):
            explicacion_profunda = explicar_motivo_tricky(t_copia, color)
            celadas_encontradas.append({
                "jugada": san_alt,
                "linea_completa": secuencia_str,
                "score": score_alt,
                "motivo": explicacion_profunda
            })
    return celadas_encontradas

def evaluar_conformacion_peones_grau(tablero, color):
    advertencias = []
    peones = tablero.pieces(chess.PAWN, color)
    peones_f = [p for p in peones if chess.square_file(p) == 5]
    if len(peones_f) >= 2:
        advertencias.append(("Estructura de Peones Defectuosa", "Peones doblados en la columna F, rompiendo el enroque."))
    return advertencias

def detectar_peon_en_germen(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if pieza_movida == chess.PAWN and turno_real <= 15:
        from_file = chess.square_file(jugada.from_square)
        to_rank = chess.square_rank(jugada.to_square)
        es_avance = (color == chess.WHITE and from_file in [5, 6, 7] and to_rank > 2) or \
                    (color == chess.BLACK and from_file in [5, 6, 7] and to_rank < 5)
        if es_avance:
            advertencias.append(("Debilidad en Germen", f"Avanzar prematuramente el peón lateral con {san_jugada} crea agujeros permanentes."))
    return advertencias

def detectar_dama_prematura_peon_b(tablero, color, jugada, san_jugada, pieza_movida, turno_real):
    advertencias = []
    if pieza_movida == chess.QUEEN and turno_real <= 10:
        to_square = jugada.to_square
        if (color == chess.WHITE and to_square == chess.B7) or (color == chess.BLACK and to_square == chess.B2):
            advertencias.append(("Tentación de Dama Temprana", f"Desviar la Dama por el peón b con {san_jugada} arriesga el encierro."))
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
                v_min_at = min(valores[tablero.piece_at(atk).piece_type] for atk in atacantes)
                v_min_df = min(valores[tablero.piece_at(df).piece_type] for df in defensores)
                if v_min_df > v_min_at and valores[piece.piece_type] > v_min_at:
                    advertencias.append(("Sostén Insuficiente", f"Pieza agredida por menor valor y defendida por mayor en {chess.square_name(square).upper()}."))
    return advertencias

def evaluar_lpdo(tablero, color):
    contador = 0
    for square in chess.SQUARES:
        piece = tablero.piece_at(square)
        if piece and piece.color == color and piece.piece_type not in [chess.KING, chess.PAWN]:
            if not tablero.is_attacked_by(color, square):
                contador += 1
    return contador >= 2

def evaluar_profilaxis_descuidada(cpl):
    return cpl > 150

def evaluar_centralizacion_dama(tablero, color, jugada, pieza_movida, fase, turno_real):
    logros = []
    if pieza_movida == chess.QUEEN and fase in ["Medio Juego", "Final"]:
        if jugada.to_square in [chess.D4, chess.E4, chess.D5, chess.E5]:
            logros.append(f"Centralización de Dama en T{turno_real} (Grau Tomo IV).")
    return logros

def fase_del_juego(tablero, turno):
    if turno <= 10: return "Apertura"
    hay_damas = len(tablero.pieces(chess.QUEEN, chess.WHITE)) > 0 or len(tablero.pieces(chess.QUEEN, chess.BLACK)) > 0
    mat_total = evaluar_material(tablero, chess.WHITE) + evaluar_material(tablero, chess.BLACK)
    if not hay_damas or mat_total < 28: return "Final"
    return "Medio Juego"

def calcular_elo_precision(lista_cpl):
    if not lista_cpl: 
        return 100, 100.0
    acpl = sum(lista_cpl) / len(lista_cpl)
    return max(100, int(3000 - (acpl * 14.5))), round(max(0.0, min(100.0, 100 - (acpl / 2.3))), 1)

# =====================================================================
# 2. INTERFAZ DE USUARIO (STREAMLIT)
# =====================================================================

with st.expander("--- CUESTIONARIO PREVIO DE AUTO-REFLEXIÓN (PEDAGOGÍA DE GRAU) ---", expanded=False):
    st.write("Como tu mentor, exijo tu honestidad intelectual antes de auditar la partida:")
    fase_colapso = st.text_input("1. ¿En qué fase del juego sientes que colapsó la armonía de tus piezas?")
    tipo_error = st.selectbox("2. چه Fue tu mayor error de juicio un fallo táctico o de planificación?", 
                              ["Selecciona...", "Fallo táctico (Visión Inmediata)", "Fallo de planificación (Visión Mediata)"])
    plan_peones = st.text_input("3. ¿Crees que colocaste tus peones de acuerdo con la base de planes estáticos de Grau?")

col1, col2 = st.columns(2)
with col1:
    color_input = st.selectbox("¿Con qué piezas jugaste?", ("Blancas", "Negras"))
    MI_COLOR = chess.WHITE if color_input == "Blancas" else chess.BLACK
    mi_color_str = "Blancas" if MI_COLOR == chess.WHITE else "Negras"

with col2:
    uploaded_file = st.file_uploader("Sube tu archivo PGN de la partida", type=["pgn"])

if st.button("Iniciar Análisis Táctico e Implacable", type="primary"):
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pgn") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        with st.spinner("Desmantelando decisiones y cruzando marcos teóricos... Por favor, espera."):
            RUTA_STOCKFISH = "stockfish-windows-x86-64-avx2.exe"
            if not os.path.exists(RUTA_STOCKFISH):
                RUTA_STOCKFISH = "stockfish"

            try:
                engine = chess.engine.SimpleEngine.popen_uci(RUTA_STOCKFISH)
                engine.configure({"Skill Level": 20})
            except Exception as e:
                st.error(f"Error al iniciar Stockfish: {e}")
                st.stop()

            with open(tmp_path, "r", encoding="utf-8") as archivo_pgn:
                partida = chess.pgn.read_game(archivo_pgn)

            if partida is None:
                st.error("El archivo PGN está vacío o no es válido.")
                engine.quit()
                st.stop()

            nombre_usuario = partida.headers.get("White" if MI_COLOR == chess.WHITE else "Black", "Tú")
            tablero = partida.board()
            limite = chess.engine.Limit(time=0.15)

            mi_cpl, rival_cpl = [], []
            resumen_errores = {}
            archivo_celadas_tricky = []
            mis_logros = []
            estadisticas = {"jugadas_attack": 0, "jugadas_defense": 0, "jugadas_neutral": 0, "jugadas_errores": 0}

            jugada_numero = 1
            rey_atascado_advertido = False
            casillas_visitadas_propias = set()

            for nodo_jugada in partida.mainline():
                jugada = nodo_jugada.move
                color_turno = tablero.turn
                es_mi_turno = (color_turno == MI_COLOR)
                turno_real = (jugada_numero + 1) // 2
                fase = fase_del_juego(tablero, turno_real)
                
                piece = tablero.piece_at(jugada.from_square)
                if not piece:
                    continue
                pieza_movida = piece.piece_type
                san_jugada = tablero.san(jugada)
                
                niveles_antes = evaluar_balance_dorfman_nivel(tablero, color_turno)
                
                if es_mi_turno and turno_real <= 18:
                    celadas = detectar_celada_tricky(tablero, MI_COLOR, engine, limite)
                    for c in celadas:
                        if c["jugada"] != san_jugada:
                            archivo_celadas_tricky.append({
                                "turno": turno_real,
                                "jugada_real": san_jugada,
                                "jugada_trampa": c["jugada"],
                                "linea": c["linea_completa"],
                                "score": c["score"],
                                "detalle": c["motivo"]
                            })

                info_antes = engine.analyse(tablero, limite)
                eval_antes = info_antes["score"].pov(color_turno).score(mate_score=10000)
                
                es_captura = tablero.is_capture(jugada)
                da_jaque = tablero.gives_check(jugada)
                if es_mi_turno:
                    es_de_defensa = tablero.is_attacked_by(not color_turno, jugada.from_square) or tablero.is_check()
                    
                tablero.push(jugada)
                
                niveles_despues = evaluar_balance_dorfman_nivel(tablero, color_turno)
                info_despues = engine.analyse(tablero, limite)
                eval_despues = info_despues["score"].pov(color_turno).score(mate_score=10000)
                cpl = max(0, eval_antes - eval_despues)
                
                if es_mi_turno:
                    mi_cpl.append(cpl)
                    if pieza_movida == chess.PAWN:
                        pass
                        
                    def registrar_error(tipo, desc):
                        if tipo not in resumen_errores:
                            resumen_errores[tipo] = {"desc": desc, "turnos": []}
                        if turno_real not in resumen_errores[tipo]["turnos"]:
                            resumen_errores[tipo]["turnos"].append(turno_real)

                    if niveles_despues[0] < niveles_antes[0] and (niveles_despues[1] > niveles_antes[1] or niveles_despues[3] > niveles_antes[3]):
                        registrar_error("Inversión Estática Ruinosa (Dorfman)", "Sacrificaste la seguridad del rey a cambio de una ventaja menor.")

                    if cpl > 150:
                        estadisticas["jugadas_errores"] += 1
                    elif da_jaque or es_captura:
                        estadisticas["jugadas_attack"] += 1
                    elif es_de_defensa:
                        estadisticas["jugadas_defense"] += 1
                    else:
                        estadisticas["jugadas_neutral"] += 1
                        
                    if caballo_en_el_borde(jugada, pieza_movida) and cpl > 30:
                        registrar_error("Caballos Marginados en la Banda", "Exiliaste caballos a las columnas a/h perdiendo opciones de salto.")
                        
                    rey_casilla_inicial = chess.E1 if MI_COLOR == chess.WHITE else chess.E8
                    if turno_real == 12 and tablero.king(MI_COLOR) == rey_casilla_inicial and not rey_atascado_advertido:
                        registrar_error("Negligencia de Enroque", "Llegaste al medio juego con el rey expuesto en el centro.")
                        rey_atascado_advertido = True
                        
                    if detectar_alfil_malo(tablero, MI_COLOR) and cpl > 40 and fase == "Medio Juego":
                        registrar_error("Alfil Aprisionado ('Alfil Malo')", "Encerraste tus alfiles detrás de tus propias cadenas de peones.")
                        
                    for tipo_err, desc_err in comprobar_orden_desarrollo(tablero, MI_COLOR, pieza_movida, turno_real):
                        registrar_error(tipo_err, desc_err)
                        
                    for tipo_err, desc_err in comprobar_perdida_tiempo_apertura(jugada, san_jugada, pieza_movida, turno_real, casillas_visitadas_propias):
                        registrar_error(tipo_err, desc_err)
                        
                    for tipo_err, desc_err in evaluar_conformacion_peones_grau(tablero, MI_COLOR):
                        registrar_error(tipo_err, desc_err)
                        
                    for tipo_err, desc_err in detectar_sosten_insuficiente(tablero, MI_COLOR):
                        registrar_error(tipo_err, desc_err)
                        
                    for w in detectar_peon_en_germen(tablero, MI_COLOR, jugada, san_jugada, pieza_movida, turno_real):
                        registrar_error(w[0], w[1])
                        
                    for w in detectar_dama_prematura_peon_b(tablero, MI_COLOR, jugada, san_jugada, pieza_movida, turno_real):
                        registrar_error(w[0], w[1])
                        
                    if evaluar_lpdo(tablero, MI_COLOR):
                        registrar_error("Peligro LPDO (Piezas Desprotegidas - John Nunn)", "Acumulaste múltiples piezas sin defensa directa.")
                        
                    if evaluar_profilaxis_descuidada(cpl):
                        registrar_error("Negligencia Profiláctica (Nimzowitsch)", "Ignoraste las amenazas inminentes del rival.")
                        
                    casillas_visitadas_propias.add(jugada.to_square)
                    
                    if torre_en_septima(jugada, pieza_movida, MI_COLOR):
                        mis_logros.append(f"Torre en séptima fila (T{turno_real}).")
                        
                    for l in evaluar_estrategia_torres(tablero, MI_COLOR, jugada, pieza_movida):
                        mis_logros.append(l)
                        
                    for l in evaluar_centralizacion_dama(tablero, MI_COLOR, jugada, pieza_movida, fase, turno_real):
                        mis_logros.append(l)
                else:
                    rival_cpl.append(cpl)

                jugada_numero += 1

            engine.quit()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            mi_elo, mi_prec = calcular_elo_precision(mi_cpl)
            rival_elo, rival_prec = calcular_elo_precision(rival_cpl)

            # =====================================================================
            # 3. MOSTRAR RESULTADOS EN LA INTERFAZ WEB
            # =====================================================================
            st.success("¡Análisis completado con éxito!")
            
            st.markdown("---")
            st.subheader("📊 Diagnóstico General")
            m1, m2, m3 = st.columns(3)
            m1.metric("Jugador", nombre_usuario)
            m2.metric("Precisión Analítica", f"{mi_prec}%")
            m3.metric("Elo Estimado", mi_elo)

            st.markdown("---")
            st.subheader("🛑 Patrones Crónicos de Error")
            if not resumen_errores:
                st.info("¡Excepcional! No se detectaron patrones recurrentes de errores estructurales.")
            else:
                for tipo, datos in resumen_errores.items():
                    turnos_str = ", ".join(map(str, datos["turnos"]))
                    with st.expander(f"{tipo} (Turnos: {turnos_str})"):
                        st.write(f"**Concepto:** {datos['desc']}")

            st.markdown("---")
            st.subheader("⚡ Triquiñuelas 'Very Tricky' Omitidas")
            if not archivo_celadas_tricky:
                st.info("La partida discurrió por cauces estrictamente sólidos; no hubo opciones de celadas complejas.")
            else:
                archivo_celadas_tricky.sort(key=lambda x: x["score"], reverse=True)
                celadas_seleccionadas = []
                vistos_turnos = set()
                
                for item in archivo_celadas_tricky:
                    if item["turno"] not in vistos_turnos and len(celadas_seleccionadas) < 4:
                        vistos_turnos.add(item["turno"])
                        celadas_seleccionadas.append(item)
                        
                for idx, item in enumerate(celadas_seleccionadas, 1):
                    with st.container():
                        st.markdown(f"**Oportunidad Clave #{idx} (Turno {item['turno']})**")
                        st.write(f"- *Jugaste en la partida:* `{item['jugada_real']}`")
                        st.write(f"- *La triquiñuela oculta:* `{item['jugada_trampa']}`")
                        st.code(f"Línea (6M): {item['linea']}")
                        st.write(f"- *Explicación táctica:* {item['detalle']}")
                        st.markdown("---")

            st.subheader("🎖 Logros Posicionales Destacados")
            if not mis_logros:
                st.write("Ninguno reseñable. Juego plano sin chispa estratégica.")
            else:
                for logro in set(mis_logros):
                    st.success(logro)
    else:
        st.error("Por favor, sube un archivo PGN válido antes de iniciar el análisis.")