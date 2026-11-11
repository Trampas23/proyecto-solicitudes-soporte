"""
===============================================================================
 API REST - Sistema automatizado de gestión de solicitudes de soporte técnico
===============================================================================
Materia : Programación en ambiente cliente servidor
Proyecto: Segundo parcial
Stack   : Python + Flask + PostgreSQL (Neon) + Render + n8n + Google Workspace

Ejecutar en local (desarrollo):
    cp .env.example .env          # y coloca tu DATABASE_URL y API_KEY
    pip install -r requirements.txt
    python app.py                 # http://localhost:5000

Ejecutar en producción (Render):
    gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60

Endpoints (resumen):
    GET    /                              Índice de la API
    GET    /health                        Estado del servicio y de la BD
    POST   /api/solicitudes               Registrar solicitud      (X-API-Key)
    GET    /api/solicitudes               Consultar con filtros
    GET    /api/solicitudes/<folio_o_id>  Consultar una solicitud
    PATCH  /api/solicitudes/<folio>/estado Actualizar estado        (X-API-Key)
    GET    /api/estadisticas              Totales para el dashboard
===============================================================================
"""

from __future__ import annotations

import os
import secrets
from datetime import date, datetime, timezone
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

import database as db
import utilidades as ut

# Carga las variables de .env cuando se ejecuta en local (en Render se usan
# las variables de entorno del servicio). No sobrescribe las ya definidas.
load_dotenv()

VERSION = "1.0.0"
NOMBRE_SERVICIO = "Sistema automatizado de gestión de solicitudes de soporte técnico"

# Zona horaria para presentar las fechas. En PostgreSQL se guardan en UTC
# (TIMESTAMPTZ); aquí se convierten a la hora de México para que n8n y la hoja
# de cálculo muestren una fecha comprensible. Si la zona no está disponible se
# devuelve la fecha en UTC, que también es ISO 8601 válido.
try:
    from zoneinfo import ZoneInfo

    ZONA_HORARIA = ZoneInfo("America/Mexico_City")
except Exception:  # pragma: no cover - depende del sistema operativo
    ZONA_HORARIA = None

app = Flask(__name__)
app.json.sort_keys = False
CORS(app, resources={r"/*": {"origins": os.getenv("CORS_ORIGINS", "*")}})


# =============================================================================
# Utilidades internas de la API
# =============================================================================
def _fecha_iso(valor):
    """Convierte datetime/date de PostgreSQL a texto ISO 8601 (America/Mexico_City)."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        momento = valor if valor.tzinfo is not None else valor.replace(tzinfo=timezone.utc)
        if ZONA_HORARIA is not None:
            momento = momento.astimezone(ZONA_HORARIA)
        return momento.isoformat(timespec="seconds")
    if isinstance(valor, date):
        return valor.isoformat()
    return valor


def _serializar_solicitud(fila: dict) -> dict:
    """Convierte una fila de la tabla en el JSON público de la API."""
    return {
        "id": fila.get("id"),
        "folio": fila.get("folio"),
        "nombre": fila.get("nombre"),
        "correo": fila.get("correo"),
        "telefono": fila.get("telefono"),
        "area": fila.get("area"),
        "categoria": fila.get("categoria"),
        "prioridad": fila.get("prioridad"),
        "descripcion": fila.get("descripcion"),
        "estado": fila.get("estado"),
        "notas": fila.get("notas"),
        "id_externo": fila.get("id_externo"),
        "correo_enviado": fila.get("correo_enviado"),
        "fecha_registro": _fecha_iso(fila.get("fecha_registro")),
        "fecha_actualizacion": _fecha_iso(fila.get("fecha_actualizacion")),
    }


def _error(mensaje: str, codigo: int, errores: dict | None = None, extra: dict | None = None):
    """Construye una respuesta JSON uniforme de error."""
    cuerpo: dict = {"ok": False, "error": mensaje}
    if errores:
        cuerpo["errores"] = errores
    if extra:
        cuerpo.update(extra)
    respuesta = jsonify(cuerpo)
    respuesta.status_code = codigo
    return respuesta


def requiere_api_key(funcion):
    """
    Protege los endpoints de escritura (POST y PATCH).

    La clave se compara contra la variable de entorno API_KEY usando
    secrets.compare_digest (comparación de tiempo constante).
    Si API_KEY no está configurada, los endpoints quedan abiertos: útil
    mientras se desarrolla en local, pero SIEMPRE debe configurarse en Render.
    """

    @wraps(funcion)
    def envoltura(*args, **kwargs):
        esperada = (os.getenv("API_KEY") or "").strip()
        if not esperada:
            return funcion(*args, **kwargs)
        recibida = (request.headers.get("X-API-Key") or "").strip()
        if not secrets.compare_digest(recibida, esperada):
            return _error(
                "No autorizado.",
                401,
                extra={
                    "mensaje": "Incluye el header 'X-API-Key' con la clave correcta. "
                    "El workflow de n8n la envía automáticamente."
                },
            )
        return funcion(*args, **kwargs)

    return envoltura


def _buscar_solicitud(identificador: str) -> dict | None:
    """Busca una solicitud por id numérico o por folio (SOL-AAAA-NNNN)."""
    identificador = (identificador or "").strip()
    if not identificador:
        return None
    if identificador.isdigit():
        return db.consultar_uno("SELECT * FROM solicitudes WHERE id = %s;", (int(identificador),))
    return db.consultar_uno(
        "SELECT * FROM solicitudes WHERE folio = %s;", (identificador.upper(),)
    )


# =============================================================================
# GET /  -> índice de la API
# =============================================================================
@app.get("/")
def indice():
    return (
        jsonify(
            {
                "ok": True,
                "servicio": NOMBRE_SERVICIO,
                "version": VERSION,
                "documentacion": "Consulta el README.md y docs/documentacion-tecnica.md del repositorio.",
                "autenticacion": "Header 'X-API-Key' obligatorio en POST y PATCH (lo envía n8n).",
                "endpoints": {
                    "GET /health": "Estado del servicio y de la base de datos.",
                    "POST /api/solicitudes": "Registrar una nueva solicitud y generar su folio.",
                    "GET /api/solicitudes": "Consultar el listado con filtros y paginación.",
                    "GET /api/solicitudes/{folio_o_id}": "Consultar una solicitud por folio o id.",
                    "PATCH /api/solicitudes/{folio}/estado": "Actualizar el estado de atención.",
                    "GET /api/estadisticas": "Totales por categoría, prioridad y estado.",
                },
                "valores_validos": ut.valores_permitidos(),
                "ejemplo_filtros": "/api/solicitudes?categoria=Hardware&prioridad=Alta&limit=10",
            }
        ),
        200,
    )


# =============================================================================
# GET /health -> estado del servicio (lo usa Render como health check)
# =============================================================================
@app.get("/health")
def health():
    conectada = db.hay_conexion()
    return (
        jsonify(
            {
                "ok": True,
                "servicio": NOMBRE_SERVICIO,
                "version": VERSION,
                "base_datos": "conectada" if conectada else "desconectada",
                "mensaje": (
                    "Servicio operando correctamente."
                    if conectada
                    else "El servicio está en línea, pero no hay conexión con PostgreSQL. "
                    "Revisa DATABASE_URL en Render y que el proyecto de Neon esté activo."
                ),
                "hora": _fecha_iso(datetime.now(timezone.utc)),
            }
        ),
        200,
    )


# =============================================================================
# POST /api/solicitudes -> registrar solicitud (n8n es el cliente principal)
# =============================================================================
SQL_INSERTAR = """
    INSERT INTO solicitudes
        (nombre, correo, telefono, area, categoria, prioridad, descripcion, id_externo)
    VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id_externo) DO NOTHING
    RETURNING *;
"""


@app.post("/api/solicitudes")
@requiere_api_key
def crear_solicitud():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return _error(
            "El cuerpo de la petición debe ser un objeto JSON válido "
            "(Content-Type: application/json).",
            400,
        )

    limpios, errores = ut.validar_solicitud(datos)
    if errores:
        return _error("La solicitud contiene datos inválidos.", 400, errores)

    fila = db.consultar_uno(
        SQL_INSERTAR,
        (
            limpios["nombre"],
            limpios["correo"],
            limpios["telefono"],
            limpios["area"],
            limpios["categoria"],
            limpios["prioridad"],
            limpios["descripcion"],
            limpios["id_externo"],
        ),
    )

    if fila:
        return (
            jsonify(
                {
                    "ok": True,
                    "mensaje": "Solicitud registrada correctamente.",
                    "data": _serializar_solicitud(fila),
                }
            ),
            201,
        )

    # No se insertó porque el id_externo ya existía (reintento de n8n).
    if limpios["id_externo"]:
        existente = db.consultar_uno(
            "SELECT * FROM solicitudes WHERE id_externo = %s;", (limpios["id_externo"],)
        )
        if existente:
            return (
                jsonify(
                    {
                        "ok": True,
                        "duplicado": True,
                        "mensaje": "La solicitud ya estaba registrada previamente; "
                        "se devuelve el registro existente.",
                        "data": _serializar_solicitud(existente),
                    }
                ),
                200,
            )

    return _error("No fue posible registrar la solicitud.", 500)


# =============================================================================
# GET /api/solicitudes -> listado con filtros y paginación
# =============================================================================
FILTROS = (
    ("categoria", ut.normalizar_categoria, ut.CATEGORIAS),
    ("prioridad", ut.normalizar_prioridad, ut.PRIORIDADES),
    ("estado", ut.normalizar_estado, ut.ESTADOS),
)


@app.get("/api/solicitudes")
def listar_solicitudes():
    condiciones: list[str] = []
    parametros: list = []

    for campo, normalizador, opciones in FILTROS:
        valor = (request.args.get(campo) or "").strip()
        if not valor:
            continue
        normalizado = normalizador(valor)
        if normalizado is None:
            return _error(
                f"El valor del filtro '{campo}' no es válido.",
                400,
                {campo: "Valores permitidos: " + ", ".join(opciones) + "."},
            )
        condiciones.append(f"{campo} = %s")
        parametros.append(normalizado)

    correo = (request.args.get("correo") or "").strip()
    if correo:
        condiciones.append("correo ILIKE %s")
        parametros.append(correo)

    busqueda = (request.args.get("q") or "").strip()
    if busqueda:
        patron = f"%{busqueda}%"
        condiciones.append(
            "(folio ILIKE %s OR nombre ILIKE %s OR descripcion ILIKE %s "
            "OR correo ILIKE %s OR area ILIKE %s)"
        )
        parametros.extend([patron] * 5)

    try:
        limite = int(request.args.get("limit", 50))
        desplazamiento = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        return _error("Los parámetros 'limit' y 'offset' deben ser números enteros.", 400)

    if not 1 <= limite <= 200:
        return _error("El parámetro 'limit' debe estar entre 1 y 200.", 400)
    if desplazamiento < 0:
        return _error("El parámetro 'offset' debe ser mayor o igual a 0.", 400)

    orden = (request.args.get("orden") or "recientes").strip().lower()
    if orden not in ("recientes", "antiguas"):
        return _error("El parámetro 'orden' debe ser 'recientes' o 'antiguas'.", 400)
    orden_sql = (
        "fecha_registro DESC, id DESC" if orden == "recientes" else "fecha_registro ASC, id ASC"
    )

    clausula = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""

    total_fila = db.consultar_uno(
        f"SELECT COUNT(*)::int AS total FROM solicitudes{clausula};", tuple(parametros)
    )
    filas = db.consultar_varios(
        f"SELECT * FROM solicitudes{clausula} ORDER BY {orden_sql} LIMIT %s OFFSET %s;",
        tuple(parametros) + (limite, desplazamiento),
    )

    return (
        jsonify(
            {
                "ok": True,
                "total": (total_fila or {}).get("total", 0),
                "limit": limite,
                "offset": desplazamiento,
                "cantidad": len(filas),
                "data": [_serializar_solicitud(fila) for fila in filas],
            }
        ),
        200,
    )


# =============================================================================
# GET /api/solicitudes/<folio_o_id> -> consultar una solicitud
# =============================================================================
@app.get("/api/solicitudes/<identificador>")
def obtener_solicitud(identificador: str):
    fila = _buscar_solicitud(identificador)
    if fila is None:
        return _error(
            f"No se encontró ninguna solicitud con el identificador '{identificador}'.", 404
        )
    return jsonify({"ok": True, "data": _serializar_solicitud(fila)}), 200


# =============================================================================
# PATCH /api/solicitudes/<folio>/estado -> cambiar estado de atención
# =============================================================================
@app.patch("/api/solicitudes/<identificador>/estado")
@requiere_api_key
def actualizar_estado(identificador: str):
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return _error("El cuerpo debe ser un objeto JSON con el campo 'estado'.", 400)

    estado = ut.normalizar_estado(datos.get("estado"))
    if estado is None:
        return _error(
            "Estado no válido.",
            400,
            {"estado": "Valores permitidos: " + ", ".join(ut.ESTADOS) + "."},
        )

    notas = ut.limpiar(datos.get("notas"))
    if notas is not None and len(notas) > ut.MAX_NOTAS:
        return _error(
            "Las notas son demasiado largas.", 400, {"notas": f"Máximo {ut.MAX_NOTAS} caracteres."}
        )

    existente = _buscar_solicitud(identificador)
    if existente is None:
        return _error(
            f"No se encontró ninguna solicitud con el identificador '{identificador}'.", 404
        )

    fila = db.consultar_uno(
        """
        UPDATE solicitudes
           SET estado = %s,
               notas  = COALESCE(%s, notas)
         WHERE id = %s
        RETURNING *;
        """,
        (estado, notas, existente["id"]),
    )

    if fila is None:
        return _error("No fue posible actualizar la solicitud.", 500)

    return (
        jsonify(
            {
                "ok": True,
                "mensaje": f"Estado actualizado a '{estado}'.",
                "data": _serializar_solicitud(fila),
            }
        ),
        200,
    )


# =============================================================================
# GET /api/estadisticas -> totales para el dashboard
# =============================================================================
@app.get("/api/estadisticas")
def estadisticas():
    total = db.consultar_uno("SELECT COUNT(*)::int AS total FROM solicitudes;") or {"total": 0}
    por_categoria = db.consultar_varios(
        "SELECT categoria, COUNT(*)::int AS total FROM solicitudes "
        "GROUP BY categoria ORDER BY total DESC, categoria ASC;"
    )
    por_prioridad = db.consultar_varios(
        "SELECT prioridad, COUNT(*)::int AS total FROM solicitudes "
        "GROUP BY prioridad ORDER BY total DESC, prioridad ASC;"
    )
    por_estado = db.consultar_varios(
        "SELECT estado, COUNT(*)::int AS total FROM solicitudes "
        "GROUP BY estado ORDER BY total DESC, estado ASC;"
    )
    ultimas_24h = db.consultar_uno(
        "SELECT COUNT(*)::int AS total FROM solicitudes "
        "WHERE fecha_registro >= NOW() - INTERVAL '24 hours';"
    ) or {"total": 0}

    return (
        jsonify(
            {
                "ok": True,
                "data": {
                    "total": total.get("total", 0),
                    "por_categoria": por_categoria,
                    "por_prioridad": por_prioridad,
                    "por_estado": por_estado,
                    "ultimas_24_horas": ultimas_24h.get("total", 0),
                    "generado_en": _fecha_iso(datetime.now(timezone.utc)),
                },
            }
        ),
        200,
    )


# =============================================================================
# Manejo uniforme de errores
# =============================================================================
@app.errorhandler(db.ErrorBaseDatos)
def manejar_error_bd(excepcion: db.ErrorBaseDatos):
    return _error(
        "Servicio de base de datos no disponible.",
        503,
        extra={
            "mensaje": str(excepcion),
            "sugerencia": "Verifica DATABASE_URL en Render y que el proyecto de Neon esté activo. "
            "También puedes consultar GET /health.",
        },
    )


@app.errorhandler(404)
def ruta_no_encontrada(_excepcion):
    return _error(
        "Recurso no encontrado. Consulta GET / para ver los endpoints disponibles.", 404
    )


@app.errorhandler(405)
def metodo_no_permitido(_excepcion):
    return _error("Método HTTP no permitido para esta ruta.", 405)


@app.errorhandler(500)
def error_interno(_excepcion):
    return _error("Error interno del servidor.", 500)


# =============================================================================
# Punto de entrada para desarrollo local
# =============================================================================
if __name__ == "__main__":
    puerto = int(os.getenv("PORT", 5000))
    depuracion = (os.getenv("FLASK_DEBUG", "false") or "").strip().lower() in ("1", "true", "yes")
    print(f"API de solicitudes escuchando en http://localhost:{puerto}")
    if not os.getenv("DATABASE_URL"):
        print("AVISO: DATABASE_URL no está definida; GET /health mostrará la BD desconectada.")
    app.run(host="0.0.0.0", port=puerto, debug=depuracion)
