"""
Notificaciones por correo (SMTP de Gmail).

Se disparan al guardar una revisión (ver captura.py):
- 1er check enviado  -> avisa a los EVALUADORES que hay un folio en la cola.
- 2do check "Requiere corrección" -> avisa al DISEÑADOR del folio (con el PDF).
- 2do check "Listo para producción" -> avisa al diseñador (opcional, con flag).

Configuración por secrets de Streamlit, sección [notificaciones]:

    [notificaciones]
    activo = true
    remitente = "avisos@buhoms.com"     # cuenta @buhoms.com que envía
    password = "xxxx xxxx xxxx xxxx"     # CONTRASEÑA DE APLICACIÓN de Google
    url_app = "https://buho-checklist.streamlit.app"
    nombre = "Doble Check Búho"          # opcional, nombre visible del remitente
    avisar_listos = false                # opcional, avisar también los liberados
    solo_a = "pfaz@buhoms.com"           # opcional: para PROBAR, manda TODO solo
                                         # a este correo (quítalo para ir en vivo)

Si la sección no existe o activo=false, no se manda nada y NADA falla: las
notificaciones son "mejor esfuerzo" y nunca deben bloquear el guardado.
"""

import smtplib
from email.message import EmailMessage

import auth
from catalogo import (
    RESULTADO_CORRECCION,
    RESULTADO_LISTO,
    TIPO_PRIMER,
    TIPO_SEGUNDO,
)


def _config():
    """Regresa la config de notificaciones si está activa y completa, o None."""
    try:
        import streamlit as st
        cfg = st.secrets.get("notificaciones", {})
    except Exception:
        return None
    if not cfg or not cfg.get("activo"):
        return None
    if not cfg.get("remitente") or not cfg.get("password"):
        return None
    return cfg


def enviar(destinatarios, asunto, cuerpo_html, pdf=None, pdf_nombre="reporte.pdf"):
    """Manda un correo por SMTP de Gmail. Regresa True/False; nunca lanza."""
    cfg = _config()
    destinatarios = [d for d in destinatarios if d]
    if not cfg or not destinatarios:
        return False
    # Válvula de prueba: si hay 'solo_a', TODO se manda solo a ese correo.
    if cfg.get("solo_a"):
        destinatarios = [cfg["solo_a"]]
    try:
        remitente = cfg["remitente"]
        msg = EmailMessage()
        msg["From"] = f'{cfg.get("nombre", "Doble Check Búho")} <{remitente}>'
        msg["To"] = ", ".join(destinatarios)
        msg["Subject"] = asunto
        msg.set_content("Este mensaje se ve mejor en un lector con HTML.")
        msg.add_alternative(cuerpo_html, subtype="html")
        if pdf:
            msg.add_attachment(pdf, maintype="application", subtype="pdf",
                               filename=pdf_nombre)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(remitente, cfg["password"])
            s.send_message(msg)
        return True
    except Exception as e:
        # El correo es "mejor esfuerzo": un fallo aquí NUNCA debe romper el
        # guardado de la revisión.
        print(f"[notificaciones] fallo al enviar: {e}")
        return False


def _cuerpo(titulo, filas, link, nota=""):
    """Arma un HTML sencillo: título, tabla de datos, link y nota opcional."""
    trs = "".join(
        f'<tr><td style="padding:2px 10px 2px 0;color:#666">{k}</td>'
        f'<td style="padding:2px 0"><b>{v}</b></td></tr>'
        for k, v in filas if v
    )
    boton = (f'<p style="margin:18px 0"><a href="{link}" '
             'style="background:#e2483d;color:#fff;padding:10px 18px;'
             'border-radius:6px;text-decoration:none">Abrir en la app</a></p>'
             if link else "")
    nota_html = f'<p style="color:#666">{nota}</p>' if nota else ""
    return (
        '<div style="font-family:sans-serif;font-size:15px;color:#222">'
        f'<h2 style="margin:0 0 12px">{titulo}</h2>'
        f'<table>{trs}</table>{boton}{nota_html}'
        '<hr style="border:none;border-top:1px solid #eee;margin:20px 0">'
        '<p style="color:#999;font-size:12px">Doble Check de Preproyectos — Búho. '
        'Mensaje automático, no respondas a este correo.</p>'
        '</div>'
    )


def notificar_revision(*, tipo, resultado, folio, cliente, campana,
                       quien, disenador_folio, pdf=None):
    """Decide destinatarios y contenido según el tipo/resultado, y envía.

    'mejor esfuerzo': si algo falla o no hay config, no hace nada y no lanza.
    """
    cfg = _config()
    if not cfg:
        return
    link = (cfg.get("url_app") or "").rstrip("/")
    base_filas = [("Folio", folio), ("Cliente", cliente), ("Campaña", campana)]

    if tipo == TIPO_PRIMER:
        # El folio entró a la cola: avisar a los evaluadores.
        destinatarios = auth.correos_evaluadores()
        filas = base_filas + [("Enviado por", quien)]
        enviar(destinatarios,
               f"[Búho] Folio {folio} listo para 2do check",
               _cuerpo("Nuevo folio en la cola de 2do check", filas, link))

    elif tipo == TIPO_SEGUNDO and resultado == RESULTADO_CORRECCION:
        # Rechazado: avisar al diseñador del folio, con el PDF del detalle.
        destinatarios = [auth.correo_de(disenador_folio)]
        filas = base_filas + [("Revisó", quien), ("Resultado", resultado)]
        enviar(destinatarios,
               f"[Búho] Folio {folio} requiere corrección",
               _cuerpo("Tu folio requiere corrección", filas, link,
                       nota="Adjuntamos el reporte con el detalle de lo que "
                            "hay que ajustar. Corrígelo y vuelve a pasar tu "
                            "1er check."),
               pdf=pdf, pdf_nombre=f"Reporte_{folio}.pdf")

    elif (tipo == TIPO_SEGUNDO and resultado == RESULTADO_LISTO
          and cfg.get("avisar_listos")):
        destinatarios = [auth.correo_de(disenador_folio)]
        filas = base_filas + [("Revisó", quien)]
        enviar(destinatarios,
               f"[Búho] Folio {folio} liberado para producción",
               _cuerpo("Folio liberado para producción", filas, link,
                       nota="¡Tu folio pasó el 2do check y quedó listo!"))
