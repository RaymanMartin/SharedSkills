---
platform: qualcomm
role: sta
issue_type: wcnss-service-crash-no-boot-impact
log_types: logcat, dmesg
root_cause_layer: layer-4
---

# Issue Summary

wcnss_service (PID 556) crashed with SIGSEGV during boot in Boot 1 (logcat_260718095835),
but the system still reached BOOT_COMPLETED, bootanim exited normally, and the main
application (SelfCheckActivity) displayed correctly.

Boot 2 (logcat_260718100008) had no wcnss crash and also booted successfully. WiFi was
available in Boot 2 but NOT in Boot 1 — confirming that wcnss_service crash only affects
the WLAN subsystem, NOT the Android boot chain.

**Core conclusion**: wcnss_service crash has NO causal relationship with the reported
"black screen / can't boot" issue. They co-occurred in the same boot cycle by coincidence.
The wcnss_service crash only causes WiFi to be unavailable. The black screen issue must
be investigated separately (display power, LCD driver, suspend/resume path).

Abnormal log features (Boot 1):
- No wpa_supplicant logs (WiFi HAL failed to init due to wcnss crash)
- No wlan driver logs at logcat layer (finit_module "No such device")
- BUT: BOOT_COMPLETED broadcast sent, app running, display OK

# Key Log Signatures

```
01-01 08:00:25.478 F libc    : Fatal signal 11 (SIGSEGV), code 1, fault addr 0x4b3de4235cae7a in tid 556 (wcnss_service)
01-01 08:00:25.540 F DEBUG   : #04 pc ... libqmi_cci.so (qmi_client_init+396)
01-01 08:00:25.540 F DEBUG   : #05 pc ... libqmi_cci.so (qmi_client_init_instance+276)
```

dmesg:
```
[13.220] wcnss_service[556]: unhandled input address range fault (11) at 0x4b3de4235cae7a
[13.297] init: Service 'wcnss-service' (pid 556) killed by signal 11
[20.561] init: Service 'bootanim' (pid 844) exited with status 0  ← system booted fine!
```

# Root Cause

wcnss_service crash: corrupted pointer passed to memset() via jemalloc calloc path inside
qmi_client_init(). The crash is self-contained within the WCNSS QMI communication layer and does
not propagate to the Android system boot chain.

The "black screen" issue reported by the customer is unrelated - it requires separate investigation
focusing on display power/brightness, LCD driver, or system suspend path.

# Next Steps

1. Separate wcnss crash from black screen investigation
2. Black screen: check LCD backlight circuit, full bootloader+kernel log from power-on
3. wcnss crash: low priority - review qmi_client_init_instance call in wcnss_service source
