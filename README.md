<div align="center">

# DeepResearch — 多智能体深度研究系统

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)](#)
[![LangGraph](https://img.shields.io/badge/LangGraph-Workflow-1C3C3C?logo=langchain&logoColor=white)](#)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D?logo=vuedotjs&logoColor=white)](#)
[![RAG](https://img.shields.io/badge/RAG-Local%20Knowledge%20Base-5B5BD6)](#)
[![Multi-Agent](https://img.shields.io/badge/AI-Multi--Agent%20Research-6E57E0)](#)

**多 Agent 协作 · 联网检索与本地 RAG · 可信引用 · 成本感知意图路由**

</div>

---

## 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [核心工作流](#核心工作流)
- [意图路由与澄清确认](#意图路由与澄清确认)
- [RAG 知识库](#rag-知识库)
- [快速开始](#快速开始)
- [接口说明](#接口说明)
- [测试与评估](#测试与评估)
- [项目结构](#项目结构)
- [部署说明](#部署说明)
- [开发规范](#开发规范)
- [常见问题](#常见问题)
- [更新日志](#更新日志)
- [许可证](#许可证)

## 项目简介

DeepResearch 是一个面向复杂问题的多智能体深度研究系统。它将用户问题拆解为可执行的研究任务，结合联网检索、本地 RAG 知识库和多 Agent 协作，完成资料收集、交叉分析、结论生成与来源整合。

系统并非对所有请求都直接启动高成本研究流程：通过规则引擎、LLM 复核与置信度门控识别用户意图，将请求分流至直接回答、深度研究或澄清确认链路，在保证研究能力的同时控制检索与模型调用成本。

| 功能 | 说明 |
| :--- | :--- |
| 🧭 意图路由 | 基于规则引擎初判、LLM 复核和动态门控，在直接回答、深度研究与澄清确认之间分流 |
| 🔍 深度研究 | 面向调研、对比、趋势、报告等复杂问题，进入任务规划、资料检索、分析与汇总流程 |
| 📚 本地 RAG | 从本地知识库检索与问题相关的文档内容，为研究任务补充领域资料 |
| 🌐 联网检索 | 获取外部信息并与本地资料结合，为研究结论提供可追溯的来源依据 |
| 🤖 多 Agent 协作 | 使用 LangGraph 编排规划、检索、分析和回答生成等工作流节点 |
| ✅ 澄清确认 | 对意图模糊但可能触发高成本研究的请求，要求用户明确选择回答方式 |
| 📡 流式交互 | 后端持续推送工作流进度与节点状态，前端实时展示研究过程和最终结果 |

### 子项目说明

| 目录 | 技术栈 | 说明 |
| :--- | :--- | :--- |
| `app/` | Python + FastAPI + LangGraph | 后端服务、工作流编排、意图路由、RAG 与流式接口 |
| `app/mult_agents/` | LangGraph + LLM | 多 Agent 节点、提示词、状态管理和条件路由 |
| `app/backend/` | FastAPI + Pydantic | 接口层、请求模型、工作流服务与澄清状态管理 |
| `front/agent_front/` | Vue 3 + Vite + TypeScript | 对话前端、流式进度展示与澄清确认交互 |
| `app/test/` | unittest | 意图路由、动态门控、澄清流程与工作流服务测试 |
| `data/rag/` | 本地文档语料 | RAG 知识库的主题资料与测试文档 |
