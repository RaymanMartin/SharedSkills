# bt_code_link 分层说明与按需订正规则

本文件定义 `bt_code_link` 在输出链路分析时，如何解释层级、如何判断用户给出的路径/归属是否有误，以及何时需要输出"层级错误订正"。

---

## 一、标准层级顺序

默认按以下顺序组织：

1. **Settings / App 触发层**
2. **Framework API 层**
   - `android.bluetooth.*` 公开 API
   - `BluetoothAdapter`、`BluetoothManager`、`BluetoothDevice`
3. **BT Framework Module 服务层**
   - `AdapterService`、Profile 服务（`A2dpService`、`HeadsetService` 等）
   - `AdapterStateMachine` / `AdapterState`
4. **BT Service APK 层（Profile 实现）**
   - commonsys vendor BT APK
   - Profile 状态机（`A2dpStateMachine`、`HeadsetStateMachine` 等）
5. **BT Stack BTIF / BTA / Stack 层**
   - `btif_*` — Java/JNI 桥接层
   - `bta_*` — BT Application 层
   - `stack/*` — BT 协议栈实现
6. **BT HAL 接口层**
   - AIDL / HIDL 接口定义
   - `IBluetoothHci`、`IBluetoothHciCallbacks`
7. **Vendor HAL 实现层**
   - HAL 具体实现（vendor 提供）
8. **BT Controller / Firmware 层**
   - HCI 通信
   - 固件初始化

注意：

- `BT Stack`（system/bt / commonsys/system/bt）**不是 HAL**，而是 userspace 协议栈
- `BT Service APK` 与 `BT Framework Module` 是不同层：APK 侧重 Profile 实现，Module 侧重系统服务
- `BT HAL` 接口定义（hardware/interfaces）与 HAL 具体实现是两回事
- `BT Controller / Firmware` 属于硬件域，需与 HAL 层区分

---

## 二、默认锚点路径

### 1. Settings / 上层触发

- `qssi16/packages/apps/Settings/src/com/android/settings/bluetooth/`
- 备用：`qssi16/packages/apps/Bluetooth/`（若有）

### 2. Framework API

- `qssi16/frameworks/base/core/java/android/bluetooth/`
- 核心类：`BluetoothAdapter.java`、`BluetoothManager.java`、`BluetoothDevice.java`

### 3. BT Framework Module

- `qssi16/packages/modules/Bluetooth/`
- 服务端：`qssi16/packages/modules/Bluetooth/service/`
- 框架层：`qssi16/packages/modules/Bluetooth/framework/`
- Android 层：`qssi16/packages/modules/Bluetooth/android/`

### 4. BT Service APK（Profile 实现）

- `target/vendor/qcom/opensource/commonsys/packages/apps/Bluetooth/`
- 关键目录：`src/com/android/bluetooth/`

### 5. BT HAL 接口层

- `target/hardware/interfaces/bluetooth/`
- 关键 AIDL：`IBluetoothHci.aidl`、`IBluetoothHciCallbacks.aidl`

### 6. BT Stack

- `target/vendor/qcom/opensource/commonsys/system/bt/`
- 关键子目录：
  - `btif/` — BTIF 桥接层
  - `bta/` — BTA 应用层
  - `stack/` — BT 协议栈
  - `hci/` — HCI 层
  - `gd/` — Gabeldorsche 新架构（如有）

### 7. Vendor HAL 实现

- `target/vendor/qcom/opensource/commonsys/system/bt/vendor_libs/` 或 vendor 特定目录

---

## 三、已知主链锚点

### `bt_enable`

1. `BluetoothEnabler.setBluetoothEnabled()` / `BluetoothDashboardFragment`
2. `BluetoothAdapter.enable()`
3. `IBluetoothManager.enable()` → Binder → `BluetoothManagerService.enable()`
4. `AdapterService.enable()`
5. `AdapterStateMachine` 接收 `BLE_TURN_ON` / `USER_TURN_ON` 消息
6. `AdapterState` 状态切换（`OffState` → `BleOnState` → `OnState`）
7. `btifEnableBluetoothNative()` → JNI → `btif_enable_bluetooth()`
8. `BTA_EnableBluetooth()` → BT Stack 初始化
9. `IBluetoothHci.initialize()` / `open()` → HAL 层

### `bt_connect`

1. `CachedBluetoothDevice.connect()` / `BluetoothDevice.connect()`
2. Profile Manager 选择（`A2dpProfile.connect()` / `HfpProfile.connect()`）
3. `A2dpService.connect()` / `HeadsetService.connect()`
4. Profile StateMachine 事件（`CONNECT` 消息）
5. `btif_av_connect()` / `btif_hf_connect()` → JNI
6. `BTA_AvOpen()` / `BTA_HfOpen()` → BTA 层
7. 协议栈连接建立

### `bt_scan`

1. `BluetoothAdapter.startDiscovery()` / `BluetoothLeScanner.startScan()`
2. `IBluetoothManager` Binder → `AdapterService.startDiscovery()`
3. `btif_dm_start_discovery()` → JNI
4. `BTA_DmSearch()` → BTA 层
5. Inquiry / LE scan 流程

---

## 四、何时只输出"层级路径说明"

如果满足以下条件，则只输出"层级路径说明"，不要强行写"错误订正"：

1. 用户给的路径基本存在
2. 用户给的层级顺序大体正确
3. 没有把 BT Stack / HAL / Controller 明显混淆
4. 只是细节不完整，但不构成错误归属

这时应输出：

- 各层路径
- 各层职责
- 本次实际追踪使用了哪些路径

---

## 五、何时必须输出"层级错误订正"

如果出现以下情况，则必须新增 `层级错误订正` 小节：

1. 路径不存在或层级归属错误
2. 把 `BT Stack`（userspace 协议栈）当成 HAL
3. 把 `BT Service APK` 与 `BT Framework Module` 混为一谈
4. 把 HAL 接口定义与 HAL vendor 实现混为一层
5. 把 `BT Controller` 与 `BT HAL` 放在同一层

输出订正时，必须包含：

1. 用户原始层级或路径
2. 错误点
3. 正确归属
4. 修正后的层级结构

---

## 六、边界说明规则

输出时必须解释这些关键边界：

1. **Framework API vs BT Framework Module Service**
   - 公开 API（`android.bluetooth.*`）与系统服务实现（`AdapterService`）的 Binder IPC 边界
2. **BT Framework Module vs BT Service APK**
   - Module 提供系统服务框架，APK 实现具体蓝牙 Profile（如 A2DP、HFP）
3. **BT Framework Module vs BT Stack**
   - Java 层通过 JNI 调用 BTIF 层，进入 native BT 协议栈
4. **BT Stack vs BT HAL**
   - BT Stack 是 userspace 协议栈；BT HAL 是与 controller 通信的硬件抽象层
5. **BT HAL vs BT Controller**
   - HAL 是 AIDL/HIDL 接口；Controller 是蓝牙芯片固件

---

## 七、检索优先级规则

分析时必须遵循以下顺序：

1. **优先用户给定路径**
   - 如果用户已经给了参考路径，就先只在这些路径内检索
2. **其次默认分层路径**
   - 如果用户没给，才使用本文件中的默认路径
3. **先同层主路径，再同层备用路径**
   - 不要跨层直接扩展
4. **最后才允许更大范围搜索**
   - 默认禁止一开始就整仓搜索

如果发生扩展检索，最终文档必须写明：

1. 原始路径
2. 为什么没命中
3. 扩展路径
4. 命中的关键锚点

---

## 八、路径变体规则

1. 如果同时存在 `qssi16/...` 与 `target/...` 同名 Java 文件：
   - 优先用 `qssi16/...` 作为 Framework 主分析路径
2. 如果 BT Stack 在 `target/vendor/qcom/opensource/commonsys/system/bt/` 更完整：
   - 可以直接引用此路径
3. 如果 vendor 或 HAL vendor 目录存在但本次主链没有直接证据：
   - 仍可列入"关键源码索引"
   - 但必须标注为"候选实现域"或"间接关联层"

---

## 九、分层输出最低要求

每一层至少输出：

1. 入口点
2. 关键函数
3. 下一跳
4. 职责说明
5. 证据路径
