import { useEffect, useRef, useState } from "react";

const CHAT_URL = import.meta.env.VITE_API_URL || "/api/chat";
const HEALTH_URL = import.meta.env.VITE_HEALTH_URL || "/api/health";
const REINDEX_URL = import.meta.env.VITE_REINDEX_URL || "/api/reindex";

const initialMessage = {
  role: "assistant",
  content:
    "Hola. Estoy listo para analizar los PDFs cargados y responder con base en su contenido.",
  sources: [],
};

function documentCountLabel(count) {
  return `${count} documento${count === 1 ? "" : "s"} cargado${count === 1 ? "" : "s"}`;
}

function App() {
  const [messages, setMessages] = useState([initialMessage]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [backendStatus, setBackendStatus] = useState({
    status: "checking",
    detail: "Verificando backend...",
    indexed_files: [],
    indexed_file_count: 0,
    index_ready: false,
    index_source: "startup",
    last_index_seconds: 0,
    embed_model: "",
    response_mode: "extractive",
    llm_model: "",
  });
  const endRef = useRef(null);
  const textareaRef = useRef(null);

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
      } catch {
        if (!active) {
          return;
        }

        setBackendStatus({
          status: "error",
          detail: "No pude consultar el estado del backend.",
          indexed_files: [],
          indexed_file_count: 0,
          index_ready: false,
          index_source: "startup",
          last_index_seconds: 0,
          embed_model: "",
          response_mode: "extractive",
          llm_model: "",
        });
      }
    }

    loadHealth();
    const timer = window.setInterval(loadHealth, 15000);

    return () => {
      active = false;
      window.clearInterval(timer);
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
        body: JSON.stringify({ question, history }),
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
    } catch (error) {
      const fallbackMessage =
        error instanceof TypeError
          ? "No pude conectar con el backend. Verifica que FastAPI este corriendo en http://localhost:8000."
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
        indexed_file_count: (payload.indexed_files || []).length,
        index_ready: true,
      }));
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
              ? "No pude conectar con el backend para reindexar. Verifica que FastAPI este corriendo en http://localhost:8000."
              : error.message || "No fue posible reindexar los documentos.",
          sources: [],
        },
      ]);
    } finally {
      setIsReindexing(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit(event);
    }
  }

  const backendReady = backendStatus.status === "ok" && backendStatus.index_ready;
  const indexSourceLabel =
    backendStatus.index_source === "storage"
      ? "Indice cargado desde almacenamiento"
      : backendStatus.index_source === "rebuild"
        ? "Indice reconstruido desde PDFs"
        : "Inicializando indice";
  const responseModeLabel =
    backendStatus.response_mode === "generative-rag"
      ? `Modo conversacional con ${backendStatus.llm_model || "LLM"}`
      : "Modo basico sin modelo generativo";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">PDF Chat</p>
          <h1>Asistente documental</h1>
          <p className="sidebar-copy">
            Haz preguntas sobre los PDFs cargados en <code>backend/data</code>.
          </p>
          <p className="document-counter">
            {documentCountLabel(backendStatus.indexed_file_count)}
          </p>
        </div>

        <div className="status-panel">
          <div className={`status-pill status-${backendStatus.status}`}>
            <span className="dot" />
            {backendReady ? "Backend listo" : "Backend no listo"}
          </div>
          <p className="status-copy">{backendStatus.detail}</p>
          <p className="status-meta">
            {backendStatus.indexed_file_count} documento(s) indexado(s)
          </p>
          <p className="status-meta">
            {indexSourceLabel}
            {backendStatus.last_index_seconds > 0
              ? ` en ${backendStatus.last_index_seconds.toFixed(2)} s`
              : ""}
          </p>
          {backendStatus.embed_model && (
            <p className="status-meta">Embeddings: {backendStatus.embed_model}</p>
          )}
          <p className="status-meta">{responseModeLabel}</p>
          <button
            className="secondary-button"
            type="button"
            onClick={handleReindex}
            disabled={isReindexing}
          >
            {isReindexing ? "Reindexando..." : "Reindexar PDFs"}
          </button>
        </div>
      </aside>

      <main className="chat-layout">
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

          <div className="messages">
            {messages.map((message, index) => (
              <article
                key={`${message.role}-${index}`}
                className={`message message-${message.role}`}
              >
                <div className="avatar">
                  {message.role === "user" ? "Tu" : "IA"}
                </div>
                <div className="bubble-stack">
                  <div className="bubble">
                    <p>{message.content}</p>
                  </div>
                  {message.role === "assistant" && message.sources?.length > 0 && (
                    <div className="sources-panel">
                      <p className="sources-title">Fuentes utilizadas</p>
                      {[...new Set(message.sources.map((source) => source.file_name))].map(
                        (fileName, sourceIndex) => (
                          <div key={`${fileName}-${sourceIndex}`} className="source-card">
                            <p>{fileName}</p>
                          </div>
                        ),
                      )}
                    </div>
                  )}
                </div>
              </article>
            ))}

            {isLoading && (
              <article className="message message-assistant">
                <div className="avatar">IA</div>
                <div className="bubble bubble-loading">
                  <span />
                  <span />
                  <span />
                </div>
              </article>
            )}
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
            disabled={!backendReady && backendStatus.status !== "checking"}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || (!backendReady && backendStatus.status !== "checking")}
          >
            Enviar
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
