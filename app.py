"""
Doble check de preproyectos Layout — punto de entrada
-----------------------------------------------------
Router de la app multipágina:
- Inicio (inicio.py): bandeja de trabajo por rol (pendientes, en
  corrección, liberados) con clic para abrir cada folio.
- Captura (captura.py): 1er check (diseñador) o 2do check (calidad),
  según el rol del usuario.
- Dashboard (dashboard.py): métricas y resultados por campaña.

Cómo correrla:
    pip install -r requirements.txt
    streamlit run app.py

Almacenamiento (ver db.py): SQLite local por default; si hay un secret
o variable de entorno DATABASE_URL, se conecta a Postgres (Supabase).
Identidad y roles: ver auth.py (login de Google restringido por dominio
cuando hay sección [auth] en secrets; selector de nombre si no).
"""

import streamlit as st

import auth
import db

st.set_page_config(page_title="Doble check de preproyectos", page_icon="✅", layout="wide")

db.init_db()

usuario = auth.get_usuario()

# Interruptor de vista para admins: permite ver la app como evaluador o
# como diseñador sin cambiar de cuenta (para probar ambos flujos).
if auth.es_admin(usuario):
    _, col_switch = st.columns([3, 1])
    with col_switch:
        vista = st.segmented_control(
            "Ver como",
            ["🔎 Evaluador", "🎨 Diseñador"],
            default="🔎 Evaluador",
            key="vista_admin",
            label_visibility="collapsed",
            help="Solo para administradores: cambia entre la vista de "
                 "evaluador (2do check) y la de diseñador (1er check).",
        )
    if vista == "🎨 Diseñador":
        usuario = {**usuario, "rol": auth.ROL_DISENADOR}
    else:
        usuario = {**usuario, "rol": auth.ROL_EVALUADOR}

st.session_state["usuario"] = usuario

pagina = st.navigation([
    st.Page("inicio.py", title="Inicio", icon="🏠", default=True),
    st.Page("captura.py", title="Captura", icon="📝"),
    st.Page("dashboard.py", title="Dashboard", icon="📊"),
])
pagina.run()
