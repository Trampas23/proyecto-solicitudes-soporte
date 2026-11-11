"""
Pruebas de humo de la API (no requieren una base de datos real).

Ejecutar:
    python test_smoke.py -v

Verifican:
  * Normalización de categorías/prioridades/estados y validación de datos.
  * Códigos HTTP y formato JSON de cada endpoint.
  * Autenticación con el header X-API-Key.
  * Respuesta 503 y mensajes claros cuando falta DATABASE_URL.
  * Serialización de fechas en formato ISO 8601.

La capa de datos se sustituye con dobles de prueba (unittest.mock), por lo que
las pruebas corren sin conexión a Neon y sin instalar PostgreSQL.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from unittest import mock

DIRECTORIO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIRECTORIO)

os.environ.setdefault("DATABASE_URL", "postgresql://usuario:clave@localhost:5432/pruebas")
os.environ.setdefault("API_KEY", "clave-de-prueba")

import app as app_mod  # noqa: E402
import database as db  # noqa: E402
import utilidades as ut  # noqa: E402

CLAVE = "clave-de-prueba"
CABECERAS_OK = {"X-API-Key": CLAVE}

# Fila simulada tal como la devolvería psycopg2 (RealDictCursor).
FILA = {
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
    "notas": None,
    "id_externo": "form-2",
    "correo_enviado": False,
    "fecha_registro": datetime(2026, 11, 10, 16, 30, tzinfo=timezone.utc),
    "fecha_actualizacion": None,
}

DATOS_VALIDOS = {
    "nombre": "Ana López Hernández",
    "correo": "ana.lopez@escuela.edu.mx",
    "telefono": "555-123-4567",
    "area": "Recursos Humanos",
    "categoria": "Hardware",
    "prioridad": "Alta",
    "descripcion": "La computadora de escritorio no enciende desde esta mañana.",
}


class PruebasUtilidades(unittest.TestCase):
    """Validación y normalización de datos."""

    def test_normaliza_categorias(self):
        self.assertEqual(ut.normalizar_categoria("hardware"), "Hardware")
        self.assertEqual(ut.normalizar_categoria("Redes e Internet"), "Redes e Internet")
        self.assertEqual(ut.normalizar_categoria("redes"), "Redes e Internet")
        self.assertEqual(ut.normalizar_categoria("ACCESOS Y CONTRASEÑAS"), "Accesos y contraseñas")
        self.assertEqual(ut.normalizar_categoria("contrasenas"), "Accesos y contraseñas")

    def test_rechaza_categoria_invalida(self):
        self.assertIsNone(ut.normalizar_categoria("Física cuántica"))
        self.assertIsNone(ut.normalizar_categoria(""))

    def test_normaliza_prioridades(self):
        self.assertEqual(ut.normalizar_prioridad("critica"), "Crítica")
        self.assertEqual(ut.normalizar_prioridad("CRÍTICA"), "Crítica")
        self.assertEqual(ut.normalizar_prioridad("urgente"), "Crítica")
        self.assertIsNone(ut.normalizar_prioridad("Altísima"))

    def test_normaliza_estados(self):
        self.assertEqual(ut.normalizar_estado("pendiente"), "Pendiente")
        self.assertEqual(ut.normalizar_estado("en proceso"), "En proceso")
        self.assertEqual(ut.normalizar_estado("resuelta"), "Resuelto")
        self.assertEqual(ut.normalizar_estado("cerrado"), "Cerrado")
        self.assertIsNone(ut.normalizar_estado("volando"))

    def test_correo_valido(self):
        self.assertTrue(ut.correo_valido("ana@escuela.edu.mx"))
        self.assertTrue(ut.correo_valido("nombre.apellido+etiqueta@dominio.com"))
        self.assertFalse(ut.correo_valido("ana-escuela.edu.mx"))
        self.assertFalse(ut.correo_valido("ana@escuela"))
        self.assertFalse(ut.correo_valido(""))

    def test_limpiar(self):
        self.assertEqual(ut.limpiar("  Ana   López  "), "Ana López")
        self.assertIsNone(ut.limpiar("   "))
        self.assertIsNone(ut.limpiar(None))

    def test_validacion_correcta(self):
        limpios, errores = ut.validar_solicitud(DATOS_VALIDOS)
        self.assertEqual(errores, {})
        self.assertEqual(limpios["nombre"], "Ana López Hernández")
        self.assertEqual(limpios["correo"], "ana.lopez@escuela.edu.mx")
        self.assertEqual(limpios["categoria"], "Hardware")

    def test_validacion_minusculas_y_alias(self):
        datos = dict(DATOS_VALIDOS, categoria="redes", prioridad="urgente")
        limpios, errores = ut.validar_solicitud(datos)
        self.assertEqual(errores, {})
        self.assertEqual(limpios["categoria"], "Redes e Internet")
        self.assertEqual(limpios["prioridad"], "Crítica")

    def test_validacion_detecta_todos_los_errores(self):
        _limpios, errores = ut.validar_solicitud(
            {
                "nombre": "",
                "correo": "no-es-un-correo",
                "categoria": "Física",
                "prioridad": "Altísima",
                "descripcion": "corta",
                "telefono": "abc",
            }
        )
        for campo in ("nombre", "correo", "categoria", "prioridad", "descripcion", "telefono"):
            self.assertIn(campo, errores, f"Falta el error de '{campo}'")

    def test_validacion_rechaza_cuerpo_no_objeto(self):
        _limpios, errores = ut.validar_solicitud(["no", "es", "objeto"])
        self.assertIn("cuerpo", errores)


class PruebasAPI(unittest.TestCase):
    """Endpoints HTTP con la capa de datos simulada."""

    def setUp(self):
        app_mod.app.config.update(TESTING=True)
        self.cliente = app_mod.app.test_client()
        parche = mock.patch.dict(os.environ, {"API_KEY": CLAVE})
        parche.start()
        self.addCleanup(parche.stop)

    # ----------------------------- índice / health -------------------------
    def test_indice(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.get_json()["ok"])
        self.assertIn("categorias", respuesta.get_json()["valores_validos"])

    @mock.patch.object(db, "hay_conexion", return_value=True)
    def test_health_con_base_de_datos(self, _mock):
        respuesta = self.cliente.get("/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["base_datos"], "conectada")

    @mock.patch.object(db, "hay_conexion", return_value=False)
    def test_health_sin_base_de_datos(self, _mock):
        respuesta = self.cliente.get("/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["base_datos"], "desconectada")

    def test_health_sin_database_url_responde_200(self):
        with mock.patch.dict(os.environ, {"DATABASE_URL": ""}):
            respuesta = self.cliente.get("/health")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.get_json()
        self.assertEqual(cuerpo["base_datos"], "desconectada")

    # --------------------------- POST /api/solicitudes ---------------------
    @mock.patch.object(db, "consultar_uno", return_value=FILA)
    def test_crear_solicitud_201(self, _mock):
        respuesta = self.cliente.post("/api/solicitudes", json=DATOS_VALIDOS, headers=CABECERAS_OK)
        self.assertEqual(respuesta.status_code, 201)
        cuerpo = respuesta.get_json()
        self.assertTrue(cuerpo["ok"])
        self.assertEqual(cuerpo["data"]["folio"], "SOL-2026-0001")
        self.assertEqual(cuerpo["data"]["estado"], "Pendiente")

    @mock.patch.object(db, "consultar_uno", return_value=FILA)
    def test_crear_solicitud_requiere_api_key(self, _mock):
        respuesta = self.cliente.post("/api/solicitudes", json=DATOS_VALIDOS)
        self.assertEqual(respuesta.status_code, 401)

    @mock.patch.object(db, "consultar_uno", return_value=FILA)
    def test_crear_solicitud_api_key_incorrecta(self, _mock):
        respuesta = self.cliente.post(
            "/api/solicitudes", json=DATOS_VALIDOS, headers={"X-API-Key": "otra-clave"}
        )
        self.assertEqual(respuesta.status_code, 401)

    def test_crear_solicitud_datos_invalidos(self):
        respuesta = self.cliente.post(
            "/api/solicitudes",
            json={"nombre": "A", "correo": "malo", "categoria": "X", "prioridad": "Y"},
            headers=CABECERAS_OK,
        )
        self.assertEqual(respuesta.status_code, 400)
        cuerpo = respuesta.get_json()
        self.assertFalse(cuerpo["ok"])
        self.assertIn("nombre", cuerpo["errores"])
        self.assertIn("correo", cuerpo["errores"])

    def test_crear_solicitud_cuerpo_no_json(self):
        respuesta = self.cliente.post(
            "/api/solicitudes", data="texto plano", headers=CABECERAS_OK
        )
        self.assertEqual(respuesta.status_code, 400)

    @mock.patch.object(db, "consultar_uno")
    def test_crear_solicitud_duplicada_devuelve_200(self, mock_consultar):
        mock_consultar.side_effect = [None, FILA]
        respuesta = self.cliente.post(
            "/api/solicitudes",
            json=dict(DATOS_VALIDOS, id_externo="form-2"),
            headers=CABECERAS_OK,
        )
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.get_json()
        self.assertTrue(cuerpo["duplicado"])
        self.assertEqual(cuerpo["data"]["folio"], "SOL-2026-0001")

    @mock.patch.object(
        db, "consultar_uno", side_effect=db.ErrorBaseDatos("Sin conexión con Neon.")
    )
    def test_crear_solicitud_sin_bd_devuelve_503(self, _mock):
        respuesta = self.cliente.post("/api/solicitudes", json=DATOS_VALIDOS, headers=CABECERAS_OK)
        self.assertEqual(respuesta.status_code, 503)
        self.assertFalse(respuesta.get_json()["ok"])

    # ---------------------------- GET /api/solicitudes ---------------------
    @mock.patch.object(db, "consultar_varios", return_value=[FILA])
    @mock.patch.object(db, "consultar_uno", return_value={"total": 1})
    def test_listar_solicitudes(self, _mock_uno, _mock_varios):
        respuesta = self.cliente.get("/api/solicitudes?limit=10")
        self.assertEqual(respuesta.status_code, 200)
        cuerpo = respuesta.get_json()
        self.assertEqual(cuerpo["total"], 1)
        self.assertEqual(cuerpo["cantidad"], 1)
        self.assertEqual(cuerpo["data"][0]["folio"], "SOL-2026-0001")

    @mock.patch.object(db, "consultar_varios", return_value=[])
    @mock.patch.object(db, "consultar_uno", return_value={"total": 0})
    def test_listar_solicitudes_filtradas(self, _mock_uno, _mock_varios):
        respuesta = self.cliente.get(
            "/api/solicitudes?categoria=hardware&prioridad=alta&estado=pendiente&q=compu"
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_listar_solicitudes_filtro_invalido(self):
        respuesta = self.cliente.get("/api/solicitudes?categoria=F%C3%ADsica")
        self.assertEqual(respuesta.status_code, 400)

    def test_listar_solicitudes_limit_invalido(self):
        respuesta = self.cliente.get("/api/solicitudes?limit=abc")
        self.assertEqual(respuesta.status_code, 400)

    def test_listar_solicitudes_orden_invalido(self):
        respuesta = self.cliente.get("/api/solicitudes?orden=aleatorio")
        self.assertEqual(respuesta.status_code, 400)

    # ------------------------ GET /api/solicitudes/<id> --------------------
    @mock.patch.object(db, "consultar_uno", return_value=FILA)
    def test_obtener_solicitud_por_folio(self, _mock):
        respuesta = self.cliente.get("/api/solicitudes/SOL-2026-0001")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["data"]["id"], 1)

    @mock.patch.object(db, "consultar_uno", return_value=None)
    def test_obtener_solicitud_inexistente(self, _mock):
        respuesta = self.cliente.get("/api/solicitudes/SOL-2099-9999")
        self.assertEqual(respuesta.status_code, 404)

    # ---------------------- PATCH /api/solicitudes/<folio>/estado ----------
    @mock.patch.object(db, "consultar_uno")
    def test_actualizar_estado(self, mock_consultar):
        mock_consultar.side_effect = [FILA, dict(FILA, estado="En proceso")]
        respuesta = self.cliente.patch(
            "/api/solicitudes/SOL-2026-0001/estado",
            json={"estado": "en proceso"},
            headers=CABECERAS_OK,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["data"]["estado"], "En proceso")

    @mock.patch.object(db, "consultar_uno", return_value=FILA)
    def test_actualizar_estado_invalido(self, _mock):
        respuesta = self.cliente.patch(
            "/api/solicitudes/SOL-2026-0001/estado",
            json={"estado": "volando"},
            headers=CABECERAS_OK,
        )
        self.assertEqual(respuesta.status_code, 400)

    @mock.patch.object(db, "consultar_uno", return_value=None)
    def test_actualizar_estado_inexistente(self, _mock):
        respuesta = self.cliente.patch(
            "/api/solicitudes/SOL-2099-9999/estado",
            json={"estado": "Cerrado"},
            headers=CABECERAS_OK,
        )
        self.assertEqual(respuesta.status_code, 404)

    # ---------------------------- GET /api/estadisticas --------------------
    @mock.patch.object(db, "consultar_varios")
    @mock.patch.object(db, "consultar_uno")
    def test_estadisticas(self, mock_uno, mock_varios):
        mock_uno.side_effect = [{"total": 5}, {"total": 2}]
        mock_varios.side_effect = [
            [{"categoria": "Hardware", "total": 3}],
            [{"prioridad": "Alta", "total": 2}],
            [{"estado": "Pendiente", "total": 5}],
        ]
        respuesta = self.cliente.get("/api/estadisticas")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()["data"]
        self.assertEqual(datos["total"], 5)
        self.assertEqual(datos["por_categoria"][0]["categoria"], "Hardware")
        self.assertEqual(datos["por_prioridad"][0]["total"], 2)
        self.assertEqual(datos["por_estado"][0]["estado"], "Pendiente")
        self.assertEqual(datos["ultimas_24_horas"], 2)

    # ------------------------------ serialización -------------------------
    def test_fecha_iso_conserva_el_instante(self):
        momento = datetime(2026, 11, 10, 16, 30, tzinfo=timezone.utc)
        texto = app_mod._fecha_iso(momento)
        self.assertIsInstance(texto, str)
        recuperado = datetime.fromisoformat(texto)
        self.assertEqual(recuperado.timestamp(), momento.timestamp())

    def test_serializar_solicitud_devuelve_json_valido(self):
        datos = app_mod._serializar_solicitud(FILA)
        self.assertEqual(datos["folio"], "SOL-2026-0001")
        self.assertIsInstance(datos["fecha_registro"], str)
        self.assertIsNone(datos["fecha_actualizacion"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
