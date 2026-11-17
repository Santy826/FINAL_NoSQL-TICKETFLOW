Universidad del Valle – Sede Tuluá

Ingeniería de Sistemas · Bases de Datos No Relacionales

**PROYECTO FINAL: TICKETFLOW**

**Sistema inteligente de gestión de eventos y venta de boletería**

Tecnologías: Python, FastAPI, MongoDB y Redis (frontend opcional en React).

Fecha de entrega: 22 de diciembre de 2026

 

# **1\. Definición del proyecto**

Una empresa comercializa boletería para eventos de naturaleza muy distinta (conciertos, shows de comedia, obras de teatro, partidos deportivos, conferencias y festivales) que se realizan en recintos muy diferentes entre sí: teatros con sillas numeradas, estadios con tribunas y zonas generales, coliseos, auditorios y salas de comedia con mesas. Cada recinto tiene una distribución física propia, y cada evento puede tener varias funciones en fechas y ciudades distintas, con precios diferentes según la zona del recinto.

Actualmente existen dificultades para conocer la disponibilidad de las sillas en tiempo real, evitar que dos personas compren la misma silla al mismo tiempo (incluso si sus solicitudes llegan a servicios o instancias distintas de la aplicación), evitar que las boletas sean clonadas o usadas dos veces, y analizar quién compra: edad de los compradores, tipo de evento preferido y sillas más vendidas.

Se propone desarrollar TicketFlow, una API REST utilizando Python y FastAPI, con MongoDB como base de datos no relacional principal y Redis para la información temporal, el control de concurrencia y la optimización de consultas frecuentes. El sistema modelará el espacio físico de forma genérica, de modo que cualquier tipo de recinto pueda registrarse sin modificar el esquema ni el código.

## **1.1 Justificación del uso de bases de datos no relacionales**

•        **Esquema flexible:** un teatro, un estadio y una sala de comedia se describen con estructuras distintas; en MongoDB cada recinto guarda su propia distribución (secciones, filas, mesas, zonas generales) sin tablas rígidas.

•        **Documentos anidados:** las funciones de un evento y las secciones de un recinto se consultan junto con su documento padre, sin JOINs.

•        **Concurrencia:** Redis permite bloquear sillas de forma atómica y con expiración, lo que evita la doble venta aunque haya varias instancias de la API.

•        **Reportes con agregaciones:** perfiles de compradores, ventas por categoría y sillas más vendidas se calculan con aggregation pipelines.

# **2\. Objetivo general**

Diseñar e implementar una API REST que permita gestionar eventos y venta de boletería mediante MongoDB y Redis, aprovechando las características de las bases de datos no relacionales para modelar recintos de cualquier tipo, evitar la doble venta de sillas, validar boletas sin posibilidad de clonación y generar reportes sobre ventas y perfil de los compradores.

## **2.1 Objetivos específicos**

•        Modelar el espacio físico de forma genérica para soportar distintos tipos de recintos.

•        Garantizar que una misma silla no pueda venderse a dos compradores, ni siquiera con solicitudes simultáneas a distintas instancias del servicio.

•        Emitir boletas únicas, firmadas y de un solo uso, y validarlas en el acceso detectando intentos de clonación.

•        Generar reportes de ventas, aforo, perfil de compradores (edad, tipo de evento) y sillas más vendidas.

•        Usar Redis para reservas temporales, bloqueos, idempotencia, sesiones y caché.

•        Comparar el rendimiento con y sin Redis, y frente a un modelo relacional equivalente.

# **3\. Actores y alcance**

| Actor | Descripción | Acciones principales |
| :---- | :---- | :---- |
| Comprador | Usuario final que adquiere boletas | Consultar eventos, elegir sillas, reservar, pagar, ver sus boletas, solicitar devoluciones |
| Organizador | Empresa o persona que realiza los eventos | Crear eventos y funciones, registrar lotes adicionales, ver ventas y facturas |
| Administrador | Personal de la plataforma | Gestionar recintos y organizadores, aprobar devoluciones, consultar reportes |
| Validador de acceso | Personal en la entrada del evento | Validar boletas mediante el código QR |

 

**Fuera del alcance:** pasarelas de pago reales (el pago se simula), aplicaciones móviles nativas y transferencia de boletas entre usuarios.

# **4\. Requerimientos funcionales**

•        **RF-01. Gestión de recintos y escenarios:** registrar recintos con su distribución física genérica: secciones, filas, sillas, mesas y zonas generales (ver sección 5).

•        **RF-02. Gestión de eventos y funciones:** registrar eventos con categoría (música, comedia, teatro, deportivo, conferencia, festival), atributos propios de la categoría, restricción de edad y una o varias funciones con fecha, recinto, ciudad y precio por sección.

•        **RF-03. Gestión de organizadores:** registrar razón social, NIT, contacto, comisión, condiciones de pago y política de devolución.

•        **RF-04. Gestión de usuarios y sesiones:** registrar usuarios con fecha de nacimiento y rol (comprador, organizador, administrador, validador); sesiones con expiración en Redis.

•        **RF-05. Control de disponibilidad en tiempo real:** consultar sillas libres, reservadas y vendidas por función y sección, y cupos de las zonas generales.

•        **RF-06. Gestión de reservas temporales:** bloquear las sillas elegidas durante un tiempo limitado (por ejemplo, 10 minutos) mientras el comprador paga; liberarlas automáticamente al expirar.

•        **RF-07. Control de concurrencia (doble venta):** impedir que dos compradores adquieran la misma silla al mismo tiempo, incluso si sus solicitudes llegan a servicios o instancias distintas de la API.

•        **RF-08. Gestión de ventas y pagos:** crear órdenes, registrar pagos simulados y usar claves de idempotencia para que un pago repetido no genere dos órdenes.

•        **RF-09. Emisión y validación de boletas:** generar boletas únicas con código firmado; validarlas en el acceso, marcarlas como usadas y detectar y registrar intentos de clonación o reutilización.

•        **RF-10. Gestión de aumento de inventario:** registrar lotes adicionales (preventa, ampliación, nueva sección o nueva función); cada lote genera una factura al organizador y actualiza automáticamente el inventario.

•        **RF-11. Gestión de devoluciones:** solicitar, aprobar o rechazar devoluciones; reembolsar o cambiar de función; liberar las sillas devueltas y anular la boleta.

•        **RF-12. Alertas:** identificar reservas próximas a vencer, eventos con baja venta cercanos a su fecha e intentos de uso de boletas duplicadas.

•        **RF-13. Reportes:** generar los reportes definidos en la sección 10, incluyendo perfil de compradores por edad y por tipo de evento, sillas más vendidas y asistencia real al evento.

## **Requerimientos no funcionales**

•        Consistencia: cero doble venta de sillas bajo concurrencia.

•        Rendimiento: consultas de disponibilidad en menos de 200 ms usando Redis.

•        Seguridad: contraseñas con hash, autenticación con token, control de acceso por rol y código de boleta firmado.

•        Documentación automática de la API con OpenAPI (Swagger) y despliegue con Docker Compose.

# **5\. Modelado genérico del espacio físico**

Para no modificar el modelo cada vez que se registra un recinto distinto, el espacio físico se describe con una estructura única y flexible: un recinto contiene secciones, y cada sección declara cómo se vende. Así, el mismo código sirve para un teatro con sillas numeradas, un estadio con tribunas y zona general, o una sala de comedia con mesas.

| Tipo de sección | Unidad de venta | Ejemplo | Cómo se controla |
| :---- | :---- | :---- | :---- |
| numerada | Silla (sección, fila, número) | Platea de un teatro, tribuna numerada de un estadio | Bloqueo por silla en Redis (SET NX con TTL) y restricción única en MongoDB |
| mesa | Mesa con capacidad de personas | Sala de comedia, bar con mesas | Bloqueo por mesa; se vende la mesa completa o por puesto |
| general | Cupo sin silla asignada | Zona general de un concierto o de un coliseo | Contador atómico en Redis (DECRBY) |

 

•        **Identificador de silla:** se forma con sección, fila y número (por ejemplo, PLATEA-A-12), lo que permite reportes por sección y fila.

•        **Precio por sección:** cada función define el precio de cada sección, sin importar el recinto.

•        **Sin un documento por silla:** el recinto guarda solo la distribución; las sillas vendidas quedan registradas en las boletas, y la disponibilidad se obtiene restando las vendidas y las bloqueadas.

## **5.1 Ejemplo de documento de la colección recintos**

{  
  "\_id": "rec\_03",  
  "nombre": "Teatro Municipal",  
  "tipo": "teatro",  
  "ciudad": "Cali",  
  "secciones": \[  
	{ "codigo": "PLATEA", "tipo": "numerada",  
      "filas": \[ { "fila": "A", "sillas": 20 }, { "fila": "B", "sillas": 22 } \] },  
	{ "codigo": "BALCON", "tipo": "numerada",  
      "filas": \[ { "fila": "A", "sillas": 14 } \] },  
	{ "codigo": "GENERAL", "tipo": "general", "capacidad": 300 }  
  \]  
}  
 

## **5.2 Ejemplo de documento de la colección eventos**

{  
  "\_id": "evt\_001",  
  "nombre": "Noche de Comedia en Vivo",  
  "categoria": "comedia",  
  "organizadorId": "org\_010",  
  "estado": "publicado",  
  "restriccionEdad": 18,  
  "atributos": { "artistas": \["Artista A", "Artista B"\], "duracionMin": 120 },  
  "funciones": \[  
	{ "funcionId": "fn\_01", "fechaHora": "2027-01-23T20:00:00-05:00",  
      "recintoId": "rec\_03", "estado": "abierta",  
      "precios": { "PLATEA": 180000, "BALCON": 120000, "GENERAL": 70000 } }  
  \]  
}  
 

# **6\. Diseño de MongoDB**

La base de datos estará organizada en las siguientes colecciones:

| Colección | Contenido |
| :---- | :---- |
| usuarios | Datos del usuario, fecha de nacimiento, rol y credenciales con hash. |
| organizadores | Razón social, NIT, contacto, comisión y política de devolución. |
| recintos | Recinto con su distribución genérica (secciones, filas, mesas y zonas generales) embebida. |
| eventos | Evento, categoría, atributos variables, restricción de edad y funciones embebidas con precio por sección. |
| ordenes | Compras: comprador, función, sillas, valores, estado, clave de idempotencia y edad del comprador al momento de la compra. |
| boletas | Una por silla o cupo: código firmado, silla, estado (válida, usada, devuelta, anulada) y fecha de uso. |
| validaciones | Historial de escaneos en el acceso (ingresos exitosos y rechazados) con puerta y hora, incluyendo intentos de reutilización o clonación. |
| lotes | Aumentos de inventario (preventa, ampliación, nueva sección o función). |
| facturas | Facturas generadas al organizador por cada lote. |
| devoluciones | Solicitudes de devolución, monto, tipo (reembolso o cambio) y estado. |

 

Se utilizarán documentos embebidos cuando los datos se consulten conjuntamente (secciones dentro del recinto, funciones dentro del evento, ítems dentro de la orden) y referencias entre colecciones cuando los datos crecen sin límite (boletas, órdenes, validaciones).

## **6.1 Índices**

•        **boletas:** índice único parcial sobre (funcionId, silla) para boletas activas, de modo que la base de datos rechace una segunda boleta activa para la misma silla aunque falle el bloqueo en Redis; índice único sobre el código de boleta.

•        usuarios: correo único.

•        eventos: (estado, categoría, funciones.fechaHora).

•        ordenes: (compradorId, fechaCreacion), (funcionId, estado) y clave de idempotencia única.

•        validaciones: (boletaId, fecha).

Decisión de diseño: al crear la orden se guarda la edad del comprador (o su rango de edad) y la categoría del evento dentro de la orden. Así, los reportes por edad y por tipo de evento no necesitan combinar colecciones en cada consulta.

# **7\. Uso de Redis**

Redis se utilizará para toda la información temporal y para apoyar el control de concurrencia. MongoDB sigue siendo la fuente principal de información persistente.

| Clave | Tipo | TTL | Uso |
| :---- | :---- | :---- | :---- |
| lock:silla:{funcionId}:{silla} | String (SET NX) | 10 min | Bloqueo temporal de una silla; el valor es el identificador de la reserva |
| reserva:{reservaId} | Hash | 10 min | Datos de la reserva: usuario, sillas y total |
| cupo:{funcionId}:{seccion} | Contador | Sin TTL | Cupos disponibles de zonas generales (DECRBY atómico) |
| ocupadas:{funcionId} | Set | Hasta la función | Sillas vendidas, para responder la disponibilidad sin consultar MongoDB |
| idem:{llave} | String | 24 h | Clave de idempotencia para pagos y compras repetidas |
| lock:validacion:{boletaId} | String (SET NX) | 5 s | Evita que dos escaneos simultáneos validen la misma boleta |
| sesion:{token} | Hash | 30 min | Sesión del usuario |
| cache:evento:{id}, cache:reporte:{hash} | String (JSON) | 2 a 5 min | Caché de eventos y reportes frecuentes, con invalidación al cambiar los datos |
| ranking:eventos:vistas | Sorted Set | Sin TTL | Ranking de eventos más consultados |
| ratelimit:{ip}:{ruta} | Contador | 1 min | Límite de solicitudes por usuario o IP |

# **8\. Control de concurrencia y validación de boletas**

## **8.1 Evitar que dos personas compren la misma silla**

Se usan dos barreras independientes. La primera, en Redis, es rápida y evita casi todos los conflictos; la segunda, en MongoDB, es la garantía final.

1\.     El comprador elige una o varias sillas de una función.

2\.     La API ejecuta en Redis un script atómico (Lua) que verifica que ninguna de las sillas esté vendida ni bloqueada y, si todas están libres, las bloquea con TTL de 10 minutos. Si alguna no está libre, no se bloquea ninguna (todo o nada).

3\.     Como el bloqueo vive en Redis y no en la memoria de la aplicación, funciona igual si las solicitudes llegan a dos servicios o instancias distintas de la API.

4\.     El comprador paga antes de que expire el bloqueo; el pago usa una clave de idempotencia, por lo que un reintento no genera una segunda orden.

5\.     Al confirmar el pago se crean las boletas. El índice único parcial de MongoDB rechaza cualquier boleta activa duplicada para la misma silla, incluso si algo fallara en Redis.

6\.     Si el tiempo expira o el usuario cancela, los bloqueos se eliminan y las sillas quedan disponibles.

## **8.2 Evitar la clonación de boletas**

•        **Código único y firmado:** cada boleta tiene un identificador aleatorio y una firma (HMAC con una clave secreta del servidor) incluidos en el código QR; un código inventado o alterado no pasa la verificación de la firma.

•        **Un solo uso:** al validar, la API cambia el estado de “válida” a “usada” con una única operación atómica condicionada al estado actual (findOneAndUpdate); solo una de las validaciones simultáneas puede tener éxito.

•        **Detección de copias:** si se presenta una boleta que ya está usada, devuelta o anulada, se rechaza el ingreso y se registra el intento (hora, puerta y validador) en la colección validaciones.

•        **Validaciones simultáneas:** un bloqueo corto en Redis por boleta evita que dos escaneos al mismo tiempo la den por válida.

•        **Estados que invalidan:** devolver o anular una boleta la deja inutilizable de inmediato, aunque alguien conserve una copia del QR.

# **9\. Endpoints principales de la API REST**

| Módulo | Endpoints |
| :---- | :---- |
| Autenticación | POST /api/v1/auth/register · POST /api/v1/auth/login · POST /api/v1/auth/logout |
| Recintos | POST /api/v1/venues · GET /api/v1/venues · GET /api/v1/venues/{id} |
| Organizadores | POST /api/v1/organizers · GET /api/v1/organizers · GET /api/v1/organizers/{id}/events |
| Eventos y funciones | POST /api/v1/events · GET /api/v1/events · GET /api/v1/events/{id} · POST /api/v1/events/{id}/shows · PATCH /api/v1/events/{id}/cancel |
| Disponibilidad | GET /api/v1/shows/{id}/availability · GET /api/v1/shows/{id}/seats |
| Reservas | POST /api/v1/reservations · GET /api/v1/reservations/{id} · DELETE /api/v1/reservations/{id} |
| Órdenes y pagos | POST /api/v1/orders (confirmar pago, con clave de idempotencia) · GET /api/v1/orders/{id} · GET /api/v1/users/{id}/orders |
| Boletas | GET /api/v1/tickets/{id} · POST /api/v1/tickets/validate |
| Lotes y facturas | POST /api/v1/batches · GET /api/v1/invoices |
| Devoluciones | POST /api/v1/refunds · PATCH /api/v1/refunds/{id}/approve · PATCH /api/v1/refunds/{id}/reject |
| Reportes | GET /api/v1/reports/occupancy · /inventory-value · /sales · /organizers · /show-availability · /buyers-by-age · /sales-by-category · /top-seats · /revenue · /low-sales · /refunds · /fraud-attempts · /attendance |

# **10\. Reportes del sistema**

Los reportes se implementarán mediante agregaciones de MongoDB. Los reportes R-01 a R-05 equivalen a los del enunciado del proyecto; R-06 a R-08 corresponden a las sugerencias del profesor; R-09 a R-13 son adicionales.

| N.º | Reporte | Descripción | Técnica en MongoDB |
| :---- | :---- | :---- | :---- |
| R-01 | Ocupación por función y sección | Sillas y cupos vendidos, bloqueados y disponibles por función y sección | \$match, \$group, \$project |
| R-02 | Valor del inventario | Ingreso potencial: boletas disponibles × precio de la sección | \$unwind, \$multiply, \$group |
| R-03 | Boletas vendidas por rango de fechas | Cantidad e ingresos por evento y por día | \$match, \$group |
| R-04 | Organizadores y sus eventos | Organizadores con sus eventos, precios por sección y comisión | \$lookup, \$project |
| R-05 | Disponibilidad de un evento por función | Cupos de un mismo evento en las distintas funciones, recintos y ciudades | \$match, \$unwind, \$lookup |
| R-06 | Compradores por rango de edad | Cantidad de compradores e ingresos por rango de edad (menores de 18, 18 a 25, 26 a 35, 36 a 50, más de 50), filtrable por evento o categoría | \$match, \$bucket, \$group |
| R-07 | Ventas por tipo de evento | Boletas e ingresos por categoría (música, comedia, teatro, etc.) y cruce con la edad del comprador | \$group, \$facet |
| R-08 | Sillas más vendidas | Sillas, filas y secciones más vendidas por recinto, función o categoría | \$match, \$group, \$sort, \$limit |
| R-09 | Ingresos por organizador | Ventas brutas, devoluciones, ingreso neto y comisión | \$group, \$lookup |
| R-10 | Eventos próximos con baja venta | Eventos a menos de 15 días con ocupación menor al 30 % | \$match, \$addFields, \$sort |
| R-11 | Devoluciones | Cantidad y monto por rango de fechas, motivo y evento | \$match, \$group |
| R-12 | Intentos de fraude | Boletas con intentos de reutilización o clonación, por evento y puerta | \$match, \$group |
| R-13 | Asistencia (personas que ingresaron) | Personas que entraron por función, puerta y franja horaria; boletas vendidas vs. boletas usadas y porcentaje de inasistencia | \$match, \$group, \$lookup, \$project |

# **11\. Arquitectura**

La solución estará organizada en las siguientes capas:

•        **API REST:** FastAPI y validaciones con Pydantic.

•        **Servicios:** lógica de negocio (reservas, ventas, validación de boletas, devoluciones).

•        **Repositorios:** acceso y consultas a MongoDB.

•        **Redis:** bloqueos, caché, idempotencia y datos con expiración.

•        **Pruebas:** pytest para pruebas funcionales y de integración, y k6 para pruebas de rendimiento y concurrencia.

Se utilizará Docker Compose para levantar la API (con dos instancias para probar la concurrencia entre servicios), MongoDB y Redis.

# **12\. Plan de pruebas**

Se realizarán pruebas para verificar:

•        El registro de recintos de distintos tipos (teatro, estadio, sala de comedia) sin cambiar el código.

•        La creación y expiración de reservas y la liberación de sillas.

•        Concurrencia: muchas solicitudes simultáneas sobre la misma silla, enviadas a dos instancias de la API, deben producir una sola compra exitosa.

•        Idempotencia: repetir un mismo pago no debe crear una segunda orden.

•        Validación de boletas: una boleta válida entra una sola vez; un código alterado, repetido, devuelto o anulado es rechazado y queda registrado.

•        Validaciones simultáneas de la misma boleta: solo una tiene éxito.

•        La exactitud de los reportes, incluyendo edades, categorías, sillas más vendidas y asistencia.

•        El funcionamiento de Redis y la invalidación de la caché.

•        La consistencia de los datos ante errores.

También se compararán los tiempos de respuesta, las solicitudes por segundo y el porcentaje de errores: con y sin Redis, y frente a un modelo relacional equivalente en PostgreSQL, usando el mismo conjunto de datos.

# **13\. Plan de trabajo**

| Periodo | Actividad |
| :---- | :---- |
| 20 al 26 de octubre | Definición de requisitos, diseño de colecciones y del modelo genérico de recintos, configuración del proyecto (Docker y repositorio) |
| 27 de octubre al 2 de noviembre | CRUD de usuarios, organizadores, recintos y eventos |
| 3 al 9 de noviembre | Reservas de sillas, ventas, boletas, integración de Redis y control de concurrencia |
| 10 al 16 de noviembre | Validación y anti-clonación de boletas, devoluciones, lotes y facturas |
| 17 al 23 de noviembre | Implementación de los reportes |
| 24 al 30 de noviembre | Simulador de datos de prueba y desarrollo opcional del frontend |
| 1 al 7 de diciembre | Pruebas de concurrencia y de rendimiento (con y sin Redis, y frente a PostgreSQL) |
| 8 al 14 de diciembre | Integración, corrección de errores y pruebas generales |
| 15 al 21 de diciembre | Documentación y preparación de la presentación |
| 22 de diciembre | Entrega y presentación final |

# **14\. Distribución del trabajo en grupo**

El trabajo se distribuirá entre los cinco integrantes de la siguiente manera:

| Integrante | Responsabilidad |
| :---- | :---- |
| Integrante 1 | Diseño de MongoDB, modelo genérico de recintos, índices y simulador de datos de prueba |
| Integrante 2 | Usuarios, organizadores, recintos, eventos y funciones; lotes y facturas |
| Integrante 3 | Reservas, órdenes, pagos con idempotencia y devoluciones |
| Integrante 4 | Integración de Redis, control de concurrencia, emisión y validación de boletas (anti-clonación) |
| Integrante 5 | Reportes, pruebas de rendimiento y documentación |

 

Todos los integrantes participarán en la integración de los componentes, la validación del sistema, el frontend opcional y la preparación de la entrega final.

# **15\. Puntos adicionales**

•        Comparar el rendimiento con y sin Redis, y frente a un modelo relacional equivalente en PostgreSQL.

•        Implementar un frontend en React con mapa interactivo de sillas, carrito con temporizador, sección “Mis boletas” con QR y panel de reportes.

•        Crear un simulador de compradores concurrentes para generar datos de prueba y demostrar en vivo que no hay doble venta.

•        Incorporar gráficas de ventas por categoría, edad de los compradores y sillas más vendidas.

•        Originalidad: el sistema se centra en un recurso que se vende una sola vez y expira (la silla de una función), con modelado genérico de recintos.

## **15.1 Cumplimiento de los criterios de calificación**

| Criterio | Peso | Cómo se cumple |
| :---- | :---- | :---- |
| Integración e implementación del backend | 50 % | API REST con los requerimientos funcionales RF-01 a RF-13 |
| Generación de reportes | 30 % | Reportes R-01 a R-13 con aggregation pipelines |
| Redis para información temporal | 20 % | Bloqueos de sillas con TTL, cupos, idempotencia, sesiones, caché y ranking |
| Puntos adicionales | Extra | Pruebas de rendimiento, frontend y originalidad |

# **16\. Resultado esperado**

Obtener una API REST funcional que permita administrar eventos en recintos de cualquier tipo, gestionar la venta de sillas sin doble venta, emitir y validar boletas que no puedan clonarse, registrar pagos y devoluciones, y generar reportes sobre ventas, aforo, perfil de los compradores y sillas más vendidas.

La solución demostrará el uso de MongoDB para modelar información flexible y analizarla con agregaciones, y de Redis para gestionar bloqueos, idempotencia e información temporal. Las decisiones técnicas estarán respaldadas por pruebas funcionales, de concurrencia y experimentos de rendimiento.

