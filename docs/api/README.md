# Contratos de API REST — TicketFlow (v1)

Endpoints implementados por el **Integrante 1**. Todos los endpoints tienen como base el prefijo `/api/v1` y siguen el estándar REST con formato JSON.

---

## 1. Módulo de Autenticación (`/api/v1/auth`)

### `POST /api/v1/auth/register`
* **Permiso:** Público
* **Cuerpo de la petición:**
```json
{
  "nombre": "Carlos Gómez",
  "correo": "carlos@correo.com",
  "contrasena": "ClaveSegura123!",
  "fechaNacimiento": "1998-07-20",
  "rol": "comprador"
}
```
* **Respuesta exitosa (201 Created):**
```json
{
  "_id": "usr_carlos_01",
  "nombre": "Carlos Gómez",
  "correo": "carlos@correo.com",
  "fechaNacimiento": "1998-07-20",
  "rol": "comprador"
}
```

### `POST /api/v1/auth/login`
* **Permiso:** Público
* **Cuerpo de la petición:**
```json
{
  "correo": "carlos@correo.com",
  "contrasena": "ClaveSegura123!"
}
```
* **Respuesta exitosa (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "usuario": {
    "_id": "usr_carlos_01",
    "nombre": "Carlos Gómez",
    "correo": "carlos@correo.com",
    "fechaNacimiento": "1998-07-20",
    "rol": "comprador"
  }
}
```

### `POST /api/v1/auth/logout`
* **Permiso:** Autenticado (Header: `Authorization: Bearer <token>`)
* **Respuesta:** 204 No Content (Invalida la sesión en Redis)

---

## 2. Módulo de Recintos (`/api/v1/venues`)

### `POST /api/v1/venues`
* **Permiso:** `administrador`
* **Cuerpo de la petición (Ejemplo teatro):**
```json
{
  "nombre": "Teatro Municipal",
  "tipo": "teatro",
  "ciudad": "Cali",
  "direccion": "Cra 5 # 6-32",
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
* **Respuesta exitosa (201 Created):** Retorna el documento creado incluyendo `_id` y `capacidad_total: 292`.

### `GET /api/v1/venues`
* **Permiso:** Autenticado
* **Query params:** `?ciudad=Cali&tipo=teatro` (opcionales)
* **Respuesta exitosa (200 OK):** Lista de recintos coincidentes.

### `GET /api/v1/venues/{id}`
* **Permiso:** Autenticado
* **Respuesta:** 200 OK con el detalle del recinto o 404 Not Found.

---

## 3. Módulo de Organizadores (`/api/v1/organizers`)

### `POST /api/v1/organizers`
* **Permiso:** `administrador`
* **Cuerpo de la petición:**
```json
{
  "razonSocial": "Productora Eventos S.A.S.",
  "nit": "900123456-7",
  "contacto": "contacto@productora.com",
  "telefono": "+57 315 1234567",
  "comision": 10.0,
  "politicaDevolucion": "hasta_48h_antes"
}
```
* **Respuesta:** 201 Created con `_id` generado.

### `GET /api/v1/organizers/{id}/events`
* **Permiso:** Autenticado
* **Respuesta (200 OK):** Lista de eventos registrados a nombre de dicho organizador.

---

## 4. Módulo de Eventos (`/api/v1/events`)

### `POST /api/v1/events`
* **Permiso:** `organizador` o `administrador`
* **Cuerpo de la petición:**
```json
{
  "nombre": "Noche de Comedia en Vivo",
  "categoria": "comedia",
  "organizadorId": "org_comedy_01",
  "restriccionEdad": 18,
  "atributos": {
    "artistas": ["Comediante A", "Comediante B"],
    "duracionMin": 120
  },
  "funciones": [
    {
      "fechaHora": "2027-01-23T20:00:00-05:00",
      "recintoId": "rec_comedy_01",
      "ciudad": "Bogotá",
      "estado": "abierta",
      "precios": {
        "PRINCIPAL": 150000,
        "VIP": 250000
      }
    }
  ]
}
```
* **Respuesta exitosa (201 Created):** Documento creado en estado `"borrador"` y `funcionId` autogenerado por cada función.

### `GET /api/v1/events`
* **Permiso:** Público
* **Query params:** `?categoria=comedia&estado=publicado&ciudad=Bogota`
* **Respuesta:** 200 OK con el listado de eventos disponibles.

### `PATCH /api/v1/events/{id}/cancel`
* **Permiso:** `organizador` o `administrador`
* **Respuesta (200 OK):** Actualiza el estado a `"cancelado"`.

## 5. Disponibilidad y reservas (Integrante 2)

### `GET /api/v1/shows/{funcionId}/availability`
Retorna las secciones de la función con capacidad, cupos disponibles y
estados `libre`, `reservada` o `vendida` para puestos numerados.

### `GET /api/v1/shows/{funcionId}/seats`
Retorna las sillas numeradas y el resumen de zonas generales.

### `POST /api/v1/reservations`
Requiere autenticación. Recibe `funcionId` e `items`, donde cada silla
numerada se indica como `seccion`, `silla` y `cantidad: 1`; una zona general
se indica con `seccion` y `cantidad`.

```json
{
  "funcionId": "fn_rock_01",
  "items": [
    { "seccion": "PLATEA", "silla": "PLATEA-A-12", "cantidad": 1 }
  ]
}
```

La respuesta es `201 Created` y contiene `estado: "activa"` y `expiraEn`
diez minutos después de `creadaEn`. Redis crea el bloqueo atómico
`lock:silla:{funcionId}:{silla}` con TTL de 600 segundos.

### `GET /api/v1/reservations/{id}` y `DELETE /api/v1/reservations/{id}`
Requieren autenticación y solo permiten consultar o cancelar la reserva de su
propietario. La cancelación libera los bloqueos y restaura el cupo general.

Las reservas activas vencen a los 10 minutos. Un trabajador periódico también
marca reservas expiradas en MongoDB y libera sus recursos; la clave Redis expira
el bloqueo aunque la API se reinicie.

## 6. Órdenes y pagos simulados

### `POST /api/v1/orders`

Requiere autenticación con rol `comprador` o `administrador`. Confirma el pago
simulado de una reserva activa y devuelve `201 Created`. El primer pago crea una
orden; repetir exactamente la misma petición devuelve `200 OK` con la misma
orden.

```json
{
  "reservaId": "res_412de009",
  "idempotencyKey": "e15-payment-001",
  "metodoPago": "simulado"
}
```

La clave de idempotencia se conserva en Redis como `idem:{clave}` durante
24 horas y también existe como índice único en MongoDB. Una reserva vencida,
pagada, inexistente o ajena al usuario devuelve un conflicto o error apropiado.

### `GET /api/v1/orders/{id}`

Permite consultar una orden al comprador propietario o a un administrador.

### `GET /api/v1/users/{id}/orders`

Permite al comprador consultar sus propias órdenes y al administrador consultar
las órdenes de cualquier usuario.

## 7. Boletas y validación de acceso

Después de confirmar el pago se generan automáticamente boletas firmadas. Una
silla numerada genera una boleta; una zona general genera una boleta por cada
cupo comprado.

Cada boleta incluye:

- `_id`;
- código aleatorio firmado con HMAC-SHA256;
- código QR almacenado como contenido o imagen codificada;
- orden, comprador, función, sección y silla;
- estado `valida`, `usada`, `devuelta` o `anulada`.

Endpoints disponibles:

- `GET /api/v1/tickets/{id}`;
- `GET /api/v1/tickets/mine`;
- `POST /api/v1/tickets/validate`.

La validación requiere rol `validador` o `administrador`.

```json
{
  "codigo": "bol_xxxxxxxx.signature",
  "puerta": "Puerta Norte"
}
```

Una validación exitosa cambia la boleta a `usada` de forma atómica y registra
un documento en `validaciones`. Los intentos alterados, repetidos, devueltos o
anulados también quedan registrados.

Redis protege cada entrada con `lock:validacion:{boletaId}` durante cinco
segundos. MongoDB realiza el cambio final `valida -> usada` para que solo una
validación concurrente pueda tener éxito.

## 8. Lotes y facturas

### `POST /api/v1/batches`

Requiere rol `organizador` o `administrador`.

Tipos admitidos:

- `preventa`;
- `ampliacion`;
- `nueva_seccion`;
- `nueva_funcion`.

Ejemplo para ampliar una zona general:

```json
{
  "tipo": "ampliacion",
  "funcionId": "fn_rock_01",
  "seccion": "ORIENTAL",
  "cantidad": 100,
  "precio": 80000
}
```

La creación registra el lote en `lotes`, actualiza la capacidad general del
recinto o crea la función solicitada, sincroniza Redis y genera una factura
única en `facturas`.

### `GET /api/v1/invoices`

Retorna las facturas emitidas. Un administrador puede ver todas; un organizador
solo puede consultar las facturas asociadas a su organizador.

## 9. Devoluciones

### `POST /api/v1/refunds`

Permite al comprador solicitar la devolución de una de sus boletas válidas.

```json
{
  "boletaId": "bol_xxxxxxxx",
  "tipo": "reembolso",
  "motivo": "No podré asistir"
}
```

Para cambio de función se agrega `nuevaFuncionId`.

La solicitud valida:

- que la boleta exista y pertenezca al usuario;
- que esté en estado `valida`;
- que no exista una solicitud pendiente;
- la política `sin_devolucion` o `hasta_48h_antes` del organizador.

### `PATCH /api/v1/refunds/{id}/approve`

Aprueba una devolución pendiente. Al aprobar:

- la boleta pasa a `devuelta`;
- se libera el bloqueo Redis de silla si existe;
- se devuelve el cupo general en Redis;
- la orden pasa a `reembolsada`;
- se registra quién aprobó y cuándo.

### `PATCH /api/v1/refunds/{id}/reject`

Rechaza una devolución pendiente sin cambiar la boleta ni liberar inventario.

```json
{
  "motivo": "La solicitud excedió el plazo permitido"
}
```

## 10. Concurrencia y limitación

Redis conserva los bloqueos compartidos por las dos instancias de API:

- `lock:silla:{funcionId}:{silla}` con `SET NX EX 600`;
- `cupo:{funcionId}:{seccion}` con un script Lua atómico para reservar y restaurar cupos;
- `reserva:{reservaId}` con TTL de 600 segundos;
- `ratelimit:{ip}:{ruta}` con una ventana configurable de 60 segundos.

Al exceder `RATE_LIMIT_REQUESTS`, la API responde `429 Too Many Requests` y
`Retry-After`. Redis es la barrera rápida distribuida; MongoDB conserva el
estado definitivo y las reservas vencidas.
