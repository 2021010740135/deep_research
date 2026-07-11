import os
import sys
import unittest
from pathlib import Path

# 将 app 目录添加到 Python 搜索路径
root = Path(__file__).resolve().parents[2]
src = root / "app"
if str(src) not in sys.path:
    sys.path.insert(0, str(src))

from mult_agents.nodes import detect_intent


class TestDetectIntent(unittest.TestCase):
    """测试意图分类器 detect_intent 函数"""
    
    # ========== 测试强信号：调研类关键词 ==========
    def test_force_multiagent_keywords(self):
        """强制 multiagent 关键词应返回高置信度"""
        test_cases = [
            ("帮我调查一下", "multiagent", 0.92),
            ("调研AI趋势", "multiagent", 0.92),
            ("来源清单", "multiagent", 0.92),
            ("证据收集", "multiagent", 0.92),
            ("热门项目", "multiagent", 0.92),
            ("最新新闻", "multiagent", 0.92),
            ("趋势分析", "multiagent", 0.92),
        ]
        for query, expected_route, expected_conf in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, expected_route, f"查询: '{query}'")
            self.assertEqual(confidence, expected_conf, f"查询: '{query}'")
    
    def test_year_trend_pattern(self):
        """年份+趋势词应返回高置信度 multiagent"""
        test_cases = [
            "2026年AI趋势",
            "2025年技术调研",
            "2024年市场盘点",
            "2026年最新新闻",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "multiagent", f"查询: '{query}'")
            self.assertEqual(confidence, 0.95, f"查询: '{query}'")
    
    def test_medium_multiagent_keywords(self):
        """中等置信度 multiagent 关键词"""
        test_cases = [
            "Python和Java对比分析",
            "架构设计方案",
            "代码实现",
            "落地计划",
            "哪个更好",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "multiagent", f"查询: '{query}'")
            self.assertEqual(confidence, 0.70, f"查询: '{query}'")
    
    # ========== 测试弱信号：纯问候 ==========
    def test_greeting_patterns(self):
        """问候语应返回高置信度 direct"""
        test_cases = [
            "你好",
            "在吗",
            "早上好",
            "晚上好",
            "嗨",
            "hello",
            "hi",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "direct", f"查询: '{query}'")
            self.assertEqual(confidence, 0.98, f"查询: '{query}'")
    
    def test_introduction_patterns(self):
        """自我介绍应返回高置信度 direct"""
        test_cases = [
            "你是谁",
            "你能做什么",
            "介绍你自己",
            "你的名字",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "direct", f"查询: '{query}'")
            self.assertEqual(confidence, 0.95, f"查询: '{query}'")
    
    def test_simple_math_patterns(self):
        """简单数学应返回高置信度 direct"""
        test_cases = [
            "1+1等于几",
            "3乘5是多少",
            "10减3",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "direct", f"查询: '{query}'")
            self.assertEqual(confidence, 0.90, f"查询: '{query}'")
    
    def test_joke_patterns(self):
        """笑话应返回高置信度 direct"""
        test_cases = [
            "讲个笑话",
            "笑话",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "direct", f"查询: '{query}'")
            self.assertEqual(confidence, 0.92, f"查询: '{query}'")
    
    # ========== 测试边界情况 ==========
    def test_greeting_with_research(self):
        """带问候的调研问题应返回 multiagent"""
        test_cases = [
            "你好，帮我调查一下",
            "在吗，想调研一下AI",
            "嗨，分析一下2026年趋势",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "multiagent", f"查询: '{query}'")
            self.assertIn(confidence, [0.92, 0.95, 0.70], f"查询: '{query}'")
    
    def test_ambiguous_query(self):
        """模糊查询应返回低置信度"""
        test_cases = [
            "关于AI的一些想法",
            "帮我看看",
            "这个问题",
        ]
        for query in test_cases:
            route, confidence = detect_intent(query)
            self.assertEqual(route, "direct", f"查询: '{query}'")
            self.assertEqual(confidence, 0.45, f"查询: '{query}'")
    
    def test_empty_query(self):
        """空查询应返回低置信度"""
        route, confidence = detect_intent("")
        self.assertEqual(route, "direct")
        self.assertEqual(confidence, 0.45)
    
    def test_whitespace_only(self):
        """纯空白字符应返回低置信度"""
        route, confidence = detect_intent("   ")
        self.assertEqual(route, "direct")
        self.assertEqual(confidence, 0.45)


if __name__ == "__main__":
    unittest.main()