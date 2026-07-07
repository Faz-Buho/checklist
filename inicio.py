"""
Página de inicio: la bandeja de trabajo, distinta por rol.

- Evaluador: pendientes de 2do check (su cola de trabajo), folios en
  corrección (esperando a diseñadores) y liberados recientes.
- Diseñador: SUS folios en corrección (lo que le toca corregir),
  esperando 2do check y liberados.

Clic en una fila abre el folio en la página de captura. Se ejecuta vía
st.navigation desde app.py.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import db
from auth import ROL_EVALUADOR
from catalogo import (
    ESTADO_CORRECCION,
    ESTADO_LISTO,
    ESTADO_PENDIENTE,
    RESULTADO_LISTO,
    TIPO_PRIMER,
    TZ_LOCAL,
)

usuario = st.session_state["usuario"]
es_evaluador = usuario["rol"] == ROL_EVALUADOR

st.title(":material/home: Inicio")
st.caption(f"Sesión de **{usuario['nombre']}**"
           + (f" ({usuario['email']})" if usuario["email"] else ""))
st.page_link("captura.py", label="Capturar un folio nuevo", icon=":material/checklist:")

rev_rows = db.get_revisiones_dashboard("todas")

if not rev_rows:
    st.info("Aún no hay folios capturados. Empieza con el botón de arriba.",
            icon=":material/arrow_upward:")
    st.stop()

df = pd.DataFrame(rev_rows)

# Estado por folio (lo define su última revisión) y quién es su diseñador
# (quien hizo su último 1er check).
ultimas = df.loc[df.groupby("folio")["revision"].idxmax()].copy()
ultimas["estado"] = [
    ESTADO_PENDIENTE if t == TIPO_PRIMER
    else (ESTADO_LISTO if r == RESULTADO_LISTO else ESTADO_CORRECCION)
    for t, r in zip(ultimas["tipo"], ultimas["resultado"])
]
primeros = df[df["tipo"] == TIPO_PRIMER]
disenador_por_folio = (primeros.loc[primeros.groupby("folio")["revision"].idxmax()]
                       .set_index("folio")["evaluador"] if not primeros.empty else {})
ultimas["disenador"] = ultimas["folio"].map(disenador_por_folio)

CAPTION_ABRIR = "Haz clic en una fila para abrir ese folio."


# Semáforo de espera: verde hasta 1 día, ámbar hasta 3, rojo después.
UMBRAL_VERDE_DIAS = 1
UMBRAL_AMARILLO_DIAS = 3
_COLOR_VERDE = ("#166534", "#dcfce7")
_COLOR_AMBAR = ("#854d0e", "#fef9c3")
_COLOR_ROJO = ("#991b1b", "#fee2e2")


def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def _espera_texto(dias):
    return "hoy" if dias < 1 else f"{dias:.1f} d"


def _estilo_espera(col):
    """Colorea la celda de espera según el umbral (mismo lenguaje del
    resto de la app), leyendo el texto ya formateado."""
    estilos = []
    for v in col:
        dias = 0.0 if v == "hoy" else float(str(v).split()[0])
        if dias <= UMBRAL_VERDE_DIAS:
            txt, bg = _COLOR_VERDE
        elif dias <= UMBRAL_AMARILLO_DIAS:
            txt, bg = _COLOR_AMBAR
        else:
            txt, bg = _COLOR_ROJO
        estilos.append(f"background-color: {bg}; color: {txt}")
    return estilos


def tabla_folios(df_view, key):
    """Tabla consistente (grid): seleccionar una fila abre ese folio en
    Captura. Colorea la columna 'Espera' si existe. El guardia evita que,
    al volver a Inicio con la fila aún seleccionada, se reabra en bucle."""
    styler = df_view.style
    if "Espera" in df_view.columns:
        styler = styler.apply(_estilo_espera, subset=["Espera"])
    ev = st.dataframe(styler, hide_index=True, width="stretch",
                      on_select="rerun", selection_mode="single-row", key=key)
    if ev.selection.rows:
        idx = ev.selection.rows[0]
        folio = df_view.iloc[idx]["Folio"]
        if st.session_state.get(f"_sel_{key}") != (folio, idx):
            st.session_state[f"_sel_{key}"] = (folio, idx)
            st.session_state["folio_abrir"] = folio
            st.switch_page("captura.py")


if es_evaluador:
    # --- Pendientes de 2do check: la cola de trabajo del evaluador ---
    pend = ultimas[ultimas["estado"] == ESTADO_PENDIENTE]
    st.subheader(f":material/inbox: Pendientes de 2do check ({len(pend)})")
    if pend.empty:
        st.success("No hay folios esperando 2do check.", icon=":material/celebration:")
    else:
        view = pend[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_espera_texto)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Enviado el", "Espera"]
        st.caption(CAPTION_ABRIR)
        tabla_folios(view, "pend")

    # --- En corrección: esperando a los diseñadores ---
    corr = ultimas[ultimas["estado"] == ESTADO_CORRECCION]
    if not corr.empty:
        st.subheader(f":material/build: En corrección con el diseñador ({len(corr)})")
        view = corr[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_espera_texto)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Rechazado el", "Espera"]
        st.caption(CAPTION_ABRIR)
        tabla_folios(view, "corr")

    # --- Liberados recientes ---
    lib = ultimas[ultimas["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f":material/check_circle: Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Liberado el"]
        st.caption(CAPTION_ABRIR)
        tabla_folios(view.sort_values("Liberado el", ascending=False).head(15), "lib")

else:
    mios = ultimas[ultimas["disenador"] == usuario["nombre"]]
    if mios.empty:
        st.info("Aún no tienes folios. Captura el primero con el botón de arriba.",
                icon=":material/arrow_upward:")
        st.stop()

    # --- Lo que le toca corregir: su cola de trabajo ---
    corr = mios[mios["estado"] == ESTADO_CORRECCION]
    st.subheader(f":material/build: En corrección — te toca ({len(corr)})")
    if corr.empty:
        st.success("No tienes folios en corrección.", icon=":material/celebration:")
    else:
        st.caption("Los motivos del rechazo están en el historial del folio y en el PDF. "
                   + CAPTION_ABRIR)
        view = corr[["folio", "cliente", "campana", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_espera_texto)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Rechazado el", "Espera"]
        tabla_folios(view, "miscorr")

    # --- Esperando 2do check ---
    pend = mios[mios["estado"] == ESTADO_PENDIENTE]
    if not pend.empty:
        st.subheader(f":material/schedule: Esperando 2do check ({len(pend)})")
        view = pend[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Enviado el"]
        st.caption(CAPTION_ABRIR)
        tabla_folios(view.sort_values("Enviado el", ascending=False), "misesp")

    # --- Liberados ---
    lib = mios[mios["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f":material/check_circle: Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Liberado el"]
        st.caption(CAPTION_ABRIR)
        tabla_folios(view.sort_values("Liberado el", ascending=False).head(15), "mislib")
