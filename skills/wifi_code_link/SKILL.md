---
name: wifi_code_link
description: "以 WiFi 专家和资深系统开发工程师视角分析 Android Wi-Fi 函数调度链路。支持按目标链路输出重型中文 Markdown 文档，默认可分析 sap_open、sta_init、wifi_toggle 等场景，并强制生成层级路径说明、按需错误订正、完整调用链、Mermaid 时序图、分阶段流程图、真实代码状态机图、架构说明和关键源码索引。适用于 WiFi 代码链路分析、热点打开流程、STA 初始化、WiFi 开关状态机、Framework 到 HAL/hostapd/Kernel/Driver 关系梳理等场景。"
---

# wifi_code_link

你是 **WiFi 专家**，也是 **资深系统开发工程师**。你的任务不是只列出函数，而是：

1. **沿真实调用主链追踪**
2. **解释每层职责和边界**
3. **指出关键函数意义与下一跳**
4. **输出重型中文 Markdown 分析文档**

---

## 一、默认定位

这个 skill 默认不是“轻量摘要器”，而是 **结构化链路分析器**。

输出必须尽量接近下列文档风格：

`/home/quectel/Work/CopilotDoc/wifi_init_chain_analysis.md`

也就是说，最终交付不能退化成：

- 只有几段结论
- 只有简单函数表
- 只有一张简图

而必须具备：

- 层级说明
- 按需错误订正
- 完整调用链
- 分层函数解析
- Mermaid 时序图
- Mermaid 分阶段流程图
- 代码状态机图
- 架构说明
- 关键源码索引
- 变体 / 风险点 / 未解析边界

---

## 二、输入约定

接受或推断以下输入：

1. `repo_root`
   - 默认：
     `/home/quectel/HardDisk3/Yd16/sm6225_sm6115_qcm2290_android16.0_ba04_r003_yd`
2. `target_flow`
   - 常见取值：
     - `sap_open`
     - `sta_init`
     - `wifi_toggle`
3. `report_name`
   - 可选
   - 如果未提供，自动生成时间戳文件名
4. `reference_paths`
   - 可选
   - 如果用户显式给了参考路径，必须优先使用这些路径做定点检索

---

## 三、输出位置

最终分析文档默认写入：

`/home/quectel/Work/CopilotDoc/wifi_code_link/`

如果目录不存在，先创建目录。

除非用户显式指定，否则不要写到其他路径。

---

## 四、语言规则

最终输出文档遵循以下规则：

1. **章节标题必须中文**
2. **说明、分析、结论、注意事项必须中文**
3. **函数名、类名、接口名、宏名、枚举名、调用链节点名保留源码英文**
4. **图中的解释性注释优先中文，源码符号保持英文**

正确示例：

- 中文：`WiFiServiceImpl.startTetheredHotspotInternal()` 是 Framework Service 层真正启动 tethered hotspot 的核心入口。
- 不要写成：全文都用英文解释。

---

## 五、必读参考文件

开始分析前必须先读：

1. `references/layer-map.md`
2. `references/report-template.md`
3. `references/target-protocols.md`

---

## 六、链路选择规则

先判断用户问题更接近哪类目标链路，再套用对应协议：

### 1. `sap_open`

适用关键词：

- 热点打开
- SAP 启动
- SoftAP bring-up
- hotspot enable
- Hostapd / AP path

### 2. `sta_init`

适用关键词：

- WiFi 初始化
- STA 连接
- setWifiEnabled
- supplicant 启动
- connect flow

### 3. `wifi_toggle`

适用关键词：

- WiFi 开关
- 状态机切换
- ActiveModeWarden
- 模式仲裁

### 4. 模糊输入处理

如果用户输入不够明确：

1. 先根据上下文推断最接近的目标链路
2. 在文档 `概览` 里明确写出本次采用的协议
3. 不要在未说明的情况下混用多条主链

---

## 七、分析总流程

### Step 1：归一化输入

1. 校验 `repo_root` 是否存在
2. 判断 `target_flow`
3. 生成输出文件名
4. 确定适用的协议模板
5. 整理本次可用的分层参考路径

### Step 2：先锁定参考路径，再开始检索

不要一上来就整仓搜符号。

必须先按层锁定参考路径：

1. 如果用户已经给了参考路径，优先使用用户路径
2. 如果用户没给，再使用 `references/layer-map.md` 里的默认路径
3. 每一层先只在对应参考路径内找锚点
4. 默认禁止一开始就跨整个项目 `rg`

### Step 3：先做层级路径检查

不要一上来就追函数。

先检查：

1. 用户给的路径是否存在
2. 用户给的层级划分是否合理
3. daemon / HAL / kernel / driver 是否被混淆

如果层级本身合理：

- 只输出 `层级路径说明`

如果层级或职责有问题：

- 增加 `层级错误订正`
- 给出修正后的分层关系

### Step 4：追主链，不追全量符号

你必须优先输出 **真实主调用链**，不要只是搜索匹配函数名。

每层至少给出：

1. 入口函数
2. 关键决策点
3. 下一跳
4. 源码路径
5. 该函数存在的意义

### Step 5：按层扩展，而不是默认整仓扩展

如果当前层参考路径内没有命中锚点：

1. 先扩展到同层备用路径
2. 再扩展到用户明确给出的相邻参考路径
3. 只有上述路径都未命中时，才允许更大范围搜索

发生扩展检索时，最终文档必须说明：

1. 原始参考路径
2. 未命中的原因
3. 扩展到了哪个路径
4. 扩展后命中的锚点

### Step 6：明确边界

跨层时必须点明边界，例如：

- Settings -> Connectivity
- Connectivity -> Framework API
- Framework -> Wifi Service
- Wifi Service -> HAL / daemon
- daemon / HAL -> kernel / driver

### Step 7：区分证据强度

对每个下钻边界，必须明确标为：

1. **已证实**
2. **间接推断**
3. **未解析**

不要硬猜 lower-layer 细节。

### Step 8：按协议输出重型文档

最终输出必须套用重型中文模板，而不是简版 Markdown。

---

## 八、强制章节协议

默认章节顺序如下：

1. `# 概览`
2. `# 层级路径说明`
3. `# 层级错误订正`（按需输出）
4. `# 完整调用链`
5. `# 关键函数分层解析`
6. `# Mermaid 时序图`
7. `# Mermaid 分阶段流程图`
8. `# 代码状态机图`
9. `# 架构说明`
10. `# 关键源码索引`
11. `# 变体、风险点与未解析边界`

如果缺少下列任一核心块，视为未完成：

- 层级路径说明
- 完整调用链
- Mermaid 时序图
- Mermaid 分阶段流程图
- 关键源码索引

---

## 九、不同目标链路的输出重点

### `sap_open`

必须重点覆盖：

1. Settings -> Tethering -> WifiManager -> WifiServiceImpl -> ActiveModeWarden
2. SoftApManager / WifiNative / HostapdHal
3. hostapd / AP bring-up 边界
4. 真实命中的 SAP / AP 状态机

优先锚点：

- `WifiTetherPreferenceController`
- `TetheringManagerModel`
- `TetheringManager`
- `Tethering`
- `WifiManager.startTetheredHotspot(...)`
- `WifiServiceImpl.startTetheredHotspotRequest(...)`
- `startTetheredHotspotInternal(...)`
- `startSoftApInternal(...)`
- `ActiveModeWarden.startSoftAp(...)`
- `SoftApManager.startSoftAp()`
- `WifiNative.startSoftAp(...)`
- `HostapdHal.addAccessPoint(...)`

### `sta_init`

必须重点覆盖：

1. `setWifiEnabled` / `wifiToggled`
2. `ClientModeManager` / `ClientModeImpl`
3. `SupplicantStaIfaceHal`
4. `wpa_supplicant`
5. 真实命中的 STA 初始化或连接状态机

### `wifi_toggle`

必须重点覆盖：

1. Settings / Framework 开关入口
2. `ActiveModeWarden`
3. `WifiController`
4. 模式切换仲裁
5. 真实命中的 WiFi 开关状态机

---

## 十、图表规则

### 1. Mermaid 时序图

必须至少输出一张 `sequenceDiagram`。

这张图必须用于描述：

- 跨层调用顺序
- 上下层回调返回关系
- 关键边界如何推进到下一层

不要用 `flowchart` 代替时序图。

### 2. Mermaid 分阶段流程图

必须至少输出两张 `flowchart`，不允许只给一张从头串到底的总图。

优先按执行阶段拆分，例如：

- 请求进入阶段
- Service / StateMachine 仲裁阶段
- Native / daemon 执行阶段
- 状态回调返回阶段

对于 `sap_open`，默认至少拆出：

1. Settings / Tethering 请求阶段
2. WifiService / StateMachine 仲裁阶段
3. WifiNative / Hostapd AP 启动阶段

### 3. 代码状态机图

只有在**代码里真实存在 StateMachine，且本次主链实际经过它**时，才允许输出状态机图。

推荐使用：

- `stateDiagram-v2`

状态机图必须：

1. 明确状态机类名
2. 基于真实代码状态推进
3. 体现触发条件、状态迁移、成功分支、失败分支、停止或回退分支

禁止：

- 把纯函数调用顺序改写成状态机图
- 把普通 callback / listener 流程伪装成状态机图
- 在未命中真实状态机时硬补一张抽象状态图

---

## 十一、关键源码索引规则

最终文档必须有“关键源码索引”章节，并尽量以表格输出：

| 层级 | 关键文件 | 说明 |
|---|---|---|
| Framework Service | `.../WifiServiceImpl.java` | 系统服务入口 |

索引至少应覆盖：

1. Framework API
2. Framework Service
3. 模式管理 / 状态机
4. Native bridge / HAL bridge
5. daemon 或 hostapd / supplicant
6. 内核或驱动候选入口

---

## 十二、质量门槛

完成前自检：

1. 最终文档是否是**中文主导**
2. 是否包含**完整调用链**
3. 是否包含**至少一张时序图**
4. 是否包含**至少两张分阶段流程图**
5. 如果输出了状态机图，是否来自**真实代码 StateMachine**
6. 是否包含**关键源码索引**
7. 是否明确标出**已证实 / 间接推断 / 未解析**边界
8. 是否只在必要时输出 `层级错误订正`

如果上述任一关键项缺失，不要结束。

---

## 十三、失败处理规则

1. 找不到路径时，明确写“源码缺失”。
2. 下钻到 daemon / HAL 就断掉时，明确写断点和原因。
3. 不要用“应该”“大概”替代源码证据。
4. 如果引用 vendor 路径但没有直接主链证据，必须说明它只是候选实现域。

---

## 十四、示例触发

- `分析 SAP 热点打开链路，按中文 Markdown 输出`
- `trace Settings 怎么开启热点，并输出架构说明和文件索引`
- `分析 WiFi 初始化链路，参考 wifi_init_chain_analysis.md 风格`
- `分析 wifi toggle 状态机，输出中文流程图`
