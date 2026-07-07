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

st.set_page_config(page_title="Doble check de preproyectos",
                   page_icon=":material/checklist:", layout="wide")

db.init_db()

usuario = auth.get_usuario()

# Registrar el inicio de sesión una sola vez por sesión (para la bitácora
# de auditoría). El "logout" no es capturable en Streamlit; se usa la
# última actividad como aproximación.
if not st.session_state.get("_login_registrado"):
    db.registrar_evento("Inicio de sesión", usuario)
    st.session_state["_login_registrado"] = True

# Interruptor de vista para admins: permite ver la app como evaluador o
# como diseñador sin cambiar de cuenta (para probar ambos flujos).
if auth.es_admin(usuario):
    _, col_switch = st.columns([3, 1])
    with col_switch:
        vista = st.segmented_control(
            "Ver como",
            ["Evaluador", "Diseñador"],
            default="Evaluador",
            key="vista_admin",
            label_visibility="collapsed",
            help="Solo para administradores: cambia entre la vista de "
                 "evaluador (2do check) y la de diseñador (1er check).",
        )
    if vista == "Diseñador":
        usuario = {**usuario, "rol": auth.ROL_DISENADOR}
    else:
        usuario = {**usuario, "rol": auth.ROL_EVALUADOR}

st.session_state["usuario"] = usuario

paginas = [
    st.Page("inicio.py", title="Inicio", icon=":material/home:", default=True),
    st.Page("captura.py", title="Captura", icon=":material/checklist:"),
    st.Page("dashboard.py", title="Dashboard", icon=":material/monitoring:"),
]
# La página de administración solo aparece para admins.
if auth.es_admin(usuario):
    paginas.append(st.Page("administracion.py", title="Administración",
                           icon=":material/admin_panel_settings:"))

pagina = st.navigation(paginas)
pagina.run()
