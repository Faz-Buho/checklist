# Despliegue: Streamlit Community Cloud + Supabase

La app corre igual en local (SQLite, sin configurar nada) y en la nube
(Postgres en Supabase). El backend se decide solo: si existe el secret
`DATABASE_URL`, usa Postgres; si no, usa `checklist_data.db` local.

## 1. Supabase (base de datos)

1. Crea una cuenta en [supabase.com](https://supabase.com) y un proyecto
   nuevo (plan gratuito). Guarda bien la contraseña de la base.
2. En el panel del proyecto: **Connect** (botón arriba) → pestaña
   **Connection string** → elige **Transaction pooler** (puerto 6543).
   Copia la URI, se ve así:

   ```
   postgresql://postgres.xxxxxxxx:[TU-PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

   Usa el **pooler**, no la conexión directa: Streamlit Cloud abre varias
   conexiones y el tier gratuito limita las directas.
3. No hace falta crear tablas a mano: la app las crea sola al arrancar
   (`db.init_db()`).

**Letras chicas del plan gratuito:**
- El proyecto se **pausa tras ~7 días sin actividad**; se reactiva desde
  el panel de Supabase. Con uso semanal no pasa.
- **No hay respaldos automáticos** (eso es del plan Pro). Exporta de vez
  en cuando desde el panel (Database → Backups → o un dump manual).

## 2. GitHub (código)

1. Crea un repo (puede ser privado) y sube estos archivos:
   `app.py`, `captura.py`, `dashboard.py`, `db.py`, `catalogo.py`,
   `requirements.txt`, `.gitignore`.
2. El `.gitignore` ya excluye la base local y los secrets — verifica que
   `checklist_data.db` y `.streamlit/secrets.toml` NO queden en el repo.

## 3. Streamlit Community Cloud (front)

1. En [share.streamlit.io](https://share.streamlit.io): **New app** →
   elige el repo, branch `main`, main file `app.py`.
2. En **Advanced settings → Secrets**, pega:

   ```toml
   DATABASE_URL = "postgresql://postgres.xxxxxxxx:TU-PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ```

3. Deploy. Cada push a `main` redespliega solo.

## 4. Acceso del equipo e identidad del evaluador

1. En la configuración de la app (Settings → Sharing): pon la app como
   **privada** y agrega los emails del equipo como viewers.
2. Con eso, cada quien entra con su cuenta y la app **firma cada revisión
   con el email del usuario logueado automáticamente** — el selector de
   nombres solo aparece cuando no hay login (uso local).

## Probar la conexión a Supabase desde local (opcional)

```bash
DATABASE_URL="postgresql://..." streamlit run app.py
```

Si arranca y guarda, la nube está lista.
