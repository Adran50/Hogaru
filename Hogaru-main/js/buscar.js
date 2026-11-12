// ===== Búsqueda y filtrado de servicios =====
(async function () {
  var LIMITE = 12;
  var pagina = 1;
  var total = 0;
  var aviso = document.getElementById('aviso');
  var resultados = document.getElementById('resultados');
  var verMas = document.getElementById('ver-mas');

  try {
    var categorias = await api('/categorias');
    var sel = document.getElementById('categoria');
    categorias.forEach(function (c) {
      sel.insertAdjacentHTML('beforeend', '<option value="' + c.id_categoria + '">' + esc(c.nombre) + '</option>');
    });
  } catch (e) { /* se puede buscar igual */ }

  // Filtros que vienen de la URL (por ejemplo desde el inicio)
  document.getElementById('q').value = param('q') || '';
  document.getElementById('categoria').value = param('categoria') || '';

  async function buscar(reiniciar) {
    if (reiniciar) { pagina = 1; total = 0; resultados.innerHTML = ''; }
    ocultarAviso(aviso);
    try {
      var lista = await api('/servicios', { params: {
        q: document.getElementById('q').value.trim(),
        categoria: document.getElementById('categoria').value,
        tarifa_max: document.getElementById('tarifa-max').value,
        orden: document.getElementById('orden').value,
        limite: LIMITE,
        pagina: pagina,
      } });
      total += lista.length;
      resultados.insertAdjacentHTML('beforeend', lista.map(tarjetaServicio).join(''));
      document.getElementById('resumen').textContent = total
        ? total + (total === 1 ? ' servicio encontrado' : ' servicios encontrados')
        : 'No encontramos servicios con esos filtros.';
      verMas.classList.toggle('oculto', lista.length < LIMITE);
    } catch (e) {
      mostrarAviso(aviso, 'error', e.message);
    }
  }

  document.getElementById('filtros').addEventListener('submit', function (e) { e.preventDefault(); buscar(true); });
  verMas.addEventListener('click', function () { pagina += 1; buscar(false); });
  buscar(true);
})();
