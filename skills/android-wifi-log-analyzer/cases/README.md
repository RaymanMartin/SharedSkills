# Cases Directory

This directory stores past analyzed WiFi cases for the `android-wifi-log-analyzer` skill.

## `issue_type` values

| Value | Description |
|---|---|
| `fw-assert` | Firmware assert / crash (Qualcomm cnss or SPRD WCN) |
| `fw-boot-fail` | Firmware failed to boot or initialize |
| `pcie-link-down` | PCIe bus error (Qualcomm) |
| `sipc-timeout` | SIPC IPC timeout (SPRD) |
| `scan-abort` | Scan layer failure (country code loop, DFS flag, regulatory) |
| `assoc-reject` | Association rejected by AP |
| `eapol-timeout` | 4-way handshake timeout |
| `dhcp-failure` | DHCP provisioning failure |
| `dns-failure` | DNS resolution failure |
| `validation-failure` | Internet validation / captive portal |
| `blocklist` | BSSID/network blocklisted (Android 12+) |
| `disconnect-loop` | Repeated disconnect/reconnect cycle |
| `sap-wont-start` | Soft AP failed to start |
| `sap-no-client` | Hotspot up but clients can't connect |
| `sap-no-internet` | Hotspot up, clients connected, but no internet |
| `regdom-unknown` | Regulatory domain became UNKNOWN causing scan issues |
| `elapsed-time-freeze` | SPRD deep sleep elapsed realtime pause causing delayed reconnect |
| `wpa3-sae-fail` | WPA3-SAE authentication failure |
| `weak_signal_roam_cascade_supplicant_crash` | RTL8852BS weak signal → roam cascade → wpa_supplicant SIGSEGV |
| `driver-tx-stall` | Driver TX queue stall |
| `self-recovery` | WiFi SelfRecovery triggered |
| `hidden_hotspot_sae_not_supported` | wpa_supplicant不支持SAE(WPA3)，隐藏热点扫码连接失败；设备可能为2.4GHz-only |
| `ap_inactivity_no_reconnect` | 企业AP空闲超时踢出设备(reason=4)，省电模式下停止发帧导致；重连延迟3~6分钟 |

## case-wpa3-no-reconnect-private-lan

**issue_type**: `wpa3_pmksa_no_reconnect`  
**平台**: SPRD SC2355  
**现象**: WPA3-SAE 连接约7小时后断开，随后约25分钟无法自动回连  
**根因**: 私有LAN AP无公网DNS → NetworkMonitor验证失败 → TEMPORARILY_DISABLED → WPA3 PMKSA到期触发断开 → 禁用期间不回连  
**触发关键词**: `PMKSA-CACHE-REMOVED`、`Enable disabled network`、`Temporarily disabling network`、`isCaptivePortal: isSuccessful()=false`  
**修复**: AP侧部署HTTP 204端点，或将网络标记为无需captive portal检查

## case-rtl8852bs-weak-signal-disconnect

**issue_type**: `weak_signal_roam_cascade_supplicant_crash`  
**平台**: Realtek RTL8852BS (`RTW:` dmesg前缀)  
**现象**: 弱网环境下WiFi频繁漫游后断开，wpa_supplicant SIGSEGV崩溃，约9.5小时后第二次崩溃  
**根因**: RTL8852BS驱动漫游候选选择Bug（当前AP扫描条目老化时delta比较失效，导致逆向roam到更差AP）→ 漫游级联3小时 → wpa_supplicant FT状态机内存损坏 → SIGSEGV  
**触发关键词**: `RTW: rssi = X/30, roam = 1`、`[age]`、`candidate == NULL`、`received signal 11`、`rtw_drv_scan_by_self`  
**修复**: 驱动修复delta比较基准逻辑（当前AP老化时fallback到已知connected_rssi），wpa_supplicant FT状态机内存管理修复


## case-hidden-hotspot-sae-failure

**issue_type**: `hidden_hotspot_sae_not_supported`  
**平台**: 通用 (Newpos POS终端, 2.4GHz-only, 未知WiFi芯片)  
**现象**: 通过QR二维码扫码添加WPA3-SAE隐藏热点，连接在安全参数配置阶段失败，非隐藏的WPA3 AP也同样失败  
**根因**: wpa_supplicant未编译CONFIG_SAE（或驱动未上报SAE capability）→ `No available security params` → AIDL HAL写入失败 → CMD_START_CONNECT Failed；叠加设备仅支持2.4GHz，无法扫描到5GHz热点  
**触发关键词**: `No available security params`、`Failed to save variables.*SAE`、`CMD_START_CONNECT Failed.*KeyMgmt: SAE`、`Cannot select a candidate security params from scan results`、`WifiDppQrCodeScanner`  
**修复**: 重编译wpa_supplicant添加CONFIG_SAE；短期绕过：手机热点改为WPA2-PSK + 2.4GHz


## case-qualcomm-enterprise-inactivity-disconnect

**issue_type**: `ap_inactivity_no_reconnect`  
**平台**: Qualcomm SM6225 (iData K8Pro, yd盈达)  
**现象**: 企业多AP环境下WiFi频繁断开（83次/41.5小时），每次断连后3~6分钟才重连；信号良好(-67dBm)但被AP踢出  
**根因**: 设备屏幕关闭后进入深度省电模式，停止发送帧，企业AP inactivity timer(默认300s)超时后发送DISASSOC(reason=4)；Framework周期扫描触发重连但有3~6分钟延迟  
**触发关键词**: `CTRL-EVENT-DISCONNECTED.*reason=4`、`DISASSOC_DUE_TO_INACTIVITY`、`Auto connect disabled: do not try to re-connect`、`CMD_START_CONNECT.*DisconnectedState`  
**修复**: 设备侧关闭深度省电/启用keepalive；AP侧延长inactivity timer；WMI TLV解析错误需升级驱动v2.0.9.22Q至配套固件版本
