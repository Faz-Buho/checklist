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


# Semáforo de espera: verde hasta 1 día, amarillo hasta 3, rojo después.
UMBRAL_VERDE_DIAS = 1
UMBRAL_AMARILLO_DIAS = 3


def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def _semaforo(dias):
    if dias <= UMBRAL_VERDE_DIAS:
        emoji = "🟢"
    elif dias <= UMBRAL_AMARILLO_DIAS:
        emoji = "🟡"
    else:
        emoji = "🔴"
    return f"{emoji} hoy" if dias < 1 else f"{emoji} {dias:.1f} d"


def tabla_accionable(df_view, key, boton="Abrir →"):
    """Tabla con un botón por fila que abre el folio en Captura."""
    spec = [1.0] * len(df_view.columns) + [0.6]
    encabezados = st.columns(spec)
    for col, nombre in zip(encabezados, df_view.columns):
        col.markdown(f"**{nombre}**")
    for _, fila in df_view.iterrows():
        cols = st.columns(spec, vertical_alignment="center")
        for col, valor in zip(cols, fila):
            col.write(valor)
        if cols[-1].button(boton, key=f"{key}_{fila['Folio']}"):
            st.session_state["folio_abrir"] = fila["Folio"]
            st.switch_page("captura.py")


if es_evaluador:
    # --- Pendientes de 2do check: la cola de trabajo del evaluador ---
    pend = ultimas[ultimas["estado"] == ESTADO_PENDIENTE]
    st.subheader(f"📥 Pendientes de 2do check ({len(pend)})")
    if pend.empty:
        st.success("No hay folios esperando 2do check. 🎉")
    else:
        view = pend[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_semaforo)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Enviado el", "Espera"]
        tabla_accionable(view, "pend", boton="Revisar →")

    # --- En corrección: esperando a los diseñadores ---
    corr = ultimas[ultimas["estado"] == ESTADO_CORRECCION]
    if not corr.empty:
        st.subheader(f"🔴 En corrección con el diseñador ({len(corr)})")
        view = corr[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_semaforo)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Rechazado el", "Espera"]
        tabla_accionable(view, "corr")

    # --- Liberados recientes ---
    lib = ultimas[ultimas["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f"✅ Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Liberado el"]
        st.dataframe(view.sort_values("Liberado el", ascending=False).head(15),
                     hide_index=True, width="stretch")

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
        st.caption("Los motivos del rechazo están en el historial del folio y en el PDF.")
        view = corr[["folio", "cliente", "campana", "fecha"]].copy()
        view["dias"] = view["fecha"].map(_dias_desde)
        view = view.sort_values("dias", ascending=False)
        view["espera"] = view["dias"].map(_semaforo)
        view = view.drop(columns=["dias"])
        view.columns = ["Folio", "Cliente", "Campaña", "Rechazado el", "Espera"]
        tabla_accionable(view, "miscorr", boton="Corregir →")

    # --- Esperando 2do check ---
    pend = mios[mios["estado"] == ESTADO_PENDIENTE]
    if not pend.empty:
        st.subheader(f"🕓 Esperando 2do check ({len(pend)})")
        view = pend[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Enviado el"]
        st.dataframe(view.sort_values("Enviado el", ascending=False),
                     hide_index=True, width="stretch")

    # --- Liberados ---
    lib = mios[mios["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.subheader(f"✅ Liberados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Liberado el"]
        st.dataframe(view.sort_values("Liberado el", ascending=False).head(15),
                     hide_index=True, width="stretch")
