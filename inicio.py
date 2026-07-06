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

st.title("🏠 Inicio")
st.caption(f"Sesión de **{usuario['nombre']}**"
           + (f" ({usuario['email']})" if usuario["email"] else ""))
st.page_link("captura.py", label="Capturar un folio nuevo", icon="📝")

rev_rows = db.get_revisiones_dashboard("todas")

if not rev_rows:
    st.info("Aún no hay folios capturados. Empieza con el botón de arriba. 👆")
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


def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def tabla_abrible(df_view, key):
    """Tabla donde el clic en una fila abre el folio en Captura."""
    sel = st.dataframe(df_view, hide_index=True, width="stretch",
                       on_select="rerun", selection_mode="single-row", key=key)
    filas = sel.selection.rows
    if filas:
        st.session_state["folio_abrir"] = df_view.iloc[filas[0]]["Folio"]
        st.switch_page("captura.py")


if es_evaluador:
    # --- Pendientes de 2do check: la cola de trabajo del evaluador ---
    pend = ultimas[ultimas["estado"] == ESTADO_PENDIENTE]
    st.subheader(f"📥 Pendientes de 2do check ({len(pend)})")
    if pend.empty:
        st.success("No hay folios esperando 2do check. 🎉")
    else:
        view = pend[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view["espera"] = view["fecha"].map(_dias_desde)
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Enviado el", "Días esperando"]
        st.caption("Haz clic en una fila para abrir el 2do check de ese folio.")
        tabla_abrible(view.sort_values("Días esperando", ascending=False), "tabla_pendientes")

    # --- En corrección: esperando a los diseñadores ---
    corr = ultimas[ultimas["estado"] == ESTADO_CORRECCION]
    if not corr.empty:
        st.subheader(f"🔴 En corrección con el diseñador ({len(corr)})")
        view = corr[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Última revisión"]
        tabla_abrible(view.sort_values("Última revisión", ascending=False), "tabla_correccion")

    # --- Liberados recientes ---
    lib = ultimas[ultimas["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f"✅ Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Liberado el"]
        tabla_abrible(view.sort_values("Liberado el", ascending=False).head(15), "tabla_liberados")

else:
    mios = ultimas[ultimas["disenador"] == usuario["nombre"]]
    if mios.empty:
        st.info("Aún no tienes folios. Captura el primero con el botón de arriba. 👆")
        st.stop()

    # --- Lo que le toca corregir: su cola de trabajo ---
    corr = mios[mios["estado"] == ESTADO_CORRECCION]
    st.subheader(f"🔴 En corrección — te toca ({len(corr)})")
    if corr.empty:
        st.success("No tienes folios en corrección. 🎉")
    else:
        st.caption("Haz clic en una fila para abrir tu 1er check y reenviar el folio. "
                   "Los motivos del rechazo están en el historial del folio y en el PDF.")
        view = corr[["folio", "cliente", "campana", "fecha"]].copy()
        view["espera"] = view["fecha"].map(_dias_desde)
        view.columns = ["Folio", "Cliente", "Campaña", "Rechazado el", "Días en corrección"]
        tabla_abrible(view.sort_values("Días en corrección", ascending=False), "tabla_mis_correcciones")

    # --- Esperando 2do check ---
    pend = mios[mios["estado"] == ESTADO_PENDIENTE]
    if not pend.empty:
        st.subheader(f"🕓 Esperando 2do check ({len(pend)})")
        view = pend[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Enviado el"]
        tabla_abrible(view.sort_values("Enviado el", ascending=False), "tabla_mis_pendientes")

    # --- Liberados ---
    lib = mios[mios["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f"✅ Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Liberado el"]
        tabla_abrible(view.sort_values("Liberado el", ascending=False).head(15), "tabla_mis_liberados")
