# REGISTRO DE PRUEBAS Y EVIDENCIAS — INTEGRANTE 1
## Backend de Recintos, Eventos, Organizadores y Autenticación

**Responsable:** Integrante 1  
**Módulos asignados:** RF-01 (Recintos), RF-02 (Eventos y Funciones), RF-03 (Organizadores), RF-04 (Usuarios y Sesiones)  
**Fecha de ejecución:** 16 de noviembre de 2026  
**Estado general:** Completado e integrado en Docker Compose  

---

## 1. Tabla Oficial de Pruebas Automatizadas y Manuales

Según la regla 6 de `dsitribucion.md`, cada prueba cuenta con su requisito, escenario, resultado esperado, resultado obtenido, fecha y nombre del archivo de evidencia asociado.

| Requisito | ID Prueba | Escenario / Caso de prueba | Método / Endpoint | Resultado esperado | Resultado obtenido | Fecha | Archivo de evidencia |
|---|---|---|---|---|---|---|---|
| **RF-01** | PRU-V01 | Creación de recinto tipo Teatro con distribución física genérica (secciones numeradas y general) | `POST /api/v1/venues` | Código 201 Created, documento persistido, cálculo automático de capacidad total (192) | Exitoso (201 Created), JSON retornado con `_id` generado y capacidad calculada | 16/11/2026 | `E01_recinto_teatro.png` |
| **RF-01** | PRU-V02 | Creación de recinto tipo Estadio con múltiples tribunas numeradas y zonas generales | `POST /api/v1/venues` | Código 201 Created, soporte de secciones tipo numerada y general sin modificar esquema | Exitoso (201 Created), persistido en MongoDB | 16/11/2026 | `E01_recinto_estadio.png` |
| **RF-01** | PRU-V03 | Creación de recinto tipo Sala de comedia / bar con secciones tipo mesa | `POST /api/v1/venues` | Código 201 Created, validación de arreglo de mesas y cálculo de puestos | Exitoso (201 Created), soporta mesas sin cambios de código | 16/11/2026 | `E01_recinto_comedia.png` |
| **RF-01** | PRU-V04 | Validación de secciones: intento de registrar secciones con códigos duplicados | `POST /api/v1/venues` | Código 422 Unprocessable Entity ("Los códigos de sección deben ser únicos") | Exitoso (422 devuelto con mensaje explícito) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-01** | PRU-V05 | Validación de datos: capacidad negativa o número de sillas menor o igual a cero | `POST /api/v1/venues` | Código 422 Validación Pydantic | Exitoso (422 rechazado por validador Pydantic) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-01** | PRU-V06 | Control de roles: usuario sin rol administrador intenta crear o eliminar un recinto | `POST /api/v1/venues` | Código 403 Forbidden ("Se requiere rol: administrador") | Exitoso (403 Forbidden bloquea la operación) | 16/11/2026 | `E04_permiso_denegado.png` |
| **RF-01** | PRU-V07 | Consulta de recinto por identificador inexistente | `GET /api/v1/venues/{id}` | Código 404 Not Found ("Recinto no encontrado") | Exitoso (404 devuelto correctamente) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-04** | PRU-A01 | Registro de nuevo usuario comprador con fecha de nacimiento y contraseña | `POST /api/v1/auth/register` | Código 201 Created, usuario insertado con contraseña protegida con hash bcrypt (sin exponer hash) | Exitoso (201 Created), retorna usuario sin campo `contrasenaHash` | 16/11/2026 | `E03_registro_login_sesion.png` |
| **RF-04** | PRU-A02 | Registro con correo electrónico ya existente en la base de datos | `POST /api/v1/auth/register` | Código 409 Conflict ("Ya existe un usuario con ese correo") | Exitoso (409 Conflict prevenido antes de colisión) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-04** | PRU-A03 | Validación de formato de correo y longitud de contraseña (<6 caracteres) | `POST /api/v1/auth/register` | Código 422 Validación Pydantic | Exitoso (422 devuelto) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-04** | PRU-A04 | Inicio de sesión exitoso con credenciales correctas | `POST /api/v1/auth/login` | Código 200 OK, token JWT emitido y clave `sesion:{token}` creada en Redis con TTL de 30 min | Exitoso (200 OK con access_token y TTL en Redis) | 16/11/2026 | `E03_registro_login_sesion.png` |
| **RF-04** | PRU-A05 | Inicio de sesión con contraseña incorrecta o correo inexistente | `POST /api/v1/auth/login` | Código 401 Unauthorized ("Correo o contraseña incorrectos") | Exitoso (401 Unauthorized sin revelar cuál falló) | 16/11/2026 | `E04_permiso_denegado.png` |
| **RF-04** | PRU-A06 | Cierre de sesión (logout) invalidando la sesión en Redis | `POST /api/v1/auth/logout` | Código 204 No Content, clave `sesion:{token}` eliminada de Redis | Exitoso (204 No Content, clave borrada) | 16/11/2026 | `E03_registro_login_sesion.png` |
| **RF-03** | PRU-O01 | Registro de organizador con NIT, comisión porcentual y política de devolución | `POST /api/v1/organizers` | Código 201 Created, documento almacenado en colección `organizadores` | Exitoso (201 Created) | 16/11/2026 | `E05_documentos_mongodb.png` |
| **RF-03** | PRU-O02 | Registro de organizador con NIT repetido | `POST /api/v1/organizers` | Código 409 Conflict ("Ya existe un organizador con ese NIT") | Exitoso (409 Conflict) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-03** | PRU-O03 | Validación de comisión fuera de rango (ej. > 100% o negativa) | `POST /api/v1/organizers` | Código 422 Validación Pydantic | Exitoso (422 rechazado) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-02** | PRU-E01 | Creación de evento con múltiples funciones, ciudades, fechas y precios por sección | `POST /api/v1/events` | Código 201 Created, funciones embebidas con IDs propios, validación de recintos existentes | Exitoso (201 Created con funciones anidadas) | 16/11/2026 | `E02_evento_funciones_precios.png` |
| **RF-02** | PRU-E02 | Creación de evento con organizador inexistente | `POST /api/v1/events` | Código 404 Not Found ("Organizador no encontrado") | Exitoso (404 Not Found) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-02** | PRU-E03 | Validación de coherencia: precios asignados a secciones no pertenecientes al recinto | `POST /api/v1/events` | Código 422 Unprocessable Entity ("Secciones no válidas para el recinto") | Exitoso (422 capturado y detallado) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-02** | PRU-E04 | Validación de restricción de edad negativa | `POST /api/v1/events` | Código 422 Validación Pydantic | Exitoso (422 rechazado) | 16/11/2026 | `E06_datos_invalidos.png` |
| **RF-02** | PRU-E05 | Cancelación de evento existente | `PATCH /api/v1/events/{id}/cancel` | Código 200 OK, estado actualizado a `cancelado` | Exitoso (200 OK) | 16/11/2026 | `E07_swagger_endpoints.png` |
| **RF-02** | PRU-E06 | Consulta pública de eventos con filtros (categoría, ciudad, estado) | `GET /api/v1/events` | Código 200 OK, lista de eventos coincidentes | Exitoso (200 OK) | 16/11/2026 | `E07_swagger_endpoints.png` |

---

## 2. Guía Detallada de Evidencias (E01 a E07)

Para obtener y nombrar las capturas requeridas sin exponer secretos:

### `E01_recinto_teatro.png` / `E01_recinto_estadio.png` / `E01_recinto_comedia.png`
- **Objetivo:** Demostrar que se pueden modelar tres recintos estructuralmente distintos (teatro, estadio, sala de comedia con mesas) usando el mismo esquema genérico en MongoDB y los mismos endpoints, sin modificar código ni tablas.
- **Acción:** Ejecutar `POST /api/v1/venues` para cada tipo de recinto.
- **Evidencia en captura:** Ventana de Swagger o cliente HTTP mostrando la respuesta HTTP 201 con la estructura anidada de secciones y el cálculo de `capacidad_total`.

### `E02_evento_funciones_precios.png`
- **Objetivo:** Mostrar un evento con funciones en diferentes fechas, ciudades y recintos, cada una con su mapa de precios por sección.
- **Acción:** `GET /api/v1/events/{id}` o `POST /api/v1/events`.
- **Evidencia en captura:** Respuesta JSON con el campo `funciones` conteniendo fechas ISO, `recintoId`, `ciudad` y el diccionario `precios: {"PLATEA": ..., "GENERAL": ...}`.

### `E03_registro_login_sesion.png`
- **Objetivo:** Probar el ciclo completo de identidad: registro de usuario, inicio de sesión recibiendo token Bearer y existencia de la clave de sesión en Redis con su TTL (Time to Live).
- **Acción:** 
  1. `POST /api/v1/auth/register`
  2. `POST /api/v1/auth/login`
  3. En terminal Redis: `redis-cli TTL sesion:<token>` y `HGETALL sesion:<token>`
- **Evidencia en captura:** División de pantalla mostrando la respuesta HTTP 200 con el token JWT y la terminal de Redis con la clave activa y su TTL decreciendo desde 1800 segundos.

### `E04_permiso_denegado.png`
- **Objetivo:** Demostrar la seguridad basada en roles (RBAC).
- **Acción:**
  1. Petición autenticada como `comprador` a `POST /api/v1/venues` → Respuesta **403 Forbidden**.
  2. Petición autenticada como `administrador` a la misma ruta → Respuesta **201 Created**.
- **Evidencia en captura:** Swagger o cliente HTTP mostrando el código 403 con mensaje `"Se requiere rol: administrador"`.

### `E05_documentos_mongodb.png`
- **Objetivo:** Comprobar la persistencia física en MongoDB y la seguridad de contraseñas.
- **Acción:** Abrir MongoDB Compass o `mongosh` sobre la base de datos `ticketflow` e inspeccionar:
  - Documento de `usuarios`: verificar que `contrasenaHash` empieza por `$2b$` (bcrypt) y no existe ninguna clave en texto plano.
  - Documentos de `recintos` y `eventos` con su esquema embebido.
- **Evidencia en captura:** Vista de colecciones en MongoDB Compass sin datos sensibles.

### `E06_datos_invalidos.png`
- **Objetivo:** Probar la robustez y validación de entradas.
- **Acción:**
  1. Petición con restricción de edad negativa (`-5`).
  2. Petición de evento con sección que no existe en el recinto asignado.
  3. Petición de recinto con códigos de sección repetidos.
- **Evidencia en captura:** Respuestas HTTP 422 Unprocessable Entity con los mensajes de error correspondientes.

### `E07_swagger_endpoints.png`
- **Objetivo:** Mostrar la documentación interactiva OpenAPI y los módulos del Integrante 1.
- **Acción:** Navegar a `http://localhost:8000/docs`.
- **Evidencia en captura:** Interfaz de Swagger desplegada con las etiquetas **Autenticación**, **Recintos**, **Organizadores** y **Eventos**, con al menos una petición ejecutada en vivo.

---

## 3. Resumen de Pruebas Automatizadas (Pytest)

Las pruebas unitarias implementadas se encuentran organizadas en:
- `backend/tests/conftest.py`: Fixtures para inyección de mocks (`mock_db`, `mock_redis`, usuarios de prueba y `TestClient`).
- `backend/tests/unit/test_venues.py`: 6 casos de prueba (creación de 3 tipos de recintos, validación de unicidad de secciones, validación de capacidad, permisos y 404).
- `backend/tests/unit/test_auth.py`: 6 casos de prueba (registro exitoso, duplicados, validación Pydantic, login válido con sesión Redis, credenciales erróneas y logout).
- `backend/tests/unit/test_organizers.py`: 5 casos de prueba (creación con comisión, unicidad de NIT, validación de porcentajes, permisos y 404).
- `backend/tests/unit/test_events.py`: 6 casos de prueba (creación con funciones embebidas y precios, validación de organizador, coherencia de secciones recinto-evento, edad negativa y cancelación).

Total: **23 pruebas automatizadas unitarias**, cubriendo todos los casos positivos y negativos requeridos.

