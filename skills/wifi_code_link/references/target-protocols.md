# wifi_code_link 目标链路协议

本文件定义不同 `target_flow` 对应的重点章节要求。

---

## 一、`sap_open`

### 必须回答的问题

1. Settings 是直接启动热点，还是先走 Tethering？
2. `WifiManager.startTetheredHotspot(...)` 在哪一层被调用？
3. `WifiServiceImpl` 到 `SoftApManager` 的主链是什么？
4. `HostapdHal` 与 `hostapd` 的边界在哪里？
5. 最深可证实边界到哪一层？

### 必须出现的图

1. SAP 跨层时序图
2. Settings / Tethering 请求阶段流程图
3. WifiService / StateMachine 仲裁阶段流程图
4. WifiNative / Hostapd AP 启动阶段流程图
5. 如果命中真实状态机，输出真实状态机图

### 状态机候选

1. `ActiveModeWarden.WifiController`
2. `SoftApManager.SoftApStateMachine`

### 必须出现的源码索引重点

- `WifiTetherPreferenceController`
- `TetheringManagerModel`
- `TetheringManager`
- `Tethering`
- `WifiManager`
- `WifiServiceImpl`
- `ActiveModeWarden`
- `SoftApManager`
- `WifiNative`
- `HostapdHal`
- `hostapd.cpp` / hostapd 相关入口

---

## 二、`sta_init`

### 必须回答的问题

1. `setWifiEnabled` 或对应入口如何进入 Wi-Fi 模式管理？
2. `ActiveModeWarden` 如何创建 ClientMode 流程？
3. `SupplicantStaIfaceHal` 与 `wpa_supplicant` 的边界在哪里？
4. 哪一层真正把连接请求送入内核无线栈？
5. 最深可证实边界到哪一层？

### 必须出现的图

1. STA 跨层时序图
2. 入口 / 模式创建阶段流程图
3. Native / supplicant 执行阶段流程图
4. 如果命中真实状态机，输出真实状态机图

### 状态机候选

1. `ActiveModeWarden.WifiController`
2. `ClientModeImpl` 中真实参与本链路的状态机

### 必须出现的源码索引重点

- `WifiManager`
- `WifiServiceImpl`
- `ActiveModeWarden`
- `ClientModeImpl`
- `ClientModeManager`
- `WifiNative`
- `SupplicantStaIfaceHal`
- `wpa_supplicant`
- `driver_nl80211`

---

## 三、`wifi_toggle`

### 必须回答的问题

1. WiFi 开关的入口函数是什么？
2. `ActiveModeWarden` 如何仲裁状态切换？
3. `WifiController` 如何处理关键事件？
4. 开关过程会切换哪些模式管理对象？
5. 失败或特殊模式（如 emergency mode）如何处理？

### 必须出现的图

1. WiFi 开关跨层时序图
2. 开关请求进入阶段流程图
3. `ActiveModeWarden` 仲裁阶段流程图
4. 如果命中真实状态机，输出真实状态机图

### 状态机候选

1. `ActiveModeWarden.WifiController`
2. 本链路真实涉及的模式管理状态机

### 必须出现的源码索引重点

- `WifiManager`
- `WifiServiceImpl`
- `ActiveModeWarden`
- `WifiController`
- `ClientModeManager` / `SoftApManager`（按实际涉及）

---

## 四、协议通用规则

1. 章节顺序统一遵循 `report-template.md`。
2. 只切换具体内容，不切换整体文风。
3. 如果某条链路跨越多个子阶段，应拆成多个流程图而不是塞进一个大图。
4. 状态机图只允许画真实代码 `StateMachine`，且该状态机必须被本次主链实际命中。
5. 如果用户问题明显要求“从 Settings 开始”，就优先从 UI 或上层入口追起，不要直接从 Framework 中层切入。
