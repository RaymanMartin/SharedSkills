# Case Cache — android-wifi-log_analyzer-sprd

每次使用本 Skill 完成分析后，会在此目录保存一个案例文件。  
案例文件随 Skill 一起分发，可在后续分析中作为快速参考。

## 命名规则

```
YYYYMMDD_<issue-type>[_N].md
```

`issue-type` 取值示例：

| 值 | 场景 |
|---|---|
| `wcn-crash` | WCN 驱动崩溃 / assert |
| `scan-abort` | 扫描失败 |
| `dhcp-failure` | DHCP 获取失败 |
| `disconnect-loop` | 反复断连重连 |
| `assoc-reject` | Association 被拒绝 |
| `4way-timeout` | 4-Way Handshake 超时 |
| `validation-fail` | 网络验证失败 |
| `captive-portal` | Captive Portal |

同一天同类型有多个案例时，追加 `_2`, `_3` 后缀。

## 案例文件格式

见 `CASE_TEMPLATE.md`。
