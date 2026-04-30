import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";

const CHAT_URL = import.meta.env.VITE_API_URL || "/api/chat";
const HEALTH_URL = import.meta.env.VITE_HEALTH_URL || "/api/health";
const REINDEX_URL = import.meta.env.VITE_REINDEX_URL || "/api/reindex";
const SUMMARY_URL = import.meta.env.VITE_SUMMARY_URL || "/api/summarize-document";

const initialMessage = {
  role: "assistant",
  content:
    "Hola. Estoy listo para analizar los PDFs cargados y responder con base en su contenido.",
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

function documentCountLabel(count) {
  return `${count} documento${count === 1 ? "" : "s"} cargado${count === 1 ? "" : "s"}`;
}

function compactLabel(text, maxLength = 72) {
  if (!text) {
    return "";
  }
  return text.length > maxLength ? `${text.slice(0, maxLength - 3)}...` : text;
}

function deploymentLabel(mode) {
  if (mode === "vercel") return "Vercel";
  if (mode === "render") return "Render";
  if (mode === "railway") return "Railway";
  if (mode === "fly") return "Fly.io";
  return "Local";
}

function responseModeLabel(status, backendReady) {
  if (!backendReady) {
    return "Inicializando";
  }
  if (status.response_mode === "generative-rag") {
    return `${status.llm_provider ? status.llm_provider.toUpperCase() : "LLM"} activo`;
  }
  return "Modo basico";
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
      display_title: document.display_title || document.file_name,
    }));
  }

  return (status.indexed_files || []).map((fileName) => ({
    file_name: fileName,
    display_title: fileName,
  }));
}

function App() {
  const [messages, setMessages] = useState([initialMessage]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isSummarizing, setIsSummarizing] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [responseStyle, setResponseStyle] = useState("academico");
  const [backendStatus, setBackendStatus] = useState({
    status: "checking",
    detail: "Verificando backend...",
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
    last_interaction_label: "Sin consultas",
    last_response_ms: 0,
    last_input_tokens: 0,
    last_output_tokens: 0,
    last_total_tokens: 0,
  });
  const endRef = useRef(null);
  const textareaRef = useRef(null);
  const backendReady = backendStatus.status === "ok" && backendStatus.index_ready;
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
    let active = true;
    let timerId;

    async function loadHealth() {
      try {
        const response = await fetch(HEALTH_URL);
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.detail || "No pude consultar el estado del backend.");
        }
        if (!active) {
          return;
        }

        setBackendStatus(data);
        setSelectedDocument((currentValue) => {
          if (currentValue && data.indexed_files?.includes(currentValue)) {
            return currentValue;
          }
          return data.indexed_documents?.[0]?.file_name || data.indexed_files?.[0] || "";
        });
      } catch {
        if (!active) {
          return;
        }

        setBackendStatus({
          status: "error",
          detail: "No pude consultar el estado del backend.",
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
          last_interaction_label: "Sin consultas",
          last_response_ms: 0,
          last_input_tokens: 0,
          last_output_tokens: 0,
          last_total_tokens: 0,
        });
      } finally {
        if (!active) {
          return;
        }

        const nextDelay = backendReady ? 15000 : 5000;
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
  }, [backendReady]);

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
        .slice(-6)
        .map((message) => ({
          role: message.role,
          content: message.content,
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
          ? "No pude conectar con el backend. Verifica que FastAPI este corriendo en http://127.0.0.1:8000."
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

  async function handleReindex() {
    setIsReindexing(true);

    try {
      const response = await fetch(REINDEX_URL, {
        method: "POST",
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "No fue posible reconstruir el indice.");
      }

      setBackendStatus((currentStatus) => ({
        ...currentStatus,
        status: "ok",
        detail: payload.detail,
        indexed_files: payload.indexed_files || [],
        indexed_documents: payload.indexed_documents || [],
        indexed_file_count: (payload.indexed_files || []).length,
        index_ready: true,
      }));
      setSelectedDocument(
        payload.indexed_documents?.[0]?.file_name || payload.indexed_files?.[0] || "",
      );
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content:
            "Reindexe los documentos correctamente. Ya puedes hacer nuevas consultas con el contenido actualizado.",
          sources: [],
        },
      ]);
    } catch (error) {
      setMessages((currentMessages) => [
        ...currentMessages,
        {
          role: "assistant",
          content:
            error instanceof TypeError
              ? "No pude conectar con el backend para reindexar. Verifica que FastAPI este corriendo en http://127.0.0.1:8000."
              : error.message || "No fue posible reindexar los documentos.",
          sources: [],
        },
      ]);
    } finally {
      setIsReindexing(false);
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
              ? "No pude conectar con el backend para resumir el documento."
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

  const statusLabel =
    backendStatus.status === "checking"
      ? "Inicializando backend"
      : backendReady
        ? "Backend listo"
        : "Backend no listo";

  return (
    <motion.div
      className="app-shell"
      initial="hidden"
      animate="visible"
      variants={shellVariants}
    >
      <motion.aside className="sidebar" variants={panelVariants}>
        <div>
          <h1>Asistente documental</h1>
          <p className="sidebar-copy">
            Consulta tus documentos y recibe respuestas mas claras y directas.
          </p>
          <p className="document-counter">
            {documentCountLabel(backendStatus.indexed_file_count)}
          </p>
        </div>

        <motion.div className="status-panel" variants={panelVariants}>
          <motion.div
            className={`status-pill status-${backendStatus.status}`}
            initial={{ opacity: 0.7, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.22 }}
          >
            <span className="dot" />
            {statusLabel}
          </motion.div>
          <div className="status-highlights">
            <div className="status-card">
              <span className="status-card-label">Respuestas</span>
              <strong>{responseModeLabel(backendStatus, backendReady)}</strong>
            </div>
            <div className="status-card">
              <span className="status-card-label">Despliegue</span>
              <strong>{deploymentLabel(backendStatus.deployment_mode)}</strong>
            </div>
          </div>
          <div className="status-highlights">
            <div className="status-card">
              <span className="status-card-label">Velocidad</span>
              <strong>
                {backendStatus.last_response_ms > 0
                  ? `${backendStatus.last_response_ms} ms`
                  : "--"}
              </strong>
            </div>
            <div className="status-card">
              <span className="status-card-label">Uso</span>
              <strong>
                {backendStatus.last_total_tokens > 0
                  ? `${backendStatus.last_total_tokens} tokens`
                  : "--"}
              </strong>
            </div>
          </div>
          <div className="status-highlights">
            <div className="status-card">
              <span className="status-card-label">Disponibles</span>
              <strong>
                No disponible
              </strong>
            </div>
          </div>
          <p className="status-meta">
            {backendStatus.last_interaction_label}
          </p>
          {!backendStatus.allow_reindex && (
            <p className="status-meta">
              El reindexado en vivo esta deshabilitado en este despliegue.
            </p>
          )}
        </motion.div>
      </motion.aside>

      <motion.main className="chat-layout" variants={panelVariants}>
        <section className="chat-window">
          <div className="chat-header">
            <div>
              <p className="eyebrow">Conversacion</p>
              <h2>Consulta tus documentos</h2>
            </div>
            <div className="header-meta">
              <span>{documentCountLabel(backendStatus.indexed_file_count)}</span>
            </div>
          </div>

          <div className="chat-toolbar">
            <div className="toolbar-group toolbar-group-style">
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
              <div className="toolbar-group toolbar-group-summary">
                <label className="summary-label" htmlFor="document-summary-select">
                  Resumir documento
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
                <button
                  className="secondary-button toolbar-button"
                  type="button"
                  onClick={handleSummarizeDocument}
                  disabled={!backendReady || !selectedDocument || isSummarizing}
                >
                  {isSummarizing ? "Resumiendo..." : "Resumir"}
                </button>
              </div>
            )}

            <div className="toolbar-group toolbar-group-help">
              <span className="summary-label">Ayuda breve</span>
              <p className="toolbar-tip">Enter para enviar</p>
              <p className="toolbar-tip">Shift + Enter para salto de linea</p>
            </div>

            {backendStatus.allow_reindex && (
              <div className="toolbar-group toolbar-group-reindex">
                <label className="summary-label" htmlFor="reindex-button">
                  Indice
                </label>
                <button
                  id="reindex-button"
                  className="secondary-button toolbar-button"
                  type="button"
                  onClick={handleReindex}
                  disabled={isReindexing}
                >
                  {isReindexing ? "Reindexando..." : "Reindexar PDFs"}
                </button>
              </div>
            )}
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
                    <span className="loading-copy">Analizando documentos...</span>
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

export default App;
