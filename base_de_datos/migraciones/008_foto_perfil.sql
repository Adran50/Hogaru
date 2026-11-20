-- Migracion 008: Soporte para foto de perfil en usuario
-- ====================================================

-- 1. Agregar columna foto_perfil a usuario si no existe
SET @existe_col = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'usuario'
      AND COLUMN_NAME = 'foto_perfil'
);

SET @sql_col = IF(@existe_col = 0,
    'ALTER TABLE usuario ADD COLUMN foto_perfil VARCHAR(255) NULL DEFAULT NULL AFTER telefono;',
    'SELECT 1;'
);
PREPARE stmt FROM @sql_col;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. Actualizar vista v_prestadores_disponibles para exponer foto_perfil
CREATE OR REPLACE VIEW v_prestadores_disponibles AS
SELECT so.id_servicio,
       p.id_prestador,
       CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS nombre_publico,
       u.foto_perfil,
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

-- 3. Fotos de demostracion para prestadores iniciales
UPDATE usuario
SET foto_perfil = 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400'
WHERE id_usuario = 2 AND (foto_perfil IS NULL OR foto_perfil = '');

UPDATE usuario
SET foto_perfil = 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400'
WHERE id_usuario = 3 AND (foto_perfil IS NULL OR foto_perfil = '');
