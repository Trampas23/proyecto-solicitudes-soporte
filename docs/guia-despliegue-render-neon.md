# Guía de despliegue: Render + Neon

**Proyecto:** Sistema automatizado de gestión de solicitudes de soporte técnico
**Materia:** Programación en ambiente cliente servidor (segundo parcial)
**Autor:** Nombre del alumno
**Fecha:** Noviembre de 2026
**Versión:** 1.0

---

## Contenido

1. [Antes de empezar](#0-antes-de-empezar)
2. [Fase 1 — Base de datos PostgreSQL en Neon](#fase-1--base-de-datos-postgresql-en-neon)
3. [Fase 2 — Repositorio del proyecto en GitHub](#fase-2--repositorio-del-proyecto-en-github)
4. [Fase 3 — API REST (Flask) en Render](#fase-3--api-rest-flask-en-render)
5. [Fase 4 — Google Cloud y OAuth para n8n](#fase-4--google-cloud-y-oauth-para-n8n)
6. [Fase 5 — Workflow de automatización en n8n](#fase-5--workflow-de-automatización-en-n8n)
7. [Fase 6 — Verificación final y checklist de entrega](#fase-6--verificación-final-y-checklist-de-entrega)
8. [Solución de problemas](#solución-de-problemas)
9. [Apéndices](#apéndices)

---

## 0. Antes de empezar

Esta guía describe, paso a paso y en orden, cómo publicar el sistema completo en servicios en la nube con costo cero para el proyecto escolar:

**Google Forms → Google Sheets → n8n → API Flask en Render → PostgreSQL en Neon**

Al finalizar tendrás cuatro cuentas conectadas entre sí y un flujo automatizado que registra solicitudes de soporte técnico, les asigna un folio, notifica por correo al solicitante y actualiza el dashboard de Google Sheets.

### 0.1 Requisitos previos

| Requisito | Para qué se necesita | Costo | Obligatorio |
|---|---|---|---|
| Cuenta de GitHub | Alojar el repositorio que Render desplegará | Gratis | Sí |
| Cuenta de Neon | PostgreSQL administrado | Plan Free | Sí |
| Cuenta de Render | Hospedar la API REST Flask | Plan Free | Sí |
| Cuenta de Google (Gmail) | Google Forms, Google Sheets y Google Cloud Console | Gratis | Sí |
| Cuenta de n8n Cloud | Orquestar el workflow de automatización | Prueba de 14 días | Sí |
| Git para Windows | Control de versiones y comandos `git` | Gratis | Sí |
| Python 3.12 instalado localmente | Generar la API key y correr las pruebas de humo | Gratis | Recomendado |
| Navegador actualizado (Chrome/Edge/Firefox) | Todas las consolas web | Gratis | Sí |

> **Nota sobre n8n:** la prueba de n8n Cloud dura 14 días con ejecuciones limitadas. Si la necesitas más tiempo, puedes exportar el workflow y ejecutarlo en n8n autoalojado con Docker de forma gratuita. La guía funciona igual en ambos casos.

### 0.2 Estructura del repositorio que se va a desplegar

```text
proyecto-solicitudes/
├── README.md
├── render.yaml                 <- Blueprint de Render (debe estar en la RAÍZ)
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── utilidades.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── .python-version         <- 3.12.6
│   └── test_smoke.py
├── database/
│   ├── schema.sql
│   └── datos_prueba.sql
├── n8n/
│   └── workflow-solicitudes.json
└── docs/
    ├── documentacion-tecnica.md
    ├── guia-despliegue-render-neon.md
    ├── guia-google-forms-sheets.md
    └── pruebas-api.md
```

Dos datos importantes de la estructura:

- `render.yaml` está en la **raíz del repositorio** y usa `rootDir: backend`, por lo que Render instala dependencias y arranca Gunicorn **dentro de `backend/`**.
- La API se compone de tres módulos: `app.py` (endpoints), `database.py` (pool de conexiones y traducción de errores) y `utilidades.py` (validación y normalización).

### 0.3 Variables de entorno de la API

| Variable | ¿Quién la define? | Ejemplo | Obligatoria |
|---|---|---|---|
| `PORT` | La inyecta Render automáticamente (en local es 5000) | `10000` | No la escribas en Render |
| `DATABASE_URL` | Tú, con la cadena de conexión de Neon | `postgresql://...@ep-xxxx-pooler.us-west-2.aws.neon.tech/neondb?sslmode=require` | Sí |
| `API_KEY` | Tú, con un valor aleatorio generado con Python | `hT9_kQ2...` | Sí (si falta, la API queda abierta) |
| `ADMIN_EMAIL` | Tú, opcional; correo del administrador para avisos | `soporte@escuela.mx` | No |
| `FLASK_DEBUG` | Tú, opcional; **debe quedar vacía o `false` en producción** | *(vacía)* | No |
| `CORS_ORIGINS` | Tú, opcional; orígenes permitidos para CORS (por defecto `*`) | `https://mi-dominio.com` | No |

> `backend/.env.example` documenta estas mismas variables para desarrollo local. En Render **no** se sube el archivo `.env`: los valores se capturan en el dashboard del servicio.

### 0.4 Convenciones de esta guía

- Todos los valores que debes reemplazar aparecen entre ángulos: `<API_KEY>`, `<TU_USUARIO>`, `<SPREADSHEET_ID>`.
- Los comandos de consola se muestran para **Windows PowerShell 7** (`pwsh`). Cuando se indique **Git Bash**, pega el bloque en esa terminal. Git Bash se instala junto con Git para Windows.
- Los bloques de comandos se ejecutan **en la carpeta del proyecto** salvo que se indique otra cosa.
- Cada fase termina con una sección **Verificación** con casillas. No avances a la siguiente fase hasta completarlas.
- Las capturas y versiones de las consolas pueden variar: los nombres de los botones son los que se indican, aunque Google, Render o Neon cambien el diseño.

### 0.5 Tabla de URLs finales (llénala durante la guía)

| Recurso | URL / valor | Se obtiene en |
|---|---|---|
| Repositorio GitHub | `https://github.com/<TU_USUARIO>/proyecto-solicitudes` | Fase 2 |
| API en Render | `https://api-solicitudes-soporte.onrender.com` | Fase 3 |
| Base de datos (host pooled) | `ep-xxxx-pooler.us-west-2.aws.neon.tech` | Fase 1 |
| Workflow n8n | `https://<SUBDOMINIO>.app.n8n.cloud` | Fase 4 |
| Formulario Google | `https://forms.gle/...` | Guía de Google Forms |
| Hoja de cálculo | ID: `<SPREADSHEET_ID>` | Guía de Google Forms |
| Correo administrador | `<CORREO_ADMIN>` | Definido por el equipo |

### 0.6 Orden recomendado de despliegue

```mermaid
flowchart LR
    A[Fase 1<br/>Neon: base de datos] --> B[Fase 2<br/>GitHub: repositorio]
    B --> C[Fase 3<br/>Render: API Flask]
    C --> D[Fase 4<br/>Google Cloud: OAuth]
    D --> E[Fase 5<br/>n8n: workflow activo]
    E --> F[Fase 6<br/>Verificación end-to-end]
```

El orden importa: la API necesita la base de datos antes de arrancar, Render necesita el código en GitHub y n8n necesita la URL de Render y las credenciales de Google ya creadas.

---

## Fase 1 — Base de datos PostgreSQL en Neon

**Objetivo:** crear el proyecto PostgreSQL en Neon, ejecutar el esquema y verificar que la tabla, los triggers, los índices y las vistas quedaron bien creados.

**Tiempo estimado:** 15 a 20 minutos.

### 1.1 Crear la cuenta de Neon

1. Abre <https://neon.tech> y haz clic en **Sign Up** (o en **Get Started**).
2. Elige **Continue with GitHub** (recomendado, porque después usarás GitHub) o regístrate con tu correo.
3. Confirma el correo si Neon te envía un mensaje de verificación.
4. Al entrar por primera vez, Neon muestra el asistente **Create your first project**. Si no aparece, haz clic en **New Project** en la esquina superior derecha de la consola.

### 1.2 Crear el proyecto

1. En **Project name** escribe: `proyecto-solicitudes`.
2. En **Postgres version** deja la versión por defecto (17 o la más reciente disponible).
3. En **Region** selecciona **AWS US West 2 (Oregon)**. Es la misma región que usa Render en `render.yaml` (`region: oregon`); mantenerlas iguales reduce la latencia entre la API y la base de datos.
4. En **Database name** deja `neondb` y en **Role name** deja `neondb_owner` (valores por defecto).
5. Haz clic en **Create project**.
6. Espera de 10 a 30 segundos. Al terminar, Neon muestra el panel del proyecto y un cuadro con la **connection string**.

> **Buenas prácticas:** anota el nombre del proyecto, la región y el rol. Neon crea una rama (`branch`) llamada `main` y una base de datos llamada `neondb`; los nombres de host tienen una parte aleatoria que no debes modificar a mano.

### 1.3 Copiar la cadena de conexión (pooled y direct)

El proyecto usa **dos** cadenas de conexión distintas, según el uso:

| Tipo | Host | ¿Para qué se usa? | ¿Dónde se configura? |
|---|---|---|---|
| **Pooled** (pool de conexiones) | contiene `-pooler`, por ejemplo `ep-xxxx-pooler.us-west-2.aws.neon.tech` | API en producción: el pool de `psycopg2` abre conexiones cortas que conviene agrupar | Variable `DATABASE_URL` en Render |
| **Direct** (conexión directa) | sin `-pooler`, por ejemplo `ep-xxxx.us-west-2.aws.neon.tech` | Ejecutar el esquema (`schema.sql`), migraciones y `psql` | SQL Editor de Neon / terminal local |

1. En el panel del proyecto haz clic en **Connect** (esquina superior derecha).
2. En el cuadro **Connect to your database**:
   - En **Branch** selecciona `main`.
   - En **Database** selecciona `neondb`.
   - En **Role** selecciona `neondb_owner`.
   - Activa la casilla **Connection pooling** para obtener la cadena *pooled*. Desactívala para la cadena *direct*.
   - En **SSL mode** deja **require**.
3. Haz clic en **Copy** (icono de copiar) y pega la cadena en un archivo temporal privado.
4. Repite el proceso desactivando **Connection pooling** y copia la cadena *direct*.

Las cadenas deben verse así (los valores son ejemplos):

```text
# Pooled (para DATABASE_URL en Render)
postgresql://neondb_owner:AbC123dEf@ep-cool-darkness-123456-pooler.us-west-2.aws.neon.tech/neondb?sslmode=require

# Direct (para ejecutar schema.sql con psql o desde el SQL Editor)
postgresql://neondb_owner:AbC123dEf@ep-cool-darkness-123456.us-west-2.aws.neon.tech/neondb?sslmode=require
```

> **Regla importante:** usa la cadena que termine en `?sslmode=require` (o `?sslmode=verify-full`). Neon rechaza conexiones sin SSL/TLS. La API además agrega `sslmode=require` automáticamente si la cadena no lo incluye, y convierte `postgres://` a `postgresql://`; aun así, es mejor copiarla completa desde Neon para evitar dudas.

> **Si tu contraseña tiene caracteres especiales** (`@`, `#`, `/`, `:`), Neon los codifica automáticamente en la connection string que copias. No edites la cadena carácter por carácter.

### 1.4 Ejecutar `database/schema.sql` en el SQL Editor de Neon

1. Abre el archivo `database/schema.sql` del repositorio en tu editor (VS Code, Notepad++, etc.).
2. Selecciona **todo** el contenido (`Ctrl + A`) y cópialo (`Ctrl + C`). El archivo incluye, en orden: la secuencia del folio, la tabla `solicitudes`, la función `asignar_folio()` con su trigger, la función `actualizar_fecha_actualizacion()` con su trigger, los índices y las tres vistas de estadísticas.
3. En la consola de Neon, en el menú lateral izquierdo, haz clic en **SQL Editor**.
4. Haz clic en **New Query** (o en el botón **+**).
5. Pega el contenido en el editor (`Ctrl + V`).
6. Haz clic en **Run** (o presiona `Ctrl + Enter`).
7. Verifica que el panel inferior muestre el mensaje **Query executed successfully**; al final del script aparece `SELECT COUNT(*) AS solicitudes_registradas FROM solicitudes;` con resultado `0`. Si aparece un error en rojo, no continúes: revisa la sección [Solución de problemas](#solución-de-problemas) y corrige antes de repetir.

> **El script es idempotente:** usa `CREATE ... IF NOT EXISTS`, `CREATE OR REPLACE` y `DROP TRIGGER IF EXISTS`, así que puedes volver a ejecutarlo sin perder datos ni duplicar objetos. Al principio del archivo hay un bloque comentado (**RESET OPCIONAL**) que borra todo si algún día necesitas empezar de cero: descoméntalo solo en ese caso.

> **Alternativa por terminal (opcional):** si tienes `psql` instalado, usa la cadena **direct** (no la pooled) para ejecutar el archivo completo:
>
> ```powershell
> psql "postgresql://neondb_owner:AbC123dEf@ep-cool-darkness-123456.us-west-2.aws.neon.tech/neondb?sslmode=require" -f database/schema.sql
> ```
>
> Para instalar `psql` en Windows: `winget install PostgreSQL.PostgreSQL.17`. Anota la contraseña del usuario `postgres` que pida el instalador (es local, no se usa para Neon).

### 1.5 Verificar el esquema (equivalente a `\d solicitudes` de psql)

El SQL Editor de Neon no interpreta los meta-comandos de `psql` (`\d`, `\dt`), pero puedes obtener exactamente la misma información con estas consultas. Ejecuta cada una en una pestaña nueva del SQL Editor y revisa el resultado:

**1) Tablas y vistas creadas:**

```sql
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_type, table_name;
```

Resultado esperado: `solicitudes` (BASE TABLE), `v_estadisticas_por_categoria`, `v_estadisticas_por_prioridad` y `v_estadisticas_por_estado` (las tres VIEW).

**2) Columnas, tipos y valores por defecto de `solicitudes` (equivalente a `\d solicitudes`):**

```sql
SELECT column_name,
       data_type,
       character_maximum_length AS longitud,
       is_nullable,
       column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'solicitudes'
ORDER BY ordinal_position;
```

Resultado esperado: las **15 columnas** `id`, `folio`, `nombre`, `correo`, `telefono`, `area`, `categoria`, `prioridad`, `descripcion`, `estado`, `notas`, `id_externo`, `correo_enviado`, `fecha_registro` y `fecha_actualizacion`, con los tipos indicados en `docs/documentacion-tecnica.md`.

**3) Restricciones CHECK, llave primaria y UNIQUE:**

```sql
SELECT conname AS restriccion,
       contype AS tipo,
       pg_get_constraintdef(oid) AS definicion
FROM pg_constraint
WHERE conrelid = 'solicitudes'::regclass
ORDER BY tipo, conname;
```

Resultado esperado: `solicitudes_pkey` (llave primaria), `solicitudes_folio_key` y `solicitudes_id_externo_key` (UNIQUE), y las restricciones `chk_categoria`, `chk_prioridad`, `chk_estado`, `chk_correo`, `chk_nombre` y `chk_descripcion` (CHECK).

**4) Triggers (folio automático y fecha de actualización):**

```sql
SELECT tgname AS trigger,
       pg_get_triggerdef(oid) AS definicion
FROM pg_trigger
WHERE tgrelid = 'solicitudes'::regclass
  AND NOT tgisinternal;
```

Resultado esperado: `trg_asignar_folio` (BEFORE INSERT, genera el folio) y `trg_actualizar_fecha` (BEFORE UPDATE, actualiza `fecha_actualizacion`).

**5) Índices:**

```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'public' AND tablename = 'solicitudes'
ORDER BY indexname;
```

Resultado esperado: los índices de la llave primaria y los cuatro índices `idx_solicitudes_categoria`, `idx_solicitudes_prioridad`, `idx_solicitudes_estado` e `idx_solicitudes_fecha_registro`.

**6) Secuencia del folio:**

```sql
SELECT sequence_name, start_value, increment
FROM information_schema.sequences
WHERE sequence_schema = 'public';
```

Resultado esperado: `solicitudes_folio_seq`, con `start_value = 1` e `increment = 1`.

**7) Todas las filas (tabla vacía al inicio):**

```sql
SELECT * FROM solicitudes;
```

Resultado esperado: cero filas, sin error. La consulta funciona aunque la tabla esté vacía.

### 1.6 Insertar un registro de prueba y comprobar folio y triggers

Ejecuta en el SQL Editor:

```sql
INSERT INTO solicitudes (nombre, correo, telefono, area, categoria, prioridad, descripcion)
VALUES ('Ana Pérez', 'ana.perez@ejemplo.com', '5551234567', 'Soporte técnico',
        'Hardware', 'Media', 'La computadora no enciende desde ayer.')
RETURNING id, folio, estado, correo_enviado, fecha_registro, fecha_actualizacion;
```

Resultado esperado:

- `id` = `1` (si es la primera fila).
- `folio` con formato `SOL-AAAA-NNNN`, por ejemplo `SOL-2026-0001`. El año corresponde a `fecha_registro` y el consecutivo lo asigna la secuencia; **no escribas el folio a mano**.
- `estado` = `Pendiente`.
- `correo_enviado` = `false`.
- `fecha_registro` con la fecha y hora actuales y `fecha_actualizacion` en `NULL` (el trigger solo actualiza esa columna en los `UPDATE`).

Comprueba el trigger de actualización (cambia `SOL-2026-0001` por el folio que te haya salido):

```sql
UPDATE solicitudes
SET estado = 'En proceso'
WHERE folio = 'SOL-2026-0001'
RETURNING folio, estado, fecha_registro, fecha_actualizacion;
```

Resultado esperado: `estado` = `En proceso` y `fecha_actualizacion` **mayor** que `fecha_registro`.

Comprueba las vistas de estadísticas:

```sql
SELECT * FROM v_estadisticas_por_categoria;
SELECT * FROM v_estadisticas_por_prioridad;
SELECT * FROM v_estadisticas_por_estado;
```

Resultado esperado: una fila con `Hardware` y el conteo correspondiente.

**Limpieza del registro de prueba** (recomendado antes de conectar el formulario real):

```sql
DELETE FROM solicitudes WHERE correo = 'ana.perez@ejemplo.com';
SELECT COUNT(*) FROM solicitudes;
```

> La secuencia del folio **no se reinicia** al borrar registros: es un consecutivo global y es correcto que el siguiente folio continúe. Si necesitas reiniciarla en un entorno de pruebas totalmente vacío: `ALTER SEQUENCE solicitudes_folio_seq RESTART WITH 1;`.

**Datos de demostración (opcional, recomendado para el dashboard):** el repositorio incluye `database/datos_prueba.sql` con 10 solicitudes de ejemplo. Después de ejecutar `schema.sql`, pega también este archivo en el SQL Editor y presiona **Run**; es idempotente gracias a `ON CONFLICT (id_externo) DO NOTHING`. Al final muestra las 10 filas con su folio. Con estos datos el dashboard de Google Sheets ya tiene qué graficar.

### Verificación de la fase 1

- [ ] El proyecto `proyecto-solicitudes` existe en Neon y está en la región **AWS US West 2 (Oregon)**.
- [ ] Copiaste y guardaste las cadenas **pooled** y **direct** completas, con `sslmode=require`.
- [ ] `database/schema.sql` se ejecutó sin errores en el **SQL Editor** y la verificación final mostró `0` solicitudes.
- [ ] La consulta `SELECT * FROM solicitudes;` responde sin error.
- [ ] La tabla `solicitudes` tiene las 15 columnas esperadas.
- [ ] Los triggers `trg_asignar_folio` y `trg_actualizar_fecha`, la secuencia `solicitudes_folio_seq` y los cuatro índices aparecen en las consultas de verificación.
- [ ] Las tres vistas `v_estadisticas_por_categoria`, `v_estadisticas_por_prioridad` y `v_estadisticas_por_estado` existen.
- [ ] Insertaste un registro con `INSERT ... RETURNING`, obtuviste un folio `SOL-AAAA-NNNN` y el `UPDATE` cambió `fecha_actualizacion`.
- [ ] Borraste el registro de prueba (opcional) y, si aplica, ejecutaste `database/datos_prueba.sql`.

---

## Fase 2 — Repositorio del proyecto en GitHub

**Objetivo:** inicializar Git en la carpeta del proyecto, subir el código (sin secretos) a GitHub y dejar el repositorio listo para que Render lo despliegue.

**Tiempo estimado:** 10 a 15 minutos.

### 2.1 Revisar el archivo `.gitignore`

El repositorio ya incluye un archivo `.gitignore` en la raíz que excluye `__pycache__/`, `.venv/`, `.deps/`, `.env`, archivos de editores y resultados de pruebas. Ábrelo y confirma que contiene al menos estas líneas:

```gitignore
# Variables de entorno (NUNCA subir credenciales al repositorio)
.env
.env.local

# Entorno de Python
__pycache__/
*.py[cod]
.venv/
venv/
env/
.deps/
```

> El archivo `.env.example` **sí** se versiona: solo contiene nombres de variables y valores de ejemplo, nunca llaves reales. La llave `API_KEY` y la cadena `DATABASE_URL` reales se guardan en `.env` local y en las variables de entorno de Render.
>
> Si en tu copia local creaste una carpeta de dependencias como `.deps/` (por ejemplo, al instalar con `pip install --target .deps`), verifica que esté ignorada antes de hacer `git add`.

### 2.2 Inicializar Git y hacer el primer commit

Abre **PowerShell** y ejecuta, una línea a la vez:

```powershell
# Ubícate en la carpeta del proyecto (ajusta la ruta a la tuya)
Set-Location "C:\Users\<TU_USUARIO>\Documents\proyecto-solicitudes"

# Comprueba que Git está instalado
git --version

# Inicializa el repositorio con la rama principal "main"
git init -b main

# Configura tu identidad global (solo la primera vez en la computadora)
git config --global user.name "Nombre Apellido"
git config --global user.email "tu.correo@ejemplo.com"

# Revisa qué archivos se van a subir (no debe aparecer .env ni .deps/)
git status --short
```

Cuando `git status --short` se vea correcto, crea el primer commit:

```powershell
git add .
git commit -m "Versión inicial: API Flask, esquema SQL y workflow n8n"
```

Resultado esperado: un mensaje similar a `[main (root-commit) 1a2b3c4] Versión inicial...` con el número de archivos del proyecto.

### 2.3 Crear el repositorio en GitHub

1. Entra a <https://github.com> e inicia sesión.
2. Haz clic en **+** (arriba a la derecha) → **New repository**.
3. En **Repository name** escribe: `proyecto-solicitudes`.
4. En **Description** escribe: `Sistema automatizado de gestión de solicitudes de soporte técnico (Flask + Neon + Render + n8n)`.
5. Selecciona **Private** (recomendado; el profesor puede recibir acceso) o **Public** si el profesor lo pide así.
6. **No** marques **Add a README file**, **Add .gitignore** ni **Choose a license**: el repositorio debe quedar vacío para poder subir tu commit local.
7. Haz clic en **Create repository**.
8. Copia la URL del repositorio, por ejemplo: `https://github.com/<TU_USUARIO>/proyecto-solicitudes.git`.

### 2.4 Conectar el repositorio local y hacer push

De vuelta en PowerShell, dentro de la carpeta del proyecto:

```powershell
git remote add origin https://github.com/<TU_USUARIO>/proyecto-solicitudes.git
git remote -v
git branch -M main
git push -u origin main
```

- Si `git remote add` marca **error: remote origin already exists**, usa: `git remote set-url origin https://github.com/<TU_USUARIO>/proyecto-solicitudes.git`.
- La primera vez, Git abre una ventana del navegador para autenticarte con **GitHub** (o te pide usuario y contraseña). **La contraseña de GitHub ya no funciona:** si te la pide, usa un **token de acceso personal (PAT)**:
  1. GitHub → foto de perfil → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
  2. Nombre: `render-proyecto`, expiración: 90 días, alcance: marca **repo**.
  3. **Generate token** y copia el token (empieza con `ghp_`). Úsalo como contraseña cuando Git lo pida.
- Resultado esperado: `Branch 'main' set up to track remote branch 'main' from 'origin'.`

### 2.5 Verificar lo subido

```powershell
git log --oneline -3
git status
git remote -v
```

Resultado esperado: el commit aparece en el historial, `git status` dice `nothing to commit, working tree clean` y `origin` apunta a tu repositorio.

Además, en la página del repositorio en GitHub (recarga con `F5`):

- [ ] Se ven `README.md`, `render.yaml`, las carpetas `backend/`, `database/`, `n8n/` y `docs/`.
- [ ] Se ve `backend/.env.example`.
- [ ] **No** se ven `backend/.env` ni `.deps/` (si aparece `.env`, detente y elimínalo del historial antes de continuar).

Comprobación de secretos desde la terminal:

```powershell
git ls-files | Select-String -Pattern "\.env"
```

Resultado esperado: solo aparece `backend/.env.example`.

### 2.6 Flujo para actualizaciones posteriores

Cada vez que modifiques el código:

```powershell
git add .
git commit -m "Descripción breve del cambio"
git push
```

Render detectará el push y volverá a desplegar automáticamente (en `render.yaml` está `autoDeploy: true`).

### Verificación de la fase 2

- [ ] `.gitignore` versionado; `.env` y `.deps/` fuera del repositorio.
- [ ] Repositorio local inicializado en la rama `main` con el primer commit.
- [ ] Repositorio remoto creado en GitHub **sin** README ni `.gitignore` iniciales.
- [ ] `git push -u origin main` terminó sin errores y `git remote -v` apunta a GitHub.
- [ ] La página de GitHub muestra el código (incluido `render.yaml` en la raíz) y **no** muestra secretos.
- [ ] Guardaste la URL del repositorio para la fase 3.

---

## Fase 3 — API REST (Flask) en Render

**Objetivo:** desplegar la API con Gunicorn, conectarla a Neon y dejarla accesible por HTTPS con su API key. Render ejecutará el servicio con la configuración que ya está declarada en `render.yaml`.

**Tiempo estimado:** 20 a 30 minutos (el primer despliegue tarda de 2 a 5 minutos).

### 3.1 Crear la cuenta de Render

1. Abre <https://dashboard.render.com/register>.
2. Haz clic en **GitHub** y autoriza a Render para acceder a tus repositorios.
3. Confirma el correo y entra al panel (dashboard).
4. Si Render pregunta por el tipo de cuenta, elige el plan **Free** / **Hobby**.

> Render ofrece el plan **Free** para servicios web. No necesitas tarjeta para empezar. Si en el futuro te pide método de pago, es para planes de pago; el plan Free no lo requiere.

### 3.2 Generar la API key

Antes de crear el servicio, genera la llave secreta que protegerá los endpoints de escritura. En PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Resultado esperado: una cadena aleatoria de unos 43 caracteres, por ejemplo `sH7v2QpR9wXkLm3nT8cYbJ5fD1gA0eZu6iK4oN2rM8s`. **Cópiala y guárdala**; será el valor de `API_KEY` en Render y en n8n.

> Esta misma llave la usarás en la fase 5, en el header `X-API-Key` del nodo HTTP Request de n8n. Si se te pierde, genera otra y actualiza Render y n8n.

> **Importante:** si dejas `API_KEY` vacía en Render, la API **no** exige llave (es útil solo para desarrollo local). En producción debes configurarla para que `POST` y `PATCH` respondan `401` sin header. Los endpoints `GET` son públicos por diseño (ver `docs/documentacion-tecnica.md`, sección de seguridad).

### 3.3 Opción A (recomendada): desplegar con el Blueprint `render.yaml`

El repositorio ya trae `render.yaml` en la raíz, con el servicio declarado y probado. Render lo detecta y crea todo automáticamente.

1. En el panel de Render haz clic en **New +** (arriba a la derecha) → **Blueprint**.
2. En **Git Provider** elige **GitHub** (si es la primera vez, autoriza el acceso). Busca y selecciona el repositorio `proyecto-solicitudes` y haz clic en **Connect**.
3. Render lee `render.yaml` y muestra una vista previa con el servicio declarado:
   - **Nombre:** `api-solicitudes-soporte` (determina la URL pública).
   - **Runtime:** Python 3, **Región:** Oregon, **Plan:** Free.
   - **Root Directory:** `backend`.
   - **Build Command:** `pip install -r requirements.txt`.
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`.
   - **Health Check Path:** `/health`, **Auto-Deploy:** activado.
4. Render te pide capturar las variables marcadas con `sync: false` (no se versionan en el repositorio). Captura:

| Key | Value |
|---|---|
| `DATABASE_URL` | La cadena **pooled** de Neon copiada en la fase 1, completa y con `?sslmode=require` |
| `API_KEY` | La llave generada en el paso 3.2 |
| `ADMIN_EMAIL` | *(opcional)* Correo del administrador, por ejemplo `soporte@escuela.mx` |

5. Escribe un nombre para el **Blueprint** (por ejemplo `proyecto-solicitudes`) y haz clic en **Apply**.
6. Render crea el servicio y comienza el despliegue. Salta a la sección [3.5 Sigue el primer despliegue](#35-sigue-el-primer-despliegue).

> La variable `PYTHON_VERSION=3.12.6` ya viene declarada en `render.yaml`; no tienes que capturarla. El repositorio también incluye `backend/.python-version` con el mismo valor.

### 3.4 Opción B: crear el Web Service manualmente

Si prefieres capturar todo a mano (útil para entender cada campo):

1. En el panel de Render haz clic en **New +** → **Web Service**.
2. Conecta el repositorio `proyecto-solicitudes`.
3. Llena el formulario con estos valores exactos:

| Campo | Valor |
|---|---|
| **Name** | `api-solicitudes-soporte` |
| **Language / Runtime** | `Python 3` |
| **Region** | `Oregon (US West)` |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60` |
| **Instance Type** | `Free` |

4. En **Advanced** (o en la sección equivalente) configura:
   - **Health Check Path:** `/health`
   - **Auto-Deploy:** `Yes`
5. En **Environment Variables** agrega, una por una (botón **Add Environment Variable**):

| Key | Value |
|---|---|
| `DATABASE_URL` | La cadena **pooled** de Neon, completa y con `?sslmode=require` |
| `API_KEY` | La llave generada en el paso 3.2 |
| `ADMIN_EMAIL` | *(opcional)* Correo del administrador |
| `PYTHON_VERSION` | `3.12.6` (recomendado: Render puede usar por defecto una versión más nueva sin ruedas de `psycopg2-binary`) |

> **No agregues `PORT`**: Render la inyecta automáticamente y el comando de arranque ya la usa. Si la agregas con un valor fijo, el servicio puede fallar.

6. Haz clic en **Create Web Service** (o **Deploy Web Service**).

### 3.5 Sigue el primer despliegue

1. Render te lleva a la página del servicio y a la pestaña **Logs**.
2. Espera de 2 a 5 minutos. Las líneas clave del log son:

```text
==> Installing dependencies from requirements.txt
==> Successfully installed Flask-3.1.0 flask-cors-5.0.0 gunicorn-23.0.0 psycopg2-binary-2.9.10 python-dotenv-1.0.1
==> Running 'gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60'
[INFO] Starting gunicorn
[INFO] Listening at: http://0.0.0.0:10000
[INFO] Booting worker with pid: ...
[INFO] Booting worker with pid: ...
```

3. Cuando el estado del servicio cambie a **Live** (punto verde), la URL pública aparece en la parte superior, con la forma `https://api-solicitudes-soporte.onrender.com`. **Cópiala**: será `API_URL` en lo que resta de la guía.

> Render puede agregar un sufijo aleatorio si el nombre ya está ocupado (por ejemplo `api-solicitudes-soporte-x7k2.onrender.com`). Usa la URL exacta que muestre el panel.

### 3.6 Verificar `/health` y los endpoints con curl

Abre **Git Bash** (recomendado para que los comandos coincidan con esta guía) y define las variables de tu sesión:

```bash
export API_URL="https://api-solicitudes-soporte.onrender.com"
export API_KEY="<TU_API_KEY>"
```

**1) Health check (sin llave):**

```bash
curl -i "$API_URL/health"
```

Resultado esperado: `HTTP/1.1 200 OK` (o `HTTP/2 200`) y un cuerpo JSON como este:

```json
{
  "ok": true,
  "servicio": "Sistema automatizado de gestión de solicitudes de soporte técnico",
  "version": "1.0.0",
  "base_datos": "conectada",
  "mensaje": "Servicio operando correctamente.",
  "hora": "2026-11-10T22:33:34-06:00"
}
```

> **Diseño importante:** `/health` **siempre responde HTTP 200**, incluso si la base de datos está caída; en ese caso el cuerpo dice `"base_datos": "desconectada"` y explica el problema. Así Render sabe que el proceso está vivo y no lo reinicia, mientras tú diagnosticas la base. Por eso: **no interpretes un 200 de `/health` como prueba de que la BD funciona**; revisa el campo `base_datos`.

**2) Endpoint raíz (sin llave):**

```bash
curl -s "$API_URL/"
```

Resultado esperado: JSON con `ok`, `servicio`, `version`, la lista de `endpoints` y `valores_validos` (categorías, prioridades y estados).

**3) POST de prueba (crea una solicitud real; requiere llave):**

```bash
curl -i -X POST "$API_URL/api/solicitudes" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "telefono": "5551234567",
    "area": "Recursos Humanos",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
    "id_externo": "despliegue-001"
  }'
```

Resultado esperado: `HTTP/1.1 201 Created` y un JSON con el folio generado:

```json
{
  "ok": true,
  "mensaje": "Solicitud registrada correctamente.",
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
    "estado": "Pendiente",
    "notas": null,
    "id_externo": "despliegue-001",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": null
  }
}
```

> Los valores concretos de `id` y del consecutivo del folio dependen de cuántas filas se hayan insertado antes (prueba de la fase 1 o datos de demostración). Lo importante es que el folio tenga el formato `SOL-AAAA-NNNN` y que `estado` sea `Pendiente`.

**4) Idempotencia (reintentos de n8n):** repite exactamente la misma petición con el mismo `id_externo`. Resultado esperado: `HTTP/1.1 200 OK`, `"duplicado": true` y **el mismo folio**, sin crear otra fila (el ejemplo muestra el `data` resumido; la API devuelve el objeto completo):

```json
{
  "ok": true,
  "duplicado": true,
  "mensaje": "La solicitud ya estaba registrada previamente; se devuelve el registro existente.",
  "data": { "id": 1, "folio": "SOL-2026-0001", "estado": "Pendiente" }
}
```

**5) Listado de solicitudes (público, sin llave):**

```bash
curl -s "$API_URL/api/solicitudes?limit=10" -H "X-API-Key: $API_KEY"
```

El header es opcional en `GET`; se puede omitir. Resultado esperado: `200` con `total`, `limit`, `offset`, `cantidad` y el arreglo `data`.

**6) Consultar una solicitud por folio o por id (público):**

```bash
curl -s "$API_URL/api/solicitudes/SOL-2026-0001"
curl -s "$API_URL/api/solicitudes/1"
```

Resultado esperado: `200` con `{"ok": true, "data": {...}}`; `404` si no existe.

**7) Actualizar el estado (requiere llave):**

```bash
curl -i -X PATCH "$API_URL/api/solicitudes/SOL-2026-0001/estado" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"estado": "En proceso", "notas": "Asignado al área de sistemas."}'
```

Resultado esperado: `200 OK` con `"mensaje": "Estado actualizado a 'En proceso'."` y `data.estado = "En proceso"`. El PATCH acepta folio o id numérico y normaliza alias como `en proceso`, `cerrada` o `finalizado`.

**8) Estadísticas del dashboard (público):**

```bash
curl -s "$API_URL/api/estadisticas"
```

Resultado esperado: `200` con `data.total`, `data.por_categoria`, `data.por_prioridad`, `data.por_estado`, `data.ultimas_24_horas` y `data.generado_en`.

**9) Comprobar que la llave realmente protege:**

```bash
curl -i -X POST "$API_URL/api/solicitudes" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Prueba", "correo": "prueba@ejemplo.com", "categoria": "Otro", "prioridad": "Baja", "descripcion": "Prueba sin llave"}'
```

Resultado esperado: `HTTP/1.1 401 Unauthorized` con:

```json
{
  "ok": false,
  "error": "No autorizado.",
  "mensaje": "Incluye el header 'X-API-Key' con la clave correcta. El workflow de n8n la envía automáticamente."
}
```

> **Si sin llave responde `201`**, no es un error del código: la variable `API_KEY` no está configurada en Render. Configúrala en **Environment** y espera el redespliegue.

**10) Validación de datos (400):**

```bash
curl -i -X POST "$API_URL/api/solicitudes" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"nombre":"A","correo":"malo","categoria":"Física","prioridad":"Altísima","descripcion":"corta"}'
```

Resultado esperado: `400` con `{"ok": false, "error": "La solicitud contiene datos inválidos.", "errores": { ... }}`, un mensaje por cada campo inválido.

> **Equivalentes en PowerShell:** usa `curl.exe` en lugar de `curl` (en PowerShell `curl` es un alias de `Invoke-WebRequest`) o revisa los ejemplos equivalentes en `docs/pruebas-api.md`. Ejemplo: `curl.exe -i "$env:API_URL/health"`.

### 3.7 Pruebas automatizadas de la API (sin Neon)

El proyecto incluye 34 pruebas de humo que no requieren base de datos. Ejecútalas en local para validar el código antes de culpar a Render o a Neon:

```powershell
Set-Location "C:\Users\<TU_USUARIO>\Documents\proyecto-solicitudes\backend"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python test_smoke.py -v
```

Resultado esperado: `Ran 34 tests in ...` y `OK`. Cubren validación, normalización de categorías/prioridades/estados, códigos HTTP, autenticación por API key, idempotencia (`id_externo`), respuestas `503` por base caída y serialización de fechas ISO 8601. En Git Bash basta con `cd backend && python test_smoke.py -v` después de activar el entorno.

### 3.8 Notas del plan Free de Render

| Característica | Comportamiento en el plan Free | Implicación práctica |
|---|---|---|
| **Suspensión por inactividad** | El servicio se **duerme** tras unos **15 minutos** sin tráfico | La primera petición después de dormir tarda más |
| **Cold start** | El primer request puede tardar **50 segundos o más** (a veces 1 minuto) | En n8n, sube el timeout del nodo HTTP a 90 s; no lo interpretes como caída |
| **Horas de instancia** | **750 horas/mes** por workspace | Alcanza para un servicio encendido 24/7; con varias personas, vigila el consumo |
| **Recursos** | 512 MB de RAM, 0.1 CPU | Suficiente para este proyecto escolar; el servicio arranca con 2 workers de Gunicorn |
| **Ancho de banda** | 100 GB/mes de salida | Más que suficiente |
| **Disco persistente** | No incluido | No se necesita: la información vive en Neon |
| **SSL/HTTPS** | Incluido y automático en `*.onrender.com` | La API siempre responde por HTTPS |

> **Si no quieres que se duerma durante la demostración:** puedes "despertarla" 2 minutos antes abriendo `https://<tu-servicio>.onrender.com/health` en el navegador. También existen servicios gratuitos de monitoreo (UptimeRobot, cron-job.org) que hacen ping cada 10–14 minutos; ten en cuenta que esto consume horas de instancia y que el plan Free está pensado para dormir. Para la entrega escolar, lo normal es aceptar el cold start y avisar al profesor.

> **Cold start en Neon:** la base también suspende el cómputo por inactividad y la primera consulta tras un rato puede tardar 1–2 segundos adicionales. Es normal y no requiere configuración.

### 3.9 Actualizaciones automáticas

Cada `git push` a la rama `main` dispara un nuevo despliegue porque `autoDeploy: true`. Para desplegar sin cambiar código: página del servicio → botón **Manual Deploy** → **Deploy latest commit**. Para revertir: **Rollback** en el menú del deploy anterior.

### Verificación de la fase 3

- [ ] Servicio `api-solicitudes-soporte` creado (Blueprint o manual) con **Root Directory** = `backend`, runtime Python 3 y plan Free.
- [ ] Build Command `pip install -r requirements.txt` y Start Command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60` configurados.
- [ ] Variables `DATABASE_URL` (pooled, con `sslmode=require`) y `API_KEY` cargadas; `PORT` **no** agregada manualmente.
- [ ] Health Check Path = `/health` y el servicio está en estado **Live**.
- [ ] `curl -i "$API_URL/health"` responde `200` con `"base_datos": "conectada"`.
- [ ] `POST /api/solicitudes` con `X-API-Key` responde `201` y devuelve folio; repetir con el mismo `id_externo` responde `200` con `"duplicado": true`.
- [ ] `POST /api/solicitudes` sin llave responde `401`.
- [ ] `PATCH .../estado` responde `200` y la solicitud se ve actualizada en Neon.
- [ ] `GET /api/solicitudes` y `GET /api/estadisticas` responden `200` sin llave.
- [ ] `python test_smoke.py -v` termina con `Ran 34 tests ... OK`.
- [ ] Guardaste `API_URL` para las fases 4 y 5.

---

## Fase 4 — Google Cloud y OAuth para n8n

**Objetivo:** crear el proyecto de Google Cloud, habilitar las APIs de Google Sheets y Gmail, configurar la pantalla de consentimiento y crear las credenciales OAuth que n8n usará para leer la hoja y enviar correos.

**Tiempo estimado:** 20 a 30 minutos.

> **Importante:** n8n no pide usuario y contraseña de Gmail: usa OAuth 2.0, que requiere crear una "aplicación" en Google Cloud y autorizarla. Los pasos siguientes son la parte más delicada de la guía; síguelos en orden.

### 4.1 Crear el proyecto en Google Cloud

1. Abre <https://console.cloud.google.com> con la cuenta de Gmail que administrará el sistema.
2. Acepta los términos de servicio si es la primera vez.
3. En la barra superior, haz clic en el selector de proyectos (a la izquierda del buscador) → **New project**.
4. En **Project name** escribe: `solicitudes-soporte`.
5. En **Location** deja **No organization**.
6. Haz clic en **Create** y espera de 10 a 30 segundos.
7. En la notificación de creación, haz clic en **Select project** (o elige el proyecto en el selector). Verifica que el nombre `solicitudes-soporte` aparezca en la barra superior.

### 4.2 Habilitar Google Sheets API y Gmail API

Para cada API:

1. En el menú lateral (☰) ve a **APIs & Services** → **Library**.
2. En el buscador escribe `Google Sheets API`, abre el resultado y haz clic en **Enable**.
3. Vuelve a **Library** con la flecha de regreso.
4. Busca `Gmail API`, ábrela y haz clic en **Enable**.

Verificación: en **APIs & Services** → **Enabled APIs & services** deben aparecer **Google Sheets API** y **Gmail API**. Si alguna no aparece, repite el paso.

### 4.3 Configurar la pantalla de consentimiento OAuth

1. Ve a **APIs & Services** → **OAuth consent screen**.
2. Haz clic en **Get started** (o **Configure consent screen** en versiones anteriores).
3. **App information:**
   - **App name:** `Gestión de solicitudes de soporte`
   - **User support email:** tu correo de Gmail
4. Haz clic en **Next**.
5. **Audience:** selecciona **External** (permite autorizar cuentas de Gmail personales). Haz clic en **Next**.
6. **Contact information:** escribe tu correo. Marca la casilla de aceptación y haz clic en **Create** (o **Save and continue**).
7. En la página de resumen, ve a **Data access** (o **Scopes**) → **Add or remove scopes**.
8. En el campo para agregar scopes manualmente, pega uno por uno y agrégalos con **Add to table**:

```text
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive.file
https://www.googleapis.com/auth/gmail.send
```

9. Haz clic en **Update** → **Save and continue** hasta terminar el asistente.
10. En **Audience** → **Test users** → **Add users**, agrega la cuenta de Gmail que usará n8n (la misma que administra el sistema) y, si aplica, la cuenta del profesor para pruebas. Guarda.

> **Scopes explicados:** `spreadsheets` permite leer y actualizar la hoja del dashboard; `drive.file` permite a n8n acceder a los archivos que la propia app abre (lo usa el nodo de Google Sheets); `gmail.send` permite enviar correos de notificación desde la cuenta autorizada.

> **Advertencia sobre el modo de prueba:** mientras la app esté en estado **Testing**, los tokens de acceso de cuentas externas caducan a los **7 días**. Si el workflow deja de funcionar después de una semana, vuelve a autorizar la credencial en n8n (o publica la app con **Publish app**; Google puede pedir verificación para scopes sensibles como Gmail, así que para el proyecto escolar es válido quedarse en modo prueba y reautorizar).

### 4.4 Crear las credenciales OAuth (cliente web)

1. Ve a **APIs & Services** → **Credentials**.
2. Haz clic en **+ Create credentials** → **OAuth client ID**.
3. En **Application type** selecciona **Web application**.
4. En **Name** escribe: `n8n Cloud`.
5. En **Authorized redirect URIs** haz clic en **+ Add URI** y pega exactamente la URL de callback de tu instancia de n8n:

```text
https://<TU_SUBDOMINIO>.app.n8n.cloud/rest/oauth2-credential/callback
```

   - Sustituye `<TU_SUBDOMINIO>` por el que te asignó n8n Cloud (lo verás en la URL de tu instancia, por ejemplo `https://mi-equipo.app.n8n.cloud`). En el paso 4.6 puedes confirmar la URL exacta que muestra n8n.
   - Si usas n8n autoalojado en tu computadora, agrega también:

```text
http://localhost:5678/rest/oauth2-credential/callback
```

6. Haz clic en **Create**.
7. Google muestra **Client ID** y **Client secret**. **Cópialos y guárdalos** en un lugar seguro; el secreto no se vuelve a mostrar completo.

> **Error frecuente:** `redirect_uri_mismatch`. Ocurre cuando la URI registrada en Google no coincide **exactamente** con la que usa n8n (un carácter, `http` vs `https` o una diagonal final de más). Copia la URL directamente desde la ventana de credenciales de n8n.

### 4.5 Crear la cuenta de n8n Cloud y obtener el subdominio

1. Abre <https://n8n.cloud> y haz clic en **Start free trial** (o **Sign up**).
2. Regístrate con tu correo o con Google, verifica el correo y completa el asistente.
3. Al entrar al editor, revisa la barra de direcciones del navegador. La instancia tiene la forma:

```text
https://<TU_SUBDOMINIO>.app.n8n.cloud
```

   Por ejemplo: `https://soporte-tecnico.app.n8n.cloud`. Ese subdominio es el que debes usar en el paso 4.4.

4. Si ya cerraste el asistente, el subdominio también aparece en **Settings** (engrane) → **Overview**, en el campo **Instance URL**.

### 4.6 Crear las credenciales de Google dentro de n8n

**Credencial Google Sheets OAuth2 API:**

1. En el editor de n8n, abre el menú lateral → **Credentials** (icono de llave).
2. Haz clic en **Add credential** (o **+ New credential**).
3. Busca y selecciona **Google Sheets OAuth2 API**.
4. En el campo **OAuth Redirect URL** n8n muestra la URL exacta de callback. Compárala con la que registraste en Google Cloud; si no coincide, corrige la de Google Cloud (paso 4.4) antes de continuar.
5. Pega el **Client ID** y el **Client Secret** del paso 4.4.
6. Haz clic en **Save** y luego en **Sign in with Google**.
7. Elige la cuenta de Gmail del sistema, revisa los permisos y haz clic en **Continue** / **Allow**.
8. Resultado esperado: la credencial muestra **Connection tested successfully** o el aviso azul **Account connected**.

**Credencial Google Sheets Trigger OAuth2 API:**

El nodo **Google Sheets Trigger** usa un tipo de credencial **distinto** al del nodo de escritura. Repite los pasos 2 a 7 seleccionando **Google Sheets Trigger OAuth2 API** y el mismo Client ID y Client Secret.

**Credencial Gmail OAuth2 API:**

1. Repite los pasos 2 a 7, pero seleccionando **Gmail OAuth2 API**.
2. Usa el **mismo** Client ID y Client Secret (la misma aplicación de Google Cloud).
3. Al autorizar, acepta el permiso de **enviar correo electrónico**.

> Si aparece **Access blocked: This app's request is invalid**: revisa que las APIs estén habilitadas y que hayas agregado tu cuenta en **Test users**. Si aparece **Error 403: access_denied**, agrega la cuenta a los usuarios de prueba o publica la app.

### 4.7 Probar las credenciales

**Google Sheets:** crea un workflow temporal → agrega un nodo **Google Sheets** → **Resource:** `Sheet Within Document` (o `Spreadsheet`) → **Operation:** `Get Row(s)` (o `Get Many`) → selecciona la credencial recién creada y la hoja del proyecto → **Execute step**. Resultado esperado: filas de la hoja en el panel de salida.

**Gmail:** agrega un nodo **Gmail** → **Operation:** `Send` → **To:** tu propio correo → **Subject:** `Prueba n8n` → **Message:** `Prueba de credenciales`. Ejecuta el paso y revisa la bandeja de entrada.

> Si la hoja de cálculo aún no existe, créala primero con la guía `docs/guia-google-forms-sheets.md` (Google Forms y dashboard) y compártela con la misma cuenta que autorizaste.

### Verificación de la fase 4

- [ ] Proyecto `solicitudes-soporte` creado en Google Cloud y seleccionado.
- [ ] **Google Sheets API** y **Gmail API** habilitadas (aparecen en *Enabled APIs & services*).
- [ ] Pantalla de consentimiento configurada como **External**, con los tres scopes y tu cuenta en **Test users**.
- [ ] Cliente OAuth **Web application** creado con la redirect URI `https://<TU_SUBDOMINIO>.app.n8n.cloud/rest/oauth2-credential/callback`.
- [ ] Credencial **Google Sheets Trigger OAuth2 API** conectada en n8n (la usa el trigger).
- [ ] Credencial **Google Sheets OAuth2 API** conectada en n8n (la usa el nodo de escritura).
- [ ] Credencial **Gmail OAuth2 API** conectada en n8n (sin errores).
- [ ] Probaste una lectura de Sheets y un envío de correo desde n8n.
- [ ] Guardaste Client ID y Client Secret en un lugar seguro.

---

## Fase 5 — Workflow de automatización en n8n

**Objetivo:** importar `n8n/workflow-solicitudes.json`, conectar los nodos con la API de Render y las credenciales de Google, activar el workflow y comprobarlo con una respuesta real del formulario.

**Tiempo estimado:** 15 a 25 minutos.

### 5.1 Importar el workflow

1. Inicia sesión en tu instancia de n8n Cloud.
2. En el menú lateral entra a **Workflows** y haz clic en **Create Workflow** (o en **+ New workflow**).
3. En la esquina superior derecha del lienzo haz clic en el menú **⋯** (tres puntos) → **Import from File...**
4. Selecciona el archivo `n8n/workflow-solicitudes.json` de tu repositorio local (o descárgalo de GitHub → botón **Code** → **Download ZIP**, si no lo tienes a mano).
5. Confirma la importación. El lienzo debe mostrar una nota llamada **Configuración** y estos nodos: **Google Sheets Trigger** → **Normalizar fila** → **Registrar en API** → **¿Respuesta OK?** → **¿Ya estaba registrada?** (rama de duplicado y rama de correo) → **Correo al solicitante** → **Escribir folio en la hoja**, más la rama de error **Alerta al administrador** → **Detener con error**.
6. Cambia el nombre del workflow (clic en el título) si quieres; el nombre original es `Solicitudes de soporte técnico · Form → API Flask → Folio`.
7. Haz clic en **Save** (o `Ctrl + S`).

> Si el archivo se importó con nodos en rojo, es normal: los nodos que necesitan credenciales o valores del entorno aparecen marcados hasta que los configures en los pasos siguientes.

### 5.2 Configurar los nodos

Al importar el workflow verás una nota **Configuración** y diez nodos. Los nombres son los del JSON; configúralos en este orden:

**1) Nota «Configuración» (sticky note):** léela. Indica los cuatro valores que debes reemplazar (`PEGA_AQUI_EL_ID_DEL_SPREADSHEET`, `TU-SERVICIO`, `TU-API-KEY-AQUI` y `soporte-admin@ejemplo.com`). No se ejecuta: es documentación dentro del lienzo.

**2) Google Sheets Trigger (nodo de disparo):**

- **Credential to connect with:** **Google Sheets Trigger OAuth2 API** (ojo: el trigger usa una credencial distinta a la del nodo de escritura; se crea con el mismo Client ID y Client Secret de la fase 4).
- **Spreadsheet:** reemplaza `PEGA_AQUI_EL_ID_DEL_SPREADSHEET` por el ID de la hoja o selecciónala de la lista.
- **Sheet Name:** `Respuestas de formulario 1` (ajusta si tu pestaña se llama distinto).
- **Trigger On:** `Row Added` (fila agregada).
- **Header Row:** `1`.
- Las opciones **Value Render** (`UNFORMATTED_VALUE`) y **Date Time Render** (`FORMATTED_STRING`) ya vienen configuradas: no las cambies.
- Guarda el nodo.

**3) Normalizar fila (Code):** no requiere configuración. Convierte las columnas del formulario (`Nombre completo`, `Correo electrónico`, `Teléfono de contacto`, `Área o departamento`, `Categoría del problema`, `Prioridad de atención`, `Descripción detallada del problema`) a las llaves de la API (`nombre`, `correo`, `telefono`, `area`, `categoria`, `prioridad`, `descripcion`), normaliza categorías y prioridades, y genera `id_externo` como `form-<marca temporal>`. La columna `Nivel de afectación` se conserva en la hoja para el dashboard, pero no se envía a la API. Si cambiaste el texto de las preguntas del formulario, edita el objeto `COLUMNAS` del código para que coincidan exactamente.

**4) Registrar en API (HTTP Request):**

- **Method:** `POST`.
- **URL:** `https://api-solicitudes-soporte.onrender.com/api/solicitudes` (reemplaza el valor de ejemplo `https://TU-SERVICIO.onrender.com/api/solicitudes`).
- **Headers:** conserva `Content-Type: application/json` y reemplaza `TU-API-KEY-AQUI` por tu API key de la fase 3.
- **Body:** tipo JSON con la expresión `={{ JSON.stringify($json) }}`. No la cambies: envía el objeto que produjo **Normalizar fila**.
- **Settings → Timeout:** el JSON trae `60000` ms; súbelo a `90000` ms para tolerar el cold start de Render.
- **Response / On Error:** el JSON trae `neverError: true` y `On Error: Continue (using error output)`; no los quites, porque así el workflow puede enviar la alerta en lugar de fallar en seco.
- Guarda el nodo.

> El texto del JSON usa expresiones de n8n (`={{ ... }}`). No las reemplaces por texto plano: son las que insertan el folio y los datos reales en el correo y en la hoja.

**5) ¿Respuesta OK? (IF):** no requiere configuración. Verifica que `$json.ok` sea verdadero y que `$json.data.folio` no esté vacío. La salida **true** continúa a la rama de correo; la salida **false** va a la alerta del administrador.

**6) ¿Ya estaba registrada? (IF):** no requiere configuración. Si `$json.duplicado === true`, la salida **true** termina en **Duplicado: no reenviar** (nodo NoOp) para no mandar el correo dos veces; la salida **false** continúa al correo del solicitante.

**7) Correo al solicitante (Gmail):**

- **Credential:** **Gmail OAuth2 API**.
- **To:** `={{ $json.data.correo }}` (el correo del solicitante tal como lo devolvió la API).
- **Subject:** ya incluye el folio (`✅ Solicitud {{ $json.data.folio }} registrada · Soporte técnico`).
- **Email Type:** `HTML`, con folio, categoría, prioridad, estado y fecha de registro tomados de `$json.data`.
- No cambies las expresiones; solo asigna la credencial y guarda.

**8) Escribir folio en la hoja (Google Sheets):**

- **Credential:** **Google Sheets OAuth2 API**.
- **Spreadsheet / Sheet Name:** los mismos del trigger.
- **Operation:** `Append or Update Row` (en el JSON aparece como `appendOrUpdate`) con **matching column** `Marca temporal`.
- Valores mapeados: `Folio` = `{{ $('Registrar en API').first().json.data.folio }}`, `Estado` = `...data.estado`, `Fecha de registro` = `...data.fecha_registro` y `Correo enviado` = `Sí`. Si tu hoja usa otros nombres de columna, ajusta la coincidencia (deben ser los definidos en `docs/guia-google-forms-sheets.md`).
- Guarda el nodo.

**9) Alerta al administrador (Gmail):**

- **Credential:** **Gmail OAuth2 API**.
- **To:** reemplaza `soporte-admin@ejemplo.com` por el correo real del administrador (idealmente el mismo valor de `ADMIN_EMAIL` configurado en Render).
- El cuerpo ya incluye el motivo del error, el solicitante, el correo y la fecha del aviso; solo ajusta el texto si lo deseas.
- Guarda el nodo.

**10) Detener con error (Stop and Error):** marca la ejecución como fallida después de avisar al administrador. Deja el mensaje o ajústalo; no requiere configuración adicional.

Después de configurar todo, haz clic en **Save**.

### 5.3 Activar el workflow

1. En la esquina superior derecha del editor, activa el interruptor **Active**.
2. Confirma el aviso. El estado debe cambiar a **Active** (verde).
3. **No cierres el proyecto de n8n con el workflow en borrador:** si el toggle no está en Active, el disparador de Google Sheets no revisa la hoja y nada se ejecutará.

> El trigger de Google Sheets revisa la hoja **cada minuto** aproximadamente. No esperes ejecución instantánea: al probar, espera hasta 2 minutos.

### 5.4 Probar con una respuesta real del formulario

1. Pide a un compañero (o hazlo tú) que llene el Google Form con datos de prueba válidos:
   - Nombre, correo, categoría, prioridad y descripción.
2. Espera 1 o 2 minutos. En n8n, abre la pestaña **Executions** (menú lateral → **Overview** → **Executions**, o **Executions** en el workflow).
3. Si el workflow se ejecutó, aparece una fila nueva con estado **Success** (verde). Haz clic para revisar la salida de cada nodo en orden.
4. Comprueba los efectos:

- [ ] La solicitud aparece en la base de datos: `GET /api/solicitudes` o `SELECT * FROM solicitudes ORDER BY id DESC;` en Neon.
- [ ] El solicitante recibió el correo con su folio (nodo **Correo al solicitante**).
- [ ] La fila de la hoja de Google Sheets se actualizó con folio, estado, fecha y `Correo enviado` = `Sí` (nodo **Escribir folio en la hoja**).
- [ ] Si simulas un error (por ejemplo, borra temporalmente la `API_KEY` en Render o desactiva el servicio), se ejecuta la rama **Alerta al administrador** → **Detener con error** y llega el aviso al correo del administrador.
- [ ] Si repites la misma respuesta (mismo `id_externo`), el nodo **¿Ya estaba registrada?** termina en **Duplicado: no reenviar** y no se envía un segundo correo.

5. Si el workflow marca **Error**, abre la ejecución, revisa qué nodo falló y consulta la sección [Solución de problemas](#solución-de-problemas).

### Verificación de la fase 5

- [ ] `n8n/workflow-solicitudes.json` importado y guardado.
- [ ] Los cuatro marcadores del workflow reemplazados: ID del spreadsheet, URL de Render, `X-API-Key` y correo del administrador.
- [ ] Credenciales **Google Sheets Trigger OAuth2 API**, **Google Sheets OAuth2 API** y **Gmail OAuth2 API** asignadas a sus nodos.
- [ ] Nodo **Registrar en API** con timeout de 90 000 ms.
- [ ] Columna de coincidencia `Marca temporal` configurada en **Escribir folio en la hoja**.
- [ ] Workflow en estado **Active**.
- [ ] Una respuesta real del formulario generó una ejecución **Success** y actualizó la BD, la hoja y los correos.

---

## Fase 6 — Verificación final y checklist de entrega

**Objetivo:** comprobar el flujo completo de punta a punta y reunir todos los entregables en el repositorio y en la nube.

**Tiempo estimado:** 20 a 30 minutos.

### 6.1 Verificación end-to-end

Ejecuta la secuencia completa, en este orden. Marca cada casilla solo si el resultado es el esperado:

1. [ ] **Formulario en línea:** abre el Google Form desde una ventana de incógnito y envíalo con datos reales de prueba.
2. [ ] **Respuesta registrada en Sheets:** la pestaña de respuestas de la hoja muestra la fila nueva en menos de 2 minutos.
3. [ ] **Workflow ejecutado:** en n8n, **Executions** muestra una ejecución **Success** con todos los nodos en verde.
4. [ ] **Solicitud en la API:** `curl -s "$API_URL/api/solicitudes" -H "X-API-Key: $API_KEY"` incluye el folio nuevo.
5. [ ] **Solicitud en Neon:** `SELECT folio, nombre, categoria, prioridad, estado, fecha_registro FROM solicitudes ORDER BY id DESC LIMIT 5;` devuelve la fila con folio `SOL-AAAA-NNNN` y estado `Pendiente`.
6. [ ] **Correo al solicitante:** la bandeja del correo capturado en el formulario recibió el mensaje con el folio (revisa también spam).
7. [ ] **Hoja actualizada:** la fila del formulario ya tiene folio, estado y fecha en las columnas del dashboard; los contadores y gráficas se actualizaron.
8. [ ] **Cambio de estado:** `PATCH /api/solicitudes/<FOLIO>/estado` con `{"estado": "En proceso"}` responde `200`; la fila de Neon y el dashboard reflejan el cambio.
9. [ ] **Estadísticas:** `GET /api/estadisticas` devuelve conteos coherentes con la hoja.
10. [ ] **Protección de la API:** `POST` sin `X-API-Key` devuelve `401`; `GET /no-existe` devuelve `404` con JSON de error.

Si alguno falla, revisa la sección [Solución de problemas](#solución-de-problemas) antes de continuar.

### 6.2 Evidencia sugerida (para el reporte)

Guarda capturas de pantalla con fecha visible en una carpeta `evidencias/` (sin datos personales reales):

| # | Evidencia | Dónde se captura |
|---|---|---|
| 1 | Proyecto y base de datos en Neon | Consola de Neon → panel del proyecto |
| 2 | Esquema ejecutado y tabla `solicitudes` | Neon SQL Editor con el resultado de `SELECT * FROM solicitudes;` |
| 3 | Repositorio en GitHub | Página principal del repositorio |
| 4 | Servicio **Live** en Render | Panel del Web Service |
| 5 | Log de arranque de Gunicorn | Render → Logs |
| 6 | `GET /health` con `"base_datos": "conectada"` | Terminal con `curl -i` |
| 7 | `POST` exitoso con folio `SOL-AAAA-NNNN` | Terminal con `curl -i` y respuesta `201` |
| 8 | Pruebas automatizadas `Ran 34 tests ... OK` | Terminal con `python test_smoke.py -v` |
| 9 | APIs habilitadas en Google Cloud | *Enabled APIs & services* |
| 10 | Credenciales OAuth conectadas | n8n → Credentials |
| 11 | Workflow activo y ejecución **Success** | n8n → Executions |
| 12 | Correo recibido con el folio | Bandeja de entrada |
| 13 | Dashboard de la hoja actualizado | Pestaña Dashboard de Google Sheets |

### 6.3 Checklist de entrega

| Entregable | Dónde se verifica | Criterio de aceptación | Listo |
|---|---|---|---|
| Código fuente en GitHub | `https://github.com/<TU_USUARIO>/proyecto-solicitudes` | Repositorio con `backend/`, `database/`, `n8n/`, `docs/`, `render.yaml` y README; sin secretos | [ ] |
| API en Render | `https://api-solicitudes-soporte.onrender.com` | Servicio **Live**, `/health` con `"base_datos": "conectada"`, endpoints funcionando | [ ] |
| Base de datos en Neon | Consola de Neon | Tabla `solicitudes`, triggers, índices y tres vistas creados; solicitudes de prueba | [ ] |
| Workflow n8n exportado | `n8n/workflow-solicitudes.json` en GitHub | JSON importable, con credenciales y URL documentadas (sin llaves reales en el JSON) | [ ] |
| Google Forms | Enlace `forms.gle/...` compartido | Preguntas, obligatoriedad y respuestas vinculadas a Sheets | [ ] |
| Dashboard en Google Sheets | Pestaña Dashboard | Totales, por categoría, por prioridad y por estado; gráficas funcionando | [ ] |
| Hoja y formulario compartidos con el profesor | Google Drive/Sheets → **Compartir** | Acceso de **Lector** (o editor si el profesor lo pide) a la hoja y al formulario | [ ] |
| Documentación técnica | `docs/documentacion-tecnica.md` | Portada, arquitectura, modelo de datos y API completos | [ ] |
| Guía de despliegue | `docs/guia-despliegue-render-neon.md` | Este documento, con las fases y verificaciones | [ ] |
| Guía de Forms/Sheets | `docs/guia-google-forms-sheets.md` | Formulario, hoja y dashboard explicados | [ ] |
| Pruebas de API | `docs/pruebas-api.md` | Casos de prueba con comandos curl y resultados | [ ] |
| README | `README.md` en la raíz del repositorio | Descripción, arquitectura, URLs públicas, variables y cómo ejecutar localmente | [ ] |

### 6.4 Limpieza final

1. Borra las solicitudes de prueba que no quieras entregar (o déjalas como datos de demostración):

```sql
DELETE FROM solicitudes
WHERE correo IN ('ana.lopez@escuela.edu.mx', 'prueba@ejemplo.com')
RETURNING folio;
```

2. Verifica que las credenciales y secretos reales **no** estén en GitHub:

```powershell
git ls-files | Select-String -Pattern "\.env|API_KEY|DATABASE_URL"
```

Resultado esperado: solo `backend/.env.example` (y este puede contener únicamente valores de ejemplo).

3. Deja el workflow de n8n en **Active** y la hoja compartida con el profesor.
4. Exporta de nuevo el workflow desde n8n (**⋯** → **Download**) y actualiza `n8n/workflow-solicitudes.json` si cambiaste algo; haz `git add`, `git commit` y `git push`.

### Verificación de la fase 6

- [ ] Las 10 comprobaciones end-to-end de la sección 6.1 fueron exitosas.
- [ ] Reuniste la evidencia de la sección 6.2.
- [ ] El checklist de entrega de la sección 6.3 está completo.
- [ ] No hay secretos en el repositorio.
- [ ] El workflow está activo y la hoja disponible para el profesor.

---

## Solución de problemas

### 7.1 Tabla rápida de diagnóstico

| Síntoma | Causa probable | Solución rápida |
|---|---|---|
| `GET /health` responde `200` con `"base_datos": "desconectada"` | `DATABASE_URL` mal escrita, cadena *direct* en lugar de *pooled*, sin `sslmode=require` o contraseña incorrecta | Revisar la variable en Render y los logs; ver 7.2 |
| `503 {"error":"Servicio de base de datos no disponible."}` en `POST`/`GET` | La conexión a Neon falló; el cuerpo trae `mensaje` y `sugerencia` | Ver 7.2 |
| `400 {"error":"La solicitud contiene datos inválidos.","errores":{...}}` | Faltan campos obligatorios o los valores no están entre los permitidos | Corregir el JSON; ver `docs/documentacion-tecnica.md` |
| `401 {"error":"No autorizado."}` | Header `X-API-Key` ausente, mal escrito o llave distinta entre Render y n8n | Revisar `API_KEY`; ver 7.3 |
| `201` al `POST` sin llave | La variable `API_KEY` está vacía en Render | Configurarla; ver 7.3 |
| El trigger de Sheets no dispara | Workflow inactivo, credencial vencida, fila de encabezados mal configurada o el formulario escribe en otra pestaña | Ver 7.4 |
| Gmail devuelve error de permiso | Scopes faltantes, app en modo prueba con token vencido o cuenta no autorizada | Ver 7.5 |
| Primer request tarda ~1 minuto o `502/503` del proxy de Render | Cold start del plan Free de Render (y de Neon) | Reintentar; subir timeout; ver 7.6 |
| `SSL connection is required` / `sslmode` | Cadena de conexión sin `sslmode=require` o con `sslmode=disable` | Corregir la cadena; ver 7.7 |
| `duplicate key value violates unique constraint "solicitudes_folio_key"` | Se insertó un `folio` manual o la secuencia quedó desfasada | No enviar `folio`; resincronizar; ver 7.8 |
| Error de CORS en el navegador | Origen no permitido o método no permitido | Revisar `CORS_ORIGINS`; ver 7.9 |
| Build falla en Render | Falta `requirements.txt`, ruta raíz incorrecta o versión de Python | Revisar logs y `Root Directory`; ver 7.10 |
| `404 {"error":"Recurso no encontrado..."}` en una ruta que debería existir | URL o método mal escrito (por ejemplo `GET /api/solicitudes/SOL-.../estado`) | Revisar `GET /` para la lista de endpoints |
| n8n: `The service is currently unavailable` o timeout | Cold start de Render o timeout corto del nodo | Aumentar timeout a 90 s; ver 7.6 |
| n8n: `403 The caller does not have permission` en Sheets | La cuenta autorizada no tiene acceso a la hoja | Compartir la hoja con esa cuenta |

### 7.2 Health en 200 pero base de datos desconectada (o errores 503)

**Síntomas:** `GET /health` responde `200` pero con `"base_datos": "desconectada"` y el mensaje "El servicio está en línea, pero no hay conexión con PostgreSQL...". Los endpoints que consultan la base devuelven `503` con `{"ok": false, "error": "Servicio de base de datos no disponible.", "mensaje": "...", "sugerencia": "..."}`.

**Causas y solución, en orden:**

1. La variable `DATABASE_URL` no existe en Render o tiene espacios/saltos de línea. Ve a Render → tu servicio → **Environment**, revisa el valor y guárdalo de nuevo (esto reinicia el servicio).
2. La cadena es la **direct** en lugar de la **pooled**, o le falta `sslmode=require`. Copia de nuevo la cadena *pooled* desde Neon (**Connect** → **Connection pooling** activado).
3. El proyecto de Neon está suspendido o la contraseña del rol cambió. Entra a Neon, abre el SQL Editor y verifica que responde; si cambiaste la contraseña, actualiza `DATABASE_URL`.
4. La tabla no existe: el mensaje del `503` incluirá "No existe la tabla 'solicitudes'. Ejecuta database/schema.sql en el SQL Editor de Neon." En ese caso, ejecuta el esquema (fase 1).
5. La estructura de la tabla es vieja: el mensaje dirá "La tabla 'solicitudes' no tiene la estructura esperada. Vuelve a ejecutar database/schema.sql."
6. Prueba la conexión localmente con `psql` usando la cadena *direct*:

```powershell
psql "postgresql://neondb_owner:<PASSWORD>@<HOST_DIRECTO>/neondb?sslmode=require" -c "SELECT version();"
```

7. Revisa **Logs** en Render: el rastro de `psycopg2.OperationalError` indica el host o la autenticación exactos que fallaron.

> Recuerda: `/health` está diseñado para **siempre** responder `200` (así Render no reinicia el servicio por una caída de la base), por lo que la prueba real de conexión es el campo `base_datos`, no el código HTTP.

### 7.3 Error 401: API key inválida o ausente

**Síntomas:** `{"ok": false, "error": "No autorizado.", "mensaje": "Incluye el header 'X-API-Key' con la clave correcta..."}` en `POST` o `PATCH`. Si el `POST` sin llave responde `201`, la llave no está configurada.

**Solución:**

1. En Render → **Environment**, confirma el valor de `API_KEY` (sin comillas ni espacios).
2. En el nodo HTTP de n8n, abre **Headers** y verifica:
   - Nombre exacto: `X-API-Key` (con mayúsculas y guion).
   - Valor: la llave **completa**, sin espacios.
3. Prueba con curl para aislar el problema:

```bash
curl -i "$API_URL/api/solicitudes" -H "X-API-Key: $API_KEY"
# Con una llave incorrecta, el POST/PATCH responde 401; el GET sigue siendo público
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$API_URL/api/solicitudes" \
  -H "Content-Type: application/json" -d '{"nombre":"Prueba sin clave"}'
```

4. Si acabas de cambiar `API_KEY` en Render, espera el redespliegue y vuelve a probar. Recuerda actualizar también n8n; de lo contrario, n8n seguirá enviando la llave anterior y recibirá `401` en cada ejecución.

> **Nunca** compartas la API key en el repositorio, en capturas públicas ni en el JSON del workflow de n8n. En el JSON, el header debe quedar como marcador (`<API_KEY>`) y configurarse manualmente en n8n.

### 7.4 El trigger de Google Sheets no se dispara

**Síntomas:** envías una respuesta al formulario y no aparece ninguna ejecución en n8n.

**Solución, en orden:**

1. **Workflow activo:** el interruptor **Active** debe estar en verde. Si está en borrador, el trigger no revisa la hoja.
2. **Pestaña correcta:** el trigger debe apuntar a la pestaña donde Google Forms escribe las respuestas (por ejemplo `Respuestas de formulario`), no al dashboard.
3. **Fila de encabezados:** el campo **Header Row** debe ser `1` y la primera fila debe tener los títulos de las columnas.
4. **Credencial:** el trigger usa **Google Sheets Trigger OAuth2 API** (distinta de la que usa el nodo de escritura). Abre esa credencial; si muestra **Connection needs to be reconnected** o el token expiró (modo prueba, 7 días), haz clic en **Reconnect**.
5. **Ventana de espera:** el trigger consulta la hoja aproximadamente cada minuto; espera 2 minutos antes de concluir que falló.
6. **Permisos:** la cuenta que autorizó la credencial debe tener acceso de edición a la hoja (o al menos lectura). Comparte la hoja con esa cuenta.
7. **Un solo trigger por hoja:** si hay dos workflows activos escuchando la misma hoja, solo uno recibirá los eventos; desactiva el duplicado.
8. **Ejecuciones:** revisa **Executions** por si el workflow se ejecutó con error en un paso posterior (por ejemplo, el correo).

### 7.5 Gmail sin permiso o token vencido

**Síntomas:** errores como `Insufficient Permission`, `invalid_grant`, `unauthorized_client` o `Request had insufficient authentication scopes`.

**Solución:**

1. Verifica en Google Cloud que la **Gmail API** está habilitada.
2. Revisa que el scope `https://www.googleapis.com/auth/gmail.send` esté aprobado en la pantalla de consentimiento.
3. Si la app está en modo **Testing**, los tokens caducan a los 7 días: en n8n abre la credencial de Gmail y haz clic en **Reconnect** (o elimínala y créala de nuevo).
4. Confirma que la cuenta autorizada en n8n es la misma que aparece en **Test users**.
5. Si el correo del remitente es distinto al de la cuenta autorizada, usa la cuenta autorizada como remitente o configura un alias verificado en Gmail.
6. Después de corregir, ejecuta de nuevo el nodo de Gmail para validar.

### 7.6 Cold start lento (50 s o más) y timeouts

**Síntomas:** el primer request del día tarda mucho; n8n falla con `timeout of 30000ms exceeded`, `The service is currently unavailable` o `502`.

**Solución:**

1. Entiende el comportamiento: Render Free duerme el servicio tras ~15 minutos sin tráfico y Neon suspende el cómputo. El primer request "despierta" ambos y puede tardar de 50 segundos a 1 minuto.
2. En el nodo HTTP de n8n, sube **Settings** → **Timeout** a `90000` ms (el comando de arranque ya usa `--timeout 60` en Gunicorn).
3. Despierta la API antes de una demostración abriendo `https://<tu-servicio>.onrender.com/health` en el navegador y esperando a que responda.
4. Si usas monitoreo externo (UptimeRobot/cron-job.org), configura pings cada 10–14 minutos y ten presente el consumo de horas de instancia. No es obligatorio para la entrega.
5. Si el error persiste por horas, revisa que el servicio esté en **Live** y que no haya alcanzado el límite de horas del mes.

### 7.7 Error de SSL requerido

**Síntomas:** `connection to server ... failed: SSL connection has been closed unexpectedly`, `sslmode value "disable" invalid` o un aviso de que Neon requiere SSL.

**Solución:**

1. Edita `DATABASE_URL` en Render y asegúrate de que termine en `?sslmode=require` (o `?sslmode=verify-full`).
2. No uses `sslmode=disable` ni `?ssl=false`.
3. La API agrega `sslmode=require` automáticamente si la cadena no lo incluye, pero si tu cadena trae un valor contradictorio (por ejemplo `sslmode=prefer`) puede fallar: reemplázalo por `require`.
4. Render sirve la API por HTTPS automáticamente; no es necesario configurar certificados en la app. El SSL del que habla este error es el de la conexión **API → Neon**.

### 7.8 Folio duplicado o secuencia desfasada

**Síntomas:** `duplicate key value violates unique constraint "solicitudes_folio_key"` al insertar, o los folios "se saltan" números.

**Causas y solución:**

1. **Causa más común:** se envió un campo `folio` en el JSON del `POST`. La API y el trigger `trg_asignar_folio` generan el folio; **nunca** lo envíes desde n8n ni desde el formulario. La API solo inserta `nombre`, `correo`, `telefono`, `area`, `categoria`, `prioridad`, `descripcion` e `id_externo`.
2. Si insertaste filas manualmente con folios fijos, la secuencia puede quedar atrás. Resincronízala con el valor máximo actual (ejecuta en el SQL Editor de Neon):

```sql
SELECT setval(
         'solicitudes_folio_seq',
         GREATEST(
           (SELECT COALESCE(MAX(SUBSTRING(folio FROM '[0-9]+$')::bigint), 0) FROM solicitudes),
           1
         ),
         true
       );
```

3. Los saltos de numeración son normales cuando una transacción falla: la secuencia no se reutiliza y eso protege contra duplicados en concurrencia.
4. Vuelve a probar con un `POST` nuevo y comprueba el folio.

### 7.9 Error de CORS en el navegador

**Síntomas:** en la consola del navegador aparece `Access to fetch ... has been blocked by CORS policy`.

**Solución:**

1. Confirma que la petición va al dominio `https://...onrender.com` (HTTPS) y no a `http://`.
2. Por defecto la API permite todos los orígenes (`CORS_ORIGINS=*`). Si restringiste los orígenes, agrega el dominio desde el que se consume la API en la variable `CORS_ORIGINS` (separados por coma, si la app lo soporta en tu configuración) y vuelve a desplegar.
3. Recuerda que n8n y curl **no** están sujetos a CORS: si el error solo ocurre en el navegador, es configuración de orígenes, no un fallo de la API.
4. Para pruebas rápidas usa curl (no el navegador) y valida que la API funciona; después ajusta el origen permitido.

### 7.10 El build falla en Render

**Síntomas:** el deploy termina en **Failed**; el log muestra `Could not open requirements file`, `No module named ...` o un error de compilación de `psycopg2`.

**Solución:**

1. Verifica que **Root Directory** sea `backend` (allí viven `requirements.txt` y `app.py`).
2. Confirma que el comando de build sea exactamente `pip install -r requirements.txt`.
3. Revisa la versión de Python: debe ser **3.12.6** (archivo `backend/.python-version` o variable `PYTHON_VERSION`). Una versión distinta puede no tener ruedas binarias de `psycopg2-binary`. Si el log dice `pg_config executable not found` o `error: command 'gcc' failed`, estás usando una versión de Python sin *wheel*: agrega `PYTHON_VERSION` = `3.12.6` en **Environment** y redespliega.
4. Verifica que `requirements.txt` no fue alterado: `Flask==3.1.0`, `flask-cors==5.0.0`, `psycopg2-binary==2.9.10`, `python-dotenv==1.0.1`, `gunicorn==23.0.0`.
5. Si cambiaste `requirements.txt`, haz commit y push; Render vuelve a desplegar.
6. Abre el log completo del deploy y busca el primer error (los siguientes suelen ser consecuencia).

---

## Apéndices

### Apéndice A. Variables y URLs del proyecto (para llenar)

| Variable | Valor final |
|---|---|
| `API_URL` (Render) | `https://api-solicitudes-soporte.onrender.com` |
| `API_KEY` | `________________________________________` (guardar en gestor de contraseñas) |
| `DATABASE_URL` pooled | `postgresql://neondb_owner:________@ep-____-pooler.________.aws.neon.tech/neondb?sslmode=require` |
| Host directo de Neon | `ep-________.________.aws.neon.tech` |
| Subdominio n8n | `https://________________.app.n8n.cloud` |
| Google Client ID | `________________________.apps.googleusercontent.com` |
| Google Client Secret | `________________________` (guardar en gestor de contraseñas) |
| `ADMIN_EMAIL` | `________________________` |
| Repositorio GitHub | `https://github.com/________________/proyecto-solicitudes` |
| ID de la hoja de cálculo | `1____________________________________________` |

### Apéndice B. Comandos de referencia

```bash
# Health check de la API
curl -i "$API_URL/health"

# Listar solicitudes (público; el header es opcional)
curl -s "$API_URL/api/solicitudes?limit=10"

# Crear una solicitud (requiere llave)
curl -i -X POST "$API_URL/api/solicitudes" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"nombre":"Prueba","correo":"prueba@ejemplo.com","categoria":"Software","prioridad":"Baja","descripcion":"Prueba de despliegue"}'

# Consultar una solicitud por folio o por id
curl -s "$API_URL/api/solicitudes/SOL-2026-0001"
curl -s "$API_URL/api/solicitudes/1"

# Cambiar el estado (requiere llave)
curl -i -X PATCH "$API_URL/api/solicitudes/SOL-2026-0001/estado" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"estado":"Resuelto","notas":"Atendido por el área de sistemas"}'

# Estadísticas (público)
curl -s "$API_URL/api/estadisticas"
```

```powershell
# Git: actualizar el repositorio
git add .
git commit -m "Actualización del proyecto"
git push

# Generar una nueva API key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Pruebas de humo de la API (34 pruebas, sin Neon)
Set-Location backend
python test_smoke.py -v

# Ver archivos versionados que contengan ".env"
git ls-files | Select-String -Pattern "\.env"
```

```sql
-- Verificar la base
SELECT COUNT(*) FROM solicitudes;
SELECT folio, nombre, categoria, prioridad, estado, fecha_registro
FROM solicitudes ORDER BY id DESC LIMIT 10;
SELECT * FROM v_estadisticas_por_categoria;
SELECT * FROM v_estadisticas_por_prioridad;
SELECT * FROM v_estadisticas_por_estado;
```

### Apéndice C. Enlaces oficiales

- Flask — documentación: <https://flask.palletsprojects.com/>
- Flask-CORS: <https://flask-cors.readthedocs.io/>
- Gunicorn: <https://docs.gunicorn.org/>
- psycopg2: <https://www.psycopg.org/docs/>
- Render — despliegue de Python: <https://render.com/docs/deploy-flask>
- Render — plan Free y límites: <https://render.com/docs/free>
- Render — variables de entorno: <https://render.com/docs/configure-environment-variables>
- Render — health checks: <https://render.com/docs/health-checks>
- Render — Blueprints (`render.yaml`): <https://render.com/docs/infrastructure-as-code>
- Neon — primer proyecto: <https://neon.com/docs/get-started/set-up-your-project>
- Neon — conexión segura: <https://neon.com/docs/connect/connect-securely>
- Neon — connection pooling: <https://neon.com/docs/connect/connection-pooling>
- n8n — documentación: <https://docs.n8n.io/>
- n8n — credenciales de Google: <https://docs.n8n.io/integrations/builtin/credentials/google/>
- Google Cloud — OAuth 2.0: <https://developers.google.com/identity/protocols/oauth2>
- Google Sheets API: <https://developers.google.com/sheets/api>
- Gmail API: <https://developers.google.com/gmail/api>
- Google Forms — ayuda: <https://support.google.com/docs/answer/6281888>

---

**Fin de la guía.** Si alguna fase no se puede completar por un límite del plan gratuito (por ejemplo, la prueba de n8n), documenta el avance en `docs/pruebas-api.md` y usa una instancia local de n8n con Docker para la demostración.
