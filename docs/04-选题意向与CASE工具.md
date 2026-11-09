# 作业：提交选题意向、CASE 工具选择（第 7 组）

> 分隔线之间为提交内容，可直接粘贴到提交框（成员信息已确认）。

---

我们组是第 7 组，共 5 位成员，组长张俊凯，组员申浩、周虹岐、袁航、李润锋。

我们想做的项目叫「智汇笔记」，一个面向学生的个人知识管理系统（Web 版）。功能有五块，Quill 富文本笔记（兼容旧 Markdown，笔记本分组、标签、正文搜索）、待办 Todo（与笔记双向关联）、思维导图（笔记一键转导图）、轻记账（收支记录与月度统计），再加一个 AI 助手（笔记摘要、自动标签）。

开发环境暂定 VS Code + Python 3.11 + Node.js 20。后端用 Flask + SQLAlchemy + SQLite，只对外提供 REST API；前端用 Vue 3（Composition API + 单文件组件）+ Vite 构建，UI 层是 Bootstrap 5，使用 Quill 编辑富文本、marked.js 兼容旧 Markdown、jsMind 画思维导图、ECharts 出图表。建模用 drawio（diagrams.net）画用例图、E-R 图与流程图，StarUML 辅助 UML 建模。版本控制用 Git + Gitee 小组私有仓库，按 Conventional Commits 规范提交，组员各自账号提交，方便区分分工。测试用 pytest 加手工测试用例表。AI 功能设计为「真实 API + 本地规则引擎自动降级」，录制演示的环境断网也能正常跑。

---

## 补充说明

- 技术栈按小组实际选型确定（Flask / SQLite / Vue 3 + Vite），未套用模板示例里的 Java SpringBoot。
- 作业模板中的"VSCode + Java SpringBoot + GitHub"只是示例格式，按本组实际选型填写。
- CASE 工具汇总：开发环境 VS Code；前端构建 Node.js 20 + Vite；建模 drawio + StarUML；版本控制 Git + Gitee；测试 pytest；外部接口 DeepSeek API。
