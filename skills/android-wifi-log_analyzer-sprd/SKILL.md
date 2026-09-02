---
name: android-wifi-log_analyzer-sprd
description: Analyzes Android WiFi logs on Spreadtrum (UNISOC) platforms to diagnose WiFi disconnection and connection failures. Filters key log components — WifiServiceImpl, DHCPClient, NetworkMonitor, WifiNative, Wificond, WCN Base, WCN, wlan0, wpa_supplicant, CTRL-EVENT, CMD_START — and reconstructs a full disconnect/connect timeline. Use when the user provides a WiFi log from a Spreadtrum/UNISOC device and reports issues like "WiFi disconnects", "WiFi won't reconnect", "WiFi keeps dropping", "no internet after reconnect", or "WiFi unstable".
---

# Android WiFi Log Analyzer — Spreadtrum (UNISOC)

Diagnoses WiFi **disconnection and reconnection** failures on **Spreadtrum (UNISOC)** platform devices by filtering Android logcat and building a structured analysis timeline.

## Scope

- **Platform**: Spreadtrum (UNISOC) WCN / WCN Base chipset
- **Role**: STA mode (device connecting to an AP/hotspot)
- **Android**: 10–14
- **Input**: `logcat.log` / `logcat.txt` / bugreport log file
- **Focus**: WiFi disconnect, reconnect, DHCP failure, internet validation failure

---

## Workflow

### Step 0 — Load case cache (do this before any analysis)

Before reading the log, scan the `cases/` directory (same folder as this SKILL.md) for past cases that may be relevant.

1. List all `.md` files in `cases/` (excluding `README.md` and `CASE_TEMPLATE.md`).
2. If the directory is empty or no cases exist, skip this step silently.
3. Read each case file's front-matter (`issue_type`, `root_cause_section`) and the **Issue Summary** line.
4. After the user provides the log file / describes the symptom, identify up to **3 most relevant** past cases and surface them briefly:

```
📂 Similar past cases found:
  • 20240320_wcn-crash.md      — WCN assert triggered by thermal stress, subsystem restart (§4.1)
  • 20240215_disconnect-loop.md — Reconnect loop every 90s, reason=34 (weak signal) (§4.4)
Use these as a quick reference while analyzing the current log.
```

5. Reference relevant past cases inline during analysis (e.g., "This matches the pattern in `20240320_wcn-crash.md`").

---

### Step 1 — Locate and load log

- Accept a single log file: `logcat.log`, `logcat.txt`, or any plain-text log file
- If multiple files provided, list them and ask the user which to analyze
- Note the log time range from first and last line timestamps

### Step 2 — Extract relevant lines

Filter for these keywords (case-insensitive where appropriate):

| Keyword | Pipeline stage |
|---|---|
| `WifiServiceImpl` | WiFi enable/disable, user connect/forget requests |
| `WifiNative` | HAL layer commands, driver interaction |
| `Wificond` / `wificond` | Scan trigger/abort, nl80211 events |
| `WCN Base` | Spreadtrum WCN base driver events (power, init, crash) |
| `WCN` | Spreadtrum WCN chipset low-level events |
| `wlan0` | Interface-level events (up/down, IP assignment) |
| `wpa_supplicant` | 802.11 association, EAPOL handshake, disconnect reason |
| `connect` | Connection request, connection result |
| `disconnect` | Disconnect events and reason codes |
| `DHCPClient` / `DhcpClient` | DHCP lease lifecycle |
| `NetworkMonitor` | Internet validation, captive portal detection |
| `CTRL-EVENT` | wpa_supplicant control events (connect, disconnect, scan, handshake) |
| `CMD_START` | wpa_supplicant command start events (driver command initiation) |

Collect all matching lines into a unified timeline sorted by timestamp.

---

### Step 3 — Build the disconnect/connect timeline

Reconstruct events across these stages in order:

1. **WiFi Enable / Interface Up**
   - `WifiServiceImpl: setWifiEnabled`
   - `wlan0: link becomes ready` / `ifconfig wlan0 up`

2. **Scan Phase**
   - `Wificond: Scan triggered` / `Scan result received`
   - `Wificond: Scan aborted` (abnormal — count occurrences)

3. **Connection Request**
   - `WifiServiceImpl: connect to network`
   - `WifiNative: startConnectToNetwork`
   - `wpa_supplicant: Trying to associate with`

4. **Association & Authentication**
   - `wpa_supplicant: Associated with`
   - `wpa_supplicant: CTRL-EVENT-CONNECTED`
   - `wpa_supplicant: CTRL-EVENT-DISCONNECTED reason=N`

5. **DHCP / IP Provisioning**
   - `DHCPClient: DISCOVER` → `OFFER` → `REQUEST` → `ACK`
   - `DHCPClient: provisioning success` / `provisioning failed`

6. **Internet Validation**
   - `NetworkMonitor: Validation succeeded`
   - `NetworkMonitor: Validation failed`
   - `NetworkMonitor: Captive portal detected`

7. **Disconnect Event**
   - Source: `wpa_supplicant: CTRL-EVENT-DISCONNECTED`
   - `locally_generated=1` (device-initiated) vs `locally_generated=0` (AP-initiated)
   - Reason code — see §4.3

8. **WCN Driver Events** (Spreadtrum-specific)
   - `WCN Base: chip power` on/off
   - `WCN: assert` / `WCN: coredump` — driver crash indicator
   - `WCN Base: subsystem restart` — recovery trigger

---

### Step 4 — Identify root cause

Work through these patterns in likelihood order:

---

#### 4.1 WCN Driver Crash / Assert (Spreadtrum-specific — check first)

If log contains `WCN: assert` or `WCN Base: coredump` / `subsystem restart`, the WiFi chip crashed:

```
WCN Base: chip power off
WCN: assert triggered
WCN Base: subsystem restart initiated
WifiNative: wificond died
WifiServiceImpl: WiFi state → DISABLING → DISABLED
```

**Root cause**: Firmware assert — collect `WCN` dump logs; check for memory/thermal stress.
**Symptom**: WiFi switch may auto-disable; `SelfRecovery` re-enables it.

---

#### 4.2 Scan Layer Failures

If no `CTRL-EVENT-CONNECTED` lines appear at all after a connect attempt:

- `Wificond: Scan aborted` repeated → scan blocked (driver busy or regulatory issue)
- `WifiNative: startScan failed` → HAL layer cannot trigger scan
- No scan results for target SSID → band/channel mismatch or AP out of range

**Diagnosis checklist**:
- Count `Scan aborted` — > 5 in 2 min is abnormal
- Check if `wlan0` interface was UP when scan was triggered
- Check WCN power state before scan

---

#### 4.3 Disconnect Reason Codes (wpa_supplicant)

```
wpa_supplicant: CTRL-EVENT-DISCONNECTED bssid=XX:XX:XX:XX:XX:XX reason=N locally_generated=Y
```

| Reason | Meaning | locally_generated |
|---|---|---|
| 1 | Unspecified | either |
| 2 | Previous auth no longer valid (AP rebooted) | 0 (AP) |
| 3 | Station leaving (normal roam/user disconnect) | 1 |
| 4 | Inactivity timeout (AP kicked device) | 0 |
| 15 | 4-way handshake timeout | 1 |
| 16 | Group key handshake timeout | 1 |
| 17 | RSN IE mismatch | 1 |
| 34 | Disassociated due to low ACK | 1 (weak signal) |

- `locally_generated=1` → device disconnected itself → check DHCP timeout, handshake failure, signal
- `locally_generated=0` → AP kicked device → check AP load, inactivity, auth mismatch

---

#### 4.4 Repeated Disconnect / Reconnect Loop

Pattern:
```
CTRL-EVENT-CONNECTED  →  (Ns later)  →  CTRL-EVENT-DISCONNECTED  →  reconnect
```

If this repeats > 3 times within 10 minutes:
- Check reason codes — consistent reason=34 → weak signal (move device closer)
- Check DHCP: is `DHCPClient: ACK` received each time? Missing ACK → DHCP server overload
- Check `NetworkMonitor: Validation failed` → AP has no internet → validation triggers disconnect
- Check WCN power events — thermal throttling can cause periodic chip reset

---

#### 4.5 DHCP Failure

```
DHCPClient: DISCOVER sent
(no OFFER received within 30s)
DHCPClient: provisioning failed
```

OR

```
DHCPClient: ACK received  →  DHCPClient: Lease expired  →  RENEW failed
```

- If **no OFFER**: DHCP server unreachable — AP/router side issue
- If **OFFER received but REQUEST rejected**: IP pool exhausted or duplicate IP conflict
- After DHCP failure → device may disconnect and blocklist the BSSID

---

#### 4.6 Internet Validation Failure

```
NetworkMonitor: Validation failed (result=NOMNOM / HTTP 599)
```

- DHCP succeeded but internet probe (HTTP 204) failed
- Causes: AP has no WAN uplink, DNS blocked, captive portal not dismissed
- Check DNS resolution: `netd` / `DnsProxyListener` lines for `NXDOMAIN` / `SERVFAIL`
- If `NetworkMonitor: Captive portal detected` → user must authenticate in browser

---

#### 4.7 Association / EAPOL Failures

- `CTRL-EVENT-ASSOC-REJECT status_code=N` → AP rejected (see §4.3 codes)
- `CTRL-EVENT-DISCONNECTED reason=15` → 4-way handshake timeout (wrong PSK or AP overload)
- `WifiNative: association error` → HAL-level rejection

---

#### 4.8 WPA3-SAE 断开后不自动回连 (Spreadtrum SPRD 特有)

**案例来源**: `references/case-wpa3-sae-disconnect-no-reconnect.md`

**现象**: WPA3-SAE 网络连接后断开，断后 20–30 分钟内无任何扫描/回连动作，需要 app 触发 `setWifiEnabled` 或用户手动操作才能恢复。

**诊断信号（断开阶段）**:

```
# Step 1: CP2/固件先行上报 + 上层竞争（SPRD特有竞争场景）
wpa_supplicant: nl80211: Was expecting local disconnect but got another disconnect event first
  → CP2/固件已先行上报断开，wpa_supplicant 的主动断开命令晚到
  → 通常伴随 PMKSA-CACHE-REMOVED（PMK缓存清除为上层断开的前兆）

# Step 2: 内核层断开序列
kernel: sprdwl_cfg80211_disconnect <SSID> reason:1  ← 上层通过cfg80211主动断开
kernel: sc2355: WIFI_CMD_DISCONNECT → WIFI_EVENT_DISCONNECT ← 固件应答
kernel: sprdwl_report_disconnection reason_code 0

# Step 3: wpa_supplicant 结果
wpa_supplicant: CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1

# Step 4: 断开前可能出现的 CP2 活动
kernel: PM: suspend aborted (wakeup: sipc-pmsys-mpm-6)  ← CP2 SIPC 唤醒 APCPU
  → 出现在断开前 ~10 秒 = CP2 侧有异常行为

# Step 5: 断开后 REGDOM 变化
wpa_supplicant: CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN ← 关键！
  → 监管域变为 UNKNOWN，wificond 可能将 5GHz DFS 信道从扫描列表移除
  → 与 WifiNative 报告的 CN 国家码存在不一致（两层 REGDOM 状态分裂）
```

**诊断信号（不回连阶段）**:

```
# 确认是否为 SPRD elapsed realtime 暂停导致 Watchdog 延迟
# 对比两个时间点的 elapsed realtime 增长 vs 挂钟增长：
AlarmManager: ... Watchdog Timer ... tElapsed=T1   (断开时)
AlarmManager: waitForAlarm elapsedRealtime=T2      (回连时)
  → 如果 (T2-T1) << 挂钟差值（秒） → 深睡期间 elapsed realtime 暂停了计时

# 确认25分钟空白（零扫描）
grep "sprdwl_cfg80211_scan\|Scan result ready event" log.txt   → 0条
grep "CMD_START_CONNECT" log.txt                               → 0条

# 确认回连是由 PNO（固件调度扫描）触发，非常规扫描
WifiNative: Pno scan result event   → 先于 CMD_START_CONNECT 出现
  → 说明 PNO 持续在固件层扫描，但受 REGDOM UNKNOWN 影响，25分钟才扫到5GHz AP
```

**两级根因**:

1. **断开原因（日志未完全揭示）**: CP2/固件内部事件（可能与PMF/PMKSA/链路质量相关）触发了下层断开，上层 wpa_supplicant 随后跟进，发生竞争。`PMKSA-CACHE-REMOVED` 是上层断开的直接前兆。具体 CP2 侧原因需从 `sprd_cp2_log`/`mdbg dump` 确认。

2. **不回连原因（已确认）**: SPRD APCPU 深睡期间 `elapsed realtime` 计时暂停 → `WifiConnectivityManager Watchdog Timer`（type=2）触发时间随之延后 → 整个 WiFi 扫描机制延迟约20分钟。叠加 `REGDOM UNKNOWN` 导致 PNO 无法扫描 5GHz 信道 → AP 在中间扫描中不可见 → 直到设备自然唤醒后全信道扫描才成功回连。

**SPRD WPA3-SAE 握手识别特征**:

```
# SAE 认证参数 (内核层)
wlan0: auth type 0x4                  ← SAE
wlan0: akm suites 0xfac08             ← SAE AKM suite 8
wlan0: management frame protection 0x1  ← PMF 强制
wlan0: wpa versions 0x2

# SPRD 定制 SAE 握手 (成功时出现3行)
wpa_supplicant: SPRD vendor SAE IE len: 16
wpa_supplicant: SPRD SAE auth results-1/2/3
wpa_supplicant: SPRD SAE completed - SET PMK for 4-way handshake
```

**修复方向**:
- **CP2侧断开**：抓取 `sprd_cp2_log` 分析 CP2 内部触发原因；检查 PMF 保护帧处理；检查 AP 侧是否存在大量 deauth（`deauth reason dump` 中 remote reason 次数）
- **不回连**：① 将 WiFi Watchdog Alarm 改为 `RTC_WAKEUP`（型号0）确保深睡唤醒；② 断开后立即重设国家码（`WifiManager.setCountryCode()`）修复 REGDOM UNKNOWN；③ 业务 App 使用 `ConnectivityManager.requestNetwork()` 保持 WiFi 激活

---

### Step 5 — Output

#### Terminal summary

```
=== WiFi Disconnect Analysis (Spreadtrum/UNISOC) ===
File: <path>  |  Range: MM-DD HH:MM – HH:MM

Disconnect events : N
WCN driver crashes: N
Scan aborts       : N
DHCP failures     : N
Root cause: <one sentence>

Key timeline:
  HH:MM:SS  [wpa_supplicant]  CTRL-EVENT-CONNECTED to AP xx:xx:xx
  HH:MM:SS  [WCN Base]        subsystem restart initiated
  HH:MM:SS  [WifiServiceImpl] WiFi DISABLING
  HH:MM:SS  [wpa_supplicant]  CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1
  HH:MM:SS  [DHCPClient]      provisioning failed
  HH:MM:SS  [NetworkMonitor]  Validation failed
```

#### Markdown report (`wifi_disconnect_analysis_sprd.md`)

```markdown
# WiFi Disconnect Analysis Report — Spreadtrum/UNISOC
**File**: <path>
**Platform**: Spreadtrum (UNISOC) WCN
**Android**: <version>
**Analysis date**: <date>

## Summary
## Event Timeline
## Disconnect Events & Reason Codes
## WCN Driver Events
## Scan Analysis
## DHCP / IP Provisioning
## Internet Validation
## Conclusion & Recommended Next Steps
```

---

### Step 6 — Save case to cache

After completing the analysis and delivering the report, **always** save a new case file:

1. Determine the `issue_type` from the root cause identified in Step 4 (use values from `cases/README.md`).
2. Generate filename: `YYYYMMDD_<issue-type>.md` using today's date. If a file with this name already exists, append `_2`, `_3`, etc.
3. Copy `cases/CASE_TEMPLATE.md`, fill in all fields, and save to `cases/<filename>`.
4. Populate:
   - **front-matter**: date, android version, issue_type, root_cause_section
   - **Issue Summary**: one-sentence symptom description
   - **Environment**: device/module, Android version, AP info, log filename
   - **Key Log Signatures**: 5–15 most diagnostic log lines (remove MAC addresses)
   - **Root Cause**: copy from the report's Conclusion section
   - **Resolution / Next Steps**: copy from the report's Recommended Next Steps section
5. Confirm to the user: `💾 Case saved: cases/YYYYMMDD_<issue-type>.md`

> **Privacy**: Strip full MAC addresses (replace with `xx:xx:xx:xx:xx:xx`) and real SSIDs (replace with `<SSID>`) before saving.

---

## Analysis Tips

- **`WCN: assert` present** → driver crash is root cause — all analysis starts here.
- **No `CTRL-EVENT-` lines** → failure at scan/HAL layer — check `Wificond` and `WifiNative`.
- **reason=34 (`locally_generated=1`)** → weak signal causing low ACK rate → physical issue.
- **DHCP gap > 30s** → AP/router DHCP server problem, not the device.
- **Repeated validation failures** → AP has no internet, not a device WiFi issue.
- **`WCN Base: chip power off` without user action** → thermal or driver watchdog reset.
- **`nl80211: Was expecting local disconnect but got another disconnect event first`** → CP2/固件先行上报断开，上层存在竞争。检查 `PMKSA-CACHE-REMOVED` 和内核 `sprdwl_cfg80211_disconnect`（§4.8）。
- **`PM: suspend aborted (wakeup: sipc-pmsys-mpm-6)` 出现在断开前 ~10s** → CP2 SIPC 活动是断开的外部触发信号，需抓 CP2 日志确认。
- **断后无任何 CMD_START_CONNECT / sprdwl_cfg80211_scan 日志** → 先对比 `tElapsed`（Watchdog设置时）和 `elapsedRealtime`（回连时）的增量：若 elapsed 增量 << 挂钟增量 → SPRD 深睡期间 elapsed realtime 暂停，Watchdog 实际延迟触发（§4.8）。
- **`CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN`** → 5GHz 信道扫描受限。检查 `sprdwl_cfg80211_scan n_channels` 是否含 5GHz；WifiNative 的 `onSetCountryCodeSucceeded: CN` 可能与此不一致（§4.8）。
- **回连由 `Pno scan result event` 触发而非常规 `Scan result ready event`** → 框架层在空白期间依赖 PNO（固件调度扫描），而非常规扫描（§4.8）。
- **`SPRD SAE completed`** → WPA3-SAE 握手成功，连接层无问题，排查验证/路由层。
- **`deauth reason dump: remote reason[0]: N times`** → 累积 AP 侧 deauth 次数（SPRD独有），N > 10 且原因不明时关注 PMF/链路质量问题。

---

## Diagnostic Commands (for "Next Steps" recommendations)

```bash
# Targeted logcat for disconnect diagnosis (Spreadtrum)
adb logcat -s WifiServiceImpl:V WifiNative:V wificond:V wpa_supplicant:V \
  DHCPClient:V NetworkMonitor:V WCN:V "WCN Base":V

# Interface state
adb shell ip link show wlan0
adb shell ip addr show wlan0

# WiFi status dump
adb shell cmd wifi status
adb shell cmd wifi dump > wifidump.txt

# Country code
adb shell cmd wifi get-country-code
adb shell iw reg get

- **WPA3-SAE specific** (`SPRD SAE`):
  ```
  SPRD vendor SAE IE / SPRD SAE auth results-1/2/3 / SPRD SAE completed
  auth type 0x4 / akm suites 0xfac08 / management frame protection 0x1
  ```

# WCN driver log (Spreadtrum)
adb shell cat /proc/wcn/dumplogs > wcn_dump.txt

# DHCP lease info
adb shell getprop dhcp.wlan0.result
adb shell getprop dhcp.wlan0.ipaddress
```
