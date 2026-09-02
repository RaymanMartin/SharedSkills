---
date: 2026-06-29
skill: android-wifi-log_analyzer-sprd
platform: Spreadtrum (UNISOC)
android: "未知"
issue_type: "scan-abort"
root_cause_section: "§4.2"
---

## Issue Summary

`<SSID>` 在 SPRD 终端上连接失败。客户确认 AP 为纯 WPA2-PSK-AES，但终端本地仍触发 `upgradable SAE` 补建逻辑，最终在 association 前报 `Network not found event`。

## Environment

- **Device / Module**: SPRD / UNISOC 终端（`uni_marlin3` 特征）
- **Android**: 未知
- **AP / Router**: 5GHz 热点 `<SSID>`（客户确认：纯 WPA2-PSK-AES）
- **Log file**: `newLog/0-android_main.log`

## Key Log Signatures

```text
06-29 09:55:32.791  WifiConfigManager: Cannot find network with networkId -1 or configKey "<SSID>"WPA_PSK
06-29 09:55:32.816  WifiConfigurationUtil: Add upgradable SAE configuration.
06-29 09:55:32.846  WifiClientModeImpl: Select best-fit security params: 2
06-29 09:55:32.850  SupplicantStaIfaceHalAidlImpl: connectToNetwork "<SSID>"WPA_PSK, actualSsid=null
06-29 09:55:32.897  SupplicantStaNetworkHalAidlImpl:  KeyMgmt: WPA_PSK
06-29 09:55:32.940  wpa_supplicant: assoc key_mgmt 0x0 network key_mgmt 0x142
06-29 09:55:32.944  WifiClientModeImpl: Network not found event received: network: "<SSID>"
```

## Root Cause

这是 2026-06-24 同类问题的再次复现，但已知 AP 不是混合模式，因此根因更明确地落在**终端本地配置对象异常**。`WifiConfigManager` 在用户点击连接时先找不到 `<SSID>` 的有效 `configKey`，随后自动补建 `upgradable SAE` 配置，但真正下发给 supplicant 的仍是 `WPA_PSK`。`assoc key_mgmt 0x0 network key_mgmt 0x142` 表明本地配置与扫描结果中的可关联 AKM 未匹配成功，连接在 association 前失败。`Scan failed - Device or resource busy` 只是并发扫描噪声。

## Resolution / Next Steps

1. 终端先 Forget `<SSID>` 后重新添加
2. 补抓 `wpa_cli scan_results` / `cmd wifi dump`，核对保存配置与扫描结果是否一致
3. 修复 SPRD 当前版本中 `configKey` 查找失败后错误补建 `upgradable SAE` 的逻辑
