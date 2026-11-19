-- =====================================================
-- Migración 005: Soporte para DNI frente y dorso separados
-- =====================================================
SET NAMES utf8mb4;

ALTER TABLE documentacion_verificacion
    MODIFY COLUMN tipo_documento ENUM('dni', 'dni_frente', 'dni_dorso', 'antecedentes_penales', 'otro') NOT NULL;
