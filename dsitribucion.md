DISTRIBUCION EQUITATIVA DE TAREAS \- PROYECTO TICKETFLOW  
\========================================================

Objetivo del archivo  
\--------------------  
Organizar el trabajo de cuatro integrantes de forma equilibrada y dejar  
evidencia verificable de cada requisito descrito en el documento del proyecto.  
Cada integrante debe entregar codigo/documentacion, pruebas ejecutables y  
capturas de pantalla. Ninguna captura debe mostrar datos sensibles, claves  
secretas ni contrasenas.

Integrantes  
\-----------  
INTEGRANTE 1 \- Backend de recintos, eventos y autenticacion  
INTEGRANTE 2 \- Reservas, concurrencia, Redis y disponibilidad  
INTEGRANTE 3 \- Ventas, boletas, devoluciones y validacion de acceso  
INTEGRANTE 4 \- Reportes, frontend, rendimiento y documentacion final

Regla de trabajo comun  
\----------------------  
1\. Trabajar en una rama propia y hacer commits pequenos, descriptivos y  
   relacionados con una sola funcionalidad.  
2\. Toda funcionalidad debe incluir validacion de entradas, manejo explicito de  
   errores y una prueba positiva y una negativa.  
3\. Todas las personas deben ejecutar el sistema con Docker Compose y verificar  
   que la API funciona con MongoDB y Redis.  
4\. Las capturas deben incluir la URL o endpoint, el cuerpo de la solicitud, la  
   respuesta, el codigo HTTP y, cuando corresponda, la evidencia en MongoDB,  
   Redis o el reporte de pruebas.  
5\. Usar datos de demostracion consistentes: al menos un teatro con sillas  
   numeradas, un estadio con tribunas y zona general, y una sala de comedia  
   con mesas.  
6\. Antes de entregar, cada integrante debe registrar sus pruebas en una tabla  
   con: requisito, escenario, resultado esperado, resultado obtenido, fecha y  
   nombre del archivo de evidencia.

INTEGRANTE 1 \- RECINTOS, EVENTOS, USUARIOS Y AUTENTICACION  
\============================================================

A. Implementacion  
\-----------------  
1\. Crear el modelo generico de recintos (RF-01):  
   \- tipos numerada, mesa y general;  
   \- secciones, filas, sillas, mesas, capacidad y zonas;  
   \- identificadores de silla compuestos por seccion, fila y numero;  
   \- precios por seccion sin acoplar el codigo a un tipo de recinto.  
2\. Implementar CRUD de recintos:  
   \- POST /api/v1/venues  
   \- GET /api/v1/venues  
   \- GET /api/v1/venues/{id}  
3\. Implementar organizadores (RF-03):  
   razon social, NIT, contacto, comision y politica de devolucion.  
4\. Implementar usuarios y sesiones (RF-04):  
   \- roles comprador, organizador, administrador y validador;  
   \- fecha de nacimiento y credenciales protegidas con hash;  
   \- registro, login y logout;  
   \- sesiones con expiracion en Redis.  
5\. Implementar eventos y funciones (RF-02):  
   categoria, atributos, restriccion de edad, organizador, recinto, ciudad,  
   fecha/hora, estado y precios por seccion.  
6\. Crear indices de MongoDB para usuarios, eventos y consultas frecuentes.  
7\. Configurar autenticacion con token y autorizacion por rol.

B. Pruebas y evidencias  
\-----------------------  
1\. Capturar tres recintos distintos creados sin cambiar el esquema ni el  
   codigo.  
2\. Capturar un evento con varias funciones, ciudades, fechas y precios.  
3\. Capturar registro, login, logout y sesion almacenada en Redis.  
4\. Capturar un intento sin permisos y otro con rol autorizado.  
5\. Capturar en MongoDB los documentos de usuarios, recintos y eventos, sin  
   exponer contrasenas reales.  
6\. Probar datos invalidos: fecha incorrecta, edad negativa, seccion  
   inexistente y precio no valido.

C. Entregables  
\--------------  
\- Modelos, esquemas, repositorios y rutas de recintos, usuarios, organizadores  
  y eventos.  
\- Indices y script de datos iniciales.  
\- Pruebas automatizadas de los endpoints anteriores.  
\- Capturas E01 a E07 y una breve explicacion de cada una.

INTEGRANTE 2 \- DISPONIBILIDAD, RESERVAS, REDIS Y CONCURRENCIA  
\==============================================================

A. Implementacion  
\-----------------  
1\. Implementar consulta de disponibilidad (RF-05):  
   \- GET /api/v1/shows/{id}/availability  
   \- GET /api/v1/shows/{id}/seats  
   \- distinguir sillas libres, reservadas, vendidas y zonas generales.  
2\. Implementar reservas temporales (RF-06):  
   \- POST /api/v1/reservations  
   \- GET /api/v1/reservations/{id}  
   \- DELETE /api/v1/reservations/{id}  
   \- TTL de 10 minutos y liberacion automatica al expirar.  
3\. Implementar el control de doble venta (RF-07):  
   \- bloqueo atomico en Redis mediante SET NX con TTL;  
   \- comportamiento correcto para dos instancias simultaneas de la API;  
   \- liberacion por pago, cancelacion o expiracion.  
4\. Implementar cupos de zonas generales con contador atomico DECRBY y  
   restauracion segura cuando corresponda.  
5\. Configurar las claves Redis documentadas:  
   lock:silla:{funcionId}:{silla}, reserva:{reservaId},  
   cupo:{funcionId}:{seccion}, ocupadas:{funcionId},  
   sesion:{token}, ratelimit:{ip}:{ruta}.  
6\. Aplicar limite de solicitudes por usuario o IP y medir disponibilidad en  
   menos de 200 ms usando Redis.  
7\. Documentar por que Redis es barrera rapida y MongoDB es la garantia final.

B. Pruebas y evidencias  
\-----------------------  
1\. Capturar consulta de disponibilidad antes y despues de una reserva.  
2\. Capturar la clave Redis, su TTL y su eliminacion al expirar o cancelar.  
3\. Ejecutar muchas solicitudes simultaneas desde dos instancias y capturar que  
   solo una obtiene la silla.  
4\. Capturar una reserva de zona general y verificar el contador atomico.  
5\. Probar que una silla reservada no aparece como libre y que vuelve a estar  
   disponible despues del TTL.  
6\. Medir y capturar tiempos con Redis, sin Redis y frente al modelo relacional  
   equivalente (PostgreSQL), indicando metodologia y numero de solicitudes.  
7\. Probar el limite de solicitudes y una solicitud rechazada por exceso.

C. Entregables  
\--------------  
\- Servicio de disponibilidad y reservas.  
\- Scripts atomicos de Redis y manejo de TTL.  
\- Pruebas de integracion y de concurrencia con k6.  
\- Capturas E08 a E14, incluyendo evidencia de las dos instancias.

INTEGRANTE 3 \- ORDENES, PAGOS SIMULADOS, BOLETAS Y DEVOLUCIONES  
\================================================================

A. Implementacion  
\-----------------  
1\. Implementar ordenes y pagos simulados (RF-08):  
   \- POST /api/v1/orders (confirmar pago con clave de idempotencia);  
   \- GET /api/v1/orders/{id};  
   \- GET /api/v1/users/{id}/orders;  
   \- impedir que un reintento genere una segunda orden.  
2\. Implementar emision de boletas (RF-09):  
   \- una boleta unica por silla o cupo;  
   \- codigo aleatorio y firma HMAC;  
   \- codigo QR y estado valida, usada, devuelta o anulada;  
   \- codigo unico parcial sobre funcionId y silla.  
3\. Implementar validacion de acceso:  
   \- POST /api/v1/tickets/validate;  
   \- cambio atomico de valida a usada;  
   \- registro de cada intento en validaciones con puerta, hora y validador;  
   \- rechazo de codigo alterado, repetido, devuelto o anulado.  
4\. Implementar deteccion de clonacion y bloqueo corto  
   lock:validacion:{boletaId} en Redis.  
5\. Implementar lotes adicionales y facturas (RF-10):  
   \- POST /api/v1/batches;  
   \- GET /api/v1/invoices;  
   \- lote preventa, ampliacion, nueva seccion o nueva funcion;  
   \- factura automatica al organizador.  
6\. Implementar devoluciones (RF-11):  
   \- POST /api/v1/refunds;  
   \- PATCH /api/v1/refunds/{id}/approve;  
   \- PATCH /api/v1/refunds/{id}/reject;  
   \- cambio de funcion, reembolso, liberacion de silla y anulacion de boleta.  
7\. Crear indices y validaciones de ordenes, boletas y validaciones.

B. Pruebas y evidencias  
\-----------------------  
1\. Capturar pago exitoso con clave de idempotencia y repetir exactamente la  
   solicitud para demostrar que no duplica la orden.  
2\. Capturar una boleta emitida, su codigo QR y su firma (usando datos de  
   demostracion).  
3\. Capturar validacion exitosa y el documento actualizado a estado usada.  
4\. Capturar segundo intento de uso, QR alterado, boleta devuelta y boleta  
   anulada, todos rechazados con su codigo HTTP.  
5\. Ejecutar validaciones simultaneas y capturar que solo una es exitosa.  
6\. Capturar un lote adicional, la factura generada y el inventario actualizado.  
7\. Capturar solicitud aprobada y rechazada de devolucion, verificando la  
   liberacion de la silla y la anulacion de la boleta.

C. Entregables  
\--------------  
\- Servicios de ordenes, pagos, boletas, validacion, lotes y devoluciones.  
\- Pruebas unitarias, de integracion y de idempotencia.  
\- Capturas E15 a E24 y explicacion de los estados observados.

INTEGRANTE 4 \- REPORTES, FRONTEND, RENDIMIENTO Y DOCUMENTACION  
\===============================================================

A. Implementacion  
\-----------------  
1\. Implementar reportes R-01 a R-13 con agregaciones MongoDB:  
   R-01 ocupacion por funcion y seccion; R-02 valor del inventario;  
   R-03 boletas vendidas por rango de fechas; R-04 organizadores y eventos;  
   R-05 disponibilidad por funcion; R-06 compradores por rango de edad;  
   R-07 ventas por tipo de evento; R-08 sillas mas vendidas; R-09 ingresos por  
   organizador; R-10 eventos proximos con baja venta; R-11 devoluciones;  
   R-12 intentos de fraude; R-13 asistencia.  
2\. Exponer:  
   GET /api/v1/reports/occupancy, /inventory-value, /sales,  
   /organizers, /show-availability, /buyers-by-age, /top-seats,  
   /revenue, /low-sales, /refunds, /fraud-attempts y /attendance.  
3\. Implementar cache Redis para eventos y reportes frecuentes con TTL de 2 a 5  
   minutos, invalidandola cuando cambien las ventas.  
4\. Crear frontend React:  
   \- mapa interactivo de sillas y zonas;  
   \- carrito con temporizador de reserva;  
   \- seccion Mis boletas con QR;  
   \- panel de reportes y estados de reserva.  
5\. Preparar Docker Compose con API, dos instancias de API, MongoDB, Redis,  
   frontend y, para la comparacion, PostgreSQL.  
6\. Integrar Swagger/OpenAPI y revisar que todos los endpoints tengan  
   descripciones, esquemas, respuestas y errores.  
7\. Consolidar la documentacion: arquitectura por capas, decisiones NoSQL,  
   indices, Redis, seguridad, instalacion y guia de demostracion.

B. Pruebas y evidencias  
\-----------------------  
1\. Capturar cada reporte con datos suficientes para comprobar sus totales y  
   filtros. Usar una captura por cada grupo de reportes si la pantalla es  
   legible, sin ocultar la respuesta completa.  
2\. Capturar cache hit, cache miss e invalidacion posterior a una venta.  
3\. Capturar el mapa, carrito con contador, Mis boletas con QR y panel de  
   reportes.  
4\. Capturar Swagger con los modulos principales y una solicitud ejecutada.  
5\. Capturar Docker Compose con todos los servicios saludables.  
6\. Ejecutar pruebas de exactitud de reportes, errores de datos, rendimiento  
   con y sin Redis y comparacion con PostgreSQL.  
7\. Elaborar la matriz final de trazabilidad requisito \-\> endpoint \-\> prueba  
   \-\> captura \-\> responsable.

C. Entregables  
\--------------  
\- Modulo de reportes y cache.  
\- Frontend funcional.  
\- Docker Compose, guia de ejecucion y documentacion final.  
\- Capturas E25 a E36, matriz de trazabilidad y consolidacion de evidencias.

ACTIVIDADES COMPARTIDAS Y REVISION CRUZADA  
\==========================================

Fase 1 \- Preparacion (los cuatro)  
\----------------------------------  
1\. Leer las secciones 1 a 16 del documento y convertir cada requisito en un  
   caso de prueba.  
2\. Definir nombres de colecciones, contratos JSON, codigos HTTP y datos de  
   demostracion antes de programar.  
3\. Crear el tablero de tareas y acordar la estrategia de ramas.

Fase 2 \- Integracion (responsables rotativos)  
\---------------------------------------------  
1\. Integrante 1 revisa modelos, autenticacion y permisos de los integrantes 2,  
   3 y 4\.  
2\. Integrante 2 revisa bloqueos, TTL, concurrencia y rendimiento.  
3\. Integrante 3 revisa estados, idempotencia, firma y seguridad de boletas.  
4\. Integrante 4 revisa reportes, frontend, documentacion y calidad de capturas.  
5\. Cada persona debe revisar y aprobar al menos una funcionalidad de otra  
   persona; no se acepta auto-revision como unica validacion.

Fase 3 \- Pruebas finales (los cuatro)  
\-------------------------------------  
1\. Ejecutar: registro de recinto, creacion de evento, disponibilidad,  
   reserva, pago, emision, validacion, devolucion y reporte.  
2\. Ejecutar concurrencia con dos instancias y comprobar cero doble venta.  
3\. Verificar que una boleta no pueda clonarse ni reutilizarse.  
4\. Verificar que Redis tenga TTL, idempotencia, sesiones, cache y ranking.  
5\. Verificar los requisitos no funcionales:  
   consistencia, rendimiento menor a 200 ms con Redis, hash, token,  
   autorizacion, Swagger y despliegue con Docker Compose.  
6\. Revisar que cada evidencia tenga un nombre unico y una entrada en la  
   matriz de trazabilidad.

LISTA DE CAPTURAS MINIMAS PARA LA ENTREGA  
\=========================================

E01-E07  Recintos, eventos, usuarios, roles, sesiones y autorizacion.  
E08-E14  Disponibilidad, reservas, TTL, Redis, concurrencia y rendimiento.  
E15-E24  Ordenes, idempotencia, boletas, QR, validacion, lotes y devoluciones.  
E25-E31  Reportes R-01 a R-13 con filtros y resultados legibles.  
E32-E34  Frontend: mapa, carrito, Mis boletas y panel de reportes.  
E35      Swagger/OpenAPI y ejecucion de endpoints.  
E36      Docker Compose, servicios saludables y evidencia de despliegue.  
E37      Comparacion con Redis, sin Redis y PostgreSQL.  
E38      Resumen de pruebas automatizadas y matriz de trazabilidad.

Convencion sugerida de nombres:  
E01\_recinto\_teatro.png, E02\_recinto\_estadio.png,  
E08\_reserva\_ttl\_redis.png, E15\_pago\_idempotente.png,  
E25\_reporte\_occupancy.png, E35\_swagger.png.

CRITERIO DE TERMINACION  
\=======================

Una tarea solo se marca como terminada cuando:  
1\. El codigo esta integrado y funciona desde Docker Compose.  
2\. Existe al menos una prueba automatizada y una prueba manual documentada.  
3\. Se verificaron los casos exitosos, invalidos, no autorizados y  
   concurrentes que correspondan.  
4\. La captura muestra claramente la evidencia y tiene una descripcion.  
5\. La matriz de trazabilidad relaciona la tarea con RF, RNF, endpoint, prueba  
   y captura.  
6\. Otro integrante reviso el resultado y dejo su aprobacion.

Distribucion equilibrada:  
Cada integrante recibe un modulo funcional completo, un bloque de pruebas  
tecnicas, un bloque de evidencias y una responsabilidad de revision. La  
integracion final es compartida, por lo que la calidad de la entrega no recae  
exclusivamente en una sola persona.  
