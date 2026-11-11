# Guía: Google Forms + Google Sheets + Dashboard

## Sistema automatizado de gestión de solicitudes de soporte técnico

| Dato | Valor |
| --- | --- |
| Materia | Programación en ambiente cliente servidor (2do parcial) |
| Proyecto | Sistema automatizado de gestión de solicitudes de soporte técnico |
| Alcance de esta guía | Formulario de captura, hoja de respaldo, columnas de control y dashboard |
| Workflow relacionado | [`../n8n/workflow-solicitudes.json`](../n8n/workflow-solicitudes.json) |
| Versión | 1.0 · noviembre 2026 |

**Flujo general del sistema:**

```
Google Forms (captura) → Google Sheets (respaldo + dashboard)
        ↓ (trigger fila añadida)
      n8n (normaliza y orquesta) → API REST Flask en Render → PostgreSQL en Neon
        ↓
   Gmail (folio al solicitante) + escritura de Folio/Estado/Fecha en la hoja
```

Esta guía cubre los pasos **1 a 6** del flujo. El despliegue de la API en Render,
la base de datos en Neon y las credenciales OAuth de Google se documentan en
[`guia-despliegue-render-neon.md`](guia-despliegue-render-neon.md).

---

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Estructura exacta del Google Forms](#2-estructura-exacta-del-google-forms)
3. [Vinculación del formulario a una hoja de cálculo](#3-vinculación-del-formulario-a-una-hoja-de-cálculo)
4. [Columnas adicionales a la derecha de las respuestas](#4-columnas-adicionales-a-la-derecha-de-las-respuestas)
5. [Pestaña Dashboard: indicadores, fórmulas y gráficas](#5-pestaña-dashboard-indicadores-fórmulas-y-gráficas)
6. [Verificación de punta a punta](#6-verificación-de-punta-a-punta)
7. [Mapeo columna del formulario → campo de la API](#7-mapeo-columna-del-formulario--campo-de-la-api)
8. [Configuración del workflow de n8n](#8-configuración-del-workflow-de-n8n)
9. [Cómo probar el workflow](#9-cómo-probar-el-workflow)
10. [Notas sobre el trigger de Google Sheets](#10-notas-sobre-el-trigger-de-google-sheets)
11. [Solución de problemas](#11-solución-de-problemas)
12. [Checklist de entrega](#12-checklist-de-entrega)

---

## 1. Requisitos previos

1. Una cuenta de Google (Gmail) con acceso a **Google Forms** y **Google Sheets**.
2. Una instancia de **n8n** (n8n Cloud o self-hosted) con los nodos *Google Sheets
   Trigger*, *Google Sheets*, *Gmail*, *HTTP Request*, *Code*, *If*, *No Operation*
   y *Stop and Error*. Todos son nodos base (`n8n-nodes-base`), no requieren
   instalar paquetes extra.
3. La **API Flask desplegada en Render** con PostgreSQL en Neon, funcionando.
   Verifica en el navegador:

   ```text
   https://<tu-servicio>.onrender.com/health
   ```

   Debe responder algo como:

   ```json
   {"ok": true, "servicio": "...", "version": "...", "base_datos": "conectada"}
   ```

   > Nota: en el plan gratuito de Render el servicio se "duerme" tras unos minutos
   > sin tráfico. La primera petición puede tardar 30–60 segundos (cold start).
   > El nodo HTTP del workflow tiene un timeout de 60 000 ms por eso.

4. El valor de la variable `API_KEY` configurada en Render (la misma que usará el
   header `X-API-Key` del workflow).
5. El **correo del administrador** que recibirá las alertas de error.

---

## 2. Estructura exacta del Google Forms

### 2.1 Crear el formulario

1. Entra a <https://forms.new> (o <https://docs.google.com/forms>) e inicia sesión
   con la cuenta que será dueña del sistema.
2. En **Título del formulario** escribe exactamente:

   ```text
   Solicitud de soporte técnico
   ```

3. En **Descripción del formulario** escribe:

   ```text
   Registro de solicitudes de soporte técnico del área de Sistemas.
   Al enviar el formulario recibirás por correo tu folio de seguimiento
   (formato SOL-AAAA-NNNN). Tiempo de respuesta estimado: 24 a 72 horas
   hábiles según la prioridad.
   ```

4. En la barra superior, abre **Configuración** y revisa:
   - **Respuestas → Recopilar direcciones de correo electrónico:** **desactivado**.
     El correo se captura como pregunta (paso 2.2, pregunta 2) para no duplicar
     columnas y para que el dato llegue a la API.
   - **Respuestas → Permitir edición de respuestas:** desactivado.
   - **Respuestas → Limitar a 1 respuesta:** desactivado.
   - **Presentación → Mostrar barra de progreso:** opcional (activado).
   - **Presentación → Mensaje de confirmación:**

     ```text
     Tu solicitud fue enviada. En unos minutos recibirás en tu correo el
     folio de seguimiento. Consérvalo para cualquier aclaración.
     ```

### 2.2 Preguntas del formulario

Agrega las preguntas **en este orden** (el orden define el orden de las columnas
en la hoja de cálculo y las fórmulas del dashboard). Usa los títulos **exactos**,
incluyendo acentos y mayúsculas, porque se convierten en los encabezados de la hoja
y el workflow los usa para mapear los datos.

| # | Pregunta (título exacto) | Tipo | Opciones / configuración | ¿Obligatoria? | Columna en Sheets |
| --- | --- | --- | --- | --- | --- |
| 1 | `Nombre completo` | Respuesta corta | Ayuda: "Escribe tu nombre y apellidos como aparecen en la escuela." | **Sí** | B |
| 2 | `Correo electrónico` | Respuesta corta | Ayuda: "Aquí recibirás tu folio. Revisa que no tenga errores." Validación de respuesta: **Texto → Dirección de correo electrónico** | **Sí** | C |
| 3 | `Teléfono de contacto` | Respuesta corta | Ayuda: "10 dígitos. Opcional, solo si necesitamos llamarte." Sin validación | No | D |
| 4 | `Área o departamento` | **Desplegable** | Opciones (en este orden): `Dirección` · `Recursos Humanos` · `Contabilidad` · `Ventas` · `Almacén` · `Sistemas` · `Otro` | No | E |
| 5 | `Categoría del problema` | **Opción múltiple** | Opciones (en este orden, sin "Otra"): `Hardware` · `Software` · `Redes e Internet` · `Accesos y contraseñas` · `Impresoras` · `Otro` | **Sí** | F |
| 6 | `Prioridad de atención` | **Opción múltiple** | Opciones (en este orden): `Baja` · `Media` · `Alta` · `Crítica`. Descripción: "Baja = puedo seguir trabajando; Media = afecta mi trabajo; Alta = no puedo continuar; Crítica = afecta a varias personas o a un servicio completo." | **Sí** | G |
| 7 | `Nivel de afectación` | **Escala lineal** | Escala de **1 a 5**, etiqueta izquierda `1 = Leve`, etiqueta derecha `5 = No puedo trabajar` | No | H |
| 8 | `Descripción detallada del problema` | **Párrafo** | Ayuda: "Describe qué pasó, cuándo empezó, el mensaje de error y el equipo o sala afectados (mínimo 10 caracteres)." | **Sí** | I |

> La columna **A** (`Marca temporal`) la crea automáticamente Google Forms y **no
> se puede ni se debe mover ni renombrar**: el workflow la usa como llave para
> localizar la fila al escribir el folio.

Notas sobre las preguntas:

1. No agregues preguntas nuevas ni cambies el orden después de crear la hoja:
   Google Forms inserta una columna nueva en medio de las respuestas y las
   fórmulas del dashboard se desalinean.
2. La **escala lineal** no se envía a la API (el contrato no la incluye), pero se
   conserva en la hoja y se usa en el dashboard como indicador de afectación.
3. Si necesitas que la descripción tenga mínimo de caracteres, activa la
   validación de longitud si tu versión de Forms la ofrece; si no, el contenido de
   ayuda es suficiente (la API también rechaza descripciones de menos de 10
   caracteres).
4. Las opciones de `Categoría del problema` y `Prioridad de atención` deben
   coincidir **exactamente** con los valores válidos de la API:
   - Categorías: `Hardware`, `Software`, `Redes e Internet`, `Accesos y contraseñas`,
     `Impresoras`, `Otro`.
   - Prioridades: `Baja`, `Media`, `Alta`, `Crítica`.
   El workflow normaliza acentos, mayúsculas y espacios, pero es mejor que el
   formulario ya entregue el valor canónico.

### 2.3 Vista previa y prueba

1. Pulsa el ícono del **ojo** (Vista previa) y llena el formulario una vez con
   datos falsos para confirmar que:
   - todas las preguntas obligatorias aparecen con asterisco,
   - el desplegable de área y la escala funcionan,
   - aparece el mensaje de confirmación.
2. **Borra esa respuesta de prueba** antes de vincular la hoja o de activar n8n
   (Formulario → Respuestas → menú ⋯ → "Eliminar todas las respuestas") para
   iniciar con la hoja limpia.

---

## 3. Vinculación del formulario a una hoja de cálculo

1. Abre el formulario y ve a la pestaña **Respuestas**.
2. Pulsa **Vincular a Hojas de cálculo**.
3. Elige **Crear una hoja de cálculo nueva** y asígnale un nombre, por ejemplo:

   ```text
   Solicitudes de soporte técnico - Registro
   ```

   > Si prefieres una hoja existente, elige "Seleccionar hoja de cálculo existente".
   > En cualquiera de los dos casos, el Form crea (o reutiliza) una pestaña para
   > las respuestas.
4. Pulsa **Crear**. Google Sheets se abrirá con la pestaña de respuestas.
5. Renombra la pestaña exactamente como:

   ```text
   Respuestas de formulario 1
   ```

   (doble clic sobre el nombre de la pestaña → escribe el nombre → Enter).

   > El workflow tiene escrito ese nombre en los nodos de Google Sheets. Si tu
   > Google está en inglés, la pestaña nace como `Form Responses 1` y **debes**
   > renombrarla o ajustar el parámetro `Sheet` de los dos nodos de Google Sheets.

6. Verifica la **fila 1 (encabezados)**. Debe verse así, en este orden:

   | Columna | A | B | C | D | E | F | G | H | I |
   | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
   | Encabezado | `Marca temporal` | `Nombre completo` | `Correo electrónico` | `Teléfono de contacto` | `Área o departamento` | `Categoría del problema` | `Prioridad de atención` | `Nivel de afectación` | `Descripción detallada del problema` |

7. Conserva el **idioma y la configuración regional** de la hoja (por ejemplo
   `Español (México)`, zona horaria `(GMT-06:00) Ciudad de México`). La zona
   horaria no afecta al workflow (la API devuelve fechas ISO 8601 con offset
   `-06:00`), pero sí a cómo se muestran las fechas del dashboard.

8. Copia el **ID del spreadsheet** (lo necesitarás en n8n): es el fragmento entre
   `/d/` y `/edit` de la URL.

   ```text
   https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789/edit
                                            └──────────── ID ────────────┘
   ```

---

## 4. Columnas adicionales a la derecha de las respuestas

El formulario escribe **solo** las columnas A–I. Las columnas J–M son columnas
propias de la hoja que n8n llenará después de registrar la solicitud en la API.

### 4.1 Crear los encabezados

1. En la hoja `Respuestas de formulario 1`, escribe en la fila 1 (continúa después
   de la última columna del formulario):

   | Columna | Encabezado exacto | Quién lo llena |
   | --- | --- | --- |
   | J | `Folio` | n8n (respuesta de la API) |
   | K | `Estado` | n8n (la API lo crea como `Pendiente`) |
   | L | `Fecha de registro` | n8n (fecha ISO 8601 de la API) |
   | M | `Correo enviado` | n8n (escribe `Sí` al enviar el correo) |

2. Selecciona las columnas J a M y aplica formato de **Texto sin formato**
   (menú *Formato → Número → Texto sin formato*). Así el folio, el estado y la
   fecha no se reinterpretan como números ni como fechas.
3. Opcional pero recomendado: en la columna K agrega una validación de datos para
   que el estado solo acepte los valores del sistema:
   1. Selecciona `K2:K1000`.
   2. Menú **Datos → Validación de datos**.
   3. Criterio: **Lista de elementos**; valores: `Pendiente, En proceso, Resuelto, Cerrado`.
   4. En "Si los datos no son válidos": **Mostrar advertencia** (no rechazar, para
      no bloquear la escritura automática de n8n).
4. Ajusta el ancho de las columnas y congela la fila 1 (*Ver → Inmovilizar → 1 fila*).

### 4.2 Por qué esto NO rompe el formulario

1. Google Forms considera "suyas" únicamente las columnas de sus preguntas
   (A–I) y las columnas extra a la **derecha** (J–M) quedan vacías en cada
   respuesta nueva; por eso se pueden usar como columnas de control.
2. **No insertes filas por encima de la fila 1** ni columnas a la izquierda: la
   fila de encabezados debe seguir siendo la fila 1 y `Marca temporal` debe seguir
   en la columna A.
3. **No renombres, muevas ni borres** encabezados. Si más adelante editas el
   formulario y agregas una pregunta, Google insertará su columna **en medio** de
   las respuestas; en ese caso vuelve a revisar las fórmulas y el nodo de Google
   Sheets (ver sección 11).
4. Si borras una respuesta desde el formulario, la fila se elimina en la hoja y
   el dashboard se recalcula solo.

---

## 5. Pestaña Dashboard: indicadores, fórmulas y gráficas

### 5.1 Preparar la pestaña

1. En el mismo spreadsheet, pulsa **+** (agregar hoja) y renombra la pestaña como:

   ```text
   Dashboard
   ```

2. Deja el dashboard como **primera pestaña** si quieres que se abra al iniciar
   (arrástrala a la izquierda de `Respuestas de formulario 1`). El dashboard solo
   lee datos; no se escribe desde n8n.
3. Ajusta el idioma de la hoja: **Archivo → Configuración → Configuración
   regional → México**, y el separador de argumentos será **punto y coma (`;`)**.

> **Nombres de funciones y separador.** Google Sheets traduce los nombres de las
> funciones según el idioma de la hoja. Las fórmulas de esta guía están escritas
> para una hoja en **español (México)** con separador `;`. Si tu hoja está en
> inglés, cambia los nombres según la tabla de equivalencias del paso 5.8.

### 5.2 Bloque de indicadores (celdas A1:B13)

1. En `A1` escribe el título y combínalo con `A1:H1`:
   **`DASHBOARD · Solicitudes de soporte técnico`** (negrita, tamaño 14, fondo azul
   `#1d4ed8`, texto blanco, centrado).
2. Escribe los encabezados `A3: Indicador` y `B3: Valor` (negrita, fondo gris
   `#e5e7eb`).
3. Llena las celdas con estas etiquetas y fórmulas **exactas**:

| Celda | Etiqueta | Fórmula (pegar en la celda) |
| --- | --- | --- |
| A4 | Total de solicitudes | `=CONTARA('Respuestas de formulario 1'!A2:A)` |
| A5 | Pendientes | `=CONTAR.SI('Respuestas de formulario 1'!K2:K;"Pendiente")` |
| A6 | En proceso | `=CONTAR.SI('Respuestas de formulario 1'!K2:K;"En proceso")` |
| A7 | Resueltas | `=CONTAR.SI('Respuestas de formulario 1'!K2:K;"Resuelto")` |
| A8 | Cerradas | `=CONTAR.SI('Respuestas de formulario 1'!K2:K;"Cerrado")` |
| A9 | Folios generados | `=CONTARA('Respuestas de formulario 1'!J2:J)` |
| A10 | Correos enviados | `=CONTAR.SI('Respuestas de formulario 1'!M2:M;"Sí")` |
| A11 | Últimas 24 horas | `=CONTAR.SI.CONJUNTO('Respuestas de formulario 1'!A2:A;">="&(AHORA()-1);'Respuestas de formulario 1'!A2:A;"<="&AHORA())` |
| A12 | Últimos 7 días | `=CONTAR.SI.CONJUNTO('Respuestas de formulario 1'!A2:A;">="&(AHORA()-7);'Respuestas de formulario 1'!A2:A;"<="&AHORA())` |
| A13 | Alta o Crítica (COUNTA filtrado) | `=CONTARA(FILTRAR('Respuestas de formulario 1'!A2:A;('Respuestas de formulario 1'!G2:G="Alta")+('Respuestas de formulario 1'!G2:G="Crítica")))` |

Explicación rápida de cada función:

- `CONTARA` (COUNTA) cuenta las filas con `Marca temporal` no vacía = total de
  solicitudes reales (ignora filas vacías al final de la hoja).
- `CONTAR.SI` (COUNTIF) cuenta cuántas filas tienen un valor exacto en una columna.
- `CONTAR.SI.CONJUNTO` (COUNTIFS) combina dos criterios; aquí se usa para contar
  fechas dentro de un rango móvil de 24 h o 7 días con `AHORA()` (NOW).
- `CONTARA(FILTRAR(...))` (COUNTA + FILTER) cuenta las filas que cumplen un
  criterio calculado (prioridad Alta **o** Crítica), algo que `CONTAR.SI` no puede
  hacer con dos valores a la vez.

### 5.3 Tabla "Solicitudes por categoría" (A15:B22)

1. En `A15` escribe **`Solicitudes por categoría`** (negrita, fondo azul claro).
2. En `A16` = `Categoría` y en `B16` = `Total`.
3. Llena las categorías y sus fórmulas:

| Celda | Valor / Fórmula |
| --- | --- |
| A17 | `Hardware` |
| A18 | `Software` |
| A19 | `Redes e Internet` |
| A20 | `Accesos y contraseñas` |
| A21 | `Impresoras` |
| A22 | `Otro` |
| B17 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A17)` |
| B18 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A18)` |
| B19 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A19)` |
| B20 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A20)` |
| B21 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A21)` |
| B22 | `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A22)` |

> Alternativa: en `B17` pega `=CONTAR.SI('Respuestas de formulario 1'!F2:F;A17)`
> y arrastra el tirador de relleno hasta `B22`.

### 5.4 Tabla "Solicitudes por prioridad" (D15:E20)

| Celda | Valor / Fórmula |
| --- | --- |
| D15 | `Solicitudes por prioridad` (título, negrita) |
| D16 | `Prioridad` · E16: `Total` |
| D17 | `Baja` |
| D18 | `Media` |
| D19 | `Alta` |
| D20 | `Crítica` |
| E17 | `=CONTAR.SI('Respuestas de formulario 1'!G2:G;D17)` |
| E18 | `=CONTAR.SI('Respuestas de formulario 1'!G2:G;D18)` |
| E19 | `=CONTAR.SI('Respuestas de formulario 1'!G2:G;D19)` |
| E20 | `=CONTAR.SI('Respuestas de formulario 1'!G2:G;D20)` |

Indicador extra sugerido:

| Celda | Etiqueta | Fórmula |
| --- | --- | --- |
| D22 | Crítica sin atender | `=CONTAR.SI.CONJUNTO('Respuestas de formulario 1'!G2:G;"Crítica";'Respuestas de formulario 1'!K2:K;"Pendiente")` |

### 5.5 Tabla "Solicitudes por estado" con QUERY (G15)

1. En `G15` escribe el título **`Solicitudes por estado (QUERY)`**.
2. En `G16` pega **una sola fórmula**; el resultado se derrama automáticamente en
   las filas y columnas siguientes:

   ```text
   =CONSULTA('Respuestas de formulario 1'!A1:M;"select K, count(K) where K is not null group by K label K 'Estado', count(K) 'Total'";1)
   ```

   Esta fórmula agrupa las filas por la columna K (`Estado`), cuenta cuántas hay de
   cada valor y devuelve una tabla de dos columnas. El `1` final indica que la
   primera fila del rango son los encabezados.

### 5.6 Indicador extra: nivel de afectación (J15:J16)

| Celda | Contenido |
| --- | --- |
| J15 | `Solicitudes con afectación 4 o 5` (negrita) |
| J16 | `=CONTAR.SI('Respuestas de formulario 1'!H2:H;">=4")` |

### 5.7 Formato visual y formato condicional

1. Da formato de número entero (`0`) a `B4:B13`, `B17:B22`, `E17:E20` y `J16`.
2. Centra las columnas de totales y aplica bordes suaves a las tablas.
3. **Formato condicional para prioridad** (requisito):
   1. Selecciona `G2:G1000` (columna `Prioridad de atención`).
   2. Menú **Formato → Formato condicional**.
   3. Crea **reglas de texto**, en este orden (el orden importa):
      - "El texto contiene" `Crítica` → fondo `#b91c1c`, texto blanco, negrita.
      - "El texto contiene" `Alta` → fondo `#f59e0b`, texto blanco, negrita.
      - "El texto contiene" `Media` → fondo `#facc15`, texto negro.
      - "El texto contiene" `Baja` → fondo `#dcfce7`, texto negro.
4. **Formato condicional opcional para estado** (columna `K2:K1000`):
   - `Pendiente` → fondo `#fee2e2`
   - `En proceso` → fondo `#fef3c7`
   - `Resuelto` → fondo `#dcfce7`
   - `Cerrado` → fondo `#e5e7eb`
5. Congela la fila 1 de esta hoja y ajusta el ancho de las columnas A–J.

### 5.8 Equivalencias de funciones si tu hoja está en inglés

| Español (México) | Inglés | Qué hace |
| --- | --- | --- |
| `CONTARA` | `COUNTA` | Cuenta celdas no vacías |
| `CONTAR.SI` | `COUNTIF` | Cuenta con un criterio |
| `CONTAR.SI.CONJUNTO` | `COUNTIFS` | Cuenta con varios criterios |
| `FILTRAR` | `FILTER` | Filtra un rango |
| `AHORA` | `NOW` | Fecha y hora actuales |
| `CONSULTA` | `QUERY` | Consulta tipo SQL |

Si al escribir una fórmula aparece `#NAME?` o `#¿NOMBRE?`, tu hoja está en otro
idioma: usa la columna inglesa de la tabla y cambia el separador `;` por `,`.

### 5.9 Insertar las 3 gráficas

**Gráfica 1 — Barras horizontales: solicitudes por categoría**

1. Selecciona el rango `A16:B22` (incluye encabezados).
2. Menú **Insertar → Gráfico**.
3. En el panel de configuración elige **Tipo de gráfico → Barra** (barras
   horizontales), y en "Barras" deja la variante simple.
4. Pestaña **Personalizar**:
   - Título: `Solicitudes por categoría`.
   - Color de las barras: `#1d4ed8`.
   - Leyenda: **Ninguna**.
   - Etiquetas de datos: activar "Valor".
5. Arrastra la gráfica a la celda `A25` y redimensiónala (por ejemplo 700 × 320 px).

**Gráfica 2 — Pastel: distribución por prioridad**

1. Selecciona `D16:E20`.
2. **Insertar → Gráfico → Tipo de gráfico → Circular** (pastel).
3. Personalizar:
   - Título: `Distribución por prioridad`.
   - Colores por sector: `Crítica` = `#b91c1c`, `Alta` = `#f59e0b`,
     `Media` = `#facc15`, `Baja` = `#16a34a`.
   - Etiqueta: "Porcentaje" y "Valor" (opcional).
   - Leyenda: a la derecha.
4. Colócala en `G25` (aprox. 640 × 320 px).

**Gráfica 3 — Columnas: solicitudes por estado**

1. Selecciona las celdas del resultado de la QUERY (`G16:H20`); si aparecen más
   filas, amplía el rango hasta la última fila con datos.
2. **Insertar → Gráfico → Tipo de gráfico → Columna** (columnas verticales).
3. Personalizar:
   - Título: `Solicitudes por estado`.
   - Color: `#0f766e`.
   - Etiquetas de datos: activar "Valor".
   - Leyenda: ninguna.
4. Colócala en `D41` (aprox. 640 × 320 px).

> **Importante:** las gráficas apuntan a rangos fijos; si insertas filas o
> columnas en medio de las tablas, vuelve a revisar el rango de datos de cada
> gráfica (clic derecho → *Rango de datos*).

---

## 6. Verificación de punta a punta

Con el formulario vinculado, el workflow de n8n configurado y **activo**:

1. Abre el formulario publicado (botón **Enviar → Enlace**) y llena una respuesta
   de prueba con datos reales de prueba:

   ```text
   Nombre completo: Ana María Pérez
   Correo electrónico: ana.perez@ejemplo.com
   Teléfono de contacto: 5512345678
   Área o departamento: Recursos Humanos
   Categoría del problema: Redes e Internet
   Prioridad de atención: Crítica
   Nivel de afectación: 5
   Descripción detallada del problema: No tengo internet desde ayer en el equipo de mi escritorio.
   ```

2. Pulsa **Enviar** y espera el mensaje de confirmación.
3. Abre la hoja `Respuestas de formulario 1`. En **menos de ~1–2 minutos** debe
   verse una fila nueva con:
   - `Marca temporal` con la fecha y hora del envío (columna A),
   - tus respuestas en B–I,
   - **J `Folio`** = `SOL-AAAA-NNNN` (por ejemplo `SOL-2026-0001`),
   - **K `Estado`** = `Pendiente`,
   - **L `Fecha de registro`** = fecha ISO 8601, por ejemplo
     `2026-11-10T22:35:41-06:00`,
   - **M `Correo enviado`** = `Sí`.
4. Revisa el correo del solicitante (`ana.perez@ejemplo.com`): debe llegar un
   correo HTML con el folio, la categoría, la prioridad, el estado, la fecha y el
   resumen de la descripción.
5. Abre la pestaña **Dashboard**:
   - `B4` (Total) aumentó en 1,
   - `B5` (Pendientes) aumentó en 1,
   - la categoría `Redes e Internet` y la prioridad `Crítica` suman 1,
   - la gráfica de pastel y la de barras se actualizan.
6. Revisa en n8n la ejecución: **Executions → última ejecución** debe estar en
   verde (`Success`) y mostrar los nodos
   `Google Sheets Trigger → Normalizar fila → Registrar en API → ¿Respuesta OK? →
   ¿Ya estaba registrada? → Correo al solicitante → Escribir folio en la hoja`.
7. Comprueba la API (endpoints públicos, sin API key):

   ```text
   https://<tu-servicio>.onrender.com/api/solicitudes?limit=1
   https://<tu-servicio>.onrender.com/api/estadisticas
   ```

   El listado debe incluir el folio generado y las estadísticas deben coincidir
   con los totales del dashboard.

Si algo falla, revisa la sección 11 (Solución de problemas).

---

## 7. Mapeo columna del formulario → campo de la API

El nodo **Code → `Normalizar fila`** del workflow transforma la fila del
formulario en el cuerpo JSON que espera `POST /api/solicitudes`:

| Columna del formulario | Columna en Sheets | Campo de la API | Transformación que aplica n8n |
| --- | --- | --- | --- |
| `Marca temporal` | A | `id_externo` | `"form-"` + la marca temporal sin signos (por ejemplo `form-10112026223541`). Sirve para no duplicar registros si el workflow se reintenta |
| `Nombre completo` | B | `nombre` | Recorta espacios y colapsa espacios repetidos |
| `Correo electrónico` | C | `correo` | Recorta espacios y pasa a minúsculas |
| `Teléfono de contacto` | D | `telefono` | Recorta; si viene vacío manda `null` |
| `Área o departamento` | E | `area` | Recorta; si viene vacío manda `null` |
| `Categoría del problema` | F | `categoria` | Normaliza acentos, mayúsculas y sinónimos al valor canónico; si no lo reconoce manda `Otro` |
| `Prioridad de atención` | G | `prioridad` | Normaliza acentos, mayúsculas y sinónimos (`urgente` → `Crítica`); si no lo reconoce manda `Media` |
| `Descripción detallada del problema` | I | `descripcion` | Recorta y colapsa espacios |
| `Nivel de afectación` | H | — | No se envía a la API; se queda en la hoja para el dashboard |

Ejemplo del JSON que n8n envía:

```json
{
  "nombre": "Ana María Pérez",
  "correo": "ana.perez@ejemplo.com",
  "telefono": "5512345678",
  "area": "Recursos Humanos",
  "categoria": "Redes e Internet",
  "prioridad": "Crítica",
  "descripcion": "No tengo internet desde ayer en el equipo de mi escritorio.",
  "id_externo": "form-10112026223541"
}
```

Y la respuesta `201` de la API que consume n8n:

```json
{
  "ok": true,
  "mensaje": "Solicitud registrada correctamente.",
  "data": {
    "id": 1,
    "folio": "SOL-2026-0001",
    "nombre": "Ana María Pérez",
    "correo": "ana.perez@ejemplo.com",
    "telefono": "5512345678",
    "area": "Recursos Humanos",
    "categoria": "Redes e Internet",
    "prioridad": "Crítica",
    "descripcion": "No tengo internet desde ayer en el equipo de mi escritorio.",
    "estado": "Pendiente",
    "notas": null,
    "id_externo": "form-10112026223541",
    "correo_enviado": false,
    "fecha_registro": "2026-11-10T22:35:41-06:00",
    "fecha_actualizacion": null
  }
}
```

> Nota: la columna **M `Correo enviado`** se escribe con `Sí` desde el nodo de
> n8n (no la llena la API), y es la evidencia visible de que la notificación salió.
> La API guarda su propio campo `correo_enviado` (por defecto `false`).

---

## 8. Configuración del workflow de n8n

### 8.1 Importar el workflow

1. Descarga el archivo [`../n8n/workflow-solicitudes.json`](../n8n/workflow-solicitudes.json).
2. En n8n entra a **Workflows → Add workflow**.
3. Abre el menú **⋯** (arriba a la derecha) → **Import from File…** y selecciona el
   archivo. También funciona **Import from clipboard** si copias el contenido JSON.
4. El workflow se abre con este grafo:

   ```
   Google Sheets Trigger ─▶ Normalizar fila ─▶ Registrar en API ─▶ ¿Respuesta OK?
                                                                     │  ├─ true ─▶ ¿Ya estaba registrada? ─┬─ true ─▶ Duplicado: no reenviar
                                                                     │  │                                   └─ false ─▶ Correo al solicitante ─▶ Escribir folio en la hoja
                                                                     │  └─ false ─▶ Alerta al administrador ─▶ Detener con error
                                                                     └─ (error de red) ─▶ Alerta al administrador
   ```

5. La nota amarilla **Configuración** dentro del lienzo resume los reemplazos que
   se explican en el paso 8.2.

### 8.2 Reemplazos y credenciales (obligatorio)

Abre cada nodo y sustituye los valores de ejemplo:

| Nodo | Parámetro | Valor de ejemplo | Debes poner |
| --- | --- | --- | --- |
| `Registrar en API` | `URL` | `https://TU-SERVICIO.onrender.com/api/solicitudes` | `https://<tu-servicio>.onrender.com/api/solicitudes` |
| `Registrar en API` | Header `X-API-Key` | `TU-API-KEY-AQUI` | El valor de `API_KEY` configurado en Render |
| `Google Sheets Trigger` | `Document` | `PEGA_AQUI_EL_ID_DEL_SPREADSHEET` | ID del spreadsheet (sección 3, paso 8) |
| `Google Sheets Trigger` | `Sheet` | `Respuestas de formulario 1` | Nombre exacto de la pestaña de respuestas |
| `Escribir folio en la hoja` | `Document` / `Sheet` | igual que el trigger | Los mismos valores |
| `Alerta al administrador` | `To` | `soporte-admin@ejemplo.com` | Correo real del administrador |
| Ambos nodos Gmail | Credencial | `REEMPLAZA_ID_DE_CREDENCIAL` | Tu credencial **Gmail OAuth2** |
| Nodos Google Sheets | Credencial | `REEMPLAZA_ID_DE_CREDENCIAL` | Tu credencial **Google Sheets OAuth2** (el trigger usa `googleSheetsTriggerOAuth2Api`) |

> El header `X-API-Key` se puede mover a una credencial **Header Auth** de n8n
> (parámetro `Authentication → Generic Credential Type → Header Auth`), lo cual es
> más seguro si el workflow se comparte o se sube al repositorio. Para el proyecto
> escolar, el valor directo es aceptable; **nunca subas la clave real al repositorio**.

Cómo seleccionar las credenciales:

1. Abre cada nodo de Google (trigger y actualización) → campo **Credential** →
   **Create new** (si es la primera vez) o elige la credencial OAuth2 existente.
2. Si el nodo muestra "Couldn't load the columns" o "credential not found", primero
   asigna la credencial y luego vuelve a seleccionar el documento y la hoja desde
   el desplegable.
3. La creación del proyecto de Google Cloud, la pantalla de consentimiento y las
   credenciales OAuth2 se explican en
   [`guia-despliegue-render-neon.md`](guia-despliegue-render-neon.md).

### 8.3 Versiones de nodo (typeVersion) del JSON

El archivo usa estas versiones de nodo; son versiones estables del catálogo de n8n:

| Nodo | Tipo | `typeVersion` |
| --- | --- | --- |
| Configuración (nota) | `n8n-nodes-base.stickyNote` | 1 |
| Google Sheets Trigger | `n8n-nodes-base.googleSheetsTrigger` | 1 |
| Normalizar fila | `n8n-nodes-base.code` | 2 |
| Registrar en API | `n8n-nodes-base.httpRequest` | 4.2 |
| ¿Respuesta OK? / ¿Ya estaba registrada? | `n8n-nodes-base.if` | 2.2 |
| Correo al solicitante / Alerta al administrador | `n8n-nodes-base.gmail` | 2.1 |
| Escribir folio en la hoja | `n8n-nodes-base.googleSheets` | 4.5 |
| Duplicado: no reenviar | `n8n-nodes-base.noOp` | 1 |
| Detener con error | `n8n-nodes-base.stopAndError` | 1 |

Si al importar aparece un aviso del tipo *"Node type version not found"* o un nodo
se muestra como desconocido, tu instancia de n8n es anterior a esa versión de nodo:

1. Abre el nodo afectado, pulsa el ícono de **engranaje** (configuración del nodo)
   y en **Node version** elige la versión más reciente que ofrezca tu instalación.
2. Alternativamente, elimina el nodo y vuélvelo a crear desde el panel de nodos
   (la configuración es equivalente).
3. Versiones objetivo recomendadas: **n8n Cloud** (siempre actualizado) o
   **self-hosted 1.60 o superior**. El trigger de Google Sheets solo tiene la
   versión 1 en el catálogo (no existe 1.2, aunque algunas plantillas lo citen).

### 8.4 Qué hace cada nodo

| Nodo | Función |
| --- | --- |
| `Google Sheets Trigger` | Consulta la hoja de respuestas y dispara el workflow cuando aparece una fila nueva (`Row Added`) |
| `Normalizar fila` | Convierte la fila del formulario en el JSON de la API, recorta espacios, normaliza acentos y calcula `id_externo` |
| `Registrar en API` | `POST /api/solicitudes` con `Content-Type: application/json` y `X-API-Key`; timeout de 60 s; devuelve el cuerpo aunque el código HTTP no sea 2xx (`Never Error`) para poder clasificar el error |
| `¿Respuesta OK?` | Éxito si `ok = true` **y** `data.folio` viene con valor |
| `¿Ya estaba registrada?` | Si la API responde `duplicado: true` (reintento), no reenvía el correo ni reescribe la hoja |
| `Correo al solicitante` | Correo HTML con folio, categoría, prioridad, estado, fecha y resumen |
| `Escribir folio en la hoja` | `Append or Update Row` en la hoja de respuestas: escribe `Folio`, `Estado`, `Fecha de registro` y `Correo enviado`, localizando la fila por la columna `Marca temporal` |
| `Alerta al administrador` | Correo HTML con el motivo del fallo, los datos enviados y la respuesta/error de la API |
| `Detener con error` | Marca la ejecución como fallida para que el error sea visible en **Executions** |
| `Duplicado: no reenviar` | Termina el flujo sin acciones (No Operation) cuando la solicitud ya existía |

Ramas del workflow:

- **Éxito nuevo (201):** correo al solicitante + actualización de la hoja.
- **Duplicado (200, `duplicado: true`):** el flujo termina en el nodo No Operation
  (no se manda un segundo correo).
- **Error (400/401/503 o fallo de red):** correo al administrador y ejecución
  marcada como error.

---

## 9. Cómo probar el workflow

### 9.1 Verificar la API antes de probar n8n

1. Prueba los endpoints públicos en el navegador o con `curl`:

   ```bash
   curl https://<tu-servicio>.onrender.com/health
   curl https://<tu-servicio>.onrender.com/api/estadisticas
   ```

2. Prueba el `POST` con un `id_externo` de prueba (después podrás borrar el
   registro o dejarlo como evidencia):

   ```bash
   curl -X POST https://<tu-servicio>.onrender.com/api/solicitudes \
     -H "Content-Type: application/json" \
     -H "X-API-Key: <TU_API_KEY>" \
     -d '{"nombre":"Prueba n8n","correo":"prueba@ejemplo.com","telefono":null,"area":null,"categoria":"Hardware","prioridad":"Media","descripcion":"Registro de prueba desde curl para validar la API.","id_externo":"form-prueba-001"}'
   ```

   Debe responder `201` con `"folio": "SOL-AAAA-NNNN"`. Si repites el mismo
   comando, debe responder `200` con `"duplicado": true` (idempotencia).

### 9.2 Probar el trigger y el workflow

1. Abre el workflow en n8n y pulsa **Execute workflow** (abajo al centro).
2. El nodo `Google Sheets Trigger` se ejecuta en **modo manual** y devuelve las
   filas de la hoja:

   > **Advertencia importante:** en modo manual el trigger devuelve **todas** las
   > filas existentes (no solo la última). Por eso, la primera prueba manual
   > registrará **todas** las respuestas que ya tenga la hoja y enviará un correo
   > por cada una. Haz la primera prueba con la hoja vacía (una sola respuesta de
   > prueba) para no generar correos masivos.

3. Observa el resultado de cada nodo:
   - `Normalizar fila` debe mostrar el JSON con los 8 campos de la API.
   - `Registrar en API` debe mostrar la respuesta `201` con `folio`.
   - `Correo al solicitante` debe quedar en verde y el correo debe llegar.
   - `Escribir folio en la hoja` debe escribir J–M en la fila correcta.
4. **Prueba la rama de error:** abre `Registrar en API` y cambia temporalmente el
   header `X-API-Key` por `clave-incorrecta`, ejecuta el workflow y verifica que:
   - llega el correo de alerta al administrador con el motivo `No autorizado.`,
   - la ejecución termina en rojo por el nodo `Detener con error`.
   Después **restaura** la clave correcta.
5. **Prueba la idempotencia:** vuelve a ejecutar el workflow con la misma fila. La
   API responderá `200` con `"duplicado": true`; el flujo debe terminar en
   `Duplicado: no reenviar`, sin segundo correo al solicitante.
6. Cuando todo funcione, activa el workflow con el interruptor **Active** (arriba a
   la derecha). A partir de ese momento n8n consulta la hoja aproximadamente cada
   minuto y procesa solo las filas **nuevas**.

> Al activarse, n8n registra el estado actual de la hoja como línea base: las
> respuestas que ya existían **no** se reenvían. Solo se procesan las que lleguen
> después de la activación.

### 9.3 Prueba sin enviar el formulario

Si no quieres llenar el formulario, agrega una fila de prueba directamente al final
de la hoja `Respuestas de formulario 1` (misma cantidad de columnas A–I). El
trigger la detectará como fila nueva en la siguiente consulta. **No escribas nada
en J–M**: esas columnas las llena el workflow.

---

## 10. Notas sobre el trigger de Google Sheets

1. **Nombre de la hoja.** El trigger y el nodo de actualización están configurados
   con la pestaña `Respuestas de formulario 1`. Si renombras la pestaña, debes
   actualizar el parámetro `Sheet` en **ambos** nodos de Google Sheets.
2. **Rango y columnas.** El trigger lee el rango `A:ZZZ` de la hoja y usa la fila 1
   como encabezados. Por eso:
   - la fila 1 no se puede eliminar ni mover,
   - todos los encabezados deben estar en la fila 1,
   - las columnas deben conservar el nombre exacto (sección 2.2).
3. **Intervalo de consulta.** El nodo `Google Sheets Trigger` no tiene un parámetro
   de intervalo: n8n consulta los triggers de tipo *polling* aproximadamente cada
   **minuto** (n8n Cloud y self-hosted). Por eso el folio puede tardar hasta ~1–2
   minutos en aparecer en la hoja después de enviar el formulario.
4. **Evento `Row Added`.** Solo se dispara cuando se **agrega** una fila; las
   actualizaciones que hace n8n en J–M no vuelven a disparar el workflow (no hay
   riesgo de ciclo). No cambies el evento a `Row Updated` ni `Row Added or
   Updated`: esas variantes requieren permisos de edición ampliados y sí podrían
   provocar ejecuciones repetidas al escribir el folio.
5. **Prueba manual vs. producción.** En modo manual el trigger devuelve todas las
   filas; en producción devuelve solo las nuevas desde la última consulta (ver
   sección 9.2).
6. **Columna `Marca temporal` intacta.** El nodo `Escribir folio en la hoja` busca
   la fila comparando ese valor; si editas a mano la marca temporal de una fila ya
   procesada, una nueva ejecución podría no encontrarla y agregar una fila extra.
7. **Una respuesta por ejecución.** El workflow está pensado para que cada consulta
   traiga una fila nueva (lo normal con respuestas humanas y consultas cada
   minuto). Si muchas personas envían el formulario en el mismo minuto, n8n procesa
   las filas en lote y la escritura de J–M puede quedar anclada a la primera fila
   del lote; en ese caso revisa la hoja y, si es necesario, actualiza esas celdas a
   mano (el registro en PostgreSQL y el folio por correo no se pierden).

---

## 11. Solución de problemas

| Síntoma | Causa probable | Solución |
| --- | --- | --- |
| El trigger no dispara | Workflow inactivo, hoja o pestaña mal seleccionada | Activa el workflow; verifica que la pestaña se llame igual en el trigger y en el nodo de actualización |
| `400` con `errores` de la API | Falta un campo obligatorio, correo inválido, descripción de menos de 10 caracteres o prioridad no reconocida | Revisa el JSON en el nodo `Normalizar fila`; corrige el dato en la hoja y ejecuta de nuevo (el `id_externo` evita duplicados) |
| `401 No autorizado` | Header `X-API-Key` ausente o distinto al de Render | Copia de nuevo el valor de `API_KEY` en el nodo `Registrar en API` |
| `503 Servicio de base de datos no disponible` | Neon suspendido o credenciales de base incorrectas | Espera unos segundos y reintenta; revisa los logs de Render y `DATABASE_URL` |
| La primera petición tarda mucho | Cold start del plan gratuito de Render | Es normal (30–60 s). El timeout del nodo es de 60 s |
| `Couldn't load the columns` en Google Sheets | Falta la credencial OAuth2 o el documento no está seleccionado | Asigna la credencial, elige el documento y la hoja; vuelve a cargar las columnas |
| `Column names were updated after the node's setup` | Los encabezados de la hoja no coinciden con los del workflow | Restaura los encabezados exactos de la sección 2.2 o vuelve a seleccionar las columnas en el nodo |
| El folio no aparece en la hoja pero el correo sí llegó | El nodo `Escribir folio en la hoja` falló o no encontró la fila por `Marca temporal` | Revisa la ejecución en n8n; confirma que la columna A no se editó y que la hoja no está protegida |
| Llega el correo de alerta al administrador | La API devolvió error o hubo fallo de red | Lee el "motivo reportado" del correo y la ejecución en n8n |
| Aparecen filas extra sin datos del formulario | Una ejecución previa no encontró la fila y agregó datos | Borra esas filas; verifica la columna `Marca temporal` y no la edites |
| `#NAME?` / `#¿NOMBRE?` en el dashboard | Nombres de función en otro idioma | Usa la tabla de equivalencias (sección 5.8) |
| Una columna nueva desalineó el dashboard | Se agregó una pregunta al formulario | Corrige las referencias de las fórmulas y del nodo de Google Sheets |

---

## 12. Checklist de entrega

**Google Forms**

- [ ] Título `Solicitud de soporte técnico` y descripción capturados.
- [ ] 8 preguntas en el orden de la sección 2.2, con los tipos y opciones exactos.
- [ ] Correo se captura como pregunta (no con "Recopilar direcciones de correo").
- [ ] Preguntas 1, 2, 5, 6 y 8 marcadas como obligatorias.
- [ ] Mensaje de confirmación configurado.

**Google Sheets**

- [ ] Formulario vinculado a la hoja de cálculo.
- [ ] Pestaña llamada `Respuestas de formulario 1`.
- [ ] Encabezados A–I idénticos a los de la sección 3.
- [ ] Columnas J–M creadas con los encabezados `Folio`, `Estado`, `Fecha de registro`, `Correo enviado`.
- [ ] Validación de datos de estado (opcional) y formato de texto aplicado.
- [ ] Pestaña `Dashboard` con los 10 indicadores y las 3 tablas de la sección 5.
- [ ] 3 gráficas insertadas: barras (categoría), pastel (prioridad), columnas (estado).
- [ ] Formato condicional de prioridad `Crítica` y `Alta` aplicado.

**n8n**

- [ ] Workflow importado desde `n8n/workflow-solicitudes.json`.
- [ ] URL de Render, `X-API-Key`, ID del spreadsheet, hoja y correo del administrador reemplazados.
- [ ] Credenciales OAuth2 de Google Sheets y Gmail asignadas.
- [ ] Prueba exitosa: fila nueva → folio en J–M → correo al solicitante → dashboard actualizado.
- [ ] Prueba de error: clave incorrecta → correo al administrador → ejecución en rojo.
- [ ] Workflow **Active**.

**Evidencias sugeridas para el reporte**

- [ ] Captura del formulario con las preguntas.
- [ ] Captura de la hoja con una fila completa (A–M) después de la automatización.
- [ ] Captura del correo recibido con el folio.
- [ ] Captura del dashboard con las gráficas.
- [ ] Captura de la ejecución exitosa en n8n (**Executions**).
- [ ] Captura de la respuesta `201` de la API (`/api/solicitudes?limit=1` o Postman).

---

## Referencias

- n8n Docs — *Google Sheets Trigger*: <https://docs.n8n.io/integrations/builtin/trigger-nodes/n8n-nodes-base.googlesheetstrigger/>
- n8n Docs — *Google Sheets node*: <https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.googlesheets/>
- n8n Docs — *HTTP Request node*: <https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/>
- n8n Docs — *Code node*: <https://docs.n8n.io/code/code-node/>
- Google Forms Help — *Vincular un formulario a una hoja de cálculo*: <https://support.google.com/docs/answer/2917686>
- Google Sheets Help — *Lista de funciones*: <https://support.google.com/docs/table/25273>
