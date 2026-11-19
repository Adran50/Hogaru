-- =====================================================
-- Migración 002: Coordenadas geográficas para prestador y actualización de vistas
-- =====================================================
SET NAMES utf8mb4;

-- Agregar latitud y longitud a prestador para cálculo de distancia Haversine
ALTER TABLE prestador
    ADD COLUMN IF NOT EXISTS latitud DECIMAL(9,6) NULL,
    ADD COLUMN IF NOT EXISTS longitud DECIMAL(9,6) NULL;

-- Recrear vista con latitud y longitud
CREATE OR REPLACE VIEW v_prestadores_disponibles AS
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
