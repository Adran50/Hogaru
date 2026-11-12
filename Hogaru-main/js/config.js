// Dirección donde corre el backend (FastAPI). Cambiala si usás otro puerto o servidor.
window.HOGARU_API_URL = (window.location.port === '8000')
  ? window.location.origin
  : 'http://localhost:8000';
