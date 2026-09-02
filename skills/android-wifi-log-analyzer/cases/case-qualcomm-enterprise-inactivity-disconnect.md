---
id: case-qualcomm-enterprise-inactivity-disconnect
issue_type: ap_inactivity_no_reconnect
platform: qualcomm
android_version: "14"
severity: medium
tags: [reason=4, inactivity, enterprise-ap, power-save, reconnect-delay, wifi5-mode]
created: 2026-05-22
log_source: /home/quectel/Work/Log/yd盈达/弱网断开/WiFi5日志/
report: /home/quectel/Work/Log/yd盈达/弱网断开/WiFi5日志/wifi_analysis_report.md
notes: /home/quectel/Work/Log/yd盈达/弱网断开/WiFi5日志/wifi_analysis_notes.md
---

# Case: Qualcomm 企业 AP 空闲超时断连 (reason=4)

## 问题描述

设备在企业多AP环境下 (SSID: JHT-WH, WPA2-PSK)，信号良好 (RSSI -67dBm) 但频繁断连，每次断连后需 3~6 分钟才重连。日志显示断连原因均为 `reason=4 (DISASSOC_DUE_TO_INACTIVITY)`。

## 根因

设备在屏幕关闭后进入深度省电模式，停止向 AP 发送任何帧，导致企业 AP 的空闲超时机制（inactivity timer）触发，AP 发送 DISASSOC(reason=4)。  
wpa_supplicant 打印 "Auto connect disabled: do not try to re-connect"，但 Framework 层通过周期性扫描在约 3~6 分钟后重新发起连接。

**信号良好但断连 = 典型的 reason=4 / 省电模式冲突特征**

## 诊断关键字

```
CTRL-EVENT-DISCONNECTED.*reason=4
DISASSOC_DUE_TO_INACTIVITY
Auto connect disabled: do not try to re-connect
CMD_START_CONNECT.*DisconnectedState
```

## 关联特征

- 断连总是在屏幕关闭一段时间后发生
- 断连前 RSSI 正常 (-50 ~ -75 dBm), score 正常
- 每次断连后 wpa_supplicant 不自动重连，Framework 扫描后 3~6 分钟才重连
- 模式: 连接 → ~30-60分钟空闲 → reason=4 → 3-6分钟断连 → 重连

## "wifi5 mode" SelfRecovery 误导性日志

iData ODM 定制代码中 `WifiSelfRecovery` 在 `REASON_STA_IFACE_DOWN` 场景下打印:
```
WifiSelfRecovery: REASON_STA_IFACE_DOWN only work on wifi5 mode.. STA interface down, disable wifi
```
**注意**: 此日志在正常系统关机时也会触发 (wlan0 down due to driver unload)。  
需检查是否有 `sys.shutdown.requested` 前序事件来区分关机 vs 异常 crash。

## 次要问题: WMI Roam Stats TLV 错误

```
wlan: [E:WMI] extract_roam_stats_event_tlv: Invalid roam ap data num_tlv:N
```
驱动 v2.0.9.22Q 与固件版本不配套，roam stats 事件 TLV 数量不匹配。非致命但累计 936 次，影响漫游统计。

## 建议修复方向

1. **设备侧**: 关闭深度 DTIM 省电 / 启用 WiFi keepalive / 调整 `wifi.supplicant_scan_interval`
2. **AP 侧**: 延长企业 AP inactivity timer (300s → 1800s+)
3. **漫游优化**: 启用固件层漫游 (firmware roaming) 减少 Framework 漫游震荡
4. **驱动升级**: 更新驱动/固件版本解决 WMI TLV 解析错误

## 版本信息

| 项目 | 版本 |
|------|------|
| 设备 | iData K8Pro |
| Android | 14 (UKQ1) |
| WiFi 驱动 | 2.0.9.22Q (Qualcomm QCA) |
| 平台 | Qualcomm SM6225 (Snapdragon 680) |
