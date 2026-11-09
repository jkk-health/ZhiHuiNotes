"""Seed only a dedicated demonstration database (demo.db by default).

Run python seed.py; an existing demo database requires explicit --reset.
Personal app.db is rejected and is never reset by this script.
"""
import random
import argparse
import json
from pathlib import Path
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import Bill, Note, Notebook, Tag, Todo, User, Mindmap
from app.services.content_service import clean_html, parse_html
from app.services.mindmap_service import generate, encode
import markdown

DEMO_USER = "demo"
DEMO_PWD = "demo123456"

random.seed(2026)  # 固定随机种子，保证每次灌的数据一致（可复现）


# ---------------------------------------------------------------- 笔记正文 --
# 结构化 Markdown：多级标题（供一键转导图）+ 代码块（供预览演示）+ 列表/表格
NOTES = [
    # ---- 笔记本：课程笔记 ----
    (
        "课程笔记",
        "操作系统 · 进程与线程",
        """# 进程与线程

## 进程

进程是**资源分配**的基本单位，拥有独立的地址空间。

- 创建开销大
- 切换需要切换页表
- 崩溃不影响其他进程

## 线程

线程是 **CPU 调度**的基本单位，共享所属进程的地址空间。

- 创建开销小
- 切换只需切换寄存器上下文
- 一个线程崩溃可能带崩整个进程

## 对比

| 维度 | 进程 | 线程 |
|------|------|------|
| 地址空间 | 独立 | 共享 |
| 切换开销 | 大 | 小 |
| 通信方式 | 管道/消息队列 | 直接读写共享变量 |

## 期末考点

1. 进程三状态转换图（就绪/运行/阻塞）
2. 临界区与互斥锁
3. 死锁四个必要条件""",
    ["操作系统", "期末复习"],
    ),
    (
        "课程笔记",
        "计算机网络 · TCP 三次握手",
        """# TCP 三次握手

## 为什么是三次

防止**已失效的连接请求**突然又传到服务端，造成资源浪费。

## 过程

1. 客户端发 SYN=1, seq=x
2. 服务端回 SYN=1, ACK=1, seq=y, ack=x+1
3. 客户端回 ACK=1, seq=x+1, ack=y+1

## 抓包验证

```bash
# 抓本机 5000 端口的握手包
tcpdump -i any port 5000 -n
```

## 常见面试题

- 四次挥手为什么要四次？
- TIME_WAIT 为什么等 2MSL？""",
    ["计算机网络", "考研"],
    ),
    (
        "课程笔记",
        "数据库 · 事务 ACID",
        """# 事务的 ACID 特性

## 原子性 Atomicity

事务是不可分割的最小单元，要么全做要么全不做。由 **undo log** 保证。

## 一致性 Consistency

事务前后，数据库的完整性约束不被破坏。

## 隔离性 Isolation

并发事务互不干扰，四个隔离级别：

1. 读未提交（脏读）
2. 读已提交（不可重复读）
3. 可重复读（幻读，InnoDB 默认）
4. 串行化

## 持久性 Durability

提交后永久生效，由 **redo log** 保证。

## 本项目应用

智汇笔记后端的笔记写入就包在事务里，保证软删除与标签关联的一致性。""",
    ["数据库", "期末复习"],
    ),
    (
        "课程笔记",
        "计算机组成原理 · 流水线",
        """# 指令流水线

## 五段流水线

取指 IF -> 译码 ID -> 执行 EX -> 访存 MEM -> 写回 WB

## 三种冲突

- **结构冲突**：硬件资源竞争，停顿一拍
- **数据冲突**：后一条指令用到前一条的结果，转发/旁路解决
- **控制冲突**：分支指令改变 PC，分支预测解决

## 公式

吞吐率 = 指令数 / 总时间；加速比趋近于段数 k""",
    ["计组", "期末复习"],
    ),
    (
        "课程笔记",
        "软件工程 · 需求分析方法",
        """# 需求分析

## 需求的层次

1. 业务需求
2. 用户需求
3. 功能需求 + 非功能需求

## 建模方法

- **结构化分析**：数据流图 DFD、数据字典 DD、E-R 图
- **面向对象分析**：用例图、类图、时序图

## 本项目实践

智汇笔记用例图覆盖三个角色：访客 / 注册用户 / 管理员，
功能需求按 MoSCoW 分级（Must / Should / Could）。

## 评审要点

需求评审的重点是**验证而不是确认**：找矛盾、找遗漏、找不可测试的描述。""",
    ["软件工程"],
    ),
    (
        "课程笔记",
        "高数 · 级数收敛判别",
        """# 无穷级数判敛

## 正项级数

1. 比较判别法：与 p-级数、等比级数比较
2. 比值法：lim n→∞ a(n+1)/a(n) = ρ，ρ<1 收敛
3. 根值法：lim ⁿ√aₙ = ρ

## 交错级数

莱布尼茨判别法：单调递减 + 趋于 0 => 收敛。

## 绝对收敛与条件收敛

- 绝对收敛必收敛
- ∑(-1)ⁿ/n 条件收敛（调和级数发散但交错收敛）

## 易错点

比较判别法的极限形式要求极限存在且非零。""",
    ["高数", "期末复习"],
    ),
    # ---- 笔记本：算法刷题 ----
    (
        "算法刷题",
        "动态规划 · 入门套路",
        """# 动态规划入门

## DP 三要素

1. **状态定义**：dp[i] 表示什么
2. **转移方程**：dp[i] 怎么由子问题推出
3. **初始条件与边界**

## 从斐波那契说起

```python
def fib(n):
    dp = [0, 1]
    for i in range(2, n + 1):
        dp.append(dp[i-1] + dp[i-2])
    return dp[n]
```

## 经典模型

- 线性 DP：爬楼梯、打家劫舍
- 背包 DP：0-1 背包、完全背包（零钱兑换）
- 区间 DP：最长回文子串
- 字符串 DP：编辑距离、LCS

## 刷题路线

先刷一维，再背包，最后区间和树形。""",
    ["算法", "动态规划", "Python"],
    ),
    (
        "算法刷题",
        "背包九讲 · 完全背包",
        """# 完全背包

## 与 0-1 背包的区别

每件物品可以用**无限次**。

## 状态转移

dp[j] = max(dp[j], dp[j - w[i]] + v[i])

## 遍历顺序（关键！）

```python
# 0-1 背包：容量倒序，防止重复选取
for i in items:
    for j in range(V, w[i] - 1, -1):
        dp[j] = max(dp[j], dp[j - w[i]] + v[i])

# 完全背包：容量正序，允许重复选取
for i in items:
    for j in range(w[i], V + 1):
        dp[j] = max(dp[j], dp[j - w[i]] + v[i])
```

## 例题

零钱兑换 II（求方案数）、完全平方数（求最少个数）。""",
    ["算法", "动态规划"],
    ),
    (
        "算法刷题",
        "二分查找 · 边界模板",
        """# 二分查找模板

## 左闭右闭 [l, r]

```python
def binary_search(nums, target):
    l, r = 0, len(nums) - 1
    while l <= r:
        mid = (l + r) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            l = mid + 1
        else:
            r = mid - 1
    return -1
```

## 三种变体

1. 找第一个 >= target（lower_bound）
2. 找最后一个 <= target
3. 旋转数组找目标

## 易错点

- 死循环：边界更新写错
- 溢出：mid = l + (r - l) // 2""",
    ["算法", "C++"],
    ),
    (
        "算法刷题",
        "图论 · DFS 与 BFS",
        """# 图的遍历

## DFS（栈/递归）

适合：连通性、拓扑排序、割点桥。

```python
def dfs(u, visited, graph):
    visited[u] = True
    for v in graph[u]:
        if not visited[v]:
            dfs(v, visited, graph)
```

## BFS（队列）

适合：**最短路（无权图）**、层次遍历。

## 剪枝技巧

- 可行性剪枝：当前状态不可能到达答案
- 最优性剪枝：当前代价已超过已知最优
- 记忆化：同一状态只算一次""",
    ["算法", "Python"],
    ),
    (
        "算法刷题",
        "C++ STL 常用容器",
        """# C++ STL 速查

## 序列容器

| 容器 | 特点 | 适用 |
|------|------|------|
| vector | 动态数组 | 随机访问 |
| list | 双向链表 | 频繁插删 |
| deque | 双端队列 | 队列/单调队列 |

## 关联容器

- set / map：红黑树，有序，O(log n)
- unordered_set / unordered_map：哈希表，均摊 O(1)

## 踩坑记录

**set 自定义结构体重载 operator< 必须加 const**，否则插入时编译报 C2678。

```cpp
struct Node {
    int x;
    bool operator<(const Node& o) const { return x < o.x; }
};```""",
    ["C++"],
    ),
    (
        "算法刷题",
        "编辑距离 · 字符串 DP",
        """# 编辑距离（LeetCode 72 / 洛谷 P2758）

## 状态定义

dp[i][j] = word1 前 i 个字符变成 word2 前 j 个字符的最少操作数。

## 转移方程

- 相等：dp[i][j] = dp[i-1][j-1]
- 不等：dp[i][j] = 1 + min(插入, 删除, 替换)

## 实现

```python
def edit_distance(s, t):
    m, n = len(s), len(t)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s[i-1] == t[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[m][n]
```

## 相关题

P1140 序列比对（带权值的变体）。""",
    ["算法", "动态规划", "Python"],
    ),
    # ---- 笔记本：项目开发 ----
    (
        "项目开发",
        "智汇笔记 · 架构决策记录",
        """# 架构决策记录（ADR）

## 分层架构

- 表现层：Vue 3 SPA（Vite 构建）
- 接口层：Flask Blueprint，统一 /api 前缀
- 业务层：Service（AI 适配器模式）
- 数据层：SQLAlchemy + SQLite

## 为什么选方案 B

Flask API + Vue SPA：前后端职责清晰，REST 接口可以写进设计报告加分；
导图/图表是交互密集模块，组件化开发质量最高。

## 关键决策

1. 导图数据流**单向**：笔记是源，导图是视图，不回写
2. AI 适配器 + 本地降级：断网也能演示（答辩保命设计）
3. 软删除：回收站用 is_deleted 标记，不物理删除""",
    ["软件工程", "Flask", "Vue"],
    ),
    (
        "项目开发",
        "Flask 蓝图与工厂模式",
        """# Flask 工厂模式

## 应用工厂

```python
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    app.register_blueprint(health_bp, url_prefix="/api")
    return app
```

## 蓝图注册

每个模块一个蓝图：auth / notes / todos / mindmaps / ai / bills，
统一挂在 /api 下，避免循环导入。

## flask run 原理

wsgi.py 里 `app = create_app()`，Flask CLI 自动检测到 app 对象。

## 注意事项

- 扩展单例放 extensions.py，init_app 延迟绑定
- SQLite 要显式打开外键 PRAGMA""",
    ["Flask", "Python"],
    ),
    (
        "项目开发",
        "Vue 3 组合式 API 要点",
        """# Vue 3 Composition API

## <script setup> 写法

```vue
<script setup>
import { ref, onMounted } from 'vue'
const count = ref(0)
onMounted(() => console.log('mounted'))
</script>
<template>
  <button @click="count++">{{ count }}</button>
</template>
```

## 项目铁律（防 AI 混写）

1. 全项目只用 `<script setup>`，禁止 Options API
2. 第三方库实例（ECharts/jsMind）不进 ref/reactive，
   用 **shallowRef** 或模块级变量
3. onMounted 初始化，onUnmounted 里 dispose()

## 响应式 API

- ref：基本类型 + 模板自动解包
- reactive：对象/数组（解构会失去响应性，慎用）
- computed：派生值缓存""",
    ["Vue", "前端"],
    ),
    (
        "项目开发",
        "RESTful 接口设计规范",
        """# REST 接口规范

## 资源命名

- 名词复数：/api/notes、/api/todos
- 动作用 HTTP 方法表达：GET 查、POST 建、PUT 改、DELETE 删

## 状态码约定

| 码 | 场景 |
|----|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 参数错误 |
| 401 | 未登录 / 密码错误 |
| 403 | 无权限（改他人数据） |
| 404 | 资源不存在 |

## 响应体格式

成功：直接返回数据；失败：`{"error": "原因"}`。""",
    ["Flask", "软件工程"],
    ),
    (
        "项目开发",
        "Git 协作与 Conventional Commits",
        """# Git 提交规范

## Conventional Commits 格式

    <type>(<scope>): <subject>

- feat：新功能
- fix：修 bug
- chore：脚手架/配置
- docs：文档
- test：测试

## 分支模型

main 保护 + feat/<迭代> 开发分支，任务完成后合并。

## 本组约定

每人用各自账号提交，提交历史就是分工证据（考核要求）。""",
    ["Git", "软件工程"],
    ),
    # ---- 笔记本：生活随笔 ----
    (
        "生活随笔",
        "本周消费复盘",
        """# 本周消费复盘

## 支出大头

- 餐饮：外卖偏多，下周改食堂
- 打印资料：课程复习资料 30 页

## 省钱计划

1. 每周外卖不超过 3 次
2. 话费套餐换成校园卡副卡
3. 教材买二手或找学长要电子版

## 记账工具

就用自己在做的智汇笔记记账模块，自用自测。""",
    ["记账", "生活"],
    ),
    (
        "生活随笔",
        "电脑义诊活动复盘",
        """# 第 4 次电脑义诊复盘

## 数据

- 接待 23 人次，重装系统 6 台、清灰 4 台、装软件 9 台
- 线下教学环节：讲解重装系统流程，围观同学 15+

## 做得好的

- 提前分了「接待 / 维修 / 教学」三组，没有排长队
- 备件（硅脂、U盘启动盘）这次带够了

## 待改进

- U 盘容易被借走，下次编号登记
- 教学环节可以提前发讲义，现场少写板书""",
    ["社团", "生活"],
    ),
    (
        "生活随笔",
        "考研 vs 就业 决策草稿",
        """# 方向决策

## 考研

- 优点：学历门槛、缓冲时间、深入方向
- 风险：一年成本、竞争激烈

## 就业

- 优点：早积累工程经验、早经济独立
- 风险：本科竞争大、天花板

## 当前策略

两手准备：按考研节奏复习数学 + 408，
同时把项目做扎实（智汇笔记 + 蓝桥杯/CSP 证书），
到大三下再根据模考成绩定。

## 下一步

- CSP 认证冲 200 分
- 项目按 Sprint 推进，不烂尾""",
    ["规划", "生活"],
    ),
    (
        "生活随笔",
        "宿舍网络抢修记",
        """# 宿舍断网排查

## 现象

每晚 11 点后 WiFi 卡顿，白天正常。

## 排查过程

1. ping 网关：丢包 30% -> 怀疑信道拥堵
2. 用 WiFi 分析仪看信道：全楼挤在信道 6
3. 路由器改信道 11 + 5G 优先

## 结果

晚高峰丢包降到 0，宿舍上网课不再卡。

## 教训

无线问题先看**信道占用**，再怀疑设备和带宽。""",
    ["生活"],
    ),
]

# ---------------------------------------------------------------- 待办样例 --
# (标题, 截止日期相对天数, 是否完成, 笔记标题或 None)
TODOS = [
    ("补交操作系统实验报告", -3, False, "操作系统 · 进程与线程"),
    ("复习高数第十一章 级数", -1, False, "高数 · 级数收敛判别"),
    ("刷 5 道动态规划题", 0, False, "动态规划 · 入门套路"),
    ("完成智汇笔记 Sprint 1 自测", 1, False, "智汇笔记 · 架构决策记录"),
    ("给组员分配需求分析文档任务", 2, False, None),
    ("预约体检", 5, False, None),
    ("还图书馆《算法导论》", -7, True, None),
    ("买硅脂（下次义诊用）", 3, False, "电脑义诊活动复盘"),
    ("背完考研英语核心词 List 12", -2, True, None),
    ("整理本月发票报销社团经费", 4, False, "电脑义诊活动复盘"),
]

# ---------------------------------------------------------------- 账单样例 --
# (类型, 类别, 金额, 相对天数, 备注)
BILLS = [
    ("支", "餐饮", 15.5, -62, "食堂三餐"),
    ("支", "餐饮", 28.0, -61, "和室友聚餐"),
    ("支", "学习", 45.0, -60, "二手教材"),
    ("收", "兼职", 300.0, -58, "机房助管"),
    ("支", "交通", 12.0, -55, "回家往返地铁"),
    ("支", "娱乐", 39.0, -50, "电影票"),
    ("支", "餐饮", 16.0, -45, "食堂三餐"),
    ("收", "奖学金", 500.0, -40, "学习进步奖"),
    ("支", "学习", 68.0, -35, "CSP 报名费"),
    ("支", "日用", 25.9, -30, "键盘键帽"),
    ("支", "餐饮", 15.0, -20, "食堂三餐"),
    ("支", "日用", 88.0, -18, "鼠标垫+散热支架"),
    ("支", "学习", 30.0, -12, "打印复习资料"),
    ("收", "兼职", 200.0, -10, "帮老师装机"),
    ("支", "餐饮", 22.0, -8, "外卖"),
    ("支", "娱乐", 15.0, -5, "游戏月卡"),
    ("支", "餐饮", 14.5, -3, "食堂三餐"),
    ("支", "学习", 19.9, -2, "云服务器学生机"),
    ("收", "兼职", 150.0, -1, "电脑义诊感谢红包"),
    ("支", "餐饮", 15.5, 0, "食堂三餐"),
]


def seed(database=None, reset=False) -> None:
    target = Path(database or Path(__file__).parent / 'demo.db').resolve()
    if target == (Path(__file__).parent / 'app.db').resolve():
        raise SystemExit('拒绝重置 app.db：演示数据只使用独立的 demo.db。')
    if target.exists() and not reset:
        raise SystemExit('演示库已存在；确认重置请显式添加 --reset。')
    target.parent.mkdir(parents=True, exist_ok=True)
    app = create_app(SQLALCHEMY_DATABASE_URI='sqlite:///' + target.as_posix())
    with app.app_context():
        print("重置数据库……")
        db.drop_all()
        db.create_all()

        # 演示账号
        user = User(username=DEMO_USER)
        user.set_password(DEMO_PWD)
        db.session.add(user)
        db.session.flush()  # 拿 user.id

        # 笔记本
        notebooks = {}
        for i, name in enumerate(["课程笔记", "算法刷题", "项目开发", "生活随笔"]):
            nb = Notebook(user_id=user.id, name=name, sort=i)
            db.session.add(nb)
            notebooks[name] = nb
        db.session.flush()

        # 标签池（出现即创建，天然去重）
        tag_objs = {}

        def get_tag(name: str) -> Tag:
            if name not in tag_objs:
                t = Tag(user_id=user.id, name=name)
                db.session.add(t)
                tag_objs[name] = t
            return tag_objs[name]

        # 笔记
        note_objs = {}
        for nb_name, title, content, tags in NOTES:
            note = Note(
                user_id=user.id,
                notebook_id=notebooks[nb_name].id,
                title=title,
                content_md=content,
            )
            if title != '操作系统 · 进程与线程':
                note.content_html = clean_html(markdown.markdown(content, extensions=['extra']))
                note.content_md = parse_html(note.content_html).text
            for tg in tags:
                note.tags.append(get_tag(tg))
            db.session.add(note)
            note_objs[title] = note
        db.session.flush()

        # 前几篇演示置顶与回收站（演示对应功能）
        note_objs["动态规划 · 入门套路"].is_top = True
        note_objs["智汇笔记 · 架构决策记录"].is_top = True
        note_objs["宿舍网络抢修记"].is_deleted = True  # 回收站里有一篇
        source = note_objs['智汇笔记 · 架构决策记录']
        source.content_html += '<p>离线示例图片：</p><img alt="演示图片" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=">'
        db.session.add(Mindmap(user_id=user.id, note_id=source.id, title='智汇笔记架构导图', map_json=encode(generate(source))))

        # 待办
        today = date.today()
        for title, rel, done, note_title in TODOS:
            db.session.add(
                Todo(
                    user_id=user.id,
                    note_id=note_objs[note_title].id if note_title else None,
                    title=title,
                    due_date=today + timedelta(days=rel),
                    done=done,
                )
            )

        # 账单
        for type_, category, amount, rel, remark in BILLS:
            db.session.add(
                Bill(
                    user_id=user.id,
                    type=type_,
                    category=category,
                    amount=amount,
                    bill_date=today + timedelta(days=rel),
                    remark=remark,
                )
            )

        db.session.commit()

        print(f"完成：账号 {DEMO_USER}/{DEMO_PWD}")
        print(f'演示数据库：{target}')
        print(
            f"数据：笔记本 {len(notebooks)} 个 | 笔记 {Note.query.count()} 篇"
            f"（置顶 2 / 回收站 1）| 标签 {Tag.query.count()} 个"
            f"| 待办 {Todo.query.count()} 条 | 账单 {Bill.query.count()} 笔（跨 3 个月）"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='创建独立演示库，不操作 app.db')
    parser.add_argument('--database', help='演示数据库文件路径，默认 backend/demo.db')
    parser.add_argument('--reset', action='store_true', help='明确重置已有演示库')
    args = parser.parse_args()
    seed(args.database, args.reset)
