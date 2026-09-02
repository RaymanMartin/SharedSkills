---
date: 2026-06-30
skill: android-wifi-log_analyzer-sprd
platform: Spreadtrum (UNISOC)
android: "未知"
issue_type: "scan-abort"
root_cause_section: "§4.2"
---

## Issue Summary

`<SSID>` 在 SPRD 终端上连接失败。verbose 日志显示 supplicant 在 BSS 选择阶段把 `<SSID>` 的两个候选链路都判定为 `MLD without MFPC`，因此直接 `No suitable network found`。

## Environment

- **Device / Module**: SPRD / UNISOC 终端
- **Android**: 未知（当前日志未包含版本字段）
- **AP / Router**: `<SSID>`，客户确认已切为纯 WPA2-PSK-AES；日志中仍可见 11be / MLO 特征
- **Log file**: `verboselog/device_issue.log`

## Key Log Signatures

```text
06-29 13:40:23.438  WifiNetworkSelector: Remove upgradable security type 4 for the network.
06-29 13:40:23.443  WifiClientModeImpl: Select best-fit security params: 2
06-29 13:40:23.444  WifiConfigManager: KeyMgmt: WPA_PSK
06-29 13:40:23.476  wpa_supplicant: SAE: Derive PT - group 19
06-29 13:40:23.498  wpa_supplicant: wlan0: 1: xx:xx:xx:xx:xx:xx ssid='<SSID>' ... freq=5180
06-29 13:40:23.498  wpa_supplicant:    skip RSNE - 6 GHz/MLD without MFPC
06-29 13:40:23.498  wpa_supplicant: wlan0: 4: xx:xx:xx:xx:xx:xx ssid='<SSID>' ... freq=2427
06-29 13:40:23.498  wpa_supplicant:    skip - 6 GHz/MLD BSS without matching RSNE
06-29 13:40:23.498  wpa_supplicant: No suitable network found
06-29 13:40:23.499  wpa_supplicant: assoc key_mgmt 0x0 network key_mgmt 0x142
06-29 13:40:23.503  WifiClientModeImpl: Network not found event received: network: "<SSID>"
```

## Root Cause

这次 verbose 日志把失败点明确到了 supplicant 的 BSS 选择路径。虽然 Framework 已经移除了 `upgradable security type 4` 并选择 `WPA_PSK`，但 supplicant 侧仍保留了 SAE / transition 相关状态（`SAE: Derive PT`、`network key_mgmt 0x142`）。随后它把 `<SSID>` 的两个候选 BSS 都判定为 `6 GHz/MLD without MFPC` / `MLD BSS without matching RSNE`，因此直接得出 `No suitable network found`，连接在 association 前失败。

结合 scan result 中的 `standard: 11be` 和 `MLO Info`，最可疑的是：

1. AP 在 WPA2 模式下仍广播了 11be / MLO 信息，但 RSNE 不满足 MLD 对 PMF/MFPC 的要求；或
2. SPRD 客户端在 auto-upgrade / supplicant key mgmt 处理上存在兼容性缺陷，错误触发了 MLD 安全检查。

## Resolution / Next Steps

1. 关闭热点/路由器的 Wi-Fi 7 / 11be / MLO，改用兼容模式复测
2. 改为单频热点（仅 2.4G 或仅 5G）复测
3. 若热点支持 PMF，开启 PMF 后复测
4. 抓 AP 侧 beacon / probe response，核对 RSNE 与 MLO IE
5. 终端侧继续排查 `WifiConfigurationUtil`、`SupplicantStaNetworkHalAidlImpl` 与 supplicant 的 `MLD without MFPC` 判定路径
