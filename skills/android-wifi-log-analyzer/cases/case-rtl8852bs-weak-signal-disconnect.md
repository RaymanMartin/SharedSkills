---
id: case-rtl8852bs-weak-signal-disconnect
issue_type: weak_signal_roam_cascade_supplicant_crash
platform: Realtek RTL8852BS (rtw88 / rtl8852bs)
android_version: Android (Qualcomm SoC + external Realtek WiFi card)
keywords:
  - RTW
  - rtl8852bs
  - rtw_drv_scan_by_self
  - roam_cascade
  - SIGSEGV
  - signal 11
  - wpa_supplicant crash
  - FT roam
  - age candidate
  - locally_generated
ssid_pattern: Enterprise multi-AP (same SSID, multiple BSSIDs, 5GHz ch161/ch40)
security: WPA2-PSK
source: yd盈达 弱网断开 (2026-05-20)
---

# Case: RTL8852BS 弱网漫游级联 + wpa_supplicant SIGSEGV

## 一句话概括

RTL8852BS 驱动漫游候选选择 Bug（当前AP扫描条目老化时delta比较失效）导致逆向漫游（roam到更差AP），引发长时间漫游级联，最终wpa_supplicant在多次FT漫游后因SIGSEGV崩溃断开连接。

## 关键识别指标

### 驱动层 (dmesg, RTW:前缀)

```
# 正常信号
RTW: rssi = 52/30, roam = 0   ← rssi_indicator > threshold(30), 不触发漫游

# 弱网触发
RTW: rssi = 29/30, roam = 1   ← rssi_indicator < 30, 触发rtw_drv_scan_by_self

# 候选选择Bug的Signature:
RTW: candidate:* iDataOffice(XX:XX:XX, ch161) rssi:-81 dBm, age:19748 [age]  ← 当前AP老化!
RTW: candidate:  iDataOffice(YY:YY:YY, ch161) rssi:-89 dBm, age:  268 [ok]  ← 更差但被选中!
RTW: rtw_select_roaming_candidate: candidate: YY:YY:YY                       ← 选了更差AP

# 漫游动作
RTW: rtw_ft_start_roam : start roaming timer
RTW: receive_disconnect
RTW: rtw_hw_disconnect(wlan0)
RTW: roaming from <SSID>(BSSID_OLD)
```

### Framework层 (logcat)

```
# wpa_supplicant崩溃
wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=XX:XX reason=1 locally_generated=1
init: Service 'wpa_supplicant' (pid XXXX) received signal 11  ← SIGSEGV
init: Sending signal 9 to service 'wpa_supplicant'           ← init强杀

# 正常漫游成功 (供对比)
wpa_supplicant: CTRL-EVENT-CONNECTED - Connection to <BSSID> completed
WifiClientModeImpl: ClientModeImpl: Leaving Roaming state
```

## 候选标签含义 (RTL8852BS)

| 标签 | 含义 | 是否可作为漫游目标 |
|------|------|--------------------|
| `[ok]` | RSSI > 当前AP RSSI + delta阈值(≈10dBm) | ✅ 可以 |
| `[delta]` | RSSI ≤ 当前AP RSSI + delta阈值 | ❌ 不足以漫游 |
| `[age]` | 扫描条目 > 5000ms 老化 | ❌ 排除出比较基准 |
| `*` | 当前已连接AP | 基准参照点 |

**Bug条件**: 当前AP `*` 被标为 `[age]` 时，delta比较基准失效 → 其他fresh条目被错误标记 `[ok]`

## rssi = X/30 格式解读

- 格式: `RTW: rssi = <indicator>/<threshold>, roam = <0|1>`
- `threshold = 30` (固定漫游触发阈值)
- `indicator` 为驱动内部正值RSSI指标，与dBm非线性对应:
  - indicator ~50-60 ≈ dBm ~-55 to -60 (良好)
  - indicator ~29-32 ≈ dBm ~-80 (边界)
  - indicator ~1-16 ≈ dBm ~-83 to -90 (极弱)
- `roam = 1` ← indicator < 30

## 根因链

```
弱网环境 (iDataOffice 多AP, 均在-80dBm以上)
    │
    ▼
RTW驱动每2s测量RSSI
    │
    ▼ rssi_indicator < 30
rtw_drv_scan_by_self 触发漫游扫描
    │
    ▼ 当前AP扫描条目老化 (age > 5000ms) → [age]
delta比较基准丢失
    │
    ▼ 任何fresh候选AP被错误标记 [ok]
选择RSSI更差的AP作为漫游目标
    │
    ▼
FT roam到更差AP → signal依然 < 30 → 再次触发漫游
    │                     ↑
    └─────────────────────┘ (漫游级联, 持续约3小时)
    │
    ▼ 多次FT roam操作累积内存损坏
RTW: cfg80211_disconnected(reason=1) →
wpa_supplicant SIGSEGV (signal 11)
    │
    ▼
init 重启 wpa_supplicant → Android重连
    │
    ▼ 约9.5小时后
第二次相同崩溃重现 (确认累积效应)
```

## 区分相似问题

| 特征 | 本Case | WPA3无回连 (SPRD) | iPhone热点无法连接 (Qualcomm) |
|------|--------|---------|------|
| 驱动平台 | RTL8852BS (`RTW:`) | SPRD SC2355 (`WCN Base`) | Qualcomm SM6225 (`cnss`) |
| 断开触发 | wpa_supplicant SIGSEGV | NetworkMonitor无网络标记 | IPv6 DNS无scope index |
| 核心崩溃信号 | signal 11 | N/A | N/A |
| 漫游行为 | 频繁FT roam级联 | 不漫游 (单AP) | N/A |
| disconnect reason | reason=1 locally_generated | reason=3 (deauth) | CMD_IP_CONFIGURATION_LOST |

## 修复方案

### P0: RTL8852BS 驱动 — 漫游候选选择修复

当前AP条目`[age]`时，使用已记录的connected_rssi作为delta比较基准：
```c
// rtw_select_roaming_candidate() 伪代码
if (cur_network->age_flag) {
    base_rssi = adapter->mlmepriv.connected_rssi;  // fallback到已知RSSI
} else {
    base_rssi = cur_network->signal;
}
if (candidate->signal < base_rssi + ROAM_RSSI_DELTA) {
    candidate->flag = CANDIDATE_DELTA;  // 正确过滤掉更差AP
}
```

### P1: wpa_supplicant SIGSEGV修复

1. 升级wpa_supplicant版本 (检查FT状态机相关CVE/修复)
2. 开启coredump获取精确调用栈 (AddressSanitizer build)
3. 检查 FT reassoc/disconnect handler 内存管理

### 短期缓解

增大漫游触发阈值，减少不必要的漫游扫描频次，避免长期漫游级联。

## 参考日志路径

`/home/quectel/Work/Log/yd盈达/弱网断开/`

详细分析报告: `wifi_analysis_report.md`
分析过程记录: `wifi_analysis_notes.md`
