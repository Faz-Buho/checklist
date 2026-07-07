"""
Página de administración: auditoría de accesos y acciones del equipo.
Solo visible para administradores (ver auth.es_admin). Se ejecuta vía
st.navigation desde app.py.

Registra y muestra: inicios de sesión, 1er/2do checks y gestión de
campañas. Nota: el "cierre de sesión" no es capturable en Streamlit; se
usa la última actividad como aproximación de hasta cuándo estuvo activo
cada usuario.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

import db
from auth import es_admin
from catalogo import TZ_LOCAL

usuario = st.session_state["usuario"]
if not es_admin(usuario):
    st.error("Esta sección es solo para administradores.", icon=":material/lock:")
    st.stop()

st.title(":material/admin_panel_settings: Administración")
st.caption("Auditoría de accesos y acciones del equipo.")

eventos = db.get_eventos(limite=5000)
if not eventos:
    st.info("Aún no hay eventos registrados.", icon=":material/history:")
    st.stop()

df = pd.DataFrame(eventos)
df["dia"] = df["fecha"].str[:10]
ahora = datetime.now(TZ_LOCAL).replace(tzinfo=None)
hoy = ahora.strftime("%Y-%m-%d")
hoy_df = df[df["dia"] == hoy]

# --- Usuarios conectados (presencia por actividad reciente) ---
UMBRAL_EN_LINEA_MIN = 10


def _hace(last_seen):
    try:
        dt = datetime.strptime(last_seen, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None
    return (ahora - dt).total_seconds() / 60


presencia = db.get_presencia()
en_linea = [p for p in presencia
            if (_hace(p["last_seen"]) or 1e9) < UMBRAL_EN_LINEA_MIN]

col_t, col_r = st.columns([4, 1], vertical_alignment="bottom")
col_t.subheader(f":material/group: Usuarios conectados　:green-badge[{len(en_linea)} en línea]")
if col_r.button("Actualizar", icon=":material/refresh:", width="stretch"):
    st.rerun()

if not presencia:
    st.caption("Aún no hay actividad registrada.")
else:
    filas = []
    for p in presencia:
        mins = _hace(p["last_seen"])
        if mins is None:
            estado = "—"
        elif mins < UMBRAL_EN_LINEA_MIN:
            estado = "En línea"
        elif mins < 60:
            estado = f"hace {int(mins)} min"
        elif mins < 1440:
            estado = f"hace {int(mins // 60)} h"
        else:
            estado = f"hace {int(mins // 1440)} d"
        filas.append({"Usuario": p["usuario"], "Rol": p["rol"],
                      "Estado": estado, "Última actividad": p["last_seen"]})
    pres_df = pd.DataFrame(filas)

    def _color_en_linea(col):
        return ["background-color: #dcfce7; color: #166534; font-weight: 600"
                if v == "En línea" else "" for v in col]

    st.dataframe(pres_df.style.apply(_color_en_linea, subset=["Estado"]),
                 hide_index=True, width="stretch")
st.caption(f"«En línea» = actividad en los últimos {UMBRAL_EN_LINEA_MIN} min. "
           "Streamlit no puede detectar el cierre de sesión, así que se usa "
           "la actividad reciente como aproximación.")

st.divider()

# --- Resumen ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Eventos (total)", len(df))
m2.metric("Inicios de sesión hoy",
          int((hoy_df["accion"] == "Inicio de sesión").sum()))
m3.metric("Usuarios activos hoy", hoy_df["usuario"].nunique())
m4.metric("Acciones hoy", len(hoy_df))

st.divider()

# --- Actividad por persona ---
st.subheader(":material/groups: Actividad por persona")
piv = (df.pivot_table(index="usuario", columns="accion", values="fecha",
                      aggfunc="count", fill_value=0)
       .reset_index())
ultima = df.groupby("usuario")["fecha"].max()
total = df.groupby("usuario").size()
piv["Última actividad"] = piv["usuario"].map(ultima)
piv["Total"] = piv["usuario"].map(total)
piv = piv.rename(columns={"usuario": "Usuario"}).sort_values("Total", ascending=False)
st.dataframe(piv, hide_index=True, width="stretch")

st.divider()

# --- Bitácora filtrable ---
st.subheader(":material/history: Bitácora de eventos")
c1, c2, c3 = st.columns(3)
u_sel = c1.selectbox("Usuario", ["Todos"] + sorted(df["usuario"].dropna().unique()))
a_sel = c2.selectbox("Acción", ["Todas"] + sorted(df["accion"].dropna().unique()))
dia_sel = c3.selectbox("Día", ["Todos"] + sorted(df["dia"].unique(), reverse=True))

fil = df
if u_sel != "Todos":
    fil = fil[fil["usuario"] == u_sel]
if a_sel != "Todas":
    fil = fil[fil["accion"] == a_sel]
if dia_sel != "Todos":
    fil = fil[fil["dia"] == dia_sel]

tabla = fil[["fecha", "usuario", "email", "rol", "accion", "folio", "detalle"]].copy()
tabla.columns = ["Fecha", "Usuario", "Correo", "Rol", "Acción", "Folio", "Detalle"]
st.caption(f"{len(tabla)} evento(s)")
st.dataframe(tabla, hide_index=True, width="stretch")
