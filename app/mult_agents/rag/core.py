import json
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Callable, Iterable, Optional

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymilvus import connections, utility
from requests.exceptions import SSLError

logger = logging.getLogger(__name__)

_DASHSCOPE_EMBEDDING_ENDPOINT = (
    "https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding"
)


# PyMilvus 2.6.14 changed the alias exposed by MilvusClient. langchain-milvus
# 0.3.3 still passes that alias to the legacy ORM Collection API, which raises
# "should create connection first" when a collection already exists.
def _package_version_tuple(package_name: str) -> tuple[int, ...]:
    try:
        version = importlib_metadata.version(package_name)
    except importlib_metadata.PackageNotFoundError:
        return ()

    parts: list[int] = []
    for raw_part in version.split(".")[:3]:
        digits = ""
        for char in raw_part:
            if not char.isdigit():
                break
            digits += char
        if digits == "":
            break
        parts.append(int(digits))
    return tuple(parts)


def _should_use_community_milvus() -> bool:
    pymilvus_version = _package_version_tuple("pymilvus")
    langchain_milvus_version = _package_version_tuple("langchain-milvus")
    return pymilvus_version >= (2, 6, 14) and () < langchain_milvus_version <= (0, 3, 3)


if _should_use_community_milvus():
    from langchain_community.vectorstores.milvus import Milvus as _MilvusVectorStore
    _MILVUS_BACKEND = "langchain_community"
else:
    try:
        from langchain_milvus import Milvus as _MilvusVectorStore
        _MILVUS_BACKEND = "langchain_milvus"
    except ImportError:
        from langchain_community.vectorstores.milvus import Milvus as _MilvusVectorStore
        _MILVUS_BACKEND = "langchain_community"


class _CurlDashScopeEmbeddings(Embeddings):
    def __init__(self, model: str, api_key: str, timeout_seconds: int = 60):
        self.model = model
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, text_type="document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], text_type="query")[0]

    def _embed(self, texts: list[str], text_type: str) -> list[list[float]]:
        if not texts:
            return []

        curl = self._curl_executable()
        body = {
            "model": self.model,
            "parameters": {"text_type": text_type},
            "input": {"texts": texts},
        }
        env = os.environ.copy()
        for proxy_key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            env.pop(proxy_key, None)

        result = subprocess.run(
            [
                curl,
                "-sS",
                "--fail-with-body",
                "-X",
                "POST",
                _DASHSCOPE_EMBEDDING_ENDPOINT,
                "-H",
                f"Authorization: Bearer {self.api_key}",
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
            ],
            input=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            capture_output=True,
            env=env,
            timeout=self.timeout_seconds,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        if result.returncode != 0:
            message = stderr.strip() or stdout.strip()
            raise RuntimeError(f"DashScope curl embedding request failed: {message}")

        payload = json.loads(stdout)
        if payload.get("code"):
            raise ValueError(f"DashScope embedding error: {payload.get('code')} {payload.get('message')}")
        embeddings = payload.get("output", {}).get("embeddings")
        if not isinstance(embeddings, list):
            raise ValueError("DashScope embedding response missing output.embeddings")
        return [item["embedding"] for item in embeddings]

    @staticmethod
    def _curl_executable() -> str:
        candidates = ("curl.exe", "curl") if os.name == "nt" else ("curl", "curl.exe")
        for candidate in candidates:
            if shutil.which(candidate):
                return candidate
        raise RuntimeError("curl executable not found")


class _DashScopeEmbeddingsWithCurlFallback(Embeddings):
    def __init__(self, model: str, api_key: str):
        self._primary = DashScopeEmbeddings(
            model=model,
            dashscope_api_key=api_key,
        )
        self._fallback = _CurlDashScopeEmbeddings(model=model, api_key=api_key)
        self._use_fallback = False

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._use_fallback:
            return self._fallback.embed_documents(texts)
        try:
            return self._primary.embed_documents(texts)
        except SSLError as exc:
            logger.warning("DashScope SDK HTTPS failed; retrying with curl.exe fallback: %s", exc)
            self._use_fallback = True
            return self._fallback.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        if self._use_fallback:
            return self._fallback.embed_query(text)
        try:
            return self._primary.embed_query(text)
        except SSLError as exc:
            logger.warning("DashScope SDK HTTPS failed; retrying with curl.exe fallback: %s", exc)
            self._use_fallback = True
            return self._fallback.embed_query(text)


@dataclass(frozen=True)
class RAGConfig:
    milvus_host: str = "127.0.0.1"
    milvus_port: int = 19530
    collection_name: str = "mult_agent_knowledge"
    embedding_model: str = "text-embedding-v1"
    chunk_size: int = 500
    chunk_overlap: int = 50


class RAGSystem:
    def __init__(self, api_key: str, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.api_key = api_key
        self.embeddings = _DashScopeEmbeddingsWithCurlFallback(
            model=self.config.embedding_model,
            api_key=self.api_key,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )
        self._connect_to_milvus()
        self.vectorstore = _MilvusVectorStore(
            embedding_function=self.embeddings,
            collection_name=self.config.collection_name,
            connection_args={"uri": f"http://{self.config.milvus_host}:{self.config.milvus_port}"},
            auto_id=True,
        )
        logger.info("RAG backend=%s | collection=%s", _MILVUS_BACKEND, self.config.collection_name)

    def _connect_to_milvus(self) -> None:
        try:
            connections.connect(
                alias="default",
                host=self.config.milvus_host,
                port=self.config.milvus_port,
            )
        except Exception as exc:
            logger.error("连接 Milvus 失败: %s", exc)

    def search(self, query: str, k: int = 3) -> str:
        try:
            records = self.search_records(query, k=k)
            if not records:
                return "未找到相关信息。"
            lines: list[str] = ["检索到的相关信息："]
            for idx, record in enumerate(records, 1):
                lines.append(f"{idx}. {record['snippet']}")
                lines.append(f"   (来源: {record['doc_id']})")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("检索失败: %s", exc)
            return f"检索过程中发生错误: {str(exc)}"

    def search_records(self, query: str, k: int = 5) -> list[dict]:
        if not utility.has_collection(self.config.collection_name):
            return []
        docs = self.vectorstore.similarity_search(query, k=k)
        records: list[dict] = []
        for idx, doc in enumerate(docs, 1):
            metadata = doc.metadata or {}
            source = str(metadata.get("source") or "").strip()
            title = Path(source).name if source else f"本地知识片段-{idx}"
            records.append(
                {
                    "source_id": f"LOC-{idx}",
                    "doc_id": source,
                    "title": title,
                    "snippet": doc.page_content,
                    "source_type": "local",
                    "metadata": metadata,
                }
            )
        return records

    def add_documents(self, documents: list[Document]) -> int:
        self.vectorstore.add_documents(documents)
        return len(documents)

    def ingest_text(self, text: str, source: str, metadata: Optional[dict] = None) -> int:
        doc_metadata = dict(metadata or {})
        doc_metadata["source"] = source
        docs = self.text_splitter.create_documents([text], metadatas=[doc_metadata])
        return self.add_documents(docs)

    def ingest_paths(
        self,
        paths: Iterable[Path],
        metadata_factory: Optional[Callable[[Path], dict]] = None,
    ) -> int:
        total = 0
        for path in paths:
            text = path.read_text(encoding="utf-8")
            metadata = metadata_factory(path) if metadata_factory else None
            total += self.ingest_text(text, source=str(path), metadata=metadata)
        return total
