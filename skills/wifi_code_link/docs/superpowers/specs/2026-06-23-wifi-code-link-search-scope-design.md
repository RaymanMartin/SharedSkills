# wifi_code_link 路径收敛与定点检索设计

## 问题定义

当前 `wifi_code_link` 虽然已经有分层路径参考，但还有两个实际使用问题：

1. **驱动参考路径不够明确**
   - 用户已经明确给出驱动参考路径应为：
     `target/vendor/qcom/opensource/wlan`
   - skill 需要把这一路径固化为默认驱动参考域，而不是继续模糊描述成 vendor driver 候选目录。
2. **检索范围仍然可能过大**
   - 当前规则更偏向“按层分析”，但没有把“优先在参考路径里定点检索”写成硬约束
   - 实际执行时容易退化为整仓搜索

## 升级目标

1. 把 `target/vendor/qcom/opensource/wlan` 固化为驱动参考路径。
2. 把检索策略改成：
   - **先按用户给定参考路径定点检索**
   - **只在当前层参考路径找不到锚点时，才允许扩展**
   - **默认禁止整仓搜索作为第一选择**
3. 让最终报告能说明：
   - 本次实际用了哪些参考路径
   - 哪些层发生了扩展检索
   - 为什么需要扩展

## 非目标

1. 不要求完全禁止扩展检索。
2. 不要求为每个厂商平台都单独定一套搜索协议。
3. 不要求把所有路径都写成绝对唯一，不处理源码树差异。

## 方案比较

### 方案 1：只补驱动路径

只把 `target/vendor/qcom/opensource/wlan` 写进参考路径。

**优点**
- 改动最小

**缺点**
- 不能解决“默认整仓搜索”的问题

### 方案 2：路径收敛 + 定点优先检索（本次选择）

同时补两条规则：

1. 明确驱动参考路径
2. 强制“参考路径优先、按层扩展、禁止默认整仓搜索”

**优点**
- 直接解决用户指出的两点
- 不会因为源码差异把 skill 卡死

**缺点**
- `SKILL.md` 和 `layer-map.md` 需要同步更新

### 方案 3：完全禁止扩展检索

只允许在用户给出的参考路径中检索，不允许外扩。

**优点**
- 约束最强

**缺点**
- 一旦源码树有变体，分析容易中断

## 设计结论

采用 **方案 2：路径收敛 + 定点优先检索**。

## 核心修正规则

### 1. 驱动参考路径修正

驱动层默认参考路径改为：

- `target/vendor/qcom/opensource/wlan`

同时保留内核无线栈路径：

- `target/kernel_platform/msm-kernel`

二者在分层说明中必须明确区分：

1. `target/kernel_platform/msm-kernel` 是 **Kernel wireless stack / cfg80211 / nl80211 相关域**
2. `target/vendor/qcom/opensource/wlan` 是 **Vendor WiFi driver 实现域**

### 2. 检索优先级改为“参考路径优先”

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

### 3. 扩展检索必须可解释

如果发生路径扩展，文档中必须说明：

1. 原始参考路径
2. 为什么在原路径中未命中
3. 扩展到了哪个路径
4. 扩展后的命中锚点是什么

### 4. 参考路径按层映射

对于当前 skill，默认按下列顺序定点检索：

1. **Settings / Tethering**
   - `qssi16/packages/apps/Settings/src/com/android/settings/wifi/tether/`
   - `qssi16/packages/apps/Settings/src/com/android/settings/network/tether/`
2. **Connectivity / NetworkStack**
   - `qssi16/packages/modules/Connectivity/Tethering/common/TetheringLib/src/android/net/`
   - `qssi16/packages/modules/Connectivity/Tethering/src/com/android/networkstack/tethering/`
3. **Wifi Framework**
   - `qssi16/packages/modules/Wifi/framework/java/android/net/wifi/`
   - `qssi16/packages/modules/Wifi/service/java/com/android/server/wifi/`
4. **HAL 接口层**
   - `target/hardware/interfaces/wifi`
5. **Userspace daemon**
   - `target/external/wpa_supplicant_8`
   - 若主源码在 `qssi16/external/wpa_supplicant_8` 更完整，可作为同层备用路径
6. **Vendor WiFi HAL / Native**
   - `target/hardware/qcom/wlan/qcwcn`
7. **Kernel wireless stack**
   - `target/kernel_platform/msm-kernel`
8. **WiFi Driver**
   - `target/vendor/qcom/opensource/wlan`

### 5. 结果输出增强

在最终报告的“层级路径说明”或“关键源码索引”中，应补充：

- **本次实际使用的检索路径**
- **未使用但属于本层候选的参考路径**
- **是否发生扩展检索**

## 实现影响面

本次修改主要影响：

1. `SKILL.md`
   - 增加“定点优先检索”硬规则
   - 明确禁止默认整仓搜索
2. `references/layer-map.md`
   - 修正驱动参考路径
   - 加入按层检索优先级说明
3. `README.md`
   - 简述检索策略已改为参考路径优先

## 验收标准

升级后，`wifi_code_link` 应满足：

1. 驱动层默认参考路径显示为 `target/vendor/qcom/opensource/wlan`
2. 执行分析时默认先在参考路径内定点检索
3. 不再默认整仓搜索
4. 发生扩展检索时，文档要说明原因与扩展结果

## 已确认决策

1. 不采用“完全禁止扩展检索”
2. 采用“参考路径优先 + 按层扩展”的中度约束方案
3. 驱动参考路径以 `target/vendor/qcom/opensource/wlan` 为准
