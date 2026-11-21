# Diseño de Base de Datos — TicketFlow (MongoDB)

Este documento detalla el modelado físico y lógico implementado para las colecciones gestionadas por el **Integrante 1**, justificando el uso de documentos embebidos y referencias según la sección 5 y 6 del proyecto.

---

## 1. Justificación de MongoDB

- **Esquema flexible:** Teatros (filas/sillas), estadios (tribunas/generales) y salas de comedia (mesas) poseen geometrías incompatibles en un modelo relacional tradicional. En MongoDB, cada recinto almacena su distribución en un único documento sin necesidad de esquemas rígidos ni tablas intermedias.
- **Documentos embebidos:** Se embeben las secciones dentro del recinto y las funciones dentro del evento para permitir lecturas en una sola operación atómica (sin `JOIN`s costosos).
- **Referencias:** Se usan referencias (`_id`) cuando las entidades crecen de forma independiente (ej: `organizadorId` dentro de evento, `recintoId` dentro de función).

---

## 2. Modelo Genérico del Espacio Físico (Colección `recintos`)

El recinto no almacena documentos individuales por silla. Modela la capacidad geométrica; las sillas ocupadas se deducen a partir de las boletas y reservas.

### Discriminación por tipo de sección
| Tipo de sección | Estructura interna | Capacidad y puestos |
|---|---|---|
| `numerada` | `filas: [{ fila: "A", sillas: 20 }, ...]` | Identificador compuesto: `SECCION-FILA-NUMERO` (ej. `PLATEA-A-12`). |
| `mesa` | `mesas: [{ mesa: "M1", capacidad: 6 }, ...]` | Identificador: `SECCION-MESA` (ej. `VIP-M1`). Se vende completa o por puesto. |
| `general` | `capacidad: 300` | Cupo sin asignación numérica fija. Control atómico en Redis. |

### Documento de ejemplo en MongoDB:
```json
{
  "_id": "rec_teatro_01",
  "nombre": "Teatro Municipal",
  "tipo": "teatro",
  "ciudad": "Cali",
  "direccion": "Cra 5 # 6-32",
  "capacidad_total": 292,
  "secciones": [
    {
      "codigo": "PLATEA",
      "tipo": "numerada",
      "filas": [
        { "fila": "A", "sillas": 20 },
        { "fila": "B", "sillas": 22 }
      ]
    },
    {
      "codigo": "GENERAL",
      "tipo": "general",
      "capacidad": 250
    }
  ]
}
```

---

## 3. Colección `eventos`

Almacena la ficha técnica del evento y un arreglo embebido de funciones. Cada función define precios por sección según el recinto donde se realiza.

```json
{
  "_id": "evt_rock_01",
  "nombre": "Concierto Rock Nacional",
  "categoria": "musica",
  "organizadorId": "org_prod_01",
  "estado": "publicado",
  "restriccionEdad": 16,
  "atributos": {
    "artistas": ["Banda X", "Grupo Y"],
    "duracionMin": 180,
    "genero": "rock"
  },
  "funciones": [
    {
      "funcionId": "fn_rock_01",
      "fechaHora": "2027-02-14T19:00:00-05:00",
      "recintoId": "rec_teatro_01",
      "ciudad": "Cali",
      "estado": "abierta",
      "precios": {
        "PLATEA": 180000,
        "GENERAL": 70000
      }
    }
  ]
}
```

---

## 4. Colección `usuarios`

Credenciales protegidas con hash bcrypt y control de roles (RBAC).

```json
{
  "_id": "usr_carlos_01",
  "nombre": "Carlos Gómez",
  "correo": "carlos@correo.com",
  "contrasenaHash": "$2b$12$e8uqQ...",
  "fechaNacimiento": "1998-07-20",
  "rol": "comprador"
}
```

---

## 5. Colección `organizadores`

Información legal, comisiones pactadas y políticas de devolución.

```json
{
  "_id": "org_prod_01",
  "razonSocial": "Productora Eventos S.A.S.",
  "nit": "900123456-7",
  "contacto": "contacto@productora.com",
  "telefono": "+57 315 1234567",
  "comision": 10.0,
  "politicaDevolucion": "hasta_48h_antes"
}
```

---

## 6. Índices Creados en MongoDB

Implementados en `app/core/database.py` e inicializados en el lifespan de FastAPI:

| Colección | Clave del Índice | Propiedades | Justificación técnica |
|---|---|---|---|
| `usuarios` | `correo` | `unique: true` | Previene colisiones de identidad en registro. |
| `eventos` | `(estado, categoria, funciones.fechaHora)` | Compuesto | Optimiza el catálogo público y los filtros por fecha/categoría. |
| `ordenes` | `idempotencyKey` | `unique: true, partialFilterExpression` | Garantiza que un reintento de pago no duplique órdenes (RF-08). |
| `ordenes` | `(compradorId, fechaCreacion)` | Compuesto | Acelera la consulta "Mis Compras" del usuario. |
| `boletas` | `(funcionId, silla)` | `unique: true, partialFilterExpression: {estado: 'valida'}` | Segunda barrera de seguridad de BD contra la doble venta. |
| `boletas` | `codigo` | `unique: true` | Validación rápida y sin colisiones en el control de acceso. |
| `validaciones` | `(boletaId, fecha)` | Compuesto | Auditoría cronológica de accesos e intentos de fraude. |

## 7. Reservas y disponibilidad (RF-05 a RF-07)

La colección `reservas` conserva la fuente de verdad de cada reserva
temporal. Las sillas numeradas se identifican con el formato
`SECCION-FILA-NUMERO`; las zonas generales usan `seccion` y `cantidad`.
Una reserva activa tiene una vigencia de 10 minutos y se consulta junto con
su fecha `expiraEn`, de modo que una clave Redis vencida no deje una reserva
disponible incorrectamente.

```json
{
  "_id": "res_7f31a2c0",
  "funcionId": "fn_rock_01",
  "usuarioId": "usr_carlos_01",
  "items": [
    { "seccion": "PLATEA", "silla": "PLATEA-A-12", "cantidad": 1 }
  ],
  "estado": "activa",
  "creadaEn": "2026-11-24T10:00:00+00:00",
  "expiraEn": "2026-11-24T10:10:00+00:00"
}
```

Redis actúa como barrera rápida y distribuida. Se usa
`lock:silla:{funcionId}:{silla}` con `SET NX EX 600` para impedir la doble
reserva, `reserva:{reservaId}` para el TTL de la reserva y
`cupo:{funcionId}:{seccion}` con scripts Lua atómicos para zonas generales.
Las operaciones Lua inicializan, decrementan y restauran el contador dentro
de una sola operación Redis. MongoDB mantiene la reserva y sus estados como
guardarraíl definitivo, y el trabajador de expiración sincroniza los recursos
cuando vence el plazo de 10 minutos.
