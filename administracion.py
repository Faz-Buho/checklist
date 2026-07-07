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
hoy = datetime.now(TZ_LOCAL).strftime("%Y-%m-%d")
hoy_df = df[df["dia"] == hoy]

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
