# 可编辑建模源文件

01：用户用例图；02：与 SQLAlchemy 模型对应的八表 E-R 图；03：业务与 AI 降级流程。
前三份 `.drawio` 为未压缩 XML，可直接在 diagrams.net 中打开和修改。
04 为 StarUML JSON 工程，包含核心数据类图和两张时序图。NoteTag 表作为数据关系类表示，实际代码采用 db.Table；类间依赖标注对应外键基数。

已校验 XML、JSON、唯一 ID 和全部内部引用。当前环境未安装 StarUML，尚未完成在 StarUML 桌面版中打开后的人工排版验收；请组员在目标版本中打开复核。模型依据最终代码而非模板示例。

格式参考：[StarUML 官方示例](https://github.com/staruml/staruml-xmi/blob/master/unittest-files/XMI21-test-model.mdj)。
