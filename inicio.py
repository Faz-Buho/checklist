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
from itables import JavascriptFunction
from itables.streamlit import interactive_table

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


# Semáforo de espera: verde hasta 1 día, ámbar hasta 3, rojo después.
UMBRAL_VERDE_DIAS = 1
UMBRAL_AMARILLO_DIAS = 3

# Colorea la celda "Espera" como pastilla (mismo lenguaje de badges de la
# app). createdCell corre en el navegador al construir cada celda.
_ESPERA_CELL = JavascriptFunction("""
function(td, cellData){
  if(cellData==null || cellData===''){ return; }
  let d = cellData==='hoy' ? 0 : parseFloat(cellData);
  let bg,fg;
  if(d<=1){bg='#dcfce7';fg='#166534';}
  else if(d<=3){bg='#fef9c3';fg='#854d0e';}
  else {bg='#fee2e2';fg='#991b1b';}
  td.innerHTML = '<span style="background:'+bg+';color:'+fg+';font-weight:600;'
    +'padding:2px 10px;border-radius:9999px;font-size:12px;white-space:nowrap;">'+cellData+'</span>';
}""")


def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def _espera_texto(dias):
    return "hoy" if dias < 1 else f"{dias:.1f} d"


def tabla_folios(df_view, key):
    """Tabla itables (DataTables) consistente: cuadrícula limpia con
    'Espera' como pastilla de color; clic en cualquier fila abre ese folio
    en Captura. El guardia evita reabrir en bucle al volver."""
    df = df_view.reset_index(drop=True)
    col_defs = []
    if "Espera" in df.columns:
        col_defs.append({"targets": list(df.columns).index("Espera"),
                         "createdCell": _ESPERA_CELL})
    res = interactive_table(
        df, key=key, select="single",
        showIndex=False, paging=False, searching=False, info=False,
        columnDefs=col_defs, classes="display compact",
        style="width:100%; margin:0",
    )
    filas = getattr(res, "selected_rows", None) or []
    if filas:
        folio = df.iloc[filas[0]]["Folio"]
        if st.session_state.get(f"_sel_{key}") != folio:
            st.session_state[f"_sel_{key}"] = folio
            st.session_state["folio_abrir"] = folio
            st.switch_page("captura.py")


st.caption("Haz clic en una fila para abrir ese folio.")

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
        tabla_folios(view, "corr")

    # --- Liberados recientes ---
    lib = ultimas[ultimas["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f":material/check_circle: Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Liberado el"]
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
        st.caption("Los motivos del rechazo están en el historial del folio y en el PDF.")
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
        tabla_folios(view.sort_values("Enviado el", ascending=False), "misesp")

    # --- Liberados ---
    lib = mios[mios["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f":material/check_circle: Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Liberado el"]
        tabla_folios(view.sort_values("Liberado el", ascending=False).head(15), "mislib")
