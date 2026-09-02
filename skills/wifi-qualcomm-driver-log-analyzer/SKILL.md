---
name: wifi-qualcomm-driver-log-analyzer
description: "Deep-dives into Qualcomm WiFi driver logs — cnss_diag, wlan kernel messages, QMI traces, and firmware crash dumps — to diagnose issues that are invisible at the logcat/HAL layer. Use when the user provides cnss_diag logs, /sys/kernel/debug/cnss dumps, wlan.ko kernel messages, or firmware assert/crash files from a Qualcomm (QCN/WCN/QCA series) platform. Triggers: cnss_diag log, Qualcomm firmware crash, wlan assert, cnss assert, fw down, QMI error in WiFi, Qualcomm driver log, wlan.ko, ath10k/ath11k crash, wcnss assert, cnss dump. Also invoke this skill when android-wifi-log-analyzer or android-wifi-sta/sap-analyzer reaches a driver-layer failure and needs deeper analysis."
---

# WiFi Qualcomm Driver Log Analyzer

Diagnoses WiFi failures at the **Qualcomm driver and firmware layer** by analyzing cnss_diag logs, kernel wlan messages, QMI traces, and firmware crash/assert events.

## Scope

- **Platform**: Qualcomm QCN/WCN chipsets (QCA6390, QCN9074, WCN6855, WCN7850, etc.)
- **Log types**: cnss_diag log, kernel dmesg (cnss/wlan sections), firmware crash dump, QMI trace
- **Roles**: STA and SAP (driver layer is shared)
- **Relates to**: `android-wifi-log-analyzer` (upper layers), `android-wifi-sta-analyzer`, `android-wifi-sap-analyzer`

---

## Log Type Identification

| Pattern in file | Log type |
|---|---|
| `cnss_diag:` prefix lines | cnss_diag userspace log |
| `cnss: ` or `cnss2: ` | Kernel cnss driver messages (from dmesg) |
| `wlan: ` or `[wlan]` | Qualcomm wlan.ko kernel driver |
| `ath10k:` / `ath11k:` / `ath12k:` | Open-source Qualcomm drivers |
| `QMI` or `qmi_wlanfw` | QMI firmware interface messages |
| `CNSS_WLAN_FW_ASSERT` | Firmware assert event |
| Hex dump blocks with `fw_assert` header | Firmware crash dump |

---

## Step 1 — Locate and Load Log

- Accept: `cnss_diag*.log`, `dmesg*.log` (filter cnss/wlan sections), `ath10k/ath11k/ath12k` logs, firmware crash dumps
- Note time range from first and last timestamps
- Identify cnss generation: cnss vs cnss2 (newer PCIe-based)
- Check if multiple log segments exist (fragmented captures)

---

## Step 2 — Extract Key Events

Filter for these critical patterns:

### Firmware lifecycle
```
cnss: fw_boot_timeout             ← firmware failed to boot within timeout
cnss: fw_down                     ← firmware went offline
cnss: CNSS_WLAN_FW_ASSERT         ← firmware assert (crash)
cnss: fw_ready                    ← firmware came up successfully
cnss: fw_init_done                ← firmware initialization complete
cnss: cold_boot_cal               ← calibration phase
cnss: pci_link_down               ← PCIe link lost (hardware level)
cnss: recovery_in_progress        ← subsystem recovery started
cnss: recovery_done               ← subsystem recovery complete
```

### QMI / firmware interface
```
qmi_wlanfw: QMI encode error      ← QMI message malformed
qmi_wlanfw: QMI send req timeout  ← firmware not responding
qmi_wlanfw: wlanfw_send_hang_ind  ← firmware reported hang
cnss: timeout waiting for qmi     ← QMI init timeout
WLFW_IND_FW_READY                 ← firmware ready indication
WLFW_IND_FW_DOWN                  ← firmware down indication
```

### Power and sleep
```
cnss: suspend/resume              ← system sleep transitions
cnss: pci_suspend/resume          ← PCIe PM transitions
cnss: runtime_suspend/resume      ← runtime PM events
cnss: wlan_enable/disable         ← radio on/off
```

### ath10k / ath11k specific
```
ath10k: chip is down              ← hardware not responding
ath10k: failed to wakeup device   ← device in deep sleep, unresponsive
ath11k: failed to fetch board data ← BDF (board data file) missing
ath11k: failed to load firmware   ← firmware file not found
ath12k: reo dest ring stuck       ← receive ring stall (throughput drop)
```

---

## Step 3 — Failure Pattern Analysis

Work through these patterns in likelihood order:

### 3.1 Firmware Assert / Crash

The most serious failure — firmware panicked internally.

**Signature**:
```
cnss: CNSS_WLAN_FW_ASSERT
cnss: fw_down
cnss: schedule recovery
```

**What to extract**:
- Assert reason code / description (appears in cnss_diag log or crash dump header)
- Assert PC (program counter) — points to firmware code location
- Call stack / backtrace if present in dump
- Timestamp of assert relative to WiFi activity in logcat

**Common assert reasons**:
| Reason | Likely cause |
|---|---|
| `PEER_DELETE_TIMEOUT` | Driver/firmware peer management mismatch |
| `TX_TIMEOUT` | Transmit queue stall — often congestion or power issue |
| `WMI_CMD_TIMEOUT` | WMI command from host timed out |
| `WATCHDOG_TIMEOUT` | Firmware watchdog fired — CPU stall |
| `THERMAL_SHUTDOWN` | Over-temperature protection |
| `ASSERT_FAILURE` | Explicit firmware assert |

**Recovery check**: After assert, look for `cnss: recovery_done` and `fw_ready` — successful recovery means WiFi re-enabled automatically. Absence of these means WiFi stayed down.

---

### 3.2 Firmware Boot / Init Failure

WiFi cannot initialize at all.

**Signature**:
```
cnss: fw_boot_timeout
cnss: failed to load fw image
qmi_wlanfw: timeout waiting for QMI connection
```

**Check**:
- Is the firmware binary present? (`/vendor/firmware/wlan/` or `/lib/firmware/ath10k/`)
- Is BDF (board data file) loaded? (`ath11k: failed to fetch board data` → missing `/vendor/etc/wifi/bdwlan*`)
- PCIe link up? (`cnss: pci_link_down` before boot attempt → hardware issue)
- Cold boot calibration succeeded? (`cnss: cold_boot_cal failed` → RF calibration error)

---

### 3.3 PCIe / Bus Errors

The WiFi chip became unreachable over PCIe.

**Signature**:
```
cnss: pci_link_down
cnss: MHI link down
ath10k: failed to wakeup device: timed out
```

**Causes**: Thermal stress, power glitch, PCIe root complex issue, bad solder joint. Usually requires hardware inspection.

---

### 3.4 WMI / QMI Command Failures

Commands from the driver to firmware are timing out — firmware is alive but unresponsive.

**Signature**:
```
ath10k: wmi command X (0xYYYY) timeout
ath11k: failed to complete wmi command
qmi_wlanfw: QMI send req timeout
```

**Check timing**: If WMI timeouts appear just before a scan or connect attempt, this explains why the HAL reports no scan results or connection failure. Cross-reference with logcat timestamp.

---

### 3.5 Runtime Power Management Issues

The chip enters deep sleep and fails to wake up in time.

**Signature**:
```
cnss: runtime_suspend
cnss: wakeup source active: wlan_ws
ath10k: failed to wakeup device (count: N)
```

**Impact**: Packet loss during suspend, delayed TX/RX causing DHCP timeouts or EAPOL M3→M4 loss.

---

### 3.6 Thermal Shutdown

**Signature**:
```
cnss: THERMAL_SHUTDOWN
cnss: fw_down reason=thermal
thermal: zone wlan_fw: temp=XXX threshold=YYY
```

**Impact**: WiFi disabled by firmware thermal protection. Usually recovers after cooling.

---

## Step 4 — Cross-Layer Correlation

Correlate driver events with logcat timeline:

1. Find the cnss/ath assert timestamp
2. In logcat, find `SelfRecovery: trigger REASON_WIFINATIVE_FAILURE` — this is the Framework-layer echo of the driver crash
3. Check: does logcat show `WifiActiveModeWarden: Primary ClientModeManager changed to null` → WiFi was fully taken down?
4. Check recovery: `WifiServiceImpl: setWifiEnabled(true)` after recovery = automatic; absent = manual user action needed

**Timeline correlation format**:
```
Driver (cnss):   HH:MM:SS.mmm  CNSS_WLAN_FW_ASSERT — reason: TX_TIMEOUT
Kernel (dmesg):  HH:MM:SS.mmm  cnss: fw_down, scheduling recovery
Framework:       HH:MM:SS.mmm  SelfRecovery: trigger REASON_WIFINATIVE_FAILURE
Framework:       HH:MM:SS+30s  WifiServiceImpl: setWifiEnabled(true)  ← auto-recovery
```

---

## Step 5 — Output

### Terminal summary

```
=== Qualcomm WiFi Driver Log Analysis ===
Platform  : Qualcomm <chipset if identifiable>
Log type  : cnss_diag | dmesg (cnss/wlan) | ath10k/11k | crash dump
Time range: MM-DD HH:MM – HH:MM

Firmware asserts   : N
Boot failures      : N
PCIe link downs    : N
WMI timeouts       : N
Recovery attempts  : N (N successful)

Root cause (driver layer): <one sentence>

Assert detail (if present):
  PC: 0xXXXXXXXX
  Reason: <reason string>
  Backtrace: <first 3 frames if available>
```

### Markdown report (`wifi_qualcomm_driver_report.md`)

```markdown
# WiFi Qualcomm Driver Log Analysis
**Platform**: Qualcomm <chipset>
**Log type**: <types analyzed>
**Analysis date**: <date>

## Summary
## Firmware Lifecycle Events
## Assert / Crash Analysis
## Boot / Init Failures
## PCIe / Bus Events
## WMI / QMI Command Analysis
## Power Management Events
## Cross-Layer Correlation
## Root Cause & Driver-Layer Verdict
## Recommended Next Steps
```

---

## Step 6 — Next-Step Recommendations

Based on findings, recommend:

| Finding | Recommendation |
|---|---|
| Firmware assert | Collect firmware crash dump (`adb pull /sys/kernel/debug/cnss2/dump/`); file Qualcomm QCA bug with assert reason + PC |
| BDF missing | Check `/vendor/etc/wifi/` for `bdwlan*.bin`; verify build includes correct board data |
| PCIe link down | Hardware inspection; check thermal paste, power supply stability |
| WMI timeout | Enable WMI trace: `echo 1 > /sys/kernel/debug/ath11k/*/wmi_trace`; check firmware version |
| Thermal shutdown | Check thermal zone limits in device tree; verify thermal grease; check ambient temperature |

### Diagnostic Commands

```bash
# Collect cnss_diag (daemon mode)
adb shell cnss_diag -f -l /sdcard/cnss_diag.log &

# Collect cnss crash dump
adb pull /sys/kernel/debug/cnss2/dump/ cnss_dump/

# Check firmware version
adb shell cat /sys/bus/platform/drivers/cnss2/*/wlan_firmware_version
adb shell cat /sys/kernel/debug/ath11k/*/wmi_ctrl_path_stats

# Enable ath11k debug tracing
adb shell echo 0x1 > /sys/kernel/debug/ath11k/*/debug_level

# Live dmesg filter
adb shell dmesg -w | grep -E "cnss|wlan|ath10k|ath11k|ath12k|QMI"

# Check PCIe link state
adb shell cat /sys/kernel/debug/cnss2/bus_bw_info
```
