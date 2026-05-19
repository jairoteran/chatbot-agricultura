from __future__ import annotations

import json
import sys
from datetime import datetime

from app.rag_service import RAGService


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _progress_logger(progress: int, stage: str, detail: str) -> None:
    print(f"[{_timestamp()}] [{progress:>3}%] {stage}: {detail}", flush=True)


def _configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> int:
    _configure_stdout()
    print(f"[{_timestamp()}] Iniciando job de reindexado...", flush=True)
    service = RAGService(
        progress_callback=_progress_logger,
        auto_initialize=False,
        eager_embeddings=False,
    )
    result = service.reindex()
    print(f"[{_timestamp()}] Reindexado finalizado.", flush=True)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
