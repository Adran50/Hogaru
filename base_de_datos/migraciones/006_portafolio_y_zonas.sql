-- =====================================================
-- Migración 006: Zonas de cobertura y Galería de Trabajos Previos (Portafolio)
-- =====================================================
SET NAMES utf8mb4;

-- 1. Agregar zona_cobertura a prestador
ALTER TABLE prestador
    ADD COLUMN IF NOT EXISTS zona_cobertura VARCHAR(100) NULL DEFAULT 'Morón y alrededores';

-- Actualizar prestadores de prueba con zonas
UPDATE prestador SET zona_cobertura = 'Morón, Haedo y Castelar' WHERE id_prestador = 2;
UPDATE prestador SET zona_cobertura = 'Haedo y Ramos Mejía' WHERE id_prestador = 3;
UPDATE prestador SET zona_cobertura = 'Castelar e Ituzaingó' WHERE id_prestador = 4;
UPDATE prestador SET zona_cobertura = 'Ramos Mejía y San Justo' WHERE id_prestador = 8;

-- 2. Tabla para galería / portafolio de trabajos realizados
CREATE TABLE IF NOT EXISTS portafolio_prestador (
    id_foto INT AUTO_INCREMENT PRIMARY KEY,
    id_prestador INT NOT NULL,
    archivo_url VARCHAR(255) NOT NULL,
    titulo VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255) NULL,
    fecha_carga DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_portafolio_prestador FOREIGN KEY (id_prestador)
        REFERENCES prestador(id_prestador) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 3. Actualizar vista v_prestadores_disponibles para exponer la zona
CREATE OR REPLACE VIEW v_prestadores_disponibles AS
SELECT so.id_servicio,
       p.id_prestador,
       CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS nombre_publico,
       c.nombre AS categoria,
       so.tarifa,
       p.puntuacion_promedio,
       p.latitud,
       p.longitud,
       p.zona_cobertura,
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

-- 4. Fotos de prueba iniciales para la galería de Marisa y Roberto
INSERT IGNORE INTO portafolio_prestador (id_foto, id_prestador, archivo_url, titulo, descripcion) VALUES
(1, 2, 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=800', 'Limpieza profunda de cocina', 'Desengrasado total de campana, alacenas y pisos cerámicos.'),
(2, 2, 'https://images.unsplash.com/photo-1527515637462-cff94eecc1ac?w=800', 'Organización y planchado', 'Planchado prolijo y organización por prenda y color.'),
(3, 3, 'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800', 'Sanitización de baños', 'Limpieza y desinfección a vapor en azulejos e hidromasajes.'),
(4, 3, 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800', 'Mantenimiento de exteriores', 'Lavado a presión de patio y veredas.');
