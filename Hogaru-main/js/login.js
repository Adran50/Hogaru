// ===== Login =====
(function () {
  var aviso = document.getElementById('aviso');
  var btn = document.getElementById('btn');

  // Solo se aceptan destinos internos del tipo "solicitud.html?id=3" (evita redirecciones a otros sitios)
  function destinoSeguro(next) {
    return next && /^(\.\.\/)?[\w-]+\.html(\?[\w=&%.-]*)?$/.test(next) ? next : null;
  }

  document.getElementById('form-login').addEventListener('submit', async function (e) {
    e.preventDefault();
    ocultarAviso(aviso);
    ocupado(btn, true);
    try {
      var r = await api('/auth/login', {
        metodo: 'POST',
        cuerpo: { email: document.getElementById('email').value.trim(), password: document.getElementById('password').value },
      });
      Sesion.guardar(r.access_token, r.usuario);
      location.href = destinoSeguro(param('next')) || inicioSegunTipo(r.usuario.tipo_cuenta);
    } catch (err) {
      mostrarAviso(aviso, 'error', err.message);
      ocupado(btn, false);
    }
  });
})();
