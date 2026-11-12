// ===== Página de inicio =====
(async function () {
  var selectCategoria = document.getElementById('categoria');
  var destacados = document.getElementById('destacados');

  document.getElementById('form-buscar').addEventListener('submit', function (e) {
    e.preventDefault();
    var q = document.getElementById('q').value.trim();
    var cat = selectCategoria.value;
    var url = RAIZ + 'paginas/buscar.html?';
    if (q) url += 'q=' + encodeURIComponent(q) + '&';
    if (cat) url += 'categoria=' + encodeURIComponent(cat);
    location.href = url;
  });

  try {
    var categorias = await api('/categorias');
    categorias.forEach(function (c) {
      selectCategoria.insertAdjacentHTML('beforeend', '<option value="' + c.id_categoria + '">' + esc(c.nombre) + '</option>');
    });
  } catch (e) { /* el buscador funciona igual sin categorías */ }

  try {
    var servicios = await api('/servicios', { params: { limite: 6 } });
    destacados.innerHTML = servicios.length
      ? servicios.map(tarjetaServicio).join('')
      : '<p class="muted">Todavía no hay prestadores publicados.</p>';
  } catch (e) {
    destacados.innerHTML = '<div class="aviso aviso-error">' + esc(e.message) + '</div>';
  }
})();
