"""
Catálogo del checklist y constantes de estatus.

Vive en su propio módulo porque lo consumen tanto la página de captura
(app.py) como el dashboard (pages/), y app.py no se puede importar desde
otra página sin ejecutar toda su UI.
"""

STATUS_CUMPLE = "Cumple"
STATUS_AJUSTE = "Con ajuste"
STATUS_NO_CUMPLE = "No cumple"
STATUS_NA = "N/A"

STATUS_OPTIONS = [STATUS_CUMPLE, STATUS_AJUSTE, STATUS_NO_CUMPLE, STATUS_NA]

STATUS_REQUIRES_MOTIVO = {STATUS_AJUSTE, STATUS_NO_CUMPLE}

# Color de badge por estatus (sintaxis de markdown de Streamlit
# :color-badge[texto]); conserva el lenguaje verde/ámbar/rojo sin emojis.
STATUS_BADGE_COLOR = {
    STATUS_CUMPLE: "green",
    STATUS_AJUSTE: "orange",
    STATUS_NO_CUMPLE: "red",
    STATUS_NA: "gray",
}

RESULTADO_LISTO = "Listo para producción"
RESULTADO_CORRECCION = "Requiere corrección"
RESULTADO_ENVIADO = "Enviado a 2do check"


def badge(texto, color):
    """Badge de color en markdown de Streamlit."""
    return f":{color}-badge[{texto}]"


def status_badge(status):
    return badge(status, STATUS_BADGE_COLOR.get(status, "gray"))

# Tipos de revisión: el 1er check lo hace el diseñador que desarrolló el
# layout (solo se puede guardar "limpio"); el 2do check es la revisión
# independiente de calidad.
TIPO_PRIMER = "primer"
TIPO_SEGUNDO = "segundo"

# Estado del folio, derivado de su última revisión
ESTADO_PENDIENTE = "Pendiente de 2do check"
ESTADO_CORRECCION = "En corrección"
ESTADO_LISTO = "Listo para producción"

ESTADO_BADGE_COLOR = {
    ESTADO_LISTO: "green",
    ESTADO_CORRECCION: "red",
    ESTADO_PENDIENTE: "orange",
}


def estado_badge(estado):
    return badge(estado, ESTADO_BADGE_COLOR.get(estado, "gray"))

from zoneinfo import ZoneInfo

# El servidor de Streamlit Cloud corre en UTC; las fechas se registran
# en hora de México.
TZ_LOCAL = ZoneInfo("America/Mexico_City")


def estado_folio(revisiones):
    """Deriva el estado del folio de su última revisión (o None si no hay)."""
    if not revisiones:
        return None
    ultima = revisiones[-1]
    if ultima.get("tipo") == TIPO_PRIMER:
        return ESTADO_PENDIENTE
    return ESTADO_LISTO if ultima["resultado"] == RESULTADO_LISTO else ESTADO_CORRECCION

# Cada ítem: id único, categoría (para agrupar), texto a mostrar
CHECKLIST_ITEMS = [
    # --- Parte técnica (con el arte abierto) ---
    {"id": "contenido_1", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Textos y elementos visuales coinciden con el original del cliente (sin cambios, cortes ni typos)"},
    {"id": "contenido_2", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Logo en versión correcta (color/fondo)"},
    {"id": "contenido_3", "bloque": "tecnica", "categoria": "1. Contenido y fidelidad al cliente",
     "texto": "Leyendas legales/obligatorias presentes y vigentes"},

    {"id": "estructura_1", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Medida final correcta y rebase (bleed) presente en todos los bordes"},
    {"id": "estructura_2", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Elementos dentro del margen de seguridad de corte/troquel"},
    {"id": "estructura_3", "bloque": "tecnica", "categoria": "2. Estructura y medidas",
     "texto": "Troquel/dieline alineado con el arte"},

    {"id": "color_1", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Modo de color correcto (CMYK/Pantone según el medio)"},
    {"id": "color_2", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Pantones coinciden con estándar de marca"},
    {"id": "color_3", "bloque": "tecnica", "categoria": "3. Color e impresión",
     "texto": "Resolución de imágenes adecuada para impresión"},

    {"id": "cierre_1", "bloque": "tecnica", "categoria": "4. Cierre técnico del archivo",
     "texto": "Sin capas ocultas ni restos de versiones anteriores"},
    {"id": "cierre_2", "bloque": "tecnica", "categoria": "4. Cierre técnico del archivo",
     "texto": "Fuentes en curvas/embebidas, exportado en formato correcto"},

    # --- Parte operativa (contra la orden de trabajo) ---
    {"id": "operativo_1", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Cantidad del layout coincide con el total de la orden y suma correctamente por versión"},
    {"id": "operativo_2", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Todas las versiones están presentes y completas"},
    {"id": "operativo_3", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "SKU, fechas de inicio/envío correctos"},
    {"id": "operativo_4", "bloque": "operativa", "categoria": "5. Datos operativos",
     "texto": "Producción correctamente asignada a la planta correspondiente"},

    {"id": "nomenclatura_1", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Número de OT correcto y coincide con la orden de trabajo"},
    {"id": "nomenclatura_2", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Nombre operativo / proyecto correcto (coincide con la orden de trabajo)"},
    {"id": "nomenclatura_3", "bloque": "operativa", "categoria": "6. Nomenclatura y trazabilidad",
     "texto": "Nombre de archivo sigue convención interna"},
]

ITEM_TEXTO = {i["id"]: i["texto"] for i in CHECKLIST_ITEMS}
ITEM_CATEGORIA = {i["id"]: i["categoria"] for i in CHECKLIST_ITEMS}

BLOQUES = [
    ("tecnica", "Parte técnica (con el arte abierto)"),
    ("operativa", "Parte operativa (contra la orden de trabajo)"),
]
