# wifi_code_link 分层说明与按需订正规则

本文件定义 `wifi_code_link` 在输出链路分析时，如何解释层级、如何判断用户给出的路径/归属是否有误，以及何时需要输出“层级错误订正”。

---

## 一、标准层级顺序

默认按以下顺序组织：

1. **Settings / App 触发层**
2. **Connectivity / Tethering 层**
3. **Framework API 层**
4. **Wifi Framework Service 层**
5. **HAL 接口 / Binder IPC 层**
6. **Userspace daemon 层**
   - `wpa_supplicant`
   - `hostapd`
7. **Vendor HAL / Native bridge 层**
8. **Kernel cfg80211 / nl80211 层**
9. **WiFi Driver 层**

注意：

- `wpa_supplicant` / `hostapd` **不是 HAL**
- `Vendor HAL` 与 `Userspace daemon` 也不是同一层
- `Kernel` 与 `Driver` 需要分开描述

---

## 二、默认锚点路径

### 1. Settings / Tethering

- `qssi16/packages/apps/Settings/src/com/android/settings/wifi/tether/`
- `qssi16/packages/apps/Settings/src/com/android/settings/network/tether/`

### 2. Connectivity / NetworkStack

- `qssi16/packages/modules/Connectivity/Tethering/common/TetheringLib/src/android/net/`
- `qssi16/packages/modules/Connectivity/Tethering/src/com/android/networkstack/tethering/`

### 3. Wifi Framework

- `qssi16/packages/modules/Wifi/framework/java/android/net/wifi/`
- `qssi16/packages/modules/Wifi/service/java/com/android/server/wifi/`

### 4. HAL 接口层

- `qssi16/hardware/interfaces/wifi`
- `target/hardware/interfaces/wifi`

### 5. Userspace daemon 层

- `qssi16/external/wpa_supplicant_8`
- `target/external/wpa_supplicant_8`

### 6. Vendor HAL / Native

- `target/hardware/qcom/wlan/qcwcn`
- 其他 vendor 平台目录（按实际源码树）

### 7. Kernel wireless stack

- `target/kernel_platform/msm-kernel`

### 8. WiFi Driver

- `target/vendor/qcom/opensource/wlan`

---

## 三、已知主链锚点

### `sap_open`

1. `WifiTetherPreferenceController.onSwitchToggled()`
2. `TetheringManagerModel.startTethering(TETHERING_WIFI)`
3. `TetheringManager.startTethering(...)`
4. `Tethering.startTethering(...)`
5. `Tethering.enableTetheringInternal(...)`
6. `Tethering.setWifiTethering(...)`
7. `WifiManager.startTetheredHotspot(...)`
8. `WifiServiceImpl.startTetheredHotspotRequest(...)`
9. `WifiServiceImpl.startTetheredHotspotInternal(...)`
10. `WifiServiceImpl.startSoftApInternal(...)`
11. `ActiveModeWarden.startSoftAp(...)`
12. `SoftApManager.startSoftAp()`
13. `WifiNative.startSoftAp(...)`
14. `HostapdHal.addAccessPoint(...)`

### `sta_init`

1. `WifiManager.setWifiEnabled(...)`
2. `WifiServiceImpl.setWifiEnabled(...)`
3. `ActiveModeWarden.wifiToggled(...)`
4. `ClientModeManager.start()`
5. `WifiNative.setupInterfaceForClientMode(...)`
6. `SupplicantStaIfaceHal.startDaemon()`
7. `connectToNetwork()`

### `wifi_toggle`

1. `WifiManager.setWifiEnabled(...)`
2. `WifiServiceImpl.setWifiEnabled(...)`
3. `ActiveModeWarden.wifiToggled(...)`
4. `WifiController`

---

## 四、何时只输出“层级路径说明”

如果满足以下条件，则只输出“层级路径说明”，不要强行写“错误订正”：

1. 用户给的路径基本存在
2. 用户给的层级顺序大体正确
3. 没有把 daemon / HAL / kernel / driver 明显混淆
4. 只是细节不完整，但不构成错误归属

这时应输出：

- 各层路径
- 各层职责
- 本次实际追踪使用了哪些路径

---

## 五、何时必须输出“层级错误订正”

如果出现以下情况，则必须新增 `层级错误订正` 小节：

1. 路径不存在或层级归属错误
2. 把 `wpa_supplicant` / `hostapd` 当成 HAL
3. 把 vendor HAL 当成 kernel driver
4. 把 Framework Java 层与 HAL 接口层混为一谈
5. 把 `cfg80211/nl80211` 与 driver 私有实现混为一层

输出订正时，必须包含：

1. 用户原始层级或路径
2. 错误点
3. 正确归属
4. 修正后的层级结构

---

## 六、边界说明规则

输出时必须解释这些关键边界：

1. **Framework API vs Wifi Service**
   - 公开 API 与系统服务实现的关系
2. **HAL 接口 vs Userspace daemon**
   - AIDL/HIDL 接口定义不等于 daemon 本体
3. **Userspace daemon vs Vendor HAL**
   - 二者都在 userspace，但职责不同
4. **Kernel vs Driver**
   - `cfg80211/nl80211` 是内核无线栈接口
   - 厂商 driver 是更下层实现

---

## 七、检索优先级规则

分析时必须遵循以下顺序：

1. **优先用户给定路径**
   - 如果用户已经给了参考路径，就先只在这些路径内检索
2. **其次默认分层路径**
   - 如果用户没给，才使用本文件中的默认路径
3. **先同层主路径，再同层备用路径**
   - 不要跨层直接扩
4. **最后才允许更大范围搜索**
   - 默认禁止一开始就整仓搜索

如果发生扩展检索，最终文档必须写明：

1. 原始路径
2. 为什么没命中
3. 扩展路径
4. 命中的关键锚点

---

## 八、路径变体规则

1. 如果同时存在 `qssi16/...` 与 `target/...` 同名 Java 文件：
    - 优先用 `qssi16/...` 作为 Framework 主分析路径
2. 如果 userspace daemon 在 `target/external/...` 更完整：
   - 可以直接引用 `target/external/...`
3. 如果 vendor 或 driver 目录存在但本次主链没有直接证据：
    - 仍可列入“关键源码索引”
    - 但必须标注为“候选实现域”或“间接关联层”

---

## 九、分层输出最低要求

每一层至少输出：

1. 入口点
2. 关键函数
3. 下一跳
4. 职责说明
5. 证据路径
