# Doble check de preproyectos Layout

App de Streamlit para hacer doble check de calidad a preproyectos
(layouts de arte de empaque/etiqueta) antes de mandarlos a producción.

## Qué hace

- **Checklist de 18 puntos** en dos bloques: parte técnica (con el arte
  abierto) y parte operativa (contra la orden de trabajo), con 4 niveles
  por punto: Cumple / Con ajuste / No cumple / N/A.
- **Versionado por folio** (= número de OT): si algo falla, el resultado
  es "Requiere corrección" y la siguiente revisión precarga lo que ya
  cumplía.
- **Campañas**: cada folio puede pertenecer a una campaña (10-20 folios);
  el dashboard muestra % de folios listos a la primera, retrabajo por
  folio y los puntos que más fallan.
- **Reporte en PDF** con formato para entregar al diseñador.

## Correr en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sin configurar nada usa SQLite local (`checklist_data.db`). Si existe el
secret o variable de entorno `DATABASE_URL`, se conecta a Postgres
(Supabase) — ver [DEPLOY.md](DEPLOY.md) para el despliegue completo en
Streamlit Community Cloud + Supabase.

## Estructura

| Archivo | Qué es |
|---|---|
| `app.py` | Punto de entrada (router de páginas) |
| `captura.py` | Página de captura: el checklist + PDF |
| `dashboard.py` | Página de dashboard por campaña |
| `catalogo.py` | Los 18 puntos del checklist y constantes |
| `db.py` | Persistencia (SQLite local / Postgres en la nube) |
| `DEPLOY.md` | Guía de despliegue paso a paso |
