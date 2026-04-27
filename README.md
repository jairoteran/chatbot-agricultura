# PDF Chat App

Proyecto web con dos carpetas:

- `backend`: API en FastAPI + LlamaIndex para cargar PDFs, construir un indice vectorial y responder preguntas.
- `frontend`: interfaz web en React con una experiencia de chat enfocada en documentos.

El objetivo del proyecto es que el asistente no solo recupere texto desde los documentos, sino que tambien lo analice y lo explique con lenguaje claro, como un chatbot conversacional.

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

### Opcion actual del proyecto: OpenAI

```powershell
$env:OPENAI_API_KEY="tu_clave"
```

Opcionalmente puedes elegir el modelo:

```powershell
$env:OPENAI_MODEL="gpt-5.4-mini"
```

Si no defines `OPENAI_API_KEY`, la aplicacion seguira respondiendo con un modo basico basado en recuperacion y sintesis local.

### 4. Agregar PDFs

Coloca tus archivos PDF dentro de `backend/data/`.

### 5. Iniciar el servidor

```powershell
uvicorn app.main:app --reload --port 8000
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
```

### 3. Iniciar el frontend

```powershell
npm run dev
```

La aplicacion quedara disponible en `http://localhost:5173`.

Durante desarrollo, el frontend usa un proxy de Vite hacia `http://localhost:8000`, por lo que no deberias tener problemas de CORS si ambos servicios estan levantados.

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
7. Si se configura una API key de OpenAI, el backend puede usar un modelo generativo para responder con continuidad conversacional y mejor razonamiento.

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

### 1. OpenAI

Ventajas:

- integracion directa con el backend actual;
- buena calidad para respuestas tipo chatbot;
- buen equilibrio entre costo y calidad con modelos mini.

Desventaja:

- no ofrece un free tier general de API para pruebas.

Modelo recomendado para este proyecto:

- `gpt-5.4-mini`

### 2. Anthropic / Claude

Ventajas:

- muy buena capacidad de redaccion y analisis;
- buena opcion si prefieres el estilo de Claude.

Desventajas:

- no es la opcion mas barata para este caso;
- no aparece un free tier general de API como opcion principal para pruebas.

Opciones razonables:

- `Claude Haiku 3.5` si buscas abaratar;
- `Claude Sonnet 4` si priorizas calidad por encima del costo.

### 3. Google Gemini

Ventajas:

- es la mejor opcion para hacer pruebas sin gastar al inicio;
- tiene free tier segun el modelo;
- tambien puede ser muy barato incluso en pago por uso.

Desventaja:

- requeriria adaptar el backend, porque hoy el proyecto esta preparado para OpenAI.

## Cual conviene usar

Si el objetivo es subir el proyecto y dejarlo listo para mostrar:

- usa `OpenAI` si quieres la integracion mas directa y una experiencia de chatbot convincente;
- usa `Gemini` si quieres hacer pruebas gratis o con el menor gasto posible;
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

1. Mantener `OpenAI` como integracion principal porque ya esta conectada al backend.
2. Usar `gpt-5.4-mini` como modelo por defecto para controlar el gasto.
3. Mencionar en la documentacion que `Gemini` es la mejor alternativa si luego se quiere una version con pruebas gratis.

## Nota importante

La primera vez que se ejecute el backend, el modelo de embeddings puede descargarse automaticamente. Eso requiere conexion a internet en ese momento.

Algunos PDFs protegidos o cifrados requieren la dependencia `cryptography`, que ya esta incluida en `backend/requirements.txt`.

Si el chat muestra un error de conexion o el backend responde que no esta listo, revisa `http://localhost:8000/health`.

## Fuentes consultadas

Documentacion oficial revisada el `26 de abril de 2026`:

- OpenAI API pricing: `https://openai.com/api/pricing/`
- OpenAI help sobre API: `https://help.openai.com/en/articles/4936851-how-do-i-start-exploring-the-openai-api`
- OpenAI help sobre ChatGPT Plus: `https://help.openai.com/en/articles/6950777-chatgpt-plus-.eps`
- Anthropic pricing: `https://docs.anthropic.com/en/docs/about-claude/pricing`
- Anthropic API getting started: `https://docs.anthropic.com/en/api/getting-started`
- Anthropic API rate limits: `https://docs.anthropic.com/en/api/rate-limits`
- Gemini billing: `https://ai.google.dev/gemini-api/docs/billing`
- Gemini rate limits y free tier: `https://ai.google.dev/gemini-api/docs/quota`
