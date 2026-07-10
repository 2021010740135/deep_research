---
topic: codecoach-agent
doc_type: research_questions
source_type: generated_internal_note
collected_at: 2026-07-09
---

# CodeCoach-Agent Research Questions

## 调研目标

判断 CodeCoach-Agent 方向是否值得继续投入，以及 DeepResearch 项目如何利用内部知识库和 Web Search 支撑这类调研。

这里的 CodeCoach-Agent 暂定不是“帮开发者自动完成任务”的 coding agent，而是“面向学习、训练、代码反馈和成长记录的编程教练 agent”。

## 核心问题

### 1. 用户是谁？

需要区分至少四类用户：

- 编程初学者：需要解释、提示、练习和纠错。
- 计算机专业学生：需要课程作业反馈、代码风格建议、错误定位。
- 企业新人：需要理解大型代码库、完成 onboarding 任务。
- 培训机构或教师：需要批量评估作业、生成反馈、追踪学习进度。

初步判断：

CodeCoach-Agent 如果直接面向成熟开发者，会和 Copilot、Cursor、Devin、CodeRabbit 正面竞争。更合理的切入点是教育、训练和 onboarding。

### 2. 核心价值是什么？

可能的价值主张：

- 不直接替学生写答案，而是分层提示。
- 对代码错误给出可理解解释。
- 把一次代码反馈沉淀成知识点和练习建议。
- 长期记录学生常犯错误，生成个性化学习路径。
- 帮老师减少重复批改压力。

需要避免的伪需求：

- 只是把 ChatGPT 包一层。
- 只是做代码补全。
- 只是自动 review，但没有教学转化。
- 只是生成大段解释，学生无法行动。

### 3. 产品形态应该是什么？

可能形态：

- IDE 插件：边写边提示。
- Web 作业平台：提交代码后生成反馈。
- GitHub PR 教练：对学生 PR 做教学式 review。
- 企业 onboarding 助手：结合内部文档和代码库引导新人。
- DeepResearch 调研助手：先用于调研和知识沉淀，不直接做开发工具。

初步建议：

第一阶段不要做 IDE 插件。先用 DeepResearch 做“研究资料库 + 调研报告生成”，验证方向和需求。之后再考虑把知识库、记忆和反馈机制迁移到真正的 CodeCoach-Agent。

### 4. 和现有竞品的差异是什么？

GitHub Copilot：

- 更强在代码补全、GitHub 工作流、agentic coding。
- CodeCoach-Agent 可以差异化在学习目标、提示层级、成长记录。

Cursor：

- 更强在 IDE 内 codebase understanding 和 agent 执行。
- CodeCoach-Agent 可以差异化在教学过程和可解释反馈。

Devin：

- 更强在异步执行工程任务。
- CodeCoach-Agent 可以差异化在让人参与、让学生学会，而不是替学生完成。

CodeRabbit：

- 更强在 PR review 和团队代码质量。
- CodeCoach-Agent 可以差异化在把 review 结果转换成知识点、练习和学习画像。

### 5. 技术上需要什么能力？

基础能力：

- 读取代码和文档。
- 运行测试或静态分析。
- 定位错误。
- 生成分层提示。
- 生成修改建议。
- 记录用户历史表现。

高级能力：

- 根据用户水平调整解释深度。
- 根据同类错误生成练习。
- 根据课程目标限制提示边界。
- 对答案进行 rubric 评分。
- 区分“代码质量问题”和“知识点缺失”。

### 6. RAG 知识库应该存什么？

适合入库：

- 课程资料。
- 编程规范。
- 常见错误案例。
- 作业说明。
- 标准答案解析。
- 竞品资料。
- 论文和行业报告摘要。
- 教师自己的批改经验。

不适合直接混入同一个 RAG collection：

- 用户短期对话。
- 用户长期记忆。
- workflow checkpoint。
- 未清洗的网页全文。

建议：

外部文档和长期记忆要分 collection。外部文档是 topic knowledge，长期记忆是 user memory，二者生命周期、权限、metadata schema 都不同。

## DeepResearch 当前适合做什么？

DeepResearch 现在适合先做研究辅助，而不是直接做 CodeCoach-Agent 产品。

第一阶段可以做：

- 收集 CodeCoach-Agent 方向资料。
- 把本地 Markdown/PDF 资料入库。
- 用 Web Search 补充最新产品信息。
- 输出竞品分析、论文综述、机会判断。

第二阶段可以做：

- 引入 topic 过滤。
- RAG 知识库和 Memory collection 拆分。
- PDF 解析。
- 检索结果显示来源。
- 报告中区分内部资料和外部搜索。

第三阶段再考虑：

- 针对学生代码生成 feedback。
- 记录学生长期错误模式。
- 做教学型 agent。

## 当前最重要的验证问题

- 学生/新人真正需要的是答案、提示、解释，还是练习路径？
- 教师是否愿意使用 AI feedback 辅助批改？
- 自动反馈的误报是否会伤害学习体验？
- 代码教练应该在 IDE、GitHub PR、Web 作业系统，还是聊天界面里？
- DeepResearch 的多 agent 流程能否稳定生成高质量调研报告？

## 下一步行动

1. 先把竞品、论文、个人判断整理成 topic 资料包。
2. 改造 RAG 入库脚本，支持 topic 目录递归入库。
3. 明确 RAG collection 和 memory collection 分离。
4. 用一个具体问题测试：

   “CodeCoach-Agent 和 Copilot/Cursor/Devin/CodeRabbit 相比，最可能成立的差异化场景是什么？”

5. 根据输出质量决定是否继续优化检索、chunk、metadata 和报告结构。

