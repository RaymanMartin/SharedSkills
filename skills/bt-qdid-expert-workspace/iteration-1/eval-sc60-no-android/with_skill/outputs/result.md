## 🔵 蓝牙信息查询结果

**模组型号：** SC60  
**Android 版本：** Android 10 (Q)（原问题未提供，按要求补全后查询）  
**Excel 检索结论：** SC60 系列在配置表中主要对应 **WCN3680B**，少量料号对应 **WCN3680**。

> 说明：按 Skill 要求，若未提供 Android 版本需要先询问；此处按要求模拟用户回复 **Android 10** 后继续查询。

### Controller（芯片端）
SC60 在 Excel 中查到的实际蓝牙芯片族为 **WCN3680 / WCN3680B**。对应 QDID 表条目如下：

| WCN 芯片 | Declaration ID | QDID / DN | BT Spec Version | 备注 |
|---|---|---:|---|---|
| WCN3680(B) | D023211 | 67796 | V4.1 | RF & RF PHY |
| WCN3680(B) | B021332 | 47905 | V4.0 | RF & RF PHY |
| WCN3680(B) | B018867 | 34203 | V4.0 | RF & RF PHY |

> 注：`qdid_table.md` 将 **WCN3680(B)** 归在同一 36xx 家族条目下；Excel 中 SC60 既出现 WCN3680B，也出现少量 WCN3680 料号，可按同家族条目匹配。  
> 另：脚本初次模糊检索返回过 **WCN3950**，这是因为匹配到了 `QSC601VP` 工作表名中的 `SC60` 子串，并非 SC60 模组本体，可忽略。

### Host（Android 端）
| Android 版本 | Declaration ID | QDID / DN | BT Spec Version |
|---|---|---:|---|
| Q (Android 10) | D034494 | 138963 | V5.1 |

### 最终结论
| 项目 | 结果 |
|---|---|
| **SC60 蓝牙版本** | **BT 4.0 / 4.1**（取 Host V5.1 与 Controller V4.0/V4.1 的较低值） |
| **Host QDID** | **138963** |
| **Controller QDID** | **67796**（若走 BT 4.1 声明） |
| **兼容的旧 Controller QDID** | **47905 / 34203**（BT 4.0 旧声明） |

### 建议
- 如果你只是要给客户一个 **SC60 蓝牙 QDID**，优先给：**Controller QDID 67796 + Host QDID 138963**。  
- 如果需要做正式资料/认证映射，建议再提供 **SC60 完整料号**（如 `SC60PCETA`、`SC60CEYH`），我可以进一步精确到它到底是 **WCN3680** 还是 **WCN3680B**。

> BT SIG 官方查询地址：<https://qualification.bluetooth.com/MyProjects/ListingsSearch>
