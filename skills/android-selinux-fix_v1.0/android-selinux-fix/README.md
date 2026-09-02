# android-selinux-fix

**一句话**：给你高通/展锐/MTK/RK Android 设备的 AVC denial 日志或新模块信息，自动完成从分析→修改 .te→整编→刷机→logcat 验证的完整闭环，并导出 patch。

---

## 有 vs 没有这个 Skill

|  | 没有 Skill（裸模型） | 有 Skill |
|--|---------------------|---------|
| AVC 日志分析 | 只能分析你粘贴的那一条，容易漏掉其他 denial | 从日志提取**全部** `avc: denied`，去重后逐条打 ✅ |
| 高通双路径 | 只改 `target/system/sepolicy/`，漏掉 `qssi14/`，刷机后策略不生效 | 强制同步修改 qssi14 + target 两侧 + prebuilts/api |
| MTK 双路径 | 把 MTK 当单仓处理，或在 `MSSI/system/sepolicy` 里直接引用 modem type，容易编译 unknown type | 自动区分 `MSSI` + `VENDOR`，modem/RIL/BIP 类问题优先回到 VENDOR modem sepolicy |
| RK 路径判断 | 把 RK 当高通双路径处理，或漏看 Rockchip common / SoC vendor 策略 | 优先关注 `device/rockchip/common/sepolicy/`、`device/rockchip/rk*/sepolicy_vendor/`、`system/sepolicy/` |
| neverallow 处理 | 报错后手足无措，不知注释哪里、同步哪些 prebuilts | 自动注释 neverallow + 同步全部 prebuilts/api 版本 |
| property.te 宏 | 不知道 `system_internal_prop()` 是宏，无法添加域例外 | 展开宏为 `define_prop + neverallow`，再添加例外 |
| 编译方式 | 可能单编一侧就刷机，验证无效 | 按平台选择编译链路：高通双路径 `--all`，MTK 按 MSSI/VENDOR/super 顺序处理，RK 先 `make selinux_policy` 再整编 super |
| 刷机 | 可能漏刷 super 分区，策略根本没更新 | 必刷 boot + dtbo + vbmeta + vbmeta_system + **super** |
| 耗时 | 约 60–120 分钟（反复试错） | 约 30–50 分钟（含整编） |
| 收尾 | 修完就完了 | 验证通过后自动导出 patch 到 `selinux_patch/` |

---

## 限制与边界

| 类型 | 说明 |
|------|------|
| ✅ 能处理 | 高通 QSSI 架构（Android 12–16，bengal/sm6115/sm6225/qcm2290 等） |
| ✅ 能处理 | 展锐（Unisoc/Sprd）平台 SELinux 修复 |
| ✅ 能处理 | MTK/MediaTek Android 12+ 双路径架构（MSSI + VENDOR），含 modem/RIL/BIP 类 sepolicy 修复 |
| ✅ 能处理 | RK/Rockchip 平台 SELinux 修复，含 `device/rockchip/common/sepolicy/`、`device/rockchip/rk*/sepolicy_vendor/`、`system/sepolicy` |
| ✅ 能处理 | neverallow 违规（注释 + prebuilts/api 全版本同步） |
| ✅ 能处理 | vendor 私有类型不可跨分区引用的架构问题 |
| ✅ 能处理 | MLS 规则冲突（platform_app / tee_device 跨级别访问） |
| ✅ 能处理 | 新模块/APK 集成 SELinux 策略（骨架生成 + permissive 收集） |
| ❌ 不能处理 | 设备 kernel 不支持的 policy 版本升级 |
| ❌ 不能处理 | 非 SELinux 原因导致的功能异常（DAC 权限、缺少 HAL 等） |
| ⚠️ 已知问题 | vendor 类型不可在 system_ext private 策略中引用，需写到 sepolicy_vndr 侧 |
| ⚠️ 已知问题 | MTK modem type 不可直接写进 MSSI platform 策略，需放回 VENDOR modem 策略或调整类型归属 |
| ⚠️ 已知问题 | `property.te` 中 `system_internal_prop(X)` 是宏，需手动展开后才能加域例外 |

---

## 使用方法

### 前置条件

- [ ] 设备 USB 已连接，`adb devices` 可见（或已有 AVC 日志文件）
- [ ] 已知使用哪个 `build_*.sh` 编译脚本
- [ ] 高通项目：源码目录下有 `qssi*/` 和 `target/` 两个子目录（QSSI 架构）
- [ ] MTK 项目：源码目录下有 `MSSI/` 和 `VENDOR/` 两个子目录（Android 12+ 常见架构）
- [ ] RK 项目：源码目录下有 `device/rockchip/` 或客户工程对应的 `devices/rockchip/` 策略目录

### 触发方式

在 Copilot Chat 中提及以下任意关键词即可自动触发：

```
avc: denied / selinux权限拒绝 / neverallow / AVC 报错 / selinux
高通 sepolicy / 展锐 sepolicy / MTK sepolicy / RK sepolicy / Rockchip selinux / rk3568 selinux / bip selinux / modem selinux / qlog selinux / audioserver selinux / 新模块集成 / 新增服务集成
```

或直接 `@workspace /android-selinux-fix` 调用并附上日志文件路径或新模块信息。

---

## 两种工作模式详解

### 模式 A：修复 AVC Denial

**适用场景**：设备开机后 logcat 中出现 `avc: denied`，功能异常需要放行 SELinux 权限。

**完整使用流程**（模拟对话）：

```
┌─────────────────────────────────────────────────────────┐
│ 第 1 步：启动                                            │
├─────────────────────────────────────────────────────────┤
│ 你：帮我修 selinux，日志在 avc.txt                        │
│  或者选择“修复 AVC Denial”，AI 会引导你提供日志             │
│                                                         │
│ AI：[弹出问卷]                                           │
│   1. 工作目标？ → 修复 AVC Denial                        │
│   2. 芯片平台？ → 高通 / 展锐 / MTK / RK                 │
│   3. 编译脚本？ → 从 build_*.sh 列表中选择               │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 2 步：日志分析（全自动）                                │
├─────────────────────────────────────────────────────────┤
│ AI：已读取 avc.txt，提取并去重后发现 4 条 denial：         │
│                                                         │
│  [ ] #1 tee → root_block_device:blk_file { read }      │
│  [ ] #2 init → sysfs:file { open write }               │
│  [ ] #3 hal_secure_element → prop:file { read }        │
│  [ ] #4 system_server → sysfs:file { read }            │
│                                                         │
│  开始逐条定位源文件并修改……                               │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 3 步：修改源码（全自动）                                │
├─────────────────────────────────────────────────────────┤
│ AI：                                                     │
│  • #1 vendor 域 → 仅修改 target/sepolicy_vndr/tee.te   │
│  • #2 触发 neverallow → 注释 public/init.te 对应行      │
│    + 同步 qssi + target 双路径 + prebuilts/api 全版本   │
│  • #3 property.te 宏展开 + 添加域例外                    │
│  • #4 追加 allow + 注释 coredomain neverallow           │
│                                                         │
│  共修改 38 个文件，准备编译。                              │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 4 步：编译（全自动，等待完成）                           │
├─────────────────────────────────────────────────────────┤
│ AI：检测到双路径修改，使用 --all 整编……                    │
│  [运行 build_qcm2290_sc200e.sh --all]                   │
│  编译成功 ✓                                              │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 5 步：刷机验证（需设备在 fastboot 模式）                 │
├─────────────────────────────────────────────────────────┤
│ AI：请将设备进入 fastboot 模式（adb reboot bootloader）   │
│                                                         │
│ [自动刷入 boot + dtbo + vbmeta + vbmeta_system + super] │
│ [设备重启后自动执行]：                                    │
│   adb shell getenforce          → Enforcing             │
│   adb logcat -b all -d | grep "avc: denied"  → 0 条    │
│                                                         │
│ ✅ 验证通过！目标 denial 已全部消除。                      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 6 步：导出 patch                                      │
├─────────────────────────────────────────────────────────┤
│ AI：已导出到 selinux_patch/ 目录：                        │
│   • selinux_fix_qssi_20260529.diff   (21 个文件)        │
│   • selinux_fix_target_20260529.diff  (24 个文件)        │
│                                                         │
│ 任务完成。                                               │
└─────────────────────────────────────────────────────────┘
```

**你只需要做 3 件事**：
1. 提供日志（粘贴/路径/设备自动抓取）
2. 回答初始问卷（平台 + 编译脚本）
3. 让设备进入 fastboot 模式

其余全部自动完成。

---

### 模式 B：新模块集成 SELinux 策略

**适用场景**：新增一个 vendor daemon、vendor APK 或 system APK，需要为它创建完整的 SELinux 策略。

**完整使用流程**（模拟对话）：

```
┌─────────────────────────────────────────────────────────┐
│ 第 1 步：启动                                            │
├─────────────────────────────────────────────────────────┤
│ 你：我要集成一个新模块 qlog 的 selinux 策略               │
| 或者无需描述内容，选择新模块集成 SELinux 策略后会引导你提供内容|
│                                                         │
│ AI：[弹出问卷]                                           │
│   1. 工作目标？ → 新模块集成                              │
│   2. 芯片平台？ → 高通 / 展锐 / MTK / RK                 │
│   3. 编译脚本？ → build_qcm2290_sc200e.sh               │
│                                                         │
│ AI：[追加询问]                                           │
│   4. 模块类型？ → vendor native daemon                   │
│   5. 模块源码路径？ → vendor/qcom/proprietary/qlog       │
│   6. APK 包名？ → (不适用)                               │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 2 步：检查现有目录 + 生成策略骨架                       │
├─────────────────────────────────────────────────────────┤
│ AI：检查 vendor/qcom/proprietary/qlog/ 目录……            │
│  → 无 sepolicy/ 子目录，生成标准骨架：                     │
│                                                         │
│  qlog/sepolicy/                                         │
│  ├── common/                                            │
│  │   ├── file_contexts     ← 可执行文件标签              │
│  │   ├── property_contexts ← 自定义属性标签              │
│  │   └── service_contexts  ← binder service 标签        │
│  └── platform-T/                                        │
│      └── qlog.te           ← type 定义 + 基础 allow     │
│                                                         │
│  已生成最小权限策略，先编译验证……                          │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 3 步：首次编译 + 刷机 + Permissive 收集                │
├─────────────────────────────────────────────────────────┤
│ AI：编译成功，刷机后设置 permissive 模式收集 denial……     │
│                                                         │
│  adb shell setenforce 0                                 │
│  [触发模块功能]                                          │
│  adb logcat -b all -d | grep "avc.*qlog"               │
│                                                         │
│  收集到 8 条新 denial：                                   │
│  [ ] #1 qlog → vendor_data_file:dir { search read }    │
│  [ ] #2 qlog → diag_device:chr_file { read write }     │
│  [ ] #3 qlog → vendor_perf_service:service_manager find│
│  …                                                      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 4 步：补全 allow 规则（全自动）                         │
├─────────────────────────────────────────────────────────┤
│ AI：逐条分析并追加到 qlog.te：                            │
│  • allow qlog vendor_data_file:dir r_dir_perms;        │
│  • allow qlog diag_device:chr_file rw_file_perms;      │
│  • allow qlog vendor_perf_service:service_manager find;│
│  …                                                      │
│  规则优先放在模块自己的 sepolicy/ 目录。                   │
│  仅 #3 涉及跨分区，需额外修改 target/sepolicy_vndr。      │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 5 步：再次编译 + Enforcing 验证                        │
├─────────────────────────────────────────────────────────┤
│ AI：编译成功，刷机后 Enforcing 模式验证：                  │
│   adb shell getenforce → Enforcing                      │
│   adb logcat | grep "avc.*qlog" → 0 条                  │
│                                                         │
│ ✅ 验证通过！                                            │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│ 第 6 步：导出 patch                                      │
├─────────────────────────────────────────────────────────┤
│ AI：已导出到 selinux_patch/ 目录：                        │
│   • selinux_module_qlog_20260529.diff                   │
│                                                         │
│ 任务完成。                                               │
└─────────────────────────────────────────────────────────┘
```

**你只需要做 4 件事**：
1. 告诉 AI 模块名称和路径
2. 回答初始问卷（平台 + 编译脚本 + 模块类型）
3. 让设备进入 fastboot 模式
4. 触发模块功能（让 AI 能抓到 permissive denial）

其余全部自动完成。

---

### 两种模式速查对比

| | 模式 A：修复 AVC Denial | 模式 B：新模块集成 |
|--|--|--|
| **输入** | AVC 日志（文件/粘贴/设备抓取） | 模块路径 + 类型 + 包名 |
| **核心动作** | 解析日志 → 修改已有 .te | 生成骨架 → permissive 收集 → 补全 |
| **编译策略** | 高通双路径修改时 `--all` 整编；MTK 按 MSSI/VENDOR/super 顺序编译；RK 先 `make selinux_policy` 快速验编，再整编 super | 首次可单编，触发 neverallow 或跨分区修改则整编；RK 最终仍需整编 super 后刷机验证 |
| **验证方式** | Enforcing + 目标 denial = 0 | Enforcing + 模块相关 denial = 0 |
| **产物** | `selinux_fix_*.diff` | `selinux_module_<name>_*.diff` |
| **典型迭代次数** | 1–3 轮 | 2–4 轮（骨架→收集→补全→验证） |

---

## 真实案例

### 案例 1：修复 AVC — SM6225 Android 14，6 条 denial 一次修完

**环境**：SM6225 bengal_515，Android 14（qssi14 API34 + target API33），Enforcing 模式  
**验证日期**：2026-05-28  
**结果**：`getenforce` = Enforcing，`avc: denied` 计数 = **0**

**输入**（selinux_debug.txt 中 6 条 denial）：
```
tee → root_block_device:blk_file read
vendor_qti_init_shell → configfs:dir write
init → sysfs:file write
hal_secure_element_default → init_service_status_private_prop:file read
init → debugfs_mmc:file setattr
system_server → sysfs:file read
```

**输出（21 + 24 = 45 个文件修改）**：

| 文件 | 修改内容 | 路径 |
|------|----------|------|
| `tee.te` | 追加 `allow tee root_block_device:blk_file read;` | target/sepolicy_vndr 仅 |
| `init_shell.te` | `configfs:dir r_dir_perms` → `rw_dir_perms` | target/sepolicy_vndr 仅 |
| `public/init.te` | 注释 `neverallow init sysfs:file { open write };` | 双路径 + prebuilts 全版本 |
| `private/init.te` | 追加 `allow init sysfs:file { open write }` + `allow init debugfs_mmc:file setattr` | 双路径 + prebuilts/34.0, 33.0 |
| `private/domain.te` | `-init` 从 `userdebug_or_eng()` 内移到外层 neverallow | 双路径 + prebuilts/31-34.0 |
| `private/coredomain.te` | neverallow sysfs 追加 `-system_server` | 双路径 + prebuilts/29-34.0 |
| `private/system_server.te` | 追加 `allow system_server sysfs:file { read open getattr }` | 双路径 + prebuilts/34.0, 33.0 |
| `private/property.te` | 展开 `system_internal_prop` 宏 + `-hal_secure_element_server` 例外 | 双路径 + prebuilts/31-34.0 |

**关键经验**：
- `property.te` 中 `system_internal_prop(X)` 是宏，展开为 `define_prop + neverallow`，才能添加域例外
- `domain.te` 中 `-init` 必须移到 `userdebug_or_eng()` 外层才能在 user/eng 编译都通过
- 编译经历 3 轮迭代：第 1 轮 coredomain neverallow 失败、第 2 轮 property neverallow 失败、第 3 轮 PASS
- 导出 `selinux_fix_target_20260528.diff`（298 行）+ `selinux_fix_qssi14_20260528.diff`（383 行）

### 案例 2：修复 AVC — vendor app 访问 vendor service（跨分区可见性）

**输入**：
```
avc: denied { find } for scontext=u:r:qlog_app:s0
  tcontext=u:object_r:vendor_perf_service:s0 tclass=service_manager
```

**输出**：
- 发现 `vendor_perf_service` 在 `private/service.te`（vendor 不可见）
- 将 type 定义移至 `public/service.te`（需 diff freeze_test + 7个 compat ignore.cil）
- 在 `qlog.te` 加 `allow qlog_app vendor_perf_service:service_manager find;`
- 只修改 target 侧 → `--vendor` 单编（无需整编）→ 刷机验证

### 案例 3：修复 AVC — MLS 级别冲突（platform_app 访问 tee_device）

**输入**：
```
avc: denied { read write } for scontext=u:r:platform_app:s0:c512,c768
  tcontext=u:object_r:tee_device:s0 tclass=chr_file
```

**输出**：
- 参考 `doc/0001-Qsee-support-platform_app-use.patch`
- 注释 `public/app.te` 中 `neverallow appdomain tee_device` + 同步 prebuilts/api/28-33.0
- 修改 `private/coredomain.te` 注释 `full_treble_only tee_device neverallow`
- 修改 `private/mls` 添加 `or t1 == platform_app` 豁免 + 同步 api/28-33.0
- 双路径修改 → `--all` 整编 → fastboot 完整刷机

### 案例 4：新模块集成 — vendor daemon（qlog 示例）

**输入**：
```
模块类型：vendor native daemon
模块路径：vendor/qcom/proprietary/qlog
```

**输出**：
- 生成 `qlog/sepolicy/` 骨架（file_contexts + qlog.te + service_contexts）
- 首轮编译刷机后 permissive 收集 12 条 denial
- 补全 allow 规则到 `qlog.te`（涉及 diag_device、vendor_data_file、init_service 等）
- 其中 2 条触发 neverallow → 修改平台策略 + 双路径同步
- 二轮编译 Enforcing 验证通过
- 导出 `selinux_module_qlog_20260529.diff`

### 案例 5：修复 AVC — MT8766 Android 13，BIP/modem socket 权限

**环境**：MT8766 Android 13（MSSI + VENDOR 双路径），modem sepolicy 位于 VENDOR 侧  
**验证日期**：2026-06-03  
**结果**：通过 VENDOR modem 策略修复，避免在 MSSI platform 策略中引用 modem domain

**输入**（BIP 启动阶段常见 denial）：
```
init → socket_device:sock_file create
init → bip_socket:unix_stream_socket create/bind
init → bip_socket:unix_dgram_socket create
bip → net_dns_prop:file read
bip → vendor_mtk_ril_mux_report_case_prop:property_service set
```

**输出**：
- 定位 `bip.te`、`file.te`、`file_contexts`、`init.bip.rc` 到 `VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/`
- 为 `/dev/socket/bip_socket` 补专用 `bip_socket` type 和 file_contexts，避免继续落到 `socket_device`
- 在 `init.bip.rc` 的 `socket bip_socket` 行显式标注 `u:object_r:bip_socket:s0`
- 在 `bip.te` 中补 `init` 对 `bip_socket` 的最小 socket 权限
- 对无害 `bip → net_dns_prop:file read` 探测使用 `dontaudit`，不硬穿 platform property neverallow
- 对 MTK/RIL vendor 属性使用 `set_prop()` 宏
- 编译使用 `bash build_MT8766_32go.sh --vendor && bash build_MT8766_32go.sh --super`，刷入 boot/dtbo/vbmeta/vbmeta_system/super 后用 ADB 保留启动日志验证

**关键经验**：
- MTK Android 12+ 不能把所有策略都当成一个目录处理，`MSSI` 和 `VENDOR` 可见性不同
- `bip` 这类 modem domain 不要写进 `MSSI/system/sepolicy/private/domain.te` 的 neverallow 例外，否则容易 `unknown type bip`
- 用 `adb shell ls -Z /dev/socket/...` 检查标签可能制造 `shell` 自身 denial，不应直接作为业务修复目标

---

## FAQ

**Q：日志来源有几种方式？**
- 方式 1：直接在聊天中粘贴 `avc: denied` 文本
- 方式 2：提供日志文件路径（如 `avc.txt`）
- 方式 3：设备在线时自动执行 `adb logcat -b all -d | grep "avc: denied"` 抓取

**Q：编译失败（neverallow 报错）怎么办？**  
AI 会自动识别 neverallow 错误，定位到 `.te` 文件并注释对应行，同时同步 prebuilts/api 全版本。无需你手动干预。

**Q：验证后还有新 denial 怎么办？**  
AI 会自动回到分析环节，提取新 denial 并继续修复，直到目标 denial 全部消除。

**Q：什么时候用 `--all` 整编？什么时候可以单编？**  
- 只改 target/sepolicy_vndr → `--vendor` 单编即可
- 同时改了 qssi + target 的 system/sepolicy → 必须 `--all` 整编
- MTK 只改 VENDOR modem sepolicy → 先 `--vendor`，再 `--super`
- MTK 改了 MSSI/system 或 MSSI/device sepolicy → 先处理 MSSI/system，再处理 VENDOR，最后 `--super`

**Q：MTK 为什么不能直接在 MSSI 里给 modem domain 放行？**  
MSSI 是 platform/system 编译上下文，VENDOR modem sepolicy 里的 `bip`、RIL、IMS 等 type 对它不一定可见。遇到 modem domain denial，优先回到 `VENDOR/vendor/mediatek/proprietary/modem/<modem>/sepolicy/s0/` 修改对应 `.te`、contexts 或 init rc。

---

## Changelog

| 版本 | 日期 | 变化 |
|------|------|------|
| v1.0 | 2026-06-03 | 初版：高通、展锐、MTK、RK 四个平台均测试验证能正常使用；支持 AVC Denial 修复与新模块集成两种模式，覆盖日志提取去重、策略定位修改、平台化编译刷机验证和 `selinux_patch/` 导出流程 |

