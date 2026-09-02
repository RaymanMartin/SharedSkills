---
id: wpa3-no-reconnect-private-lan
issue_type: wpa3_pmksa_no_reconnect
platform: sprd
role: sta
severity: high
keywords: [WPA3, SAE, PMKSA, TEMPORARILY_DISABLED, no-internet, NetworkMonitor, 无回连, 私有局域网]
date: 2026-05
source: hzr华智融 客户案例
---

# Case: WPA3-PSK WiFi 断开后无回连（私有局域网 AP）

## 一句话摘要

私有局域网 WPA3-SAE AP 无公网 DNS → NetworkMonitor 验证失败 → 网络 TEMPORARILY_DISABLED → WPA3 PMKSA 到期触发断开 → 25分钟无法自动回连

## 关键标志

| 标志 | 说明 |
|------|------|
| `PMKSA-CACHE-REMOVED <bssid> 0` | WPA3 PMKSA 生命期归零，触发断开 |
| `CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1` | 本地触发断开（非 AP 端踢除） |
| `nl80211: Was expecting local disconnect but got another disconnect event first` | SPRD SC2355 驱动 disconnect 上报竞态（已知问题） |
| `SCAN_DONE: got N BSSes` 但 **无 CMD_START_CONNECT** | AP 可见但不尝试连接 → 网络被禁用 |
| `WifiConfigManager: Enable disabled network: "<SSID>"` | 证明网络处于 DISABLED 状态 |
| `Temporarily disabling network because of no-internet access` | 禁用原因确认 |
| `isCaptivePortal: isSuccessful()=false isPortal()=false` | 无互联网验证失败 |
| `PROBE_DNS *.google.com 6011ms FAIL Timeout` | DNS 全超时（AP 无公网 DNS 服务器）|

## 根因链

```
AP 无公网 DNS
  → NetworkMonitor DNS 全超时 (7 URLs × 6s)
  → isCaptivePortal=false isSuccessful=false (60s)
  → NETWORK_STATUS_UNWANTED_VALIDATION_FAILED
  → Temporarily disabling network (no-internet)
  → [7小时后] WPA3 PMKSA lifetime=0 → PMKSA-CACHE-REMOVED
  → sprdwl_cfg80211_disconnect reason=1 (SPRD 驱动本地断开)
  → Scan: 56 BSSes found — AP 可见
  → WifiNetworkSelector: 跳过 DISABLED 网络
  → 约 25 min 无 CMD_START_CONNECT (回连失败)
```

## 平台特性

- **驱动**: sc2355 sprd-wlan (SPRD SC2355 芯片)
- **SAE 实现**: SPRD vendor SAE IE (`dd 0e 40 45 da 02 ...`), 自定义 SAE auth results
- **PMKSA 竞态**: `nl80211: Was expecting local disconnect...` 是 SPRD 已知问题，不影响断开结果
- **日志格式**: SystemLog (logcat + dmesg 合并), 无独立 pcap / CP2 log

## 时间轴关键点

| 时间 | 事件 |
|------|------|
| ~00:04 | 连接 H3R0014000004297 (WPA3-SAE) |
| 00:05:20 | NetworkMonitor: isSuccessful=false (首次) |
| 00:16:20 | NetworkMonitor: isSuccessful=false (第二次) |
| 07:20:03 | PMKSA-CACHE-REMOVED + DISCONNECTED reason=1 |
| 07:20:08 | SCAN: 56 BSSes (AP 可见) |
| 07:20~07:45 | **25分钟空白，无回连尝试** |
| 07:45:03 | Enable disabled network → 用户手动重连 |
| 07:46:02 | 再次 TEMPORARILY_DISABLED (死循环) |

## 修复建议

1. **P0 (AP侧)**: 在 AP 192.168.4.x 上部署 HTTP 204 端点，通过 captive portal check
2. **P1 (系统)**: 将此 SSID 配置为不需要 captive portal 检查的可信网络
3. **P2 (WPA3)**: SPRD wpa_supplicant 实现 PMKSA 到期时的 inline SAE reauthentication

## 鉴别关键词（区分相似问题）

| 关键词 | 是本案 | 备注 |
|--------|--------|------|
| `PMKSA-CACHE-REMOVED ... 0` 在断开前 | ✅ | WPA3 特有 |
| `Enable disabled network` 在重连前 | ✅ | 证明网络被禁用 |
| `isCaptivePortal: isSuccessful()=false` 多次出现 | ✅ | 私有 LAN 特征 |
| `PROBE_DNS ... FAIL Timeout` 全部超时 | ✅ | 无公网 DNS |
| `reason=4` 或 `reason=3` 断开 | ❌ | 本案是 reason=1 |
| AP 侧踢除 (`locally_generated=0`) | ❌ | 本案是本地触发 |

