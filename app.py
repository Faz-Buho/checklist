"""
Doble check de preproyectos Layout — punto de entrada
-----------------------------------------------------
Router de la app multipágina:
- Captura (captura.py): 1er check (diseñador) o 2do check (calidad),
  según el rol del usuario.
- Dashboard (dashboard.py): resultados por campaña y cola de pendientes.

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
st.session_state["usuario"] = usuario

pagina = st.navigation([
    st.Page("captura.py", title="Captura", icon="📝", default=True),
    st.Page("dashboard.py", title="Dashboard", icon="📊"),
])
pagina.run()
