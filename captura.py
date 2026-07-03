"""
Página de captura: el checklist de revisión por folio (= número de OT),
con cliente y campaña como atributos del folio, y reporte en PDF para
entregar al diseñador. Se ejecuta vía st.navigation desde app.py.
"""

from datetime import datetime

import pandas as pd
import streamlit as st
from fpdf import FPDF
from fpdf.fonts import FontFace

import db
from catalogo import (
    BLOQUES,
    CHECKLIST_ITEMS,
    RESULTADO_CORRECCION,
    RESULTADO_LISTO,
    STATUS_ICONS,
    STATUS_OPTIONS,
    STATUS_REQUIRES_MOTIVO,
    STATUS_AJUSTE,
    STATUS_CUMPLE,
    STATUS_NA,
    STATUS_NO_CUMPLE,
)

# ---------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------

# Lista de evaluadores para uso local (sin login). En Streamlit Cloud,
# con viewers restringidos por email, el evaluador se toma solo del
# usuario logueado y este selector no aparece.
EVALUADORES = [
    "Nombre Apellido 1",
    "Nombre Apellido 2",
    "Nombre Apellido 3",
]
OTRO_EVALUADOR = "Otro (especificar)"

SIN_CAMPANA = "(Sin campaña)"
NUEVA_CAMPANA = "➕ Nueva campaña..."

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
# Reporte en PDF
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
            "Después del ajuste se abrirá una nueva revisión de este folio."))

    return bytes(pdf.output())


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

def _email_usuario():
    """Email del usuario logueado (Streamlit Cloud con viewers por email).
    En local, sin login configurado, regresa None y se usa el selector."""
    try:
        if st.user.is_logged_in:
            return st.user.email or None
    except Exception:
        pass
    return None


st.title("Doble check de preproyectos Layout")

# --- Sidebar: datos del proyecto ---
with st.sidebar:
    st.header("Datos del proyecto")
    folio = st.text_input("Folio *").strip()

    folio_info = db.get_folio(folio) if folio else None
    revisiones_folio = db.get_revisiones(folio) if folio else []

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

    email = _email_usuario()
    if email:
        evaluador = email
        st.markdown(f"**Evaluador:** {email}")
    else:
        evaluador_sel = st.selectbox("Evaluador *", EVALUADORES + [OTRO_EVALUADOR],
                                     index=None, placeholder="Selecciona tu nombre")
        if evaluador_sel == OTRO_EVALUADOR:
            evaluador = st.text_input("Nombre del evaluador")
        else:
            evaluador = evaluador_sel or ""

    prefill = None
    if revisiones_folio:
        last = revisiones_folio[-1]
        st.info(f"Este folio ya tiene {len(revisiones_folio)} revisión(es). "
                f"La última fue: **{last['resultado']}** (Revisión {last['revision']}).")
        if last["resultado"] == RESULTADO_CORRECCION:
            usar_prefill = st.checkbox(
                "Precargar respuestas de la última revisión "
                "(mantiene lo que ya cumplía, deja en blanco lo que falló)",
                value=True,
            )
            if usar_prefill:
                prefill = last["respuestas"]
        st.divider()
        with st.expander("Ver historial de revisiones de este folio"):
            hist = pd.DataFrame([
                {
                    "Revisión": rev["revision"],
                    "Fecha": rev["fecha"],
                    "Evaluador": rev.get("evaluador", ""),
                    "Resultado": rev["resultado"],
                }
                for rev in revisiones_folio
            ])
            st.dataframe(hist, hide_index=True, width="stretch")

st.caption(
    "Revisa primero toda la parte técnica con el arte abierto. "
    "Al final, valida los datos operativos contra la orden de trabajo."
)

respuestas = {}
faltan_motivo = []

tab_tecnica, tab_operativa = st.tabs([
    "🎨 Parte técnica (con el arte abierto)",
    "📋 Parte operativa (contra la orden de trabajo)",
])
tab_por_bloque = {"tecnica": tab_tecnica, "operativa": tab_operativa}

for bloque_id, bloque_titulo in BLOQUES:
    with tab_por_bloque[bloque_id]:
        items_bloque = [i for i in CHECKLIST_ITEMS if i["bloque"] == bloque_id]
        categorias = list(dict.fromkeys(i["categoria"] for i in items_bloque))

        for categoria in categorias:
            with st.container(border=True):
                st.subheader(categoria)
                for item in [i for i in items_bloque if i["categoria"] == categoria]:
                    item_id = item["id"]
                    # Sin selección por default: cada punto se evalúa a conciencia.
                    # Solo se precarga si viene del prefill de la revisión anterior,
                    # y aun así lo que venía fallando se deja en blanco.
                    prefill_item = prefill.get(item_id) if prefill else None
                    default_status = prefill_item["status"] if prefill_item else None
                    if prefill_item and prefill_item["status"] in STATUS_REQUIRES_MOTIVO:
                        default_status = None

                    status = st.segmented_control(
                        item["texto"],
                        STATUS_OPTIONS,
                        format_func=lambda s: f"{STATUS_ICONS[s]} {s}",
                        default=default_status if default_status in STATUS_OPTIONS else None,
                        key=f"status_{item_id}",
                    )

                    motivo = ""
                    if status in STATUS_REQUIRES_MOTIVO:
                        motivo = st.text_area(
                            f"Motivo / ajuste requerido — {STATUS_ICONS[status]} {status}",
                            key=f"motivo_{item_id}",
                            value=prefill_item.get("motivo", "") if prefill_item and prefill_item["status"] == status else "",
                            placeholder="Describe qué está mal y qué ajuste se necesita...",
                        )
                        if not motivo.strip():
                            faltan_motivo.append(item["texto"])

                    respuestas[item_id] = {"status": status, "motivo": motivo}

# --- Guardar y generar reporte ---
st.divider()

n_total = len(respuestas)
n_evaluados = sum(1 for r in respuestas.values() if r["status"] is not None)
st.progress(n_evaluados / n_total if n_total else 0.0,
            text=f"**{n_evaluados} de {n_total}** puntos evaluados")

col_a, col_b = st.columns([1, 3])
with col_a:
    guardar = st.button("Guardar y generar reporte", type="primary", width="stretch")

if guardar:
    errores = []
    if not folio:
        errores.append("Falta el folio.")
    if campana_sel == NUEVA_CAMPANA and not nueva_campana.strip():
        errores.append("Falta el nombre de la nueva campaña.")
    if not evaluador.strip():
        errores.append("Falta especificar el evaluador.")
    if any(r["status"] is None for r in respuestas.values()):
        errores.append("Hay puntos del checklist sin evaluar.")
    if faltan_motivo:
        errores.append(
            "Falta el motivo en: " + "; ".join(faltan_motivo)
        )

    if errores:
        for e in errores:
            st.error(e)
    else:
        if campana_sel == NUEVA_CAMPANA:
            campana_id = db.crear_campana(nueva_campana)
            campana_nombre = nueva_campana.strip()
        elif campana_sel == SIN_CAMPANA:
            campana_id = None
            campana_nombre = ""
        else:
            campana_id = nombre_a_id[campana_sel]
            campana_nombre = campana_sel

        resultado = compute_resultado(respuestas)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

        revision_num = db.save_revision(
            folio, cliente, campana_id, evaluador, respuestas, resultado, fecha
        )

        if resultado == RESULTADO_LISTO:
            st.success(f"✅ Revisión {revision_num} — Listo para producción")
        else:
            st.warning(f"🔴 Revisión {revision_num} — Requiere corrección. "
                       f"Al corregir, vuelve a abrir este folio para crear la Revisión {revision_num + 1}.")

        n_cumple = sum(1 for r in respuestas.values() if r["status"] == STATUS_CUMPLE)
        n_ajuste = sum(1 for r in respuestas.values() if r["status"] == STATUS_AJUSTE)
        n_no_cumple = sum(1 for r in respuestas.values() if r["status"] == STATUS_NO_CUMPLE)
        n_na = sum(1 for r in respuestas.values() if r["status"] == STATUS_NA)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("✅ Cumple", n_cumple)
        m2.metric("⚠️ Con ajuste", n_ajuste)
        m3.metric("🛑 No cumple", n_no_cumple)
        m4.metric("➖ N/A", n_na)

        proyecto_info = {
            "folio": folio,
            "cliente": cliente,
            "evaluador": evaluador,
            "fecha": fecha,
            "campana": campana_nombre,
        }
        pdf_bytes = generar_pdf(proyecto_info, respuestas, resultado, revision_num)

        st.download_button(
            label="Descargar reporte en PDF (para el diseñador)",
            data=pdf_bytes,
            file_name=f"Reporte_{folio}_rev{revision_num}.pdf",
            mime="application/pdf",
        )
