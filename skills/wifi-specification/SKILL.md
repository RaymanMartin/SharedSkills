---
name: wifi-specification
description: |
  查询Quectel模组的WiFi安全协议支持情况。当用户问"XX模组支持哪些安全协议"、"XX模组的WiFi安全"、"XX模组支持WPA3吗"、"找到XX模组的WiFi规格"等问题时，必须使用本skill。
  
  工作流程：先从 /home/quectel/Documents/Smart module Configuration table_V7.1-20250603.xlsx 查找模组对应的WCN芯片型号，再从 /home/quectel/Documents/Wifi/Qcom/ 对应目录的文档中提取安全协议信息。
  
  Trigger keywords: 安全协议, WPA, WPA3, WPA2, WiFi安全, 安全模式, wifi规格, security protocol, wifi spec, WCN, 模组wifi, 模组安全
---

# WiFi Specification Skill

用于查询Quectel模组所支持的WiFi安全协议。

## 资源说明

- **配置表**: `/home/quectel/Documents/Smart module Configuration table_V7.1-20250603.xlsx`  
  每个Sheet对应一款模组型号，列B（`Chipset+Power chip+Transceiver+PA+WCN`）包含WCN芯片型号。
  
- **Qcom文档目录**: `/home/quectel/Documents/Wifi/Qcom/`  
  按WCN芯片型号分子目录，存放规格书和用户指南PDF。

- **查询脚本**: `/home/quectel/.copilot/skills/wifi_specification/scripts/lookup_module.py`

## ⚠️ 隐私原则（必须遵守）

**绝对禁止**将文档原文贴入对话，包括：
- 禁止使用 `pdftotext`、`pdfgrep`、`strings` 等命令提取 PDF 原文
- 禁止使用 `--raw` 参数运行脚本
- 禁止在对话中引用文档原句（文档标注了 Confidential / Export Controlled）

**只允许转述脚本输出的结论**（协议名称、芯片型号、文档命中数量）。

---

## 标准工作流程

### 第一步：运行查询脚本（唯一允许的检索方式）

```bash
python3 /home/quectel/.copilot/skills/wifi-specification/scripts/lookup_module.py "<模组名称>"
```

脚本在本地完成全部 PDF 分析，只向 stdout 输出结构化结论，**不输出任何原始文档文字**。

**示例：**
```bash
python3 /home/quectel/.copilot/skills/wifi-specification/scripts/lookup_module.py "SC665S"
python3 /home/quectel/.copilot/skills/wifi-specification/scripts/lookup_module.py "SC200U"
```

如需 JSON 格式：
```bash
python3 /home/quectel/.copilot/skills/wifi-specification/scripts/lookup_module.py "SC665S" --json
```

### 第二步：将脚本输出的结论直接转述给用户

脚本输出包含：
- WCN 芯片型号
- 匹配到的模组变体数量
- 扫描文档及命中数
- **✔ 支持的安全协议列表（结论，非原文）**

### 第三步：脚本找不到结果时

如果脚本报告 "No entries found"，尝试更短的前缀：
```bash
# 用 SC200U 而不是 SC200U-EMNA
python3 .../lookup_module.py "SC200U"
```

如果脚本找到了芯片但协议数为 0，只需告知用户"文档中未找到该芯片的安全协议描述"，**不要手动 grep 文档**。

## WCN芯片 → 文档目录 映射参考

| WCN芯片系列 | 子目录 |
|------------|--------|
| WCN3660/3680 | `36xx/` |
| WCN3950 | `3950/`，也查 `39xx/` |
| WCN3980/3988/3991/3998 | `3988/`，也查 `39xx/` |
| WCN6750/6856/685x | `WCN6856/` |
| WCN7850/7851/785x | `78xx/` |

## 输出格式

回答用户时，请用清晰的格式输出：

```
📶 模组: <模组型号>
🔧 WCN芯片: <WCN型号>
📄 参考文档: <文档名>

✅ 支持的安全协议:
  • WPA3 (Personal/SAE, OWE/Enhanced Open)
  • WPA2 (Personal/Enterprise, CCMP/AES)
  • WPA (Personal/Enterprise, TKIP)
  • WEP
  • WAPI
  • PMF / 802.11w (Protected Management Frames)
  • WPS
```

如果文档中没有明确列出某个协议，不要猜测，直接说明"未在文档中找到相关描述"。

## 注意事项

- 模组名称大小写不敏感，支持前缀匹配（如输入 `SC665S` 会匹配所有 `SC665S-*` 变体）
- 不同变体（-CE/-EM/-NA等）使用相同WCN芯片，安全协议相同
- 部分老款模组（WCN3660等）的文档可能没有明确列出安全协议，可查阅39xx通用文档
- **WPA3-Enterprise 检测**：不同芯片系列文档用词不同，脚本已覆盖所有已知写法：
  - WCN3950（39xx）文档：`isWpa3SuiteBSupported`、`CONFIG_SUITEB192`
  - WCN6856（WCN68xx）文档：`SUITE_B`、`SUITEB192`、`Suite-B-192`
  - 脚本已同时匹配以上全部变体，**无需手动补查**
