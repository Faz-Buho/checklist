"""
Página de dashboard: resultados organizados por cliente → campaña →
folio. Se ejecuta vía st.navigation desde app.py.

Métricas clave (calculadas SOLO sobre 2dos checks, la revisión
independiente de calidad; los 1er checks del diseñador no cuentan porque
siempre se guardan "limpios"):
- % de folios listos a la primera (first-pass yield): calidad real del
  proceso, no solo del retrabajo.
- Top de puntos que más fallan: señala problemas de proceso (si un punto
  falla en muchos folios, la causa no es un diseñador).

Estilo visual: iconos Material (:material/...:) y estados con color tipo
badge vía pandas Styler; nada de emojis.
"""

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import db
from auth import ROL_EVALUADOR
from catalogo import (
    ESTADO_CORRECCION,
    ESTADO_LISTO,
    ESTADO_PENDIENTE,
    RESULTADO_LISTO,
    STATUS_REQUIRES_MOTIVO,
    TIPO_PRIMER,
    TIPO_SEGUNDO,
)

es_evaluador = st.session_state["usuario"]["rol"] == ROL_EVALUADOR

COLOR_BARRA = "#2a78d6"  # azul validado para barras de una sola serie
SIN_CLIENTE = "(Sin cliente)"
SIN_CAMPANA = "(Sin campaña)"
TODOS_CLIENTES = "Todos los clientes"
TODAS_CAMPANAS = "Todas las campañas"

# Estado del folio → etiqueta corta + colores (texto, fondo) tipo badge
ESTADO_CORTO = {
    ESTADO_LISTO: "Listo",
    ESTADO_CORRECCION: "En corrección",
    ESTADO_PENDIENTE: "Pendiente",
}
ESTADO_COLOR = {
    "Listo": ("#166534", "#dcfce7"),
    "En corrección": ("#991b1b", "#fee2e2"),
    "Pendiente": ("#854d0e", "#fef9c3"),
}


def _estilo_estado(col):
    return [
        f"background-color: {ESTADO_COLOR[v][1]}; color: {ESTADO_COLOR[v][0]}"
        if v in ESTADO_COLOR else "" for v in col
    ]


st.title(":material/monitoring: Dashboard")

rev_rows = db.get_revisiones_dashboard("todas")
if not rev_rows:
    st.info("Aún no hay revisiones guardadas. Captura folios en la página "
            "**Captura** y aquí aparecerán los resultados.")
    st.stop()

df = pd.DataFrame(rev_rows)
df["cliente"] = df["cliente"].fillna("").replace("", SIN_CLIENTE)
df["campana"] = df["campana"].fillna("").replace("", SIN_CAMPANA)

# --- Nivel folio: estado, nº de 2dos checks y si salió listo a la primera ---
ultimas = df.loc[df.groupby("folio")["revision"].idxmax()].copy()
ultimas["estado"] = [
    ESTADO_PENDIENTE if t == TIPO_PRIMER
    else (ESTADO_LISTO if r == RESULTADO_LISTO else ESTADO_CORRECCION)
    for t, r in zip(ultimas["tipo"], ultimas["resultado"])
]
seg = df[df["tipo"] == TIPO_SEGUNDO]
n_seg = seg.groupby("folio").size()
primer_res = (seg.loc[seg.groupby("folio")["revision"].idxmin()]
              .set_index("folio")["resultado"] if not seg.empty
              else pd.Series(dtype=object))

folios = ultimas[["folio", "cliente", "campana", "estado", "fecha"]].copy()
folios["n_seg"] = folios["folio"].map(n_seg).fillna(0).astype(int)
folios["primer_listo"] = folios["folio"].map(primer_res).map(
    lambda r: 1.0 if r == RESULTADO_LISTO else (0.0 if pd.notna(r) else np.nan))

# --- Filtro jerárquico: primero cliente, luego campaña de ese cliente ---
clientes = sorted(folios["cliente"].unique())
col_cli, col_camp = st.columns(2)
cliente_sel = col_cli.selectbox("Cliente", [TODOS_CLIENTES] + clientes)

if cliente_sel != TODOS_CLIENTES:
    campanas_cli = sorted(folios.loc[folios["cliente"] == cliente_sel, "campana"].unique())
    campana_sel = col_camp.selectbox("Campaña", [TODAS_CAMPANAS] + campanas_cli)
else:
    campana_sel = TODAS_CAMPANAS
    col_camp.selectbox("Campaña", [TODAS_CAMPANAS], disabled=True,
                       help="Elige primero un cliente para filtrar por campaña.")

sel = folios.copy()
if cliente_sel != TODOS_CLIENTES:
    sel = sel[sel["cliente"] == cliente_sel]
if campana_sel != TODAS_CAMPANAS:
    sel = sel[sel["campana"] == campana_sel]

folios_sel = set(sel["folio"])
seg_sel = seg[seg["folio"].isin(folios_sel)]

# --- Métricas de la selección ---
n_folios = len(sel)
n_listos = int((sel["estado"] == ESTADO_LISTO).sum())
n_corr = int((sel["estado"] == ESTADO_CORRECCION).sum())
n_pend = int((sel["estado"] == ESTADO_PENDIENTE).sum())
yield_series = sel["primer_listo"].dropna()
yield_txt = "—" if yield_series.empty else f"{yield_series.mean() * 100:.0f} %"

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Folios", n_folios)
m2.metric("Listos", n_listos)
m3.metric("En corrección", n_corr)
m4.metric("Pendientes", n_pend)
m5.metric("Listos a la primera", yield_txt,
          help="Porcentaje de folios cuyo PRIMER 2do check salió 'Listo para producción'.")

st.divider()


def _resumen(df_folios, by):
    g = df_folios.groupby(by)
    out = pd.DataFrame({
        "Folios": g.size(),
        "Listos": g["estado"].apply(lambda s: int((s == ESTADO_LISTO).sum())),
        "En corrección": g["estado"].apply(lambda s: int((s == ESTADO_CORRECCION).sum())),
        "Pendientes": g["estado"].apply(lambda s: int((s == ESTADO_PENDIENTE).sum())),
        "yield": g["primer_listo"].mean(),
    })
    out["Listos a la primera"] = out["yield"].map(
        lambda x: "—" if pd.isna(x) else f"{x * 100:.0f} %")
    return out.drop(columns=["yield"]).reset_index()


# --- Desglose por cliente (global) o por campaña (dentro de un cliente) ---
if cliente_sel == TODOS_CLIENTES:
    st.subheader(":material/groups: Por cliente")
    res = _resumen(sel, "cliente")
    n_camp = sel.groupby("cliente")["campana"].nunique()
    res.insert(1, "Campañas", res["cliente"].map(n_camp).astype(int))
    res = res.rename(columns={"cliente": "Cliente"}).sort_values("Folios", ascending=False)
    st.dataframe(res, hide_index=True, width="stretch")
    grupo_label, grupo_col = "cliente", "cliente"
else:
    st.subheader(f":material/campaign: Campañas de {cliente_sel}")
    res = _resumen(sel, "campana")
    res = res.rename(columns={"campana": "Campaña"}).sort_values("Folios", ascending=False)
    st.dataframe(res, hide_index=True, width="stretch")
    grupo_label, grupo_col = "campana", "campana"

# Comparativa visual de "a la primera" entre los grupos del desglose
comparables = sel.dropna(subset=["primer_listo"])
if comparables[grupo_col].nunique() > 1:
    comp = (comparables.groupby(grupo_col)
            .agg(folios=("folio", "count"), yield_=("primer_listo", "mean"))
            .reset_index())
    comp["pct"] = comp["yield_"] * 100
    comp["etiqueta"] = comp.apply(lambda r: f"{r['pct']:.0f} % ({int(r['folios'])})", axis=1)
    base = alt.Chart(comp).encode(
        x=alt.X("pct:Q", title="% de folios listos a la primera",
                scale=alt.Scale(domain=[0, 100])),
        y=alt.Y(f"{grupo_col}:N", sort="-x", title=None),
        tooltip=[alt.Tooltip(f"{grupo_col}:N", title=grupo_label.capitalize()),
                 alt.Tooltip("pct:Q", title="A la primera (%)", format=".0f"),
                 alt.Tooltip("folios:Q", title="Folios")],
    )
    barras = base.mark_bar(color=COLOR_BARRA, cornerRadiusEnd=4, height=18)
    etiquetas = base.mark_text(align="left", dx=4).encode(text="etiqueta:N")
    st.altair_chart((barras + etiquetas).properties(height=max(90, 34 * len(comp))),
                    width="stretch")

st.divider()
col_izq, col_der = st.columns([3, 2])

# --- Puntos que más fallan (solo 2dos checks de la selección) ---
with col_izq:
    st.subheader(":material/warning: Puntos que más fallan")
    resp_rows = db.get_respuestas_dashboard("todas")
    df_resp = pd.DataFrame(resp_rows)
    if not df_resp.empty:
        df_resp = df_resp[df_resp["folio"].isin(folios_sel)]
    fallas = (df_resp[df_resp["status"].isin(STATUS_REQUIRES_MOTIVO)]
              if not df_resp.empty else df_resp)
    if fallas.empty:
        st.success("Ninguna falla registrada en esta selección.")
    else:
        item_texto = db.get_item_texto()
        conteo = (fallas.groupby("item_id").size()
                  .sort_values(ascending=False).head(10)
                  .rename("fallas").reset_index())
        conteo["punto"] = conteo["item_id"].map(
            lambda i: item_texto.get(i, i)[:58] + ("…" if len(item_texto.get(i, i)) > 58 else ""))
        base = alt.Chart(conteo).encode(
            x=alt.X("fallas:Q", title="Veces marcado 'Con ajuste' o 'No cumple'",
                    axis=alt.Axis(format="d", tickMinStep=1)),
            y=alt.Y("punto:N", sort="-x", title=None),
            tooltip=[alt.Tooltip("punto:N", title="Punto"),
                     alt.Tooltip("fallas:Q", title="Fallas")],
        )
        barras = base.mark_bar(color=COLOR_BARRA, cornerRadiusEnd=4, height=18)
        etiquetas = base.mark_text(align="left", dx=4).encode(text="fallas:Q")
        st.altair_chart((barras + etiquetas).properties(height=max(120, 30 * len(conteo))),
                        width="stretch")

# --- Estado por folio (con color tipo badge en la columna Estado) ---
with col_der:
    st.subheader(":material/table_rows: Estado por folio")
    tabla = sel[["folio", "cliente", "campana", "n_seg", "estado", "fecha"]].copy()
    tabla["estado"] = tabla["estado"].map(ESTADO_CORTO)
    tabla.columns = ["Folio", "Cliente", "Campaña", "2dos checks", "Estado", "Última revisión"]
    if cliente_sel != TODOS_CLIENTES:
        tabla = tabla.drop(columns=["Cliente"])
    if campana_sel != TODAS_CAMPANAS:
        tabla = tabla.drop(columns=["Campaña"])
    tabla = tabla.sort_values("Última revisión", ascending=False)
    st.dataframe(tabla.style.apply(_estilo_estado, subset=["Estado"]),
                 hide_index=True, width="stretch")

# --- Gestión de campañas (solo evaluadores) ---
if es_evaluador:
    st.divider()
    with st.expander("Gestión de campañas", icon=":material/settings:"):
        st.caption("Cerrar una campaña solo la oculta del selector de captura; "
                   "no bloquea nada y siempre se puede reabrir.")
        campanas = db.get_campanas()
        if not campanas:
            st.write("No hay campañas todavía; se crean desde la página de captura "
                     "al dar de alta un folio.")
        for c in campanas:
            col_nombre, col_estado, col_accion = st.columns([3, 1, 1])
            col_nombre.write(c["nombre"])
            col_estado.write("Abierta" if c["estado"] == "abierta" else "Cerrada")
            if c["estado"] == "abierta":
                if col_accion.button("Cerrar", key=f"cerrar_{c['id']}",
                                     icon=":material/lock:"):
                    db.cambiar_estado_campana(c["id"], "cerrada")
                    db.registrar_evento("Cerrar campaña", st.session_state["usuario"],
                                        detalle=c["nombre"])
                    st.rerun()
            else:
                if col_accion.button("Reabrir", key=f"reabrir_{c['id']}",
                                     icon=":material/lock_open:"):
                    db.cambiar_estado_campana(c["id"], "abierta")
                    db.registrar_evento("Reabrir campaña", st.session_state["usuario"],
                                        detalle=c["nombre"])
                    st.rerun()
