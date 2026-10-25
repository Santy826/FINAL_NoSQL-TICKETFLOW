# TicketFlow

API REST para gestión de eventos, recintos, reservas y venta de boletería con
MongoDB y Redis.

## Estado del proyecto

Este repositorio contiene el esqueleto inicial. La estructura está preparada
para implementar progresivamente los módulos definidos en
`DISTRIBUCION_TAREAS_TICKETFLOW.txt`; todavía no contiene lógica de negocio.

## Estructura

- `backend/`: API FastAPI, dominio, servicios, repositorios y pruebas.
- `frontend/`: aplicación React y componentes de la experiencia de compra.
- `docs/`: arquitectura, contratos, decisiones técnicas y evidencias.
- `scripts/`: datos de demostración y utilidades futuras.
- `tests/`: pruebas de integración y rendimiento.

## Inicio previsto

1. Copiar `.env.example` a `.env`.
2. Ejecutar `docker compose up --build`.
3. Implementar los módulos siguiendo la distribución de tareas y actualizar
   la matriz de trazabilidad.

## Reglas iniciales

- No agregar secretos al repositorio.
- Cada módulo debe incluir pruebas y documentación de sus endpoints.
- Mantener la separación entre rutas, servicios, repositorios y modelos.