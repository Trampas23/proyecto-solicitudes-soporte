# Sistema automatizado de gestión de solicitudes de soporte técnico

**Materia:** Programación en ambiente cliente servidor · **Profesor:** Ing. Alex Ramírez Galindo
**Proyecto:** Segundo parcial · **Modalidad:** Individual

> **Este repositorio ya trae el código y los archivos listos y probados.**
> A ti te toca la parte de **crear las cuentas, desplegar y conectar los servicios**.
> Sigue las 8 fases en orden; cada una termina con un ✅ criterio de aceptación.
> **Tiempo total estimado: 3 a 4 horas** (puedes repartirlo en 2 o 3 días).

---

## Índice

1. [Lo que vas a entregar](#1-lo-que-vas-a-entregar)
2. [Antes de empezar: cuentas y herramientas](#2-antes-de-empezar-cuentas-y-herramientas)
3. [Arquitectura del sistema](#3-arquitectura-del-sistema)
4. [Fase 1 — Base de datos en Neon](#fase-1--base-de-datos-en-neon-15-min)
5. [Fase 2 — Subir el proyecto a GitHub](#fase-2--subir-el-proyecto-a-github-10-min)
6. [Fase 3 — Desplegar la API en Render](#fase-3--desplegar-la-api-en-render-20-min)
7. [Fase 4 — Probar la API](#fase-4--probar-la-api-10-min)
8. [Fase 5 — Google Forms + Google Sheets](#fase-5--google-forms--google-sheets-25-min)
9. [Fase 6 — Automatización con n8n](#fase-6--automatización-con-n8n-40-min)
10. [Fase 7 — Dashboard en Google Sheets](#fase-7--dashboard-en-google-sheets-20-min)
11. [Fase 8 — Documentación y entrega](#fase-8--documentación-y-entrega-15-min)
12. [Planes de trabajo según tu tiempo](#planes-de-trabajo-según-tu-tiempo)
13. [Problemas comunes y cómo resolverlos](#problemas-comunes-y-cómo-resolverlos)
14. [Estructura del proyecto](#estructura-del-proyecto)
15. [Cómo se cumple cada requisito del PDF](#cómo-se-cumple-cada-requisito-del-pdf)
16. [Capturas de pantalla para el reporte](#capturas-de-pantalla-para-el-reporte)

---

## 1. Lo que vas a entregar

| # | Entregable (según el PDF) | Dónde queda | Estado en este repo |
|---|---|---|---|
| 1 | Código fuente del backend | GitHub (carpeta `backend/`) | ✅ Listo y probado (34 pruebas) |
| 2 | API desplegada en Render | URL pública `https://...onrender.com` | ⬜ La creas tú (Fase 3) |
| 3 | Base de datos funcional en Neon | `database/schema.sql` ejecutado en Neon | ⬜ La creas tú (Fase 1) |
| 4 | Workflow de n8n | `n8n/workflow-solicitudes.json` (se importa) | ✅ Listo, tú lo importas (Fase 6) |
| 5 | Google Forms + dashboard funcional | Google Workspace (se comparten con el profesor) | ⬜ Lo creas tú (Fases 5 y 7) |
| 6 | Documentación técnica | `docs/documentacion-tecnica.md` | ✅ Lista, ponle tu nombre |

**Documentos de apoyo incluidos:**

| Archivo | Para qué sirve |
|---|---|
| `docs/guia-despliegue-render-neon.md` | Clics y comandos exactos de Neon, Render, GitHub y OAuth de Google |
| `docs/guia-google-forms-sheets.md` | Preguntas exactas del formulario, fórmulas y gráficas del dashboard |
| `docs/pruebas-api.md` | Comandos curl/PowerShell/Postman para probar cada endpoint |
| `docs/documentacion-tecnica.md` | Documento formal que se entrega al profesor |

---

## 2. Antes de empezar: cuentas y herramientas

Marca cada casilla antes de avanzar:

- [ ] **Cuenta de Google** (con Gmail y Drive). Ideal que no sea la institucional si tiene restricciones de administrador.
- [ ] **GitHub** — [github.com](https://github.com) (cuenta gratuita).
- [ ] **Neon** — [neon.tech](https://neon.tech) (registro con GitHub/Google, plan *Free*, sin tarjeta).
- [ ] **Render** — [render.com](https://render.com) (registro con GitHub, plan *Free*, sin tarjeta).
- [ ] **n8n** — elige una opción (Fase 6):
  - *Opción A (más fácil):* **n8n Cloud** → [n8n.cloud](https://n8n.cloud), prueba gratuita de 14 días.
  - *Opción B (gratis, un poco más de trabajo):* **n8n autoalojado** con Docker Desktop o con `npx n8n`.
- [ ] **Git** instalado en tu computadora ([git-scm.com](https://git-scm.com/download/win)).
- [ ] **Python 3.12** instalado, solo si quieres probar la API en tu compu antes de desplegarla.
- [ ] **Postman** o **Insomnia** (opcional, para capturas de evidencias).

> ⚠️ **Regla de oro:** nunca subas el archivo `.env` ni tu `API_KEY` a GitHub.
> El `.gitignore` del proyecto ya los excluye.

---

## 3. Arquitectura del sistema

```
┌──────────────┐   respuestas    ┌──────────────────┐
│ Google Forms │ ──────────────► │ Google Sheets    │
│ (captura)    │                 │ (respaldo)       │
└──────────────┘                 └────────┬─────────┘
                                          │ fila nueva (trigger)
                                          ▼
                                 ┌──────────────────┐
                                 │      n8n         │
                                 │  (orquestador)   │
                                 └───┬───────┬──────┘
                     POST /api/solicitudes      │ Gmail
                     (X-API-Key)                ▼
                                          ┌──────────────┐
                                          │ Correo al    │
                                          │ solicitante  │
                                          │ con su folio │
                                          └──────────────┘
                                          │ actualiza la hoja
                                          ▼
┌──────────────┐   INSERT/SELECT  ┌──────────────────┐
│  API Flask   │ ◄──────────────► │ PostgreSQL en    │
│  (en Render) │                  │ Neon             │
└──────────────┘                  └──────────────────┘
        │
        └─► genera folio SOL-AAAA-NNNN
                                          ┌──────────────┐
                                          │ Dashboard en │
                                          │ Google Sheets│
                                          │ (3 gráficas) │
                                          └──────────────┘
```

**El flujo completo cuando alguien llena el formulario:**

1. La persona responde el Google Form.
2. Google guarda la respuesta en la hoja de cálculo.
3. n8n detecta la fila nueva (trigger de Google Sheets).
4. n8n normaliza los datos y hace `POST /api/solicitudes` a la API en Render con su `X-API-Key`.
5. La API valida los datos, inserta en Neon y el **trigger de PostgreSQL genera el folio**.
6. La API responde con el folio (ej. `SOL-2026-0001`).
7. n8n envía un **correo por Gmail** al solicitante con su folio.
8. n8n escribe el folio, el estado y la fecha en la hoja de cálculo.
9. El **dashboard** recalcula los totales y las gráficas.
10. El técnico consulta o actualiza el estado con `GET /api/solicitudes` y `PATCH .../estado`.

---

# Fase 1 — Base de datos en Neon (15 min)

📖 Detalle con clics exactos: `docs/guia-despliegue-render-neon.md` → *Fase 1*.

1. Entra a [console.neon.tech](https://console.neon.tech) → **Sign up** (con GitHub o Google).
2. **New Project**:
   - *Project name:* `solicitudes-soporte`
   - *Postgres version:* la que venga por defecto (16 o 17)
   - *Region:* la más cercana (`AWS US East` u `Oregon`)
3. Copia la **connection string**. En el panel del proyecto: **Connect** → pestaña
   *Connection string* → activa **Pooled connection** y copia la cadena completa.
   Debe verse así:
   ```
   postgresql://usuario:contraseña@ep-xxxx-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   📌 Guárdala en un lugar seguro: la usarás en la Fase 3.
4. En el menú izquierdo abre **SQL Editor**.
5. Abre el archivo `database/schema.sql` de este repositorio, copia **todo** su
   contenido, pégalo en el SQL Editor y presiona **Run**.
   Debe terminar sin errores y mostrar `solicitudes_registradas = 0`.
6. *(Opcional pero recomendado)* Repite el paso anterior con
   `database/datos_prueba.sql`. Crea 10 solicitudes de ejemplo con distintas
   categorías y prioridades para que el dashboard no esté vacío en la demo.
7. Verifica en el SQL Editor:
   ```sql
   SELECT folio, nombre, categoria, prioridad, estado FROM solicitudes ORDER BY id;
   ```
   Debes ver 10 filas (o 0 si no cargaste los datos de prueba) **con folio ya
   asignado**, aunque nunca lo escribiste.

✅ **Listo cuando:** la consulta anterior devuelve la tabla `solicitudes` con folios `SOL-AAAA-NNNN`.

> 🧠 **Por qué el folio se genera solo:** `schema.sql` crea un *trigger*
> (`trg_asignar_folio`) que, antes de insertar, toma el siguiente número de la
> secuencia y arma `SOL-2026-0001`. Así el folio es único aunque dos personas
> respondan al mismo tiempo, y funciona incluso si insertas a mano desde Neon.

---

# Fase 2 — Subir el proyecto a GitHub (10 min)

📖 Detalle: `docs/guia-despliegue-render-neon.md` → *Fase 2*.

1. Crea un repositorio nuevo en GitHub:
   - Nombre: `proyecto-solicitudes-soporte`
   - Visibilidad: **Public** (Render lo lee gratis)
   - **No** marques "Add a README" (ya tienes uno).

2. Abre una terminal en la carpeta `proyecto-solicitudes` y ejecuta:

   ```powershell
   git init
   git add .
   git commit -m "Proyecto segundo parcial: API de solicitudes"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/proyecto-solicitudes-soporte.git
   git push -u origin main
   ```

3. Recarga GitHub y confirma que aparecen `backend/`, `database/`, `docs/`,
   `n8n/`, `render.yaml` y `README.md`.

✅ **Listo cuando:** el código está en GitHub y **no** aparece ningún `.env`.

---

# Fase 3 — Desplegar la API en Render (20 min)

📖 Detalle: `docs/guia-despliegue-render-neon.md` → *Fase 3*.

1. Entra a [dashboard.render.com](https://dashboard.render.com) → **New +** → **Web Service**.
2. Conecta tu cuenta de GitHub y elige el repositorio del proyecto.
3. Captura:

   | Campo | Valor |
   |---|---|
   | **Name** | `api-solicitudes-trampas23` |
   | **Language / Runtime** | `Python 3` |
   | **Region** | `Oregon (US West)` |
   | **Branch** | `main` |
   | **Root Directory** | `backend` |
   | **Build Command** | `pip install -r requirements.txt` |
   | **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60` |
   | **Instance Type** | `Free` |
   | **Health Check Path** | `/health` |

   > 💡 También puedes usar **New + → Blueprint**, que lee el archivo
   > `render.yaml` de la raíz del repo y configura todo lo anterior solo.

4. Antes de crear el servicio (o en **Environment** después), agrega las
   variables de entorno:

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La connection string **pooled** de Neon (Fase 1) |
   | `API_KEY` | Una clave secreta que tú inventes (ver abajo) |
   | `ADMIN_EMAIL` | Tu correo, para las alertas de n8n |
   | `PYTHON_VERSION` | `3.12.6` (solo si no usaste el Blueprint) |

   Genera la `API_KEY` con:
   ```powershell
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   📌 **Anótala**: debe ser exactamente la misma que usarás en n8n.

5. Presiona **Create Web Service** y espera a que el estado sea **Live**
   (la primera vez tarda 2-4 minutos).
6. Copia la URL pública que aparece arriba: `https://api-solicitudes-trampas23.onrender.com`.

✅ **Listo cuando:** el servicio está en **Live** y al abrir `TU-URL/health` en el navegador ves `"base_datos": "conectada"`.

> ⚠️ **Plan gratuito de Render:** el servicio se duerme tras 15 minutos sin
> visitas. La primera petición después de dormido tarda **~50 segundos**.
> Entra a `/health` un minuto antes de tu demo y antes de probar n8n.

---

# Fase 4 — Probar la API (10 min)

📖 Comandos completos: `docs/pruebas-api.md`.

En PowerShell (ajusta las dos variables):

```powershell
$URL = "https://api-solicitudes-trampas23.onrender.com"
$API_KEY = "tu-clave-secreta"
$headers = @{ "X-API-Key" = $API_KEY; "Content-Type" = "application/json" }
```

1. **¿Está viva?**
   ```powershell
   Invoke-RestMethod -Uri "$URL/health" | ConvertTo-Json
   ```
2. **Registrar una solicitud de prueba:**
   ```powershell
   $cuerpo = @{
     nombre = "Ana López Hernández"; correo = "ana.lopez@escuela.edu.mx"
     telefono = "5551234567"; area = "Recursos Humanos"
     categoria = "Hardware"; prioridad = "Alta"
     descripcion = "La computadora de escritorio no enciende desde esta mañana."
     id_externo = "prueba-001"
   } | ConvertTo-Json

   Invoke-RestMethod -Uri "$URL/api/solicitudes" -Method Post -Headers $headers -Body $cuerpo |
     ConvertTo-Json -Depth 4
   ```
   Debes recibir **201** y un folio `SOL-2026-0001` generado por el sistema.
3. **Consultar:** `Invoke-RestMethod "$URL/api/solicitudes?limit=5"`
4. **Estadísticas:** `Invoke-RestMethod "$URL/api/estadisticas"`
5. **Seguridad:** repite el POST **sin** el header `X-API-Key`; debe responder `401`.

✅ **Listo cuando:** obtuviste un folio y `/health` dice `base_datos: conectada`.
(Si el POST falla, revisa la sección [Problemas comunes](#problemas-comunes-y-cómo-resolverlos)).

---

# Fase 5 — Google Forms + Google Sheets (25 min)

📖 Preguntas, opciones y fórmulas exactas: `docs/guia-google-forms-sheets.md`.

1. Ve a [forms.google.com](https://forms.google.com) → **En blanco**.
2. Título: `Solicitud de soporte técnico` y una descripción breve con las instrucciones.
3. Crea las **8 preguntas** con estos **títulos exactos** (se convierten en los
   encabezados de la hoja y el workflow de n8n los usa para mapear los datos):

   | # | Pregunta (título exacto) | Tipo | Obligatoria | Opciones / configuración |
   |---|---|---|---|---|
   | 1 | `Nombre completo` | Respuesta corta | **Sí** | — |
   | 2 | `Correo electrónico` | Respuesta corta | **Sí** | Validación: *Texto → Dirección de correo electrónico* |
   | 3 | `Teléfono de contacto` | Respuesta corta | No | 10 dígitos |
   | 4 | `Área o departamento` | Desplegable | No | Dirección · Recursos Humanos · Contabilidad · Ventas · Almacén · Sistemas · Otro |
   | 5 | `Categoría del problema` | Opción múltiple | **Sí** | Hardware · Software · Redes e Internet · Accesos y contraseñas · Impresoras · Otro |
   | 6 | `Prioridad de atención` | Opción múltiple | **Sí** | Baja · Media · Alta · Crítica |
   | 7 | `Nivel de afectación` | Escala lineal | No | 1 = Leve … 5 = No puedo trabajar |
   | 8 | `Descripción detallada del problema` | Párrafo | **Sí** | Mínimo 10 caracteres |

   > No agregues ni reordenes preguntas **después** de vincular la hoja: se
   > desalinean las columnas y las fórmulas del dashboard.

4. Pestaña **Respuestas** → icono de Google Sheets → **Vincular a Hojas de cálculo**
   → *Crear una hoja de cálculo nueva* → nombre `Solicitudes de soporte técnico - Registro`.
5. Renombra la pestaña de respuestas exactamente como `Respuestas de formulario 1`
   (el workflow de n8n trae ese nombre escrito). El formulario escribe las columnas
   **A–I**; agrega **4 columnas propias a la derecha** (J–M), sin borrar ni mover nada:
   `J Folio` · `K Estado` · `L Fecha de registro` · `M Correo enviado`.
6. Prueba el formulario una vez desde **Vista previa (ojo)**, confirma que la fila
   llega a la hoja y luego **borra esa respuesta de prueba**
   (**Respuestas → ⋯ → Eliminar todas las respuestas**) para iniciar limpio.

✅ **Listo cuando:** la fila 1 de la hoja tiene los encabezados A–M en el orden indicado.

> 📌 Ten a la mano el **ID de la hoja de cálculo**: está en la URL, entre
> `/d/` y `/edit`. Lo necesitarás en la Fase 6.

---

# Fase 6 — Automatización con n8n (40 min)

📖 Clics exactos de OAuth y credenciales: `docs/guia-despliegue-render-neon.md` → *Fases 4 y 5*.

**Paso 0 — Elige dónde correr n8n:**

| Opción | Ventajas | Consideraciones |
|---|---|---|
| **A. n8n Cloud** ([n8n.cloud](https://n8n.cloud)) | No instalas nada; credenciales de Google integradas; levanta en 2 min | Prueba de 14 días (suficiente para el proyecto) |
| **B. Autoalojado** (`npx n8n` o Docker) | 100% gratis, corre en tu compu | Debe estar encendido para que el workflow funcione; requiere tu propio cliente OAuth de Google Cloud |

Si eliges la **Opción B** y tienes Docker Desktop:
```powershell
docker run -it --rm --name n8n -p 5678:5678 -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n
```
Luego abre `http://localhost:5678`. Con `npx` (si tienes Node.js): `npx n8n`.

**Paso 1 — Credenciales de Google**
- *n8n Cloud:* en cada nodo de Google elige **Sign in with Google** y autoriza.
  (Los nodos de Google Sheets y Gmail usan el cliente OAuth de n8n, no necesitas
  crear nada en Google Cloud.)
- *Autoalojado:* crea un proyecto en [Google Cloud Console](https://console.cloud.google.com),
  habilita **Google Sheets API** y **Gmail API**, crea credenciales *OAuth client ID*
  (tipo *Web application*), agrega el redirect URI de tu n8n
  (`http://localhost:5678/rest/oauth2-credential/callback`) y pega el *Client ID*
  y *Client Secret* en la credencial de n8n.

**Paso 2 — Importar el workflow**
1. En n8n: **Overview → Import from File** (o arrastra el archivo al lienzo).
2. Selecciona `n8n/workflow-solicitudes.json`.
3. Revisa que aparezcan los nodos: **Google Sheets Trigger → Normalizar fila →
   Registrar en API → ¿Respuesta OK? → ¿Ya estaba registrada? → Correo al
   solicitante → Escribir folio en la hoja**, más la rama de error
   (**Alerta al administrador → Detener con error**) y el nodo *Duplicado: no reenviar*.

**Paso 3 — Configurar cada nodo** (3 valores clave repetidos en varios nodos):

| Qué | Dónde se saca |
|---|---|
| `API_URL` = `https://api-solicitudes-trampas23.onrender.com` | Fase 3 |
| `API_KEY` = tu clave | Fase 3 (la misma del header `X-API-Key`) |
| `Spreadsheet ID` = `1AbC...` | URL de la hoja (Fase 5) |
| Hoja / pestaña | `Respuestas de formulario 1` (renómbrala si tu Google está en inglés) |
| Correo del administrador | Tu correo (`ADMIN_EMAIL`) |

Asigna también las **credenciales de Google** en el trigger, en el nodo de
Google Sheets y en Gmail (botón *Credential → seleccionar*).

**Paso 4 — Probar**
1. Botón **Execute workflow** (o *Test workflow*).
2. Mientras escucha, llena el formulario real con otra respuesta de prueba.
3. Revisa que: el trigger muestre la fila, el HTTP Request responda `201` con
   `folio`, llegue el correo a tu Gmail y la hoja se actualice con `Folio`,
   `Estado` y `Fecha de registro`.
4. Si todo salió bien, activa el workflow con el interruptor **Active** (arriba a
   la derecha). Sin activarlo, solo funciona con ejecuciones manuales.

✅ **Listo cuando:** llenas el formulario y, sin tocar nada, ves en la hoja el folio y te llega el correo.

> 🔁 **Nota sobre duplicados:** el workflow calcula `id_externo` a partir de la
> `Marca temporal` de la respuesta (`form-10112026223541`). Si n8n reintenta,
> la API responde `200` con `"duplicado": true` y no se crea otra solicitud ni se
> reenvía el correo. (El evento *Row Added* del trigger no expone el número de fila,
> por eso se usa la marca temporal como llave estable.)

---

# Fase 7 — Dashboard en Google Sheets (20 min)

📖 Fórmulas exactas y pasos de las gráficas: `docs/guia-google-forms-sheets.md`.

1. En la hoja de respuestas, crea una **pestaña nueva** llamada `Dashboard`.
2. Arma los bloques con estas fórmulas (hoja en **español (México)**, separador `;`).
   El rango apunta a la pestaña de respuestas `'Respuestas de formulario 1'`:

   | Bloque | Fórmula base | Columna |
   |---|---|---|
   | **Total de solicitudes** | `=CONTARA('Respuestas de formulario 1'!A2:A)` | A (Marca temporal) |
   | **Folios generados** | `=CONTARA('Respuestas de formulario 1'!J2:J)` | J |
   | **Por categoría** | `=CONTAR.SI('Respuestas de formulario 1'!F2:F; "Hardware")`, etc. | F |
   | **Por prioridad** | `=CONTAR.SI('Respuestas de formulario 1'!G2:G; "Alta")`, etc. | G |
   | **Por estado** | `=CONTAR.SI('Respuestas de formulario 1'!K2:K; "Pendiente")`, etc. | K |

   > Si tu hoja está en inglés, usa `COUNTA`, `COUNTIF` y el separador `,`.
   > La guía trae las fórmulas con `QUERY` (equivalente `CONSULTA`) y `COUNTIFS`,
   > las celdas exactas y la tabla de equivalencias de funciones.

3. Selecciona la tabla de categorías → **Insertar → Gráfico** → tipo *barras*.
4. Repite con la tabla de prioridades → tipo *pastel* (o *columnas*).
5. Da formato: títulos, colores, y **formato condicional** para que `Crítica` y
   `Alta` se vean en rojo/amarillo.
6. (Extra que da puntos) Agrega tarjetas de *pendientes*, *en proceso* y
   *últimas 24 horas*, y una tabla con las últimas solicitudes usando `QUERY`.

✅ **Listo cuando:** la pestaña Dashboard muestra el total y las 3 gráficas con datos reales.

---

# Fase 8 — Documentación y entrega (15 min)

1. Abre `docs/documentacion-tecnica.md` y personaliza:
   - Tu nombre, matrícula, fecha y grupo en la portada.
   - Si usaste n8n Cloud o autoalojado (indícalo en la arquitectura).
2. Agrega las **capturas de pantalla** (lista en la sección 16).
3. Exporta el workflow de n8n: en el workflow → menú **⋯ → Download** y guarda el
   JSON actualizado en `n8n/` (evidencia de la versión final).
4. Comparte con el profesor (permiso **Lector**):
   - El **Google Forms** (enviar el enlace público).
   - La **hoja de cálculo** completa (respuestas + dashboard).
   - El **repositorio de GitHub** (público).
   - La **URL de Render** y el **JSON del workflow**.
5. Actualiza el README con tu nombre y la URL real del servicio:
   ```powershell
   git add .
   git commit -m "Entrega final: evidencias y documentación"
   git push
   ```

✅ **Checklist de entrega:**

- [ ] Código del backend en GitHub.
- [ ] API desplegada en Render y funcionando (`/health` conectada).
- [ ] Base de datos en Neon con la tabla `solicitudes` y folios generados.
- [ ] Workflow de n8n activo y exportado (`.json`).
- [ ] Google Forms vinculado a Sheets y funcionando de punta a punta.
- [ ] Dashboard con total, por categoría y por prioridad.
- [ ] Documentación técnica con tu nombre y capturas.
- [ ] Enlaces compartidos/enviados al profesor.

---

## Planes de trabajo según tu tiempo

### Si tienes un día (≈4 horas seguidas)
| Bloque | Fases | Tiempo |
|---|---|---|
| Mañana | 1 → 5 | 2 h |
| Tarde | 6 → 8 | 2 h |

### Si tienes dos días
| Día | Fases | Tiempo |
|---|---|---|
| Día 1 | 1, 2, 3, 4 (todo el backend en línea y probado) | 1 h 15 min |
| Día 2 | 5, 6, 7, 8 (Google, n8n, dashboard y entrega) | 1 h 45 min |

### Si solo tienes unas horas
Prioriza en este orden (es lo que más pesa en la evaluación):
1. Base de datos + API desplegada y probada (Fases 1-4).
2. Forms + Sheet vinculados (Fase 5).
3. n8n registrando y notificando (Fase 6).
4. Dashboard (Fase 7).
5. Documentación y capturas (Fase 8).

---

## Problemas comunes y cómo resolverlos

| Síntoma | Causa probable | Solución |
|---|---|---|
| `/health` dice `"base_datos": "desconectada"` | `DATABASE_URL` mal copiada o Neon suspendido | Vuelve a copiar la cadena **pooled** completa; verifica que empiece con `postgresql://` y termine en `sslmode=require`; guarda y redespliega en Render |
| POST responde `503` | Fallo de conexión a la BD | Revisa *Logs* en Render; suele ser `DATABASE_URL` |
| POST responde `401` | Falta/incorrecta `X-API-Key` | Verifica que `API_KEY` en Render sea idéntica a la del nodo HTTP de n8n (sin espacios) |
| `404` al probar `/solicitudes` | Ruta mal escrita | Es `/api/solicitudes` (con `/api`) |
| `500` al insertar | Falta ejecutar `schema.sql` o el trigger | Vuelve a ejecutar `database/schema.sql` en Neon (es idempotente) |
| La primera petición tarda ~50 s | Render free se durmió | Normal. Entra a `/health` un minuto antes de la demo |
| n8n no dispara al llenar el formulario | Workflow inactivo o trigger mal apuntado | Activa el workflow; revisa *Spreadsheet ID*, nombre de pestaña y que la credencial tenga permiso |
| El correo no llega | Gmail sin autorización o en spam | Reautoriza la credencial de Gmail; revisa Spam; el remitente debe ser la cuenta autorizada |
| El folio sale como `null` en la hoja | El nodo de Sheets corre antes de la respuesta de la API | Asegúrate de que el nodo de actualizar hoja esté *después* del HTTP Request y use `{{ $json.data.folio }}` |
| Folio repetido o solicitud duplicada | Reintento de n8n sin `id_externo` | El workflow lo genera con la `Marca temporal` (`form-<marca temporal sin signos>`); no lo cambies a mano |
| Dashboard no suma | Rangos apuntan a otra pestaña/columna | Ajusta los rangos; recuerda que Categoría es la columna F y Prioridad la G |
| n8n Cloud dice que caducó la prueba | 14 días | Exporta el workflow, crea otro trial con otra cuenta o cambia a autoalojado |
| El deploy falla con `error: command 'gcc' failed` o `pg_config executable not found` | Render usó Python 3.14 (su versión por defecto actual) y no encuentra el wheel de `psycopg2-binary==2.9.10` | Agrega la variable `PYTHON_VERSION` = `3.12.6` en **Environment** y redespliega (el `render.yaml` del repo ya la incluye) |
| `permission denied` al hacer `git push` | Credenciales de GitHub | Usa un *Personal Access Token* como contraseña o el login por navegador de Git Credential Manager |

---

## Estructura del proyecto

```
proyecto-solicitudes/
├── README.md                        ← esta guía
├── render.yaml                      ← despliegue automático en Render (raíz del repo)
├── .gitignore
├── backend/
│   ├── app.py                       ← API Flask (endpoints, validación, auth)
│   ├── database.py                  ← pool de conexiones a Neon + errores
│   ├── utilidades.py                ← validación y normalización de datos
│   ├── test_smoke.py                ← 34 pruebas automatizadas (sin Neon)
│   ├── requirements.txt             ← dependencias
│   ├── .env.example                 ← variables de entorno de ejemplo
│   └── .python-version
├── database/
│   ├── schema.sql                   ← tabla, triggers de folio, índices, vistas
│   └── datos_prueba.sql             ← 10 solicitudes de ejemplo para la demo
├── n8n/
│   └── workflow-solicitudes.json    ← workflow importable en n8n
└── docs/
    ├── documentacion-tecnica.md     ← entregable formal del proyecto
    ├── guia-despliegue-render-neon.md
    ├── guia-google-forms-sheets.md
    └── pruebas-api.md
```

### Probar la API en tu computadora (opcional)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # edita DATABASE_URL y API_KEY
python test_smoke.py -v         # 34 pruebas automáticas
python app.py                   # http://localhost:5000
```

---

## Cómo se cumple cada requisito del PDF

| # | Requisito | Cómo se cumple | Dónde verlo |
|---|---|---|---|
| 1 | API REST para registrar y consultar solicitudes | Flask con `POST/GET /api/solicitudes`, `GET /api/solicitudes/<folio>`, `PATCH .../estado`, `GET /api/estadisticas` | `backend/app.py` |
| 2 | Base de datos PostgreSQL en Neon | Proyecto Neon + `schema.sql` (tabla, secuencia, triggers, índices, vistas) | `database/schema.sql` |
| 3 | API desplegada en Render | `render.yaml` + guía de despliegue; servicio con health check | `render.yaml`, Fase 3 |
| 4 | Google Forms vinculado a Google Sheets | Form de 8 preguntas + vinculación a hoja de respuestas | `docs/guia-google-forms-sheets.md`, Fase 5 |
| 5 | n8n automatiza el registro en la API y BD | Trigger de Sheets → Code → HTTP Request → API → PostgreSQL | `n8n/workflow-solicitudes.json`, Fase 6 |
| 6 | Generar folios y notificar por Gmail | Trigger `trg_asignar_folio` en PostgreSQL + nodo Gmail con el folio | `database/schema.sql`, Fase 6 |
| 7 | Pestaña con dashboard (total, categoría, prioridad) | Pestaña `Dashboard` con `COUNTIF`/`QUERY` y 3 gráficas | `docs/guia-google-forms-sheets.md`, Fase 7 |

---

## Capturas de pantalla para el reporte

Toma estas capturas (te ahorran puntos en la documentación):

1. Neon: pestaña **Tables** mostrando `solicitudes` con folios.
2. Neon: SQL Editor con el resultado de `SELECT * FROM solicitudes;`.
3. Render: servicio en estado **Live** con su URL.
4. Navegador: `TU-URL/health` con `"base_datos": "conectada"`.
5. Navegador: `TU-URL/` con el índice de endpoints.
6. Postman o terminal: `POST` devolviendo `201` con el folio.
7. Postman: colección ejecutada con todas las pruebas en verde.
8. Google Forms: vista previa con las 8 preguntas.
9. Google Sheets: hoja de respuestas con la fila nueva + folio escrito por n8n.
10. n8n: lienzo del workflow completo.
11. n8n: **Executions** con una ejecución exitosa (nodos en verde).
12. Gmail: correo recibido con el folio.
13. Google Sheets: dashboard con las 3 gráficas.
14. GitHub: repositorio con la estructura del proyecto.

---

## Recursos oficiales

- Flask: [flask.palletsprojects.com](https://flask.palletsprojects.com/)
- Neon: [neon.tech/docs](https://neon.tech/docs)
- Render: [render.com/docs](https://render.com/docs)
- n8n: [docs.n8n.io](https://docs.n8n.io/)
- Google Forms: [support.google.com/docs/answer/6281888](https://support.google.com/docs/answer/6281888)

---

**Nota académica:** este proyecto es una plantilla funcional de referencia.
Personaliza la documentación, entiende cada parte del flujo (te pueden preguntar
en la presentación) y cita este repositorio si lo usas como base.
