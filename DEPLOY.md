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

## 4. Acceso del equipo e identidad

Hay dos niveles, de menos a más control:

### Nivel A — Viewers de Streamlit Cloud (el actual)

1. En la configuración de la app (Settings → Sharing): app **privada** y
   agregar los emails del equipo (evaluadores Y diseñadores) como viewers.
2. Dentro de la app, cada quien elige su nombre en el selector "¿Quién
   eres?" — el rol (evaluador/diseñador) se deriva del nombre elegido
   (ver `auth.py`). Community Cloud no le pasa el email del viewer a la
   app, por eso el selector.

### Nivel B — Login de Google restringido por dominio (@buhoms.com / @buho.com)

La app trae soporte para login nativo con Google: se activa solo cuando
existe la sección `[auth]` en los Secrets. Con esto el acceso lo controla
la app (solo correos de los dominios permitidos o listados en `auth.py`),
cada quien queda identificado por su correo real y el rol se asigna solo.

1. En [Google Cloud Console](https://console.cloud.google.com) →
   APIs & Services → Credentials → **Create OAuth client ID** (tipo Web).
   - Authorized redirect URI: `https://buho-checklist.streamlit.app/oauth2callback`
   - (para probar en local agrega también `http://localhost:8501/oauth2callback`)
2. Agrega a los Secrets de la app (además del DATABASE_URL):

   ```toml
   [auth]
   redirect_uri = "https://buho-checklist.streamlit.app/oauth2callback"
   cookie_secret = "UNA-CADENA-ALEATORIA-LARGA"
   client_id = "xxx.apps.googleusercontent.com"
   client_secret = "GOCSPX-..."
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```

3. En Settings → Sharing pon la app **pública** (el login ahora lo hace
   la propia app; si la dejas privada, el equipo tendría doble login).
4. En `auth.py`: registra los correos de evaluadores en `EVALUADORES` y
   los de diseñadores (con su nombre bonito) en `DISENADORES`. Cualquier
   otro correo de los dominios permitidos entra como diseñador; correos
   fuera de dominio quedan bloqueados con mensaje.

## Probar la conexión a Supabase desde local (opcional)

```bash
DATABASE_URL="postgresql://..." streamlit run app.py
```

Si arranca y guarda, la nube está lista.
