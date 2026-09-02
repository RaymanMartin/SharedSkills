---
date: 2026-06-24
skill: android-wifi-log_analyzer-sprd
platform: Spreadtrum (UNISOC)
android: "未知"
issue_type: "scan-abort"
root_cause_section: "§4.2"
---

## Issue Summary

WPA2/WPA3 混合热点 `<SSID>` 在 SPRD 终端上反复连接失败，未进入 association，Framework 持续收到 `Network not found event`。

## Environment

- **Device / Module**: SPRD / UNISOC 终端（`uni_marlin3` 资源包特征）
- **Android**: 未知
- **AP / Router**: 5GHz 热点 `<SSID>`（WPA2/WPA3 混合）
- **Log file**: `wifi_5g_attach_failure(1).log` + `wifi_5g_attach_failure1(1).log`

## Key Log Signatures

```text
06-23 09:59:11.905  WifiConfigurationUtil: Add upgradable SAE configuration.
06-23 09:59:11.943  WifiClientModeImpl: Select best-fit security params: 2
06-23 09:59:11.949  SupplicantStaIfaceHalAidlImpl: connectToNetwork "<SSID>"WPA_PSK, actualSsid=null
06-23 09:59:11.982  SupplicantStaNetworkHalAidlImpl:  KeyMgmt: WPA_PSK
06-23 09:59:11.982  SupplicantStaNetworkHalAidlImpl:  RequirePmf: false
06-23 09:59:12.032  wpa_supplicant: assoc key_mgmt 0x0 network key_mgmt 0x142
06-23 09:59:12.037  WifiClientModeImpl: Network not found event received: network: "<SSID>"
06-23 10:00:03.426  wificond: NL80211_CMD_TRIGGER_SCAN failed: Device or resource busy
```

## Root Cause

这是一个 **WPA2/WPA3 过渡网络的安全类型匹配失败** 案例。Framework 识别 `<SSID>` 为可升级 SAE 网络，但实际下发的是 `WPA_PSK + RequirePmf:false`。supplicant 随后出现 `assoc key_mgmt 0x0 network key_mgmt 0x142`，说明当前扫描到的 BSS 与下发配置未能匹配出可关联 AKM，因此连接在 association 前失败。`Scan aborted / -6 busy` 是伴随现象，不是主根因。

## Resolution / Next Steps

1. AP 先改成纯 `WPA2-PSK` 或纯 `WPA3-SAE` 验证
2. 补抓 `wpa_cli scan_results` / `cmd wifi list-scan-results` 确认 AP 的 AKM 与 PMF 能力
3. 检查 SPRD Framework / supplicant 对 `upgradable SAE` 的降级逻辑，重点关注 `RequirePmf:false` 和 `assoc key_mgmt 0x0`
