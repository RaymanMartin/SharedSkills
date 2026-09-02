# AVC Denial 修复工作流

本文档承接 `SKILL.md` 的分支 A，负责日志收集、denial 解析、源码修改、编译刷机验证的细节。

## 1. 收集日志

先用 `vscode_askQuestions` 询问日志来源：

| 选项 | 后续动作 |
|------|----------|
| 粘贴 logcat 内容 | 直接解析用户粘贴内容 |
| 提供 `.txt` 文件路径 | 再用 `vscode_askQuestions` 询问路径，然后用 `read_file` 读取 |
| 设备已连接，自动抓取 | 执行 `adb logcat -b all -d 2>/dev/null \| grep "avc: denied" \| head -30` |

如果 ADB 不可用，要求用户连接设备并授权后继续。

## 2. 提取全部 denial

必须处理日志中的全部 `avc: denied`，不要遗漏同一批日志里的其他 domain。

```bash
grep "avc: denied" <log_file> | sed 's/audit([^)]*): //' | sort -u
```

按以下四元组去重：

```text
scontext + tcontext + tclass + perms
```

生成清单并维护状态：

```text
[ ] denial #1: scontext=... tcontext=... tclass=... { perms }
[ ] denial #2: scontext=... tcontext=... tclass=... { perms }
```

所有条目都标记完成后才能进入编译。

## 3. 解析字段

从每条 denial 提取：

```text
scontext=u:r:<source_domain>:s0
tcontext=u:object_r:<target_type>:s0
tclass=<class>
{ <perms> }
```

判断要点：

| 条件 | 常见修改方向 |
|------|--------------|
| `source_domain` 有 `vendor_` 前缀 | vendor 策略目录 |
| platform 系统域，如 init、system_server | platform/system sepolicy；Android 12 后高通/MTK 需先判断双路径同步或构建范围 |
| system_ext 进程，如 audioserver、lmkd | device/qcom 或 sprd system private 策略 |
| `tclass=binder` 且 `call` 被拒 | 添加 binder call allow 或相应宏 |
| target 是 service 且 vendor app 无法引用 | 将 service type 移到 public，并补 service_contexts/compat |
| coredomain 操作 vendor sock_file | 定义带 `coredomain_socket` 属性的新类型 |
| 日志出现 `s0:c512,c768` | MLS 限制，参考平台模式修复 |

高通具体判断以 `qcom-source-structure.md` 和 `qcom-selinux-patterns.md` 为准；展锐以 `unisoc-source-structure.md` 为准；MTK 以 `mtk-source-structure.md` 和 `mtk-selinux-patterns.md` 为准。

## 4. 定位源码

高通同时搜索 qssi 与 target：

```bash
find qssi14/system/sepolicy/ target/system/sepolicy/ -name "<domain>.te" 2>/dev/null
find qssi14/device/qcom/sepolicy/ target/device/qcom/sepolicy/ target/device/qcom/sepolicy_vndr/ -name "<domain>.te" 2>/dev/null
```

展锐搜索 mpool：

```bash
find device/sprd/mpool -name "<domain>.te" 2>/dev/null
grep -rn "type <target_type>" device/sprd/mpool/ 2>/dev/null
```

MTK 先分 MSSI 与 VENDOR/modem：
```bash
find VENDOR/vendor/mediatek/proprietary/modem -name "<domain>.te" 2>/dev/null
grep -rn "type <target_type>" VENDOR/vendor/mediatek/proprietary/modem VENDOR/device/mediatek MSSI/device/mediatek 2>/dev/null
grep -rn "<socket_or_path_name>" VENDOR/vendor/mediatek/proprietary/modem/*/sepolicy 2>/dev/null
grep -rn "service .*<name>\|socket <name>" VENDOR/vendor/mediatek/proprietary/modem/*/init_rc 2>/dev/null
```

## 5. 常用修复模式

直接 allow：

```te
allow <source_domain> <target_type>:<tclass> { <perms> };
```

属性访问优先用宏：

```te
get_prop(<domain>, <prop_type>)
set_prop(<domain>, <prop_type>)
```

新增 type 时通常需要：

1. 在 public `file.te`、`property.te` 或对应模块策略定义 type。
2. 在 domain `.te` 添加 allow 或宏。
3. 在 `file_contexts`、`property_contexts`、`service_contexts` 等添加标签映射。
4. 高通新增 public 可见 type 时同步 compat `ignore.cil`，必要时同步 prebuilts。

高通特殊模式见 `qcom-selinux-patterns.md`：tee_device neverallow、MLS、debugfs、property private type、compat 映射缺失。

## 6. 编译、刷机、验证

编译和刷机命令必须按平台文档执行：

- 高通：`qcom-build-and-flash.md`
- 展锐：`unisoc-build-and-flash.md`
- MTK：`mtk-build-and-flash.md`

编译前必须：

```bash
adb devices
```

`adb devices` 后必须用 `vscode_askQuestions` 确认后续动作，至少包含以下选项：

| 选项 | 后续动作 |
|------|----------|
| 是，可以继续刷机验证 | 按平台文档整编、刷入完整固件并做 ADB/logcat 验证 |
| 否，先暂停 | 停止在外部阻塞状态，提示用户恢复动作 |
| 只编译不刷机，编译成功后导出 patch | 只运行 SELinux 策略编译；成功后读取 `patch-export.md` 并导出 patch；最终说明未做功能生效验证 |

只编译模式适用于用户明确要求“这次不用刷机，修改后编译成功即可”等场景。该模式的通过标准仅是策略编译成功，不能汇报为目标 denial 已在设备上消除。

验证时不要清空 logcat buffer：

```bash
adb wait-for-device
adb shell getprop sys.boot_completed
adb logcat -b all -d 2>/dev/null | grep "avc: denied"
```

结果判断：

| 结果 | 下一步 |
|------|--------|
| 目标 denial 消失，且无相关新 denial | 读取 `patch-export.md` 导出 patch |
| 只编译不刷机模式下 SELinux 策略编译成功 | 读取 `patch-export.md` 导出 patch，并说明未做刷机/ADB 功能验证 |
| 仍有 denial 或出现新 denial | 回到本文第 2 节，继续完整分析 |
| 设备未连接或未授权 | 告诉用户具体恢复动作，等待确认后继续 |
