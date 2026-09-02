---
date: 2026-07-01
skill: android-wifi-log_analyzer-sprd
platform: Spreadtrum (UNISOC)
android: "未知"
issue_type: "scan-abort"
root_cause_section: "§4.2"
---

## Issue Summary

`<SSID>` 在客户声称已切换为 WPA2 + Wi‑Fi 6 后仍连接失败。终端日志显示 `<SSID>` 依旧被识别成 11be/MLO 目标，supplicant 在 BSS 选择阶段将两个候选链路都判为 `MLD without MFPC`。

## Environment

- **Device / Module**: SPRD / UNISOC 终端
- **Android**: 未知（当前日志未包含版本字段）
- **AP / Router**: `<SSID>`，客户口径为 WPA2 + Wi‑Fi 6，但终端日志仍见 `11be` / `MLO Info`
- **Log file**: `device_issue111.log`

## Key Log Signatures

```text
07-01 16:09:56.717  WifiNetworkSelector: Remove upgradable security type 4 for the network.
07-01 16:09:56.719  WifiConfigManager: ... standard: 11be ... MLO Info: AP MLD MAC Address: xx:xx:xx:xx:xx:xx
07-01 16:09:56.723  WifiClientModeImpl: Select best-fit security params: 2
07-01 16:09:56.731  SupplicantStaNetworkHalAidlImpl: KeyMgmt: WPA_PSK
07-01 16:09:56.743  wpa_supplicant: SAE: Derive PT - group 19
07-01 16:10:06.645  wpa_supplicant: 2: xx:xx:xx:xx:xx:xx ssid='<SSID>' ... freq=5180
07-01 16:10:06.645  wpa_supplicant:    skip RSNE - 6 GHz/MLD without MFPC
07-01 16:10:06.645  wpa_supplicant: 5: xx:xx:xx:xx:xx:xx ssid='<SSID>' ... freq=2427
07-01 16:10:06.645  wpa_supplicant:    skip - 6 GHz/MLD BSS without matching RSNE
07-01 16:10:06.645  wpa_supplicant: No suitable network found
07-01 16:10:06.646  wpa_supplicant: assoc key_mgmt 0x0 network key_mgmt 0x142
```

## Root Cause

这份日志延续了前一份 verbose 案例的根因：虽然 Framework 已经按 `WPA_PSK` 连接，且移除了 `upgradable security type 4`，但终端扫描结果里 `<SSID>` 仍被识别成 `standard: 11be` 且带 `MLO Info`。supplicant 随后在 BSS 选择阶段对两个 `<SSID>` 候选都执行了 `MLD` 相关 RSNE/MFPC 校验，并以 `skip RSNE - 6 GHz/MLD without MFPC` / `No suitable network found` 结束连接。

因此，这次失败说明：

1. AP 改成 Wi‑Fi 6 后，从终端视角并未真正变成纯 Wi‑Fi 6 目标；或
2. SPRD 客户端仍将该 AP 误解析为 11be/MLO 目标；并且
3. supplicant key mgmt 路径仍残留复合 AKM / SAE 痕迹（`network key_mgmt 0x142`）。

## Resolution / Next Steps

1. 抓 AP 侧 beacon / probe response，确认是否仍含 11be / MLO IE
2. 确认 AP 切换 Wi‑Fi 模式后已真正重启生效
3. 关闭 Wi‑Fi 7 / 11be / MLO 后复测
4. 用另一台已知纯 Wi‑Fi 6 WPA2-PSK AP 交叉验证
5. 若仍复现，继续排查 SPRD 对 MLO/RSNE 的解析和 supplicant key mgmt 下发路径
