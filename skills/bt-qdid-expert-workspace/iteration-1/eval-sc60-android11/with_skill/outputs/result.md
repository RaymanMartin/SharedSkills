## 🔵 蓝牙信息查询结果

**模组型号：** SC60  
**Android 版本：** Android 11 (R)  
**Excel 配置表检索结果：** SC60 当前存在两类蓝牙/WCN 方案：**WCN3680B**（多数早期/常见版本）和 **WCN3680**（部分 V5.2 版本）。参考 QDID 表时按 **WCN3680(B) 家族**处理。

### Controller（芯片端）
| 项目 | 值 |
|------|-----|
| WCN 芯片 | WCN3680B / WCN3680 |
| Declaration ID | B018867 / B021332 / D023211 |
| QDID / DN | 34203 / 47905 / 67796 |
| BT Spec Version | V4.0 / V4.0 / V4.1 |
| 备注 | D023211 对应 BT 4.1；其余两个条目对应 BT 4.0 |

### Host（Android 端）
| 项目 | 值 |
|------|-----|
| Android 版本 | R (Android 11) |
| Declaration ID | D050631 |
| QDID / DN | 149467 |
| BT Spec Version | V5.2 |

### 最终结论
| 项目 | 值 |
|------|-----|
| **蓝牙版本** | **4.0 或 4.1**（取 Host V5.2 与 Controller 较低值） |
| **Host QDID** | **149467** |
| **Controller QDID** | **67796（若走 BT 4.1 认证）** / **34203、47905（若走 BT 4.0 认证）** |

### 补充说明
1. 从 `Smart module Configuration table_V7.1-20250603.xlsx` 的 `SC60` sheet 看，SC60 并非单一硬件：
   - 多数型号（如 SC60PCETA、SC60CEYA 等）使用 **WCN3680B**；
   - 部分 V5.2 型号（如 SC60CEYH、SC60PCETI 等）使用 **WCN3680**。
2. 由于本地 QDID 对照表按 **WCN3680(B)** 家族给出认证信息，因此实际项目通常按上表查询。
3. 如果您需要锁定**最终用哪个 Controller QDID**，建议在设备上确认蓝牙固件版本：
   - `adb shell logcat | grep "BT SoC FW SU Build"`
   - 对 WCN36xx 旧方案也可用：`adb shell dmesg | grep wcnss`
4. 可在 BT SIG 官网进一步核验：<https://qualification.bluetooth.com/MyProjects/ListingsSearch>
