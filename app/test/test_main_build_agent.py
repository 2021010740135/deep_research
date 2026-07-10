import os
import unittest
from unittest.mock import patch

from langchain_community.chat_models import ChatTongyi

from mult_agents import main as agent_main


class BuildAgentTest(unittest.TestCase):
    def test_build_agent_uses_chat_tongyi_model(self) -> None:
        with patch.object(agent_main, "create_agent", return_value="agent") as create_agent:
            result = agent_main.build_agent("qwen-turbo", "test-key", "intent_router", 0.1, [])

        self.assertEqual("agent", result)
        self.assertEqual("test-key", os.environ["DASHSCOPE_API_KEY"])
        llm = create_agent.call_args.kwargs["model"]
        self.assertIsInstance(llm, ChatTongyi)


if __name__ == "__main__":
    unittest.main()
