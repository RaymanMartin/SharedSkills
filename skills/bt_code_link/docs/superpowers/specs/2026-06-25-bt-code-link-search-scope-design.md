# bt_code_link 路径收敛与定点检索设计

## 问题定义

`bt_code_link` 在执行链路分析时，必须遵守以下两条约束：

1. **先按用户给定参考路径定点检索**
   - 用户已明确给出各层参考路径，必须优先在这些路径内检索，不能默认整仓搜索
2. **只在当前层参考路径找不到锚点时，才允许按层扩展**
   - 扩展必须可解释：说明原始路径、未命中原因、扩展路径、命中锚点

## 设计目标

1. 将用户给定的参考路径固化为默认检索域
2. 把检索策略改成：
   - **先按用户给定参考路径定点检索**
   - **只在当前层参考路径找不到锚点时，才允许按层扩展**
   - **默认禁止整仓搜索作为第一选择**
3. 让最终报告能说明：
   - 本次实际用了哪些参考路径
   - 哪些层发生了扩展检索
   - 为什么需要扩展

## 非目标

1. 不要求完全禁止扩展检索
2. 不要求为每个厂商平台都单独定一套搜索协议
3. 不要求把所有路径都写成绝对唯一，不处理源码树差异

## 设计结论

采用 **路径收敛 + 定点优先检索**：

1. 明确各层默认参考路径（来自用户给定）
2. 强制"参考路径优先、按层扩展、禁止默认整仓搜索"

## 用户给定参考路径（默认检索域）

| 层级 | 路径 | 说明 |
|---|---|---|
| Settings | `qssi16/packages/apps/Settings` | Settings 蓝牙相关 UI |
| Framework | `qssi16/frameworks` | Android Framework（BluetoothAdapter 等） |
| BT Framework Module | `qssi16/packages/modules/Bluetooth` | BT 核心系统服务模块 |
| BT Service APK | `target/vendor/qcom/opensource/commonsys/packages/apps/Bluetooth` | Profile 实现 APK（vendor） |
| BT HAL | `target/hardware/interfaces/bluetooth` | BT HAL AIDL/HIDL 接口 |
| BT Stack | `target/vendor/qcom/opensource/commonsys/system/bt` | BT 协议栈 native 实现 |

检索时先在上述路径内定点检索，未命中时再扩展。

## 核心检索规则

### 1. 参考路径优先

对任一链路分析，必须遵循以下顺序：

1. 根据当前目标层，先定位对应参考路径
2. 只在该参考路径内检索锚点函数、类、状态机、关键文件
3. 如果未命中，再扩展到：
   - 同层的备用路径
   - 用户明确提供的相邻参考路径
4. 只有在上述路径都未命中时，才允许更大范围搜索

默认禁止：

- 一开始就整仓 `rg`
- 未分层就跨所有目录搜符号

### 2. 扩展检索必须可解释

如果发生路径扩展，文档中必须说明：

1. 原始参考路径
2. 为什么在原路径中未命中
3. 扩展到了哪个路径
4. 扩展后的命中锚点是什么

### 3. 参考路径按层映射（定点检索顺序）

1. **Settings / 上层触发**
   - 主路径：`qssi16/packages/apps/Settings/src/com/android/settings/bluetooth/`
   - 备用：`qssi16/packages/apps/Settings/src/com/android/settings/connected_devices/`

2. **Framework API**
   - 主路径：`qssi16/frameworks/base/core/java/android/bluetooth/`
   - 备用：`qssi16/frameworks/base/services/core/java/com/android/server/BluetoothManagerService.java`

3. **BT Framework Module**
   - 主路径：`qssi16/packages/modules/Bluetooth/service/`
   - 备用：`qssi16/packages/modules/Bluetooth/framework/`
   - 备用：`qssi16/packages/modules/Bluetooth/android/`

4. **BT Service APK（Profile 实现）**
   - 主路径：`target/vendor/qcom/opensource/commonsys/packages/apps/Bluetooth/src/com/android/bluetooth/`
   - 备用：如有 AOSP 路径 `qssi16/packages/apps/Bluetooth/`

5. **BT HAL 接口**
   - 主路径：`target/hardware/interfaces/bluetooth/`
   - 备用：`qssi16/hardware/interfaces/bluetooth/`

6. **BT Stack**
   - 主路径：`target/vendor/qcom/opensource/commonsys/system/bt/`
   - 子路径（按需定点）：
     - `btif/` — BTIF 桥接层
     - `bta/` — BTA 应用层
     - `stack/` — 协议栈实现
     - `hci/` — HCI 层

7. **Vendor HAL 实现**
   - 候选：`target/vendor/qcom/opensource/commonsys/system/bt/vendor_libs/`
   - 标注为"候选实现域"

## 结果输出增强

在最终报告的"层级路径说明"或"关键源码索引"中，应补充：

- **本次实际使用的检索路径**
- **未使用但属于本层候选的参考路径**
- **是否发生扩展检索**

## 路径变体规则

1. 如果同时存在 `qssi16/...` 与 `target/...` 同名 Java 文件：
   - 优先用 `qssi16/...` 作为 Framework / BT Module 主分析路径
2. 如果 BT Stack 在 `target/vendor/qcom/opensource/commonsys/system/bt/` 更完整：
   - 直接引用此路径
3. 如果 vendor HAL 目录存在但本次主链没有直接证据：
   - 仍可列入"关键源码索引"，但必须标注为"候选实现域"

## 验收标准

1. 执行分析时默认先在参考路径内定点检索
2. 不再默认整仓搜索
3. 发生扩展检索时，文档要说明原因与扩展结果
4. 各层参考路径在报告"层级路径说明"中有记录

## 已确认决策

1. 不采用"完全禁止扩展检索"
2. 采用"参考路径优先 + 按层扩展"的中度约束方案
3. BT Stack 默认参考路径以 `target/vendor/qcom/opensource/commonsys/system/bt/` 为准
4. 用户给定的六层路径作为默认检索域的起点
