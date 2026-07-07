"""
Página de inicio: la bandeja de trabajo, distinta por rol.

- Evaluador: pendientes de 2do check (su cola), folios en corrección
  (esperando a diseñadores) y liberados recientes.
- Diseñador: SUS folios en corrección (lo que le toca corregir),
  esperando 2do check y liberados.

Cada folio es una TARJETA (no una fila de tabla): la bandeja es una cola
de trabajo, no una hoja de cálculo. Cada tarjeta trae un botón nativo que
abre ese folio en Captura. Se ejecuta vía st.navigation desde app.py.
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

# Semáforo de espera: verde hasta 1 día, ámbar hasta 3, rojo después.
UMBRAL_VERDE_DIAS = 1
UMBRAL_AMARILLO_DIAS = 3

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


def _dias_desde(fecha_str):
    ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
    return round((ahora - datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")).total_seconds() / 86400, 1)


def _badge_espera(dias):
    """Badge de urgencia (color) con el tiempo esperando."""
    texto = "hoy" if dias < 1 else f"{dias:.1f} d"
    color = ("green" if dias <= UMBRAL_VERDE_DIAS
             else "orange" if dias <= UMBRAL_AMARILLO_DIAS else "red")
    return f":{color}-badge[{texto}]"


def tarjeta(row, boton, tipo="primary", fecha_label="Enviado",
            con_espera=True, mostrar_disenador=True, validado_por=None):
    """Una tarjeta de folio con su info en tres niveles (identificador,
    proyecto, metadatos) y un botón que lo abre en Captura."""
    folio = row["folio"]
    with st.container(border=True):
        col_info, col_btn = st.columns([5, 1], vertical_alignment="center")
        with col_info:
            # Nivel 1: el identificador y la urgencia, solos y prominentes
            linea1 = f"##### Folio {folio}"
            if con_espera:
                linea1 += " &nbsp; " + _badge_espera(_dias_desde(row["fecha"]))
            st.markdown(linea1)
            # Nivel 2: cliente y campaña
            proyecto = row["cliente"] or "—"
            if row.get("campana"):
                proyecto += f"  ·  {row['campana']}"
            st.markdown(proyecto)
            # Nivel 3: metadatos, atenuados
            meta = []
            if mostrar_disenador and row.get("disenador"):
                meta.append(f"Diseñador: {row['disenador']}")
            if validado_por:
                meta.append(f"Validado por: {validado_por}")
            meta.append(f"Check No.: {int(row['revision'])}")
            meta.append(f"{fecha_label}: {row['fecha']}")
            st.caption("　·　".join(meta))
        with col_btn:
            if st.button(boton, key=f"open_{folio}", type=tipo, width="stretch"):
                st.session_state["folio_abrir"] = folio
                st.switch_page("captura.py")


def tabla_liberados(view):
    """Liberados como tabla nativa (referencia, no acción)."""
    st.dataframe(view.sort_values(view.columns[-1], ascending=False).head(15),
                 hide_index=True, width="stretch")


def _ordenar_por_espera(sub):
    return sub.assign(_d=sub["fecha"].map(_dias_desde)).sort_values("_d", ascending=False)


if es_evaluador:
    # --- Pendientes de 2do check: la cola de trabajo del evaluador ---
    pend = ultimas[ultimas["estado"] == ESTADO_PENDIENTE]
    st.subheader(f":material/inbox: Pendientes de 2do check ({len(pend)})")
    if pend.empty:
        st.success("No hay folios esperando 2do check.", icon=":material/celebration:")
    else:
        for _, row in _ordenar_por_espera(pend).iterrows():
            tarjeta(row, "Revisar →", tipo="primary", fecha_label="Enviado")

    # --- En corrección: esperando a los diseñadores ---
    corr = ultimas[ultimas["estado"] == ESTADO_CORRECCION]
    if not corr.empty:
        st.divider()
        st.subheader(f":material/build: En corrección con el diseñador ({len(corr)})")
        for _, row in _ordenar_por_espera(corr).iterrows():
            tarjeta(row, "Abrir →", tipo="secondary", fecha_label="Rechazado",
                    validado_por=row["evaluador"])

    # --- Liberados recientes (tabla nativa: es referencia, no acción) ---
    lib = ultimas[ultimas["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.divider()
        st.subheader(f":material/verified: Certificados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "disenador", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Diseñador", "Certificado el"]
        tabla_liberados(view)

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
        for _, row in _ordenar_por_espera(corr).iterrows():
            tarjeta(row, "Corregir →", tipo="primary", fecha_label="Rechazado",
                    mostrar_disenador=False, validado_por=row["evaluador"])

    # --- Esperando 2do check ---
    pend = mios[mios["estado"] == ESTADO_PENDIENTE]
    if not pend.empty:
        st.divider()
        st.subheader(f":material/schedule: Esperando 2do check ({len(pend)})")
        for _, row in pend.sort_values("fecha", ascending=False).iterrows():
            tarjeta(row, "Ver →", tipo="secondary", fecha_label="Enviado",
                    con_espera=False, mostrar_disenador=False)

    # --- Liberados (tabla nativa: es referencia, no acción) ---
    lib = mios[mios["estado"] == ESTADO_LISTO]
    if not lib.empty:
        st.divider()
        st.subheader(f":material/verified: Certificados ({len(lib)})")
        view = lib[["folio", "cliente", "campana", "fecha"]].copy()
        view.columns = ["Folio", "Cliente", "Campaña", "Certificado el"]
        tabla_liberados(view)
