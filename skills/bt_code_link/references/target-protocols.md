# bt_code_link 目标链路协议

本文件定义不同 `target_flow` 对应的重点章节要求。

---

## 一、`bt_enable`

### 必须回答的问题

1. Settings 是通过哪个类触发蓝牙开关的？
2. `BluetoothAdapter.enable()` 如何通过 Binder 到达 `AdapterService`？
3. `AdapterService` 到 `AdapterStateMachine` 的主链是什么？
4. BT Stack BTIF 层与 HAL 层的边界在哪里？
5. 最深可证实边界到哪一层？

### 必须出现的图

1. BT Enable 跨层时序图（Settings → Framework → BT Module → Stack → HAL）
2. Settings / Framework 请求阶段流程图
3. BT Framework Module / StateMachine 仲裁阶段流程图
4. BT Stack / HAL 执行阶段流程图
5. 如果命中真实状态机，输出真实状态机图

### 状态机候选

1. `AdapterStateMachine`（主适配器状态机）
2. `AdapterState`（如果采用新版 AdapterState 实现）

### 必须出现的源码索引重点

- `BluetoothEnabler` / `BluetoothDashboardFragment`
- `BluetoothAdapter`
- `BluetoothManagerService` / `AdapterService`
- `AdapterStateMachine` / `AdapterState`
- `btif_core.cc` / `btif_enable_bluetooth`
- `bta_dm_act.cc` / `BTA_EnableBluetooth`
- `IBluetoothHci.aidl` / HAL 初始化入口

---

## 二、`bt_connect`

### 必须回答的问题

1. 用户发起连接的入口函数是什么（Settings / 系统 UI）？
2. `CachedBluetoothDevice.connect()` 如何路由到具体 Profile？
3. `A2dpService` / `HeadsetService` 的 Profile 状态机如何接收 CONNECT 消息？
4. BTIF Profile 层如何向 BTA 发送连接请求？
5. 最深可证实边界到哪一层？

### 必须出现的图

1. BT Connect 跨层时序图
2. Settings / 上层连接请求阶段流程图
3. Profile Service / StateMachine 仲裁阶段流程图
4. BTIF / BTA Profile 执行阶段流程图
5. 如果命中真实状态机，输出真实状态机图

### 状态机候选

1. `A2dpStateMachine`（A2DP Profile 连接状态机）
2. `HeadsetStateMachine`（HFP Profile 连接状态机）
3. `HeadsetClientStateMachine`（HFP Client 状态机）
4. `GattService` 中的 GATT 连接状态机（GATT 路径时）

### 必须出现的源码索引重点

- `CachedBluetoothDevice`
- `BluetoothDevice`
- `A2dpService` / `HeadsetService`
- `A2dpStateMachine` / `HeadsetStateMachine`
- `btif_av.cc` / `btif_hf.cc`
- `bta_av_act.cc` / `bta_hf_act.cc`

---

## 三、`bt_scan`

### 必须回答的问题

1. 蓝牙扫描 / 设备发现的入口函数是什么？
2. Classic BT 的 `startDiscovery()` 与 BLE 的 `startLeScan()` / `BluetoothLeScanner.startScan()` 是否走同一条链路？
3. `AdapterService.startDiscovery()` 如何到达 BTIF 层？
4. BTA 层的 `BTA_DmSearch()` 如何触发 Inquiry 或 LE scan？
5. 最深可证实边界到哪一层？

### 必须出现的图

1. BT Scan 跨层时序图
2. 扫描请求进入阶段流程图（Classic BT）
3. BTIF / BTA 扫描执行阶段流程图
4. 如果有 BLE scan 路径，额外输出 BLE scan 对比流程图
5. 如果命中真实状态机，输出真实状态机图

### 状态机候选

- 如果分析 BLE scan，注意 `ScanManager` / `GattService` 内部的扫描状态机

### 必须出现的源码索引重点

- `BluetoothAdapter`（`startDiscovery`）
- `BluetoothLeScanner`（`startScan`）
- `AdapterService`（`startDiscovery`）
- `btif_dm.cc`（`btif_dm_start_discovery`）
- `bta_dm_act.cc`（`BTA_DmSearch`）
- BLE scan 路径：`GattService` / `ScanManager`

---

## 四、协议通用规则

1. 章节顺序统一遵循 `report-template.md`。
2. 只切换具体内容，不切换整体文风。
3. 如果某条链路跨越多个子阶段，应拆成多个流程图而不是塞进一个大图。
4. 状态机图只允许画真实代码 `StateMachine`，且该状态机必须被本次主链实际命中。
5. 如果用户问题明显要求"从 Settings 开始"，就优先从 UI 或上层入口追起，不要直接从 BT Stack 中层切入。
6. 时序图参与者必须体现层级划分：
   - `Settings` → `Framework API` → `BT Framework Module` → `BT Stack` → `BT HAL`
