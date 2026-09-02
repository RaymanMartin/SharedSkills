# 案例：WPA3-SAE 连接后断开且长时间不自动回连

**来源日志**: `SystemLog_20260513000338.log` / `SystemLog_20260513000416.log` / `SystemLog_20260513072042.log`  
**平台**: Spreadtrum (UNISOC) SC2355 WCN  
**SSID**: `H3R0014000004297` (WPA3-SAE)  
**BSSID**: `d0:cf:13:ec:dd:a9` (5GHz, Channel 36)  
**复现路径**: `/home/quectel/Work/Log/hzr华智融/wpa3-psk-wifi断开后无回连/`

---

## 完整事件时间线

```
07:19:52  [kernel]               PM: suspend entry (deep)
                                 PM: suspend aborted (wakeup: sipc-pmsys-mpm-6) ← CP2 SIPC活动！
                                 → CP2 通过 SIPC 唤醒 APCPU，约10秒后触发断开

07:20:02  [UnisocWatchdog]       UNISOCWATCHDOG_MESSAGE_TIMER30 trigger (系统看门狗正常)

07:20:03  [kernel/wpa_supplicant] ← 断开序列（详见根因1分析）
          [kernel]               sprdwl: PMKSA-CACHE-REMOVED (PMK缓存被清除)
          [kernel]               sprdwl_cfg80211_disconnect H3R0014000004297 reason:1
                                  ← 上层通过 cfg80211 发起主动断开
          [wpa_supplicant]       nl80211: send_mlme - disassoc (nlmode=3)
          [kernel]               sc2355: WIFI_CMD_DISCONNECT sent to firmware
          [kernel]               sc2355: recv[WIFI_EVENT_DISCONNECT] ← 固件应答
          [kernel]               sprdwl_report_disconnection reason_code 0
          [wpa_supplicant]       nl80211: Was expecting local disconnect but got
                                  another disconnect event first
                                  ← 关键竞争：上层还未处理完，CP2/固件已先上报断开事件!
          [wpa_supplicant]       CTRL-EVENT-DISCONNECTED bssid=d0:cf:13:ec:dd:a9
                                  reason=1 locally_generated=1
          [wpa_supplicant]       deauth reason dump: remote reason[0]: 61 times
                                  ← AP侧共计61次 reason=0 的去认证事件（累积）

07:20:03  [wpa_supplicant]       CTRL-EVENT-REGDOM-CHANGE init=CORE type=WORLD
          [WifiNative]           onSetCountryCodeSucceeded: CN (WifiNative认为国家码=CN)
          [wificond]             Regulatory domain changed to country: CN (短暂)
          [wpa_supplicant]       CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN ← 关键!
                                  → wpa_supplicant/wificond 认为监管域变为 UNKNOWN
                                  → 可能限制 5GHz DFS 信道（ch36）从扫描列表移除

07:20:03  [WifiClientModeImpl]   ClientModeImpl: Leaving Connected state
          [WifiClientModeImpl]   disconnectedstate enter
          [AlarmManager]         WifiConnectivityManager Schedule Watchdog Timer
                                  type=2 (ELAPSED_REALTIME_WAKEUP) triggerAtTime=79655210 win=900000
          [ConnectivityService]  [171 WIFI] EVENT_NETWORK_INFO_CHANGED: CONNECTED→DISCONNECTED
          [DhcpClient]           doQuit → DHCP Packet Handler stopped

07:20:09  [wificond]             Received external scan result notification ← 仅此1次常规扫描回调
          [WifiNl80211Manager]   Scan result ready event
          [WifiNative]           Scan result ready event
          → 本次扫描为断开前残留的 in-flight 扫描结果，未触发回连
            （REGDOM UNKNOWN 导致扫描结果中 5GHz ch36 不可见）

╔══════════════════════════════════════════════════════════════════╗
║            25分钟空白期 (07:20:09 → 07:44:59)                   ║
║  Android 层: 0次 sprdwl_cfg80211_scan / 0次 CMD_START_CONNECT   ║
║  Android 层: 0次 WifiNl80211Manager: Scan result ready event    ║
║  内核层: PD_WCN_STATE=0 / PD_WIFI_WRAP_STATE=7 每30s上报        ║
║          WCN深度睡眠中，WiFi MAC 供电但无扫描活动               ║
║  关键: elapsedRealtime 仅增长 ~296s (≈5分钟), 而挂钟走了25分钟  ║
║       → SPRD平台 APCPU 进入深睡, elapsed realtime 计时暂停      ║
║       → ELAPSED_REALTIME_WAKEUP 定时器实际未能在预期时间唤醒    ║
╚══════════════════════════════════════════════════════════════════╝

07:45:00  [AlarmManager]         waitForAlarm result:4 elapsedRealtime=79951535
                                  → 设备被外部事件唤醒（非WiFi Watchdog触发）
          [AlarmManager]         WifiConnectivityManager Schedule Watchdog Timer 触发
                                  (triggerAtTime=79655210 已过期，立即处理)
          [kernel]               sprdwl_cfg80211_scan n_channels 27 ← 全信道扫描!

07:45:01  [kernel]               sprdwl_scan_done: 58 BSSes found
          [kernel]               sprdwl_cfg80211_sched_scan_start: channel is 36
          [kernel]               proberesp d0:cf:13:ec:dd:a9, channel 36, signal -3200
                                  ← 5GHz AP（此时 REGDOM 已恢复）在 ch36 找到
          [WifiNl80211Manager]   Scan result ready event
          [WifiNative]           Pno scan result event ← PNO（固件调度扫描）上报结果!
          [WifiClientModeImpl]   CMD_START_CONNECT nid=9 roam=false (DisconnectedState)
          [SupplicantStaIfaceHal] connectToNetwork "H3R0014000004297" SAE

07:45:02  [wpa_supplicant]       SPRD vendor SAE IE len: 16 (OUI: 40:45:DA)
          [wpa_supplicant]       SPRD SAE auth results-1/2/3 → SPRD SAE completed
          [wpa_supplicant]       CTRL-EVENT-CONNECTED to d0:cf:13:ec:dd:a9
          [ConnectivityService]  [172 WIFI] CONNECTING→CONNECTED
```

---

## 根因分析

### 根因1：断开原因 (07:20:03 CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1)

**现象**：`CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1` 且伴随 `nl80211: Was expecting local disconnect but got another disconnect event first`

**断开序列**：
```
PMKSA-CACHE-REMOVED                                    ← wpa_supplicant 清除了 PMK 缓存
  ↓
sprdwl_cfg80211_disconnect reason:1                    ← 上层（wpa_supplicant）通过 cfg80211 发起主动断开
  ↓
WIFI_CMD_DISCONNECT → firmware → WIFI_EVENT_DISCONNECT ← 固件应答
  ↓
nl80211: Was expecting local disconnect but got another disconnect event first
  ↓                                                    ← 竞争！固件已自行上报断开，上层来晚了
sprdwl_report_disconnection reason_code 0
  ↓
CTRL-EVENT-DISCONNECTED reason=1 locally_generated=1
```

**关键指标**：
- `nl80211: Was expecting local disconnect but got another disconnect event first` → wpa_supplicant 已发出主动断开命令，但 CP2/固件**先行上报**了断开事件——说明固件/CP2层已经探测到断开状态
- `PMKSA-CACHE-REMOVED` → PMK 缓存被清除是上层断开的前兆，可能由 CP2 内部事件触发
- `deauth reason dump: remote reason[0]: 61 times` → 从 AP 侧累计了61次 reason=0 去认证事件
- 07:19:52 `PM: suspend aborted (wakeup: sipc-pmsys-mpm-6)` → 断开前约10秒 CP2 通过 SIPC 唤醒 APCPU，是最早可见的异常先兆

**根本原因（未完全确认）**：日志中无直接 CP2/固件侧触发事件可见。最可能的机制：
1. CP2 内部探测到 AP 链路质量异常（PMF/加密问题？）→ 上报 disconnect event
2. wpa_supplicant 收到固件 disconnect 通知 → 清除 PMKSA → 尝试主动断开
3. 两者之间发生竞争（race condition），形成 `Was expecting local disconnect` 现象

**不是以下原因**：
- ❌ NetworkMonitor 7小时验证失败导致框架强制断开（日志中无此触发路径可见）
- ❌ WPA3-SAE 握手失败（断开发生在连接建立后，SAE 本身正常完成）

### 根因2：不自动回连 (25分钟空白期)

**确认结论**：**与 WifiConnectivityManager 直接相关**

**证据**：
```
07:20:09 ~ 07:44:59 之间（Android 层确认）：
  - sprdwl_cfg80211_scan: 0次
  - WifiNl80211Manager "Scan result ready event": 0次  
  - WifiNative "Scan result ready event": 0次
  - CMD_START_CONNECT: 0次
  - WifiConnectivityManager 相关日志: 0条
  → 整个 WiFi 框架层完全静默
```

**主因：SPRD 平台深睡期间 elapsed realtime 不计时**
```
证据（时间对比）：
  07:20:03  Watchdog Timer triggerAtTime=79655210 (设置时的 elapsed realtime ≈ 79655210)
  07:45:00  AlarmManager: waitForAlarm elapsedRealtime=79951535
  
  elapsed 差值: 79951535 - 79655210 = 296325ms ≈ 5分钟
  挂钟差值: 07:45:00 - 07:20:03 = 1497秒 ≈ 25分钟
  → 设备深睡约 20分钟，SPRD APCPU 的 elapsed realtime 在深睡期间暂停计时

结论：
  WifiConnectivityManager Watchdog Timer (type=2 ELAPSED_REALTIME_WAKEUP)
  在 SPRD 平台深睡期间无法及时触发——当 elapsed realtime 不增长时，
  触发条件（elapsed ≥ triggerAtTime）在设备唤醒前始终不满足。
  直到 07:45 设备被外部事件唤醒后，Watchdog 才立即触发。
```

**次因：REGDOM→UNKNOWN 阻断 5GHz 扫描**
```
07:20:03 CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN
  → wificond 更新频率列表，可能将 ch36（5180 MHz，5GHz DFS 信道）排除
  → 即使偶有扫描，也无法找到目标 AP（WPA3-SAE AP 在 ch36）
  → 07:45 时 REGDOM 状态恢复 → 27信道全扫含 ch36 → 找到 AP

对比：
  WifiNative: onSetCountryCodeSucceeded: CN （框架层认为已设置 CN）
  wpa_supplicant: CTRL-EVENT-REGDOM-CHANGE init=CORE type=UNKNOWN （nl80211层报告UNKNOWN）
  → 两层存在不一致，wificond 跟随 wpa_supplicant nl80211 的 UNKNOWN 状态
```

**回连触发机制（07:45）**：
```
1. 外部事件唤醒设备（非 WiFi Watchdog）
2. Watchdog Timer（已过期）立即处理 → 触发全信道扫描
3. 扫描结果：sprdwl_cfg80211_scan n_channels 27 → 58 BSSes found（含 ch36 AP）
4. PNO（固件调度扫描）同时上报：WifiNative: Pno scan result event
5. WifiConnectivityManager: CMD_START_CONNECT → SAE 握手 → 成功连接
```

### 根因3：回连后仍无法验证互联网

```
07:45:02 resolv: validateDnsTlsServer returned 0 for 8.8.8.8
  → AP 侧 WAN 连接问题 / DNS 8.8.8.8 不可达 → 根本问题在 AP/路由器侧
```

---

## WPA3-SAE (SPRD 平台) 关键特征

```
# 连接触发
SupplicantStaIfaceHal: connectToNetwork "SSID" SAE

# SPRD 定制 SAE 握手 (3步)
wpa_supplicant: SPRD vendor SAE IE len: 16
    hexdump: dd 0e 40 45 da 02 ...  ← SPRD vendor OUI: 40:45:DA
wpa_supplicant: SPRD SAE auth results-1: (54 bytes)
wpa_supplicant: SPRD SAE auth results-2: (32 bytes PMK partial)
wpa_supplicant: SPRD SAE auth results-3: (16 bytes)
wpa_supplicant: SPRD SAE completed - SET PMK for 4-way handshake

# 内核层参数 (sc2355 / sprd-wlan)
wlan0: auth type 0x4          ← SAE
wlan0: akm suites 0xfac08     ← SAE AKM (suite 8)
wlan0: management frame protection 0x1  ← PMF 强制开启
wlan0: wpa versions 0x2       ← WPA2/3
wlan0: pairwise cipher 0xfac04 (CCMP)
wlan0: group cipher 0xfac04 (CCMP)

# Security type=4 (WPA3-SAE) in ConnectivityService log
TransportInfo: Security type: 4, Wi-Fi standard: 4, Frequency: 5180MHz
```

---

## 诊断方法

### 判断断开是否为 CP2/固件-上层竞争导致

```bash
# 关键竞争标志
grep "Was expecting local disconnect but got another disconnect event first" log.txt
  → 出现此行 = CP2/固件与wpa_supplicant断开处理发生竞争

# 查看断开前的 CP2/SIPC 活动（内核日志）
grep "sipc-pmsys-mpm\|suspend aborted" log.txt | grep -B5 "suspend aborted"
  → suspend aborted + sipc-pmsys-mpm-6 = CP2 SIPC 活动唤醒 APCPU

# 查看 PMKSA 缓存清除（是上层断开的前兆）
grep "PMKSA-CACHE-REMOVED\|pmksa" log.txt
  → 出现在 CTRL-EVENT-DISCONNECTED 之前 = 上层触发了断开

# 查看累积的 deauth 事件
grep "deauth reason dump\|remote reason" log.txt
  → remote reason[0]: N times = AP侧 deauth 次数（N很大时值得关注）

# 完整断开序列（sprdwl 内核驱动）
grep "sprdwl_cfg80211_disconnect\|WIFI_CMD_DISCONNECT\|WIFI_EVENT_DISCONNECT\|sprdwl_report_disconnection" log.txt
```

### 判断是否为"SPRD深睡+elapsed realtime暂停"导致不回连

```bash
# 提取 elapsed realtime 数据点，计算斜率
grep "elapsedRealtime\|tElapsed" log.txt | grep -E "Watchdog|waitForAlarm" | head -20
  → elapsed 增长量 远小于 挂钟增长量 → 深睡期间计时暂停

# 确认 Watchdog Timer 类型（SPRD上type=2不等于标准Android ELAPSED_REALTIME_WAKEUP）
grep "WifiConnectivityManager Schedule Watchdog Timer" log.txt
  → type=2, 触发时间间隔与挂钟时间不一致 → 深睡暂停了计时

# 统计断开后到回连前的扫描次数（应为0）
grep "sprdwl_cfg80211_scan\|Scan result ready event" log.txt \
  | awk -F'[ :]' '{print $1, $2}' | grep -A9999 "07:20:" | grep -B9999 "07:45:"
  → 0条 = 确认25分钟内无任何WiFi扫描

# 查看回连触发类型（是PNO还是常规扫描）
grep "Pno scan result event\|CMD_START_CONNECT" log.txt
  → "Pno scan result event" 先于 CMD_START_CONNECT = PNO触发的回连
```

### 判断 REGDOM 状态对5GHz扫描的影响

```bash
# 检查 REGDOM 变化链
grep "CTRL-EVENT-REGDOM-CHANGE\|onSetCountryCodeSucceeded" log.txt
  → type=UNKNOWN 出现后 5GHz 扫描可能被限制
  → WifiNative CN + wpa_supplicant UNKNOWN = 两层不一致（SPRD常见）

# 验证扫描结果是否含5GHz信道
grep "sprdwl_cfg80211_scan n_channels" log.txt
  → n_channels=27 (2.4G+5G全信道) vs n_channels=13以下 (仅2.4G)

# 确认回连时AP所在信道
grep "proberesp.*channel 3[0-9]\|channel 4[0-9]\|channel 5[0-9]\|channel 6[0-9]" log.txt
  → channel 36/40/44/48/149/153/157/161 = 5GHz AP
```

### 判断是否为 WPA3-SAE 特有问题

```bash
# 确认 SAE 连接成功标志
grep "SPRD SAE completed\|SPRD vendor SAE IE" log.txt

# 确认 PMF 已启用
grep "management frame protection" log.txt  # 应为 0x1

# 确认 AKM 为 SAE
grep "akm suites 0xfac08" log.txt
```

---

## 结论与建议

| 问题 | 根因 | 建议 |
|---|---|---|
| WiFi 断开 | CP2/固件先行上报断开 + wpa_supplicant 竞争（具体触发原因日志不可见，疑为CP2内部事件）| 抓取 CP2/固件侧日志（sprd_cp2_log / mdbg dump）确认CP2层触发原因 |
| 不自动回连（25分钟）| SPRD深睡期间 elapsed realtime 暂停 → WCM Watchdog 无法按时触发 + REGDOM UNKNOWN 阻断5GHz扫描 | ① 将 Watchdog Timer 改为 `RTC_WAKEUP`（type=0）或保活 WiFi wakelock；② 断开后立即重新设置正确 REGDOM（国家码） |
| 5GHz AP 扫描不可见 | REGDOM→UNKNOWN 后 wificond 可能排除 DFS 信道（ch36）| 断开事件处理中加入 `WifiManager.setCountryCode()` 重置国家码；检查 SPRD wificond 对 UNKNOWN regdom 的频率列表处理 |
| 回连后仍无互联网 | AP/路由器 WAN 侧 DNS (8.8.8.8) 不可达 | AP 侧检查 WAN 连接；改用本地 DNS 服务器 |

**SPRD平台特殊提示**：
- `ELAPSED_REALTIME_WAKEUP`（type=2）在 SPRD APCPU 深睡模式下计时暂停，不等同于标准 Android 行为
- `deauth reason dump: remote reason[0]` 是 SPRD 独有的累积去认证统计，大量 reason=0 可能指向 AP 侧行为或 PMF 保护帧问题
- `nl80211: Was expecting local disconnect` 是 SPRD WCN 上层/固件竞争的常见特征，非必然异常

**额外建议（针对 pos/IoT 设备）**:
- 在应用层监听 `WifiManager.NETWORK_STATE_CHANGED_ACTION`，当 WiFi 断开时使用 `WifiManager.reconnect()` 主动触发重连
- 考虑使用 `ConnectivityManager.requestNetwork()` 注册高优先级网络请求，让系统持续维护 WiFi 连接

---

## 新增关键词

以下关键词在 SPRD WPA3-SAE 日志中具有重要诊断价值（已加入 SKILL.md）：

- `SPRD vendor SAE IE` — SPRD 定制 SAE 握手开始
- `SPRD SAE completed` — SAE 认证成功标志
- `CTRL-EVENT-REGDOM-CHANGE` — 监管域变化（type=UNKNOWN 为异常）
- `UnisocWatchdog` — UNISOC 系统看门狗（与 WiFi 无关，但可帮助确认系统存活）
- `ELAPSED_REALTIME` (type=2) — 非唤醒定时器（睡眠时不触发）
- `validateDnsTlsServer` — DNS-over-TLS 验证失败（指向 AP 侧问题）
- `management frame protection` — PMF 状态（WPA3 强制为 0x1）
- `akm suites 0xfac08` — SAE AKM 标识
- `PD_WCN_STATE` / `PD_WIFI_WRAP_STATE` — 内核层 WCN/WiFi 电源域状态
