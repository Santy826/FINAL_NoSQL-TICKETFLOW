# Módulo: Recintos, Eventos, Organizadores y Autenticación

Documentación técnica de la implementación del módulo base de la API REST de TicketFlow.

---

## 1. Alcance del módulo

Este módulo cubre la gestión de usuarios, seguridad, organizadores, eventos y el modelado físico de los recintos:

- **Recintos (RF-01):** Modelado físico genérico para soportar teatros, estadios y salas de comedia sin modificar el esquema de base de datos.
- **Eventos y funciones (RF-02):** Registro de eventos, control de categorías, restricción de edad y funciones anidadas con precios por sección.
- **Organizadores (RF-03):** Registro y consulta de organizadores, NIT, comisiones y políticas de devolución.
- **Usuarios y autenticación (RF-04):** Registro con hash bcrypt, login con JWT, sesiones con expiración en Redis y autorización por roles.

---

## 2. Arquitectura de capas

La implementación sigue la separación de responsabilidades definida para el proyecto:

```
app/
├── core/           # Configuración, conexión a Mongo/Redis y seguridad (JWT, hash)
├── schemas/        # Modelos Pydantic para validación de entrada y salida
├── repositories/   # Operaciones de persistencia y consultas sobre MongoDB
├── services/       # Lógica de negocio, cálculos y validaciones de dominio
└── api/
    ├── dependencies.py # Inyección de dependencias (DB, Redis, autenticación, roles)
    ├── router.py       # Registro central de rutas
    └── routes/         # Endpoints agrupados por recurso
```

---

## 3. Endpoints disponibles

### Autenticación (`/api/v1/auth`)

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/v1/auth/register` | Registro de nuevo usuario | Público |
| POST | `/api/v1/auth/login` | Login, emisión de JWT y sesión en Redis | Público |
| POST | `/api/v1/auth/logout` | Cierre de sesión y eliminación en Redis | Autenticado |

### Recintos (`/api/v1/venues`)

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/v1/venues` | Creación de recinto con secciones | Administrador |
| GET | `/api/v1/venues` | Listado de recintos con filtros | Autenticado |
| GET | `/api/v1/venues/{id}` | Detalle de recinto por ID | Autenticado |
| PATCH | `/api/v1/venues/{id}` | Actualización de datos de recinto | Administrador |
| DELETE | `/api/v1/venues/{id}` | Eliminación de recinto | Administrador |

### Organizadores (`/api/v1/organizers`)

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/v1/organizers` | Registro de organizador | Administrador |
| GET | `/api/v1/organizers` | Listado de organizadores | Autenticado |
| GET | `/api/v1/organizers/{id}` | Detalle de organizador | Autenticado |
| PATCH | `/api/v1/organizers/{id}` | Actualización de datos | Administrador |
| DELETE | `/api/v1/organizers/{id}` | Eliminación de organizador | Administrador |
| GET | `/api/v1/organizers/{id}/events` | Eventos asociados al organizador | Autenticado |

### Eventos (`/api/v1/events`)

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| POST | `/api/v1/events` | Creación de evento con funciones | Organizador / Admin |
| GET | `/api/v1/events` | Listado público con filtros | Público |
| GET | `/api/v1/events/{id}` | Detalle público del evento | Público |
| PATCH | `/api/v1/events/{id}` | Actualización de evento | Organizador / Admin |
| PATCH | `/api/v1/events/{id}/cancel` | Cancelación de evento | Organizador / Admin |
| POST | `/api/v1/events/{id}/shows` | Adición de funciones al evento | Organizador / Admin |

---

## 4. Modelado genérico de recintos

Para evitar alterar colecciones o código con cada tipo de recinto, la distribución física se modela dentro del documento de recinto según el tipo de sección:

- **Numerada:** Arreglo de filas con cantidad de sillas (`{ fila: "A", sillas: 20 }`).
- **Mesa:** Arreglo de mesas con capacidad individual (`{ mesa: "M1", capacidad: 6 }`).
- **General:** Capacidad total sin asignación de puesto individual (`{ capacidad: 300 }`).

Al crear o actualizar un recinto, el servicio calcula automáticamente la `capacidad_total` sumando las secciones y verifica que los códigos de sección no se repitan.

---

## 5. Índices en MongoDB

Configurados al iniciar la aplicación en `app/core/database.py`:

- `usuarios`: Índice único sobre `correo`.
- `eventos`: Índice compuesto sobre `(estado, categoria, funciones.fechaHora)`.
- `ordenes`: Índice único parcial sobre `idempotencyKey`.
- `boletas`: Índice único parcial sobre `(funcionId, silla)` para boletas con estado `valida`, e índice único sobre `codigo`.
- `validaciones`: Índice compuesto sobre `(boletaId, fecha)`.

---

## 6. Pruebas unitarias

Ubicadas en `backend/tests/unit/`:

- `test_venues.py`: Pruebas de creación para teatros, estadios y mesas, validación de códigos de sección únicos, validación de capacidad negativa y control de roles.
- `test_auth.py`: Registro de usuarios, prevención de correos duplicados, login con JWT y sesión Redis, rechazo de credenciales incorrectas y logout.
- `test_organizers.py`: Creación con comisión, control de NIT único, validación de comisiones inválidas y verificación de permisos.
- `test_events.py`: Creación con funciones y precios por sección, validación de recintos existentes, rechazo de secciones inexistentes en el recinto, edad negativa y cancelación.
