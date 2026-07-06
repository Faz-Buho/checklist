"""
Página de dashboard: resultados por campaña (10-20 folios por campaña)
y cola de pendientes de 2do check. Se ejecuta vía st.navigation desde
app.py.

Métricas clave (calculadas SOLO sobre 2dos checks, la revisión
independiente de calidad; los 1er checks del diseñador no cuentan
porque siempre se guardan "limpios"):
- % de folios listos a la primera (first-pass yield): calidad real del
  proceso, no solo del retrabajo.
- 2dos checks por folio: cuánto retrabajo genera la campaña.
- Top de puntos que más fallan: señala problemas de proceso (si un punto
  falla en muchos folios, la causa no es un diseñador).
"""

import altair as alt
import pandas as pd
import streamlit as st

import db
from catalogo import (
    ESTADO_CORRECCION,
    ESTADO_LISTO,
    ESTADO_PENDIENTE,
    ITEM_TEXTO,
    RESULTADO_LISTO,
    STATUS_REQUIRES_MOTIVO,
    TIPO_PRIMER,
    TIPO_SEGUNDO,
)

# Azul validado para barras de una sola serie (ver skill de dataviz);
# la identidad no depende del color: todas las barras llevan etiqueta.
COLOR_BARRA = "#2a78d6"

ESTADO_TEXTO = {
    ESTADO_PENDIENTE: "🕓 Pendiente de 2do check",
    ESTADO_CORRECCION: "🔴 En corrección",
    ESTADO_LISTO: "✅ Listo",
}

st.title("Dashboard de campañas")

# --- Selector de campaña ---
TODAS = "Todas las campañas"
SIN_CAMPANA = "(Sin campaña)"

campanas = db.get_campanas()
opciones = {TODAS: "todas", SIN_CAMPANA: None}
for c in campanas:
    etiqueta = c["nombre"] + (" 🔒 (cerrada)" if c["estado"] == "cerrada" else "")
    opciones[etiqueta] = c["id"]

seleccion = st.selectbox("Campaña", list(opciones))
filtro = opciones[seleccion]

rev_rows = db.get_revisiones_dashboard(filtro)

if not rev_rows:
    st.info("Aún no hay revisiones guardadas para esta selección. "
            "Captura folios en la página **📝 Captura** y aquí aparecerán los resultados.")
else:
    df_rev = pd.DataFrame(rev_rows)
    df_seg = df_rev[df_rev["tipo"] == TIPO_SEGUNDO]

    # Estado por folio: lo define su última revisión (de cualquier tipo).
    ultimas = df_rev.loc[df_rev.groupby("folio")["revision"].idxmax()].copy()
    ultimas["estado"] = [
        ESTADO_PENDIENTE if t == TIPO_PRIMER
        else (ESTADO_LISTO if r == RESULTADO_LISTO else ESTADO_CORRECCION)
        for t, r in zip(ultimas["tipo"], ultimas["resultado"])
    ]

    n_folios = len(ultimas)
    n_listos = int((ultimas["estado"] == ESTADO_LISTO).sum())
    n_correccion = int((ultimas["estado"] == ESTADO_CORRECCION).sum())
    n_pendientes = int((ultimas["estado"] == ESTADO_PENDIENTE).sum())

    # "A la primera": el PRIMER 2do check del folio salió listo.
    if df_seg.empty:
        yield_pct = None
        prom_seg = None
    else:
        primeras_seg = df_seg.loc[df_seg.groupby("folio")["revision"].idxmin()]
        yield_pct = 100 * (primeras_seg["resultado"] == RESULTADO_LISTO).mean()
        prom_seg = df_seg.groupby("folio").size().mean()

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Folios", n_folios)
    m2.metric("✅ Listos", n_listos)
    m3.metric("🔴 En corrección", n_correccion)
    m4.metric("🕓 Pendientes", n_pendientes)
    m5.metric("Listos a la primera",
              "—" if yield_pct is None else f"{yield_pct:.0f} %",
              help="Porcentaje de folios cuyo PRIMER 2do check salió "
                   "'Listo para producción'")

    st.divider()

    col_izq, col_der = st.columns([3, 2])

    # --- Top de puntos que más fallan (solo 2dos checks) ---
    with col_izq:
        st.subheader("Puntos que más fallan")
        resp_rows = db.get_respuestas_dashboard(filtro)
        df_resp = pd.DataFrame(resp_rows)
        fallas = (df_resp[df_resp["status"].isin(STATUS_REQUIRES_MOTIVO)]
                  if not df_resp.empty else df_resp)
        if fallas.empty:
            st.success("Ninguna falla registrada en esta selección. 🎉")
        else:
            conteo = (fallas.groupby("item_id").size()
                      .sort_values(ascending=False).head(10)
                      .rename("fallas").reset_index())
            conteo["punto"] = conteo["item_id"].map(
                lambda i: ITEM_TEXTO.get(i, i)[:58] + ("…" if len(ITEM_TEXTO.get(i, i)) > 58 else ""))

            base = alt.Chart(conteo).encode(
                x=alt.X("fallas:Q", title="Veces marcado 'Con ajuste' o 'No cumple'",
                        axis=alt.Axis(format="d", tickMinStep=1)),
                y=alt.Y("punto:N", sort="-x", title=None),
                tooltip=[alt.Tooltip("punto:N", title="Punto"),
                         alt.Tooltip("fallas:Q", title="Fallas")],
            )
            barras = base.mark_bar(color=COLOR_BARRA, cornerRadiusEnd=4, height=18)
            etiquetas = base.mark_text(align="left", dx=4).encode(text="fallas:Q")
            st.altair_chart((barras + etiquetas).properties(
                height=max(120, 30 * len(conteo))), width="stretch")

    # --- Estado por folio ---
    with col_der:
        st.subheader("Estado por folio")
        tabla = ultimas.merge(
            df_seg.groupby("folio").size().rename("segundos_checks"),
            on="folio", how="left",
        )
        tabla["segundos_checks"] = tabla["segundos_checks"].fillna(0).astype(int)
        tabla["estado"] = tabla["estado"].map(ESTADO_TEXTO)
        tabla = tabla[["folio", "cliente", "campana", "segundos_checks", "estado", "fecha"]]
        tabla.columns = ["Folio", "Cliente", "Campaña", "2dos checks", "Estado", "Última revisión"]
        if seleccion != TODAS:
            tabla = tabla.drop(columns=["Campaña"])
        st.dataframe(tabla.sort_values("Última revisión", ascending=False),
                     hide_index=True, width="stretch")

    # --- Comparativa entre campañas (solo en vista global) ---
    if (seleccion == TODAS and not df_seg.empty
            and df_rev["campana"].nunique(dropna=True) > 1):
        st.divider()
        st.subheader("Comparativa entre campañas")
        primeras_seg = df_seg.loc[df_seg.groupby("folio")["revision"].idxmin()].copy()
        primeras_seg["campana"] = primeras_seg["campana"].fillna(SIN_CAMPANA)

        resumen = (primeras_seg.assign(
            listo=(primeras_seg["resultado"] == RESULTADO_LISTO).astype(int))
            .groupby("campana").agg(folios=("folio", "count"), a_la_primera=("listo", "mean"))
            .reset_index())
        resumen["a_la_primera"] *= 100
        resumen["etiqueta"] = resumen.apply(
            lambda r: f"{r['a_la_primera']:.0f} % ({r['folios']} folios)", axis=1)

        base = alt.Chart(resumen).encode(
            x=alt.X("a_la_primera:Q", title="% de folios listos a la primera",
                    scale=alt.Scale(domain=[0, 100])),
            y=alt.Y("campana:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("campana:N", title="Campaña"),
                     alt.Tooltip("a_la_primera:Q", title="Listos a la primera (%)", format=".0f"),
                     alt.Tooltip("folios:Q", title="Folios")],
        )
        barras = base.mark_bar(color=COLOR_BARRA, cornerRadiusEnd=4, height=18)
        etiquetas = base.mark_text(align="left", dx=4).encode(text="etiqueta:N")
        st.altair_chart((barras + etiquetas).properties(
            height=max(100, 34 * len(resumen))), width="stretch")

# --- Gestión de campañas ---
st.divider()
with st.expander("⚙️ Gestión de campañas"):
    st.caption("Cerrar una campaña solo la oculta del selector de captura; "
               "no bloquea nada y siempre se puede reabrir.")
    if not campanas:
        st.write("No hay campañas todavía; se crean desde la página de captura "
                 "al dar de alta un folio.")
    for c in campanas:
        col_nombre, col_estado, col_accion = st.columns([3, 1, 1])
        col_nombre.write(c["nombre"])
        col_estado.write("🔓 Abierta" if c["estado"] == "abierta" else "🔒 Cerrada")
        if c["estado"] == "abierta":
            if col_accion.button("Cerrar", key=f"cerrar_{c['id']}"):
                db.cambiar_estado_campana(c["id"], "cerrada")
                st.rerun()
        else:
            if col_accion.button("Reabrir", key=f"reabrir_{c['id']}"):
                db.cambiar_estado_campana(c["id"], "abierta")
                st.rerun()
