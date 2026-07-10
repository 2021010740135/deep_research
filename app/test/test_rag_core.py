import importlib.metadata
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from mult_agents.rag import core


def _version_tuple(package_name: str) -> tuple[int, ...]:
    version = importlib.metadata.version(package_name)
    return tuple(int(part) for part in version.split(".")[:3] if part.isdigit())


class RAGMilvusBackendTest(unittest.TestCase):
    def test_uses_community_backend_for_current_pymilvus_alias_regression(self) -> None:
        pymilvus_version = _version_tuple("pymilvus")
        if pymilvus_version < (2, 6, 14):
            self.skipTest("PyMilvus alias regression is not present in this environment")

        self.assertEqual("langchain_community", core._MILVUS_BACKEND)


class CurlDashScopeEmbeddingsTest(unittest.TestCase):
    def test_embed_documents_posts_to_dashscope_with_curl_stdin(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"output": {"embeddings": [{"embedding": [1.0, 2.0]}]}}).encode("utf-8"),
            stderr=b"",
        )

        with patch("mult_agents.rag.core.subprocess.run", return_value=completed) as run:
            embeddings = core._CurlDashScopeEmbeddings(
                model="text-embedding-v1",
                api_key="test-key",
            )
            result = embeddings.embed_documents(["ping"])

        self.assertEqual([[1.0, 2.0]], result)
        args = run.call_args.args[0]
        self.assertEqual("curl.exe", args[0])
        self.assertIn("--data-binary", args)
        self.assertIn("@-", args)

        body = json.loads(run.call_args.kwargs["input"].decode("utf-8"))
        self.assertEqual("text-embedding-v1", body["model"])
        self.assertEqual({"texts": ["ping"]}, body["input"])
        self.assertEqual({"text_type": "document"}, body["parameters"])


class RAGSystemIngestTest(unittest.TestCase):
    def test_ingest_text_merges_source_with_extra_metadata(self) -> None:
        rag = core.RAGSystem.__new__(core.RAGSystem)
        rag.text_splitter = MockTextSplitter()
        rag.add_documents = Mock(return_value=1)

        total = rag.ingest_text(
            "hello",
            source="D:/docs/note.md",
            metadata={"topic": "codecoach-agent", "doc_type": "notes"},
        )

        self.assertEqual(1, total)
        doc = rag.add_documents.call_args.args[0][0]
        self.assertEqual("hello", doc.page_content)
        self.assertEqual(
            {
                "source": "D:/docs/note.md",
                "topic": "codecoach-agent",
                "doc_type": "notes",
            },
            doc.metadata,
        )


class MockTextSplitter:
    def create_documents(self, texts, metadatas):
        return [
            core.Document(page_content=texts[0], metadata=metadatas[0])
        ]


if __name__ == "__main__":
    unittest.main()
