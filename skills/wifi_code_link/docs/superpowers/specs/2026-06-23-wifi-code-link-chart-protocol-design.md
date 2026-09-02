# wifi_code_link 图表协议修正设计

## 问题定义

在上一轮升级后，`wifi_code_link` 已经具备中文主导、重型章节和目标链路自适应能力，但图表协议还有两个明显问题：

1. **Mermaid 流程图仍然偏单调**
   - 只有从入口串到出口的一条主线
   - 没有把执行过程拆成关键阶段
   - 没有单独输出跨层时序图
2. **状态机图不够“代码真实”**
   - 当前状态机图是按分析链路抽象出来的状态流转
   - 但用户真正需要的是：**代码里实际存在的 StateMachine 的状态流转图**
   - 如果分析链路没有命中真实代码状态机，不应硬画“状态机分析”

## 升级目标

1. 图表协议必须同时覆盖：
   - **跨层时序**
   - **分阶段执行**
   - **真实代码状态机**
2. `状态机图` 只允许来源于：
   - 代码里真实存在的状态机实现
   - 且本次分析链路实际经过该状态机
3. `sap_open` 这类链路必须把 `WifiNative` / `Hostapd` 等关键执行阶段单独拆出来，而不是只放在一张总图里。

## 非目标

1. 不要求把所有 helper 调用都画进图里。
2. 不要求对每个链路都画很多张图。
3. 不要求把普通回调逻辑伪装成状态机图。

## 设计结论

采用 **中度升级图表协议**：

1. 保留当前重型文档骨架
2. 重点修改图表章节协议
3. 强化“真实 StateMachine 才能画状态机图”的规则

## 方案比较

### 方案 1：轻改图表协议

只补一张 `sequenceDiagram`，并略微拆细原流程图。

**优点**
- 改动小

**缺点**
- 状态机真实性约束仍不够硬
- 难以彻底解决“图太直、阶段感不强”的问题

### 方案 2：中度升级图表协议（本次选择）

在现有重型协议上新增三条硬规则：

1. `sequenceDiagram` 强制输出
2. `flowchart` 必须按阶段拆分
3. `stateDiagram-v2` 只允许画真实代码状态机

**优点**
- 能精准解决当前两类不满意点
- 不需要额外引入太多新文件

**缺点**
- `SKILL.md`、模板和目标协议都需要同步更新

### 方案 3：重构整套图表子协议

把图表规则单独抽成新的大 reference 文件，对每条链路定义完整图表族。

**优点**
- 最完整

**缺点**
- 维护成本偏高
- 当前问题不一定需要走到这一步

## 核心修正规则

### 1. Mermaid 时序图变为强制项

新增单独章节：

`# Mermaid 时序图`

要求：

1. 至少一张 `sequenceDiagram`
2. 专门描述跨层调用顺序
3. 适合表现：
   - Settings → Connectivity → Framework → WifiService
   - 回调从 lower-layer 返回上层

这张图回答的是：

> 谁先调谁，回调怎么回来，跨层时序如何推进。

### 2. Mermaid 流程图必须按阶段拆分

`# Mermaid 分阶段流程图`

不再允许只有一张从头连到底的总图。

默认要求：

1. 至少两张 `flowchart`
2. 优先按执行阶段拆分

对于 `sap_open`，默认拆分成以下阶段：

1. **Settings / Tethering 请求阶段**
   - Settings UI 开关
   - `TetheringManagerModel`
   - `TetheringManager`
   - `Tethering`
2. **WifiService / StateMachine 仲裁阶段**
   - `WifiManager`
   - `WifiServiceImpl`
   - `ActiveModeWarden.WifiController`
3. **WifiNative / Hostapd AP 启动阶段**
   - `SoftApManager`
   - `WifiNative`
   - `HostapdHal`
   - `hostapd`

必要时可以额外加：

4. **状态回调返回阶段**

### 3. 代码状态机图改为“真实状态机专用”

原来的 `状态机图` 章节升级为：

`# 代码状态机图`

规则：

1. 只画代码里真实存在的状态机
2. 必须是本次链路确实经过的状态机
3. 图标题中明确写出状态机类名

不再允许：

- 用分析链路抽象一个伪状态图
- 把普通状态回调当成完整状态机

## `sap_open` 的真实状态机候选

在当前源码树中，这条链路至少命中以下两个真实状态机：

### 1. `ActiveModeWarden.WifiController extends StateMachine`

适合画的内容：

- `CMD_SET_AP` 到达后
- `DisabledState` 如何处理热点启动请求
- 何时转入 `EnabledState`
- 特殊模式（如 emergency mode）如何拒绝或丢弃启动

这是**模式仲裁状态机**。

### 2. `SoftApManager.SoftApStateMachine extends StateMachine`

适合画的内容：

- `IdleState`
- `WaitingForDriverCountryCodeChangedState`
- `StartedState`
- 启动失败时如何回退

这是**热点执行状态机**。

## 状态机输出策略

升级后按如下策略输出：

1. 如果链路只命中一个真实状态机：
   - 输出这一张状态机图
2. 如果链路命中多个真实状态机：
   - 可以拆成：
     - `主状态机图`
     - `执行状态机图`
3. 如果链路没有真实状态机命中：
   - 不画状态机图
   - 并在文档中说明：
     - 当前链路未命中真实状态机实现

## 文档章节调整

图表相关章节改成以下顺序：

1. `# Mermaid 时序图`
2. `# Mermaid 分阶段流程图`
3. `# 代码状态机图`

其中：

- 时序图回答“跨层调用顺序”
- 分阶段流程图回答“执行过程被拆成哪些阶段”
- 代码状态机图回答“真实状态机如何推进”

## 实现影响面

本次修改主要影响：

1. `SKILL.md`
   - 增加图表强制规则
   - 增加真实状态机限制
2. `references/report-template.md`
   - 图表章节改名并细化
3. `references/target-protocols.md`
   - 为 `sap_open` / `sta_init` / `wifi_toggle` 增加状态机候选与阶段切分要求

## 验收标准

升级后，`wifi_code_link` 输出应满足：

1. 不再只有一张线性总流程图
2. 必须包含至少一张时序图
3. `sap_open` 至少能拆出 `WifiNative / Hostapd AP 启动阶段`
4. 状态机图只引用代码里真实存在的状态机
5. 不再把纯分析链路伪装成状态机图

## 已确认决策

1. 状态机图只画真实代码状态机
2. `sap_open` 至少考虑 `ActiveModeWarden.WifiController` 与 `SoftApManager.SoftApStateMachine`
3. 图表协议升级采用“时序图 + 分阶段流程图 + 真实状态机图”的组合
