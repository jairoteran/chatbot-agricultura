# Resumen de avance - 2026-05-11

Hoy se dejo lista la base principal del sistema en Google Cloud para que ya no dependa solo del entorno local.

## Lo que ya esta hecho

- Ya tenemos la base de datos en la nube funcionando.
- Ya tenemos el almacenamiento en la nube creado y operativo.
- Ya tenemos el backend preparado para trabajar con esos servicios.
- Ya tenemos el proceso de reindexado funcionando tanto en local como en la nube.
- Ya tenemos la imagen del backend construida y publicada.
- Ya tenemos creado y probado el job en la nube para ejecutar el reindexado.
- Ya comprobamos que el sistema guarda, consulta y actualiza informacion real en Google Cloud.
- Ya organizamos la documentacion y las evidencias del avance para presentacion, resultados y anexos.

## Explicado de forma sencilla

### Firestore

Firestore es la base de datos en la nube que se eligio para guardar la informacion del sistema.

En este proyecto se esta usando para guardar:

- los documentos registrados
- el estado general del sistema
- el historial de reindexados

En otras palabras, Firestore permite que el sistema recuerde que documentos tiene, en que estado estan y que procesos se ejecutaron.

### Cloud Storage

Cloud Storage es el almacenamiento en la nube.

En este proyecto se usa para guardar los archivos importantes del sistema, especialmente el indice que luego utiliza el backend para responder consultas.

Esto permite que la informacion deje de depender solo de carpetas locales de la computadora.

### Backend

El backend es la parte del sistema que se encarga de procesar la informacion y conectarse con los servicios de Google Cloud.

Durante este avance ya quedo preparado para:

- leer y escribir informacion en Firestore
- usar almacenamiento en la nube
- ejecutar reindexados de forma controlada

### Reindexado

El reindexado es el proceso que reorganiza la informacion de los documentos para que luego el sistema pueda consultarla mejor.

Ese proceso ya funciona:

- en local
- y tambien en la nube

### Job en la nube

Tambien se creo y se probo un job en la nube.

Un job es una tarea automatizada que se ejecuta cuando se necesita. En este caso, sirve para lanzar el reindexado sin depender de que todo se haga manualmente desde la computadora local.


## Que sigue despues

- desplegar la API completa en la nube
- mover los documentos completamente al almacenamiento cloud
- seguir cerrando la arquitectura final del sistema
