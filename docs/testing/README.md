# Pruebas y evidencias

## Pruebas del Integrante 2

Casos cubiertos:

- disponibilidad antes y después de reservar;
- reserva numérica exitosa y cancelación;
- silla repetida rechazada;
- concurrencia de 20 solicitudes sobre una misma silla;
- zona general con decremento REST/Redis;
- expiración automática por TTL y trabajador periódico;
- limitación por IP y ruta mediante Redis;
- validación de silla inexistente.

Ejecutar la suite automatizada dentro de la API:

```bash
docker compose exec api pytest -q
```

Ejecutar concurrencia con dos instancias:

```bash
k6 run tests/performance/reservation.js
BASE_URL=http://localhost:8001 k6 run tests/performance/reservation.js
```

Nota metodológica: el mismo asiento se envía desde múltiples virtual users. El resultado esperado es exactamente una reserva `201` y el resto `409`; ambos puertos deben compartir MongoDB y Redis. La prueba de rendimiento debe informar número de solicitudes, duración, p95, número de éxitos y conflictos.

## Pruebas del Integrante 4

- caché de reportes: primero se genera un cache miss y después un cache hit;
- invalidación: la venta, reserva, cancelación o devolución elimina las claves `report:*`;
- reportes R-01 a R-13 disponibles desde `/api/v1/reports`;
- frontend: mapa de sillas, temporizador de reserva, mis boletas y panel de reportes;
- build de producción React ejecutado dentro del contenedor frontend.

Ejecutar las pruebas específicas:

```bash
docker compose exec api pytest -q tests/unit/test_reports.py
```

Construir el frontend:

```bash
docker compose exec frontend npm run build
```
