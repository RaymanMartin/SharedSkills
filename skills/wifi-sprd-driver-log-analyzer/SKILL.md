---
name: wifi-sprd-driver-log-analyzer
description: "Deep-dives into Spreadtrum (UNISOC/SPRD) WiFi driver logs — CP2 log, mdbg dumps, WCN assert/coredump, and sc2355/marlin kernel messages — to diagnose issues invisible at the logcat layer. Use when the user provides SPRD cp2 logs, mdbg dump files, WCN coredump data, or dmesg sections with sprdwl/sc2355/WCN patterns from a Spreadtrum (UNISOC) platform. Triggers: cp2 log, SPRD driver log, WCN assert, WCN coredump, mdbg dump, sc2355 crash, sprdwl error, SPRD WiFi firmware, UNISOC driver log, marlin WiFi crash, sipc WiFi. Also invoke when android-wifi-log-analyzer or android-wifi-log_analyzer-sprd reaches a driver-layer failure on SPRD platform."
---

# WiFi SPRD Driver Log Analyzer

Diagnoses WiFi failures at the **Spreadtrum (UNISOC) driver and CP2 firmware layer** by analyzing cp2 logs, mdbg dumps, WCN assert/coredump events, and sprdwl/sc2355 kernel messages.

## Scope

- **Platform**: Spreadtrum (UNISOC) WCN chipsets (sc2355, marlin2, marlin3, etc.)
- **Log types**: CP2 log, mdbg dump, WCN coredump, dmesg (sprdwl/WCN sections)
- **Roles**: STA and SAP (driver layer is shared)
- **Architecture**: SPRD uses a dedicated connectivity processor (CP2) that runs WiFi firmware separately from the application CPU (APCPU). Communication is via SIPC (Spreadtrum Inter-Processor Communication).
- **Relates to**: `android-wifi-log-analyzer` (upper layers), `android-wifi-log_analyzer-sprd`

---

## SPRD Architecture Overview

```
┌─────────────────────┐        ┌──────────────────────┐
│   APCPU (Android)   │        │   CP2 (ConnProc)     │
│                     │        │                      │
│  sprdwl.ko          │◄──────►│  WiFi Firmware       │
│  (kernel driver)    │  SIPC  │  (sc2355/marlin)     │
│                     │  SMSG  │                      │
│  WCN Base (kernel)  │        │  802.11 MAC/PHY      │
└─────────────────────┘        └──────────────────────┘
         ↑
    /proc/wcn/
    mdbg interface
    WCN coredump
```

CP2 runs autonomously. When CP2 crashes or asserts, the APCPU receives a SIPC interrupt and the WCN Base driver triggers subsystem recovery.

---

## Log Type Identification

| Pattern | Log type |
|---|---|
| `[CP2]` prefix or `cp2_` filename | CP2 firmware log (SPRD-specific) |
| `sprdwl_` functions | sprdwl kernel driver (dmesg) |
| `sc2355:` or `sc2355_` | sc2355 chipset kernel messages |
| `WCN Base:` / `WCN:` | WCN Base Android kernel driver |
| `mdbg:` / `mdbg_recv` | mdbg inter-processor debug interface |
| `sipc-pmsys` | SIPC power management wake events |
| `WIFI_CMD_` / `WIFI_EVENT_` | CP2↔APCPU command/event protocol |
| Hex dump with `WCN coredump` header | WCN crash dump |

---

## Step 1 — Locate and Load Log

- Accept: `cp2*.log`, `mdbg*.log`, `wcn*.txt`, dmesg with sprdwl/WCN sections, coredump files
- Note CP2 log time format (may differ from APCPU time — check `APCPU time offset` header if present)
- Identify chipset: sc2355 (common in SC9863A/T610) vs marlin (older platforms)
- Check if log was captured continuously or in fragments

---

## Step 2 — Extract Key Events

### WCN Driver (APCPU side — from dmesg / logcat WCN tags)

```
WCN Base: chip power on/off       ← WiFi radio power state
WCN Base: subsystem restart       ← CP2 recovery triggered from APCPU
WCN Base: assert                  ← CP2 crash signal received
WCN: coredump                     ← CP2 crash dump collection started
WCN: assert triggered             ← APCPU received CP2 assert interrupt
WCN Base: firmware ready          ← CP2 re-initialized after recovery
mdbg: CP2 assert                  ← mdbg interface received assert notice
sipc-pmsys-mpm-6: wakeup          ← CP2 woke APCPU (SIPC IRQ)
```

### sprdwl kernel driver (from dmesg)

```
sprdwl_cfg80211_connect            ← connection request to firmware
sprdwl_cfg80211_disconnect         ← disconnect request to firmware
sprdwl_cfg80211_scan               ← scan request (note n_channels)
sprdwl_report_disconnection        ← firmware reported disconnect to kernel
sprdwl_report_connection           ← firmware reported connect result
sc2355: WIFI_CMD_CONNECT           ← command sent to CP2
sc2355: WIFI_EVENT_CONNECT         ← CP2 response to connect command
sc2355: WIFI_CMD_DISCONNECT        ← command sent to CP2
sc2355: WIFI_EVENT_DISCONNECT      ← CP2 response
sc2355: tx_queue_full              ← transmit queue stall
sc2355: rx_error                   ← receive path error
```

### CP2 log (firmware side)

```
[WiFi] connect request             ← AP association initiation
[WiFi] auth/assoc success/fail     ← 802.11 auth/assoc result
[WiFi] 4way handshake M1/M2/M3/M4 ← EAPOL handshake stages
[WiFi] disconnect reason=N         ← firmware-level disconnect reason
[WiFi] scan complete channels=N    ← scan result stats
[WiFi] channel switch              ← DFS/congestion triggered channel change
[PMF] deauth frame                 ← Protected management frame events
ASSERT                             ← Firmware assert (crash)
watchdog: timeout                  ← CP2 watchdog fired
malloc failed                      ← CP2 memory allocation failure
```

---

## Step 3 — Failure Pattern Analysis

### 3.1 WCN Assert / CP2 Crash

The most critical failure — CP2 firmware panicked.

**APCPU-side signature (dmesg/logcat)**:
```
WCN: assert triggered
WCN Base: chip power off
WCN Base: subsystem restart initiated
WifiNative: wificond died           ← Framework echo
SelfRecovery: trigger REASON_WIFINATIVE_FAILURE
```

**CP2 log signature (if available)**:
```
ASSERT: <reason string>
PC: 0xXXXXXXXX  LR: 0xYYYYYYYY
Call stack: ...
```

**Common CP2 assert reasons**:

| Reason | Likely cause |
|---|---|
| `WATCHDOG_TIMEOUT` | CP2 CPU stall — check for memory pressure |
| `MALLOC_FAILED` | CP2 heap exhausted — too many concurrent peers/requests |
| `TX_STUCK` | Transmit queue frozen — usually link quality issue |
| `RX_BUF_OVERFLOW` | High traffic + slow consumption by APCPU |
| `PMF_ASSOC_FAIL` | PMF-protected association failure (WPA3-SAE related) |
| `CHAN_SWITCH_FAIL` | DFS channel switch did not complete |
| `SMSG_TIMEOUT` | SIPC message timeout — APCPU-CP2 IPC broken |

**Recovery check**: After assert, look for:
- `WCN Base: firmware ready` → CP2 recovered → WiFi re-enabled
- Absence → CP2 stuck; check if `WCN Base: subsystem restart` was successful

---

### 3.2 SIPC / IPC Communication Failure

CP2 is alive but APCPU cannot communicate with it.

**Signature**:
```
mdbg: SMSG send timeout
sc2355: WIFI_CMD_* no response within NNms
WCN Base: smsg channel init timeout
sipc-pmsys-mpm-6: wakeup (abnormal frequency)
```

**Impact**: Commands from driver to firmware time out → WiFi HAL reports errors → Framework retries → eventually triggers recovery.

**Check**: `sipc-pmsys-mpm-6` wakeup events just before disconnect suggest CP2 was waking APCPU abnormally, possibly due to firmware activity before crashing.

---

### 3.3 Scan Path Issues (sprdwl layer)

**Signature**:
```
sprdwl_cfg80211_scan n_channels=N  ← check if 5GHz / 6GHz channels included
sc2355: scan timeout
WCN: scan_complete with 0 results
```

**REGDOM / channel interaction (SPRD-specific)**:
```
wpa_supplicant: CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN
```
When REGDOM becomes UNKNOWN, `sprdwl_cfg80211_scan` may be called with reduced channel list (no DFS / 5GHz). Cross-check `n_channels` count before and after REGDOM change.

**PNO (Passive Network Offload)**:
```
sprdwl: PNO enabled
sc2355: PNO scan result event
```
CP2 can run PNO scans independently while APCPU is in deep sleep. PNO results trigger reconnect, but REGDOM UNKNOWN limits which channels PNO scans.

---

### 3.4 4-Way Handshake at CP2 Level

The CP2 log may contain more detail about EAPOL stages than logcat.

**Expected sequence (from CP2 log)**:
```
[WiFi] EAPOL M1 received from AP
[WiFi] EAPOL M2 sent
[WiFi] EAPOL M3 received
[WiFi] EAPOL M4 sent
[WiFi] PTK installed
```

**Failure patterns**:
- M3 received but M4 not sent → CP2 TX path stall
- M1 received, no M2 → CP2 key derivation failure
- M3 timeout → AP-side issue (check dmesg `CTRL-EVENT-DISCONNECTED reason=15`)

**WPA3-SAE specific (SPRD)**:
```
[WiFi] SAE commit sent
[WiFi] SAE confirm sent
[WiFi] SAE auth success → PMK installed
SPRD vendor SAE IE len: 16       ← visible in upper logcat
SPRD SAE auth results-1/2/3
SPRD SAE completed
```
Failure in SAE commit/confirm exchange → WPA3 network cannot connect. Check CP2 log for `SAE timeout` or `SAE failure reason`.

---

### 3.5 Power Management / Deep Sleep Issues

**SPRD elapsed realtime freeze (critical bug pattern)**:

When APCPU enters deep sleep, `elapsed realtime` may pause (SPRD platform-specific behavior). This delays any timer-based reconnect logic (e.g., `WifiConnectivityManager Watchdog`) by the sleep duration.

**Diagnosis (from dmesg)**:
```
# Checkpoint 1 — Watchdog timer set after disconnect
AlarmManager: ... Watchdog Timer ... tElapsed=T1

# Checkpoint 2 — Actual reconnect
AlarmManager: waitForAlarm elapsedRealtime=T2
```

If `(T2 - T1)` >> wall clock difference → elapsed realtime froze during sleep → reconnect was delayed.

**CP2 log cross-check**: During the same interval, CP2 log may show:
- PNO scans running (CP2 is active independently)
- CP2 timestamp advancing normally (CP2 clock unaffected by APCPU sleep)

---

### 3.6 TX Queue Stall / Throughput Failure

**Signature**:
```
sc2355: tx_queue_full (count: N)
sc2355: WIFI_CMD_TX_DATA timeout
[WiFi] tx queue stuck for NNms
```

**Impact**: Upper layers see packet loss but WiFi stays connected. May eventually trigger `CTRL-EVENT-DISCONNECTED reason=34` (low ACK).

---

## Step 4 — Cross-Layer Correlation

Correlate CP2/driver events with logcat and dmesg:

1. Find CP2 assert timestamp → find `WCN: assert triggered` in dmesg → find `SelfRecovery` in logcat
2. Find CP2 `disconnect reason=N` → find `sprdwl_report_disconnection` in dmesg → find `CTRL-EVENT-DISCONNECTED` in logcat
3. Check CP2 clock vs APCPU clock alignment (they may drift during sleep)

**Timeline format**:
```
CP2 log:    HH:MM:SS.mmm  ASSERT: TX_STUCK
dmesg:      HH:MM:SS.mmm  WCN: assert triggered → subsystem restart
logcat:     HH:MM:SS.mmm  WifiNative: wificond died
logcat:     HH:MM:SS.mmm  SelfRecovery: REASON_WIFINATIVE_FAILURE
logcat:     HH:MM:SS+15s  WCN Base: firmware ready
```

---

## Step 5 — Output

### Terminal summary

```
=== SPRD WiFi Driver Log Analysis ===
Platform  : Spreadtrum (UNISOC) <chipset>
Log type  : cp2 log | mdbg dump | dmesg (sprdwl/WCN) | coredump
Time range: MM-DD HH:MM – HH:MM

WCN asserts        : N
SIPC IPC timeouts  : N
TX queue stalls    : N
Recovery attempts  : N (N successful)
CP2 clock drift    : <detected / not detected>

Root cause (CP2/driver layer): <one sentence>

Assert detail (if present):
  Reason : <reason string>
  PC     : 0xXXXXXXXX
  LR     : 0xYYYYYYYY
```

### Markdown report (`wifi_sprd_driver_report.md`)

```markdown
# WiFi SPRD Driver Log Analysis
**Platform**: Spreadtrum (UNISOC) <chipset>
**Log types**: <types analyzed>
**Analysis date**: <date>

## Summary
## CP2 Lifecycle Events
## WCN Assert / Crash Analysis
## SIPC / IPC Communication
## Scan Path Analysis
## 4-Way Handshake at CP2 Level
## WPA3-SAE CP2 Events
## Power Management / Deep Sleep
## TX/RX Path Issues
## Cross-Layer Correlation (CP2 ↔ dmesg ↔ logcat)
## Root Cause & Driver-Layer Verdict
## Recommended Next Steps
```

---

## Step 6 — Next-Step Recommendations

| Finding | Recommendation |
|---|---|
| WCN assert | Collect full mdbg dump: `adb shell mdbg --dump-wcn > /sdcard/wcn_dump.log`; analyze assert reason + PC |
| SIPC timeout | Check APCPU-CP2 power dependencies; verify SPRD platform voltage rails |
| REGDOM UNKNOWN | Add `WifiManager.setCountryCode()` after disconnect to restore correct REGDOM |
| Elapsed realtime freeze | Change WiFi Watchdog alarm from `ELAPSED_REALTIME` to `RTC_WAKEUP` |
| WPA3-SAE CP2 failure | Capture `sprd_cp2_log` during SAE auth; check PMF frame handling in CP2 firmware version |
| TX queue stall | Check link quality (RSSI/noise); reduce concurrent TX load; update CP2 firmware |

### Diagnostic Commands

```bash
# Collect CP2 / WCN log via mdbg
adb shell mdbg --dump-wcn > /sdcard/wcn_dump.log
adb pull /sdcard/wcn_dump.log

# WCN proc interface
adb shell cat /proc/wcn/dumplogs > wcn_proclog.txt

# Live dmesg filter for sprdwl/WCN events
adb shell dmesg -w | grep -E "sprdwl|sc2355|WCN|mdbg|sipc"

# Targeted logcat for SPRD WiFi driver interface
adb logcat -s "WCN Base":V WCN:V WifiNative:V SelfRecovery:V

# Check WCN power state
adb shell cat /proc/wcn/state

# SPRD CP2 log (if sprd_cp2_log tool available)
adb shell sprd_cp2_log --start --output /sdcard/cp2.log
# ... reproduce issue ...
adb shell sprd_cp2_log --stop
adb pull /sdcard/cp2.log

# Check SIPC channel state
adb shell cat /proc/sipc/*/state
```
