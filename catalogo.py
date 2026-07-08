"""
Catálogo del checklist y constantes compartidas.

Vive en su propio módulo porque lo consumen varias páginas (captura,
inicio, dashboard, administración) y app.py no se puede importar desde
otra página sin ejecutar toda su UI.

PARA EDITAR EL TEXTO DEL FORMULARIO ve directo a la sección
«CHECKLIST — el formulario» al final (CHECKLIST_ITEMS y BLOQUES).
Lo de arriba son constantes de lógica: no cambies sus valores.
"""

from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------
# Zona horaria
# ---------------------------------------------------------------------
# El servidor de Streamlit Cloud corre en UTC; las fechas se registran
# en hora de México.
TZ_LOCAL = ZoneInfo("America/Mexico_City")


# ---------------------------------------------------------------------
# Estatus de cada punto (los 4 niveles de evaluación)
# ---------------------------------------------------------------------
STATUS_CUMPLE = "Cumple"
STATUS_AJUSTE = "Con ajuste"
STATUS_NO_CUMPLE = "No cumple"
STATUS_NA = "N/A"

STATUS_OPTIONS = [STATUS_CUMPLE, STATUS_AJUSTE, STATUS_NO_CUMPLE, STATUS_NA]

# "Con ajuste" y "No cumple" exigen escribir un motivo.
STATUS_REQUIRES_MOTIVO = {STATUS_AJUSTE, STATUS_NO_CUMPLE}

# Color del badge por estatus (verde/ámbar/rojo, sin emojis).
STATUS_BADGE_COLOR = {
    STATUS_CUMPLE: "green",
    STATUS_AJUSTE: "orange",
    STATUS_NO_CUMPLE: "red",
    STATUS_NA: "gray",
}


# ---------------------------------------------------------------------
# Resultado de una revisión y tipo de check
# ---------------------------------------------------------------------
RESULTADO_LISTO = "Listo para producción"
RESULTADO_CORRECCION = "Requiere corrección"
RESULTADO_ENVIADO = "Enviado a 2do check"

# El 1er check lo hace el diseñador que desarrolló el layout (solo se
# puede enviar "limpio"); el 2do check es la revisión independiente.
TIPO_PRIMER = "primer"
TIPO_SEGUNDO = "segundo"


# ---------------------------------------------------------------------
# Estado del folio (derivado de su última revisión)
# ---------------------------------------------------------------------
ESTADO_PENDIENTE = "Pendiente de 2do check"
ESTADO_CORRECCION = "En corrección"
ESTADO_LISTO = "Listo para producción"

ESTADO_BADGE_COLOR = {
    ESTADO_LISTO: "green",
    ESTADO_CORRECCION: "red",
    ESTADO_PENDIENTE: "orange",
}


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def badge(texto, color):
    """Badge de color en markdown de Streamlit (:color-badge[texto])."""
    return f":{color}-badge[{texto}]"


def status_badge(status):
    return badge(status, STATUS_BADGE_COLOR.get(status, "gray"))


def estado_badge(estado):
    return badge(estado, ESTADO_BADGE_COLOR.get(estado, "gray"))


def estado_folio(revisiones):
    """Deriva el estado del folio de su última revisión (o None si no hay)."""
    if not revisiones:
        return None
    ultima = revisiones[-1]
    if ultima.get("tipo") == TIPO_PRIMER:
        return ESTADO_PENDIENTE
    return ESTADO_LISTO if ultima["resultado"] == RESULTADO_LISTO else ESTADO_CORRECCION


# =====================================================================
# CHECKLIST — el formulario  (EDITA AQUÍ el texto de los puntos)
# =====================================================================
# Los dos grandes bloques del checklist, en el orden en que se muestran:
BLOQUES = [
    ("tecnica", "Parte técnica (con el arte abierto)"),
    ("operativa", "Parte operativa (contra la orden de trabajo)"),
]

# Cada punto del checklist es un diccionario con:
#   id        -> identificador único (NO lo cambies en puntos ya usados;
#                es la llave con la que se guarda cada respuesta)
#   bloque    -> "tecnica" u "operativa"
#   categoria -> subtítulo que agrupa varios puntos
#   texto     -> el enunciado que lee el evaluador (edítalo libremente)
# Los puntos se muestran en el mismo orden en que aparecen aquí.
CHECKLIST_ITEMS = [

    # ===================  PARTE TÉCNICA (con el arte abierto)  ===================

    # 1. Contenido y fidelidad al cliente
    {"id": "contenido_1", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Textos y elementos visuales coinciden con el original del cliente (sin cambios, cortes ni typos)"},
    {"id": "contenido_2", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Logo en versión correcta (color/fondo)"},
    {"id": "contenido_3", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Leyendas legales/obligatorias presentes y vigentes"},

    # 2. Estructura y medidas
    {"id": "estructura_1", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Medida final correcta y rebase (bleed) presente en todos los bordes"},
    {"id": "estructura_2", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Elementos dentro del margen de seguridad de corte/troquel"},
    {"id": "estructura_3", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Troquel/dieline alineado con el arte"},

    # 3. Color e impresión
    {"id": "color_1", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Modo de color correcto (CMYK/Pantone según el medio)"},
    {"id": "color_2", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Pantones coinciden con estándar de marca"},
    {"id": "color_3", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Resolución de imágenes adecuada para impresión"},

    # 4. Cierre técnico del archivo
    {"id": "cierre_1", "bloque": "tecnica", "categoria": "4. Cierre técnico del archivo",
     "texto": "Sin capas ocultas ni restos de versiones anteriores"},
    {"id": "cierre_2", "bloque": "tecnica", "categoria": "4. Cierre técnico del archivo",
     "texto": "Fuentes en curvas/embebidas, exportado en formato correcto"},

    # ==================  PARTE OPERATIVA (contra la orden de trabajo)  ==================

    # 5. Datos operativos
    {"id": "operativo_1", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Cantidad del layout coincide con el total de la orden y suma correctamente por versión"},
    {"id": "operativo_2", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Todas las versiones están presentes y completas"},
    {"id": "operativo_3", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "SKU, fechas de inicio/envío correctos"},
    {"id": "operativo_4", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Producción correctamente asignada a la planta correspondiente"},

    # 6. Nomenclatura y trazabilidad
    {"id": "nomenclatura_1", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Número de OT correcto y coincide con la orden de trabajo"},
    {"id": "nomenclatura_2", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Nombre operativo / proyecto correcto (coincide con la orden de trabajo)"},
    {"id": "nomenclatura_3", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Nombre de archivo sigue convención interna"},
]

# Búsquedas rápidas por id (derivadas de CHECKLIST_ITEMS; no editar).
ITEM_TEXTO = {i["id"]: i["texto"] for i in CHECKLIST_ITEMS}
ITEM_CATEGORIA = {i["id"]: i["categoria"] for i in CHECKLIST_ITEMS}
