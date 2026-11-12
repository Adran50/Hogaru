-- =====================================================
-- Hogaru - Esquema de base de datos (MySQL 8 / InnoDB)
-- Versión consolidada: Esquema base + Coordenadas + Índices
-- =====================================================

SET NAMES utf8mb4;

DROP DATABASE IF EXISTS hogaru;
CREATE DATABASE hogaru CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE hogaru;

-- -----------------------------------------------------
-- TABLA DE CONTROL DE MIGRACIONES
-- -----------------------------------------------------
CREATE TABLE _migraciones (
    id_migracion INT AUTO_INCREMENT PRIMARY KEY,
    version      VARCHAR(50) NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    aplicada_en  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- USUARIOS (entidad base + especializaciones)
-- -----------------------------------------------------
CREATE TABLE usuario (
    id_usuario     INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(60)  NOT NULL,
    apellido       VARCHAR(60)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    contrasena     VARCHAR(255) NOT NULL,              -- hash, nunca texto plano
    telefono       VARCHAR(30),
    tipo_cuenta    ENUM('cliente','prestador','administrador') NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado         ENUM('activo','suspendido') NOT NULL DEFAULT 'activo'
) ENGINE=InnoDB;

CREATE TABLE cliente (
    id_cliente INT PRIMARY KEY,
    direccion  VARCHAR(200),
    latitud    DECIMAL(9,6),
    longitud   DECIMAL(9,6),
    CONSTRAINT fk_cliente_usuario FOREIGN KEY (id_cliente)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE prestador (
    id_prestador         INT PRIMARY KEY,
    descripcion          TEXT,
    estado_verificacion  ENUM('pendiente','aprobado','rechazado') NOT NULL DEFAULT 'pendiente',
    puntuacion_promedio  DECIMAL(3,2) NOT NULL DEFAULT 0.00,   -- se actualiza por trigger y servicio
    latitud              DECIMAL(9,6) NULL,                    -- coordenadas para cálculo Haversine
    longitud             DECIMAL(9,6) NULL,
    CONSTRAINT fk_prestador_usuario FOREIGN KEY (id_prestador)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE administrador (
    id_admin      INT PRIMARY KEY,
    nivel_permiso ENUM('moderador','superadmin') NOT NULL DEFAULT 'moderador',
    CONSTRAINT fk_admin_usuario FOREIGN KEY (id_admin)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- VERIFICACION DE PRESTADORES
-- -----------------------------------------------------
CREATE TABLE documentacion_verificacion (
    id_documento   INT AUTO_INCREMENT PRIMARY KEY,
    id_prestador   INT NOT NULL,
    id_admin       INT NULL,                           -- moderador que revisó
    tipo_documento ENUM('dni','antecedentes_penales','otro') NOT NULL,
    archivo_url    VARCHAR(255) NOT NULL,
    estado         ENUM('pendiente','aprobado','rechazado') NOT NULL DEFAULT 'pendiente',
    fecha_carga    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_revision DATETIME NULL,
    CONSTRAINT fk_doc_prestador FOREIGN KEY (id_prestador)
        REFERENCES prestador(id_prestador) ON DELETE CASCADE,
    CONSTRAINT fk_doc_admin FOREIGN KEY (id_admin)
        REFERENCES administrador(id_admin) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- SERVICIOS
-- -----------------------------------------------------
CREATE TABLE categoria_servicio (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(80) NOT NULL UNIQUE,
    descripcion  VARCHAR(200)
) ENGINE=InnoDB;

CREATE TABLE servicio_ofrecido (
    id_servicio  INT AUTO_INCREMENT PRIMARY KEY,
    id_prestador INT NOT NULL,
    id_categoria INT NOT NULL,
    descripcion  TEXT,
    tarifa       DECIMAL(10,2) NOT NULL CHECK (tarifa >= 0),   -- tarifa por hora
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_serv_prestador FOREIGN KEY (id_prestador)
        REFERENCES prestador(id_prestador) ON DELETE CASCADE,
    CONSTRAINT fk_serv_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria_servicio(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE disponibilidad (
    id_disponibilidad INT AUTO_INCREMENT PRIMARY KEY,
    id_servicio       INT NOT NULL,
    dia_semana        TINYINT NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),  -- 1=lunes ... 7=domingo
    hora_inicio       TIME NOT NULL,
    hora_fin          TIME NOT NULL,
    CHECK (hora_fin > hora_inicio),
    CONSTRAINT fk_disp_servicio FOREIGN KEY (id_servicio)
        REFERENCES servicio_ofrecido(id_servicio) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- CONTRATACION
-- -----------------------------------------------------
CREATE TABLE solicitud_contratacion (
    id_solicitud          INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente            INT NOT NULL,
    id_servicio           INT NOT NULL,
    fecha_hora_programada DATETIME NOT NULL,
    duracion_horas        DECIMAL(4,2) NOT NULL DEFAULT 1 CHECK (duracion_horas > 0),
    direccion_trabajo     VARCHAR(200) NOT NULL,
    estado                ENUM('pendiente','aceptada','en_curso','finalizada','cancelada')
                          NOT NULL DEFAULT 'pendiente',
    fecha_creacion        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sol_cliente FOREIGN KEY (id_cliente)
        REFERENCES cliente(id_cliente),
    CONSTRAINT fk_sol_servicio FOREIGN KEY (id_servicio)
        REFERENCES servicio_ofrecido(id_servicio)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- PAGOS (1 a 1 con la solicitud)
-- -----------------------------------------------------
CREATE TABLE pago (
    id_pago             INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud        INT NOT NULL UNIQUE,
    monto               DECIMAL(10,2) NOT NULL CHECK (monto >= 0),
    comision_plataforma DECIMAL(10,2) NOT NULL CHECK (comision_plataforma >= 0),
    metodo_pago         ENUM('tarjeta','transferencia','mercado_pago','efectivo') NOT NULL,
    estado              ENUM('pendiente','completado','reembolsado') NOT NULL DEFAULT 'pendiente',
    fecha               DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pago_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- CALIFICACIONES (1 a 1 con la solicitud)
-- -----------------------------------------------------
CREATE TABLE calificacion (
    id_calificacion        INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud           INT NOT NULL UNIQUE,
    puntuacion_puntualidad TINYINT NOT NULL CHECK (puntuacion_puntualidad BETWEEN 1 AND 5),
    puntuacion_prolijidad  TINYINT NOT NULL CHECK (puntuacion_prolijidad  BETWEEN 1 AND 5),
    puntuacion_trato       TINYINT NOT NULL CHECK (puntuacion_trato       BETWEEN 1 AND 5),
    comentario             TEXT,
    fecha                  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cal_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- DISPUTAS
-- -----------------------------------------------------
CREATE TABLE disputa (
    id_disputa     INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud   INT NOT NULL,
    id_admin       INT NULL,                           -- moderador asignado
    motivo         TEXT NOT NULL,
    estado         ENUM('abierta','en_revision','resuelta') NOT NULL DEFAULT 'abierta',
    resolucion     TEXT,
    fecha_apertura DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre   DATETIME NULL,
    CONSTRAINT fk_disp_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud),
    CONSTRAINT fk_disputa_admin FOREIGN KEY (id_admin)
        REFERENCES administrador(id_admin) ON DELETE SET NULL
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- MENSAJES (chat entre cliente y prestador sobre un trabajo)
-- -----------------------------------------------------
CREATE TABLE mensaje (
    id_mensaje   INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud INT NOT NULL,
    id_emisor    INT NOT NULL,                         -- cliente o prestador de esa solicitud
    contenido    TEXT NOT NULL,
    fecha_envio  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_msj_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud) ON DELETE CASCADE,
    CONSTRAINT fk_msj_emisor FOREIGN KEY (id_emisor)
        REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- NOTIFICACIONES (módulo de notificaciones del backend)
-- -----------------------------------------------------
CREATE TABLE notificacion (
    id_notificacion INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT NOT NULL,                      -- destinatario
    tipo            ENUM('mensaje','solicitud','cambio_estado','pago','disputa') NOT NULL,
    id_solicitud    INT NULL,
    id_mensaje      INT NULL,
    texto           VARCHAR(255) NOT NULL,
    leida           BOOLEAN NOT NULL DEFAULT FALSE,
    fecha           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notif_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE,
    CONSTRAINT fk_notif_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud) ON DELETE CASCADE,
    CONSTRAINT fk_notif_mensaje FOREIGN KEY (id_mensaje)
        REFERENCES mensaje(id_mensaje) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- INDICES de búsqueda y rendimiento
-- -----------------------------------------------------
CREATE INDEX idx_servicio_categoria       ON servicio_ofrecido(id_categoria);
CREATE INDEX idx_servicio_prestador_activo ON servicio_ofrecido(id_prestador, activo);
CREATE INDEX idx_solicitud_cliente        ON solicitud_contratacion(id_cliente);
CREATE INDEX idx_solicitud_servicio       ON solicitud_contratacion(id_servicio);
CREATE INDEX idx_solicitud_estado         ON solicitud_contratacion(estado);
CREATE INDEX idx_solicitud_fecha          ON solicitud_contratacion(fecha_hora_programada);
CREATE INDEX idx_disp_servicio_dia        ON disponibilidad(id_servicio, dia_semana);
CREATE INDEX idx_doc_prestador_estado     ON documentacion_verificacion(id_prestador, estado);
CREATE INDEX idx_disputa_solicitud_estado ON disputa(id_solicitud, estado);
CREATE INDEX idx_mensaje_solicitud        ON mensaje(id_solicitud, fecha_envio);
CREATE INDEX idx_notif_usuario            ON notificacion(id_usuario, leida, fecha);
CREATE INDEX idx_prestador_coords         ON prestador(latitud, longitud);

-- -----------------------------------------------------
-- TRIGGERS
-- -----------------------------------------------------
DELIMITER //
CREATE TRIGGER trg_actualizar_promedio
AFTER INSERT ON calificacion
FOR EACH ROW
BEGIN
    DECLARE v_prestador INT;

    SELECT so.id_prestador INTO v_prestador
    FROM solicitud_contratacion sc
    JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio
    WHERE sc.id_solicitud = NEW.id_solicitud;

    UPDATE prestador
    SET puntuacion_promedio = (
        SELECT ROUND(AVG((c.puntuacion_puntualidad + c.puntuacion_prolijidad + c.puntuacion_trato) / 3), 2)
        FROM calificacion c
        JOIN solicitud_contratacion sc ON sc.id_solicitud = c.id_solicitud
        JOIN servicio_ofrecido so      ON so.id_servicio  = sc.id_servicio
        WHERE so.id_prestador = v_prestador
    )
    WHERE id_prestador = v_prestador;
END//

CREATE TRIGGER trg_notificar_solicitud
AFTER INSERT ON solicitud_contratacion
FOR EACH ROW
BEGIN
    INSERT INTO notificacion (id_usuario, tipo, id_solicitud, texto)
    SELECT so.id_prestador, 'solicitud', NEW.id_solicitud,
           'Recibiste una nueva solicitud de trabajo'
    FROM servicio_ofrecido so
    WHERE so.id_servicio = NEW.id_servicio;
END//

CREATE TRIGGER trg_notificar_mensaje
AFTER INSERT ON mensaje
FOR EACH ROW
BEGIN
    DECLARE v_cliente   INT;
    DECLARE v_prestador INT;
    DECLARE v_destino   INT;

    SELECT sc.id_cliente, so.id_prestador INTO v_cliente, v_prestador
    FROM solicitud_contratacion sc
    JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio
    WHERE sc.id_solicitud = NEW.id_solicitud;

    IF NEW.id_emisor NOT IN (v_cliente, v_prestador) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'El emisor no participa de esta solicitud';
    END IF;

    SET v_destino = IF(NEW.id_emisor = v_cliente, v_prestador, v_cliente);

    INSERT INTO notificacion (id_usuario, tipo, id_solicitud, id_mensaje, texto)
    VALUES (v_destino, 'mensaje', NEW.id_solicitud, NEW.id_mensaje,
            'Tenés un mensaje nuevo sobre un trabajo');
END//
DELIMITER ;

-- -----------------------------------------------------
-- VISTAS
-- -----------------------------------------------------
CREATE VIEW v_prestadores_disponibles AS
SELECT so.id_servicio,
       p.id_prestador,
       CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS nombre_publico,
       c.nombre AS categoria,
       so.tarifa,
       p.puntuacion_promedio,
       p.latitud,
       p.longitud,
       (SELECT COUNT(*)
          FROM solicitud_contratacion sc
          JOIN servicio_ofrecido so2 ON so2.id_servicio = sc.id_servicio
         WHERE so2.id_prestador = p.id_prestador
           AND sc.estado = 'finalizada') AS servicios_realizados
FROM servicio_ofrecido so
JOIN prestador p          ON p.id_prestador = so.id_prestador
JOIN usuario u            ON u.id_usuario   = p.id_prestador
JOIN categoria_servicio c ON c.id_categoria = so.id_categoria
WHERE so.activo = TRUE
  AND p.estado_verificacion = 'aprobado'
  AND u.estado = 'activo';

CREATE VIEW v_historial_cliente AS
SELECT sc.id_cliente,
       sc.id_solicitud,
       c.nombre AS servicio,
       CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS prestador,
       sc.fecha_hora_programada,
       COALESCE(pa.monto, so.tarifa * sc.duracion_horas) AS monto,
       sc.estado
FROM solicitud_contratacion sc
JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio
JOIN categoria_servicio c ON c.id_categoria = so.id_categoria
JOIN usuario u            ON u.id_usuario   = so.id_prestador
LEFT JOIN pago pa         ON pa.id_solicitud = sc.id_solicitud;

-- -----------------------------------------------------
-- DATOS INICIALES Y REGISTRO DE MIGRACIONES
-- -----------------------------------------------------
INSERT INTO categoria_servicio (id_categoria, nombre, descripcion) VALUES
    (1, 'Limpieza doméstica', 'Limpieza de hogares y departamentos'),
    (2, 'Limpieza de oficinas', 'Limpieza de espacios de trabajo'),
    (3, 'Jardinería', 'Mantenimiento de jardines y espacios verdes'),
    (4, 'Limpieza profunda', 'Limpieza a fondo de hogares, mudanzas y fin de obra');

INSERT INTO _migraciones (version, nombre) VALUES
    ('001', '001_esquema_inicial.sql'),
    ('002', '002_coordenadas_prestador.sql'),
    ('003', '003_indices_optimizacion.sql');
