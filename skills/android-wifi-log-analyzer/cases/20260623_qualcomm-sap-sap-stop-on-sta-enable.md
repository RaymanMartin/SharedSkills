---
platform: qualcomm
role: sap
issue_type: sap-stop-on-sta-enable
log_types: [logcat, dmesg]
root_cause_layer: 1
created: 2026-06-23
source: /home/quectel/Work/Log/xz迅族
---

# Issue Summary

在热点已经正常工作、且已有客户端接入的情况下，用户/业务再打开 STA Wi-Fi。  
Framework 立即启动 `ClientModeManager`，并同时关闭所有 SoftAP manager，导致热点客户端被强制踢下线，随后设备转为 STA 并成功连接外部 AP。

## Key Log Signatures

```text
WifiActiveModeWarden: Starting ClientModeManager
WifiActiveModeWarden: Shutting down all softap mode managers in mode -1
hostapd: Force all clients disconnect by driver with reason: 1
hostapd: wlan1: AP-STA-DISCONNECTED xx:xx:xx:xx:xx:xx
WifiHAL: wifi_virtual_interface_delete: ifname=wlan1 delete
wpa_supplicant: CTRL-EVENT-CONNECTED - Connection to <SSID> completed
```

## Root Cause

根因位于 **Layer 1 / Framework**：系统在打开 STA Wi-Fi 时主动收掉现有热点，而不是热点异常掉线。  
从 dmesg 看，`hostapd` 以状态 0 正常退出，随后 `wpa_supplicant` 正常启动并完成扫描、4-way 和 DHCP，排除了驱动崩溃/固件重启。

## Next Steps

1. 若产品要求热点与 STA 共存，确认并启用 STA+SAP concurrency 能力。
2. 若平台不支持共存，在业务/UI 层阻止“热点开着再开 Wi-Fi”的操作，并给出明确提示。
3. 补抓 `dumpsys wifi` 并发组合与版本信息，确认限制来自硬件能力还是产品策略。
