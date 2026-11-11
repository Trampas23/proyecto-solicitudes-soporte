# Pruebas de la API REST

Guía para comprobar que la API funciona, tanto en local como ya desplegada en
Render. Sin estas pruebas no puedes avanzar a n8n: si la API no responde, el
workflow no podrá registrar solicitudes.

---

## 1. Variables que usarás

| Variable | Ejemplo | De dónde se obtiene |
|---|---|---|
| `URL` | `https://api-solicitudes-trampas23.onrender.com` | Dashboard de Render, servicio de la API |
| `API_KEY` | `Xb7...` (32+ caracteres) | La que capturaste en Render (variable `API_KEY`) |

> En Render la URL la ves arriba del servicio: *"https://<nombre>.onrender.com"*.
> No agregues `/` al final.

### PowerShell (Windows) — recomendado

```powershell
$URL = "https://api-solicitudes-trampas23.onrender.com"
$API_KEY = "tu-clave-secreta"
$headers = @{ "X-API-Key" = $API_KEY; "Content-Type" = "application/json" }
```

### CMD / Git Bash / Mac / Linux (curl)

```bash
export URL="https://api-solicitudes-trampas23.onrender.com"
export API_KEY="tu-clave-secreta"
```

---

## 2. Prueba 1 — El servicio está arriba (`GET /health`)

```powershell
Invoke-RestMethod -Uri "$URL/health" | ConvertTo-Json
```

```bash
curl -s "$URL/health"
```

Respuesta esperada (**HTTP 200**):

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

✅ **Criterio de aceptación:** `"base_datos": "conectada"`.
Si dice `"desconectada"`, el problema es `DATABASE_URL` en Render (ver
`guia-despliegue-render-neon.md`, sección de problemas comunes).

---

## 3. Prueba 2 — Índice de la API (`GET /`)

```powershell
Invoke-RestMethod -Uri "$URL/" | ConvertTo-Json -Depth 4
```

```bash
curl -s "$URL/"
```

Debe listar los endpoints y los **valores válidos** de categorías, prioridades
y estados. Sirve como evidencia en el reporte.

---

## 4. Prueba 3 — Registrar una solicitud (`POST /api/solicitudes`)

```powershell
$cuerpo = @{
  nombre      = "Ana López Hernández"
  correo      = "ana.lopez@escuela.edu.mx"
  telefono    = "5551234567"
  area        = "Recursos Humanos"
  categoria   = "Hardware"
  prioridad   = "Alta"
  descripcion = "La computadora de escritorio no enciende desde esta mañana."
  id_externo  = "prueba-001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "$URL/api/solicitudes" -Method Post -Headers $headers -Body $cuerpo |
  ConvertTo-Json -Depth 4
```

```bash
curl -s -X POST "$URL/api/solicitudes" \
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
    "id_externo": "prueba-001"
  }'
```

Respuesta esperada (**HTTP 201**):

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
    "id_externo": "prueba-001",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:40:12-06:00",
    "fecha_actualizacion": null
  }
}
```

✅ **Criterios de aceptación:**
1. El folio se genera **automáticamente** (no lo mandaste tú).
2. El folio tiene el formato `SOL-AAAA-NNNN`.
3. El estado inicial es `Pendiente`.

### Prueba 3b — Idempotencia (reintentos de n8n)

Repite exactamente la misma petición (mismo `id_externo`). Debe responder
**HTTP 200** con `"duplicado": true` y **el mismo folio**, sin crear otra fila:

```json
{ "ok": true, "duplicado": true, "mensaje": "...ya estaba registrada...", "data": { "folio": "SOL-2026-0001" } }
```

Esto evita solicitudes duplicadas si n8n reintenta el envío.

### Prueba 3c — Validación de datos

```bash
curl -s -X POST "$URL/api/solicitudes" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"nombre":"A","correo":"malo","categoria":"Física","prioridad":"Altísima","descripcion":"corta"}'
```

Respuesta esperada (**HTTP 400**) con el detalle por campo:

```json
{
  "ok": false,
  "error": "La solicitud contiene datos inválidos.",
  "errores": {
    "nombre": "El nombre debe tener al menos 3 caracteres.",
    "correo": "El correo no tiene un formato válido (ejemplo: usuario@dominio.com).",
    "categoria": "Categoría no válida. Valores permitidos: Hardware, Software, ...",
    "prioridad": "Prioridad no válida. Valores permitidos: Baja, Media, Alta, Crítica.",
    "descripcion": "La descripción debe tener al menos 10 caracteres."
  }
}
```

### Prueba 3d — Seguridad (API key)

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "$URL/api/solicitudes" \
  -H "Content-Type: application/json" -d '{"nombre":"Prueba sin clave"}'
```

Debe imprimir `401`. Si imprime `201`, la variable `API_KEY` **no está
configurada** en Render: corrígela antes de continuar.

---

## 5. Prueba 4 — Consultar solicitudes (`GET /api/solicitudes`)

```powershell
Invoke-RestMethod -Uri "$URL/api/solicitudes?limit=5" | ConvertTo-Json -Depth 4
```

```bash
curl -s "$URL/api/solicitudes?limit=5"
```

Respuesta esperada (**HTTP 200**):

```json
{ "ok": true, "total": 3, "limit": 5, "offset": 0, "cantidad": 3, "data": [ { "folio": "...", "...": "..." } ] }
```

### Filtros (todos combinables)

| Filtro | Ejemplo | Notas |
|---|---|---|
| `categoria` | `?categoria=Hardware` | Acepta variantes: `hardware`, `redes`, `contrasenas` |
| `prioridad` | `?prioridad=Alta` | Acepta `critica` (sin acento) |
| `estado` | `?estado=En proceso` | Codifica el espacio: `En%20proceso` |
| `correo` | `?correo=ana.lopez@escuela.edu.mx` | Búsqueda sin distinguir mayúsculas |
| `q` | `?q=impresora` | Busca en folio, nombre, descripción, correo y área |
| `limit` | `?limit=10` | Entre 1 y 200 (por defecto 50) |
| `offset` | `?offset=20` | Para paginar |
| `orden` | `?orden=antiguas` | `recientes` (por defecto) o `antiguas` |

Ejemplo combinado:

```bash
curl -s "$URL/api/solicitudes?categoria=Hardware&prioridad=Alta&limit=10&orden=recientes"
```

Pruebas negativas: `?categoria=Física` → `400`; `?limit=abc` → `400`;
`?orden=aleatorio` → `400`.

---

## 6. Prueba 5 — Consultar una solicitud por folio o id

```bash
curl -s "$URL/api/solicitudes/SOL-2026-0001"
curl -s "$URL/api/solicitudes/1"
```

- `200` con `{"ok":true,"data":{...}}` si existe.
- `404` si no existe: `{"ok":false,"error":"No se encontró ninguna solicitud con el identificador 'SOL-2099-9999'."}`

---

## 7. Prueba 6 — Cambiar el estado (`PATCH`)

```bash
curl -s -X PATCH "$URL/api/solicitudes/SOL-2026-0001/estado" \
  -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
  -d '{"estado": "En proceso", "notas": "Asignado al técnico de turno."}'
```

Respuesta esperada (**HTTP 200**): `"estado": "En proceso"` y
`"fecha_actualizacion"` con la hora del cambio (la asigna un trigger de la BD).

Valores válidos: `Pendiente`, `En proceso`, `Resuelto`, `Cerrado`.
Un estado inválido (`"volando"`) devuelve `400`.

---

## 8. Prueba 7 — Estadísticas para el dashboard (`GET /api/estadisticas`)

```bash
curl -s "$URL/api/estadisticas"
```

```json
{
  "ok": true,
  "data": {
    "total": 3,
    "por_categoria":    [ { "categoria": "Hardware", "total": 2 }, { "categoria": "Software", "total": 1 } ],
    "por_prioridad":    [ { "prioridad": "Alta", "total": 2 }, { "prioridad": "Media", "total": 1 } ],
    "por_estado":       [ { "estado": "Pendiente", "total": 3 } ],
    "ultimas_24_horas": 3,
    "generado_en": "2026-11-10T22:45:03-06:00"
  }
}
```

Estos números deben **coincidir** con los del dashboard de Google Sheets
(evidencia de que el flujo completo quedó consistente).

---

## 9. Comparar con la base de datos (Neon)

En el **SQL Editor** de Neon:

```sql
SELECT folio, nombre, categoria, prioridad, estado, fecha_registro
FROM solicitudes
ORDER BY id DESC
LIMIT 10;
```

Si el `POST` respondió 201 pero aquí no aparece nada, la API está escribiendo en
otra base de datos (revisa `DATABASE_URL`).

---

## 10. Pruebas automatizadas (sin Neon)

El proyecto incluye 34 pruebas que no necesitan base de datos:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python test_smoke.py -v
```

Resultado esperado: `Ran 34 tests ... OK`. Cubren validaciones, normalización,
códigos HTTP, autenticación por API key y el formato de las respuestas.

> Puedes incluir una captura de esta salida en la documentación técnica.

---

## 11. Postman (opcional, para entregar evidencias)

1. Abre Postman → **New → Collection** → nómbrala `Solicitudes Soporte API`.
2. **Variables de colección** (pestaña *Variables*):
   - `url` = `https://tu-servicio.onrender.com`
   - `api_key` = tu clave
3. Agrega las peticiones usando `{{url}}` y el header `X-API-Key: {{api_key}}`:

| # | Método | Ruta | Body |
|---|---|---|---|
| 1 | GET | `{{url}}/health` | — |
| 2 | GET | `{{url}}/` | — |
| 3 | POST | `{{url}}/api/solicitudes` | JSON del ejemplo |
| 4 | GET | `{{url}}/api/solicitudes?limit=10` | — |
| 5 | GET | `{{url}}/api/solicitudes/SOL-2026-0001` | — |
| 6 | PATCH | `{{url}}/api/solicitudes/SOL-2026-0001/estado` | `{"estado":"Resuelto"}` |
| 7 | GET | `{{url}}/api/estadisticas` | — |

4. Ejecuta la colección con **Run → Run collection** y guarda/captura el
   *Test Results* (todas en verde). Es una evidencia muy valorada por el
   profesor.

---

## 12. Checklist de esta etapa

- [ ] `GET /health` responde 200 con `"base_datos": "conectada"`.
- [ ] `POST /api/solicitudes` responde 201 con folio `SOL-AAAA-NNNN`.
- [ ] Repetir el mismo `id_externo` responde 200 con `"duplicado": true`.
- [ ] Datos inválidos responden 400 con `errores` por campo.
- [ ] Sin header `X-API-Key` responde 401.
- [ ] `GET /api/solicitudes` filtra por categoría, prioridad y estado.
- [ ] `PATCH .../estado` actualiza el estado y la fecha de actualización.
- [ ] `GET /api/estadisticas` cuadra con los registros de Neon.
- [ ] `python test_smoke.py -v` termina en OK.
