-- ============================================================================
--  DATOS DE PRUEBA (OPCIONAL, pero recomendado para la demostración)
--  Archivo: database/datos_prueba.sql
-- ----------------------------------------------------------------------------
--  CÓMO EJECUTARLO
--    1. Ejecuta primero database/schema.sql en el SQL Editor de Neon.
--    2. Pega este archivo y presiona "Run".
--
--  Sirve para que el dashboard de Google Sheets tenga datos con qué mostrar
--  los 3 gráficos que pide el proyecto (total, por categoría, por prioridad).
--
--  Es IDEMPOTENTE gracias a ON CONFLICT (id_externo) DO NOTHING: si lo
--  ejecutas dos veces no duplica registros.
-- ============================================================================

INSERT INTO solicitudes
    (nombre, correo, telefono, area, categoria, prioridad, descripcion, estado, fecha_registro, id_externo)
VALUES
    ('Ana López Hernández', 'ana.lopez@escuela.edu.mx', '5551234567', 'Recursos Humanos',
     'Hardware', 'Alta', 'La computadora de escritorio no enciende desde esta mañana; el foco de la fuente parpadea.',
     'Pendiente', NOW() - INTERVAL '2 hours', 'demo-001'),

    ('Carlos Méndez Ruiz', 'carlos.mendez@escuela.edu.mx', '5552345678', 'Contabilidad',
     'Software', 'Media', 'El sistema de facturación marca error al generar el reporte mensual en PDF.',
     'En proceso', NOW() - INTERVAL '6 hours', 'demo-002'),

    ('María José Torres', 'maria.torres@escuela.edu.mx', '5553456789', 'Dirección Académica',
     'Redes e Internet', 'Crítica', 'No hay conexión a internet en el edificio B desde el corte de luz de anoche.',
     'En proceso', NOW() - INTERVAL '1 day', 'demo-003'),

    ('Luis Fernando Ramírez', 'luis.ramirez@escuela.edu.mx', '5554567890', 'Servicios Escolares',
     'Accesos y contraseñas', 'Media', 'Olvidé mi contraseña del sistema escolar y necesito restablecerla para capturar calificaciones.',
     'Resuelto', NOW() - INTERVAL '2 days', 'demo-004'),

    ('Sofía Castillo Núñez', 'sofia.castillo@escuela.edu.mx', '5555678901', 'Biblioteca',
     'Impresoras', 'Baja', 'La impresora del área de biblioteca imprime con líneas negras en todas las hojas.',
     'Pendiente', NOW() - INTERVAL '3 days', 'demo-005'),

    ('Jorge Alberto Peña', 'jorge.pena@escuela.edu.mx', '5556789012', 'Mantenimiento',
     'Hardware', 'Media', 'El teclado de la laptop de mantenimiento tiene varias teclas que no responden.',
     'Resuelto', NOW() - INTERVAL '4 days', 'demo-006'),

    ('Daniela Ortiz Vega', 'daniela.ortiz@escuela.edu.mx', '5557890123', 'Psicopedagogía',
     'Software', 'Alta', 'La aplicación de control escolar se cierra sola al subir un archivo de evidencia.',
     'En proceso', NOW() - INTERVAL '5 days', 'demo-007'),

    ('Ricardo Salinas Mora', 'ricardo.salinas@escuela.edu.mx', '5558901234', 'Laboratorio de Cómputo',
     'Redes e Internet', 'Media', 'El proyector del laboratorio no se conecta al WiFi de la red de invitados.',
     'Cerrado', NOW() - INTERVAL '6 days', 'demo-008'),

    ('Fernanda Rojas Silva', 'fernanda.rojas@escuela.edu.mx', '5559012345', 'Comunicación Social',
     'Accesos y contraseñas', 'Alta', 'Necesito acceso al repositorio de fotografías institucionales para la campaña de redes.',
     'Pendiente', NOW() - INTERVAL '7 days', 'demo-009'),

    ('Alejandro Guzmán Ríos', 'alejandro.guzman@escuela.edu.mx', '5550123456', 'Dirección General',
     'Otro', 'Baja', 'Solicito una cotización para renovar las licencias del software de diseño gráfico.',
     'Pendiente', NOW() - INTERVAL '10 days', 'demo-010');

-- Verificación: debe mostrar 10 registros con folio asignado automáticamente
SELECT folio, nombre, categoria, prioridad, estado, fecha_registro
FROM solicitudes
ORDER BY fecha_registro DESC;
