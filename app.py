"""
Doble check de preproyectos Layout — punto de entrada
-----------------------------------------------------
Router de la app multipágina:
- Captura (captura.py): el checklist de revisión por folio.
- Dashboard (dashboard.py): resultados por campaña.

Cómo correrla:
    pip install -r requirements.txt
    streamlit run app.py

Almacenamiento (ver db.py): SQLite local por default; si hay un secret
o variable de entorno DATABASE_URL, se conecta a Postgres (Supabase).
"""

import streamlit as st

import db

st.set_page_config(page_title="Doble check de preproyectos", page_icon="✅", layout="wide")

db.init_db()

pagina = st.navigation([
    st.Page("captura.py", title="Captura", icon="📝", default=True),
    st.Page("dashboard.py", title="Dashboard", icon="📊"),
])
pagina.run()
