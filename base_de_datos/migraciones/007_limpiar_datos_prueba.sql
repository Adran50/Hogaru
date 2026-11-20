-- Migracion 007: Limpiar categorias de prueba y corregir iconos

UPDATE categoria_servicio SET nombre = 'Tapizados y sillones', descripcion = 'Limpieza a vapor y restauracion de tapizados, sillones y colchones', icono = CHAR(0xF0,0x9F,0x9B,0x8B) WHERE id_categoria = 5;
UPDATE servicio_ofrecido SET id_categoria = 5 WHERE id_categoria IN (6, 7, 8, 9, 10);
DELETE FROM categoria_servicio WHERE id_categoria IN (6, 7, 8, 9, 10);
UPDATE categoria_servicio SET icono = CHAR(0xF0,0x9F,0x8F,0xA0) WHERE id_categoria = 1;
UPDATE categoria_servicio SET icono = CHAR(0xF0,0x9F,0x8F,0xA2) WHERE id_categoria = 2;
UPDATE categoria_servicio SET icono = CHAR(0xF0,0x9F,0x8C,0xBF) WHERE id_categoria = 3;
UPDATE categoria_servicio SET icono = CHAR(0xF0,0x9F,0xA7,0xBD) WHERE id_categoria = 4;
INSERT INTO categoria_servicio (id_categoria, nombre, descripcion, icono, estado) SELECT 11, 'Planchado y lavanderia', 'Servicio de planchado lavado y organizacion de ropa', CHAR(0xF0,0x9F,0x91,0x95), 'activa' WHERE NOT EXISTS (SELECT 1 FROM categoria_servicio WHERE id_categoria = 11);
