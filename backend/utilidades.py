"""
Utilidades de validación y normalización de datos.

Se separan de la aplicación para poder probarlas de forma unitaria y para que
la API acepte variantes escritas por el usuario (mayúsculas, minúsculas o sin
acentos) y las convierta siempre a los valores canónicos que exige la base de
datos:

    Categorías : Hardware | Software | Redes e Internet |
                 Accesos y contraseñas | Impresoras | Otro
    Prioridades: Baja | Media | Alta | Crítica
    Estados    : Pendiente | En proceso | Resuelto | Cerrado
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Valores canónicos (deben coincidir con los CHECK de database/schema.sql)
# ---------------------------------------------------------------------------
CATEGORIAS = (
    "Hardware",
    "Software",
    "Redes e Internet",
    "Accesos y contraseñas",
    "Impresoras",
    "Otro",
)

PRIORIDADES = ("Baja", "Media", "Alta", "Crítica")

ESTADOS = ("Pendiente", "En proceso", "Resuelto", "Cerrado")

# Longitudes máximas (iguales a las columnas de la tabla)
MAX_NOMBRE = 120
MAX_CORREO = 120
MAX_TELEFONO = 20
MAX_AREA = 100
MAX_DESCRIPCION = 2000
MAX_NOTAS = 1000
MAX_ID_EXTERNO = 120
MIN_NOMBRE = 3
MIN_DESCRIPCION = 10

PATRON_CORREO = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
PATRON_TELEFONO = re.compile(r"^[0-9+\-() .]{7,20}$")
PATRON_ID_EXTERNO = re.compile(r"^[A-Za-z0-9._:\-]{1,120}$")

# Sinónimos frecuentes -> valor canónico (las claves van sin acentos y en
# minúsculas; se comparan con la función _comparables()).
ALIAS_CATEGORIA = {
    "redes": "Redes e Internet",
    "red": "Redes e Internet",
    "internet": "Redes e Internet",
    "wifi": "Redes e Internet",
    "redes e internet": "Redes e Internet",
    "accesos": "Accesos y contraseñas",
    "acceso": "Accesos y contraseñas",
    "contrasenas": "Accesos y contraseñas",
    "contrasena": "Accesos y contraseñas",
    "accesos y contrasenas": "Accesos y contraseñas",
    "impresora": "Impresoras",
    "impresion": "Impresoras",
    "equipo": "Hardware",
    "equipos": "Hardware",
    "pc": "Hardware",
    "programa": "Software",
    "programas": "Software",
    "sistema": "Software",
    "otro": "Otro",
    "otros": "Otro",
}

ALIAS_PRIORIDAD = {
    "baja": "Baja",
    "bajo": "Baja",
    "media": "Media",
    "medio": "Media",
    "normal": "Media",
    "alta": "Alta",
    "alto": "Alta",
    "critica": "Crítica",
    "critico": "Crítica",
    "urgente": "Crítica",
    "inmediata": "Crítica",
}

ALIAS_ESTADO = {
    "pendiente": "Pendiente",
    "abierto": "Pendiente",
    "nuevo": "Pendiente",
    "en proceso": "En proceso",
    "proceso": "En proceso",
    "en atencion": "En proceso",
    "atendiendo": "En proceso",
    "resuelto": "Resuelto",
    "resuelta": "Resuelto",
    "cerrado": "Cerrado",
    "cerrada": "Cerrado",
    "finalizado": "Cerrado",
}


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------
def sin_acentos(texto: str) -> str:
    """Devuelve el texto sin acentos (Á -> A, ñ -> n) para comparar."""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _comparables(valor: str) -> str:
    """Texto listo para comparar: sin acentos, minúsculas y espacios simples."""
    return " ".join(sin_acentos(valor).lower().split())


def limpiar(valor) -> str | None:
    """
    Normaliza un texto recibido por la API:
      * convierte a texto,
      * elimina espacios al inicio/final y espacios repetidos,
      * regresa None cuando el valor está vacío o no es un tipo permitido.
    """
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if not isinstance(valor, (str, int, float)):
        return None
    texto = " ".join(str(valor).strip().split())
    return texto or None


def _coincidir(valor, opciones: tuple[str, ...], alias: dict[str, str]) -> str | None:
    """Busca el valor canónico de una opción aceptando alias y variantes."""
    limpio = limpiar(valor)
    if limpio is None:
        return None
    comparable = _comparables(limpio)
    for opcion in opciones:
        if _comparables(opcion) == comparable:
            return opcion
    return alias.get(comparable)


def normalizar_categoria(valor) -> str | None:
    """Regresa la categoría canónica o None si no es válida."""
    return _coincidir(valor, CATEGORIAS, ALIAS_CATEGORIA)


def normalizar_prioridad(valor) -> str | None:
    """Regresa la prioridad canónica o None si no es válida."""
    return _coincidir(valor, PRIORIDADES, ALIAS_PRIORIDAD)


def normalizar_estado(valor) -> str | None:
    """Regresa el estado canónico o None si no es válido."""
    return _coincidir(valor, ESTADOS, ALIAS_ESTADO)


def correo_valido(correo: str) -> bool:
    """Valida el formato del correo electrónico."""
    return bool(correo and PATRON_CORREO.match(correo.strip()))


def _texto(valor) -> str | None:
    return limpiar(valor)


# ---------------------------------------------------------------------------
# Validación principal del cuerpo de POST /api/solicitudes
# ---------------------------------------------------------------------------
def validar_solicitud(datos: dict) -> tuple[dict, dict]:
    """
    Valida y normaliza los datos de una nueva solicitud.

    Parámetros
    ----------
    datos : dict
        Cuerpo JSON recibido por la API.

    Regresa
    -------
    (limpios, errores)
        limpios : dict con los valores listos para insertarse en PostgreSQL.
        errores : dict {campo: mensaje}. Vacío cuando todo es válido.
    """
    if not isinstance(datos, dict):
        return {}, {"cuerpo": "Se esperaba un objeto JSON con los datos de la solicitud."}

    errores: dict[str, str] = {}

    # --- nombre -----------------------------------------------------------
    nombre = _texto(datos.get("nombre"))
    if nombre is None:
        errores["nombre"] = "El nombre del solicitante es obligatorio."
    elif len(nombre) < MIN_NOMBRE:
        errores["nombre"] = f"El nombre debe tener al menos {MIN_NOMBRE} caracteres."
    elif len(nombre) > MAX_NOMBRE:
        errores["nombre"] = f"El nombre no debe exceder {MAX_NOMBRE} caracteres."

    # --- correo -----------------------------------------------------------
    correo = _texto(datos.get("correo"))
    if correo is None:
        errores["correo"] = "El correo electrónico es obligatorio."
    elif not correo_valido(correo):
        errores["correo"] = "El correo no tiene un formato válido (ejemplo: usuario@dominio.com)."
    elif len(correo) > MAX_CORREO:
        errores["correo"] = f"El correo no debe exceder {MAX_CORREO} caracteres."
    else:
        correo = correo.lower()

    # --- teléfono (opcional) ---------------------------------------------
    telefono = _texto(datos.get("telefono"))
    if telefono is not None:
        if not PATRON_TELEFONO.match(telefono):
            errores["telefono"] = (
                "El teléfono solo debe contener números, espacios, +, -, puntos y "
                "paréntesis (entre 7 y 20 caracteres)."
            )
        elif len(telefono) > MAX_TELEFONO:
            errores["telefono"] = f"El teléfono no debe exceder {MAX_TELEFONO} caracteres."

    # --- área (opcional) --------------------------------------------------
    area = _texto(datos.get("area"))
    if area is not None and len(area) > MAX_AREA:
        errores["area"] = f"El área no debe exceder {MAX_AREA} caracteres."

    # --- categoría --------------------------------------------------------
    categoria = normalizar_categoria(datos.get("categoria"))
    if categoria is None:
        errores["categoria"] = (
            "Categoría no válida. Valores permitidos: " + ", ".join(CATEGORIAS) + "."
        )

    # --- prioridad --------------------------------------------------------
    prioridad = normalizar_prioridad(datos.get("prioridad"))
    if prioridad is None:
        errores["prioridad"] = (
            "Prioridad no válida. Valores permitidos: " + ", ".join(PRIORIDADES) + "."
        )

    # --- descripción ------------------------------------------------------
    descripcion = _texto(datos.get("descripcion"))
    if descripcion is None:
        errores["descripcion"] = "La descripción de la solicitud es obligatoria."
    elif len(descripcion) < MIN_DESCRIPCION:
        errores["descripcion"] = (
            f"La descripción debe tener al menos {MIN_DESCRIPCION} caracteres."
        )
    elif len(descripcion) > MAX_DESCRIPCION:
        errores["descripcion"] = (
            f"La descripción no debe exceder {MAX_DESCRIPCION} caracteres."
        )

    # --- id_externo (opcional, idempotencia desde n8n) --------------------
    id_externo = _texto(datos.get("id_externo"))
    if id_externo is not None:
        if not PATRON_ID_EXTERNO.match(id_externo):
            errores["id_externo"] = (
                "El identificador externo solo admite letras, números y los "
                "caracteres . _ : - (máximo 120)."
            )
        elif len(id_externo) > MAX_ID_EXTERNO:
            errores["id_externo"] = f"El identificador externo no debe exceder {MAX_ID_EXTERNO} caracteres."

    limpios = {
        "nombre": nombre,
        "correo": correo,
        "telefono": telefono,
        "area": area,
        "categoria": categoria,
        "prioridad": prioridad,
        "descripcion": descripcion,
        "id_externo": id_externo,
    }
    return limpios, errores


def valores_permitidos() -> dict:
    """Valores válidos para publicarlos en GET / y en la documentación."""
    return {
        "categorias": list(CATEGORIAS),
        "prioridades": list(PRIORIDADES),
        "estados": list(ESTADOS),
    }
