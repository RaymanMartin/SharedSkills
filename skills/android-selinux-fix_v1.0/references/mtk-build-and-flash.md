# MTK (MediaTek) 编译与刷机指南

## 核心原则

> ✅ 验证 SELinux 修改必须走源码修改、编译镜像、完整刷入、ADB 验证流程。
> ❌ 禁止用 `adb push` 单独替换 `precompiled_sepolicy`、`.cil` 或策略文件。
> ⚠️ 具体项目脚本优先于通用命令；用户明确说某个命令会失败时，不要再使用该命令。

如果用户明确选择“只编译不刷机”，本轮可以在对应 MSSI/VENDOR 编译目标成功后停止刷机流程，但必须继续读取 `patch-export.md` 并导出 patch；最终结论只能说明“编译通过”，不能说明目标 denial 已在设备上消除。

---

## MT8766 已验证编译流程

项目根目录：

```text
/home/liangjj/work3/MT8766_Android13.0_R01_V15.65
```

该项目已验证：修改 VENDOR 侧 modem sepolicy 后使用：

```bash
bash build_MT8766_32go.sh --vendor
bash build_MT8766_32go.sh --super
```

或连续执行：

```bash
bash build_MT8766_32go.sh --vendor && bash build_MT8766_32go.sh --super
```

只编译不刷机模式下，若本项目策略编译必须依赖 `--super` 才能产出最终 sepolicy，则按脚本要求跑到 `--super` 成功后导出 patch；若项目有可用的单独 sepolicy/system/vendor 编译目标，则以该目标成功为准。

> 已知限制：本项目 `make selinux_policy` 会失败，不要用于验证。只改 VENDOR 侧策略时，走 `--vendor` 后必须再走 `--super`。

---

## 编译目标选择

| 修改范围 | 推荐编译 |
|------|------|
| `VENDOR/vendor/mediatek/proprietary/modem/<modem>/sepolicy/s0/` | `--vendor` → `--super` |
| `VENDOR/vendor/mediatek/proprietary/modem/<modem>/init_rc/s0/` | `--vendor` → `--super` |
| `VENDOR/device/mediatek/` vendor 策略 | `--vendor` → `--super` |
| `MSSI/system/sepolicy/` 或 `MSSI/device/mediatek/sepolicy/` | 按项目脚本编 MSSI/system，再编 vendor/super；不要只编 VENDOR 验证 platform 改动 |
| MSSI 与 VENDOR 两侧都改 | 先编 MSSI/system，再编 VENDOR，最后 `--super` |

---

## 镜像输出位置

MT8766 实战中的 merged 镜像目录：

```text
VENDOR/out/target/product/tb8766p1_bsp_1g/merged
```

刷机前检查 5 个镜像是否存在且时间戳更新：

```bash
cd VENDOR/out/target/product/tb8766p1_bsp_1g/merged
ls -lh boot.img dtbo.img super.img vbmeta.img vbmeta_system.img
```

---

## Fastboot 刷入流程

该 MT8766 项目用户已验证：必须使用 `adb reboot bootloader` 进入刷机模式。进入 fastboot 后刷机不能漏刷 `super.img`。

```bash
cd VENDOR/out/target/product/tb8766p1_bsp_1g/merged

adb reboot bootloader
fastboot devices

fastboot flash boot boot.img
fastboot flash dtbo dtbo.img
fastboot flash super super.img
fastboot flash vbmeta vbmeta.img
fastboot flash vbmeta_system vbmeta_system.img

fastboot reboot
```

如果 fastboot 返回：

```text
FAILED (remote: not allowed in locked state)
unlocked: no
secure: yes
```

说明 bootloader 锁定，当前 fastboot 不允许刷写。此时不要反复重试 fastboot flash；需要使用项目允许的 MTK 刷机工具刷入完整镜像，或由用户处理设备解锁/授权刷机方式。

---

## 使用 MTK 刷机工具时的协作流程

当设备无法 fastboot unlock 或 fastboot 禁止刷写时：

1. 编译完成后确认 merged 目录下镜像已更新。
2. 告知用户使用 MTK 刷机工具刷入新镜像。
3. 等用户确认设备回到 ADB 后继续验证。
4. 不要假设镜像已生效；必须通过 ADB 启动日志验证目标 denial 是否变化。

---

## ADB 验证流程

验证时不要清空 logcat buffer，保留启动阶段 AVC：

```bash
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell getenforce

# 过滤目标 domain/type，不清空 buffer
adb logcat -b all -d 2>/dev/null | grep "avc: denied" | grep -E "<domain>|<target_type>|<path_or_prop>"

# 查看全局 AVC 概览，帮助发现新暴露的 denial
adb logcat -b all -d 2>/dev/null | grep "avc: denied" | sed 's/audit([^)]*): //' | sort -u | head -80
```

MT8766 bip 示例：

```bash
adb shell ps -AZ | grep -E "bip|muxreport|ril"
adb shell getprop | grep -E "bip|muxreport|ril|boot_completed"
adb logcat -b all -d 2>/dev/null | grep "avc: denied" | grep -E "bip|bip_socket|socket_device|net_dns_prop"
```

> 注意：用 `adb shell ls -Z /dev/socket/...` 检查 socket 标签时，shell 自身可能触发 `shell -> vendor_bip_socket:sock_file getattr` denial。这类由验证命令触发的 shell denial 不应当直接作为业务修复目标。

---

## 结果判断

| 结果 | 下一步 |
|------|------|
| 目标 denial 消失，无相关新 denial | 读取 `patch-export.md`，导出 patch 到源码根 `selinux_patch/` |
| 只编译不刷机模式下编译成功 | 读取 `patch-export.md`，导出 patch 到源码根 `selinux_patch/`，并说明未做刷机/ADB 功能验证 |
| 旧 denial 变成更精确的新 tclass/perms | 说明前一轮标签或权限已生效，继续按新 denial 最小补规则 |
| 出现 unrelated AVC | 记录但不要扩大改动范围，除非用户要求处理全部系统 AVC |
| 设备不在线或刷机受限 | 给出明确恢复动作，等待用户处理后继续 |
