-- =====================================================
-- Migración 009: Perfil ampliado y gestión de categorías
-- =====================================================
SET NAMES utf8mb4;

-- 1. Agregar biografía, control de cambio de nombre y redes sociales a usuario
ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS biografia VARCHAR(200) NULL DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS fecha_ultimo_cambio_nombre DATETIME NULL DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS redes_sociales TEXT NULL DEFAULT NULL;

-- 2. Permitir estado 'inactiva' en categoria_servicio para borrado lógico seguro por admins
ALTER TABLE categoria_servicio
    MODIFY COLUMN estado ENUM('activa', 'propuesta', 'inactiva') NOT NULL DEFAULT 'activa';
