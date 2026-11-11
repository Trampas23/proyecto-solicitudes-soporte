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
