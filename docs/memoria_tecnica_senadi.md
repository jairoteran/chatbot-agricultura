# Memoria tecnica del software

## Registro de derechos de autor - SENADI

Documento de apoyo para describir tecnicamente el software **AGROJ ESPECIALIZADO** ante el Servicio Nacional de Derechos Intelectuales de Ecuador.

## 1. Datos generales de la obra

| Campo | Descripcion |
| --- | --- |
| Nombre del software | AGROJ ESPECIALIZADO |
| Tipo de obra | Soporte logico / programa de computacion |
| Dominio de aplicacion | Consulta agricola basada en documentos |
| Lenguajes | Python, JavaScript/JSX, PowerShell |
| Framework frontend | React + Vite |
| Framework backend | FastAPI |
| Arquitectura IA | RAG, embeddings y generacion con modelo de lenguaje |
| Entorno local | Windows, Python 3.12, Node.js |
| Entorno cloud | Google Cloud Run, Cloud Run Jobs, Cloud Storage, Firestore |
| Version documentada | Julio 2026 |

## 2. Resumen ejecutivo

AGROJ ESPECIALIZADO es una aplicacion web que permite consultar informacion agricola a partir de una base documental propia. El sistema permite cargar documentos PDF, procesarlos, indexarlos y responder preguntas en lenguaje natural usando una arquitectura RAG.

El objetivo del software es facilitar el acceso a informacion tecnica, academica e historica sobre agricultura, agroecologia, cultivos, territorio rural y saberes ancestrales, evitando que el usuario tenga que revisar manualmente grandes cantidades de PDFs.

## 3. Alcance funcional

El software incluye:

- interfaz publica de chat
- historial local de conversaciones
- panel protegido de gestion documental
- autenticacion con Google para cuentas autorizadas
- carga de documentos PDF
- subida directa de archivos pesados a Cloud Storage
- eliminacion de documentos
- reindexado manual
- monitoreo de progreso del reindexado
- busqueda semantica y lexical en documentos
- generacion de respuestas con IA
- visualizacion de fuentes cuando corresponde

## 4. Arquitectura tecnica

```text
Frontend React / Vite
  |
  v
Backend FastAPI
  |
  +--> Gestion documental
  +--> Autenticacion y sesiones
  +--> Servicio RAG
  +--> Estado operativo
  |
  +--> Cloud Storage: PDFs e indices
  +--> Firestore: metadatos y progreso
  +--> Cloud Run Jobs: reindexado
  +--> Gemini: generacion de respuestas
```

## 5. Componentes principales

### Frontend

Ubicacion:

```text
frontend/
```

Responsabilidades:

- mostrar el chat publico
- enviar preguntas al backend
- mostrar respuestas y fuentes
- mantener historial local
- mostrar estado del sistema
- implementar el panel `/gestion`
- permitir subida y administracion de PDFs
- adaptar la interfaz a escritorio y movil

Archivo central:

```text
frontend/src/App.jsx
```

### Backend

Ubicacion:

```text
backend/app/
```

Responsabilidades:

- exponer endpoints HTTP
- validar sesiones de gestion documental
- procesar preguntas
- ejecutar recuperacion RAG
- comunicarse con Gemini
- crear sesiones de subida a Cloud Storage
- lanzar reindexado manual
- reportar salud y progreso

Archivos principales:

```text
main.py
rag_service.py
document_repository.py
index_repository.py
metadata_repository.py
admin_auth.py
corpus_analyzer.py
settings.py
```

### Reindexado

El reindexado reconstruye el indice documental.

Entrada:

```text
PDFs almacenados
```

Proceso:

```text
extraccion de texto -> fragmentacion -> embeddings -> indice -> publicacion
```

Salida:

```text
indice activo actualizado y metadatos en Firestore
```

Comando batch:

```powershell
python -m app.reindex_job
```

## 6. Modelo de inteligencia artificial

El sistema no entrena un modelo propio desde cero.

Utiliza modelos ya entrenados:

- `sentence-transformers/all-MiniLM-L6-v2`: embeddings y similitud semantica.
- `Gemini 2.5 Flash`: generacion de respuestas.
- `Gemini 2.5 Flash Lite`: modelo alternativo de respaldo.

La actualizacion de conocimiento ocurre mediante reindexado de documentos, no mediante entrenamiento de pesos del modelo.

## 7. Arquitectura RAG

RAG significa `Retrieval-Augmented Generation`.

En este software:

1. El usuario hace una pregunta.
2. El backend valida que pertenezca al dominio agricola.
3. El sistema busca fragmentos relevantes en los documentos.
4. Los fragmentos se entregan al modelo generativo.
5. Gemini redacta una respuesta clara.
6. El backend devuelve la respuesta al frontend.

Este enfoque reduce respuestas inventadas y permite basar la salida en documentos del corpus.

## 8. Gestion de documentos

Los documentos se administran desde:

```text
/gestion
```

Operaciones:

- subir PDFs
- listar documentos
- eliminar documentos
- reindexar
- revisar estado de indexacion

Estados documentales:

```text
pending_index
indexed
failed
deleted
```

## 9. Infraestructura cloud

Servicios usados:

| Servicio | Uso |
| --- | --- |
| Cloud Run | Backend API y frontend. |
| Cloud Run Jobs | Reindexado documental. |
| Cloud Storage | PDFs originales e indices. |
| Firestore | Metadatos, progreso y estado runtime. |
| Secret Manager | Claves y secretos. |
| Artifact Registry | Imagenes Docker. |

## 10. Seguridad

Medidas implementadas:

- acceso documental protegido con Google Sign-In
- lista de correos autorizados
- sesiones firmadas para el panel
- secretos fuera del repositorio
- subida directa a Cloud Storage mediante sesiones controladas
- separacion entre chat publico y gestion documental

## 11. Limpieza y mantenibilidad

El repositorio evita versionar artefactos generados:

- indices locales
- caches
- builds del frontend
- `node_modules`
- entornos virtuales
- logs
- PDFs de prueba

Esto facilita la revision del codigo fuente y reduce ruido en una entrega formal.

## 12. Dependencias principales

Backend:

- FastAPI
- Uvicorn
- LlamaIndex
- sentence-transformers
- Google GenAI
- Google Cloud Storage
- Google Cloud Firestore
- spaCy
- pypdf

Frontend:

- React
- Vite
- motion

Automatizacion:

- PowerShell
- Google Cloud CLI
- Docker

## 13. Originalidad del software

La originalidad del sistema se encuentra en la integracion funcional de:

- una interfaz conversacional especializada
- un flujo RAG aplicado a documentacion agricola
- gestion documental protegida
- reindexado manual controlado
- operacion cloud separada entre API y proceso batch
- filtros de dominio agricola
- respuestas conversacionales enfocadas en utilidad practica

Aunque utiliza librerias y modelos existentes, la seleccion, integracion, flujo de operacion, organizacion documental, interfaz y logica del backend constituyen el desarrollo propio del software.

## 14. Limitaciones conocidas

- La calidad de respuesta depende de la calidad de los PDFs.
- PDFs escaneados sin OCR pueden aportar poco texto.
- El reindexado masivo puede tardar varias horas.
- La generacion depende de disponibilidad del proveedor de IA.
- Se recomienda agregar pruebas automatizadas mas completas en futuras versiones.

## 15. Evidencia tecnica sugerida

Para anexos o respaldo, conviene capturar:

- `backend/app/main.py` mostrando endpoint `/chat`
- `backend/app/rag_service.py` mostrando modelo de embeddings y RAG
- `backend/Dockerfile`
- `backend/cloudrun.env.yaml.example`
- `frontend/src/App.jsx`
- panel `/gestion`
- Cloud Run services
- Cloud Run Jobs
- buckets de Cloud Storage
- colecciones Firestore

## 16. Conclusión

AGROJ ESPECIALIZADO es un software web funcional orientado a consulta agricola basada en documentos. Su arquitectura separa frontend, backend, almacenamiento, estado y reindexado, lo que permite operar el sistema localmente y en Google Cloud. El proyecto usa IA generativa y recuperacion documental para ofrecer respuestas utiles sin entrenar un modelo propio desde cero.
