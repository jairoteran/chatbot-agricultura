# PDF Chat App

Proyecto web con dos carpetas:

- `backend`: API en FastAPI + LlamaIndex para cargar PDFs, construir un indice vectorial y responder preguntas.
- `frontend`: interfaz web en React con una experiencia de chat enfocada en documentos.

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

### 3. Agregar PDFs

Coloca tus archivos PDF dentro de `backend/data/`.

### 4. Iniciar el servidor

```powershell
uvicorn app.main:app --reload --port 8000
```

Endpoints disponibles:

- `GET /health`: estado del backend, cantidad de archivos indexados y diagnostico.
- `POST /chat`: responde preguntas usando solo el contenido recuperado de los PDFs.
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

Puedes crear `frontend/.env` a partir de `frontend/.env.example`.

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

1. El backend detecta cambios en los PDFs y reconstruye el indice cuando hace falta.
2. El indice vectorial se persiste en `backend/storage/`.
3. El backend expone estado de salud y reindexacion manual.
4. El frontend muestra el estado del backend, las fuentes usadas y un boton de reindexado.
5. Si no hay evidencia suficiente, el sistema responde claramente que no encontro informacion suficiente.

## Nota importante

La primera vez que se ejecute el backend, el modelo de embeddings puede descargarse automaticamente. Eso requiere conexion a internet en ese momento.

Si el chat muestra un error de conexion o el backend responde que no esta listo, revisa `http://localhost:8000/health`.
