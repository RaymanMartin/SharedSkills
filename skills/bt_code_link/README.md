# bt_code_link

**BT（蓝牙）函数调度链路分析工具**

以 BT 专家和资深系统开发工程师视角，分析 Android Bluetooth 函数调度链路。支持按目标链路输出重型中文 Markdown 文档。

---

## 支持的分析链路

| 链路标识 | 说明 | 典型触发关键词 |
|---|---|---|
| `bt_enable` | 蓝牙开关流程（从 Settings 到 BT HAL） | 蓝牙开关、BT 初始化、AdapterService、蓝牙状态机 |
| `bt_connect` | 蓝牙设备连接流程（A2DP / HFP / GATT） | 蓝牙连接、A2DP、HFP、BluetoothDevice.connect |
| `bt_scan` | 蓝牙扫描 / 设备发现流程 | 蓝牙扫描、startDiscovery、BLE scan |

---

## 默认层级

```
Settings / App 触发层
    ↓
Framework API 层（android.bluetooth）
    ↓
BT Framework Module 服务层（packages/modules/Bluetooth）
    ↓
BT Service APK 层（commonsys/packages/apps/Bluetooth）[Profile 实现]
    ↓
BT Stack BTIF / BTA / Stack 层（commonsys/system/bt）
    ↓
BT HAL 接口层（hardware/interfaces/bluetooth）
    ↓
BT Controller / Firmware 层（HCI）
```

---

## 默认路径

| 层级 | 默认路径 |
|---|---|
| Settings | `qssi16/packages/apps/Settings/src/com/android/settings/bluetooth/` |
| Framework API | `qssi16/frameworks/base/core/java/android/bluetooth/` |
| BT Framework Module | `qssi16/packages/modules/Bluetooth/` |
| BT Service APK | `target/vendor/qcom/opensource/commonsys/packages/apps/Bluetooth/` |
| BT HAL | `target/hardware/interfaces/bluetooth/` |
| BT Stack | `target/vendor/qcom/opensource/commonsys/system/bt/` |

---

## 输出位置

`/home/quectel/Work/CopilotDoc/bt_code_link/`

---

## 使用示例

```
分析蓝牙开关链路，按中文 Markdown 输出
trace Settings 怎么开启蓝牙，并输出架构说明和文件索引
分析 BT Enable 链路，输出时序图和状态机图
分析 A2DP 连接链路，输出完整调用链
分析蓝牙扫描链路，输出中文流程图
```

---

## 输出文档结构

每次分析都输出重型中文 Markdown，包含：

1. 概览（链路说明、入口、深度边界）
2. 层级路径说明
3. 层级错误订正（按需）
4. 完整调用链
5. 关键函数分层解析
6. Mermaid 时序图（跨层调用顺序）
7. Mermaid 分阶段流程图（≥ 2 张）
8. 代码状态机图（仅限真实 StateMachine）
9. 架构说明
10. 关键源码索引
11. 变体、风险点与未解析边界
