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
