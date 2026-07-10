---
topic: codecoach-agent
doc_type: paper_notes
source_type: generated_research_note
collected_at: 2026-07-09
sources:
  - https://arxiv.org/abs/2405.15793
  - https://arxiv.org/abs/2407.16741
  - https://arxiv.org/abs/2412.18531
  - https://arxiv.org/abs/2602.14690
  - https://arxiv.org/abs/2601.18341
  - https://arxiv.org/abs/2602.09185
---

# Software Engineering Agent Papers

## 目的

这份笔记整理 AI software engineering agent、agentic coding tool、automated code review 方向的论文线索，用来支撑 CodeCoach-Agent 调研。当前只做摘要级整理，不替代精读论文。

## SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering

来源：https://arxiv.org/abs/2405.15793

核心问题：

语言模型 agent 做软件工程任务时，不能只依赖普通聊天接口。它们需要适合 agent 使用的计算机接口，包括文件编辑、仓库导航、命令执行、测试反馈等。

关键观点：

- Agent-computer interface 会显著影响 agent 的能力。
- SWE-agent 通过专门设计的 ACI 支持 agent 修改代码、浏览仓库、运行测试。
- 论文在 SWE-bench 和 HumanEvalFix 上评估，重点不是教育，而是自动修复和工程任务执行。

对 CodeCoach-Agent 的启发：

- 如果做编程教练，不能只做“聊天回答”。需要让系统理解代码、运行测试、定位错误、解释修改。
- 教学场景的 ACI 还应加入“学习者视角”：错误类型、知识点映射、提示强度、逐步引导。
- 对 DeepResearch 而言，这篇论文适合作为 coding agent 技术架构参考。

## OpenHands: An Open Platform for AI Software Developers as Generalist Agents

来源：https://arxiv.org/abs/2407.16741

核心问题：

OpenHands 关注如何构建开放平台，让 AI agent 像人类开发者一样使用代码、命令行和浏览器完成任务。

关键观点：

- 软件工程 agent 需要 sandbox、命令行、浏览器、代码编辑和 benchmark 支持。
- 平台能力比单个 prompt 更重要。
- 多 agent 协作、安全执行环境和评估基准是核心系统问题。

对 CodeCoach-Agent 的启发：

- 如果目标是教练而不是代写，平台仍然需要安全执行环境和可观察的操作轨迹。
- 教学版 agent 应记录“学生尝试了什么、系统提示了什么、最终如何修复”，这比只生成最终答案更有价值。
- OpenHands 的开放平台定位适合作为技术参考，但产品定位不同。

## Automated Code Review In Practice

来源：https://arxiv.org/abs/2412.18531

核心问题：

LLM 自动代码审查在真实工业环境中到底有什么影响。

关键观点：

- 自动 review 能发现 bug、提升代码质量意识、促进最佳实践。
- 研究也发现了副作用，包括错误建议、不必要修改、无关评论，以及 PR 关闭时间可能变长。
- 这说明自动反馈不是越多越好，反馈质量、时机和可执行性很关键。

对 CodeCoach-Agent 的启发：

- 教练式反馈必须控制噪声，不能只堆建议。
- 初学者更需要“为什么错、怎么改、关联知识点、类似练习”，而不是工程审查式一句话评论。
- 可以把 feedback 分级：blocking issue、learning point、style suggestion、optional improvement。

## Harness Engineering for Agentic AI Coding Tools

来源：https://arxiv.org/abs/2602.14690

核心问题：

Agentic AI coding tools 如何通过仓库级配置文件、上下文文件、skills、subagents 等机制被工程团队配置和约束。

关键观点：

- Context files 在 coding agent 配置中很重要。
- Skills 和 subagents 是更高级的机制，但真实采用还较浅。
- 不同工具形成了不同配置文化，如 Claude Code、GitHub Copilot、Cursor、Gemini、Codex 等。

对 CodeCoach-Agent 的启发：

- 教练 agent 也需要配置层：课程目标、评分标准、禁止直接给答案、提示层级、项目技术栈。
- 可以设计类似 `COACH.md` 或 topic profile 的配置文件，让同一套 agent 面向不同课程/项目时行为不同。
- DeepResearch 的 RAG topic 目录也可以借鉴这个思路，为每个研究方向放一个主题说明文件。

## Agentic Coding Adoption on GitHub

来源：

- https://arxiv.org/abs/2601.18341
- https://arxiv.org/abs/2602.09185

核心问题：

Coding agents 正在真实 GitHub 项目中被快速采用，研究者开始通过 commit、pull request 和 agent-authored traces 观测其影响。

对 CodeCoach-Agent 的启发：

- Coding agent 已经不只是 demo，而是进入真实工程协作流程。
- CodeCoach-Agent 需要明确自己到底优化什么指标：学习效果、代码质量、完成任务速度、减少 tutor 工作量，还是新人 onboarding 效率。
- 如果以后做实验，可以借鉴这类研究的数据视角：PR 反馈、提交质量、任务完成率、学生错误复现率、重复错误下降情况。

## 初步研究判断

这个方向可以拆成三个研究支线：

1. Agent engineering：如何让 agent 操作代码、终端、浏览器、测试环境。
2. Human-agent collaboration：如何让人接管、审查、反馈、配置 agent。
3. Educational feedback：如何把代码修改和 review 转换为学习反馈。

CodeCoach-Agent 的差异化最好落在第三条，同时借鉴前两条的工程能力。

## 下一步精读问题

- SWE-agent 的 ACI 设计能不能抽象成教学 agent 的接口？
- OpenHands 的 sandbox 和 benchmark 机制能不能服务代码练习平台？
- 自动 code review 的误报、噪声和 PR 延迟问题如何迁移到教学场景？
- Context files / skills / subagents 能不能用于课程规则和个性化学习路径？
- CodeCoach-Agent 应该自动修代码，还是只给分层提示？

