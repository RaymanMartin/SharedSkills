## 🔵 蓝牙信息查询结果

**模组型号：** SC680A  
**WCN 芯片：** WCN3988  
**Android 版本：** Android 12 (S)

### Controller（芯片端）
| 项目 | 值 |
|------|-----|
| WCN 型号来源 | `lookup_module_wcn.py SC680A` + Smart module Configuration table V7.1 |
| 芯片型号 | WCN3988 |
| Controller QDID/DN | **133994**（按 `qdid_table.md` / KBA REV_6 中的 **WCN39x8 / WCN3990** 条目匹配） |
| Declaration ID | **D043254** |
| BT Spec Version | **V5.1** |
| 备注 | 本地 QDID 表未单独列出 `WCN3988`，但 `WCN3988` 属于 **WCN39x8** 家族；其本地 datasheet 也标注 **Bluetooth 5.1 compliant**，因此按该家族条目匹配 |

### Host（Android 端）
| 项目 | 值 |
|------|-----|
| Android 版本 | S (Android 12) |
| Declaration ID | **D057039** / **D057041** |
| QDID/DN | **176512**（含 LE Audio） / **176546**（不含 LE Audio） |
| BT Spec Version | **V5.2** |
| 推荐 | **D057041 / 176546**（通常推荐不含 LE Audio 版本） |

### 最终结论
| 项目 | 值 |
|------|-----|
| **蓝牙版本** | **V5.1**（取 Host V5.2 与 Controller V5.1 的较低值） |
| **Controller QDID** | **133994** |
| **Controller Declaration ID** | **D043254** |
| **Host QDID** | **176546**（推荐） / **176512**（若项目启用 LE Audio） |

### 依据说明
1. `SC680A` 在本地 Excel `Smart module Configuration table_V7.1-20250603.xlsx` 中对应芯片串包含 **WCN3988**。  
2. 本地参考表 `references/qdid_table.md` 中未单列 `WCN3988`，但存在 **WCN39x8 / WCN3990 → D043254 / 133994 / V5.1** 条目。  
3. 本地 Qualcomm datasheet `WCN3988_Wireless_Connectivity_IC_data_sheet_80-WL023-1.pdf` 明确写到 **Bluetooth 5.1 compliant**，与上述条目一致。  
4. Android 12 (S) Host 条目来自 `references/qdid_table.md`：  
   - `D057039 / 176512 / V5.2`（含 LE Audio）  
   - `D057041 / 176546 / V5.2`（不含 LE Audio）

> 💡 BT SIG 官方查询地址：<https://qualification.bluetooth.com/MyProjects/ListingsSearch>
>
> 如需 100% 对应到具体量产固件，建议再用设备确认 BT FW 标识（例如 `adb shell logcat | grep "BT SoC FW SU Build"`），因为同一家族芯片在不同 FW 分支下可能存在不同认证条目。
