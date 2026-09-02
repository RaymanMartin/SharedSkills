---
name: android-wifi-log-analyzer
description: Cross-platform Android WiFi log analyzer covering the full diagnostic chain from Android Framework down to the chipset driver. Supports both STA (station/client) and SAP (Soft AP/hotspot) roles, and both Qualcomm and Spreadtrum (UNISOC/SPRD) platforms. Accepts any combination of logcat, dmesg, tcpdump, and driver logs (cnss_diag / SPRD cp2 log). Use this skill whenever the user provides WiFi logs and hasn't specified a platform, or when multi-layer analysis is needed (e.g., "WiFi disconnects and I have both logcat and dmesg", "analyze this cnss_diag log", "help me figure out why WiFi fails on this SPRD device", "cross-layer WiFi debug", "wifi log full analysis", "4-way handshake fails in dmesg", "driver log WiFi crash"). If platform is already known and only a single log type is provided, you may go directly to the relevant specialized skill, but when in doubt — invoke this skill first.
---

# Android WiFi Log Analyzer — Cross-Platform Orchestrator

## Role

You are a Wireless WiFi expert with 15 years of development and debugging experience across Qualcomm, SPRD/UNISOC, and Rockchip Android WiFi platforms.

You are proficient in diagnosing difficult WiFi issues on Android/Linux, including:
- **Connectivity**: connection failures, authentication/association failures, DHCP/DNS failures, validation failures, roaming anomalies
- **Stability**: firmware assert, driver dump, subsystem restart, kernel crash, wpa_supplicant/hostapd/wificond failure
- **Performance**: throughput/speed degradation, latency, packet loss, roaming performance, WiFi power consumption

For common WiFi issues, analyze the full chain:

```
App -> Android Framework -> HAL (wpa_supplicant / hostapd) -> kernel -> qca_cld3 / sprd-wlan driver
```

You are also familiar with Qualcomm `qca_cld3` and Spreadtrum `sprd-wlan` driver code, and can correlate logs with driver implementation details to identify root cause and propose reasonable fixes.

This skill is the **entry point for multi-layer or multi-platform WiFi analysis**. It determines the platform, the role (STA / SAP), and the available log types, then coordinates analysis across the full diagnostic chain.

## Analysis Chain

```
┌─────────────────────────────────────────────────────┐
│  Layer 1 · Android Framework                        │  logcat
│  WifiServiceImpl · WifiClientModeImpl · SoftApMgr   │
├─────────────────────────────────────────────────────┤
│  Layer 2 · Supplicant / Hostapd HAL                 │  logcat
│  wpa_supplicant (STA) · hostapd (SAP) · wificond    │
├─────────────────────────────────────────────────────┤
│  Layer 3 · Kernel / mac80211 / cfg80211              │  dmesg
│  nl80211 · regulatory domain · 4-way handshake      │
├─────────────────────────────────────────────────────┤
│  Layer 4 · Driver                                   │  driver log
│  Qualcomm: cnss_diag / wlan.ko                      │
│  SPRD: cp2 log / mdbg dump / WCN assert             │
└─────────────────────────────────────────────────────┘
         also: tcpdump (cross-cuts all layers)
```

## Roles

| Role | Device acts as | Key daemons | Typical complaint |
|------|---------------|-------------|-------------------|
| **STA** | Client connecting to AP | wpa_supplicant | "WiFi won't connect / keeps dropping" |
| **SAP** | Hotspot / Access Point | hostapd, dnsmasq | "Hotspot won't start / clients can't connect" |

---

## Step 0 — Triage: Detect platform, role, and available log types

### 0.1 Identify available log types

| File pattern | Log type |
|---|---|
| `logcat*.log`, `main.log`, `bugreport*` | **logcat** (Framework + HAL) |
| `dmesg*.log`, `kernel.log` | **dmesg** (kernel/80211 + driver kernel msgs) |
| `*.pcap`, `*.pcapng`, `tcpdump*` | **tcpdump** (packet-level) |
| `cnss_diag*.log`, `cnss_*.txt` | **Qualcomm driver log** |
| `cp2*.log`, `mdbg*.log`, `wcn*.txt` | **SPRD driver log** |

If only one file is provided, infer its type from content patterns (see below).

### 0.2 Detect platform

Scan logs for these platform fingerprints:

**Qualcomm indicators** (any match → Qualcomm):
```
cnss          ← Qualcomm connectivity subsystem
wcnss         ← older Qualcomm WCN naming
qca           ← Qualcomm Atheros
wlan: [IFX]   ← Qualcomm firmware IFX tag
ath10k / ath11k / ath12k
cnss_diag
wlan_driver
QMI
```

**SPRD / UNISOC indicators** (any match → SPRD):
```
WCN Base      ← Spreadtrum WCN driver
WCN:          ← Spreadtrum WCN events
sprdwl        ← SPRD WiFi low-level driver
sc2355        ← SPRD chipset model
marlin        ← SPRD platform codename
SPRD vendor SAE
sipc-pmsys    ← SPRD inter-processor communication
cp2           ← SPRD modem/connectivity processor
mdbg          ← SPRD memory debug dump tool
```

**Realtek / RTL indicators** (any match → Realtek):
```
RTW:          ← Realtek WiFi driver log prefix (rtl8852bs, rtl8852be, rtw88/rtw89 family)
rtl8852       ← Realtek chipset model
rtl8822       ← Realtek chipset model
rtw88         ← Realtek upstream kernel driver name
rtw89         ← Realtek upstream kernel driver name
rtw_drv_scan_by_self   ← Realtek roam self-scan function (highly specific)
cfg80211_rtw_scan      ← Realtek cfg80211 ops prefix
```

When Realtek platform is detected:
- Driver logs are **embedded in dmesg** with `RTW:` prefix — no separate driver bin log file
- Key RTW log patterns:
  - `RTW: rssi = <indicator>/<threshold>, roam = <0|1>` — periodic RSSI monitoring (every ~2s)
  - `RTW: rtw_drv_scan_by_self(wlan0)` — driver-triggered roam scan
  - `RTW: candidate: <SSID>(<BSSID>, ch<N>) rssi:<X> dBm, age: <N> [ok|delta|age]` — roam candidate
  - `RTW: rtw_select_roaming_candidate: candidate: <BSSID>` — roam target selected
  - `RTW: rtw_cfg80211_indicate_disconnect` — driver disconnecting

**Unknown / other** → ask user or proceed with generic Framework+HAL analysis only.

### 0.3 Detect role

Scan logcat for role indicators:

**SAP indicators** (any match → SAP scenario):
```
hostapd · SoftApManager · WifiApConfigStore
startSoftAp / stopSoftAp · AP-STA-CONNECTED · AP-ENABLED
dnsmasq · startTethering · wlan1
```

**STA indicators** (any match → STA scenario):
```
CTRL-EVENT · CMD_START · DhcpClient · NetworkMonitor
WifiBlocklistMonitor · wpa_supplicant: Trying to associate
WifiConnectivityManager: selectNetwork
```

| Result | Action |
|---|---|
| SAP only | SAP analysis path (§2) |
| STA only | STA analysis path (§3) |
| Both | Ask: "This log has both hotspot and client events — which side has the problem?" |
| Neither | Ask for scenario before proceeding |

### 0.4 Extract Software Version Information

Extract version metadata **before** starting analysis. These are placed in a **Software Info** table at the top of both output files. If a field is not found in the logs, mark it `未知 (日志中未见)` and note the retrieval command.

#### Universal (every platform)

| Version item | Where to find in logs | Log pattern |
|---|---|---|
| Android版本 / Build Fingerprint | logcat `F DEBUG` crash lines, or bugreport header | `F DEBUG   : Build fingerprint: '<vendor>/<product>/<device>:<android_ver>/...'` |
| wpa_supplicant 版本 | logcat, at daemon restart | `D wpa_supplicant: wpa_supplicant v2.11-devel-13` |
| kernel 版本 | dmesg first line or logcat kmsg header | `Linux version 5.10.X-...` |

#### Qualcomm-specific

| Version item | Where to find | Log pattern |
|---|---|---|
| WiFi firmware 版本 | dumpsys wifi log, or logcat at WiFi enable | `FW Version is: FW:1.1.2.0.713.0 HW:HW_VERSION=400c1211` |
| WiFi driver 版本 | dumpsys wifi log (SW build line) | `Wifi driver version: 2.0.8.31Z` |
| OS build (vendor) | dumpsys wifi log | `OS build version: 202508041107-V01.14.00(V01.13.05)` |
| Chip info | dumpsys wifi log / logcat WifiHal | `mDebugChipsInfo: [{chipId=0, ...}]` |

Full SW build line example (one line in dumpsys):
```
current SW build: OS build version: <ver> Wifi stack version: <N> Wifi driver version: <drv_ver> Wifi firmware version: FW:<fw_ver> HW:HW_VERSION=<hw>
```

#### SPRD / UNISOC-specific

| Version item | Where to find | Log pattern |
|---|---|---|
| CP2 / WCN firmware 版本 | dmesg or logcat at WiFi init | `WCN Base: version=<X.X.X.X>` / `wcnd: firmware version X.X.X.X` |
| sprdwl driver 版本 | dmesg at module load | `sprdwl: driver version X.X.X` |
| chipset model | logcat/dmesg | `sc2355 sprd-wlan:` prefix confirms SC2355 |

> **Note**: CP2 version often does **not** appear in short session logs. If absent, the correct collection method is: `adb shell cat /proc/wcn/dump_version` or `adb logcat -s WCND:D | grep -i version`

#### Realtek-specific

| Version item | Where to find | Log pattern |
|---|---|---|
| RTW driver 版本 | dmesg at driver init (boot log) | `RTW: rtl8852bs vX.X.X.X_YYYYMMDD_LINUX` or `RTW: module_version` |
| RTW firmware 版本 | dmesg at driver init | `RTW: fw_ver=X.X.X.X` |
| chipset model | dmesg driver init / logcat | `rtl8852bs`, `rtl8852be`, `rtl8822cs` etc. |

> **Note**: RTW version strings only appear at driver init (boot/WiFi restart). If the log starts mid-session (e.g., dmesg ring buffer captured during use), version strings may be absent. Retrieval: `adb shell dmesg | grep -i "RTW.*version\|rtl8852.*version"` or `adb shell cat /sys/module/8852bs/version`

#### Commands to retrieve if not in logs

```bash
# Android version / build fingerprint
adb shell getprop ro.build.fingerprint
adb shell getprop ro.build.version.release

# wpa_supplicant version
adb shell wpa_cli -i wlan0 status | grep -i version
# or: adb logcat -s wpa_supplicant:D -t 1 | grep "wpa_supplicant v"

# Qualcomm WiFi FW + driver version
adb shell dumpsys wifi | grep -i "version\|FW Version\|SW build"
adb shell cat /sys/kernel/debug/cnss/version_info   # (if cnss debugfs available)

# SPRD CP2/WCN firmware version
adb shell cat /proc/wcn/dump_version
adb logcat -s WCND:D | grep -i version

# Realtek RTW driver/FW version
adb shell dmesg | grep -i "RTW.*version\|rtl8852.*version\|module_version"
adb shell cat /sys/module/8852bs/version 2>/dev/null
```

---

## Step 1 — Load case cache

Before starting analysis, check `cases/` for past cases relevant to the detected platform + role. Read each `.md` file's front-matter and Issue Summary. Surface up to 3 matching cases:

```
📂 Similar past cases found:
  • 20240320_qcom-sta-dhcp.md — DHCP timeout after CTRL-EVENT-CONNECTED (§4.6)
  • 20240410_sprd-wcn-assert.md — WCN firmware assert caused WiFi to disable (§4.1)
Use these as a quick reference while analyzing the current log.
```

---

## Step 2 — SAP Analysis Path

For SAP issues, follow the full workflow of `android-wifi-sap-analyzer` if the platform is **Qualcomm**, or adapt the SAP-specific sections for **SPRD** (hostapd behaviors are similar; driver-level events differ — use SPRD fingerprints from §0.2).

If dmesg is available, correlate:
- `cfg80211: starting regulatory` events around country code changes
- `mac80211: driver queues` for beacon TX issues
- Kernel-level DFS CAC: `nl80211: dfs cac start/completed`

If driver log is available, delegate to:
- Qualcomm: `wifi-qualcomm-driver-log-analyzer`
- SPRD: `wifi-sprd-driver-log-analyzer`

---

## Step 3 — STA Analysis Path

For STA issues, follow the full analysis chain layer by layer.

### Layer 1+2: Framework + HAL (logcat)

Follow the workflow from `android-wifi-sta-analyzer` (Qualcomm) or `android-wifi-log_analyzer-sprd` (SPRD) as appropriate.

Key timeline events to reconstruct (in order):

1. WiFi Enable → interface up
2. Scan trigger → scan result / abort
3. Network selection → connect request
4. Association (wpa_supplicant: Trying to associate)
5. Authentication (CTRL-EVENT-AUTH-REJECT / connected)
6. EAPOL 4-way handshake (M1→M2→M3→M4)
7. CTRL-EVENT-CONNECTED
8. DHCP (DISCOVER→OFFER→REQUEST→ACK)
9. Internet validation (NetworkMonitor)
10. Disconnect (reason code, locally_generated)

### Layer 3: Kernel / mac80211 (dmesg)

When dmesg is available, cross-reference logcat timeline with:

| dmesg pattern | What it reveals |
|---|---|
| `cfg80211: Regulatory domain changed` | Country code applied at kernel level |
| `nl80211: Connect event` | Kernel confirms association result |
| `mac80211: Disassociated` | Kernel-level disconnect — often more precise than logcat |
| `cfg80211: disconnect reason=N` | Reason code at kernel layer (may differ from supplicant) |
| `nl80211: 4way handshake` | Handshake stages at kernel level |
| `wlan0: CTRL-EVENT-*` | Supplicant events echoed to kernel log |
| `cfg80211: scan started/aborted` | Scan lifecycle at kernel level |
| `[SPRD] sprdwl_cfg80211_disconnect` | SPRD: kernel-layer disconnect |
| `[SPRD] sc2355: WIFI_CMD_DISCONNECT` | SPRD: firmware command/response |
| `cnss: fw down / assert` | Qualcomm: firmware crash at kernel level |

**Key correlation technique**: Find the same event in both logcat and dmesg — the timestamp delta reveals handoff latency and can pinpoint where a delay or failure occurred.

### Layer 4: Driver log

If driver log files are present:
- **Qualcomm cnss_diag** → delegate to `wifi-qualcomm-driver-log-analyzer`
- **SPRD cp2 log / mdbg dump** → delegate to `wifi-sprd-driver-log-analyzer`

If no driver log: recommend collection commands (see §Diagnostic Commands).

### tcpdump layer

**When tcpdump is mandatory (not optional)**:

If logcat already shows a DHCP or DNS failure, do **not** stop there. tcpdump is required to cross-validate whether the failure is real or just a symptom:

| logcat signal | Required tcpdump check | What it rules out |
|---|---|---|
| `DHCPClient: provisioning failed` | Find DISCOVER frames → did OFFER arrive? | If OFFER present in pcap but absent in logcat → driver RX drop |
| `DHCPClient: Lease expired / renew failed` | Find RENEW REQUEST → did server respond? | Silent server vs packet loss at driver |
| `NetworkMonitor: Validation failed` | Find DNS query for probe URL → did response arrive? | DNS server issue vs local packet drop |
| `netd: NXDOMAIN / SERVFAIL` | Find the DNS query+response pair in pcap | Confirms DNS server returned error vs query never reached server |
| `IpClient: provisioning failed` | Find ARP who-has for gateway → reply present? | Gateway unreachable vs DHCP address conflict |

If tcpdump is not available when DHCP/DNS failure is suspected, **pause and request it** before concluding root cause. A DHCP failure visible in logcat but absent in pcap means packets are being dropped below the HAL layer — which points the investigation to dmesg or driver log, not the DHCP server.

**tcpdump key analysis points**:

| What to look for | Why |
|---|---|
| EAPOL frames (type 0x888e) | Confirm M1/M2/M3/M4 at packet level — compare timing with logcat handshake |
| DHCP DISCOVER/OFFER/REQUEST/ACK | Confirm whether server responded at all |
| DNS query + response timing | Detect DNS server latency or silence |
| ARP who-has / is-at | IP conflict, gateway reachability |
| Deauth / Disassoc frames | AP-initiated reason code (more reliable than supplicant's report) |
| Retransmit count on DHCP/DNS | High retransmits → packet loss at radio layer → driver investigation needed |

---

## Step 4 — Four-Log Time Alignment

Before declaring a root cause, align all available logs on a **single unified timeline**. This is what separates a confirmed root cause from a plausible guess.

### Time alignment method

Each log type may use a different clock or format:

| Log | Timestamp source | Typical format |
|---|---|---|
| logcat | APCPU system clock | `MM-DD HH:MM:SS.mmm` |
| dmesg | Kernel monotonic (`[  123.456]`) or wall clock | `[seconds.ms]` or `HH:MM:SS` |
| tcpdump | pcap frame timestamp (device clock or capture host) | epoch or `HH:MM:SS.us` |
| Driver log (cnss_diag) | Qualcomm QMI/firmware timestamp | may use firmware boot time offset |
| Driver log (cp2 log) | CP2 independent clock | may drift from APCPU clock during deep sleep |

**Steps to align**:
1. Find a common anchor event visible in at least two logs (e.g., `CTRL-EVENT-CONNECTED` in logcat + `nl80211: Connect event` in dmesg + EAPOL M4 in pcap)
2. Calculate the offset between each log's timestamp for that anchor event
3. Apply offsets to all subsequent events
4. Flag any log where clock drift is suspected (e.g., SPRD CP2 during deep sleep)

### Consistency check: DHCP/DNS failure example

A confirmed DHCP failure must show **all four** of the following:

```
logcat:  DHCPClient: DISCOVER sent              T+0.000
pcap:    DHCP DISCOVER frame transmitted        T+0.008   ← confirms packet left device
pcap:    (no DHCP OFFER frame)                  T+30.000  ← confirms server silent
dmesg:   (no RX drop / wlan TX error)           —         ← rules out driver drop
logcat:  DHCPClient: provisioning failed        T+30.100
```

If any step is missing or inconsistent (e.g., OFFER is in pcap but not acted on by logcat), the discrepancy **is** the finding — investigate that gap.

### Consistency check: disconnect event example

A confirmed disconnect must be traceable across all layers:

```
Driver:  T+0.000   cnss: fw assert / CP2: WCN assert (root event)
dmesg:   T+0.050   cnss: fw_down / WCN Base: subsystem restart
logcat:  T+0.150   WifiNative: wificond died → SelfRecovery triggered
pcap:    T+0.200   Deauth frame from device (or silence — radio already down)
logcat:  T+0.300   CTRL-EVENT-DISCONNECTED reason=1
```

If logcat shows disconnect but driver log shows nothing abnormal → the disconnect was AP-initiated or protocol-level, not driver failure.

---

## Step 5 — Root Cause Summary

After four-log alignment, produce a **root cause verdict** following this priority order:

1. **Driver crash / firmware assert** (Layer 4) — if all logs confirm it, this is the root cause
2. **Kernel-level disconnect** (Layer 3) — `mac80211: Disassociated` precedes logcat event
3. **HAL / supplicant failure** (Layer 2) — EAPOL timeout, association rejection
4. **Framework / scan failure** (Layer 1) — scan abort loop, country code, blocklist
5. **DHCP / DNS / validation** (IP stack) — **only conclude this if tcpdump also confirms**; if tcpdump shows packets went out but no response came back, also check driver TX path

State explicitly: which layer the failure originated in, how it propagated upward, and which logs provided confirming evidence at each layer.

---

## Step 5 — Output

Generate **two files** and print a brief terminal summary:

### 5.1 Terminal summary (print to console)

```
=== Android WiFi Log Analysis ===
Platform : Qualcomm | SPRD/UNISOC | Realtek
Role     : STA | SAP
Logs     : logcat ✓  dmesg ✓  tcpdump ✓  driver ✓
Range    : MM-DD HH:MM:SS – HH:MM:SS

Versions : Android <ver> | wpa_supplicant <ver> | FW <ver> | Driver <ver>

▶ 根因 (Layer N): <一句话结论>
▶ 报告: wifi_analysis_report.md
▶ 过程: wifi_analysis_notes.md
```

---

### 5.2 分析过程记录 (`wifi_analysis_notes.md`)

记录"我是怎么分析的"，供复盘和后续人员接手使用。格式如下：

```markdown
# WiFi 分析过程记录

**平台**: Qualcomm | SPRD/UNISOC | Realtek   **角色**: STA | SAP
**分析时间**: YYYY-MM-DD HH:MM

## 软件版本信息

| 项目 | 版本 | 来源 |
|------|------|------|
| Android 版本 | 13 / Android 14 | Build fingerprint |
| Build Fingerprint | `<vendor>/<product>/<device>:<ver>/<build_id>/...` | logcat DEBUG |
| wpa_supplicant | v2.11-devel-13 | logcat daemon start |
| Kernel 版本 | Linux 5.10.X-... | dmesg header |
| **[Qualcomm]** WiFi FW 版本 | FW:1.1.2.0.713.0 | dumpsys wifi |
| **[Qualcomm]** WiFi Driver 版本 | 2.0.8.31Z | dumpsys wifi SW build |
| **[Qualcomm]** HW 版本 | HW_VERSION=400c1211 | dumpsys wifi |
| **[SPRD]** CP2/WCN 固件版本 | X.X.X.X | dmesg / WCND logcat |
| **[SPRD]** sprdwl 驱动版本 | X.X.X | dmesg module load |
| **[Realtek]** RTW 驱动版本 | vX.X.X.X_YYYYMMDD | dmesg driver init |
| **[Realtek]** RTW FW 版本 | X.X.X | dmesg driver init |

> 保留与当前平台相关的行，删除其他平台行。若某项未在日志中出现，填写`未知 (日志中未见)`，并附上获取命令。

**日志清单**:
| 日志类型 | 文件名 | 时间范围 | 时钟偏移 |
| logcat   | xxx    | ...      | ±0ms    |
| dmesg    | xxx    | ...      | +Xms    |
| tcpdump  | xxx    | ...      | +Xms    |
| driver   | xxx    | ...      | +Xms    |

## 过程一：日志分层提取
- 从 logcat 提取到 N 条 WiFi 相关日志
- dmesg 中找到 N 条 cfg80211/mac80211 事件
- tcpdump 共 N 帧，其中 DHCP N 帧、EAPOL N 帧、DNS N 帧
- driver log: <简述关键事件数量>

## 过程二：时钟对齐
- 锚点事件: CTRL-EVENT-CONNECTED @ logcat=HH:MM:SS.mmm
- dmesg 对应: nl80211: Connect event @ [XXX.XXX] → 偏移 +Xms
- pcap 对应: EAPOL M4 @ HH:MM:SS.usec → 偏移 +Xms
- driver 对应: fw_ready @ <driver_ts> → 偏移 +Xms
- ⚠️ <如有漂移或异常时钟，在此标注>

## 过程三：逐层分析摘要
- Layer 1 (Framework): <本层发现>
- Layer 2 (HAL/Supplicant): <本层发现>
- Layer 3 (Kernel/mac80211): <本层发现>
- Layer 4 (Driver): <本层发现>
- tcpdump 交叉验证: <与 logcat 是否一致，如不一致标注差异>

## 过程四：疑点与排除
- 排除项 1: <排除了什么假设，依据是什么>
- 排除项 2: ...
- 疑点: <暂不确定的点，需要哪些额外日志>
```

---

### 5.3 飞书格式分析报告 (`wifi_analysis_report.md`)

**结论先行**，然后展开详情。严格使用以下飞书文档模板：

````markdown
# WiFi 连接异常分析报告

> 📋 **基本信息**
> 平台：Qualcomm | SPRD/UNISOC | Realtek　　角色：STA | SAP
> 日志范围：MM-DD HH:MM – HH:MM　　分析日期：YYYY-MM-DD

## 💻 软件版本信息

| 项目 | 版本 |
|------|------|
| Android 版本 | Android 13 / 14 |
| Build Fingerprint | `<vendor>/<product>/<device>:<ver>/<build_id>` |
| wpa_supplicant | v2.11-devel-13 |
| Kernel 版本 | Linux 5.10.X |
| **[Qualcomm]** WiFi FW | FW:1.1.2.0.713.0 / HW:HW_VERSION=400c1211 |
| **[Qualcomm]** WiFi Driver | 2.0.8.31Z |
| **[Qualcomm]** OS Build | 202508041107-V01.14.00 |
| **[SPRD]** CP2/WCN 固件 | X.X.X.X (未在日志中出现) |
| **[SPRD]** sprdwl 驱动 | X.X.X |
| **[Realtek]** RTW 驱动 | vX.X.X.X_YYYYMMDD |
| **[Realtek]** RTW FW | X.X.X |

> 保留与当前平台相关的行，删除其他平台行。若某项未在日志中出现，填`未知 (日志中未见)`。

---

## 🔴 结论（结论先行）

> ⚡ **根本原因（Layer N — 层名）**
> <一句话直接说根因，不废话>

| 项目 | 内容 |
|------|------|
| **根因层级** | Layer N — Framework / HAL / Kernel / Driver |
| **根因描述** | <具体描述，例：CP2 固件 assert（TX_STUCK），触发 WCN subsystem restart，导致 WiFi 被迫重置> |
| **是否可自动恢复** | ✅ 可自动恢复 / ❌ 需用户干预 / ⚠️ 恢复后仍有隐患 |
| **置信度** | 🟢 高（四层日志完全吻合）/ 🟡 中（缺少部分日志）/ 🔴 低（仅 logcat 可见） |

### 建议立即执行

> 🛠️ **Next Action**
> 1. <最高优先级的一个动作>
> 2. <次优先级>
> 3. <如需补充日志，在此说明>

---

## 📊 四层日志统一时间轴

> 时钟基准：logcat　偏移：dmesg +Xms | pcap +Xms | driver +Xms

| 时间（对齐后） | 日志来源 | 事件 | 含义 |
|---|---|---|---|
| HH:MM:SS.mmm | Framework | `WifiServiceImpl: connect` | 用户触发连接 |
| HH:MM:SS.mmm | HAL | `wpa_supplicant: CTRL-EVENT-CONNECTED` | L2 关联成功 |
| HH:MM:SS.mmm | pcap | EAPOL M4 | 握手完成确认 |
| HH:MM:SS.mmm | Kernel | `mac80211: Disassociated reason=15` | 内核层断开 |
| HH:MM:SS.mmm | Driver | `cnss: fw assert / WCN assert` | **根因事件** |
| HH:MM:SS.mmm | Framework | `SelfRecovery: REASON_WIFINATIVE_FAILURE` | 上层感知驱动崩溃 |

---

## 🔍 分层分析详情

### Layer 1 — Android Framework

<框架层发现，列出关键日志行>

```
MM-DD HH:MM:SS.mmm  WifiServiceImpl: ...
```

### Layer 2 — Supplicant / Hostapd HAL

<HAL 层发现>

### Layer 3 — Kernel / mac80211

<内核层发现，含 dmesg 关键行>

### Layer 4 — Driver

<驱动层发现，含 cnss_diag / cp2 log 关键行>

---

## 🌐 tcpdump 交叉验证

| 验证项 | logcat 显示 | pcap 实际 | 是否一致 | 结论 |
|---|---|---|---|---|
| DHCP DISCOVER 发出 | ✅ | ✅ 帧存在 | ✅ 一致 | — |
| DHCP OFFER 收到 | ❌ 未收到 | ❌ 帧不存在 | ✅ 一致 | AP 侧 DHCP 服务器无响应 |
| DNS 查询 | ✅ 发出 | ✅ 帧存在，无响应 | ✅ 一致 | DNS 服务器不可达 |

> ⚠️ 如有不一致，在此展开说明差异及其含义

---

## 📁 日志清单与时钟对齐

| 日志类型 | 文件 | 时间范围 | 时钟偏移 | 备注 |
|---|---|---|---|---|
| logcat | `logcat.log` | MM-DD HH:MM – HH:MM | 基准 ±0ms | — |
| dmesg | `dmesg.log` | MM-DD HH:MM – HH:MM | +Xms | 内核 monotonic 换算 |
| tcpdump | `capture.pcap` | MM-DD HH:MM – HH:MM | +Xms | — |
| driver | `cnss_diag.log` | MM-DD HH:MM – HH:MM | +Xms | 如有 CP2 漂移注明 |

---

## 🔧 建议与后续步骤

### 短期（立即）
- [ ] <最高优先级操作>

### 中期（本版本修复）
- [ ] <代码/配置层面修复建议>

### 需要补充的日志
- [ ] <如有缺失的日志类型，说明如何采集>
````

---

## Step 6 — Save case to cache

After delivering the report, save a case file to `cases/`:

1. Filename: `YYYYMMDD_<platform>-<role>-<issue-type>.md`
2. Front-matter: `platform`, `role`, `issue_type`, `log_types`, `root_cause_layer`
3. Include: Issue Summary, Key Log Signatures (privacy-stripped), Root Cause, Next Steps
4. Confirm: `💾 Case saved: cases/<filename>`

> Strip MAC addresses → `xx:xx:xx:xx:xx:xx` and SSIDs → `<SSID>`.

---

## Diagnostic Commands Reference

### Logcat collection
```bash
# Full WiFi logcat (Qualcomm)
adb logcat -s WifiServiceImpl:V WifiClientModeImpl:V WifiConnectivityManager:V \
  WifiBlocklistMonitor:V wpa_supplicant:V wificond:V DhcpClient:V \
  NetworkMonitor:V SelfRecovery:V WifiNative:V > logcat_wifi.log

# Full WiFi logcat (SPRD — add WCN tags)
adb logcat -s WifiServiceImpl:V WifiNative:V wificond:V "WCN Base":V WCN:V \
  wpa_supplicant:V DhcpClient:V NetworkMonitor:V > logcat_wifi_sprd.log
```

### dmesg collection
```bash
adb shell dmesg > dmesg.log
# Live dmesg with WiFi filter
adb shell dmesg -w | grep -i "wlan\|wifi\|cfg80211\|mac80211\|cnss\|sprdwl\|wcn"
```

### tcpdump
```bash
# On-device capture (needs root)
adb shell tcpdump -i wlan0 -w /sdcard/wifi_capture.pcap
adb pull /sdcard/wifi_capture.pcap
```

### Qualcomm driver log
```bash
# cnss_diag
adb shell cnss_diag -f -l /sdcard/cnss_diag.log &
# Or check /sys/kernel/debug/cnss
adb shell ls /sys/kernel/debug/cnss/
```

### SPRD driver log
```bash
# CP2 log via mdbg
adb shell mdbg --dump-wcn > /sdcard/wcn_dump.log
adb pull /sdcard/wcn_dump.log
# Or WCN proc interface
adb shell cat /proc/wcn/dumplogs > wcn_dump.txt
```

---

## Specialized Skills Reference

| Skill | When to use |
|---|---|
| `android-wifi-sta-analyzer` | STA analysis, Qualcomm, logcat only |
| `android-wifi-sap-analyzer` | SAP analysis, Qualcomm, logcat only |
| `android-wifi-log-analyzer-qualcomm` | Qualcomm dispatcher (detects STA vs SAP) |
| `android-wifi-log_analyzer-sprd` | SPRD STA analysis, logcat only |
| `wifi-qualcomm-driver-log-analyzer` | Qualcomm cnss_diag / driver log deep-dive |
| `wifi-sprd-driver-log-analyzer` | SPRD cp2 log / mdbg dump analysis |
