"""
Identidad y roles de la app.

Dos modos, elegidos automáticamente:

1. Con login de Google (cuando hay una sección [auth] en los secrets,
   ver DEPLOY.md): cada quien inicia sesión con su cuenta y SOLO se
   permiten correos de los dominios de la empresa (o los listados
   explícitamente). El rol se asigna por correo.

2. Sin login (uso local, o Streamlit Cloud restringido por viewers):
   selector de nombre en la barra lateral. El acceso lo controla la
   lista de viewers de Streamlit Cloud; el selector solo dice quién es.

Roles:
- evaluador: hace el 2do check, ve la cola de pendientes y el dashboard.
- disenador: hace el 1er check de sus folios.
"""

import streamlit as st

DOMINIOS_PERMITIDOS = {"buhoms.com", "buho.com"}

ROL_EVALUADOR = "evaluador"
ROL_DISENADOR = "disenador"

# Correos con rol de evaluador (2do check). Cualquier otro correo de un
# dominio permitido entra como diseñador.
EVALUADORES = {
    "pfaz@buhoms.com": "Pablo Faz",
    "mhernandez@buhoms.com": "Mariana Hernandez",
    "pablo.faz.meza@gmail.com": "Pablo Faz",  # correo personal de Pablo
}

# Correos de diseñadores con nombre para mostrar (opcional: un correo de
# dominio permitido que no esté aquí entra igual, mostrando su correo).
# TODO: reemplazar los placeholders por los nombres reales.
DISENADORES = {
    "mfernandez@buhoms.com": "Diseñador 1",
    "fhernandez@buhoms.com": "Diseñador 2",
    "dsifuentes@buhoms.com": "Diseñador 3",
}

# Nombres para el modo sin login (selector). Reemplazar los placeholders
# de diseñador por los nombres reales cuando estén definidos.
EVALUADORES_LOCAL = ["Pablo Faz", "Mariana Hernandez"]
DISENADORES_LOCAL = ["Diseñador 1", "Diseñador 2", "Diseñador 3"]


def _auth_configurado():
    try:
        return "auth" in st.secrets
    except Exception:
        return False


def _dominio(email):
    return email.rsplit("@", 1)[-1].lower()


def get_usuario():
    """Regresa {'nombre', 'email', 'rol'} o detiene la app si no hay acceso."""
    if _auth_configurado():
        if not st.user.is_logged_in:
            st.title("Doble check de preproyectos Layout")
            st.write("Inicia sesión con tu cuenta de la empresa para continuar.")
            if st.button("Iniciar sesión con Google", type="primary"):
                st.login()
            st.stop()

        email = (st.user.email or "").lower()
        if email in EVALUADORES:
            return {"nombre": EVALUADORES[email], "email": email, "rol": ROL_EVALUADOR}
        if email in DISENADORES:
            return {"nombre": DISENADORES[email], "email": email, "rol": ROL_DISENADOR}
        if _dominio(email) in DOMINIOS_PERMITIDOS:
            return {"nombre": email, "email": email, "rol": ROL_DISENADOR}

        st.error(f"El correo **{email}** no tiene acceso a esta aplicación. "
                 "Solo se permiten cuentas de los dominios: "
                 + ", ".join(sorted(DOMINIOS_PERMITIDOS)) + ".")
        if st.button("Salir e intentar con otra cuenta"):
            st.logout()
        st.stop()

    # --- Modo sin login: selector de nombre ---
    with st.sidebar:
        nombre = st.selectbox(
            "¿Quién eres? *",
            EVALUADORES_LOCAL + DISENADORES_LOCAL,
            index=None,
            placeholder="Selecciona tu nombre",
            key="usuario_actual",
        )
    if not nombre:
        st.info("👈 Selecciona tu nombre en la barra lateral para comenzar.")
        st.stop()
    rol = ROL_EVALUADOR if nombre in EVALUADORES_LOCAL else ROL_DISENADOR
    return {"nombre": nombre, "email": "", "rol": rol}
