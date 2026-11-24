# TicketFlow

API REST para gestión de eventos, recintos, reservas y venta de boletería con
MongoDB y Redis.

## Estado del proyecto

El proyecto incluye la base funcional de FastAPI, MongoDB y Redis. El módulo
del Integrante 1 está implementado y el módulo del Integrante 2 incluye
disponibilidad, reservas temporales, concurrencia Redis y limitación de
solicitudes. Los módulos de los Integrantes 3 y 4 continúan según
`DISTRIBUCION_TAREAS_TICKETFLOW.txt`.

## Estructura

- `backend/`: API FastAPI, dominio, servicios, repositorios y pruebas.
- `frontend/`: aplicación React y componentes de la experiencia de compra.
- `docs/`: arquitectura, contratos, decisiones técnicas y evidencias.
- `scripts/`: datos de demostración y utilidades futuras.
- `tests/`: pruebas de integración y rendimiento.

## Inicio

1. Copiar `.env.example` a `.env`.
2. Ejecutar `docker compose up --build`.
3. Cargar datos de demostración con
   `docker compose exec api python scripts/seed.py`.
4. Ejecutar pruebas con `docker compose exec api pytest -q`.

## Reglas iniciales

- No agregar secretos al repositorio.
- Cada módulo debe incluir pruebas y documentación de sus endpoints.
- Mantener la separación entre rutas, servicios, repositorios y modelos.

## Integrante 4

- Los reportes R-01 a R-13 están disponibles bajo `/api/v1/reports`.
- Las respuestas incluyen el encabezado `X-Cache` con los valores `miss` o `hit`.
- Los reportes usan caché Redis con TTL de 300 segundos y se invalidan después de reservas, pagos y devoluciones.
- El frontend incluye mapa de sillas, carrito con temporizador, mis boletas y panel de reportes.
- El frontend incluye un panel administrativo para crear recintos por escenario, organizadores y eventos con funciones.
- También permite crear lotes/facturas, gestionar devoluciones y validar boletas desde la interfaz.
- Swagger: <http://localhost:8000/docs>.