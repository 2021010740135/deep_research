import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = PROJECT_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from dotenv import load_dotenv

from mult_agents.config import AppConfig
from mult_agents.rag.core import RAGConfig, RAGSystem


env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


SUPPORTED_SUFFIXES = (".txt", ".md", ".markdown", ".pdf")
COLLECTION_NAME = ""
MILVUS_HOST = ""
MILVUS_PORT = 0
EMBEDDING_MODEL = "text-embedding-v1"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


@dataclass(frozen=True)
class IngestResult:
    input_path: Path
    file_count: int
    chunk_count: int
    collection_name: str
    dry_run: bool


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest local RAG documents into Milvus.")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--topic", help="Topic folder name under data/rag/topics, for example: codecoach-agent")
    source.add_argument(
        "--input",
        dest="input_path",
        help="File or directory to ingest. Relative paths are resolved from project root.",
    )
    parser.add_argument("--collection", default=None, help="Milvus collection name. Defaults to app config.")
    parser.add_argument("--milvus-host", default=None, help="Milvus host. Defaults to app config.")
    parser.add_argument("--milvus-port", type=int, default=None, help="Milvus port. Defaults to app config.")
    parser.add_argument("--embedding-model", default=EMBEDDING_MODEL, help="DashScope embedding model name.")
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE, help="Text chunk size.")
    parser.add_argument("--chunk-overlap", type=int, default=CHUNK_OVERLAP, help="Text chunk overlap.")
    parser.add_argument("--dry-run", action="store_true", help="List target files and config without writing to Milvus.")
    return parser


def _resolve_input_path(topic: str | None, input_path: str | None) -> Path:
    if topic:
        return (_topics_dir() / topic).resolve()
    if input_path:
        path = Path(input_path).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()
    return _default_input_path().resolve()


def _default_input_path() -> Path:
    return PROJECT_ROOT / "data" / "rag" / "README.md"


def _topics_dir() -> Path:
    return PROJECT_ROOT / "data" / "rag" / "topics"


def _collect_paths(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path] if _is_supported_non_empty_file(input_path) else []

    paths: list[Path] = []
    for suffix in SUPPORTED_SUFFIXES:
        paths.extend(path for path in input_path.rglob(f"*{suffix}") if _is_supported_non_empty_file(path))
    return sorted(paths, key=lambda path: str(path).lower())


def _is_supported_non_empty_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and path.stat().st_size > 0


def _infer_topic(input_path: Path) -> str:
    try:
        relative = input_path.resolve().relative_to(_topics_dir().resolve())
    except ValueError:
        return ""
    return relative.parts[0] if relative.parts else ""


def _metadata_for_path(path: Path, input_root: Path, topic: str | None = None) -> dict:
    if input_root.is_file():
        relative_path = Path(path.name)
    else:
        relative_path = path.resolve().relative_to(input_root.resolve())

    parts = relative_path.parts
    metadata = {
        "relative_path": relative_path.as_posix(),
        "file_type": path.suffix.lower(),
        "doc_type": parts[0] if len(parts) > 1 else "document",
    }
    effective_topic = topic or _infer_topic(path)
    if effective_topic:
        metadata["topic"] = effective_topic
    return metadata


def _read_document_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(path)
    return path.read_text(encoding="utf-8")


def _extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF ingestion requires pypdf. Install it with: uv add pypdf"
        ) from exc

    reader = PdfReader(str(path))
    pages: list[str] = []
    for index, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"[page {index}]\n{text}")
    if not pages:
        raise ValueError(f"No extractable text found in PDF: {path}")
    return "\n\n".join(pages)


def _ingest_files(rag: RAGSystem, paths: list[Path], input_root: Path, topic: str | None) -> int:
    total = 0
    for path in paths:
        text = _read_document_text(path)
        total += rag.ingest_text(
            text,
            source=str(path),
            metadata=_metadata_for_path(path, input_root=input_root, topic=topic),
        )
    return total


def run(argv: Sequence[str] | None = None) -> IngestResult:
    args = _build_parser().parse_args(argv)
    config = AppConfig.from_file()
    input_path = _resolve_input_path(topic=args.topic, input_path=args.input_path)
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))

    paths = _collect_paths(input_path)
    if not paths:
        raise ValueError(f"No supported non-empty RAG files found under: {input_path}")

    collection_name = args.collection or COLLECTION_NAME or config.milvus_collection or RAGConfig().collection_name
    milvus_host = args.milvus_host or MILVUS_HOST or config.milvus_host
    milvus_port = args.milvus_port or MILVUS_PORT or config.milvus_port

    if args.dry_run:
        return IngestResult(
            input_path=input_path,
            file_count=len(paths),
            chunk_count=0,
            collection_name=collection_name,
            dry_run=True,
        )

    rag_cfg = RAGConfig(
        milvus_host=milvus_host,
        milvus_port=milvus_port,
        collection_name=collection_name,
        embedding_model=args.embedding_model,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
    rag = RAGSystem(api_key=config.api_key, config=rag_cfg)
    total_chunks = _ingest_files(rag, paths=paths, input_root=input_path, topic=args.topic)
    return IngestResult(
        input_path=input_path,
        file_count=len(paths),
        chunk_count=total_chunks,
        collection_name=collection_name,
        dry_run=False,
    )


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    result = run(argv)
    if result.dry_run:
        print(
            f"dry-run | input={result.input_path} | files={result.file_count} "
            f"| collection={result.collection_name}"
        )
        return
    print(
        f"ingest complete | input={result.input_path} | files={result.file_count} "
        f"| chunks={result.chunk_count} | collection={result.collection_name}"
    )


if __name__ == "__main__":
    main()
