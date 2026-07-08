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

# Usuarios que pueden alternar la vista entre evaluador y diseñador (para
# probar ambos flujos). Por correo (con login) o por nombre (modo local).
ADMINS = {"pfaz@buhoms.com", "pablo.faz.meza@gmail.com"}
ADMINS_LOCAL = {"Pablo Faz"}


def es_admin(usuario):
    return usuario.get("email") in ADMINS or usuario.get("nombre") in ADMINS_LOCAL


# Solo estas personas pueden editar el formulario del checklist (gestor).
# Es más restrictivo que es_admin a propósito.
EDITORES_FORMULARIO = {"pfaz@buhoms.com"}
EDITORES_FORMULARIO_LOCAL = {"Pablo Faz"}


def puede_editar_formulario(usuario):
    return (usuario.get("email") in EDITORES_FORMULARIO
            or (not usuario.get("email") and usuario.get("nombre") in EDITORES_FORMULARIO_LOCAL))

# Correos con rol de evaluador (2do check). Cualquier otro correo de un
# dominio permitido entra como diseñador.
EVALUADORES = {
    "pfaz@buhoms.com": "Pablo Faz",
    "mhernandez@buhoms.com": "Mariana Hernandez",
    "pablo.faz.meza@gmail.com": "Pablo Faz",  # correo personal de Pablo
}

# Correos de diseñadores con nombre para mostrar (opcional: un correo de
# dominio permitido que no esté aquí entra igual, mostrando su correo).
DISENADORES = {
    "mfernandez@buhoms.com": "Mauricio Fernandez",
    "fhernandez@buhoms.com": "Fatima Hernandez",
    "dsifuentes@buhoms.com": "Dana Sofia Sifuentes",
}

# Nombres para el modo sin login (selector de "¿Quién eres?")
EVALUADORES_LOCAL = ["Pablo Faz", "Mariana Hernandez"]
DISENADORES_LOCAL = ["Mauricio Fernandez", "Fatima Hernandez", "Dana Sofia Sifuentes"]


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
        elegido = st.selectbox(
            "¿Quién eres? *",
            EVALUADORES_LOCAL + DISENADORES_LOCAL,
            index=None,
            placeholder="Selecciona tu nombre",
            key="usuario_actual",
        )
    # Persistir el nombre: al navegar entre páginas (p.ej. clic en una
    # fila que abre Captura), el selectbox puede regresar None por un
    # instante; el valor guardado mantiene la sesión estable.
    if elegido:
        st.session_state["nombre_local"] = elegido
    nombre = st.session_state.get("nombre_local")
    if not nombre:
        st.info("Selecciona tu nombre en la barra lateral para comenzar.",
                icon=":material/arrow_back:")
        st.stop()
    rol = ROL_EVALUADOR if nombre in EVALUADORES_LOCAL else ROL_DISENADOR
    return {"nombre": nombre, "email": "", "rol": rol}
