# Documentación técnica

## Sistema automatizado de gestión de solicitudes de soporte técnico

| | |
|---|---|
| **Título del documento** | Documentación técnica del sistema |
| **Materia** | Programación en ambiente cliente servidor |
| **Proyecto** | Sistema automatizado de gestión de solicitudes de soporte técnico (segundo parcial) |
| **Autor** | Nombre del alumno |
| **Profesor** | ______________________________ |
| **Institución** | ______________________________ |
| **Fecha** | Noviembre de 2026 |
| **Versión del documento** | 1.0 |
| **Versión del sistema** | 1.0.0 |

---

## Control de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | Noviembre de 2026 | Nombre del alumno | Versión inicial: arquitectura, modelo de datos, referencia de API, seguridad, pruebas y conclusiones. |

---

## Contenido

1. [Introducción](#1-introducción)
2. [Objetivos](#2-objetivos)
3. [Alcance y limitaciones](#3-alcance-y-limitaciones)
4. [Arquitectura del sistema](#4-arquitectura-del-sistema)
5. [Modelo de datos](#5-modelo-de-datos)
6. [Referencia de la API REST](#6-referencia-de-la-api-rest)
7. [Seguridad](#7-seguridad)
8. [Pruebas](#8-pruebas)
9. [Conclusiones](#9-conclusiones)
10. [Mejoras futuras](#10-mejoras-futuras)
11. [Referencias](#11-referencias)
12. [Apéndices](#12-apéndices)

---

## 1. Introducción

El presente documento describe el diseño, la implementación y la operación del **Sistema automatizado de gestión de solicitudes de soporte técnico**, desarrollado para la materia *Programación en ambiente cliente servidor* como proyecto del segundo parcial.

El sistema atiende un problema cotidiano en una institución educativa: las solicitudes de soporte técnico (equipos que no encienden, fallas de software, problemas de red, accesos y contraseñas, impresoras, etc.) suelen recibirse por mensajes informales, correo o de viva voz, sin un registro único, sin folio de seguimiento y sin visibilidad del estado de atención. La solución propuesta automatiza el ciclo completo de captura, registro, notificación y seguimiento:

1. El usuario llena un **Google Forms**.
2. Las respuestas se guardan automáticamente en una **hoja de Google Sheets**.
3. **n8n** detecta la fila nueva, normaliza los datos y llama a la **API REST**.
4. La API valida la información, la guarda en **PostgreSQL (Neon)** y devuelve un **folio** generado por la base de datos.
5. n8n envía un correo de confirmación al solicitante con su folio y actualiza la hoja.
6. Un **dashboard** construido en otra pestaña de la misma hoja muestra los indicadores de gestión.

La API está implementada en **Python 3.12.6 + Flask 3.1.0**, se sirve con **Gunicorn 23.0.0** en **Render** (plan Free) y persiste en **PostgreSQL en Neon** (plan Free; versión 15 o superior, el proyecto usa la versión por defecto 17). La automatización se implementa con **n8n Cloud**. El documento está organizado para que cualquier integrante del equipo —o el profesor— pueda entender la arquitectura, reproducir el despliegue, consumir la API y validar el funcionamiento.

> **Documentos complementarios:** `README.md` (descripción general y ejecución local), `docs/guia-despliegue-render-neon.md` (paso a paso de despliegue), `docs/guia-google-forms-sheets.md` (formulario, hoja y dashboard) y `docs/pruebas-api.md` (evidencias de pruebas con curl y PowerShell).

---

## 2. Objetivos

### 2.1 Objetivo general

Diseñar, implementar y desplegar en la nube un sistema automatizado de gestión de solicitudes de soporte técnico que, a partir de un formulario de Google, registre cada solicitud en una base de datos PostgreSQL mediante una API REST propia, le asigne un folio único de seguimiento y notifique automáticamente al solicitante, manteniendo un dashboard actualizado para la gestión del área de soporte.

### 2.2 Objetivos específicos

1. **Diseñar el modelo de datos** de las solicitudes de soporte con restricciones de integridad (dominios válidos para categoría, prioridad y estado; validación de correo y de longitudes mínimas) en PostgreSQL.
2. **Implementar una API REST en Flask** con endpoints para crear, consultar, filtrar, actualizar el estado y calcular estadísticas de las solicitudes, aplicando validación y normalización de datos de entrada.
3. **Generar el folio de seguimiento de forma automática y segura** mediante una secuencia y un trigger `BEFORE INSERT` en la base de datos, con formato `SOL-AAAA-NNNN` y protección ante concurrencia.
4. **Proteger las operaciones de escritura** con una API key enviada en el header `X-API-Key`, comparada en tiempo constante, y con validación estricta del cuerpo JSON.
5. **Automatizar el flujo de punta a punta con n8n**: detección de la respuesta del formulario, normalización, llamada a la API, manejo de éxito/error, envío de correos con Gmail y actualización de la hoja de cálculo.
6. **Desplegar el sistema en servicios en la nube** de nivel gratuito (Render + Neon) dejando evidencia de health checks, pruebas y configuración reproducible mediante `render.yaml`.
7. **Documentar y probar** la solución con pruebas automatizadas de humo (34 casos, sin base de datos) y una batería de pruebas funcionales con curl, además de esta documentación técnica y las guías de despliegue y operación.

---

## 3. Alcance y limitaciones

### 3.1 Alcance funcional

| # | Funcionalidad | Estado | Descripción |
|---|---|---|---|
| F1 | Captura de solicitudes | Incluida | Formulario de Google con campos controlados y validación de obligatoriedad. |
| F2 | Registro automatizado | Incluida | n8n detecta la fila nueva y registra la solicitud vía API sin intervención humana. |
| F3 | Folio de seguimiento | Incluida | Generado por la base de datos con formato `SOL-AAAA-NNNN`, único y consecutivo. |
| F4 | Validación y normalización | Incluida | Correo, longitudes, teléfono, categorías/prioridades/estados con alias y sin distinción de acentos. |
| F5 | Idempotencia | Incluida | El campo `id_externo` evita duplicados cuando n8n reintenta una ejecución. |
| F6 | Notificación al solicitante | Incluida | Correo HTML con folio, categoría, prioridad y estado mediante Gmail API. |
| F7 | Aviso al administrador | Incluida | Rama de error del workflow que notifica fallas de registro. |
| F8 | Consulta y filtros | Incluida | Listado paginado con filtros por categoría, prioridad, estado, correo, texto libre y orden. |
| F9 | Consulta individual | Incluida | Búsqueda por folio o por id numérico. |
| F10 | Actualización de estado | Incluida | `PATCH` para mover la solicitud entre Pendiente, En proceso, Resuelto y Cerrado. |
| F11 | Estadísticas | Incluida | Totales por categoría, prioridad, estado y últimas 24 horas. |
| F12 | Dashboard de gestión | Incluida | Pestaña de Google Sheets con tablas y gráficas alimentadas por fórmulas. |
| F13 | Health check | Incluida | `GET /health` reporta estado del servicio y de la base de datos. |
| F14 | Documentación | Incluida | README, documentación técnica, guías de despliegue, Forms/Sheets y pruebas. |

### 3.2 Alcance técnico

| Capa | Tecnología | Versión / configuración |
|---|---|---|
| Front-end de captura | Google Forms | Servicio en la nube de Google |
| Hoja de cálculo y dashboard | Google Sheets | Fórmulas, tablas y gráficas |
| Orquestación | n8n Cloud | Workflow importable `n8n/workflow-solicitudes.json` (10 nodos + nota de configuración) |
| Lenguaje | Python | 3.12.6 (`backend/.python-version`) |
| Framework web | Flask | 3.1.0 |
| CORS | Flask-CORS | 5.0.0 |
| Servidor WSGI | Gunicorn | 23.0.0, 2 workers, timeout 60 s |
| Driver de base de datos | psycopg2-binary | 2.9.10 |
| Variables de entorno | python-dotenv | 1.0.1 |
| Base de datos | PostgreSQL (Neon) | 17, región AWS us-west-2 (Oregon) |
| Hosting de la API | Render | Web Service, plan Free, región Oregon |
| Correo | Gmail API | OAuth 2.0 |
| Control de versiones | Git + GitHub | Rama `main` |
| Pruebas | unittest + `Flask.test_client` | 34 pruebas de humo (`backend/test_smoke.py`) |

### 3.3 Limitaciones conocidas

| # | Limitación | Impacto | Mitigación / trabajo futuro |
|---|---|---|---|
| L1 | Solo hay una API key compartida; no hay usuarios, roles ni sesiones | Cualquier cliente con la llave puede escribir; no se distingue quién hizo cada cambio | Agregar autenticación con JWT/OAuth2 y roles (ver sección 10) |
| L2 | Los endpoints `GET` son públicos por diseño | Cualquier persona con la URL puede leer nombres, correos y descripciones (datos personales) | Restringir lecturas con API key o protegerlas con un proxy autenticado |
| L3 | No hay límite de peticiones (rate limiting) | La API podría saturarse o usarse para fuerza bruta de la llave | Implementar límites por IP/clave en Flask o en un proxy |
| L4 | Sin auditoría detallada de cambios | No hay historial de quién cambió el estado | Tabla `historial_estados` o `auditoria` |
| L5 | Plan Free de Render | El servicio se duerme tras ~15 min y el primer request tarda 50 s o más | Aceptado en el proyecto; se documenta el cold start y el timeout de n8n a 90 s |
| L6 | Plan Free de Neon | Suspensión de cómputo por inactividad y límites de almacenamiento/conexiones | Conexión *pooled*, pool de 1 a 8 conexiones y reconexión automática |
| L7 | n8n Cloud en periodo de prueba | La prueba dura 14 días; después requiere plan de pago o n8n autoalojado | Exportar el workflow y documentar la alternativa con Docker |
| L8 | Sin adjuntos ni archivos | El formulario solo captura texto | Integrar almacenamiento de objetos (S3/Drive) en una versión futura |
| L9 | Sin migraciones automáticas | El esquema se ejecuta a mano en el SQL Editor de Neon | Adoptar Alembic o un runner de migraciones |
| L10 | Pruebas automatizadas con dobles de prueba | No validan la conexión real a Neon ni el workflow de n8n | Agregar pruebas de integración contra una rama de Neon de pruebas |
| L11 | Una sola región y un solo proveedor de base de datos | Sin alta disponibilidad ni réplica geográfica | Fuera del alcance de un proyecto escolar |
| L12 | El dashboard no lee la API en tiempo real | Depende de las fórmulas de Google Sheets y de que la hoja esté sincronizada | Dashboard web que consuma `GET /api/estadisticas` |

> **Nota sobre datos personales:** el sistema almacena nombre, correo, teléfono y área del solicitante. En producción institucional se requeriría aviso de privacidad, control de acceso a la hoja de cálculo y una política de retención. Para el proyecto escolar se usan datos ficticios (`@ejemplo.com`, `@escuela.edu.mx`).

---

## 4. Arquitectura del sistema

### 4.1 Diagrama de arquitectura

```mermaid
flowchart TB
    subgraph GW["Google Workspace"]
        F["Google Forms<br/>Formulario de soporte técnico"]
        S["Google Sheets · pestaña Respuestas<br/>una fila por solicitud"]
        DASH["Google Sheets · pestaña Dashboard<br/>tablas y gráficas"]
    end

    subgraph N8N["n8n Cloud · workflow-solicitudes.json"]
        TRIG["Google Sheets Trigger<br/>Row Added · revisa cada minuto"]
        NORM["Normalizar fila · Code"]
        HTTP["Registrar en API · HTTP Request"]
        COND{"¿Respuesta OK?"}
        GMAIL1["Correo al solicitante · Gmail"]
        SHEETSU["Escribir folio en la hoja · Google Sheets"]
        GMAIL2["Alerta al administrador · Gmail"]
    end

    subgraph RW["Render · plan Free · Oregon"]
        GUN["Gunicorn · 2 workers · timeout 60 s"]
        APP["Flask API · app.py"]
        AUTH["Decorador requiere_api_key<br/>X-API-Key"]
        VAL["Validación · utilidades.py"]
        DATA["Capa de datos · database.py<br/>pool de conexiones"]
    end

    subgraph NE["Neon · PostgreSQL"]
        TB[("Tabla solicitudes<br/>trigger de folio")]
        VISTAS["Vistas de estadísticas"]
    end

    USU["Solicitante"] -->|"llena el formulario"| F
    F -->|"respuestas"| S
    S -->|"fila nueva"| TRIG
    TRIG --> NORM --> HTTP
    HTTP -->|"HTTPS · JSON · X-API-Key"| GUN
    GUN --> APP --> AUTH --> VAL --> DATA
    DATA -->|"TLS · sslmode=require"| TB
    DATA -->|"JSON 201/200/4xx/5xx"| HTTP
    HTTP --> COND
    COND -->|"sí · 201 o 200"| GMAIL1
    COND -->|"sí · 201 o 200"| SHEETSU
    COND -->|"no · error"| GMAIL2
    SHEETSU -->|"folio · estado · fecha"| S
    S -->|"fórmulas y gráficas"| DASH
    GMAIL1 -->|"Gmail API"| USU
    GMAIL2 -->|"Gmail API"| ADM["Administrador de soporte"]
    VISTAS -.->|"consulta directa opcional"| TB
```

### 4.2 Componentes

| Componente | Tecnología | Función principal | Dónde se ejecuta | Artefacto de configuración |
|---|---|---|---|---|
| Formulario de captura | Google Forms | Recibe los datos del solicitante y valida campos obligatorios | Google Workspace | Formulario compartido (`forms.gle/...`) |
| Hoja de respuestas | Google Sheets | Almacena una fila por respuesta del formulario | Google Workspace | Hoja de cálculo `<SPREADSHEET_ID>` |
| Dashboard | Google Sheets | Totales y gráficas por categoría, prioridad y estado | Pestaña de la misma hoja | Fórmulas y gráficas de la hoja |
| Orquestador | n8n Cloud | Detecta filas nuevas (Google Sheets Trigger), normaliza (Normalizar fila), llama a la API (Registrar en API), envía correos y actualiza la hoja | n8n Cloud | `n8n/workflow-solicitudes.json` |
| API REST | Flask 3.1.0 + Flask-CORS | Expone los endpoints, valida, autoriza y serializa JSON | Render | `backend/app.py` |
| Autenticación | Decorador `requiere_api_key` | Verifica el header `X-API-Key` con `secrets.compare_digest` | Render | `backend/app.py`, variable `API_KEY` |
| Validación y normalización | Módulo `utilidades.py` | Valida longitudes, correo, teléfono; normaliza categorías, prioridades y estados | Render | `backend/utilidades.py` |
| Capa de datos | `psycopg2-binary` + `SimpleConnectionPool` | Ejecuta SQL parametrizado, traduce errores a mensajes claros, administra el pool | Render | `backend/database.py` |
| Servidor WSGI | Gunicorn 23.0.0 | Sirve la aplicación Flask en `0.0.0.0:$PORT` con 2 workers | Render | `render.yaml` |
| Base de datos | PostgreSQL (Neon; 15+) | Persiste solicitudes, genera folios, mantiene índices y vistas | Neon (AWS us-west-2) | `database/schema.sql` |
| Datos de demostración | SQL | 10 solicitudes de ejemplo para el dashboard | Neon | `database/datos_prueba.sql` |
| Correo saliente | Gmail API (OAuth 2.0) | Notifica al solicitante y al administrador | n8n Cloud / Google | Credenciales OAuth en n8n |
| Pruebas | unittest + `test_client` | 34 pruebas de humo sin base de datos | Local | `backend/test_smoke.py` |
| Documentación | Markdown | README y guías | GitHub | `docs/` |

### 4.3 Flujo completo de una solicitud

El siguiente es el recorrido de una solicitud desde que el usuario llena el formulario hasta que el dashboard refleja el registro. Son 15 pasos:

1. **Captura.** El solicitante abre el enlace del Google Forms y llena nombre, correo, teléfono (opcional), área, categoría, prioridad y descripción de la falla.
2. **Almacenamiento de la respuesta.** Google Forms guarda la respuesta como una **fila nueva** en la hoja de cálculo vinculada, en la pestaña de respuestas, con una marca temporal.
3. **Detección.** El nodo **Google Sheets Trigger** del workflow de n8n revisa la hoja aproximadamente cada minuto y detecta la fila nueva (`Row Added`).
4. **Normalización.** El nodo **Normalizar fila** (`Code`) mapea los encabezados de la hoja (`Nombre completo`, `Correo electrónico`, `Teléfono de contacto`, `Área o departamento`, `Categoría del problema`, `Prioridad de atención`, `Descripción detallada del problema`) a las llaves JSON que espera la API (`nombre`, `correo`, `telefono`, `area`, `categoria`, `prioridad`, `descripcion`), normaliza categorías y prioridades con sus propios alias y genera un `id_externo` estable con la forma `form-<marca temporal>` para que los reintentos no dupliquen registros. La columna adicional `Nivel de afectación` (escala 1 a 5 del formulario) se conserva en la hoja para el dashboard, pero no forma parte del contrato de la API.
5. **Llamada a la API.** El nodo **Registrar en API** (`HTTP Request`) envía `POST https://api-solicitudes-trampas23.onrender.com/api/solicitudes` con `Content-Type: application/json`, el header `X-API-Key` y el cuerpo completo que produjo la normalización. Si el servicio de Render está dormido, esta petición lo despierta (cold start de 50 s o más); el JSON trae timeout de 60 s y la guía de despliegue recomienda subirlo a 90 s.
6. **Recepción en Render.** Gunicorn recibe la petición HTTPS y la entrega a uno de los 2 workers de Flask; Flask enruta a la función `crear_solicitud()`.
7. **Autenticación.** El decorador `requiere_api_key` compara el header `X-API-Key` con la variable de entorno `API_KEY` usando `secrets.compare_digest` (tiempo constante). Si falta o no coincide, devuelve `401`.
8. **Validación.** `utilidades.validar_solicitud()` limpia espacios, valida longitudes, formato de correo y teléfono, y normaliza categoría, prioridad y estado (acepta mayúsculas, minúsculas, sin acentos y alias como `redes`, `urgente`, `cerrada`). Si hay errores, responde `400` con el detalle por campo y el workflow toma la rama de error.
9. **Inserción.** `app.py` arma un `INSERT ... ON CONFLICT (id_externo) DO NOTHING RETURNING *` y lo envía a través de `database.py`, que obtiene una conexión del pool (`SimpleConnectionPool`, 1 a 8 conexiones) hacia Neon usando TLS (`sslmode=require`).
10. **Folio automático.** Antes de guardar la fila, el trigger `trg_asignar_folio` ejecuta `asignar_folio()`, que consume la secuencia `solicitudes_folio_seq` y construye el folio `SOL-<año>-<consecutivo de 4 dígitos>`; las demás columnas toman sus valores por defecto (`estado = 'Pendiente'`, `correo_enviado = false`, `fecha_registro = NOW()`).
11. **Respuesta.** La base devuelve la fila insertada; Flask la serializa (fechas en ISO 8601, zona `America/Mexico_City`) y responde `201 Created` con `{"ok": true, "mensaje": "Solicitud registrada correctamente.", "data": {...}}`.
12. **Idempotencia.** Si el `id_externo` ya existía, el `ON CONFLICT` no inserta nada; la API busca la solicitud existente y responde `200` con `"duplicado": true` y el **mismo folio**. El nodo **¿Ya estaba registrada?** detecta esa bandera y termina en **Duplicado: no reenviar** para no enviar un segundo correo.
13. **Correo al solicitante.** El nodo **¿Respuesta OK?** evalúa la respuesta como exitosa y el nodo **Correo al solicitante** (`Gmail`) envía al correo capturado un mensaje HTML con el folio, la categoría, la prioridad, el estado inicial y la fecha de registro.
14. **Actualización de la hoja.** El nodo **Escribir folio en la hoja** (`Google Sheets`, operación `appendOrUpdate`) localiza la fila del formulario por la columna `Marca temporal` y escribe `Folio`, `Estado`, `Fecha de registro` y `Correo enviado = Sí` en las columnas de gestión.
15. **Dashboard y consulta.** Las fórmulas y gráficas de la pestaña Dashboard se recalculan con la nueva fila. El área de soporte puede consultar el detalle por `GET /api/solicitudes/<folio>` y mover el estado con `PATCH /api/solicitudes/<folio>/estado`. Si algo falla en cualquier punto, los nodos **Alerta al administrador** (`Gmail`) y **Detener con error** (`Stop and Error`) avisan del problema y marcan la ejecución como fallida.

### 4.4 Decisiones de diseño

| Decisión | Alternativas consideradas | Justificación |
|---|---|---|
| **Folio generado por la base de datos con secuencia + trigger** | Generarlo en Flask con `MAX(folio)+1` o con UUID | Una secuencia es atómica y segura ante concurrencia; el trigger garantiza el formato aun si se inserta por SQL. Además, el folio es legible y ordenable. |
| **API REST propia en Flask** | Escribir directo de n8n a PostgreSQL o usar una hoja como base | La API centraliza validación, autenticación y reglas del negocio; permite reutilizar el sistema desde cualquier cliente y demuestra el modelo cliente-servidor. |
| **Idempotencia con `id_externo` y `ON CONFLICT`** | Confiar en que n8n no reintentará | n8n puede repetir una ejecución por errores de red o cold start; el `UNIQUE` + `ON CONFLICT` evita duplicados de forma transparente. |
| **Trigger de Google Sheets (polling) en lugar de webhook** | Webhook de Google Forms hacia n8n | El trigger de n8n no requiere publicar la app de Google ni exponer un endpoint; su latencia de ~1 min es aceptable. |
| **Normalizar valores en la API** | Exigir al formulario valores exactos | El formulario puede enviar variantes; la normalización tolera mayúsculas, acentos y alias y mantiene los CHECK de la base satisfechos. |
| **Dashboard dentro de Google Sheets** | Dashboard web propio | Cero infraestructura adicional, actualización inmediata con las respuestas y demuestra el uso de fórmulas y gráficas requerido por la materia. |
| **Neon (PostgreSQL administrado) + Render Free** | PostgreSQL local o Render Postgres de pago | Neon Free no expira y ofrece TLS y pooling; Render Free permite publicar la API con HTTPS sin costo. |
| **`/health` siempre HTTP 200** | Devolver 503 cuando la base falla | Render reiniciaría el servicio si el health check falla aunque el proceso esté sano; el estado real de la base se reporta en el campo `base_datos`. |
| **Dos workers de Gunicorn** | Un solo worker o más workers | Balance entre tolerancia a cold start, memoria del plan Free y simplicidad; 2 workers atienden el volumen de un proyecto escolar. |
| **Pruebas de humo con dobles de prueba** | Pruebas que requieran Neon en CI | Permiten verificar endpoints y validaciones sin credenciales ni red, y corren en cualquier computadora con Python. |

### 4.5 Workflow de n8n implementado

El archivo `n8n/workflow-solicitudes.json` contiene 11 elementos (1 nota de configuración y 10 nodos), con `executionOrder: v1`, zona horaria `America/Mexico_City` y `active: false` (el workflow se activa manualmente al terminar la configuración).

| # | Nodo | Tipo | Función | Configuración clave |
|---|---|---|---|---|
| 1 | Configuración | Sticky Note | Nota con los pasos y los marcadores por reemplazar | `PEGA_AQUI_EL_ID_DEL_SPREADSHEET`, `TU-SERVICIO`, `TU-API-KEY-AQUI`, `soporte-admin@ejemplo.com` |
| 2 | Google Sheets Trigger | Google Sheets Trigger | Dispara con cada fila nueva de la hoja | Pestaña `Respuestas de formulario 1`, evento `rowAdded`, encabezados en la fila 1, credencial **Google Sheets Trigger OAuth2 API** |
| 3 | Normalizar fila | Code | Mapea las columnas del formulario al JSON de la API, normaliza categoría/prioridad y genera `id_externo` (`form-<marca temporal>`) | Objeto `COLUMNAS` con los encabezados exactos del Form |
| 4 | Registrar en API | HTTP Request | Envía el `POST` a Render | Header `X-API-Key`, cuerpo `={{ JSON.stringify($json) }}`, timeout 60 000 ms, `neverError: true`, salida de error activa |
| 5 | ¿Respuesta OK? | IF | Valida `ok` y que exista `data.folio` | `true` → ¿Ya estaba registrada?; `false` → Alerta al administrador |
| 6 | ¿Ya estaba registrada? | IF | Detecta la bandera `duplicado` | `true` → Duplicado: no reenviar; `false` → Correo al solicitante |
| 7 | Correo al solicitante | Gmail | Envía el folio y el resumen al solicitante | `To: {{ $json.data.correo }}`, cuerpo HTML con `data.*` |
| 8 | Escribir folio en la hoja | Google Sheets | `appendOrUpdate` localizando la fila por `Marca temporal` | Escribe `Folio`, `Estado`, `Fecha de registro` y `Correo enviado = Sí` |
| 9 | Duplicado: no reenviar | NoOp | Termina la ejecución sin reenviar correo | — |
| 10 | Alerta al administrador | Gmail | Avisa del error con el motivo, el solicitante y la fecha | `To: <CORREO_ADMIN>` (reemplazar el valor de ejemplo) |
| 11 | Detener con error | Stop and Error | Marca la ejecución como fallida después de la alerta | Mensaje de error editable |

**Conexiones principales:** `Google Sheets Trigger → Normalizar fila → Registrar en API`; de `Registrar en API` salen la rama de éxito (hacia `¿Respuesta OK?`) y la rama de error (hacia `Alerta al administrador`); `¿Respuesta OK?` (true) → `¿Ya estaba registrada?`, (false) → `Alerta al administrador`; `¿Ya estaba registrada?` (true) → `Duplicado: no reenviar`, (false) → `Correo al solicitante → Escribir folio en la hoja`; `Alerta al administrador → Detener con error`.

> **Credenciales distintas:** el nodo de disparo usa **Google Sheets Trigger OAuth2 API** y el nodo de escritura usa **Google Sheets OAuth2 API**; son tipos de credencial separados en n8n, aunque se crean con el mismo Client ID y Client Secret de la aplicación de Google Cloud.

---

## 5. Modelo de datos

### 5.1 Diagrama entidad-relación

La base tiene una sola tabla principal (`solicitudes`) y tres vistas de solo lectura para estadísticas. El folio y la fecha de actualización se generan con triggers, por lo que forman parte del comportamiento del modelo.

```mermaid
erDiagram
    SOLICITUDES {
        bigint id PK "Identificador interno"
        varchar folio UK "SOL-AAAA-NNNN generado por trigger"
        varchar nombre "3 a 120 caracteres"
        varchar correo "formato válido, 120 máximo"
        varchar telefono "opcional, 20 máximo"
        varchar area "opcional, 100 máximo"
        varchar categoria "6 valores permitidos"
        varchar prioridad "4 valores permitidos"
        text descripcion "mínimo 10 caracteres"
        varchar estado "Pendiente por defecto"
        text notas "opcional, API máx 1000"
        varchar id_externo UK "idempotencia de n8n"
        boolean correo_enviado "default false"
        timestamptz fecha_registro "default NOW"
        timestamptz fecha_actualizacion "trigger BEFORE UPDATE"
    }
```

### 5.2 Tabla `solicitudes`

| # | Columna | Tipo | Restricciones | Descripción |
|---|---|---|---|---|
| 1 | `id` | `BIGSERIAL` | `PRIMARY KEY` | Identificador interno autoincremental. Se puede usar en la API como alternativa al folio. |
| 2 | `folio` | `VARCHAR(20)` | `NOT NULL`, `UNIQUE` | Folio de seguimiento con formato `SOL-AAAA-NNNN`. Lo genera `trg_asignar_folio`; la API nunca lo recibe del cliente. |
| 3 | `nombre` | `VARCHAR(120)` | `NOT NULL`, `CHECK (length(btrim(nombre)) >= 3)` | Nombre completo del solicitante. |
| 4 | `correo` | `VARCHAR(120)` | `NOT NULL`, `CHECK (correo ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')` | Correo para la notificación. La API lo guarda en minúsculas. |
| 5 | `telefono` | `VARCHAR(20)` | `NULL` | Teléfono opcional; la API valida el formato si se envía. |
| 6 | `area` | `VARCHAR(100)` | `NULL` | Área o departamento del solicitante. |
| 7 | `categoria` | `VARCHAR(50)` | `NOT NULL`, `CHECK (categoria IN (...))` | Clasificación de la falla: Hardware, Software, Redes e Internet, Accesos y contraseñas, Impresoras u Otro. |
| 8 | `prioridad` | `VARCHAR(20)` | `NOT NULL`, `CHECK (prioridad IN (...))` | Urgencia: Baja, Media, Alta o Crítica. |
| 9 | `descripcion` | `TEXT` | `NOT NULL`, `CHECK (length(btrim(descripcion)) >= 10)` | Descripción del problema (la API acepta hasta 2000 caracteres). |
| 10 | `estado` | `VARCHAR(20)` | `NOT NULL`, `DEFAULT 'Pendiente'`, `CHECK (estado IN (...))` | Estado de atención: Pendiente, En proceso, Resuelto o Cerrado. |
| 11 | `notas` | `TEXT` | `NULL` | Notas internas de seguimiento (la API limita a 1000 caracteres). |
| 12 | `id_externo` | `VARCHAR(120)` | `UNIQUE`, `NULL` | Identificador de la respuesta del formulario; evita registrar dos veces la misma solicitud. |
| 13 | `correo_enviado` | `BOOLEAN` | `NOT NULL`, `DEFAULT FALSE` | Bandera informativa: `TRUE` cuando n8n ya envió la notificación por Gmail. |
| 14 | `fecha_registro` | `TIMESTAMPTZ` | `NOT NULL`, `DEFAULT NOW()` | Momento de captura. Se almacena en UTC y la API la presenta en hora de México. |
| 15 | `fecha_actualizacion` | `TIMESTAMPTZ` | `NULL` | Se actualiza con `NOW()` en cada `UPDATE` mediante `trg_actualizar_fecha`. |

**Total: 15 columnas.** La tabla se crea con `CREATE TABLE IF NOT EXISTS`, tiene comentarios de catálogo (`COMMENT ON TABLE/COLUMN`) y no usa borrado lógico.

### 5.3 Restricciones CHECK y valores válidos

| Restricción | Regla | Valores permitidos |
|---|---|---|
| `chk_categoria` | `categoria IN (...)` | `Hardware`, `Software`, `Redes e Internet`, `Accesos y contraseñas`, `Impresoras`, `Otro` |
| `chk_prioridad` | `prioridad IN (...)` | `Baja`, `Media`, `Alta`, `Crítica` |
| `chk_estado` | `estado IN (...)` | `Pendiente`, `En proceso`, `Resuelto`, `Cerrado` |
| `chk_correo` | Expresión regular (sin distinguir mayúsculas) | `usuario@dominio.com` con TLD de 2 o más letras |
| `chk_nombre` | `length(btrim(nombre)) >= 3` | Al menos 3 caracteres después de recortar espacios |
| `chk_descripcion` | `length(btrim(descripcion)) >= 10` | Al menos 10 caracteres después de recortar espacios |
| `solicitudes_pkey` | `PRIMARY KEY (id)` | — |
| `solicitudes_folio_key` | `UNIQUE (folio)` | — |
| `solicitudes_id_externo_key` | `UNIQUE (id_externo)` | — |

La API, además, normaliza variantes antes de insertar. Ejemplos de alias aceptados por `utilidades.py`:

| Campo | Entrada del formulario | Valor guardado |
|---|---|---|
| `categoria` | `hardware`, `HARDWARE` | `Hardware` |
| `categoria` | `redes`, `internet`, `wifi` | `Redes e Internet` |
| `categoria` | `contrasenas`, `accesos` | `Accesos y contraseñas` |
| `categoria` | `impresora`, `equipo`, `pc`, `programa`, `sistema` | `Impresoras`, `Hardware`, `Hardware`, `Software`, `Software` |
| `prioridad` | `critica`, `urgente`, `inmediata` | `Crítica` |
| `prioridad` | `bajo`, `medio`, `alto` | `Baja`, `Media`, `Alta` |
| `estado` | `en proceso`, `proceso`, `atendiendo` | `En proceso` |
| `estado` | `cerrada`, `finalizado`, `resuelta` | `Cerrado`, `Cerrado`, `Resuelto` |

### 5.4 Secuencia y triggers del folio

El folio se construye en la base de datos con una secuencia global y una función PL/pgSQL que se ejecuta antes de cada inserción. El consecutivo **no se reinicia cada año**; el año del folio corresponde al año de `fecha_registro`.

```sql
-- 1) Secuencia consecutiva del folio
CREATE SEQUENCE IF NOT EXISTS solicitudes_folio_seq
    START WITH 1
    INCREMENT BY 1
    MINVALUE 1
    NO MAXVALUE
    CACHE 1;

-- 2) Función que asigna el folio si la fila no lo trae
CREATE OR REPLACE FUNCTION asignar_folio() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.folio IS NULL OR btrim(NEW.folio) = '' THEN
        NEW.folio := 'SOL-' || to_char(COALESCE(NEW.fecha_registro, NOW()), 'YYYY')
                     || '-' || lpad(nextval('solicitudes_folio_seq')::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3) Trigger BEFORE INSERT
DROP TRIGGER IF EXISTS trg_asignar_folio ON solicitudes;
CREATE TRIGGER trg_asignar_folio
    BEFORE INSERT ON solicitudes
    FOR EACH ROW
    EXECUTE FUNCTION asignar_folio();
```

Comportamiento y garantías:

- **Formato:** `SOL-` + año de 4 dígitos + `-` + consecutivo con ceros a la izquierda (`lpad(..., 4, '0')`), por ejemplo `SOL-2026-0001`.
- **Atomicidad:** `nextval()` es atómico; dos inserciones simultáneas nunca reciben el mismo número, aunque se salten números si una transacción falla (comportamiento estándar y deseable de las secuencias).
- **Uso directo por SQL:** si una persona inserta por el SQL Editor sin especificar folio, el trigger también lo genera; si especifica un folio manual, el trigger lo respeta y la restricción `UNIQUE` evita duplicados.
- **Nunca viene del cliente:** la API no envía la columna `folio` en el `INSERT`; solo envían `nombre`, `correo`, `telefono`, `area`, `categoria`, `prioridad`, `descripcion` e `id_externo`.

El segundo trigger mantiene la fecha de actualización:

```sql
CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion() RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_actualizar_fecha ON solicitudes;
CREATE TRIGGER trg_actualizar_fecha
    BEFORE UPDATE ON solicitudes
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_actualizacion();
```

`trg_actualizar_fecha` garantiza que la API y cualquier actualización manual mantengan `fecha_actualizacion` coherente. Como consecuencia, la API no necesita enviar esa fecha en el `UPDATE` de estado; solo cambia `estado` y `notas` y el trigger actualiza la marca de tiempo.

### 5.5 Índices

| Índice | Definición | ¿Para qué consulta? |
|---|---|---|
| `solicitudes_pkey` | `PRIMARY KEY (id)` | Búsqueda por id numérico (`GET /api/solicitudes/1`). |
| `solicitudes_folio_key` | `UNIQUE (folio)` | Búsqueda por folio y validación de unicidad. |
| `solicitudes_id_externo_key` | `UNIQUE (id_externo)` | `ON CONFLICT (id_externo) DO NOTHING` e idempotencia. |
| `idx_solicitudes_categoria` | `(categoria)` | Filtro `?categoria=...` y agrupaciones de estadísticas. |
| `idx_solicitudes_prioridad` | `(prioridad)` | Filtro `?prioridad=...` y agrupaciones. |
| `idx_solicitudes_estado` | `(estado)` | Filtro `?estado=...` y agrupaciones. |
| `idx_solicitudes_fecha_registro` | `(fecha_registro DESC)` | Orden `recientes` (por defecto), conteo de últimas 24 horas y listados del dashboard. |

### 5.6 Vistas de estadísticas

| Vista | Columnas | Uso |
|---|---|---|
| `v_estadisticas_por_categoria` | `categoria`, `total`, `porcentaje` | Comprobar que los conteos por categoría coinciden con el dashboard. |
| `v_estadisticas_por_prioridad` | `prioridad`, `total`, `porcentaje` | Validar la distribución de urgencias. |
| `v_estadisticas_por_estado` | `estado`, `total`, `porcentaje` | Ver el avance de atención. |

Cada vista calcula `total` con `COUNT(*)` y `porcentaje` con `ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM solicitudes), 0), 2)`, de modo que no divide entre cero cuando la tabla está vacía (el porcentaje queda en `NULL`).

### 5.7 Ejemplo de fila

Fila insertada por la API el 10 de noviembre de 2026 (representación lógica de `SELECT * FROM solicitudes`):

| Columna | Valor |
|---|---|
| `id` | `12` |
| `folio` | `SOL-2026-0012` |
| `nombre` | `Ana López Hernández` |
| `correo` | `ana.lopez@escuela.edu.mx` |
| `telefono` | `5551234567` |
| `area` | `Recursos Humanos` |
| `categoria` | `Hardware` |
| `prioridad` | `Alta` |
| `descripcion` | `La computadora de escritorio no enciende desde esta mañana.` |
| `estado` | `Pendiente` |
| `notas` | `NULL` |
| `id_externo` | `form-2` |
| `correo_enviado` | `false` |
| `fecha_registro` | `2026-11-10 16:30:12-06` |
| `fecha_actualizacion` | `NULL` |

Representación JSON tal como la devuelve la API (`data` de `POST`, `GET` o `PATCH`):

```json
{
  "id": 12,
  "folio": "SOL-2026-0012",
  "nombre": "Ana López Hernández",
  "correo": "ana.lopez@escuela.edu.mx",
  "telefono": "5551234567",
  "area": "Recursos Humanos",
  "categoria": "Hardware",
  "prioridad": "Alta",
  "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
  "estado": "Pendiente",
  "notas": null,
  "id_externo": "form-2",
  "correo_enviado": false,
  "fecha_registro": "2026-11-10T16:30:12-06:00",
  "fecha_actualizacion": null
}
```

> Las fechas se guardan como `TIMESTAMPTZ` (UTC) y se serializan en ISO 8601 con la zona `America/Mexico_City` (`-06:00`). Si `zoneinfo` no está disponible en el sistema, se devuelven en UTC.

### 5.8 Esquema SQL completo

El script `database/schema.sql` es **idempotente** (se puede ejecutar más de una vez sin perder datos) y está diseñado para pegarse completo en el **SQL Editor** de Neon. Su contenido íntegro se reproduce en el [Apéndice C](#apéndice-c-esquema-sql-completo-databaseschemasql).

Los datos de demostración (`database/datos_prueba.sql`) insertan 10 solicitudes con `id_externo` `demo-001` a `demo-010`, estados variados y fechas retroactivas; también es idempotente gracias a `ON CONFLICT (id_externo) DO NOTHING`.

---

## 6. Referencia de la API REST

### 6.1 Convenciones generales

| Aspecto | Definición |
|---|---|
| **URL base (producción)** | `https://api-solicitudes-trampas23.onrender.com` (Render, región Oregon) |
| **URL base (local)** | `http://localhost:5000` |
| **Formato** | JSON (`Content-Type: application/json`); respuestas con `application/json` y UTF-8 |
| **Autenticación** | Header `X-API-Key` en `POST` y `PATCH`. Los `GET` son públicos. |
| **Fechas** | ISO 8601 con offset de México, por ejemplo `2026-11-10T16:30:12-06:00` |
| **Envoltura de éxito** | `{"ok": true, ...}` |
| **Envoltura de error** | `{"ok": false, "error": "<mensaje>", ...}` |
| **Versión del servicio** | `1.0.0` (campo `version` en `GET /` y `GET /health`) |
| **CORS** | Habilitado con Flask-CORS; orígenes configurables con `CORS_ORIGINS` (por defecto `*`) |
| **Idempotencia del `POST`** | Si se envía `id_externo` repetido, responde `200` con `"duplicado": true` |

### 6.2 Resumen de endpoints

| Método | Ruta | Autenticación | Descripción | Códigos de éxito |
|---|---|---|---|---|
| `GET` | `/` | Pública | Índice de la API: nombre, versión, endpoints y valores válidos | `200` |
| `GET` | `/health` | Pública | Estado del servicio y de la base de datos | `200` (siempre) |
| `POST` | `/api/solicitudes` | `X-API-Key` | Registra una solicitud y genera el folio | `201`, `200` (duplicado) |
| `GET` | `/api/solicitudes` | Pública | Lista con filtros, paginación y orden | `200` |
| `GET` | `/api/solicitudes/<folio_o_id>` | Pública | Consulta una solicitud por folio o id | `200` |
| `PATCH` | `/api/solicitudes/<folio>/estado` | `X-API-Key` | Actualiza estado y notas | `200` |
| `GET` | `/api/estadisticas` | Pública | Totales para el dashboard | `200` |

### 6.3 `GET /` — Índice de la API

Describe el servicio y publica los valores válidos para que el equipo y n8n no tengan que adivinarlos.

**Solicitud:**

```bash
curl -s "$API_URL/"
```

**Respuesta `200`:**

```json
{
  "ok": true,
  "servicio": "Sistema automatizado de gestión de solicitudes de soporte técnico",
  "version": "1.0.0",
  "documentacion": "Consulta el README.md y docs/documentacion-tecnica.md del repositorio.",
  "autenticacion": "Header 'X-API-Key' obligatorio en POST y PATCH (lo envía n8n).",
  "endpoints": {
    "GET /health": "Estado del servicio y de la base de datos.",
    "POST /api/solicitudes": "Registrar una nueva solicitud y generar su folio.",
    "GET /api/solicitudes": "Consultar el listado con filtros y paginación.",
    "GET /api/solicitudes/{folio_o_id}": "Consultar una solicitud por folio o id.",
    "PATCH /api/solicitudes/{folio}/estado": "Actualizar el estado de atención.",
    "GET /api/estadisticas": "Totales por categoría, prioridad y estado."
  },
  "valores_validos": {
    "categorias": ["Hardware", "Software", "Redes e Internet", "Accesos y contraseñas", "Impresoras", "Otro"],
    "prioridades": ["Baja", "Media", "Alta", "Crítica"],
    "estados": ["Pendiente", "En proceso", "Resuelto", "Cerrado"]
  },
  "ejemplo_filtros": "/api/solicitudes?categoria=Hardware&prioridad=Alta&limit=10"
}
```

### 6.4 `GET /health` — Estado del servicio

Lo usa Render como **health check path**. **Siempre responde HTTP `200`**, incluso cuando la base de datos no está disponible: el campo `base_datos` indica la situación real y el campo `mensaje` la explica. Esto evita que Render reinicie el servicio por una caída de Neon.

**Solicitud:**

```bash
curl -i "$API_URL/health"
```

**Respuesta con base de datos conectada (`200`):**

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

**Respuesta con base de datos desconectada (`200`):**

```json
{
  "ok": true,
  "servicio": "Sistema automatizado de gestión de solicitudes de soporte técnico",
  "version": "1.0.0",
  "base_datos": "desconectada",
  "mensaje": "El servicio está en línea, pero no hay conexión con PostgreSQL. Revisa DATABASE_URL en Render y que el proyecto de Neon esté activo.",
  "hora": "2026-11-10T22:33:34-06:00"
}
```

> **Criterio de aceptación:** `"base_datos": "conectada"`. Un `200` con `"desconectada"` es la señal de que `DATABASE_URL` está mal configurada o Neon no responde.

### 6.5 `POST /api/solicitudes` — Registrar una solicitud

Crea una solicitud, genera el folio automáticamente y devuelve el registro completo. Es el endpoint que consume n8n desde el workflow.

**Headers:**

| Header | Valor | Obligatorio |
|---|---|---|
| `Content-Type` | `application/json` | Sí |
| `X-API-Key` | La llave configurada en la variable `API_KEY` de Render | Sí |

**Cuerpo (`application/json`):**

| Campo | Tipo | Obligatorio | Reglas de validación | Normalización |
|---|---|---|---|---|
| `nombre` | string | Sí | 3 a 120 caracteres | Recorta y colapsa espacios |
| `correo` | string | Sí | Formato `usuario@dominio.com`, máximo 120 | Se guarda en minúsculas |
| `telefono` | string | No | 7 a 20 caracteres; solo números, espacios, `+`, `-`, `.`, `(`, `)` | Recorta espacios |
| `area` | string | No | Máximo 100 caracteres | Recorta y colapsa espacios |
| `categoria` | string | Sí | Uno de los 6 valores permitidos (acepta alias y variantes) | Se convierte al valor canónico |
| `prioridad` | string | Sí | Uno de los 4 valores permitidos (acepta alias) | Se convierte al valor canónico |
| `descripcion` | string | Sí | 10 a 2000 caracteres | Recorta y colapsa espacios |
| `id_externo` | string | No | Letras, números y `. _ : -`, máximo 120 | Se usa para idempotencia |

**Solicitud (curl):**

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
    "id_externo": "form-2"
  }'
```

**Respuesta `201 Created`:**

```json
{
  "ok": true,
  "mensaje": "Solicitud registrada correctamente.",
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "telefono": "5551234567",
    "area": "Recursos Humanos",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
    "estado": "Pendiente",
    "notas": null,
    "id_externo": "form-2",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": null
  }
}
```

**Respuesta `200 OK` por idempotencia (mismo `id_externo`; el `data` se muestra resumido):**

```json
{
  "ok": true,
  "duplicado": true,
  "mensaje": "La solicitud ya estaba registrada previamente; se devuelve el registro existente.",
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "correo": "ana.lopez@escuela.edu.mx",
    "estado": "Pendiente",
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": null
  }
}
```

**Errores posibles:**

| Código | Condición | Cuerpo |
|---|---|---|
| `400` | El cuerpo no es un objeto JSON o falta `Content-Type` | `{"ok": false, "error": "El cuerpo de la petición debe ser un objeto JSON válido (Content-Type: application/json)."}` |
| `400` | Datos inválidos | `{"ok": false, "error": "La solicitud contiene datos inválidos.", "errores": {"campo": "mensaje", ...}}` |
| `401` | Falta `X-API-Key` o no coincide | `{"ok": false, "error": "No autorizado.", "mensaje": "Incluye el header 'X-API-Key' con la clave correcta. El workflow de n8n la envía automáticamente."}` |
| `503` | No hay conexión con la base | `{"ok": false, "error": "Servicio de base de datos no disponible.", "mensaje": "...", "sugerencia": "Verifica DATABASE_URL en Render y que el proyecto de Neon esté activo. También puedes consultar GET /health."}` |
| `500` | Falla no controlada (sin `id_externo` y sin fila insertada) | `{"ok": false, "error": "No fue posible registrar la solicitud."}` |

**Respuesta `400` de validación (ejemplo):**

```json
{
  "ok": false,
  "error": "La solicitud contiene datos inválidos.",
  "errores": {
    "nombre": "El nombre debe tener al menos 3 caracteres.",
    "correo": "El correo no tiene un formato válido (ejemplo: usuario@dominio.com).",
    "categoria": "Categoría no válida. Valores permitidos: Hardware, Software, Redes e Internet, Accesos y contraseñas, Impresoras, Otro.",
    "prioridad": "Prioridad no válida. Valores permitidos: Baja, Media, Alta, Crítica.",
    "descripcion": "La descripción debe tener al menos 10 caracteres."
  }
}
```

### 6.6 `GET /api/solicitudes` — Listar con filtros

Devuelve un listado paginado. Todos los filtros son opcionales y combinables.

**Parámetros de consulta:**

| Parámetro | Tipo | Valor por defecto | Reglas |
|---|---|---|---|
| `categoria` | string | — | Uno de los 6 valores; acepta alias (`hardware`, `redes`, `contrasenas`…). Valor inválido → `400` |
| `prioridad` | string | — | Uno de los 4 valores; acepta alias (`critica`, `urgente`). Valor inválido → `400` |
| `estado` | string | — | Uno de los 4 valores; acepta alias (`en proceso`, `cerrada`). Valor inválido → `400` |
| `correo` | string | — | Coincidencia exacta sin distinguir mayúsculas (ILIKE sin comodines) |
| `q` | string | — | Texto libre: busca con comodines en `folio`, `nombre`, `descripcion`, `correo` y `area` |
| `limit` | entero | `50` | Entre 1 y 200; fuera de rango o no numérico → `400` |
| `offset` | entero | `0` | Mayor o igual a 0; no numérico → `400` |
| `orden` | string | `recientes` | `recientes` (fecha y id descendente) o `antiguas` (ascendente); otro valor → `400` |

**Solicitud:**

```bash
# Listado simple
curl -s "$API_URL/api/solicitudes?limit=10"

# Filtros combinados
curl -s "$API_URL/api/solicitudes?categoria=Hardware&prioridad=Alta&estado=Pendiente&limit=10&offset=0&orden=recientes"

# Búsqueda de texto libre
curl -s "$API_URL/api/solicitudes?q=impresora"
```

**Respuesta `200`:**

```json
{
  "ok": true,
  "total": 3,
  "limit": 10,
  "offset": 0,
  "cantidad": 3,
  "data": [
    {
      "id": 3,
      "folio": "SOL-2026-0003",
      "nombre": "María José Torres",
      "correo": "maria.torres@escuela.edu.mx",
      "telefono": "5553456789",
      "area": "Dirección Académica",
      "categoria": "Redes e Internet",
      "prioridad": "Crítica",
      "descripcion": "No hay conexión a internet en el edificio B desde el corte de luz de anoche.",
      "estado": "En proceso",
      "notas": null,
      "id_externo": "demo-003",
      "correo_enviado": true,
      "fecha_registro": "2026-11-09T16:30:00-06:00",
      "fecha_actualizacion": "2026-11-10T09:12:31-06:00"
    }
  ]
}
```

**Errores posibles:**

| Código | Condición | Cuerpo |
|---|---|---|
| `400` | Filtro de categoría/prioridad/estado inválido | `{"ok": false, "error": "El valor del filtro 'categoria' no es válido.", "errores": {"categoria": "Valores permitidos: Hardware, Software, ..."}}` |
| `400` | `limit` o `offset` no numéricos | `{"ok": false, "error": "Los parámetros 'limit' y 'offset' deben ser números enteros."}` |
| `400` | `limit` fuera de 1–200 o `offset` negativo | Mensaje específico del rango |
| `400` | `orden` distinto de `recientes` o `antiguas` | `{"ok": false, "error": "El parámetro 'orden' debe ser 'recientes' o 'antiguas'."}` |
| `503` | Base de datos no disponible | Envoltura de error `503` |

### 6.7 `GET /api/solicitudes/<folio_o_id>` — Consultar una solicitud

Acepta el folio (`SOL-2026-0001`, sin distinguir mayúsculas) o el id numérico (`1`).

**Solicitud:**

```bash
curl -s "$API_URL/api/solicitudes/SOL-2026-0001"
curl -s "$API_URL/api/solicitudes/1"
```

**Respuesta `200`:**

```json
{
  "ok": true,
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "telefono": "5551234567",
    "area": "Recursos Humanos",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
    "estado": "Pendiente",
    "notas": null,
    "id_externo": "form-2",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": null
  }
}
```

**Respuesta `404`:**

```json
{
  "ok": false,
  "error": "No se encontró ninguna solicitud con el identificador 'SOL-2099-9999'."
}
```

### 6.8 `PATCH /api/solicitudes/<folio>/estado` — Actualizar estado

Cambia el estado de atención y, opcionalmente, reemplaza las notas. Acepta folio o id numérico en la ruta. El trigger `trg_actualizar_fecha` actualiza `fecha_actualizacion` automáticamente.

**Headers:** `Content-Type: application/json` y `X-API-Key`.

**Cuerpo:**

| Campo | Tipo | Obligatorio | Reglas |
|---|---|---|---|
| `estado` | string | Sí | Valores permitidos: `Pendiente`, `En proceso`, `Resuelto`, `Cerrado` (acepta alias y variantes: `en proceso`, `proceso`, `resuelta`, `cerrada`, `finalizado`…) |
| `notas` | string | No | Máximo 1000 caracteres; si se omite o es `null`, se conservan las notas anteriores |

**Solicitud:**

```bash
curl -i -X PATCH "$API_URL/api/solicitudes/SOL-2026-0001/estado" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{"estado": "en proceso", "notas": "Asignado al técnico de turno."}'
```

**Respuesta `200`:**

```json
{
  "ok": true,
  "mensaje": "Estado actualizado a 'En proceso'.",
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "telefono": "5551234567",
    "area": "Recursos Humanos",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
    "estado": "En proceso",
    "notas": "Asignado al técnico de turno.",
    "id_externo": "form-2",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": "2026-11-10T23:05:47-06:00"
  }
}
```

**Errores posibles:**

| Código | Condición | Cuerpo |
|---|---|---|
| `400` | Cuerpo no JSON o sin objeto | `{"ok": false, "error": "El cuerpo debe ser un objeto JSON con el campo 'estado'."}` |
| `400` | Estado no válido | `{"ok": false, "error": "Estado no válido.", "errores": {"estado": "Valores permitidos: Pendiente, En proceso, Resuelto, Cerrado."}}` |
| `400` | Notas demasiado largas | `{"ok": false, "error": "Las notas son demasiado largas.", "errores": {"notas": "Máximo 1000 caracteres."}}` |
| `401` | Falta `X-API-Key` o no coincide | Envoltura de error `401` |
| `404` | No existe el folio/id | `{"ok": false, "error": "No se encontró ninguna solicitud con el identificador '<id>'."}` |
| `503` | Base de datos no disponible | Envoltura de error `503` |

### 6.9 `GET /api/estadisticas` — Totales para el dashboard

Agrega los conteos del dashboard en una sola llamada. Es público para que la hoja o cualquier visualizador lo consulte sin exponer la llave de escritura.

**Solicitud:**

```bash
curl -s "$API_URL/api/estadisticas"
```

**Respuesta `200`:**

```json
{
  "ok": true,
  "data": {
    "total": 10,
    "por_categoria": [
      {"categoria": "Hardware", "total": 2},
      {"categoria": "Software", "total": 2},
      {"categoria": "Redes e Internet", "total": 2},
      {"categoria": "Accesos y contraseñas", "total": 2},
      {"categoria": "Impresoras", "total": 1},
      {"categoria": "Otro", "total": 1}
    ],
    "por_prioridad": [
      {"prioridad": "Media", "total": 4},
      {"prioridad": "Alta", "total": 3},
      {"prioridad": "Baja", "total": 2},
      {"prioridad": "Crítica", "total": 1}
    ],
    "por_estado": [
      {"estado": "Pendiente", "total": 4},
      {"estado": "En proceso", "total": 3},
      {"estado": "Resuelto", "total": 2},
      {"estado": "Cerrado", "total": 1}
    ],
    "ultimas_24_horas": 2,
    "generado_en": "2026-11-10T22:45:03-06:00"
  }
}
```

> Los arreglos respetan el orden `total DESC` y, en empate, el valor alfabético del grupo. Los números deben coincidir con las vistas `v_estadisticas_por_categoria`, `v_estadisticas_por_prioridad` y `v_estadisticas_por_estado` de Neon y con el dashboard de Google Sheets.

### 6.10 Códigos de error de la API

| Código | Nombre | Cuándo ocurre | Formato del cuerpo |
|---|---|---|---|
| `200` | OK | Consultas exitosas, actualización de estado y `POST` idempotente | `{"ok": true, ...}` |
| `201` | Created | `POST` que inserta una solicitud nueva | `{"ok": true, "mensaje": "...", "data": {...}}` |
| `400` | Bad Request | JSON inválido, validación de campos, filtros/parámetros/orden inválidos, notas demasiado largas | `{"ok": false, "error": "...", "errores": {...}}` |
| `401` | Unauthorized | Falta `X-API-Key` o no coincide, en `POST` o `PATCH` | `{"ok": false, "error": "No autorizado.", "mensaje": "..."}` |
| `404` | Not Found | Solicitud inexistente, ruta inexistente | `{"ok": false, "error": "..."}` |
| `405` | Method Not Allowed | Método HTTP no permitido en una ruta existente (por ejemplo `PUT /api/solicitudes`) | `{"ok": false, "error": "Método HTTP no permitido para esta ruta."}` |
| `500` | Internal Server Error | Error inesperado no controlado | `{"ok": false, "error": "Error interno del servidor."}` |
| `503` | Service Unavailable | No hay conexión con PostgreSQL o error de la capa de datos | `{"ok": false, "error": "Servicio de base de datos no disponible.", "mensaje": "...", "sugerencia": "..."}` |

**Formato uniforme de error:** todos los errores incluyen `"ok": false` y `"error"`; los de validación agregan `"errores"` (objeto campo → mensaje) y los de base de datos agregan `"mensaje"` y `"sugerencia"`.

**Traducción de errores de PostgreSQL** (`backend/database.py`):

| Excepción de psycopg2 | Mensaje que recibe el cliente |
|---|---|
| `OperationalError` / `InterfaceError` | "Se perdió la conexión con la base de datos (Neon). Verifica DATABASE_URL y que el proyecto no esté suspendido por inactividad." |
| `UndefinedTable` | "No existe la tabla 'solicitudes'. Ejecuta database/schema.sql en el SQL Editor de Neon." |
| `UndefinedColumn` | "La tabla 'solicitudes' no tiene la estructura esperada. Vuelve a ejecutar database/schema.sql." |
| `UniqueViolation` | "Ya existe un registro con ese valor único (folio o id_externo)." |
| `CheckViolation` | "Un dato no cumple las restricciones definidas en la tabla solicitudes." |
| Otro error de base de datos | "Ocurrió un error al consultar la base de datos." |

---

## 7. Seguridad

### 7.1 Autenticación con API key

- **Mecanismo:** header HTTP `X-API-Key`. La API compara la llave recibida con la variable de entorno `API_KEY` usando `secrets.compare_digest`, que tarda el mismo tiempo para llaves correctas e incorrectas (evita ataques de temporización).
- **Alcance:** obligatorio en `POST /api/solicitudes` y `PATCH /api/solicitudes/<folio>/estado`; los `GET` son públicos.
- **Comportamiento si falta `API_KEY`:** el decorador deja pasar la petición. Es una facilidad exclusiva para desarrollo local; **en Render la variable siempre debe estar configurada**.
- **Longitud recomendada:** al menos 32 caracteres aleatorios generados con `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- **Manejo de la llave:** se captura en Render (variable de entorno) y en n8n (header del nodo HTTP). No se versiona en el repositorio; el JSON del workflow debe usar un marcador (`<API_KEY>`) y configurarse a mano en n8n.
- **Respuesta de rechazo:** `401` con un mensaje que no revela la llave esperada ni detalles internos.
- **Limitación aceptada:** una sola llave compartida; no identifica usuarios ni permite roles (ver mejoras futuras).

### 7.2 Cifrado en tránsito (SSL/TLS)

| Tramo | Protección |
|---|---|
| Navegador / n8n → Render | HTTPS con certificado automático de Render (`*.onrender.com`); el tráfico viaja cifrado. |
| Render → Neon | TLS obligatorio en PostgreSQL con `sslmode=require` en la cadena `DATABASE_URL`. Neon rechaza conexiones sin TLS. |
| Google APIs (Sheets/Gmail) | HTTPS con OAuth 2.0; los tokens se administran en n8n, no en el código. |

La capa de datos (`database.py`) normaliza la cadena: convierte el formato antiguo `postgres://` a `postgresql://` y agrega `sslmode=require` si no viene, de modo que una cadena copiada incompleta no rompe el requisito de TLS. Para mayor rigor puede usarse `sslmode=verify-full` en cargas productivas.

### 7.3 Validación de entrada

La validación se hace en dos niveles (defensa en profundidad):

1. **API (`utilidades.py`):** tipos, longitudes mínimas/máximas, formato de correo y teléfono, listas blancas para categoría/prioridad/estado, normalización de alias y recorte de espacios. Devuelve `400` con el detalle por campo.
2. **Base de datos (`schema.sql`):** restricciones `CHECK`, `NOT NULL`, `UNIQUE`, llave primaria y disparadores. Aunque alguien inserte por SQL directo, la integridad se conserva.

Controles adicionales:

- **SQL parametrizado:** todas las consultas usan `%s` y tuplas de parámetros; el `ORDER BY` solo puede tomar dos valores fijos (`recientes`/`antiguas`), lo que impide inyección por esa vía.
- **Idempotencia:** `id_externo` con `UNIQUE` y `ON CONFLICT (id_externo) DO NOTHING` evita duplicados por reintentos.
- **Límites de paginación:** `limit` entre 1 y 200 para evitar consultas masivas.
- **Cuerpo JSON:** se exige un objeto JSON; arreglos, texto plano o JSON inválido se rechazan con `400`.

### 7.4 CORS

- La API usa **Flask-CORS** con la configuración `CORS(app, resources={r"/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})`.
- Por defecto permite cualquier origen (`*`), lo que facilita las pruebas desde cualquier cliente.
- **Recomendación para producción:** definir `CORS_ORIGINS` con el origen exacto del dashboard o de la aplicación que consuma la API, por ejemplo `https://midominio.com`, y no dejar `*`.
- **Importante:** CORS protege al navegador, no a la API. n8n y curl no aplican CORS; la autenticación real es la API key. Restringir orígenes no sustituye la autenticación.

### 7.5 Variables de entorno y manejo de secretos

| Variable | Secreta | Dónde vive | ¿Se versiona? |
|---|---|---|---|
| `DATABASE_URL` | Sí (contiene la contraseña de Neon) | Render → Environment; `.env` local | No (`backend/.env` está en `.gitignore`) |
| `API_KEY` | Sí | Render → Environment; n8n (header); `.env` local | No |
| `ADMIN_EMAIL` | No sensible | Render → Environment; n8n | No |
| `PORT` | No | La inyecta Render; `5000` en local | No aplica |
| `FLASK_DEBUG` | No | Local: `false`; producción: vacía | No |
| `CORS_ORIGINS` | No | Render → Environment | No |

Buenas prácticas aplicadas:

1. `backend/.env.example` documenta las variables con valores de ejemplo y **sí** se versiona.
2. `backend/.env` (valores reales) está en `.gitignore`.
3. `render.yaml` declara `DATABASE_URL`, `API_KEY` y `ADMIN_EMAIL` con `sync: false`: Render las pide en el panel y no las guarda en el repositorio.
4. Los mensajes de error de la API no exponen la cadena de conexión ni trazas de Python; el detalle técnico queda en los logs de Render.
5. **Rotación:** si la llave se filtra, se genera una nueva, se actualiza Render y n8n, y se redespliega.

### 7.6 Otras consideraciones y riesgos

| Riesgo | Estado actual | Recomendación |
|---|---|---|
| Lecturas públicas sin autenticación | Los `GET` exponen datos personales a quien tenga la URL | Proteger con API key o proxy autenticado en una versión institucional |
| Sin límite de peticiones | Posible saturación o fuerza bruta de la llave | Rate limiting (Flask-Limiter o proxy) |
| Sin roles ni auditoría | No se sabe quién cambió un estado | Autenticación con usuarios + tabla de auditoría |
| Llave compartida | Difícil de revocar por persona | Varias llaves por cliente o JWT |
| Enlaces de la hoja de cálculo | Quien tenga el enlace con permiso de edición puede alterarla | Compartir solo con el equipo y el profesor; revisar permisos |
| Datos de prueba en producción | Pueden mezclarse con datos reales | Ejecutar `datos_prueba.sql` solo en la base de demostración o borrar antes de la entrega |
| Fugas en el repositorio | Un commit con `.env` expondría secretos | Revisar `.gitignore`, `git ls-files` y usar `git secret`/GitHub secret scanning |

---

## 8. Pruebas

### 8.1 Preparación del entorno de pruebas

**Variables para curl (Git Bash / Linux / macOS):**

```bash
export API_URL="https://api-solicitudes-trampas23.onrender.com"
export API_KEY="<TU_API_KEY>"
```

**Variables para PowerShell (Windows):**

```powershell
$API_URL = "https://api-solicitudes-trampas23.onrender.com"
$API_KEY = "<TU_API_KEY>"
$headers = @{ "X-API-Key" = $API_KEY; "Content-Type" = "application/json" }
```

**API en local (opcional):**

```powershell
Set-Location backend
Copy-Item .env.example .env
# Edita .env y coloca DATABASE_URL de Neon y una API_KEY de prueba
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
# La API queda en http://localhost:5000
```

### 8.2 Sintaxis de los comandos curl

| Bandera | Para qué sirve en estas pruebas |
|---|---|
| `-s` | Modo silencioso: no muestra la barra de progreso. |
| `-i` | Incluye los encabezados HTTP de la respuesta (para ver `201`, `401`, etc.). |
| `-X POST` / `-X PATCH` | Indica el método HTTP de la petición. |
| `-H "Header: valor"` | Agrega un encabezado (`X-API-Key`, `Content-Type`). |
| `-d '...'` | Envía el cuerpo de la petición con los datos JSON. |
| `--data-binary "@archivo.json"` | Envía el cuerpo desde un archivo (útil en PowerShell/Windows). |
| `-o /dev/null -w "%{http_code}\n"` | Descarta el cuerpo y muestra solo el código HTTP (pruebas de seguridad). |
| `$API_URL` / `$API_KEY` | Variables de entorno definidas en la sección 8.1. |

**Plantilla general:**

```bash
curl -i -X <MÉTODO> "$API_URL/<ruta>" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '<cuerpo-json>'
```

> En **Windows PowerShell** usa `curl.exe` (no `curl`, que es alias de `Invoke-WebRequest`). En **Git Bash** los comandos funcionan tal cual. Las equivalencias con `Invoke-RestMethod` están en `docs/pruebas-api.md`.

### 8.3 Pruebas automatizadas (34 pruebas de humo)

El repositorio incluye `backend/test_smoke.py`, que se ejecuta **sin base de datos** porque sustituye la capa de datos con dobles de prueba (`unittest.mock`). Verifica validaciones, normalización, códigos HTTP, autenticación, manejo de `503` y serialización de fechas.

**Ejecución:**

```powershell
Set-Location backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python test_smoke.py -v
```

**Resultado esperado:** `Ran 34 tests in ...` y `OK`.

| Suite | N.º de pruebas | Qué verifica | Resultado esperado | Resultado obtenido |
|---|---|---|---|---|
| `PruebasUtilidades` | 10 | Normalización de categorías/prioridades/estados, validación de correo, limpieza de espacios, detección de todos los errores, rechazo de cuerpos que no son objeto | `OK` | Por llenar |
| `PruebasAPI` | 24 | `GET /`, `/health` con y sin base, `POST` (201, 401, 400, 200 duplicado, 503), listado y filtros inválidos, consulta por folio/id, `PATCH` (200, 400, 404), estadísticas y serialización ISO 8601 | `OK` | Por llenar |
| **Total** | **34** | — | **`OK`** | Por llenar |

### 8.4 Tabla de casos de prueba funcionales

Los casos se ejecutan con curl contra la API desplegada (o en local). La columna **Resultado obtenido** se deja deliberadamente para llenarla durante la ejecución y la captura de evidencias.

| ID | Tipo | Descripción | Entrada / comando | Resultado esperado | Resultado obtenido |
|---|---|---|---|---|---|
| CP-01 | Funcional | Índice de la API | `GET /` | `200`; incluye `ok`, `version` y `valores_validos` | Por llenar |
| CP-02 | Funcional | Health con base conectada | `GET /health` | `200` con `"base_datos": "conectada"` | Por llenar |
| CP-03 | Integración | Health con base caída | `GET /health` con `DATABASE_URL` inválida (local) | `200` con `"base_datos": "desconectada"` y mensaje explicativo | Por llenar |
| CP-04 | Funcional | Registrar solicitud válida | `POST /api/solicitudes` con datos válidos e `id_externo` nuevo | `201` con folio `SOL-AAAA-NNNN` y `estado: "Pendiente"` | Por llenar |
| CP-05 | Funcional | Idempotencia | Repetir el `POST` anterior con el mismo `id_externo` | `200` con `"duplicado": true` y el mismo folio | Por llenar |
| CP-06 | Seguridad | POST sin API key | `POST` sin header `X-API-Key` | `401` con `error: "No autorizado."` | Por llenar |
| CP-07 | Seguridad | POST con API key incorrecta | `POST` con `X-API-Key: llave-incorrecta` | `401` | Por llenar |
| CP-08 | Validación | Campos obligatorios faltantes | `POST` con `{"nombre": "A"}` | `400` con `errores.nombre`, `errores.correo`, `errores.categoria`, `errores.prioridad`, `errores.descripcion` | Por llenar |
| CP-09 | Validación | Categoría y prioridad inválidas | `POST` con `"categoria": "Física"`, `"prioridad": "Altísima"` | `400` con mensajes de valores permitidos | Por llenar |
| CP-10 | Validación | Correo inválido | `POST` con `"correo": "correo-mal"` | `400` con `errores.correo` | Por llenar |
| CP-11 | Validación | Descripción demasiado corta | `POST` con `"descripcion": "corta"` | `400` con `errores.descripcion` | Por llenar |
| CP-12 | Validación | Teléfono inválido | `POST` con `"telefono": "abc"` | `400` con `errores.telefono` | Por llenar |
| CP-13 | Validación | Cuerpo que no es JSON | `POST` con `Content-Type: text/plain` y texto plano | `400` con mensaje de cuerpo JSON inválido | Por llenar |
| CP-14 | Funcional | Normalización de alias | `POST` con `"categoria": "redes"`, `"prioridad": "urgente"` | `201` con `categoria: "Redes e Internet"` y `prioridad: "Crítica"` | Por llenar |
| CP-15 | Funcional | Listado por defecto | `GET /api/solicitudes` | `200` con `total`, `limit: 50`, `offset: 0`, `data` | Por llenar |
| CP-16 | Funcional | Filtros combinados | `GET /api/solicitudes?categoria=Hardware&prioridad=Alta&limit=10` | `200`; todas las filas cumplen los filtros | Por llenar |
| CP-17 | Funcional | Búsqueda de texto libre | `GET /api/solicitudes?q=impresora` | `200`; resultados con la palabra en folio/nombre/descripción/correo/área | Por llenar |
| CP-18 | Validación | Filtro inválido | `GET /api/solicitudes?categoria=Física` | `400` con `errores.categoria` | Por llenar |
| CP-19 | Validación | `limit` no numérico | `GET /api/solicitudes?limit=abc` | `400` con mensaje de enteros | Por llenar |
| CP-20 | Validación | `limit` fuera de rango | `GET /api/solicitudes?limit=500` | `400` con "debe estar entre 1 y 200" | Por llenar |
| CP-21 | Validación | `orden` inválido | `GET /api/solicitudes?orden=aleatorio` | `400` con "recientes o antiguas" | Por llenar |
| CP-22 | Funcional | Consulta por folio | `GET /api/solicitudes/SOL-2026-0001` | `200` con `data.folio` | Por llenar |
| CP-23 | Funcional | Consulta por id | `GET /api/solicitudes/1` | `200` con `data.id = 1` | Por llenar |
| CP-24 | Funcional | Consulta inexistente | `GET /api/solicitudes/SOL-2099-9999` | `404` con mensaje de no encontrado | Por llenar |
| CP-25 | Funcional | Cambio de estado | `PATCH /api/solicitudes/SOL-2026-0001/estado` con `{"estado": "en proceso"}` | `200` con `estado: "En proceso"` y `fecha_actualizacion` actualizada | Por llenar |
| CP-26 | Validación | Estado inválido | `PATCH .../estado` con `{"estado": "volando"}` | `400` con `errores.estado` | Por llenar |
| CP-27 | Funcional | PATCH de folio inexistente | `PATCH /api/solicitudes/SOL-2099-9999/estado` | `404` | Por llenar |
| CP-28 | Seguridad | PATCH sin API key | `PATCH .../estado` sin header | `401` | Por llenar |
| CP-29 | Validación | Notas demasiado largas | `PATCH .../estado` con `notas` de 1001 caracteres | `400` con `errores.notas` | Por llenar |
| CP-30 | Funcional | Estadísticas | `GET /api/estadisticas` | `200` con `total`, `por_categoria`, `por_prioridad`, `por_estado`, `ultimas_24_horas` | Por llenar |
| CP-31 | Integración | Base no disponible | Endpoint de datos con `DATABASE_URL` inválida | `503` con `error`, `mensaje` y `sugerencia` | Por llenar |
| CP-32 | Funcional | Ruta inexistente | `GET /api/no-existe` | `404` con JSON de recurso no encontrado | Por llenar |
| CP-33 | Funcional | Método no permitido | `PUT /api/solicitudes` | `405` con JSON de método no permitido | Por llenar |
| CP-34 | Integración | Flujo completo de n8n | Enviar el Google Form real | Ejecución `Success`; solicitud en Neon, correo recibido y hoja actualizada | Por llenar |

### 8.5 Casos de prueba de extremo a extremo

| # | Paso | Resultado esperado | Resultado obtenido |
|---|---|---|---|
| E2E-01 | Enviar el Google Form con datos válidos | Respuesta registrada como fila en la hoja | Por llenar |
| E2E-02 | Esperar 1–2 minutos al trigger de n8n | Ejecución visible en **Executions** | Por llenar |
| E2E-03 | Revisar la salida del nodo HTTP | `201` con folio en la respuesta | Por llenar |
| E2E-04 | Consultar Neon | Fila con folio, estado `Pendiente` y `fecha_registro` | Por llenar |
| E2E-05 | Revisar la bandeja del solicitante | Correo con folio, categoría, prioridad y estado | Por llenar |
| E2E-06 | Revisar la hoja | Columnas de folio/estado/fecha actualizadas | Por llenar |
| E2E-07 | Cambiar el estado con `PATCH` | Dashboard y Neon reflejan el nuevo estado | Por llenar |
| E2E-08 | Comparar `GET /api/estadisticas` con el dashboard | Conteos iguales | Por llenar |

### 8.6 Criterios de aceptación

| # | Criterio | Evidencia |
|---|---|---|
| 1 | La API responde `200` en `/health` con `"base_datos": "conectada"` | Captura de curl |
| 2 | El `POST` con llave responde `201` y genera folio `SOL-AAAA-NNNN` | Captura de curl y fila en Neon |
| 3 | El `POST` sin llave responde `401` | Captura de curl |
| 4 | Las validaciones responden `400` con detalle por campo | Captura de curl |
| 5 | El listado filtra y pagina correctamente | Captura de curl |
| 6 | El `PATCH` actualiza estado y `fecha_actualizacion` | Captura de curl y consulta SQL |
| 7 | Un formulario nuevo termina con solicitud en Neon, correo enviado y hoja actualizada | Captura de n8n Execution y de la hoja |
| 8 | Las 34 pruebas automatizadas terminan en `OK` | Captura de `python test_smoke.py -v` |
| 9 | La API y la hoja no exponen `DATABASE_URL` ni `API_KEY` | Revisión del repositorio y de las capturas |

---

## 9. Conclusiones

El proyecto cumplió el objetivo de automatizar el ciclo completo de una solicitud de soporte técnico con un modelo cliente-servidor real:

1. **Se implementó una API REST propia y desplegada en la nube.** Flask + Gunicorn sobre Render, con PostgreSQL administrado en Neon, health check, manejo uniforme de errores y configuración reproducible mediante `render.yaml`. La API no solo almacena: valida, normaliza, autentica y traduce errores técnicos a mensajes en español.
2. **El folio se resolvió en el lugar correcto.** Generarlo con una secuencia y un trigger de PostgreSQL garantiza unicidad y orden incluso con inserciones concurrentes o reintentos; es un ejemplo práctico de por qué las reglas de integridad pertenecen también a la base de datos y no solo a la aplicación.
3. **La automatización eliminó el trabajo manual.** n8n detecta la respuesta del formulario, registra la solicitud, notifica al solicitante y actualiza la hoja sin intervención humana; la rama de error avisa al administrador cuando algo falla, y la idempotencia por `id_externo` evita duplicados en los reintentos.
4. **La separación por capas facilitó el desarrollo y las pruebas.** `app.py` (endpoints), `utilidades.py` (validación) y `database.py` (persistencia) permitieron probar la lógica sin base de datos: las 34 pruebas de humo se ejecutan en segundos y cubren los códigos HTTP, la autenticación y el formato de las respuestas.
5. **El dashboard en Google Sheets demostró que una herramienta cotidiana puede convertirse en un tablero de gestión** cuando los datos llegan ordenados y consistentes desde la API.
6. **Los servicios gratuitos tienen límites que el diseño debe asumir:** cold start de hasta un minuto en Render, suspensión del cómputo de Neon, prueba de 14 días de n8n y tokens OAuth de 7 días en modo prueba. Documentarlos y ajustar los timeouts del workflow fue parte del trabajo profesional, no un accidente.
7. **La principal deuda técnica es la seguridad de las lecturas:** los `GET` son públicos y la API key es única y compartida. El siguiente paso natural es agregar autenticación de usuarios, roles y auditoría, que se proponen en la sección siguiente.

En conjunto, el sistema demuestra un flujo completo *formulario → automatización → API → base de datos → notificación → tablero*, con documentación reproducible y evidencia de pruebas, que es exactamente el tipo de integración que la materia busca: un cliente (Google/n8n) consumiendo un servicio propio (Flask) que persiste en una base de datos relacional (PostgreSQL).

---

## 10. Mejoras futuras

| Prioridad | Mejora | Beneficio | Complejidad |
|---|---|---|---|
| Alta | **Autenticación de usuarios y roles** (JWT o sesiones) con tabla `usuarios` y permisos (`solicitante`, `técnico`, `administrador`) | Elimina la llave compartida y permite saber quién consulta y quién cambia estados | Media |
| Alta | **Proteger los `GET`** con API key, token o proxy autenticado | Evita exponer nombres, correos y descripciones a cualquiera con la URL | Baja |
| Alta | **Rate limiting** con Flask-Limiter o en el proxy de Render | Mitiga abuso y fuerza bruta de la llave | Baja |
| Alta | **Auditoría de cambios** (`historial_estados`: solicitud, estado anterior, estado nuevo, usuario, fecha) | Trazabilidad completa del ciclo de atención | Media |
| Alta | **Migraciones automáticas** (Alembic o Flyway) en lugar de ejecutar `schema.sql` a mano | Despliegues repetibles y control de versiones del esquema | Media |
| Alta | **Pruebas de integración** contra una rama de Neon de pruebas | Valida SQL real, triggers y pool, no solo dobles | Media |
| Media | **API versionada** (`/api/v1/...`) y documento **OpenAPI/Swagger** | Compatibilidad hacia atrás y documentación interactiva | Media |
| Media | **Notificaciones al técnico asignado** y correos de cambio de estado al solicitante | Mejor comunicación con el usuario | Baja |
| Media | **Adjuntos** (capturas de pantalla) con Google Drive o S3 | Diagnóstico más rápido de las fallas | Media |
| Media | **Dashboard web** que consuma `GET /api/estadisticas` y `GET /api/solicitudes` con filtros en vivo | Independencia de Google Sheets y mejor experiencia | Alta |
| Media | **Paginación por cursor** y búsqueda de texto completo con `tsvector` | Mejor rendimiento con miles de solicitudes | Media |
| Media | **Manejo de reintentos y error workflow en n8n** con correo de resumen | Mayor tolerancia a fallas de red | Baja |
| Baja | **Soft delete** y política de retención de datos | Cumplimiento de privacidad y limpieza | Media |
| Baja | **Métricas y monitoreo** (Sentry, UptimeRobot, alertas de errores) | Detección temprana de fallas | Baja |
| Baja | **Internacionalización** de mensajes (español/inglés) | Reutilización en otros contextos | Baja |
| Baja | **Accesibilidad del formulario** (etiquetas, contraste, ayudas) | Inclusión de todos los usuarios | Baja |
| Baja | **CI/CD** con GitHub Actions (pruebas automáticas en cada push) | Calidad continua del repositorio | Media |
| Baja | **Contraseñas/llaves con rotación programada** y varias API keys por cliente | Menor impacto de una filtración | Media |

---

## 11. Referencias

1. Pallets Projects. *Flask Documentation*. <https://flask.palletsprojects.com/>
2. Pallets Projects. *Flask-CORS Documentation*. <https://flask-cors.readthedocs.io/>
3. Benoit Chesneau. *Gunicorn Documentation*. <https://docs.gunicorn.org/>
4. Psycopg. *psycopg2 Documentation*. <https://www.psycopg.org/docs/>
5. PostgreSQL Global Development Group. *PostgreSQL Documentation* (triggers, secuencias, restricciones). <https://www.postgresql.org/docs/>
6. Neon Inc. *Neon Documentation: Get started*. <https://neon.com/docs/get-started/set-up-your-project>
7. Neon Inc. *Connect to Neon securely*. <https://neon.com/docs/connect/connect-securely>
8. Neon Inc. *Connection pooling*. <https://neon.com/docs/connect/connection-pooling>
9. Render Services. *Deploy a Flask App on Render*. <https://render.com/docs/deploy-flask>
10. Render Services. *Free instances (plan Free)*. <https://render.com/docs/free>
11. Render Services. *Environment variables and secrets*. <https://render.com/docs/configure-environment-variables>
12. Render Services. *Health checks*. <https://render.com/docs/health-checks>
13. Render Services. *Infrastructure as code (render.yaml / Blueprints)*. <https://render.com/docs/infrastructure-as-code>
14. n8n GmbH. *n8n Documentation*. <https://docs.n8n.io/>
15. n8n GmbH. *Google credentials in n8n*. <https://docs.n8n.io/integrations/builtin/credentials/google/>
16. n8n GmbH. *Google Sheets node*. <https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/>
17. n8n GmbH. *Gmail node*. <https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.gmail/>
18. Google. *Google Forms: crea un formulario y vincúlalo a Hojas de cálculo*. <https://support.google.com/docs/answer/6281888>
19. Google. *Google Sheets API Documentation*. <https://developers.google.com/sheets/api>
20. Google. *Gmail API Documentation*. <https://developers.google.com/gmail/api>
21. Google. *OAuth 2.0 Documentation*. <https://developers.google.com/identity/protocols/oauth2>
22. Python Software Foundation. *unittest — Unit testing framework*. <https://docs.python.org/3/library/unittest.html>
23. GitHub. *GitHub Docs: crear un repositorio y hacer push*. <https://docs.github.com/es/get-started>
24. Documentación del proyecto: `README.md`, `docs/guia-despliegue-render-neon.md`, `docs/guia-google-forms-sheets.md`, `docs/pruebas-api.md`.

---

## 12. Apéndices

### Apéndice A. Estructura del repositorio

```text
proyecto-solicitudes/
├── README.md                      Descripción general y ejecución local
├── render.yaml                    Blueprint de Render (raíz del repositorio)
├── .gitignore                     Exclusiones (.env, .deps, __pycache__, .venv)
├── backend/
│   ├── app.py                     Endpoints Flask y manejo de errores
│   ├── database.py                Pool de conexiones, SQL y traducción de errores
│   ├── utilidades.py              Validación y normalización de datos
│   ├── requirements.txt           Dependencias con versiones fijas
│   ├── .env.example               Plantilla de variables de entorno
│   ├── .python-version            3.12.6
│   └── test_smoke.py              34 pruebas de humo
├── database/
│   ├── schema.sql                 Tabla, secuencia, triggers, índices y vistas
│   └── datos_prueba.sql           10 solicitudes de demostración
├── n8n/
│   └── workflow-solicitudes.json  Workflow importable en n8n
└── docs/
    ├── documentacion-tecnica.md       Este documento
    ├── guia-despliegue-render-neon.md Guía de despliegue paso a paso
    ├── guia-google-forms-sheets.md    Guía de Forms, Sheets y dashboard
    └── pruebas-api.md                 Evidencias y pruebas con curl/PowerShell
```

### Apéndice B. Variables de entorno

| Variable | Obligatoria | Ejemplo | Descripción |
|---|---|---|---|
| `DATABASE_URL` | Sí | `postgresql://neondb_owner:clave@ep-xxxx-pooler.us-west-2.aws.neon.tech/neondb?sslmode=require` | Cadena de conexión a Neon (formato pooled). La API normaliza `postgres://` y agrega `sslmode=require` si falta. |
| `API_KEY` | Sí en producción | `sH7v2QpR9wXkLm3nT8cYbJ5fD1gA0eZu6iK4oN2rM8s` | Llave del header `X-API-Key`. Si está vacía, `POST`/`PATCH` quedan abiertos. |
| `ADMIN_EMAIL` | No | `soporte@escuela.mx` | Correo del administrador para avisos del workflow. |
| `PORT` | No | `10000` (Render) / `5000` (local) | Puerto del servidor; Render la inyecta automáticamente. |
| `FLASK_DEBUG` | No | `false` | Activa el modo depuración de Flask; nunca en producción. |
| `CORS_ORIGINS` | No | `*` o `https://midominio.com` | Orígenes permitidos por Flask-CORS. |

### Apéndice C. Esquema SQL completo (`database/schema.sql`)

```sql
-- ============================================================================
--  SISTEMA AUTOMATIZADO DE GESTIÓN DE SOLICITUDES DE SOPORTE TÉCNICO
--  Base de datos: PostgreSQL (Neon)          Versión del esquema: 1.0.0
--  Archivo: database/schema.sql
-- ----------------------------------------------------------------------------
--  CÓMO EJECUTARLO
--    1. Entra a https://console.neon.tech y abre tu proyecto.
--    2. Menú izquierdo -> "SQL Editor".
--    3. Pega TODO el contenido de este archivo y presiona "Run".
--
--    Alternativa por terminal (psql):
--      psql "postgresql://usuario:clave@host/neondb?sslmode=require" -f database/schema.sql
--
--  El script es IDEMPOTENTE: puedes ejecutarlo varias veces sin perder datos.
--  Para reiniciar todo desde cero (borra las solicitudes), descomenta el bloque
--  "RESET OPCIONAL" que está justo debajo.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- RESET OPCIONAL (borra todos los datos; úsalo solo si quieres empezar de cero)
-- ----------------------------------------------------------------------------
-- DROP VIEW  IF EXISTS v_estadisticas_por_estado;
-- DROP VIEW  IF EXISTS v_estadisticas_por_prioridad;
-- DROP VIEW  IF EXISTS v_estadisticas_por_categoria;
-- DROP TABLE IF EXISTS solicitudes CASCADE;
-- DROP SEQUENCE IF EXISTS solicitudes_folio_seq;

-- ----------------------------------------------------------------------------
-- 1) SECUENCIA PARA GENERAR LOS FOLIOS CONSECUTIVOS
-- ----------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS solicitudes_folio_seq
    START WITH 1
    INCREMENT BY 1
    MINVALUE 1
    NO MAXVALUE
    CACHE 1;

-- ----------------------------------------------------------------------------
-- 2) TABLA PRINCIPAL: solicitudes
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitudes (
    id                  BIGSERIAL PRIMARY KEY,
    folio               VARCHAR(20)  NOT NULL UNIQUE,
    nombre              VARCHAR(120) NOT NULL,
    correo              VARCHAR(120) NOT NULL,
    telefono            VARCHAR(20),
    area                VARCHAR(100),
    categoria           VARCHAR(50)  NOT NULL,
    prioridad           VARCHAR(20)  NOT NULL,
    descripcion         TEXT         NOT NULL,
    estado              VARCHAR(20)  NOT NULL DEFAULT 'Pendiente',
    notas               TEXT,
    id_externo          VARCHAR(120) UNIQUE,
    correo_enviado      BOOLEAN      NOT NULL DEFAULT FALSE,
    fecha_registro      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    fecha_actualizacion TIMESTAMPTZ,

    CONSTRAINT chk_categoria CHECK (
        categoria IN ('Hardware', 'Software', 'Redes e Internet',
                      'Accesos y contraseñas', 'Impresoras', 'Otro')
    ),
    CONSTRAINT chk_prioridad CHECK (
        prioridad IN ('Baja', 'Media', 'Alta', 'Crítica')
    ),
    CONSTRAINT chk_estado CHECK (
        estado IN ('Pendiente', 'En proceso', 'Resuelto', 'Cerrado')
    ),
    CONSTRAINT chk_correo CHECK (
        correo ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    ),
    CONSTRAINT chk_nombre CHECK (length(btrim(nombre)) >= 3),
    CONSTRAINT chk_descripcion CHECK (length(btrim(descripcion)) >= 10)
);

-- Documentación de la tabla (aparece en el catálogo de PostgreSQL)
COMMENT ON TABLE  solicitudes IS
    'Solicitudes de soporte técnico capturadas con Google Forms y registradas por la API REST.';
COMMENT ON COLUMN solicitudes.folio IS
    'Folio único generado por trigger: SOL-AAAA-NNNN (ej. SOL-2026-0001).';
COMMENT ON COLUMN solicitudes.id_externo IS
    'Identificador de la respuesta del formulario; evita registrar dos veces la misma solicitud (idempotencia).';
COMMENT ON COLUMN solicitudes.correo_enviado IS
    'Bandera informativa: TRUE cuando n8n ya envió la notificación por Gmail.';

-- ----------------------------------------------------------------------------
-- 3) TRIGGER: GENERACIÓN AUTOMÁTICA DEL FOLIO
--    Se ejecuta ANTES de insertar. Si la fila no trae folio, lo construye con
--    el año actual y el siguiente número de la secuencia:
--        SOL-2026-0001, SOL-2026-0002, ...
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION asignar_folio() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.folio IS NULL OR btrim(NEW.folio) = '' THEN
        NEW.folio := 'SOL-' || to_char(COALESCE(NEW.fecha_registro, NOW()), 'YYYY')
                     || '-' || lpad(nextval('solicitudes_folio_seq')::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_asignar_folio ON solicitudes;
CREATE TRIGGER trg_asignar_folio
    BEFORE INSERT ON solicitudes
    FOR EACH ROW
    EXECUTE FUNCTION asignar_folio();

-- ----------------------------------------------------------------------------
-- 4) TRIGGER: FECHA DE ACTUALIZACIÓN AUTOMÁTICA
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION actualizar_fecha_actualizacion() RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_actualizar_fecha ON solicitudes;
CREATE TRIGGER trg_actualizar_fecha
    BEFORE UPDATE ON solicitudes
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_actualizacion();

-- ----------------------------------------------------------------------------
-- 5) ÍNDICES (aceleran los filtros de la API y las consultas del dashboard)
-- ----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_solicitudes_categoria      ON solicitudes (categoria);
CREATE INDEX IF NOT EXISTS idx_solicitudes_prioridad      ON solicitudes (prioridad);
CREATE INDEX IF NOT EXISTS idx_solicitudes_estado         ON solicitudes (estado);
CREATE INDEX IF NOT EXISTS idx_solicitudes_fecha_registro ON solicitudes (fecha_registro DESC);

-- ----------------------------------------------------------------------------
-- 6) VISTAS DE ESTADÍSTICAS (listas para usarse desde Neon o para comprobar
--    que los números coinciden con el dashboard de Google Sheets)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_estadisticas_por_categoria AS
SELECT categoria,
       COUNT(*)                                                          AS total,
       ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM solicitudes), 0), 2) AS porcentaje
FROM solicitudes
GROUP BY categoria
ORDER BY total DESC, categoria;

CREATE OR REPLACE VIEW v_estadisticas_por_prioridad AS
SELECT prioridad,
       COUNT(*)                                                          AS total,
       ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM solicitudes), 0), 2) AS porcentaje
FROM solicitudes
GROUP BY prioridad
ORDER BY total DESC, prioridad;

CREATE OR REPLACE VIEW v_estadisticas_por_estado AS
SELECT estado,
       COUNT(*)                                                          AS total,
       ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM solicitudes), 0), 2) AS porcentaje
FROM solicitudes
GROUP BY estado
ORDER BY total DESC, estado;

-- ----------------------------------------------------------------------------
-- 7) VERIFICACIÓN RÁPIDA (debe regresar 0 en una base recién creada)
-- ----------------------------------------------------------------------------
SELECT COUNT(*) AS solicitudes_registradas FROM solicitudes;
```

### Apéndice D. Glosario

| Término | Definición |
|---|---|
| **API REST** | Interfaz HTTP que expone recursos (solicitudes) mediante métodos (`GET`, `POST`, `PATCH`) y representaciones JSON. |
| **Endpoint** | Ruta de la API que atiende una operación, por ejemplo `POST /api/solicitudes`. |
| **Folio** | Identificador legible y único de una solicitud, con formato `SOL-AAAA-NNNN`. |
| **Trigger (base de datos)** | Función PL/pgSQL que se ejecuta automáticamente `BEFORE INSERT` o `BEFORE UPDATE` sobre una tabla. |
| **Secuencia** | Objeto de PostgreSQL que entrega números consecutivos de forma atómica (`nextval`). |
| **Idempotencia** | Propiedad por la que repetir la misma petición no produce efectos adicionales (aquí, no duplica solicitudes). |
| **Pool de conexiones** | Conjunto de conexiones reutilizables a la base de datos para evitar abrir/cerrar una conexión por petición. |
| **PgBouncer / conexión pooled** | Componente de Neon que multiplexa conexiones; se usa el host con `-pooler` para la API. |
| **TLS / SSL** | Cifrado del transporte; Neon exige `sslmode=require` en la conexión. |
| **CORS** | Mecanismo del navegador que restringe peticiones entre orígenes distintos. |
| **OAuth 2.0** | Protocolo de autorización delegada; n8n lo usa para acceder a Google Sheets y Gmail sin guardar contraseñas. |
| **Cold start** | Demora del primer request cuando un servicio en plan gratuito estaba suspendido. |
| **WSGI** | Interfaz estándar entre un servidor web (Gunicorn) y una aplicación Python (Flask). |
| **Health check** | Petición periódica que un proveedor hace a la app para saber si está viva (`/health`). |
| **Webhook / polling** | Mecanismos de integración: Google Forms no se usa por webhook; n8n consulta la hoja (polling) cada minuto. |
| **Idempotencia `ON CONFLICT`** | Cláusula de PostgreSQL que evita insertar una fila si el valor único ya existe. |
| **TIMESTAMPTZ** | Tipo de PostgreSQL que guarda fecha y hora con zona horaria (UTC internamente). |

### Apéndice E. Documentos relacionados

| Documento | Contenido |
|---|---|
| `README.md` | Descripción general, arquitectura resumida, URLs públicas y ejecución local. |
| `docs/guia-despliegue-render-neon.md` | Fases de despliegue (Neon, GitHub, Render, Google Cloud/OAuth, n8n) y solución de problemas. |
| `docs/guia-google-forms-sheets.md` | Estructura del formulario, columnas de la hoja, fórmulas y gráficas del dashboard. |
| `docs/pruebas-api.md` | Pruebas con curl/PowerShell, resultados esperados y checklist de evidencias. |

---

**Fin de la documentación técnica.** Para consultas sobre el despliegue, revisa `docs/guia-despliegue-render-neon.md`; para el formulario y el dashboard, `docs/guia-google-forms-sheets.md`; para las pruebas, `docs/pruebas-api.md`.
