# 队员学习路线与 Git 协作指南

环境统一 Python 3.11、Node.js 20、VS Code。远程继续使用现有 Gitee 仓库；小组管理员核对私有权限和成员邀请。

## 阅读顺序

先读 README 并运行 demo，再读后台 auth、notes 和 models；前端先看 router、api、stores，再看 NotesView、TodosView、MindmapsView、BillsView。正文服务、导图转换和AI降级分别在 backend/app/services 下。

## 日常协作

开工拉取最新主干，创建本人功能分支，一个明确任务一个提交。提交格式如 feat(todos): 新增待办编辑，fix(notes): 修复切换覆盖，test(ai): 增加超时降级验证，docs: 更新接口契约。合入使用 Gitee Pull Request，组长评审。禁止将 .env、个人数据库、node_modules、虚拟环境提交。

当前改动保留在 feat/five-module-delivery；不为了让分工好看，把同一个人完成的工作改成他人的提交身份。各成员审核、修改并提交自己负责的部分。

## 学习任务

张俊凯重点解释session、8秒等待和降级；申浩解释HTML与纯文本、未保存保护；周虹岐解释资源归属、日期和导图层级；袁航解释Decimal与月度统计；李润锋解释第三方组件实例、事件清理和构建托管。

每人演示一条完整路径并说明失败时如何处理。不能只照读文档或把未做的功能称为已完成。
