import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

const CHAT_URL = import.meta.env.VITE_API_URL || "/api/chat";
const HEALTH_URL = import.meta.env.VITE_HEALTH_URL || "/api/health";
const SUMMARY_URL = import.meta.env.VITE_SUMMARY_URL || "/api/summarize-document";
const ADMIN_CONFIG_URL = import.meta.env.VITE_ADMIN_CONFIG_URL || "/api/admin/config";
const ADMIN_SESSION_URL = import.meta.env.VITE_ADMIN_SESSION_URL || "/api/admin/session";
const ADMIN_GOOGLE_SESSION_URL = `${ADMIN_SESSION_URL}/google`;
const ADMIN_DOCUMENTS_URL = import.meta.env.VITE_ADMIN_DOCUMENTS_URL || "/api/admin/documents";
const ADMIN_DOCUMENT_UPLOAD_SESSION_URL = `${ADMIN_DOCUMENTS_URL}/upload-session`;
const ADMIN_DOCUMENT_UPLOAD_COMPLETE_URL = `${ADMIN_DOCUMENTS_URL}/complete`;
const ADMIN_REINDEX_URL = import.meta.env.VITE_ADMIN_REINDEX_URL || "/api/reindex";
const ADMIN_BASE_PATH = import.meta.env.VITE_ADMIN_BASE_PATH || "/gestion";
const HEALTH_CACHE_KEY = "tesis-producto-health-cache";
const HEALTH_CACHE_TTL_MS = 1000 * 60 * 30;
const ADMIN_SESSION_STORAGE_KEY = "tesis-producto-admin-session";

const initialMessage = {
  role: "assistant",
  content:
    "Hola. Estoy listo para ayudarte. Puede hacer preguntas, pedir resúmenes o comparar información cuando lo necesite.",
  sources: [],
};

const shellVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
  },
};

const messageVariants = {
  hidden: { opacity: 0, y: 18, scale: 0.985 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { duration: 0.34, ease: [0.22, 1, 0.36, 1] },
  },
  exit: {
    opacity: 0,
    y: -10,
    transition: { duration: 0.18, ease: "easeOut" },
  },
};

const panelVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.28, ease: [0.22, 1, 0.36, 1] },
  },
};

const responseStyleOptions = [
  { value: "academico", label: "Academico" },
  { value: "simple", label: "Simple" },
  { value: "tecnico", label: "Tecnico" },
];

const suggestedQuestions = [
  "¿Qué dice el manual sobre agricultura ecológica?",
  "Resume el panorama histórico de 1999",
  "¿Diferencia entre agricultura tradicional y ecológica?",
];

const initialBackendStatus = {
  status: "checking",
  detail: "Verificando backend...",
  init_stage: "starting",
  init_progress: 0,
  indexed_files: [],
  indexed_documents: [],
  indexed_file_count: 0,
  index_ready: false,
  index_source: "startup",
  last_index_seconds: 0,
  embed_model: "",
  response_mode: "extractive",
  llm_provider: "",
  llm_model: "",
  deployment_mode: "local",
  allow_reindex: true,
  enable_vector_retrieval: true,
  runtime_reindex_progress: 0,
  runtime_reindex_stage: "",
  runtime_reindex_detail: "",
  runtime_reindex_total_documents: 0,
  runtime_reindex_processed_documents: 0,
  last_interaction_label: "Sin consultas",
  last_response_ms: 0,
  last_input_tokens: 0,
  last_output_tokens: 0,
  last_total_tokens: 0,
  last_generation_status: "not_used",
  last_generation_error: "",
  last_generation_model: "",
};

function readCachedHealthStatus() {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const rawValue = window.localStorage.getItem(HEALTH_CACHE_KEY);
    if (!rawValue) {
      return null;
    }

    const parsed = JSON.parse(rawValue);
    const savedAt = Number(parsed?.saved_at || 0);
    const status = parsed?.status;
    if (!savedAt || !status) {
      return null;
    }

    if (Date.now() - savedAt > HEALTH_CACHE_TTL_MS) {
      return null;
    }

    if (status.status !== "ok" || !status.index_ready) {
      return null;
    }

    return { ...initialBackendStatus, ...status };
  } catch {
    return null;
  }
}

function persistHealthStatus(status) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(
      HEALTH_CACHE_KEY,
      JSON.stringify({
        saved_at: Date.now(),
        status,
      }),
    );
  } catch {
    // Ignoramos fallos de localStorage.
  }
}

function normalizeAppPath(path) {
  if (!path) {
    return "/";
  }
  if (path.length > 1 && path.endsWith("/")) {
    return path.slice(0, -1);
  }
  return path;
}

function isAdminPath(pathname) {
  const normalizedPath = normalizeAppPath(pathname);
  const normalizedAdminBasePath = normalizeAppPath(ADMIN_BASE_PATH);
  return (
    normalizedPath === normalizedAdminBasePath ||
    normalizedPath.startsWith(`${normalizedAdminBasePath}/`)
  );
}

function readAdminSessionToken() {
  if (typeof window === "undefined") {
    return "";
  }
  return window.sessionStorage.getItem(ADMIN_SESSION_STORAGE_KEY) || "";
}

function persistAdminSessionToken(token) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(ADMIN_SESSION_STORAGE_KEY, token);
}

function clearAdminSessionToken() {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(ADMIN_SESSION_STORAGE_KEY);
}

function adminAuthHeaders(token) {
  return {
    Authorization: `Bearer ${token}`,
  };
}

function loadGoogleIdentityScript() {
  if (typeof window === "undefined") {
    return Promise.reject(new Error("Google Identity solo esta disponible en el navegador."));
  }

  if (window.google?.accounts?.id) {
    return Promise.resolve(window.google);
  }

  return new Promise((resolve, reject) => {
    const existingScript = document.getElementById("google-identity-services");
    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(window.google), { once: true });
      existingScript.addEventListener("error", () => reject(new Error("No se pudo cargar Google Identity Services.")), { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = "google-identity-services";
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => resolve(window.google);
    script.onerror = () => reject(new Error("No se pudo cargar Google Identity Services."));
    document.head.appendChild(script);
  });
}

function isLocalServiceUrl(url) {
  return /127\.0\.0\.1|localhost/i.test(url);
}

function getConnectionErrorMessage(target = "backend") {
  if (isLocalServiceUrl(CHAT_URL) || isLocalServiceUrl(HEALTH_URL) || isLocalServiceUrl(SUMMARY_URL)) {
    return target === "summary"
      ? "No pude conectar con el backend para resumir el documento. Verifica que FastAPI este corriendo en http://127.0.0.1:8000."
      : "No pude conectar con el backend. Verifica que FastAPI este corriendo en http://127.0.0.1:8000.";
  }

  return target === "summary"
    ? "No pude conectar con el servicio para resumir el documento. Intenta nuevamente en unos segundos."
    : "No pude conectar con el servicio. Verifica tu conexion o intenta nuevamente en unos segundos.";
}

function documentCountLabel(count) {
  return `${count} documento${count === 1 ? "" : "s"} cargado${count === 1 ? "" : "s"}`;
}

function compactLabel(text, maxLength = 72) {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function prettifyDocumentTitle(title, fileName = "") {
  const source = String(title || fileName || "")
    .replace(/\.[^.]+$/, "")
    .trim();

  if (!source) {
    return "Documento disponible";
  }

  const normalized = source
    .replace(/[_]+/g, " ")
    .replace(/(?<=[a-záéíóúñ])(?=[A-ZÁÉÍÓÚÑ])/g, " ")
    .replace(/\s*[-–]+\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  const withoutNumericPrefix =
    /^\d{1,3}\s+/u.test(normalized) && !/^\d{4}\b/u.test(normalized)
      ? normalized.replace(/^\d{1,3}\s+/u, "")
      : normalized;

  const minorWords = new Set([
    "a",
    "al",
    "de",
    "del",
    "e",
    "el",
    "en",
    "la",
    "las",
    "lo",
    "los",
    "o",
    "para",
    "por",
    "un",
    "una",
    "y",
  ]);

  return withoutNumericPrefix
    .split(" ")
    .filter(Boolean)
    .map((word, index) => {
      if (/^\d+$/u.test(word) || /^[A-ZÁÉÍÓÚÑ]{2,}$/u.test(word)) {
        return word;
      }

      const lowered = word.toLowerCase();
      if (index > 0 && minorWords.has(lowered)) {
        return lowered;
      }

      return lowered.charAt(0).toUpperCase() + lowered.slice(1);
    })
    .join(" ");
}

function backendUiState(status, backendReady) {
  if (status.status === "error") {
    return "error";
  }
  if (status.status === "checking") {
    return "checking";
  }
  if (!backendReady) {
    return "warning";
  }
  return "ok";
}

function backendStageLabel(stage, detail, uiState) {
  if (uiState === "ok") {
    return "Servicio listo para consultas.";
  }
  if (uiState === "error") {
    return detail || "No fue posible inicializar el backend.";
  }
  if (uiState === "warning") {
    return detail || "El backend arranco, pero el indice aun no esta sincronizado.";
  }
  return detail || stage || "Inicializando backend...";
}

function renderInlineFormatting(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`strong-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`text-${index}`}>{part}</span>;
  });
}

function renderMessageContent(content) {
  const lines = content.split("\n");
  const elements = [];
  let bulletItems = [];
  let key = 0;

  function flushBullets() {
    if (bulletItems.length === 0) {
      return;
    }

    elements.push(
      <ul key={`list-${key++}`} className="formatted-list">
        {bulletItems.map((item, index) => (
          <li key={`bullet-${index}`}>{renderInlineFormatting(item)}</li>
        ))}
      </ul>,
    );
    bulletItems = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushBullets();
      continue;
    }

    if (line.startsWith("- ") || line.startsWith("* ")) {
      bulletItems.push(line.slice(2).trim());
      continue;
    }

    flushBullets();
    elements.push(
      <p key={`paragraph-${key++}`} className="formatted-paragraph">
        {renderInlineFormatting(line)}
      </p>,
    );
  }

  flushBullets();
  return elements;
}

function normalizeIndexedDocuments(status) {
  if (status.indexed_documents?.length) {
    return status.indexed_documents.map((document) => ({
      file_name: document.file_name,
      display_title: prettifyDocumentTitle(document.display_title, document.file_name),
    }));
  }

  return (status.indexed_files || []).map((fileName) => ({
    file_name: fileName,
    display_title: prettifyDocumentTitle(fileName, fileName),
  }));
}

function trimHistoryContent(content, maxLength = 600) {
  const normalized = String(content || "").split(/\s+/).filter(Boolean).join(" ");
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 3)}...`;
}

function friendlyStatusLabel(uiState) {
  if (uiState === "checking") {
    return "Preparando sistema";
  }
  if (uiState === "warning") {
    return "Sincronizacion pendiente";
  }
  if (uiState === "error") {
    return "No disponible";
  }
  return "Sistema listo";
}

function assistantModeLabel(status) {
  if (status.response_mode === "generative-rag") {
    return "Respuestas con IA";
  }
  return "Respuestas basadas en documentos";
}

function adminHealthTone(status) {
  if (!status) {
    return "warning";
  }
  if (status.status === "error") {
    return "error";
  }
  if (status.status === "ok" && status.index_ready) {
    return "ok";
  }
  return "warning";
}

function adminHealthLabel(status) {
  if (!status) {
    return "Cargando";
  }
  if (status.status === "error") {
    return "Con incidencias";
  }
  if (status.status === "ok" && status.index_ready) {
    return "En linea";
  }
  return "Revision pendiente";
}

function adminResponseModeLabel(status) {
  if (!status) {
    return "Sin datos";
  }
  if (status.response_mode === "generative-rag") {
    return "Respuestas con IA";
  }
  return "Solo documentos";
}

function adminReindexLabel(status) {
  const value = status?.runtime_last_reindex_status || "";
  if (!value) {
    return "Sin registro";
  }
  if (value === "success") {
    return "Correcto";
  }
  if (value === "running") {
    return "En curso";
  }
  if (value === "failed") {
    return "Fallido";
  }
  return value;
}

function adminReindexProgress(status) {
  const processedDocuments = Number(status?.runtime_reindex_processed_documents || 0);
  const totalDocuments = Number(status?.runtime_reindex_total_documents || 0);
  if (totalDocuments > 0) {
    return Math.max(0, Math.min(100, Math.round((processedDocuments / totalDocuments) * 100)));
  }

  const rawValue = Number(status?.runtime_reindex_progress || 0);
  if (!Number.isFinite(rawValue)) {
    return 0;
  }
  return Math.max(0, Math.min(100, Math.round(rawValue)));
}

function adminReindexMetricLabel(status) {
  const processedDocuments = Number(status?.runtime_reindex_processed_documents || 0);
  const totalDocuments = Number(status?.runtime_reindex_total_documents || 0);
  if (totalDocuments > 0) {
    return `${processedDocuments}/${totalDocuments} documentos`;
  }
  return `${adminReindexProgress(status)}%`;
}

function adminReindexStageCopy(status) {
  if (!status) {
    return "Sin datos de reindexado.";
  }
  if (status.runtime_last_reindex_status === "running") {
    return status.runtime_reindex_detail || "Reindexado en curso.";
  }
  if (status.runtime_last_reindex_status === "failed") {
    return status.runtime_reindex_detail || "El ultimo reindexado termino con errores.";
  }
  if (status.runtime_last_reindex_status === "success") {
    return status.runtime_reindex_detail || "Ultimo reindexado completado correctamente.";
  }
  return "Aun no se ha ejecutado un reindexado manual.";
}

function documentStatusLabel(status) {
  if (status === "indexed") {
    return "Indexado";
  }
  if (status === "pending_index") {
    return "Pendiente de indexar";
  }
  if (status === "failed") {
    return "Con error";
  }
  if (status === "deleted") {
    return "Eliminado";
  }
  return "Pendiente";
}

function compactListLabel(items, maxItems = 3) {
  const values = (items || []).filter(Boolean).slice(0, maxItems);
  return values.length ? values.join(", ") : "Sin etiquetas todavia";
}

function uploadFileToGcsSession(uploadUrl, file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", file.type || "application/pdf");

    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) {
        return;
      }
      const progressValue = Math.min(100, Math.round((event.loaded / event.total) * 100));
      onProgress?.(progressValue);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(100);
        resolve();
        return;
      }
      reject(new Error("No fue posible transferir el archivo al almacenamiento documental."));
    };

    xhr.onerror = () => {
      reject(new Error("La subida del archivo fallo durante la transferencia al almacenamiento."));
    };

    xhr.onabort = () => {
      reject(new Error("La subida del archivo fue cancelada."));
    };

    xhr.send(file);
  });
}

function PublicChatApp() {
  const cachedBackendStatus = readCachedHealthStatus();
  const [messages, setMessages] = useState([initialMessage]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [responseStyle, setResponseStyle] = useState("academico");
  const [backendLoadProgress, setBackendLoadProgress] = useState(
    cachedBackendStatus ? 100 : 7,
  );
  const [backendStatus, setBackendStatus] = useState(
    cachedBackendStatus || initialBackendStatus,
  );
  const previousBackendStatusRef = useRef(
    (cachedBackendStatus || initialBackendStatus).status,
  );
  const endRef = useRef(null);
  const textareaRef = useRef(null);
  const backendReady = backendStatus.status === "ok" && backendStatus.index_ready;
  const currentBackendUiState = backendUiState(backendStatus, backendReady);
  const indexedDocuments = normalizeIndexedDocuments(backendStatus);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [input]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined;
    }

    function handleResize() {
      if (window.innerWidth > 900) {
        setIsMobileSidebarOpen(false);
      }
    }

    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (typeof document === "undefined") {
      return undefined;
    }

    if (isMobileSidebarOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }

    document.body.style.overflow = "";
    return undefined;
  }, [isMobileSidebarOpen]);

  useEffect(() => {
    const previousStatus = previousBackendStatusRef.current;
    previousBackendStatusRef.current = backendStatus.status;

    if (Number.isFinite(backendStatus.init_progress) && backendStatus.init_progress > 0) {
      setBackendLoadProgress(backendStatus.init_progress);
      return undefined;
    }

    if (backendReady) {
      setBackendLoadProgress(100);
      return undefined;
    }

    if (backendStatus.status === "error") {
      setBackendLoadProgress(0);
      return undefined;
    }

    if (backendStatus.status === "checking" && previousStatus !== "checking") {
      setBackendLoadProgress(7);
    }

    const intervalId = window.setInterval(() => {
      setBackendLoadProgress((currentProgress) => {
        if (currentProgress >= 95) {
          return currentProgress;
        }

        const step = Math.max(1, Math.ceil((96 - currentProgress) / 12));
        return Math.min(currentProgress + step, 95);
      });
    }, 350);

    return () => window.clearInterval(intervalId);
  }, [backendReady, backendStatus.status, backendStatus.init_progress]);

  useEffect(() => {
    let active = true;
    let timerId;

    async function loadHealth() {
      let nextDelay = 5000;

      try {
        const response = await fetch(HEALTH_URL);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || "No pude consultar el estado del backend.");
        }
        if (!active) {
          return;
        }

        const normalizedStatus = { ...initialBackendStatus, ...data };
        nextDelay =
          normalizedStatus.status === "ok" && normalizedStatus.index_ready ? 15000 : 5000;
        setBackendStatus(normalizedStatus);
        if (normalizedStatus.status === "ok" && normalizedStatus.index_ready) {
          persistHealthStatus(normalizedStatus);
        }
        setSelectedDocument((currentValue) => {
          if (currentValue && normalizedStatus.indexed_files?.includes(currentValue)) {
            return currentValue;
          }
          return (
            normalizedStatus.indexed_documents?.[0]?.file_name ||
            normalizedStatus.indexed_files?.[0] ||
            ""
          );
        });
      } catch {
        if (!active) {
          return;
        }

        nextDelay = 5000;
        setBackendStatus({
          ...initialBackendStatus,
          status: "error",
          detail: "No pude consultar el estado del backend.",
          init_stage: "error",
          init_progress: 0,
        });
      } finally {
        if (!active) {
          return;
        }

        timerId = window.setTimeout(loadHealth, nextDelay);
      }
    }

    loadHealth();

    return () => {
      active = false;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();

    const question = input.trim();
    if (!question || isLoading) {
      return;
    }

    const nextMessages = [...messages, { role: "user", content: question, sources: [] }];
    setMessages(nextMessages);
    setInput("");
    setIsLoading(true);

    try {
      const history = messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .slice(-4)
        .map((message) => ({
          role: message.role,
          content: trimHistoryContent(message.content),
        }));

      const response = await fetch(CHAT_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question, history, response_style: responseStyle }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "No fue posible consultar el backend.");
      }

      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: payload.answer,
          sources: payload.sources || [],
        },
      ]);
      setBackendStatus((currentStatus) => ({
        ...currentStatus,
        last_interaction_label: "Ultima respuesta",
        last_response_ms: payload.response_ms || 0,
        last_input_tokens: payload.input_tokens || 0,
        last_output_tokens: payload.output_tokens || 0,
        last_total_tokens: payload.total_tokens || 0,
      }));
    } catch (error) {
      const fallbackMessage =
        error instanceof TypeError
          ? getConnectionErrorMessage("backend")
          : "Ocurrio un error al comunicarse con el backend.";

      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content:
            error instanceof TypeError
              ? fallbackMessage
              : error.message || fallbackMessage,
          sources: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleSummarizeDocument() {
    if (!selectedDocument || isSummarizing || !backendReady) {
      return;
    }

    setIsSummarizing(true);

    try {
      const response = await fetch(SUMMARY_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          file_name: selectedDocument,
          response_style: responseStyle,
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "No fue posible resumir el documento.");
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content: payload.answer,
          sources: payload.sources || [],
        },
      ]);
      setBackendStatus((currentStatus) => ({
        ...currentStatus,
        last_interaction_label: "Ultimo resumen",
        last_response_ms: payload.response_ms || 0,
        last_input_tokens: payload.input_tokens || 0,
        last_output_tokens: payload.output_tokens || 0,
        last_total_tokens: payload.total_tokens || 0,
      }));
    } catch (error) {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content:
            error instanceof TypeError
              ? getConnectionErrorMessage("summary")
              : error.message || "No fue posible resumir el documento.",
          sources: [],
        },
      ]);
    } finally {
      setIsSummarizing(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  function handleSuggestedQuestion(question) {
    setInput(question);
    setIsMobileSidebarOpen(false);
    textareaRef.current?.focus();
  }

  const statusLabel = friendlyStatusLabel(currentBackendUiState);
  const backendStageText = backendStageLabel(
    backendStatus.init_stage,
    backendStatus.detail,
    currentBackendUiState,
  );
  const backendProgressValue =
    currentBackendUiState === "warning"
      ? 14
      : Number.isFinite(backendStatus.init_progress) && backendStatus.init_progress > 0
        ? backendStatus.init_progress
        : backendLoadProgress;
  const showBackendDetailMeta =
    backendStatus.detail &&
    backendStatus.detail !== backendStageText &&
    backendStatus.detail !== "Servicio listo";
  const showProgressDetails = currentBackendUiState !== "ok";

  return (
    <motion.div
      className="app-shell"
      initial="hidden"
      animate="visible"
      variants={shellVariants}
    >
      <motion.aside
        className={`sidebar ${isMobileSidebarOpen ? "is-open" : ""}`}
        variants={panelVariants}
      >
        <div className="sidebar-mobile-topbar">
          <span className="status-card-label">Menu</span>
          <button
            type="button"
            className="sidebar-close-button"
            aria-label="Cerrar menu lateral"
            onClick={() => setIsMobileSidebarOpen(false)}
          >
            ×
          </button>
        </div>

        <div>
          <h1>Asistente documental</h1>
          <p className="sidebar-copy">
            Consultas con IA sobre sus archivos.
          </p>
        </div>

        <motion.div className="status-panel" variants={panelVariants}>
          <div className="sidebar-heading-row">
            <motion.div
              className={`status-pill status-${currentBackendUiState}`}
              initial={{ opacity: 0.7, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.22 }}
            >
              <span className="dot" />
              {currentBackendUiState === "ok" ? "En línea" : statusLabel}
            </motion.div>
          </div>

          <div className="status-highlights">
            <div className="status-card status-card-wide">
              <span className="status-card-value">&lt; 3s</span>
              <span className="status-card-caption">Tiempo de respuesta</span>
            </div>
          </div>

          <div className="sidebar-section">
            <span className="status-card-label">Resumen rapido</span>
            <div className="sidebar-mobile-summary">
              <div className="toolbar-field sidebar-mobile-field">
                <label className="summary-label" htmlFor="response-style-select-mobile">
                  Estilo
                </label>
                <select
                  id="response-style-select-mobile"
                  className="summary-select toolbar-select"
                  value={responseStyle}
                  onChange={(event) => setResponseStyle(event.target.value)}
                  disabled={isLoading || isSummarizing}
                >
                  {responseStyleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {indexedDocuments.length > 0 && (
                <div className="toolbar-field toolbar-field-document sidebar-mobile-field">
                  <label className="summary-label" htmlFor="document-summary-select-mobile">
                    Documento
                  </label>
                  <select
                    id="document-summary-select-mobile"
                    className="summary-select toolbar-select"
                    value={selectedDocument}
                    onChange={(event) => setSelectedDocument(event.target.value)}
                    disabled={!backendReady || isSummarizing}
                  >
                    {indexedDocuments.map((document) => (
                      <option
                        key={document.file_name}
                        value={document.file_name}
                        title={document.display_title || document.file_name}
                      >
                        {compactLabel(document.display_title || document.file_name)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                className="secondary-button sidebar-mobile-summary-button"
                type="button"
                onClick={handleSummarizeDocument}
                disabled={!backendReady || !selectedDocument || isSummarizing}
              >
                {isSummarizing ? "Resumiendo..." : "Resumir"}
              </button>
            </div>
          </div>

          <div className="sidebar-section">
            <span className="status-card-label">Preguntas frecuentes</span>
            <div className="sidebar-action-list">
              {suggestedQuestions.map((question) => (
                <button
                  key={question}
                  type="button"
                  className="sidebar-action-button"
                  onClick={() => handleSuggestedQuestion(question)}
                >
                  <span>{question}</span>
                  <span className="sidebar-action-arrow">↗</span>
                </button>
              ))}
            </div>
          </div>

          {showProgressDetails && (
            <div className="backend-progress" aria-live="polite">
              <div className="backend-progress-header">
                <span className="status-card-label">Estado</span>
                <strong>{statusLabel}</strong>
              </div>
              <div
                className="backend-progress-track"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={backendProgressValue}
                aria-label="Progreso de carga del backend"
              >
                <motion.div
                  className="backend-progress-fill"
                  initial={false}
                  animate={{ width: `${backendProgressValue}%` }}
                  transition={{ duration: 0.35, ease: "easeOut" }}
                />
              </div>
              <p className="backend-progress-stage">{backendStageText}</p>
              {showBackendDetailMeta && (
                <p className="status-meta">{backendStatus.detail}</p>
              )}
            </div>
          )}
        </motion.div>
      </motion.aside>

      {isMobileSidebarOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Cerrar panel lateral"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      <motion.main className="chat-layout" variants={panelVariants}>
        <section className="chat-window">
          <div className="chat-header">
            <div>
              <p className="eyebrow">Conversacion</p>
              <h2>Consulta tus documentos</h2>
            </div>
            <div className="chat-header-actions">
              <button
                type="button"
                className="mobile-sidebar-toggle"
                aria-label="Abrir menu lateral"
                aria-expanded={isMobileSidebarOpen}
                onClick={() => setIsMobileSidebarOpen((currentValue) => !currentValue)}
              >
                <span />
                <span />
                <span />
              </button>
              <div className="header-meta">
                <span>{assistantModeLabel(backendStatus)}</span>
              </div>
            </div>
          </div>

          <div className="chat-toolbar chat-toolbar-desktop">
            <div className="toolbar-controls">
              <div className="toolbar-field">
                <label className="summary-label" htmlFor="response-style-select">
                  Estilo
                </label>
                <select
                  id="response-style-select"
                  className="summary-select toolbar-select"
                  value={responseStyle}
                  onChange={(event) => setResponseStyle(event.target.value)}
                  disabled={isLoading || isSummarizing}
                >
                  {responseStyleOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              {indexedDocuments.length > 0 && (
                <div className="toolbar-field toolbar-field-document">
                  <label className="summary-label" htmlFor="document-summary-select">
                    Documento
                  </label>
                  <select
                    id="document-summary-select"
                    className="summary-select toolbar-select"
                    value={selectedDocument}
                    onChange={(event) => setSelectedDocument(event.target.value)}
                    disabled={!backendReady || isSummarizing}
                  >
                    {indexedDocuments.map((document) => (
                      <option
                        key={document.file_name}
                        value={document.file_name}
                        title={document.display_title || document.file_name}
                      >
                        {compactLabel(document.display_title || document.file_name)}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <button
                className="secondary-button toolbar-button"
                type="button"
                onClick={handleSummarizeDocument}
                disabled={!backendReady || !selectedDocument || isSummarizing}
              >
                {isSummarizing ? "Resumiendo..." : "Resumir"}
              </button>
            </div>

            <p className="toolbar-inline-tip">
              Preguntas concretas dan respuestas más rápidas.
            </p>
          </div>

          <div className="messages">
            <AnimatePresence initial={false}>
              {messages.map((message, index) => (
                <motion.article
                  key={`${message.role}-${index}`}
                  className={`message message-${message.role}`}
                  variants={messageVariants}
                  initial="hidden"
                  animate="visible"
                  exit="exit"
                  layout
                >
                  <div className="avatar">{message.role === "user" ? "Tu" : "IA"}</div>
                  <div className="bubble-stack">
                    <div className="bubble">{renderMessageContent(message.content)}</div>
                    {message.role === "assistant" && message.sources?.length > 0 && (
                      <motion.div
                        className="sources-panel"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.08, duration: 0.25 }}
                      >
                        <p className="sources-title">Fuentes utilizadas</p>
                        {[
                          ...new Map(
                            message.sources.map((source) => [
                              source.file_name,
                              {
                                file_name: source.file_name,
                                display_title: source.display_title || source.file_name,
                              },
                            ]),
                          ).values(),
                        ].map((sourceGroup, sourceIndex) => (
                          <motion.div
                            key={`${sourceGroup.file_name}-${sourceIndex}`}
                            className="source-card"
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: sourceIndex * 0.04, duration: 0.2 }}
                          >
                            <p>{sourceGroup.display_title}</p>
                            {message.sources
                              .filter((source) => source.file_name === sourceGroup.file_name)
                              .slice(0, 3)
                              .map((source, pageIndex) => (
                                <p
                                  key={`${sourceGroup.file_name}-page-${pageIndex}`}
                                  className="source-meta"
                                >
                                  {source.page_label
                                    ? `Pagina ${source.page_label}`
                                    : "Pagina no identificada"}
                                </p>
                              ))}
                          </motion.div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                </motion.article>
              ))}
            </AnimatePresence>

            <AnimatePresence>
              {isLoading && (
                <motion.article
                  className="message message-assistant"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <div className="avatar">IA</div>
                  <motion.div
                    className="bubble bubble-loading"
                    initial={{ scale: 0.96 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="loading-dots" aria-hidden="true">
                      <motion.span
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 1, delay: 0 }}
                      />
                      <motion.span
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 1, delay: 0.15 }}
                      />
                      <motion.span
                        animate={{ y: [0, -4, 0] }}
                        transition={{ repeat: Infinity, duration: 1, delay: 0.3 }}
                      />
                    </div>
                    <span className="loading-copy">Preparando respuesta...</span>
                  </motion.div>
                </motion.article>
              )}
            </AnimatePresence>
            <div ref={endRef} />
          </div>
        </section>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Escribe tu pregunta sobre los documentos..."
            rows={1}
            disabled={!backendReady}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || !backendReady}
          >
            Enviar
          </button>
        </form>
      </motion.main>
    </motion.div>
  );
}

function AdminApp() {
  const [config, setConfig] = useState(null);
  const [isLoadingConfig, setIsLoadingConfig] = useState(true);
  const [isValidatingSession, setIsValidatingSession] = useState(true);
  const [session, setSession] = useState(null);
  const [activeAdminSection, setActiveAdminSection] = useState("overview");
  const [errorMessage, setErrorMessage] = useState("");
  const [isSigningIn, setIsSigningIn] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isUploadingDocument, setIsUploadingDocument] = useState(false);
  const [deletingDocumentPath, setDeletingDocumentPath] = useState("");
  const [isReindexing, setIsReindexing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [documentActionMessage, setDocumentActionMessage] = useState("");
  const [selectedUploadName, setSelectedUploadName] = useState("");
  const [systemStatus, setSystemStatus] = useState(null);
  const [isLoadingSystemStatus, setIsLoadingSystemStatus] = useState(false);
  const googleButtonRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    let active = true;

    async function loadAdminConfig() {
      setIsLoadingConfig(true);
      try {
        const response = await fetch(ADMIN_CONFIG_URL);
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || "No fue posible cargar la configuracion de gestion documental.");
        }
        if (!active) {
          return;
        }
        setConfig(payload);
      } catch (error) {
        if (!active) {
          return;
        }
        setErrorMessage(error.message || "No fue posible preparar el acceso de gestion documental.");
      } finally {
        if (active) {
          setIsLoadingConfig(false);
        }
      }
    }

    loadAdminConfig();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    async function validateSession() {
      const token = readAdminSessionToken();
      if (!token) {
        setIsValidatingSession(false);
        return;
      }

      setIsValidatingSession(true);
      try {
        const response = await fetch(ADMIN_SESSION_URL, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || "La sesion de gestion documental ya no es valida.");
        }
        if (!active) {
          return;
        }
        setSession(payload);
        setErrorMessage("");
      } catch (error) {
        clearAdminSessionToken();
        if (!active) {
          return;
        }
        setSession(null);
        setErrorMessage(error.message || "La sesion de gestion documental expiro o no es valida.");
      } finally {
        if (active) {
          setIsValidatingSession(false);
        }
      }
    }

    validateSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!config?.enabled || session?.authenticated || !googleButtonRef.current) {
      return undefined;
    }

    let active = true;

    async function prepareGoogleButton() {
      try {
        const google = await loadGoogleIdentityScript();
        if (!active || !googleButtonRef.current) {
          return;
        }

        google.accounts.id.initialize({
          client_id: config.client_id,
          callback: async ({ credential }) => {
            setIsSigningIn(true);
            setErrorMessage("");
            try {
              const response = await fetch(ADMIN_GOOGLE_SESSION_URL, {
                method: "POST",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({ credential }),
              });
              const payload = await response.json().catch(() => ({}));
              if (!response.ok) {
                throw new Error(payload.detail || "No fue posible iniciar la sesion de gestion documental.");
              }
              persistAdminSessionToken(payload.session_token);
              if (!active) {
                return;
              }
              setSession(payload);
            } catch (error) {
              clearAdminSessionToken();
              if (!active) {
                return;
              }
              setSession(null);
              setErrorMessage(error.message || "No fue posible iniciar la sesion de gestion documental.");
            } finally {
              if (active) {
                setIsSigningIn(false);
              }
            }
          },
        });

        const buttonWidth = Math.max(
          260,
          Math.min(googleButtonRef.current.offsetWidth || 0, 360),
        );

        googleButtonRef.current.innerHTML = "";
        google.accounts.id.renderButton(googleButtonRef.current, {
          theme: "filled_black",
          size: "large",
          shape: "rectangular",
          text: "continue_with",
          logo_alignment: "left",
          width: buttonWidth,
        });
      } catch (error) {
        if (!active) {
          return;
        }
        setErrorMessage(error.message || "No fue posible cargar el acceso con Google.");
      }
    }

    prepareGoogleButton();
    return () => {
      active = false;
    };
  }, [config, session]);

  function handleSignOut() {
    clearAdminSessionToken();
    setSession(null);
    setErrorMessage("");
    setDocuments([]);
    setDeletingDocumentPath("");
    setDocumentActionMessage("");
  }

  async function refreshSystemStatus() {
    const response = await fetch(HEALTH_URL);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "No fue posible consultar el estado operativo.");
    }
    setSystemStatus({ ...initialBackendStatus, ...payload });
  }

  useEffect(() => {
    let active = true;

    async function loadDocuments() {
      if (!session?.authenticated) {
        return;
      }

      setIsLoadingDocuments(true);
      try {
        const token = readAdminSessionToken();
        const response = await fetch(ADMIN_DOCUMENTS_URL, {
          headers: adminAuthHeaders(token),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || "No fue posible cargar los documentos del corpus.");
        }
        if (!active) {
          return;
        }
        setDocuments(payload.documents || []);
      } catch (error) {
        if (!active) {
          return;
        }
        setErrorMessage(error.message || "No fue posible cargar los documentos.");
      } finally {
        if (active) {
          setIsLoadingDocuments(false);
        }
      }
    }

    loadDocuments();
    return () => {
      active = false;
    };
  }, [session]);

  useEffect(() => {
    let active = true;

    async function loadSystemStatus() {
      if (!session?.authenticated) {
        return;
      }

      setIsLoadingSystemStatus(true);
      try {
        await refreshSystemStatus();
      } catch (error) {
        if (!active) {
          return;
        }
        setErrorMessage(error.message || "No fue posible consultar el estado operativo.");
      } finally {
        if (active) {
          setIsLoadingSystemStatus(false);
        }
      }
    }

    loadSystemStatus();
    return () => {
      active = false;
    };
  }, [session]);

  useEffect(() => {
    if (!session?.authenticated) {
      return undefined;
    }

    let active = true;
    let timerId;

    async function pollSystemStatus() {
      const delay =
        systemStatus?.runtime_last_reindex_status === "running" ? 2500 : 12000;

      timerId = window.setTimeout(async () => {
        if (!active) {
          return;
        }

        try {
          await refreshSystemStatus();
        } catch {
          // El panel ya muestra el ultimo error relevante; no sobreescribimos mientras hace polling.
        } finally {
          if (active) {
            pollSystemStatus();
          }
        }
      }, delay);
    }

    pollSystemStatus();
    return () => {
      active = false;
      if (timerId) {
        window.clearTimeout(timerId);
      }
    };
  }, [session, systemStatus?.runtime_last_reindex_status]);

  async function refreshDocuments() {
    const token = readAdminSessionToken();
    const response = await fetch(ADMIN_DOCUMENTS_URL, {
      headers: adminAuthHeaders(token),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.detail || "No fue posible refrescar los documentos.");
    }
    setDocuments(payload.documents || []);
  }

  async function handleDocumentUpload(event) {
    const selectedFile = event.target.files?.[0];
    if (!selectedFile) {
      setSelectedUploadName("");
      return;
    }

    setSelectedUploadName(selectedFile.name);
    setIsUploadingDocument(true);
    setUploadProgress(0);
    setDocumentActionMessage("");
    setErrorMessage("");
    try {
      const token = readAdminSessionToken();
      if (systemStatus?.document_storage_backend === "gcs") {
        const sessionResponse = await fetch(ADMIN_DOCUMENT_UPLOAD_SESSION_URL, {
          method: "POST",
          headers: {
            ...adminAuthHeaders(token),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            file_name: selectedFile.name,
            content_type: selectedFile.type || "application/pdf",
            size: selectedFile.size,
          }),
        });
        const sessionPayload = await sessionResponse.json().catch(() => ({}));
        if (!sessionResponse.ok) {
          throw new Error(sessionPayload.detail || "No fue posible preparar la subida del documento.");
        }

        await uploadFileToGcsSession(
          sessionPayload.upload_url,
          selectedFile,
          (progressValue) => setUploadProgress(progressValue),
        );

        const completeResponse = await fetch(ADMIN_DOCUMENT_UPLOAD_COMPLETE_URL, {
          method: "POST",
          headers: {
            ...adminAuthHeaders(token),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            relative_path: sessionPayload.relative_path,
          }),
        });
        const completePayload = await completeResponse.json().catch(() => ({}));
        if (!completeResponse.ok) {
          throw new Error(completePayload.detail || "El archivo se subio, pero no se pudo registrar en el sistema.");
        }

        await refreshDocuments();
        await refreshSystemStatus();
        setDocumentActionMessage(completePayload.detail || "Documento subido correctamente.");
      } else {
        const formData = new FormData();
        formData.append("file", selectedFile);

        const response = await fetch(ADMIN_DOCUMENTS_URL, {
          method: "POST",
          headers: adminAuthHeaders(token),
          body: formData,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(payload.detail || "No fue posible subir el documento.");
        }

        await refreshDocuments();
        await refreshSystemStatus();
        setDocumentActionMessage(payload.detail || "Documento subido correctamente.");
      }
    } catch (error) {
      setErrorMessage(error.message || "No fue posible subir el documento.");
    } finally {
      setIsUploadingDocument(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      setSelectedUploadName("");
    }
  }

  async function handleDeleteDocument(relativePath) {
    const shouldDelete = window.confirm("¿Seguro que deseas eliminar este documento?");
    if (!shouldDelete) {
      return;
    }

    setDeletingDocumentPath(relativePath);
    setDocumentActionMessage("");
    setErrorMessage("");
    try {
      const token = readAdminSessionToken();
      const response = await fetch(`${ADMIN_DOCUMENTS_URL}/${encodeURIComponent(relativePath)}`, {
        method: "DELETE",
        headers: adminAuthHeaders(token),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "No fue posible eliminar el documento.");
      }
      await refreshDocuments();
      await refreshSystemStatus();
      setDocumentActionMessage(payload.detail || "Documento eliminado correctamente.");
    } catch (error) {
      setErrorMessage(error.message || "No fue posible eliminar el documento.");
    } finally {
      setDeletingDocumentPath("");
    }
  }

  async function handleManualReindex() {
    setIsReindexing(true);
    setDocumentActionMessage("");
    setErrorMessage("");
    try {
      const token = readAdminSessionToken();
      const response = await fetch(ADMIN_REINDEX_URL, {
        method: "POST",
        headers: adminAuthHeaders(token),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "No fue posible ejecutar el reindexado manual.");
      }
      await refreshDocuments();
      await refreshSystemStatus();
      setDocumentActionMessage(payload.detail || "Indice reconstruido correctamente.");
    } catch (error) {
      setErrorMessage(error.message || "No fue posible ejecutar el reindexado manual.");
    } finally {
      setIsReindexing(false);
    }
  }

  const isBusy = isLoadingConfig || isValidatingSession;
  const adminEmail = session?.email || "";
  const managementReady = Boolean(session?.authenticated);
  const reindexRunning = systemStatus?.runtime_last_reindex_status === "running";
  const reindexProgress = adminReindexProgress(systemStatus);
  const reindexMetricLabel = adminReindexMetricLabel(systemStatus);
  const reindexStageCopy = adminReindexStageCopy(systemStatus);
  const isDocumentMutationBusy =
    isUploadingDocument || isReindexing || reindexRunning || Boolean(deletingDocumentPath);
  const systemHealthTone = adminHealthTone(systemStatus);
  const systemHealthLabel = adminHealthLabel(systemStatus);
  const adminSections = [
    { id: "overview", label: "Resumen" },
    { id: "documents", label: "Documentos" },
    { id: "monitoring", label: "Monitoreo" },
  ];
  const showAuthLanding = !isBusy && config?.enabled && !managementReady;
  const adminShellClassName = showAuthLanding
    ? "admin-shell admin-shell-auth"
    : `admin-shell admin-shell-${activeAdminSection}`;
  const adminCardClassName = managementReady
    ? `admin-card admin-card-${activeAdminSection}`
    : "admin-card admin-card-auth";
  const uploadSizeHint =
    systemStatus?.document_storage_backend === "gcs"
      ? "Los PDFs pesados se suben directo a Cloud Storage para evitar limites de Cloud Run."
      : "Formato aceptado: .pdf";
  const totalDocumentCount = documents.length;
  const indexedDocumentCount = Math.min(systemStatus?.indexed_file_count || 0, totalDocumentCount);
  const pendingDocumentCount = Math.max(totalDocumentCount - indexedDocumentCount, 0);
  const showReindexProgressPanel =
    reindexRunning ||
    systemStatus?.runtime_last_reindex_status === "failed" ||
    (systemStatus?.runtime_last_reindex_status === "success" && pendingDocumentCount > 0);

  return (
    <div className={adminShellClassName}>
      <div className={showAuthLanding ? "admin-auth-stack" : undefined}>
      <div className={adminCardClassName}>
        {showAuthLanding ? (
          <div className="admin-auth-topbar">
            <div className="admin-auth-topbar-side" aria-hidden="true" />
            <p className="eyebrow admin-auth-topbar-title">Gestion documental</p>
            <div className="admin-auth-topbar-side" aria-hidden="true" />
          </div>
        ) : (
          <div className="admin-header">
            <div>
              <p className="eyebrow">Gestion documental</p>
              <h1>Panel de gestion documental</h1>
              <p className="admin-copy">
                Esta zona controla la carga, curacion e indexacion del corpus. El chat publico sigue abierto para todos.
              </p>
            </div>
            <div className="admin-header-actions">
              {managementReady && (
                <button
                  type="button"
                  className="admin-link-button admin-link-button-signout"
                  onClick={handleSignOut}
                >
                  Cerrar sesion
                </button>
              )}
              <button
                type="button"
                className="admin-link-button"
                onClick={() => window.location.assign("/")}
              >
                Volver al chat
              </button>
            </div>
          </div>
        )}

        {isBusy && (
          <div className="admin-state-card">
            <strong>Verificando acceso</strong>
            <p>Estamos validando la configuracion y tu sesion de gestion documental.</p>
          </div>
        )}

        {!isBusy && errorMessage && (
          <div className="admin-state-card admin-state-error">
            <strong>No se pudo completar el acceso</strong>
            <p>{errorMessage}</p>
          </div>
        )}

        {!isBusy && config && !config.enabled && (
          <div className="admin-state-card admin-state-warning">
            <strong>Gestion documental aun no configurada</strong>
            <p>
              Falta definir <code>GOOGLE_AUTH_CLIENT_ID</code>, <code>ADMIN_EMAILS</code> y <code>ADMIN_SESSION_SECRET</code> en el backend.
            </p>
          </div>
        )}

        {showAuthLanding && (
          <div className="admin-auth-landing">
            <div className="admin-auth-copy">
              <h1>Panel de gestion documental</h1>
              <p>Zona de carga, curacion e indexacion del corpus. El chat publico sigue abierto para todos.</p>
            </div>
            <div className="admin-panel admin-auth-panel">
              <h2>Gestion documental</h2>
              <p>Zona de carga, curacion e indexacion del corpus.</p>
              <p>El chat público sigue abierto para todos.</p>
              <div className="admin-auth-divider" />
              <div className="admin-auth-access-label">
                <span>Acceso autorizado</span>
              </div>
              <div className="admin-google-button-shell">
                <div className="admin-google-button" aria-hidden="true">
                  <span className="admin-google-button-icon">
                    <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
                      <path
                        fill="#EA4335"
                        d="M12 10.2v3.9h5.4c-.2 1.3-1.6 3.8-5.4 3.8-3.3 0-6-2.7-6-6s2.7-6 6-6c1.9 0 3.1.8 3.9 1.5l2.7-2.6C17 3.3 14.7 2.3 12 2.3 6.7 2.3 2.4 6.6 2.4 12S6.7 21.7 12 21.7c6.9 0 9.1-4.8 9.1-7.2 0-.5-.1-.9-.1-1.3H12z"
                      />
                      <path
                        fill="#34A853"
                        d="M2.4 7.7l3.2 2.4C6.5 8 9 6 12 6c1.9 0 3.1.8 3.9 1.5l2.7-2.6C17 3.3 14.7 2.3 12 2.3 8 2.3 4.6 4.6 2.4 7.7z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M12 21.7c2.6 0 4.8-.9 6.5-2.5l-3-2.5c-.8.6-1.9 1.1-3.5 1.1-3.7 0-5.1-2.5-5.4-3.8l-3.2 2.5c2.1 4.2 5.6 5.2 8.6 5.2z"
                      />
                      <path
                        fill="#4285F4"
                        d="M2.4 16.3l3.2-2.5c-.2-.6-.3-1.2-.3-1.8s.1-1.3.3-1.8L2.4 7.7C1.6 9.2 1.1 10.6 1.1 12s.5 2.8 1.3 4.3z"
                      />
                    </svg>
                  </span>
                  <span>{isSigningIn ? "Validando cuenta..." : "Continuar con Google"}</span>
                </div>
                <div
                  ref={googleButtonRef}
                  className={`admin-google-button-hitbox${isSigningIn ? " is-busy" : ""}`}
                />
              </div>
              <p className="admin-auth-footnote">Solo cuentas autorizadas pueden gestionar el corpus documental.</p>
              {isSigningIn && <p className="status-meta">Validando cuenta autorizada...</p>}
            </div>
          </div>
        )}

        {!isBusy && config?.enabled && managementReady && (
          <nav className="admin-section-nav" aria-label="Secciones de gestion documental">
            {adminSections.map((section) => (
              <button
                key={section.id}
                type="button"
                className={`admin-section-tab${activeAdminSection === section.id ? " is-active" : ""}`}
                onClick={() => setActiveAdminSection(section.id)}
              >
                {section.label}
              </button>
            ))}
          </nav>
        )}

        {!isBusy && config?.enabled && managementReady && activeAdminSection === "overview" && (
          <div className="admin-section-view">
          <div className="admin-grid">
            <div className="admin-panel">
              <span className="status-card-label">Control general</span>
              <h2>Vista resumida del sistema</h2>
              <div className="admin-metric-grid">
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Estado</span>
                  <strong>{isLoadingSystemStatus ? "Cargando" : systemHealthLabel}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Documentos</span>
                  <strong>{systemStatus?.indexed_file_count || documents.length}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Chat</span>
                  <strong>{adminResponseModeLabel(systemStatus)}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Reindex</span>
                  <strong>{adminReindexLabel(systemStatus)}</strong>
                </div>
              </div>
              <div className="admin-detail-list">
                <div className="admin-detail-row">
                  <span>Cuenta autorizada</span>
                  <strong>{adminEmail}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Indice activo</span>
                  <strong>{systemStatus?.active_index_name || "Sin definir"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Ultima latencia</span>
                  <strong>
                    {systemStatus?.last_response_ms ? `${systemStatus.last_response_ms} ms` : "Sin consultas"}
                  </strong>
                </div>
              </div>
            </div>

            <div className="admin-panel">
              <span className="status-card-label">Estado del sistema</span>
              <div className={`admin-health-pill admin-health-pill-${systemHealthTone}`}>
                <span className="dot" />
                {isLoadingSystemStatus ? "Consultando..." : systemHealthLabel}
              </div>
              <div className="admin-metric-grid">
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Indice</span>
                  <strong>{systemStatus?.index_ready ? "Listo" : "Pendiente"}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Documentos</span>
                  <strong>{systemStatus?.indexed_file_count || documents.length}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Chat</span>
                  <strong>{adminResponseModeLabel(systemStatus)}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Reindex</span>
                  <strong>{adminReindexLabel(systemStatus)}</strong>
                </div>
              </div>
              <p className="status-meta">
                {systemStatus?.detail || "Sin novedades operativas por ahora."}
              </p>
            </div>
          </div>
          </div>
        )}

        {!isBusy && config?.enabled && managementReady && activeAdminSection === "documents" && (
          <div className="admin-section-view">
          <div className="admin-grid admin-grid-wide">
            <div className="admin-panel">
              <span className="status-card-label">Carga manual</span>
              <h2>Subir documentos PDF</h2>
              <p>Los archivos que subas quedaran almacenados y luego podras reindexarlos para que entren al chat.</p>
              <label className="admin-upload-field">
                <span>Selecciona un PDF</span>
                <span className="admin-upload-hint">{uploadSizeHint}</span>
                <input
                  ref={fileInputRef}
                  className="admin-upload-input"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleDocumentUpload}
                  disabled={isDocumentMutationBusy}
                />
                <span className="admin-upload-surface">
                  <span className="admin-upload-button">
                    {isUploadingDocument ? "Subiendo..." : "Elegir archivo"}
                  </span>
                  <span className="admin-upload-name">
                    {selectedUploadName || "Ningun archivo seleccionado"}
                  </span>
                </span>
              </label>
              {isUploadingDocument && (
                <p className="status-meta">
                  {systemStatus?.document_storage_backend === "gcs"
                    ? `Subiendo documento... ${uploadProgress}%`
                    : "Subiendo documento..."}
                </p>
              )}
              {documentActionMessage && <p className="admin-success">{documentActionMessage}</p>}
            </div>

            <div className="admin-panel">
              <span className="status-card-label">Control documental</span>
              <h2>{totalDocumentCount} documentos</h2>
              <div className="admin-metric-grid">
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Total</span>
                  <strong>{totalDocumentCount}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Indexados</span>
                  <strong>{indexedDocumentCount}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Pendientes</span>
                  <strong>{pendingDocumentCount}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Fuente</span>
                  <strong>{systemStatus?.document_storage_backend || "local"}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Indice</span>
                  <strong>{systemStatus?.index_ready ? "Sincronizado" : "Pendiente"}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Ruta</span>
                  <strong>{config.admin_base_path || ADMIN_BASE_PATH}</strong>
                </div>
                <div className="admin-metric-card">
                  <span className="admin-metric-label">Bucket</span>
                  <strong>{compactLabel(systemStatus?.documents_bucket || "No aplica", 20)}</strong>
                </div>
              </div>
              <p className="status-meta">
                {isLoadingDocuments
                  ? "Actualizando lista..."
                  : pendingDocumentCount > 0
                    ? `Hay ${pendingDocumentCount} documento${pendingDocumentCount === 1 ? "" : "s"} pendiente${pendingDocumentCount === 1 ? "" : "s"} de indexacion.`
                    : "Todos los documentos visibles ya estan indexados."}
              </p>
              {showReindexProgressPanel && (
                <div className="backend-progress" aria-live="polite">
                  <div className="backend-progress-header">
                    <strong>
                      {reindexRunning
                        ? `Reindexado en curso${systemStatus?.runtime_reindex_total_documents ? ` · ${systemStatus.runtime_reindex_total_documents} documentos` : ""}`
                        : "Ultimo reindexado"}
                    </strong>
                    <span className="status-inline-meta">{reindexMetricLabel}</span>
                  </div>
                  <div
                    className="backend-progress-track"
                    role="progressbar"
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-valuenow={reindexProgress}
                    aria-label="Progreso del reindexado"
                  >
                    <div
                      className="backend-progress-fill"
                      style={{ width: `${reindexProgress}%` }}
                    />
                  </div>
                  <p className="backend-progress-stage">{reindexStageCopy}</p>
                </div>
              )}
              <div className="admin-panel-actions">
                <button
                  type="button"
                  className="admin-reindex-button"
                  onClick={handleManualReindex}
                  disabled={isDocumentMutationBusy}
                >
                  {isReindexing || reindexRunning ? "Reindexando..." : "Reindexar ahora"}
                </button>
              </div>
            </div>
          </div>

          <div className="admin-grid admin-grid-wide admin-grid-single">
            <div className="admin-panel">
              <span className="status-card-label">Biblioteca interna</span>
              <h2>Documentos disponibles en gestion</h2>
              <p className="status-meta">
                {isLoadingDocuments ? "Actualizando lista..." : "Explora, revisa y elimina archivos desde un solo lugar."}
              </p>
              <div className="admin-documents-list admin-documents-list-wide">
                {documents.map((document) => (
                  <div key={document.relative_path} className="admin-document-row">
                    <div className="admin-document-copy">
                      <strong>{document.file_name}</strong>
                      <span>
                        {Math.max(1, Math.round(document.size / 1024))} KB · {documentStatusLabel(document.status)}
                      </span>
                      <span>{compactListLabel(document.topics?.length ? document.topics : document.key_terms)}</span>
                      {document.entities?.length > 0 && <span>{compactListLabel(document.entities, 2)}</span>}
                    </div>
                    <button
                      type="button"
                      className="admin-delete-button"
                      onClick={() => handleDeleteDocument(document.relative_path)}
                      disabled={isDocumentMutationBusy}
                    >
                      {deletingDocumentPath === document.relative_path ? "Eliminando..." : "Eliminar"}
                    </button>
                  </div>
                ))}
                {!isLoadingDocuments && documents.length === 0 && (
                  <p className="status-meta">Aun no hay documentos cargados para gestion documental.</p>
                )}
              </div>
            </div>
          </div>
          </div>
        )}

        {!isBusy && config?.enabled && managementReady && activeAdminSection === "monitoring" && (
          <div className="admin-section-view">
          <div className="admin-grid admin-grid-wide">
            <div className="admin-panel">
              <span className="status-card-label">Monitoreo del chat</span>
              <h2>Operacion conversacional</h2>
              <div className="admin-detail-list">
                <div className="admin-detail-row">
                  <span>Proveedor</span>
                  <strong>{systemStatus?.llm_provider || "No disponible"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Modelo</span>
                  <strong>{systemStatus?.llm_model || "No disponible"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Ultima latencia</span>
                  <strong>
                    {systemStatus?.last_response_ms ? `${systemStatus.last_response_ms} ms` : "Sin consultas"}
                  </strong>
                </div>
                <div className="admin-detail-row">
                  <span>Ultima actividad</span>
                  <strong>{systemStatus?.last_interaction_label || "Sin registro"}</strong>
                </div>
              </div>
            </div>

            <div className="admin-panel">
              <span className="status-card-label">Infraestructura</span>
              <h2>Servicios conectados</h2>
              <div className="admin-detail-list">
                <div className="admin-detail-row">
                  <span>Despliegue</span>
                  <strong>{systemStatus?.deployment_mode || "local"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Documentos</span>
                  <strong>{systemStatus?.document_storage_backend || "local"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Indices</span>
                  <strong>{systemStatus?.index_storage_backend || "local"}</strong>
                </div>
                <div className="admin-detail-row">
                  <span>Bucket documentos</span>
                  <strong>{compactLabel(systemStatus?.documents_bucket || "No aplica", 26)}</strong>
                </div>
              </div>
            </div>
          </div>
          </div>
        )}
      </div>
        {showAuthLanding && (
          <button
            type="button"
            className="admin-auth-exit-button"
            onClick={() => window.location.assign("/")}
          >
            Volver al chat
          </button>
        )}
      </div>
    </div>
  );
}

function App() {
  const pathname = typeof window === "undefined" ? "/" : window.location.pathname;
  if (isAdminPath(pathname)) {
    return <AdminApp />;
  }
  return <PublicChatApp />;
}

export default App;
