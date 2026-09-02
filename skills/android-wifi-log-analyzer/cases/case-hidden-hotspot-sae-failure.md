---
id: case-hidden-hotspot-sae-failure
title: 扫码连WiFi失败 — wpa_supplicant不支持SAE (WPA3)
platform: generic (POS terminal, unknown WiFi chip, 2.4GHz-only)
device: Newpos POS terminal (com.newpos.*)
issue_type: hidden_hotspot_sae_not_supported
severity: critical
android_version: Android 13
log_path: /home/quectel/Work/Log/hzr华智融/Syslog-9228扫码连WiFi失败
keywords:
  - "No available security params"
  - "SupplicantStaNetworkHalAidlImpl"
  - "Failed to save variables.*SAE"
  - "CMD_START_CONNECT Failed.*PMF: true.*KeyMgmt: SAE"
  - "Cannot select a candidate security params from scan results"
  - "WifiDppQrCodeScanner"
  - "SECURITY_TYPES.*4"
tags:
  - WPA3
  - SAE
  - hidden-ssid
  - QR-code
  - 2.4GHz-only
  - POS-terminal
---

## 问题描述

用户通过WiFi设置中的QR二维码扫码功能尝试连接隐藏热点"mthgh"（手机共享的WPA2/WPA3混合热点），连接始终失败，设备无法在系统界面通过扫描发现或连接该热点。

## 根因链

```
用户扫码QR → addOrUpdateNetwork "mthgh" SAE+HIDDEN
  ↓
wpa_supplicant扫描：仅2.4GHz → 热点未出现在scan结果（可能在5GHz）
  ↓
WifiClientModeImpl: Cannot select candidate security params from scan results
  → try "first available" = SAE (from network config)
  ↓
SupplicantStaIfaceHalAidlImpl: connectToNetwork "mthgh" SAE
  ↓
SupplicantStaNetworkHalAidlImpl: No available security params.  ← 核心失败点
  (wpa_supplicant未编译CONFIG_SAE 或 驱动未上报SAE capability)
  ↓
CMD_START_CONNECT Failed HIDDEN:true PMF:true KeyMgmt:SAE
  ↓
am_wtf: SupplicantStaNetworkHalAidlImpl, No available security params.
```

## 决定性证据

### "非隐藏AP同样SAE失败"是根因的最强证明

```logcat
# 隐藏热点失败
09:03:47.954  SupplicantStaNetworkHalAidlImpl: No available security params.
09:03:47.959  CMD_START_CONNECT Failed SSID:"mthgh" HIDDEN:true KeyMgmt:SAE

# 非隐藏热点，同样失败
09:04:06.857  SupplicantStaNetworkHalAidlImpl: No available security params.
09:04:06.860  CMD_START_CONNECT Failed SSID:"AndroidAP_5600" HIDDEN:false KeyMgmt:SAE
```

→ 根因是 **SAE不支持**，与"隐藏"属性无关。

## 关键日志模式

| 日志 | 含义 |
|------|------|
| `SupplicantStaNetworkHalAidlImpl: No available security params.` | wpa_supplicant不支持所请求的安全类型 |
| `am_wtf: SupplicantStaNetworkHalAidlImpl, No available security params.` | 系统标记为Watchdog触发的严重错误 |
| `Cannot select a candidate security params from scan results` | 热点未出现在scan结果中（5GHz或范围外） |
| `CMD_START_CONNECT Failed ... PMF: true KeyMgmt: SAE` | SAE+PMF组合连接失败 |
| `Scan included frequencies: 2412~2484` | 仅2.4GHz，无5GHz能力 |

## 2.4GHz-only 识别方式

所有扫描频率完全落在 2400-2500MHz 范围内：
```
nl80211: Scan included frequencies: 2412 2417 2422 2427 2432 2437 2442 2447 2452 2457 2462 2467 2472 2484
```
5GHz频道特征值: 5180, 5200, 5220, 5240, 5745, 5765, 5785, 5805 等。

## SECURITY_TYPES 映射

| 值 | 含义 |
|----|------|
| 2 | WPA2-PSK (TKIP/CCMP) |
| 4 | WPA3-SAE |
| [2,4] | WPA2/WPA3混合模式 |
| 5 | WPA3-SAE-Transition |

当 Framework 无法从 scan result 推断安全类型时，会尝试第一个可用参数（通常 SAE）。

## 修复方案

### 立即可用（不改代码）

手机热点配置:
- 安全方式: **WPA2 Personal** (不选WPA3或混合)
- 频段: **2.4GHz**

### 根本解决

```makefile
# wpa_supplicant编译配置 (android_wpa_supplicant.conf 或 .config)
CONFIG_SAE=y
CONFIG_IEEE80211W=y    # PMF (PMF is mandatory for WPA3)
```

同时确认WiFi驱动/固件向nl80211上报 SAE AKM (0000FAC8)。

## 快速诊断命令

```bash
# 确认wpa_supplicant是否支持SAE
adb shell wpa_cli -i wlan0 get_capability key_mgmt
# 输出应含 SAE；若无则确认为编译问题

# 查看驱动能力
adb shell iw phy phy0 info | grep -A5 "AKM"
# 应含 SAE (00-0f-ac:8)

# 确认频段支持
adb shell iw phy phy0 info | grep "Band"
# 若只有 Band 1 (2.4GHz)，无 Band 2 (5GHz)，为2.4GHz-only设备
```

## 日志完整性

- logcat: ✅ 完整（12467行）
- dmesg: ✅ 完整（2822行）
- tcpdump: ❌ 缺失（L2未建立，不影响分析）
- 驱动日志: ❌ 无（无平台专属驱动）
