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
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

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

def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def _espera_texto(dias):
    return "hoy" if dias < 1 else f"{dias:.1f} d"


# "Espera" como pastilla de color centrada (mismo lenguaje de badges del
# resto de la app), no como fondo de celda; se ve intencional y alineado.
_ESPERA_RENDERER = JsCode("""
class R {
  init(p){
    this.e=document.createElement('div');
    this.e.style.cssText='display:flex;align-items:center;height:100%;';
    if(p.value==null){ return; }
    let d = p.value==='hoy' ? 0 : parseFloat(p.value);
    let bg,fg;
    if(d<=1){bg='#dcfce7';fg='#166534';}
    else if(d<=3){bg='#fef9c3';fg='#854d0e';}
    else {bg='#fee2e2';fg='#991b1b';}
    const s=document.createElement('span');
    s.innerText=p.value;
    s.style.cssText='background:'+bg+';color:'+fg+';font-weight:600;'
      +'padding:2px 10px;border-radius:9999px;font-size:12px;white-space:nowrap;';
    this.e.appendChild(s);
  }
  getGui(){return this.e;}
}""")


def _boton_renderer(etiqueta):
    """Botón por fila, centrado, que al hacer clic selecciona la fila
    (AgGrid la devuelve a Python y ahí abrimos el folio). Se usa .replace
    (no el operador %) porque el CSS lleva 'height:100%'."""
    js = """
    class R {
      init(p){
        this.e=document.createElement('div');
        this.e.style.cssText='display:flex;align-items:center;justify-content:center;height:100%;';
        const b=document.createElement('button');
        b.innerText='__LABEL__';
        b.style.cssText='background:#ff4b4b;color:#fff;border:none;border-radius:6px;'
          +'padding:4px 14px;cursor:pointer;font-weight:600;font-size:13px;';
        b.addEventListener('click',e=>{e.stopPropagation(); p.node.setSelected(true);});
        this.e.appendChild(b);}
      getGui(){return this.e;} }"""
    return JsCode(js.replace("__LABEL__", etiqueta))


def tabla_folios(df_view, key, accion=None):
    """Grid (AgGrid) consistente: cuadrícula limpia, columna 'Espera'
    coloreada y —si 'accion' se indica— un botón por fila que abre ese
    folio en Captura. El guardia evita reabrir en bucle al volver."""
    df = df_view.copy()
    if accion:
        df["Acción"] = ""
    fila_px = 36
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(sortable=True, filterable=False, resizable=True)
    gb.configure_grid_options(suppressCellFocus=True, rowHeight=fila_px, headerHeight=fila_px)
    gb.configure_selection("single", use_checkbox=False)
    if "Espera" in df.columns:
        gb.configure_column("Espera", cellRenderer=_ESPERA_RENDERER, width=100)
    if accion:
        gb.configure_column("Acción", header_name="", cellRenderer=_boton_renderer(accion),
                            width=130, pinned="right", sortable=False)
    # Altura ajustada al contenido (encabezado + filas), sin espacio muerto.
    altura = fila_px * (len(df) + 1) + 4
    resp = AgGrid(df, gridOptions=gb.build(), allow_unsafe_jscode=True,
                  update_mode=GridUpdateMode.SELECTION_CHANGED, theme="streamlit",
                  fit_columns_on_grid_load=True, height=altura, key=key)
    if accion:
        sr = resp.selected_rows
        if sr is not None and len(sr):
            folio = sr.iloc[0]["Folio"] if hasattr(sr, "iloc") else sr[0]["Folio"]
            if st.session_state.get(f"_sel_{key}") != folio:
                st.session_state[f"_sel_{key}"] = folio
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
        tabla_folios(view, "pend", accion="Revisar →")

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
        tabla_folios(view, "corr", accion="Abrir →")

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
        tabla_folios(view, "miscorr", accion="Corregir →")

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
