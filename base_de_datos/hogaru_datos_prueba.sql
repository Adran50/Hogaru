-- =====================================================
-- Hogaru - Datos de prueba (Seed para desarrollo y testing)
-- =====================================================
SET NAMES utf8mb4;
USE hogaru;

-- Hash PBKDF2 para la contraseña 'hogaru123'
-- Permite iniciar sesión de inmediato con cualquier cuenta de prueba
SET @PASSWORD_HASH = 'pbkdf2_sha256$200000$00000000000000000000000000000000$ec85746e3306c8591946fe3bb70539a1cdf5305534e154b19a61d83bb4233e20';

-- -----------------------------------------------------
-- 1. USUARIOS (1 admin, 3 clientes, 4 prestadores)
-- -----------------------------------------------------
INSERT INTO usuario (id_usuario, nombre, apellido, email, contrasena, telefono, tipo_cuenta, estado) VALUES
    -- 1 Administrador
    (1, 'Admin',   'Hogaru',  'admin@hogaru.test',   @PASSWORD_HASH, '1100000001', 'administrador', 'activo'),
    -- 4 Prestadores
    (2, 'Marisa',  'Gómez',   'marisa@hogaru.test',  @PASSWORD_HASH, '1100000002', 'prestador',     'activo'),
    (3, 'Roberto', 'Tello',   'roberto@hogaru.test', @PASSWORD_HASH, '1100000003', 'prestador',     'activo'),
    (4, 'Lucía',   'Paz',     'lucia@hogaru.test',   @PASSWORD_HASH, '1100000004', 'prestador',     'activo'),
    (8, 'Esteban', 'Morales', 'esteban@hogaru.test', @PASSWORD_HASH, '1100000008', 'prestador',     'activo'),
    -- 3 Clientes
    (5, 'Carla',   'Méndez',  'carla@hogaru.test',   @PASSWORD_HASH, '1100000005', 'cliente',       'activo'),
    (6, 'Julián',  'Ríos',    'julian@hogaru.test',  @PASSWORD_HASH, '1100000006', 'cliente',       'activo'),
    (7, 'Lucas',   'Benítez', 'lucas@hogaru.test',   @PASSWORD_HASH, '1100000007', 'cliente',       'activo');

-- Administrador
INSERT INTO administrador (id_admin, nivel_permiso) VALUES
    (1, 'superadmin');

-- 3 Clientes con ubicación
INSERT INTO cliente (id_cliente, direccion, latitud, longitud) VALUES
    (5, 'Av. Rivadavia 17000, Morón',     -34.651000, -58.619000),
    (6, 'Belgrano 250, Haedo',            -34.642000, -58.592000),
    (7, 'Leandro N. Alem 800, Castelar',  -34.658000, -58.635000);

-- 4 Prestadores con mezcla de estados de verificación y coordenadas
-- 2 aprobados (Marisa, Roberto), 1 pendiente (Lucía), 1 rechazado (Esteban)
INSERT INTO prestador (id_prestador, descripcion, estado_verificacion, puntuacion_promedio, latitud, longitud) VALUES
    (2, 'Más de 8 años de experiencia en limpieza doméstica profunda y planchado.', 'aprobado',   5.00, -34.653000, -58.621000),
    (3, 'Especialista en limpieza integral, fin de obra y áreas exteriores.',      'aprobado',   4.50, -34.640000, -58.588000),
    (4, 'Limpieza de oficinas comerciales y consultorios. Turnos mañana/tarde.',   'pendiente',  0.00, -34.660000, -58.640000),
    (8, 'Mantenimiento de jardines, parquización y desmalezado de terrenos.',      'rechazado',  0.00, -34.635000, -58.560000);

-- -----------------------------------------------------
-- 2. DOCUMENTACION DE VERIFICACION
-- -----------------------------------------------------
INSERT INTO documentacion_verificacion (id_prestador, id_admin, tipo_documento, archivo_url, estado, fecha_revision) VALUES
    -- Marisa: aprobada
    (2, 1, 'dni',                  '/docs/marisa_dni.pdf',          'aprobado',  NOW()),
    (2, 1, 'antecedentes_penales', '/docs/marisa_antecedentes.pdf', 'aprobado',  NOW()),
    -- Roberto: aprobado
    (3, 1, 'dni',                  '/docs/roberto_dni.pdf',         'aprobado',  NOW()),
    (3, 1, 'antecedentes_penales', '/docs/roberto_antecedentes.pdf','aprobado',  NOW()),
    -- Lucía: pendiente de antecedentes
    (4, 1, 'dni',                  '/docs/lucia_dni.pdf',           'aprobado',  NOW()),
    (4, NULL, 'antecedentes_penales','/docs/lucia_antecedentes.pdf','pendiente', NULL),
    -- Esteban: antecedentes rechazados
    (8, 1, 'dni',                  '/docs/esteban_dni.pdf',         'aprobado',  NOW()),
    (8, 1, 'antecedentes_penales', '/docs/esteban_antecedentes.pdf','rechazado', NOW());

-- -----------------------------------------------------
-- 3. SERVICIOS OFRECIDOS (8 servicios en total)
-- -----------------------------------------------------
INSERT INTO servicio_ofrecido (id_servicio, id_prestador, id_categoria, descripcion, tarifa, activo) VALUES
    (1, 2, 1, 'Limpieza doméstica general por hora (habitaciones, living y cocina)', 4500.00, TRUE),
    (2, 2, 4, 'Limpieza profunda de cocinas, baños y sanitarios a fondo',             5500.00, TRUE),
    (3, 3, 4, 'Limpieza de fin de obra, mudanzas y retiro de polvo fino',             5200.00, TRUE),
    (4, 3, 1, 'Mantenimiento del hogar y limpieza periódica programada',             4800.00, TRUE),
    (5, 3, 3, 'Cuidado, corte de pasto y mantenimiento de jardines',                  4200.00, TRUE),
    (6, 2, 2, 'Limpieza de consultorios médicos y oficinas pequeñas',                5000.00, TRUE),
    (7, 4, 2, 'Limpieza corporativa de oficinas y plantas abiertas',                 4900.00, TRUE),
    (8, 8, 3, 'Parquización integral, poda en altura y desmalezado',                 4600.00, TRUE);

-- Disponibilidad para los 8 servicios
INSERT INTO disponibilidad (id_servicio, dia_semana, hora_inicio, hora_fin) VALUES
    -- Servicio 1: Lunes y Miércoles 08:00 a 16:00
    (1, 1, '08:00', '16:00'),
    (1, 3, '08:00', '16:00'),
    -- Servicio 2: Martes y Jueves 09:00 a 17:00
    (2, 2, '09:00', '17:00'),
    (2, 4, '09:00', '17:00'),
    -- Servicio 3: Martes y Viernes 08:00 a 18:00
    (3, 2, '08:00', '18:00'),
    (3, 5, '08:00', '18:00'),
    -- Servicio 4: Miércoles y Sábado 09:00 a 15:00
    (4, 3, '09:00', '15:00'),
    (4, 6, '09:00', '15:00'),
    -- Servicio 5: Lunes y Jueves 10:00 a 17:00
    (5, 1, '10:00', '17:00'),
    (5, 4, '10:00', '17:00'),
    -- Servicio 6: Viernes 08:00 a 14:00
    (6, 5, '08:00', '14:00'),
    -- Servicio 7: Lunes a Viernes 17:00 a 21:00
    (7, 1, '17:00', '21:00'),
    (7, 3, '17:00', '21:00'),
    -- Servicio 8: Sábados 08:00 a 16:00
    (8, 6, '08:00', '16:00');

-- -----------------------------------------------------
-- 4. SOLICITUDES DE CONTRATACION (una en cada estado)
-- Estados: pendiente, aceptada, en_curso, finalizada, cancelada
-- -----------------------------------------------------
INSERT INTO solicitud_contratacion
    (id_solicitud, id_cliente, id_servicio, fecha_hora_programada, duracion_horas, direccion_trabajo, estado) VALUES
    -- 1. Pendiente: cliente 5 solicita servicio 1
    (1, 5, 1, DATE_ADD(NOW(), INTERVAL 3 DAY), 2.0, 'Av. Rivadavia 17000, Morón', 'pendiente'),
    -- 2. Aceptada: cliente 7 contrata servicio 4
    (2, 7, 4, DATE_ADD(NOW(), INTERVAL 2 DAY), 3.0, 'Leandro N. Alem 800, Castelar', 'aceptada'),
    -- 3. En curso: cliente 6 con servicio 3
    (3, 6, 3, NOW(), 4.0, 'Belgrano 250, Haedo', 'en_curso'),
    -- 4. Finalizada: cliente 5 contrató servicio 1
    (4, 5, 1, DATE_SUB(NOW(), INTERVAL 7 DAY), 1.0, 'Av. Rivadavia 17000, Morón', 'finalizada'),
    -- 5. Finalizada: cliente 6 contrató servicio 2
    (5, 6, 2, DATE_SUB(NOW(), INTERVAL 4 DAY), 2.0, 'Belgrano 250, Haedo', 'finalizada'),
    -- 6. Cancelada: cliente 7 canceló servicio 5
    (6, 7, 5, DATE_SUB(NOW(), INTERVAL 2 DAY), 2.0, 'Leandro N. Alem 800, Castelar', 'cancelada');

-- -----------------------------------------------------
-- 5. PAGOS (completado, reembolsado, pendiente)
-- -----------------------------------------------------
INSERT INTO pago (id_pago, id_solicitud, monto, comision_plataforma, metodo_pago, estado) VALUES
    -- Solicitud 4 (finalizada): $4500 (comisión 10% = $450)
    (1, 4, 4500.00,  450.00, 'mercado_pago', 'completado'),
    -- Solicitud 5 (finalizada): 2 hs x $5500 = $11000 (comisión $1100)
    (2, 5, 11000.00, 1100.00, 'tarjeta',     'completado'),
    -- Solicitud 6 (cancelada con reembolso): 2 hs x $4200 = $8400
    (3, 6, 8400.00,  840.00, 'transferencia', 'reembolsado');

-- -----------------------------------------------------
-- 6. CALIFICACIONES (solicitudes finalizadas)
-- -----------------------------------------------------
INSERT INTO calificacion (id_calificacion, id_solicitud, puntuacion_puntualidad, puntuacion_prolijidad, puntuacion_trato, comentario) VALUES
    (1, 4, 5, 5, 5, 'Excelente trabajo de Marisa, puntual y muy detallista con la limpieza.'),
    (2, 5, 4, 5, 4, 'Muy buen trabajo en baños y cocina, muy recomendada.');

-- -----------------------------------------------------
-- 7. DISPUTAS (abierta, en_revision, resuelta)
-- -----------------------------------------------------
INSERT INTO disputa (id_disputa, id_solicitud, id_admin, motivo, estado, resolucion, fecha_cierre) VALUES
    -- Disputa 1: en revisión (sobre solicitud 5)
    (1, 5, 1, 'Hubo una demora de 40 minutos en el inicio del servicio programado.', 'en_revision', NULL, NULL),
    -- Disputa 2: resuelta con reembolso (sobre solicitud 6 cancelada)
    (2, 6, 1, 'Cancelación por rotura de cañería en el domicilio del cliente.', 'resuelta', 'Se procedió al reembolso total de lo abonado.', NOW()),
    -- Disputa 3: abierta (sobre solicitud 3 en curso)
    (3, 3, NULL, 'Consulta sobre los productos provistos para el retiro de polvo fino.', 'abierta', NULL, NULL);

-- -----------------------------------------------------
-- 8. MENSAJES DE PRUEBA
-- -----------------------------------------------------
INSERT INTO mensaje (id_solicitud, id_emisor, contenido) VALUES
    (1, 5, 'Hola Marisa, ¿incluye aspirado completo de alfombras?'),
    (1, 2, 'Hola Carla, sí, aspiramos todas las alfombras y tapizados.');

-- -----------------------------------------------------
-- 9. NOTIFICACIONES
-- -----------------------------------------------------
INSERT INTO notificacion (id_usuario, tipo, id_solicitud, texto, leida) VALUES
    (2, 'solicitud', 1, 'Recibiste una nueva solicitud de trabajo', FALSE),
    (5, 'cambio_estado', 4, 'El servicio de Limpieza doméstica general finalizó. ¡Ya podés calificarlo!', TRUE),
    (2, 'pago', 4, 'Recibiste un pago de $4500.00 por Limpieza doméstica general', TRUE),
    (7, 'pago', 6, 'Tu pago fue reembolsado por la cancelación', FALSE);
