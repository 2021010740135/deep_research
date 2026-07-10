import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from mult_agents.rag import ingest


class RAGIngestPathTest(unittest.TestCase):
    def test_collect_paths_recurses_supported_non_empty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            (root / "notes" / "a.md").write_text("alpha", encoding="utf-8")
            (root / "notes" / "b.txt").write_text("beta", encoding="utf-8")
            (root / "notes" / "c.markdown").write_text("gamma", encoding="utf-8")
            (root / "notes" / "empty.md").write_text("", encoding="utf-8")
            (root / "notes" / "paper.pdf").write_bytes(b"%PDF")

            paths = ingest._collect_paths(root)

        self.assertEqual(
            ["a.md", "b.txt", "c.markdown"],
            [path.name for path in paths],
        )

    def test_resolve_input_path_from_topic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            topic_path = project_root / "data" / "rag" / "topics" / "codecoach-agent"
            topic_path.mkdir(parents=True)

            with patch.object(ingest, "PROJECT_ROOT", project_root):
                resolved = ingest._resolve_input_path(topic="codecoach-agent", input_path=None)

        self.assertEqual(topic_path.resolve(), resolved)

    def test_dry_run_does_not_create_rag_system(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            topic_path = project_root / "data" / "rag" / "topics" / "codecoach-agent"
            topic_path.mkdir(parents=True)
            (topic_path / "note.md").write_text("hello", encoding="utf-8")

            config = Mock()
            config.milvus_collection = "mult_agent_memory"
            config.milvus_host = "127.0.0.1"
            config.milvus_port = 19530
            config.api_key = "test-key"

            with patch.object(ingest, "PROJECT_ROOT", project_root), patch.object(
                ingest.AppConfig, "from_file", return_value=config
            ), patch.object(ingest, "RAGSystem", side_effect=AssertionError("should not construct RAG")):
                result = ingest.run(["--topic", "codecoach-agent", "--dry-run"])

        self.assertEqual(1, result.file_count)
        self.assertEqual(0, result.chunk_count)
        self.assertEqual(topic_path.resolve(), result.input_path)
        self.assertEqual("mult_agent_memory", result.collection_name)

    def test_metadata_for_path_includes_topic_and_relative_path(self) -> None:
        root = Path("D:/code/deep_research/data/rag/topics/codecoach-agent")
        path = root / "competitors" / "Copilot.md"

        metadata = ingest._metadata_for_path(path, input_root=root, topic="codecoach-agent")

        self.assertEqual("codecoach-agent", metadata["topic"])
        self.assertEqual("competitors/Copilot.md", metadata["relative_path"])
        self.assertEqual(".md", metadata["file_type"])
        self.assertEqual("competitors", metadata["doc_type"])


if __name__ == "__main__":
    unittest.main()
