-- =====================================================
-- Migración 004: Mejoras en Categorías dinámicas, Bolsa de Anuncios y Contratación
-- =====================================================
SET NAMES utf8mb4;

-- 1. Categorías dinámicas con icono y estado de moderación
ALTER TABLE categoria_servicio
    ADD COLUMN IF NOT EXISTS icono VARCHAR(50) DEFAULT '🧹',
    ADD COLUMN IF NOT EXISTS estado ENUM('activa', 'propuesta') NOT NULL DEFAULT 'activa',
    ADD COLUMN IF NOT EXISTS solicitada_por INT NULL;

-- 2. Tabla de Anuncios de Trabajo (publicados por clientes)
CREATE TABLE IF NOT EXISTS anuncio_trabajo (
    id_anuncio        INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente        INT NOT NULL,
    id_categoria      INT NOT NULL,
    titulo            VARCHAR(120) NOT NULL,
    descripcion       TEXT NOT NULL,
    presupuesto       DECIMAL(10,2) NOT NULL CHECK (presupuesto >= 0),
    fecha_servicio    DATETIME NOT NULL,
    duracion_horas    DECIMAL(4,2) NOT NULL DEFAULT 1.0 CHECK (duracion_horas > 0),
    direccion         VARCHAR(200) NOT NULL,
    estado            ENUM('abierto', 'adjudicado', 'cancelado') NOT NULL DEFAULT 'abierto',
    fecha_creacion    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_anuncio_cliente FOREIGN KEY (id_cliente)
        REFERENCES cliente(id_cliente) ON DELETE CASCADE,
    CONSTRAINT fk_anuncio_categoria FOREIGN KEY (id_categoria)
        REFERENCES categoria_servicio(id_categoria)
) ENGINE=InnoDB;

-- 3. Tabla de Postulaciones a Anuncios (por prestadores verificados)
CREATE TABLE IF NOT EXISTS postulacion_anuncio (
    id_postulacion    INT AUTO_INCREMENT PRIMARY KEY,
    id_anuncio        INT NOT NULL,
    id_prestador      INT NOT NULL,
    propuesta_precio  DECIMAL(10,2) NOT NULL CHECK (propuesta_precio >= 0),
    mensaje           TEXT NULL,
    estado            ENUM('pendiente', 'aceptada', 'rechazada') NOT NULL DEFAULT 'pendiente',
    fecha_postulacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_postulacion_anuncio FOREIGN KEY (id_anuncio)
        REFERENCES anuncio_trabajo(id_anuncio) ON DELETE CASCADE,
    CONSTRAINT fk_postulacion_prestador FOREIGN KEY (id_prestador)
        REFERENCES prestador(id_prestador) ON DELETE CASCADE,
    CONSTRAINT uq_anuncio_prestador UNIQUE (id_anuncio, id_prestador)
) ENGINE=InnoDB;

-- 4. Vincular solicitud_contratacion con anuncio (opcional si proviene de licitación inversa)
ALTER TABLE solicitud_contratacion
    ADD COLUMN IF NOT EXISTS id_anuncio INT NULL;

-- Índices para búsqueda rápida de anuncios y postulaciones
CREATE INDEX IF NOT EXISTS idx_anuncio_categoria_estado ON anuncio_trabajo(id_categoria, estado);
CREATE INDEX IF NOT EXISTS idx_anuncio_cliente ON anuncio_trabajo(id_cliente);
CREATE INDEX IF NOT EXISTS idx_postulacion_anuncio ON postulacion_anuncio(id_anuncio);
CREATE INDEX IF NOT EXISTS idx_postulacion_prestador ON postulacion_anuncio(id_prestador);
