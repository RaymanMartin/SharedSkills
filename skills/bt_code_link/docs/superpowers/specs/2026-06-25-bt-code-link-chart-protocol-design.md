# bt_code_link 图表协议设计

## 问题定义

`bt_code_link` 的输出必须同时满足以下三种图表需求：

1. **跨层时序** — 谁先调谁，回调如何返回上层，层级边界如何推进
2. **分阶段执行** — 每条链路按执行阶段拆成若干独立流程图，不允许只出一张总图
3. **真实代码状态机** — 只画代码里真实存在的 `StateMachine`，且本次链路必须实际经过它

## 设计目标

1. 图表协议必须同时覆盖：
   - **跨层时序图**（`sequenceDiagram`）
   - **分阶段流程图**（≥ 2 张 `flowchart`）
   - **真实代码状态机图**（`stateDiagram-v2`，按需）
2. 状态机图只允许来源于代码里真实存在的状态机实现，且本次链路实际经过该状态机
3. 时序图参与者必须体现 BT 特有的层级划分：
   - `Settings → Framework API → BT Framework Module → BT Stack → BT HAL`

## 非目标

1. 不要求把所有 helper 调用都画进图里
2. 不要求对每个链路都画很多张图
3. 不要求把普通回调逻辑伪装成状态机图

## 图表协议规则

### 1. Mermaid 时序图（强制）

新增单独章节：

`# Mermaid 时序图`

要求：

1. 至少一张 `sequenceDiagram`
2. 专门描述跨层调用顺序
3. 参与者必须体现 BT 层级：
   - `Settings`
   - `Framework API`
   - `BT Framework Module`
   - `BT Service APK`（按需，如 Profile 连接链路）
   - `BT Stack (BTIF/BTA)`
   - `BT HAL`

这张图回答的是：

> 谁先调谁，回调怎么回来，跨层时序如何推进。

### 2. Mermaid 流程图必须按阶段拆分（强制）

`# Mermaid 分阶段流程图`

不再允许只有一张从头连到底的总图。

默认要求：

1. 至少两张 `flowchart`
2. 优先按执行阶段拆分

#### `bt_enable` 默认拆分阶段

1. **Settings / Framework 请求阶段**
   - Settings 蓝牙开关触发
   - `BluetoothEnabler`
   - `BluetoothAdapter.enable()`
   - Binder IPC 到 `AdapterService`

2. **BT Framework Module / StateMachine 仲裁阶段**
   - `AdapterService.enable()`
   - `AdapterStateMachine` 状态切换
   - `AdapterState: OffState → BleOnState → OnState`

3. **BT Stack / HAL 执行阶段**
   - `btifEnableBluetoothNative()` JNI
   - `btif_enable_bluetooth()`
   - `BTA_EnableBluetooth()`
   - `IBluetoothHci.initialize()` HAL AIDL

必要时可以额外加：

4. **状态回调返回阶段**

#### `bt_connect` 默认拆分阶段

1. **连接请求进入阶段**（Settings / `CachedBluetoothDevice`）
2. **Profile Service / StateMachine 仲裁阶段**（`A2dpService` / `HeadsetService`）
3. **BTIF / BTA Profile 执行阶段**（`btif_av_connect` / `BTA_AvOpen`）

#### `bt_scan` 默认拆分阶段

1. **扫描请求进入阶段**（`BluetoothAdapter.startDiscovery` / `BluetoothLeScanner.startScan`）
2. **BTIF / BTA 扫描执行阶段**（`btif_dm_start_discovery` / `BTA_DmSearch`）

### 3. 代码状态机图（真实状态机专用）

`# 代码状态机图`

规则：

1. 只画代码里真实存在的状态机
2. 必须是本次链路确实经过的状态机
3. 图标题中明确写出状态机类名

不再允许：

- 用分析链路抽象一个伪状态图
- 把普通状态回调当成完整状态机

## 各链路的真实状态机候选

### `bt_enable`

#### 1. `AdapterStateMachine extends StateMachine`（BT Framework Module）

适合画的内容：

- `OffState` 如何响应 `USER_TURN_ON` 事件
- `OffState → BleOnState → OnState` 的推进
- 关闭时 `OnState → BleOnState → OffState` 的回退
- 异常状态（超时、错误）如何处理

这是**蓝牙适配器主状态机**。

#### 2. `AdapterState`（新版 BT Module，如有）

部分 Android 版本中 `AdapterStateMachine` 被重构为 `AdapterState`，需要在实际源码中确认。

### `bt_connect`

#### 1. `A2dpStateMachine extends StateMachine`（BT Service APK）

适合画的内容：

- `Disconnected → Connecting → Connected`
- 断连时 `Connected → Disconnecting → Disconnected`
- 连接失败的退回路径

#### 2. `HeadsetStateMachine extends StateMachine`（BT Service APK）

适合画的内容：

- `Disconnected → Connecting → Connected`
- AT 命令处理状态
- SCO 连接状态

### `bt_scan`

- BLE 扫描路径通常在 `GattService` / `ScanManager` 内有状态跟踪
- Classic inquiry 通常通过 `btif_dm` 直接触发，状态回调较简单
- 若未命中真实 `StateMachine`，则不画状态机图，并在正文说明

## 状态机输出策略

升级后按如下策略输出：

1. 如果链路只命中一个真实状态机：
   - 输出这一张状态机图
2. 如果链路命中多个真实状态机：
   - 可以拆成：
     - `主状态机图`（`AdapterStateMachine`）
     - `Profile 状态机图`（`A2dpStateMachine` / `HeadsetStateMachine`）
3. 如果链路没有真实状态机命中：
   - 不画状态机图
   - 并在文档中说明：当前链路未命中真实状态机实现

## 文档章节调整

图表相关章节按以下顺序输出：

1. `# Mermaid 时序图`（跨层调用顺序）
2. `# Mermaid 分阶段流程图`（执行过程分阶段）
3. `# 代码状态机图`（真实状态机流转，按需）

## 验收标准

1. 不再只有一张线性总流程图
2. 必须包含至少一张时序图，且参与者体现 BT 层级
3. `bt_enable` 至少能拆出 `BT Stack / HAL 执行阶段`
4. 状态机图只引用代码里真实存在的状态机
5. 不再把纯分析链路伪装成状态机图

## 已确认决策

1. 状态机图只画真实代码状态机
2. `bt_enable` 至少考虑 `AdapterStateMachine`
3. `bt_connect` 至少考虑 `A2dpStateMachine` / `HeadsetStateMachine`
4. 图表协议采用"时序图 + 分阶段流程图 + 真实状态机图"的组合
