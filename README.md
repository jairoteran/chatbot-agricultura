# PDF Chat App

Proyecto web con dos carpetas:

- `backend`: API en FastAPI + LlamaIndex para cargar PDFs, construir un indice vectorial y responder preguntas.
- `frontend`: interfaz web en React con una experiencia de chat enfocada en documentos.

El objetivo del proyecto es que el asistente no solo recupere texto desde los documentos, sino que tambien lo analice y lo explique con lenguaje claro, como un chatbot conversacional.

## Listo para Vercel

El repositorio ya incluye configuracion para desplegarse en `Vercel` con:

- frontend `Vite` construido desde `frontend/`
- backend `FastAPI` expuesto como funcion Python desde `api/index.py`
- `vercel.json` con `buildCommand`, `outputDirectory` y exclusions para reducir el bundle
- `requirements.txt` en la raiz para que Vercel instale las dependencias de Python
- `.python-version` fijado en `3.12`

Importante para produccion:

- En Vercel el backend se ejecuta sobre un sistema de archivos efimero.
- Por eso, este proyecto asume que `backend/storage/` ya va incluido y actualizado en el repositorio.
- El boton `Reindexar PDFs` queda deshabilitado en despliegues Vercel salvo que habilites `ALLOW_RUNTIME_REINDEX=true`.
- La recomendacion es reindexar localmente, confirmar que `backend/storage/` quedo actualizado y luego hacer deploy.

## Estructura

```text
backend/
  app/
  data/
  storage/
frontend/
  src/
```

## Backend

### 1. Crear entorno virtual

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Configurar el modo conversacional con LLM

Si quieres que el asistente razone y redacte como un chatbot real, configura una clave de API en el backend.

### Opcion recomendada para pruebas gratis: Gemini

El backend ahora prioriza `Gemini` si encuentra `GEMINI_API_KEY`. Si no encuentra esa variable, intenta usar `OpenAI`. Si no encuentra ninguna, responde con el modo local basico.

El backend carga automaticamente variables desde `backend/.env`, y ese archivo ya esta ignorado por Git para no exponer claves.

```powershell
$env:GEMINI_API_KEY="tu_clave"
```

Opcionalmente puedes elegir el modelo:

```powershell
$env:GEMINI_MODEL="gemini-2.5-flash"
```

Segun la documentacion oficial de Google revisada el `28 de abril de 2026`, Gemini API ofrece un nivel `free` y un nivel `pay-as-you-go`, con cuotas y modelos que dependen del proyecto y del modelo usado.

### Opcion alternativa: OpenAI

```powershell
$env:OPENAI_API_KEY="tu_clave"
```

Opcionalmente puedes elegir el modelo:

```powershell
$env:OPENAI_MODEL="gpt-5.4-mini"
```

Si no defines ni `GEMINI_API_KEY` ni `OPENAI_API_KEY`, la aplicacion seguira respondiendo con un modo basico basado en recuperacion y sintesis local.

### 4. Agregar PDFs

Coloca tus archivos PDF dentro de `backend/data/`.

### 5. Iniciar el servidor

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Endpoints disponibles:

- `GET /health`: estado del backend, cantidad de archivos indexados y diagnostico.
- `POST /chat`: responde preguntas usando solo el contenido recuperado de los PDFs, pero sintetizando los hallazgos en un lenguaje mas claro en lugar de devolver citas literales como respuesta principal.
- `POST /reindex`: reconstruye el indice cuando agregas o cambias documentos.

Ejemplo de cuerpo JSON para `/chat`:

```json
{
  "question": "Que dice el documento sobre enfermedades del cultivo de papa?"
}
```

## Frontend

### 1. Instalar dependencias

```powershell
cd frontend
npm install
```

### 2. Configurar variables opcionales

Puedes crear `frontend/.env` a partir de `frontend/.env.example`, que ya esta incluido en el repo.

```env
VITE_API_URL=/api/chat
VITE_HEALTH_URL=/api/health
VITE_REINDEX_URL=/api/reindex
VITE_SUMMARY_URL=/api/summarize-document
```

### 3. Iniciar el frontend

```powershell
npm run dev
```

La aplicacion quedara disponible en `http://localhost:5173`.

Durante desarrollo, el frontend usa un proxy de Vite hacia `http://localhost:8000`, por lo que no deberias tener problemas de CORS si ambos servicios estan levantados.

## Despliegue en Vercel

### 1. Variables de entorno recomendadas

Configura en Vercel las variables necesarias para el proveedor que vayas a usar:

```text
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
```

o bien:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
```

Tambien conviene definir:

```text
CORS_ORIGINS=https://tu-dominio.vercel.app
```

Solo si quieres permitir reindexado en produccion:

```text
ALLOW_RUNTIME_REINDEX=true
```

### 2. Flujo recomendado antes de desplegar

1. Coloca o actualiza tus PDFs en `backend/data/`.
2. Ejecuta localmente el backend y usa `Reindexar PDFs` o reconstruye el indice.
3. Verifica que `backend/storage/` se actualizo correctamente.
4. Sube esos cambios al repositorio.
5. Despliega en Vercel.

### 3. Que esperar en produccion

- Las rutas del backend quedaran bajo `/api`, por ejemplo `/api/health` y `/api/chat`.
- El frontend consumira esas rutas automaticamente.
- Si `backend/storage/` no coincide con `backend/data/`, el despliegue puede iniciar en error porque no podra reconstruir el indice por defecto dentro de Vercel.

## Iniciar todo con un solo script

Despues de instalar dependencias en ambos servicios, puedes arrancar todo desde la raiz del proyecto:

```powershell
.\start-all.ps1
```

Eso abrira dos ventanas nuevas de PowerShell:

- una para el backend en `http://localhost:8000`
- otra para el frontend en `http://localhost:5173`

Si prefieres ejecutarlos en segundo plano dentro de la misma sesion:

```powershell
.\start-all.ps1 -NoNewWindows
```

## Mejoras incluidas

1. El backend detecta cambios en los PDFs y reutiliza el indice persistido cuando no hubo cambios.
2. El indice vectorial se persiste en `backend/storage/` y puede reconstruirse manualmente.
3. El backend expone estado de salud y reindexacion manual.
4. El frontend muestra el estado del backend, las fuentes usadas y un boton de reindexado.
5. Si no hay evidencia suficiente, el sistema responde claramente que no encontro informacion suficiente.
6. Las respuestas del chat priorizan sintesis y analisis de los fragmentos recuperados antes que copiar texto del documento.
7. Si se configura una API key de Gemini o OpenAI, el backend puede usar un modelo generativo para responder con continuidad conversacional y mejor razonamiento.

## Sobre el "entrenamiento"

Para este proyecto no hace falta entrenar un modelo con tus PDFs. Lo que si hace falta es una arquitectura que:

1. recupere los fragmentos mas relevantes del documento;
2. pase esa evidencia a un modelo que pueda razonar y redactar;
3. reformule la respuesta de forma entendible y conversacional.

Antes, el proyecto hacia bien el paso 1, pero el paso 2 y 3 eran muy limitados, por eso la salida se parecia demasiado al texto original. La version actual puede usar un modelo generativo para analizar la evidencia recuperada, mantener continuidad con el historial reciente y responder de forma mucho mas parecida a un chatbot real.

## ChatGPT Plus, API y costos

Tener `ChatGPT Plus` no incluye creditos para la API. Son productos separados:

- `ChatGPT Plus` sirve para usar ChatGPT desde la web o la app.
- La `API` se cobra aparte y es la que necesita este proyecto para responder desde el backend.

En otras palabras, aunque tengas Plus, para que este proyecto use un modelo generativo desde codigo necesitas una API key y facturacion de API.

## Opciones de proveedor

### 1. Google Gemini

Ventajas:

- es la opcion mas conveniente para probar sin pagar al inicio;
- el backend ya puede usarlo directamente;
- tiene free tier oficial segun el proyecto y el modelo.

Desventaja:

- las cuotas gratis tienen limites y pueden variar segun el modelo.

Modelo recomendado para empezar:

- `gemini-2.5-flash`

### 2. OpenAI

Ventajas:

- integracion directa con el backend actual;
- buena calidad para respuestas tipo chatbot;
- buen equilibrio entre costo y calidad con modelos mini.

Desventaja:

- no ofrece un free tier general de API para pruebas.

Modelo recomendado para este proyecto:

- `gpt-5.4-mini`

### 3. Anthropic / Claude

Ventajas:

- muy buena capacidad de redaccion y analisis;
- buena opcion si prefieres el estilo de Claude.

Desventajas:

- no es la opcion mas barata para este caso;
- no aparece un free tier general de API como opcion principal para pruebas.

Opciones razonables:

- `Claude Haiku 3.5` si buscas abaratar;
- `Claude Sonnet 4` si priorizas calidad por encima del costo.

## Cual conviene usar

Si el objetivo es subir el proyecto y dejarlo listo para mostrar:

- usa `Gemini` si quieres hacer pruebas gratis o con el menor gasto posible;
- usa `OpenAI` si quieres una alternativa estable con buena calidad y costo razonable;
- usa `Claude` si ya decidiste pagar y prefieres ese proveedor por estilo de respuesta.

## Opcion para pruebas

De las opciones evaluadas, la mas clara para pruebas es `Gemini`, porque su documentacion oficial indica que maneja un nivel `free` y un nivel `pay-as-you-go`, dependiendo del modelo.

En cambio:

- `OpenAI API` no incluye uso gratis general por tener ChatGPT Plus;
- `Claude API` no aparece como la opcion principal para pruebas gratuitas generales.

## Costos orientativos

Estos valores pueden cambiar, asi que conviene verificarlos antes de publicar o desplegar. Como referencia, para un proyecto RAG como este:

- `OpenAI mini` suele ser una opcion equilibrada en costo/calidad.
- `Gemini Flash-Lite` suele ser de las opciones mas baratas.
- `Claude Haiku` suele ser mas barato que `Claude Sonnet`, pero aun asi no siempre gana frente a Gemini u OpenAI mini.

Si cada consulta envia contexto del documento y recibe una respuesta corta o media, el costo por pregunta normalmente puede mantenerse bajo usando modelos mini o lite.

## Recomendacion para este repositorio

Para dejar el proyecto listo para subir:

1. Usar `Gemini` como opcion principal para pruebas porque ya esta integrado en el backend y puede aprovechar el free tier.
2. Usar `Gemini` como primera opcion para pruebas y validacion inicial.
3. Mantener `OpenAI` como respaldo opcional cuando quieras comparar calidad o comportamiento.

## Nota importante

La primera vez que se ejecute el backend, el modelo de embeddings puede descargarse automaticamente. Eso requiere conexion a internet en ese momento.

Algunos PDFs protegidos o cifrados requieren la dependencia `cryptography`, que ya esta incluida en `backend/requirements.txt`.

Si el chat muestra un error de conexion o el backend responde que no esta listo, revisa `http://localhost:8000/health`.

## Fuentes consultadas

Documentacion oficial revisada entre el `26 de abril de 2026` y el `28 de abril de 2026`:

- OpenAI API pricing: `https://openai.com/api/pricing/`
- OpenAI help sobre API: `https://help.openai.com/en/articles/4936851-how-do-i-start-exploring-the-openai-api`
- OpenAI help sobre ChatGPT Plus: `https://help.openai.com/en/articles/6950777-chatgpt-plus-.eps`
- Anthropic pricing: `https://docs.anthropic.com/en/docs/about-claude/pricing`
- Anthropic API getting started: `https://docs.anthropic.com/en/api/getting-started`
- Anthropic API rate limits: `https://docs.anthropic.com/en/api/rate-limits`
- Gemini billing: `https://ai.google.dev/gemini-api/docs/billing`
- Gemini rate limits y free tier: `https://ai.google.dev/gemini-api/docs/quota`
