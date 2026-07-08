"""
Gestor del formulario (checklist): crear, editar, reordenar y activar/
desactivar puntos y bloques. Solo para quien puede_editar_formulario
(pfaz@buhoms.com). Se ejecuta vía st.navigation desde app.py.

El checklist vive en la base (tablas checklist_bloques / checklist_items),
así que los cambios aquí se reflejan de inmediato para todo el equipo.
Regla de oro: los puntos no se borran (para no perder el historial de
respuestas), se DESACTIVAN; y su 'clave' interna nunca cambia.
"""

import pandas as pd
import streamlit as st

import db
from auth import puede_editar_formulario

usuario = st.session_state["usuario"]
if not puede_editar_formulario(usuario):
    st.error("Solo el administrador del formulario puede entrar aquí.",
             icon=":material/lock:")
    st.stop()

st.title(":material/edit_note: Gestor del formulario")
st.caption("Edita el checklist que ve el equipo. Los cambios aplican al instante. "
           "Los puntos que quites se **desactivan** (no se borran) para conservar el "
           "historial.")

bloques = db.get_bloques()
bloque_claves = [b[0] for b in bloques]
bloque_nombre = dict(bloques)

# =====================================================================
# Puntos del checklist
# =====================================================================
st.subheader(":material/checklist: Puntos del checklist")

items = db.get_checklist(solo_activos=False)
if not items:
    st.info("No hay puntos todavía. Agrega el primero abajo.")
else:
    df = pd.DataFrame(items)[["orden", "bloque", "categoria", "texto", "activo", "id"]]
    df["activo"] = df["activo"].astype(bool)
    editado = st.data_editor(
        df,
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        column_config={
            "orden": st.column_config.NumberColumn("Orden", width="small", step=1),
            "bloque": st.column_config.SelectboxColumn("Bloque", options=bloque_claves,
                                                       width="small"),
            "categoria": st.column_config.TextColumn("Categoría", width="medium"),
            "texto": st.column_config.TextColumn("Texto del punto", width="large"),
            "activo": st.column_config.CheckboxColumn("Activo", width="small"),
            "id": st.column_config.TextColumn("Clave", disabled=True, width="small"),
        },
        key="editor_items",
    )
    if st.button("Guardar cambios de los puntos", type="primary", icon=":material/save:"):
        for _, r in editado.iterrows():
            db.guardar_item(r["id"], r["bloque"], (r["categoria"] or "").strip(),
                            (r["texto"] or "").strip(), int(r["orden"] or 0),
                            1 if r["activo"] else 0)
        db.registrar_evento("Editar formulario", usuario, detalle="puntos")
        st.success("Cambios guardados.", icon=":material/check_circle:")
        st.rerun()

# --- Agregar un punto nuevo ---
with st.expander("Agregar un punto nuevo", icon=":material/add:"):
    with st.form("nuevo_item", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n_bloque = c1.selectbox("Bloque", bloque_claves,
                                format_func=lambda k: bloque_nombre.get(k, k))
        n_categoria = c2.text_input("Categoría",
                                    placeholder="Ej. 1. Contenido y fidelidad al cliente")
        n_texto = st.text_area("Texto del punto",
                               placeholder="Enunciado que leerá el evaluador...")
        n_orden = st.number_input("Orden (posición en la lista)", value=len(items) + 1, step=1)
        if st.form_submit_button("Agregar punto", type="primary", icon=":material/add:"):
            if not n_texto.strip() or not n_categoria.strip():
                st.warning("Faltan la categoría o el texto del punto.")
            else:
                db.crear_item(n_bloque, n_categoria.strip(), n_texto.strip(), int(n_orden))
                db.registrar_evento("Editar formulario", usuario,
                                    detalle=f"nuevo punto: {n_texto.strip()[:40]}")
                st.success("Punto agregado.", icon=":material/check_circle:")
                st.rerun()

st.divider()

# =====================================================================
# Bloques
# =====================================================================
st.subheader(":material/view_agenda: Bloques")
st.caption("Los dos grandes apartados del checklist. Puedes renombrarlos y reordenarlos.")

df_b = pd.DataFrame([{"orden": i, "clave": b[0], "nombre": b[1]}
                     for i, b in enumerate(bloques)])
editado_b = st.data_editor(
    df_b,
    hide_index=True,
    width="stretch",
    num_rows="fixed",
    column_config={
        "orden": st.column_config.NumberColumn("Orden", width="small", step=1),
        "nombre": st.column_config.TextColumn("Nombre del bloque", width="large"),
        "clave": st.column_config.TextColumn("Clave", disabled=True, width="small"),
    },
    key="editor_bloques",
)
if st.button("Guardar cambios de los bloques", type="primary", icon=":material/save:",
             key="save_bloques"):
    for _, r in editado_b.iterrows():
        db.guardar_bloque(r["clave"], (r["nombre"] or "").strip(), int(r["orden"] or 0))
    db.registrar_evento("Editar formulario", usuario, detalle="bloques")
    st.success("Bloques guardados.", icon=":material/check_circle:")
    st.rerun()

with st.expander("Agregar un bloque nuevo", icon=":material/add:"):
    with st.form("nuevo_bloque", clear_on_submit=True):
        b_nombre = st.text_input("Nombre del bloque",
                                 placeholder="Ej. Parte técnica (con el arte abierto)")
        if st.form_submit_button("Agregar bloque", type="primary", icon=":material/add:"):
            if not b_nombre.strip():
                st.warning("Falta el nombre del bloque.")
            else:
                db.crear_bloque(b_nombre.strip(), len(bloques))
                db.registrar_evento("Editar formulario", usuario,
                                    detalle=f"nuevo bloque: {b_nombre.strip()}")
                st.success("Bloque agregado.", icon=":material/check_circle:")
                st.rerun()
