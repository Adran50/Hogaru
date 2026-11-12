-- =====================================================
-- Migración 001: Esquema Inicial de Hogaru
-- =====================================================
SET NAMES utf8mb4;

-- Tabla de control de migraciones
CREATE TABLE IF NOT EXISTS _migraciones (
    id_migracion INT AUTO_INCREMENT PRIMARY KEY,
    version      VARCHAR(50) NOT NULL UNIQUE,
    nombre       VARCHAR(100) NOT NULL,
    aplicada_en  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- USUARIOS (entidad base + especializaciones)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS usuario (
    id_usuario     INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(60)  NOT NULL,
    apellido       VARCHAR(60)  NOT NULL,
    email          VARCHAR(120) NOT NULL UNIQUE,
    contrasena     VARCHAR(255) NOT NULL,
    telefono       VARCHAR(30),
    tipo_cuenta    ENUM('cliente','prestador','administrador') NOT NULL,
    fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado         ENUM('activo','suspendido') NOT NULL DEFAULT 'activo'
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cliente (
    id_cliente INT PRIMARY KEY,
    direccion  VARCHAR(200),
    latitud    DECIMAL(9,6),
    longitud   DECIMAL(9,6),
    CONSTRAINT fk_cliente_usuario FOREIGN KEY (id_cliente)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS prestador (
    id_prestador         INT PRIMARY KEY,
    descripcion          TEXT,
    estado_verificacion  ENUM('pendiente','aprobado','rechazado') NOT NULL DEFAULT 'pendiente',
    puntuacion_promedio  DECIMAL(3,2) NOT NULL DEFAULT 0.00,
    CONSTRAINT fk_prestador_usuario FOREIGN KEY (id_prestador)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS administrador (
    id_admin      INT PRIMARY KEY,
    nivel_permiso ENUM('moderador','superadmin') NOT NULL DEFAULT 'moderador',
    CONSTRAINT fk_admin_usuario FOREIGN KEY (id_admin)
        REFERENCES usuario(id_usuario) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- VERIFICACION DE PRESTADORES
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS documentacion_verificacion (
    id_documento   INT AUTO_INCREMENT PRIMARY KEY,
    id_prestador   INT NOT NULL,
    id_admin       INT NULL,
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
CREATE TABLE IF NOT EXISTS categoria_servicio (
    id_categoria INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(80) NOT NULL UNIQUE,
    descripcion  VARCHAR(200)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS servicio_ofrecido (
    id_servicio  INT AUTO_INCREMENT PRIMARY KEY,
    id_prestador INT NOT NULL,
    id_categoria INT NOT NULL,
    descripcion  TEXT,
    tarifa       DECIMAL(10,2) NOT NULL CHECK (tarifa >= 0),
    activo       BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_serv_prestador FOREIGN KEY (id_prestador)
        REFERENCES prestador(id_prestador) ON DELETE CASCADE,
    CONSTRAINT fk_serv_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria_servicio(id_categoria)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS disponibilidad (
    id_disponibilidad INT AUTO_INCREMENT PRIMARY KEY,
    id_servicio       INT NOT NULL,
    dia_semana        TINYINT NOT NULL CHECK (dia_semana BETWEEN 1 AND 7),
    hora_inicio       TIME NOT NULL,
    hora_fin          TIME NOT NULL,
    CHECK (hora_fin > hora_inicio),
    CONSTRAINT fk_disp_servicio FOREIGN KEY (id_servicio)
        REFERENCES servicio_ofrecido(id_servicio) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -----------------------------------------------------
-- CONTRATACION
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS solicitud_contratacion (
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
-- PAGOS
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS pago (
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
-- CALIFICACIONES
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS calificacion (
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
CREATE TABLE IF NOT EXISTS disputa (
    id_disputa     INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud   INT NOT NULL,
    id_admin       INT NULL,
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
-- MENSAJES Y NOTIFICACIONES
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS mensaje (
    id_mensaje   INT AUTO_INCREMENT PRIMARY KEY,
    id_solicitud INT NOT NULL,
    id_emisor    INT NOT NULL,
    contenido    TEXT NOT NULL,
    fecha_envio  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_msj_solicitud FOREIGN KEY (id_solicitud)
        REFERENCES solicitud_contratacion(id_solicitud) ON DELETE CASCADE,
    CONSTRAINT fk_msj_emisor FOREIGN KEY (id_emisor)
        REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notificacion (
    id_notificacion INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario      INT NOT NULL,
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
-- INDICES
-- -----------------------------------------------------
CREATE INDEX idx_servicio_categoria ON servicio_ofrecido(id_categoria);
CREATE INDEX idx_solicitud_cliente  ON solicitud_contratacion(id_cliente);
CREATE INDEX idx_solicitud_servicio ON solicitud_contratacion(id_servicio);
CREATE INDEX idx_solicitud_estado   ON solicitud_contratacion(estado);
CREATE INDEX idx_mensaje_solicitud  ON mensaje(id_solicitud, fecha_envio);
CREATE INDEX idx_notif_usuario      ON notificacion(id_usuario, leida, fecha);

-- Categorías iniciales
INSERT IGNORE INTO categoria_servicio (id_categoria, nombre, descripcion) VALUES
    (1, 'Limpieza doméstica', 'Limpieza de hogares y departamentos'),
    (2, 'Limpieza de oficinas', 'Limpieza de espacios de trabajo'),
    (3, 'Jardinería', 'Mantenimiento de jardines y espacios verdes'),
    (4, 'Limpieza profunda', 'Limpieza a fondo de hogares, mudanzas y fin de obra');
