-- =====================================================
-- Migración 003: Índices de optimización de búsquedas y relaciones
-- =====================================================
SET NAMES utf8mb4;

-- Índices en coordenadas para filtrado de cercanía
CREATE INDEX IF NOT EXISTS idx_prestador_coords ON prestador(latitud, longitud);

-- Índices en prestador y estado de servicio
CREATE INDEX IF NOT EXISTS idx_servicio_prestador_activo ON servicio_ofrecido(id_prestador, activo);

-- Índices en fecha programada de contratación
CREATE INDEX IF NOT EXISTS idx_solicitud_fecha ON solicitud_contratacion(fecha_hora_programada);

-- Índices en disponibilidad por servicio y día
CREATE INDEX IF NOT EXISTS idx_disp_servicio_dia ON disponibilidad(id_servicio, dia_semana);

-- Índices en documentación por prestador y estado
CREATE INDEX IF NOT EXISTS idx_doc_prestador_estado ON documentacion_verificacion(id_prestador, estado);

-- Índices en disputa por solicitud y estado
CREATE INDEX IF NOT EXISTS idx_disputa_solicitud_estado ON disputa(id_solicitud, estado);
