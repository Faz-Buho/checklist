"""
Página de captura, con dos flujos según el rol del usuario (ver auth.py):

- Diseñador (1er check): pasa los mismos 18 puntos sobre su propio
  layout. Solo puede guardarlo si TODO está en Cumple/N/A — guardarlo es
  lo que somete el folio a 2do check (aparece en la cola de pendientes).
- Evaluador (2do check): la revisión independiente de calidad, con cola
  de pendientes, resultado, PDF para el diseñador y ciclo de correcciones.

Se ejecuta vía st.navigation desde app.py.
"""

from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF
from fpdf.fonts import FontFace

import db
from auth import ROL_DISENADOR, ROL_EVALUADOR
from catalogo import (
    BLOQUES,
    CHECKLIST_ITEMS,
    ESTADO_CORRECCION,
    ESTADO_LISTO,
    ESTADO_PENDIENTE,
    RESULTADO_CORRECCION,
    RESULTADO_ENVIADO,
    RESULTADO_LISTO,
    STATUS_OPTIONS,
    STATUS_REQUIRES_MOTIVO,
    STATUS_AJUSTE,
    STATUS_CUMPLE,
    STATUS_NA,
    STATUS_NO_CUMPLE,
    TIPO_PRIMER,
    TIPO_SEGUNDO,
    TZ_LOCAL,
    estado_badge,
    estado_folio,
    status_badge,
)

# ---------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------

SIN_CAMPANA = "(Sin campaña)"
NUEVA_CAMPANA = "+ Nueva campaña..."

# Colores (texto, fondo) por estatus para el reporte en PDF
STATUS_PDF_COLORS = {
    STATUS_CUMPLE: ((22, 101, 52), (220, 252, 231)),
    STATUS_AJUSTE: ((133, 77, 14), (254, 249, 195)),
    STATUS_NO_CUMPLE: ((153, 27, 27), (254, 226, 226)),
    STATUS_NA: ((71, 85, 105), (241, 245, 249)),
}


# ---------------------------------------------------------------------
# Lógica de negocio
# ---------------------------------------------------------------------

def compute_resultado(respuestas):
    """respuestas: dict item_id -> {"status":..., "motivo":...}"""
    bloqueante = any(
        r["status"] in STATUS_REQUIRES_MOTIVO for r in respuestas.values()
    )
    return RESULTADO_CORRECCION if bloqueante else RESULTADO_LISTO


# ---------------------------------------------------------------------
# Reporte en PDF (solo para el 2do check)
# ---------------------------------------------------------------------

def _pdf_text(s):
    """Las fuentes base del PDF solo cubren latin-1; los caracteres fuera
    de ese rango (emojis, comillas tipográficas pegadas de otros docs) se
    sustituyen por '?' en vez de romper la generación del reporte."""
    return str(s).encode("latin-1", "replace").decode("latin-1")


class _ReportePDF(FPDF):
    def footer(self):
        self.set_y(-13)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 8, _pdf_text(f"Doble check de preproyectos - Página {self.page_no()}/{{nb}}"), align="C")


def generar_pdf(proyecto_info, respuestas, resultado, revision_num):
    pdf = _ReportePDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    ancho = pdf.w - pdf.l_margin - pdf.r_margin

    # --- Encabezado ---
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 8, "Doble check de preproyectos Layout", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, _pdf_text("Reporte de revisión de calidad para el diseñador"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(203, 213, 225)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    # --- Datos del proyecto ---
    label_style = FontFace(color=(100, 116, 139), emphasis="BOLD", size_pt=9)
    value_style = FontFace(color=(30, 41, 59), size_pt=10)
    datos = [
        ("Folio", proyecto_info["folio"]),
        ("Cliente", proyecto_info.get("cliente") or "-"),
        ("Revisión", f"{revision_num}"),
        ("Evaluador", proyecto_info.get("evaluador") or "-"),
        ("Fecha", proyecto_info["fecha"]),
        ("Campaña", proyecto_info.get("campana") or "-"),
    ]
    pdf.set_font("helvetica", "", 10)
    with pdf.table(col_widths=(25, 65, 25, 65), borders_layout="NONE",
                   line_height=6, num_heading_rows=0, first_row_as_headings=False,
                   text_align="LEFT", padding=(0.6, 0)) as table:
        for i in range(0, len(datos), 2):
            row = table.row()
            for label, valor in datos[i:i + 2]:
                row.cell(_pdf_text(label), style=label_style)
                row.cell(_pdf_text(valor), style=value_style)
    pdf.ln(3)

    # --- Resultado general ---
    if resultado == RESULTADO_LISTO:
        txt_color, fill_color = STATUS_PDF_COLORS[STATUS_CUMPLE]
    else:
        txt_color, fill_color = STATUS_PDF_COLORS[STATUS_NO_CUMPLE]
    pdf.set_font("helvetica", "B", 12)
    pdf.set_text_color(*txt_color)
    pdf.set_fill_color(*fill_color)
    pdf.cell(0, 11, _pdf_text(f"Resultado general: {resultado}"),
             fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    # --- Conteo por estatus ---
    conteos = {s: sum(1 for r in respuestas.values() if r["status"] == s) for s in STATUS_OPTIONS}
    chip_w = ancho / 4
    pdf.set_font("helvetica", "B", 9)
    for status in STATUS_OPTIONS:
        c_txt, c_fill = STATUS_PDF_COLORS[status]
        pdf.set_text_color(*c_txt)
        pdf.set_fill_color(*c_fill)
        pdf.cell(chip_w, 8, _pdf_text(f"{status}: {conteos[status]}"), fill=True, align="C")
    pdf.ln(12)

    # --- Detalle del checklist ---
    heading_style = FontFace(color=(255, 255, 255), fill_color=(51, 65, 85), emphasis="BOLD", size_pt=9)
    categoria_style = FontFace(color=(51, 65, 85), fill_color=(226, 232, 240), emphasis="BOLD", size_pt=9)
    item_style = FontFace(color=(30, 41, 59), size_pt=9)
    motivo_style = FontFace(color=(71, 85, 105), size_pt=9)

    for bloque_id, bloque_titulo in BLOQUES:
        items_bloque = [i for i in CHECKLIST_ITEMS if i["bloque"] == bloque_id]
        # Evitar que el título del bloque quede huérfano al final de la página
        if pdf.get_y() > pdf.h - 75:
            pdf.add_page()
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 8, _pdf_text(bloque_titulo), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

        pdf.set_font("helvetica", "", 9)
        with pdf.table(col_widths=(88, 24, 68), line_height=5,
                       text_align=("LEFT", "CENTER", "LEFT"),
                       borders_layout="HORIZONTAL_LINES", padding=1.6,
                       headings_style=heading_style) as table:
            head = table.row()
            head.cell(_pdf_text("Punto de revisión"))
            head.cell("Resultado")
            head.cell(_pdf_text("Motivo / ajuste requerido"))

            categorias = list(dict.fromkeys(i["categoria"] for i in items_bloque))
            for categoria in categorias:
                cat_row = table.row()
                cat_row.cell(_pdf_text(categoria), colspan=3, style=categoria_style)
                for item in [i for i in items_bloque if i["categoria"] == categoria]:
                    r = respuestas.get(item["id"], {"status": "", "motivo": ""})
                    s_txt, s_fill = STATUS_PDF_COLORS.get(r["status"], ((30, 41, 59), (255, 255, 255)))
                    row = table.row()
                    row.cell(_pdf_text(item["texto"]), style=item_style)
                    row.cell(_pdf_text(r["status"]),
                             style=FontFace(color=s_txt, fill_color=s_fill, emphasis="BOLD", size_pt=9))
                    row.cell(_pdf_text(r.get("motivo", "") or ""), style=motivo_style)
        pdf.ln(5)

    # --- Nota final para el diseñador ---
    if resultado == RESULTADO_CORRECCION:
        pdf.set_font("helvetica", "I", 9)
        pdf.set_text_color(153, 27, 27)
        pdf.multi_cell(0, 5, _pdf_text(
            "Los puntos marcados 'Con ajuste' o 'No cumple' requieren corrección. "
            "Después del ajuste, el diseñador debe pasar de nuevo su 1er check "
            "para someter el folio otra vez a 2do check."))

    return bytes(pdf.output())


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

usuario = st.session_state["usuario"]

# Estado diferido (se aplica ANTES de instanciar widgets, que es cuando
# Streamlit permite modificarlos):
# - limpiar_folio: tras guardar se vacía el campo de folio; con eso los
#   controles del folio dejan de renderizarse y Streamlit descarta su
#   estado solo (evita dobles guardados y deja lista la página).
# - folio_abrir: un clic en una tabla de la página Inicio precarga el folio.
if st.session_state.pop("limpiar_folio", None):
    st.session_state["folio"] = ""
if "folio_abrir" in st.session_state:
    st.session_state["folio"] = st.session_state.pop("folio_abrir")

# --- Sidebar: el folio primero (su ESTADO define el tipo de check) ---
with st.sidebar:
    st.header("Datos del proyecto")
    folio = st.text_input("Folio *", key="folio").strip()
    folio_info = db.get_folio(folio) if folio else None
    revisiones_folio = db.get_revisiones(folio) if folio else []
    estado = estado_folio(revisiones_folio)

# El TIPO de check lo define el ESTADO del folio, NO el rol de la persona
# (hay quien es diseñador y evaluador a la vez). Un folio nuevo o en
# corrección es un 1er check (autorevisión de quien lo somete); uno
# pendiente es un 2do check (revisión independiente). Así un folio nuevo
# nunca se certifica sin pasar antes por su 2do check.
es_evaluador = (estado == ESTADO_PENDIENTE)
tipo_check = TIPO_SEGUNDO if es_evaluador else TIPO_PRIMER

# Independencia: quien diseñó el folio (hizo su último 1er check) no puede
# hacer su propio 2do check; debe revisarlo otra persona.
_primeros = [r for r in revisiones_folio if r.get("tipo") == TIPO_PRIMER]
disenador_folio = _primeros[-1]["evaluador"] if _primeros else None
bloqueo_propio = es_evaluador and disenador_folio == usuario["nombre"]

if es_evaluador:
    st.title("2do check — Revisión de calidad")
else:
    st.title("1er check — Autorevisión del diseñador")
st.caption(f"Sesión de **{usuario['nombre']}**"
           + (f" ({usuario['email']})" if usuario["email"] else ""))

# --- Sidebar: resto de datos del proyecto ---
with st.sidebar:
    # Cliente y campaña son atributos del folio: si ya existe se
    # precargan, pero quedan editables para corregir asignaciones.
    cliente = st.text_input("Cliente",
                            value=folio_info["cliente"] if folio_info else "",
                            key=f"cliente_{folio}")

    campanas = db.get_campanas(solo_abiertas=True)
    nombre_a_id = {c["nombre"]: c["id"] for c in campanas}
    if folio_info and folio_info["campana"] and folio_info["campana"] not in nombre_a_id:
        # La campaña del folio está cerrada: se muestra igual para no
        # forzar una reasignación accidental.
        nombre_a_id[folio_info["campana"]] = folio_info["campana_id"]
    opciones_campana = [SIN_CAMPANA] + list(nombre_a_id) + [NUEVA_CAMPANA]
    campana_default = (folio_info["campana"]
                       if folio_info and folio_info["campana"] else SIN_CAMPANA)
    campana_sel = st.selectbox("Campaña", opciones_campana,
                               index=opciones_campana.index(campana_default),
                               key=f"campana_{folio}")
    nueva_campana = ""
    if campana_sel == NUEVA_CAMPANA:
        nueva_campana = st.text_input("Nombre de la nueva campaña *",
                                      key=f"nueva_campana_{folio}")

    prefill = None
    if revisiones_folio:
        st.markdown(f"Estado: {estado_badge(estado)} · "
                    f"{len(revisiones_folio)} revisión(es) en total.")

        # Prefill según el rol: cada quien retoma su propio último check,
        # dejando en blanco lo que falló en el último 2do check.
        propias = [r for r in revisiones_folio if r.get("tipo") == tipo_check]
        segundas = [r for r in revisiones_folio if r.get("tipo") == TIPO_SEGUNDO]
        ultima_segunda = segundas[-1] if segundas else None
        ofrecer_prefill = bool(propias) and (
            ultima_segunda is not None and ultima_segunda["resultado"] == RESULTADO_CORRECCION
        )
        if ofrecer_prefill:
            usar_prefill = st.checkbox(
                "Precargar respuestas de la revisión anterior "
                "(mantiene lo que ya cumplía, deja en blanco lo que falló)",
                value=True,
            )
            if usar_prefill:
                prefill = dict(propias[-1]["respuestas"])
                for item_id, r in ultima_segunda["respuestas"].items():
                    if r["status"] in STATUS_REQUIRES_MOTIVO:
                        prefill[item_id] = {"status": None, "motivo": r["motivo"]}
        st.divider()
        with st.expander("Ver historial de revisiones de este folio"):
            hist = pd.DataFrame([
                {
                    "Revisión": rev["revision"],
                    "Check": "1er" if rev.get("tipo") == TIPO_PRIMER else "2do",
                    "Fecha": rev["fecha"],
                    "Realizó": rev.get("evaluador", ""),
                    "Resultado": rev["resultado"],
                }
                for rev in revisiones_folio
            ])
            st.dataframe(hist, hide_index=True, width="stretch")

# --- Sin folio: mostrar la confirmación del último guardado o la guía ---
ultimo_guardado = st.session_state.get("ultimo_guardado")
if folio:
    st.session_state.pop("ultimo_guardado", None)
elif ultimo_guardado:
    ug = ultimo_guardado
    if ug["tipo"] == TIPO_PRIMER:
        st.success(f"Revisión {ug['revision']} (1er check) guardada — el folio "
                   f"**{ug['folio']}** quedó **pendiente de 2do check**.",
                   icon=":material/outgoing_mail:")
    elif ug["resultado"] == RESULTADO_LISTO:
        st.success(f"Revisión {ug['revision']} del folio **{ug['folio']}** — "
                   f"Listo para producción", icon=":material/check_circle:")
    else:
        st.warning(f"Revisión {ug['revision']} del folio **{ug['folio']}** — "
                   f"Requiere corrección. Cuando el diseñador corrija y pase su "
                   f"1er check, el folio volverá a la cola de pendientes.",
                   icon=":material/error:")
    if ug.get("conteos"):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Cumple", ug["conteos"][STATUS_CUMPLE])
        m2.metric("Con ajuste", ug["conteos"][STATUS_AJUSTE])
        m3.metric("No cumple", ug["conteos"][STATUS_NO_CUMPLE])
        m4.metric("N/A", ug["conteos"][STATUS_NA])
    if ug.get("pdf"):
        st.download_button(
            label="Descargar reporte en PDF (para el diseñador)",
            data=ug["pdf"],
            file_name=f"Reporte_{ug['folio']}_rev{ug['revision']}.pdf",
            mime="application/pdf",
            icon=":material/download:",
        )
    st.page_link("inicio.py", label="Volver al inicio", icon=":material/home:")
    st.stop()
else:
    st.info("Escribe el folio en la barra lateral, o ábrelo con un clic "
            "desde la página de inicio.", icon=":material/arrow_back:")
    st.page_link("inicio.py", label="Ir al inicio", icon=":material/home:")
    st.stop()

# --- Encabezado de contexto: qué se está evaluando ---
st.subheader(f":material/description: Folio {folio}")
partes = []
if cliente:
    partes.append(f"**Cliente:** {cliente}")
if campana_sel not in (SIN_CAMPANA, NUEVA_CAMPANA):
    partes.append(f"**Campaña:** {campana_sel}")
if estado:
    partes.append(f"Estado: {estado_badge(estado)}")
else:
    partes.append("**Folio nuevo**")
partes.append(f"**Esta revisión será la #{len(revisiones_folio) + 1}**")
st.markdown(" · ".join(partes))

if es_evaluador:
    st.caption(
        "Revisa primero toda la parte técnica con el arte abierto. "
        "Al final, valida los datos operativos contra la orden de trabajo."
    )
else:
    st.caption(
        "Autorevisión de tu layout con los mismos 18 puntos del 2do check. "
        "Solo puedes enviarlo cuando todo esté en Cumple o N/A — "
        "si algo falla, corrígelo en el arte antes de enviar."
    )

# Independencia: no puedes hacer el 2do check de un folio que tú enviaste.
if bloqueo_propio:
    st.warning(
        f"Este folio lo enviaste tú ({disenador_folio}). El 2do check debe "
        "hacerlo **otra persona** — es la revisión independiente. Pídele a "
        "otro evaluador que lo revise.",
        icon=":material/block:",
    )
    st.stop()

respuestas = {}
faltan_motivo = []
fallas_disenador = []

# Ambos bloques (técnica y operativa) en una sola pantalla, uno debajo
# del otro (antes eran pestañas).
BLOQUE_ICONO = {"tecnica": ":material/brush:", "operativa": ":material/fact_check:"}

for bloque_id, bloque_titulo in BLOQUES:
    st.header(f"{BLOQUE_ICONO.get(bloque_id, '')} {bloque_titulo}")
    items_bloque = [i for i in CHECKLIST_ITEMS if i["bloque"] == bloque_id]
    categorias = list(dict.fromkeys(i["categoria"] for i in items_bloque))

    for categoria in categorias:
        with st.container(border=True):
            st.subheader(categoria)
            for item in [i for i in items_bloque if i["categoria"] == categoria]:
                item_id = item["id"]
                # Sin selección por default: cada punto se evalúa a conciencia.
                prefill_item = prefill.get(item_id) if prefill else None
                default_status = prefill_item["status"] if prefill_item else None

                # El key incluye el folio: al cambiar de folio los
                # controles se crean de cero (aplica el prefill y no
                # se arrastran marcas de un folio a otro).
                status = st.segmented_control(
                    item["texto"],
                    STATUS_OPTIONS,
                    format_func=status_badge,
                    default=default_status if default_status in STATUS_OPTIONS else None,
                    key=f"status_{item_id}_{folio}",
                )

                motivo = ""
                if status in STATUS_REQUIRES_MOTIVO:
                    if es_evaluador:
                        motivo = st.text_area(
                            f"Motivo / ajuste requerido — {status_badge(status)}",
                            key=f"motivo_{item_id}_{folio}",
                            value=(prefill_item.get("motivo", "")
                                   if prefill_item and prefill_item["status"] == status else ""),
                            placeholder="Describe qué está mal y qué ajuste se necesita...",
                        )
                        if not motivo.strip():
                            faltan_motivo.append(item["texto"])
                    else:
                        st.warning("Corrige este punto en el arte: debe quedar en "
                                   "Cumple o N/A para poder enviar a 2do check.",
                                   icon=":material/build:")
                        fallas_disenador.append(item["texto"])

                respuestas[item_id] = {"status": status, "motivo": motivo}

# --- Guardar ---
st.divider()

n_total = len(respuestas)
n_evaluados = sum(1 for r in respuestas.values() if r["status"] is not None)
st.progress(n_evaluados / n_total if n_total else 0.0,
            text=f"**{n_evaluados} de {n_total}** puntos evaluados")

boton_label = "Guardar y generar reporte" if es_evaluador else "Enviar a 2do check"
col_a, col_b = st.columns([1, 3])
with col_a:
    guardar = st.button(boton_label, type="primary", width="stretch")

if guardar:
    errores = []
    if not folio:
        errores.append("Falta el folio.")
    if campana_sel == NUEVA_CAMPANA and not nueva_campana.strip():
        errores.append("Falta el nombre de la nueva campaña.")
    if any(r["status"] is None for r in respuestas.values()):
        errores.append("Hay puntos del checklist sin evaluar.")
    if es_evaluador and faltan_motivo:
        errores.append("Falta el motivo en: " + "; ".join(faltan_motivo))
    if not es_evaluador and fallas_disenador:
        errores.append(
            "No puedes enviar a 2do check con puntos en 'Con ajuste' o 'No cumple'. "
            "Corrige en el arte: " + "; ".join(fallas_disenador)
        )

    if errores:
        for e in errores:
            st.error(e)
    else:
        if campana_sel == NUEVA_CAMPANA:
            campana_id = db.crear_campana(nueva_campana)
            campana_nombre = nueva_campana.strip()
            db.registrar_evento("Crear campaña", usuario, detalle=campana_nombre)
        elif campana_sel == SIN_CAMPANA:
            campana_id = None
            campana_nombre = ""
        else:
            campana_id = nombre_a_id[campana_sel]
            campana_nombre = campana_sel

        fecha = datetime.now(TZ_LOCAL).strftime("%Y-%m-%d %H:%M")
        resultado = compute_resultado(respuestas) if es_evaluador else RESULTADO_ENVIADO

        revision_num = db.save_revision(
            folio, cliente, campana_id, usuario["nombre"], respuestas,
            resultado, fecha, tipo=tipo_check,
        )

        db.registrar_evento("2do check" if es_evaluador else "1er check",
                            usuario, folio=folio, detalle=resultado)

        conteos = None
        pdf_bytes = None
        if es_evaluador:
            conteos = {s: sum(1 for r in respuestas.values() if r["status"] == s)
                       for s in STATUS_OPTIONS}
            proyecto_info = {
                "folio": folio,
                "cliente": cliente,
                "evaluador": usuario["nombre"],
                "fecha": fecha,
                "campana": campana_nombre,
            }
            pdf_bytes = generar_pdf(proyecto_info, respuestas, resultado, revision_num)

        # La confirmación (y el PDF) se muestran en el siguiente rerun con
        # el folio ya limpio: así el botón de descarga no se esfuma al
        # interactuar y no se puede guardar dos veces por accidente.
        st.session_state["ultimo_guardado"] = {
            "folio": folio,
            "tipo": tipo_check,
            "resultado": resultado,
            "revision": revision_num,
            "conteos": conteos,
            "pdf": pdf_bytes,
        }
        st.session_state["limpiar_folio"] = folio
        st.rerun()
