# 展锐 (Unisoc) 编译与刷机指南

## 核心原则

> ✅ **验证 SELinux 修改必须走完整编译 + fastboot 刷入流程。**
> ❌ **禁止用 `adb push` 直接替换策略文件**（会导致策略与固件不配套）。
> ⚠️ **展锐没有 `make selinux_policy` 快速验证命令**，需整编 system 或 vendor 镜像。

如果用户明确选择“只编译不刷机”，本轮可以在对应 system/vendor 编译目标成功后停止刷机流程，但必须继续读取 `patch-export.md` 并导出 patch；最终结论只能说明“编译通过”，不能说明目标 denial 已在设备上消除。

---

## 编译脚本说明（以 uis7885 为例）

脚本：`compile_uis7885.sh`，支持以下目标：

| 目标 | 作用 | 适用场景 |
|------|------|---------|
| `system` | 编译 system/system_ext 镜像 | 修改了 `sepolicy/system/` 或模块 `msepolicy/system/` |
| `vendor` | 编译 vendor 镜像 | 修改了 `sepolicy/vendor/` 或模块 `msepolicy/vendor/` |
| `super` | 打包 super.img | **每次 system/vendor 编译后必须执行** |
| `all` | 完整编译 | 首次或大改动 |
| `pac` | 打包 PAC 刷机包 | 需要 PAC 包时使用 |
| `boot` | 编译 boot 镜像 | kernel/initrc 有改动时 |

**SELinux 修改推荐流程（按改动位置选择）：**

```bash
# 改了 sepolicy/system/ 或模块 msepolicy/system/
bash compile_uis7885.sh system

# 改了 sepolicy/vendor/ 或模块 msepolicy/vendor/
bash compile_uis7885.sh vendor

# 只编译不刷机模式：对应 system/vendor 编译成功即可导出 patch，不再打包 super/fastboot/ADB 验证

# 每次以上编译完成后必须打包 super
bash compile_uis7885.sh super
```

> ⚠️ 若同时修改了 system 和 vendor 两侧，需先编 system，再编 vendor，最后打包 super。

---

## 判断编译哪个目标

| 修改的文件路径 | 需要的编译步骤 |
|-------------|-------------|
| `device/sprd/mpool/sepolicy/system/` | `system` → `super` |
| `device/sprd/mpool/sepolicy/vendor/` | `vendor` → `super` |
| `device/sprd/mpool/module/system_ext/*/msepolicy/system/` | `system` → `super` |
| `device/sprd/mpool/module/vendor/*/msepolicy/vendor/` | `vendor` → `super` |
| 两侧都改 | `system` → `vendor` → `super` |

---

## Fastboot 刷入流程

> ⚠️ **`fastboot flash super` 绝对不能中途中断！**
> super.img 分多个 sparse chunk 传输，中断后 bootloader 卡在等待剩余数据，必须完整断电重启才能恢复。

```bash
IMG=out/target/product/uis7885_2h10

# 重启进入 fastboot 并确认设备
adb reboot bootloader && sleep 12 && fastboot devices

# 刷入 super（包含 system/vendor/product 等分区）
fastboot flash super $IMG/super.img

# 若同时改了 kernel/dtbo（SELinux 修改通常不需要）
# fastboot flash boot  $IMG/boot.img
# fastboot flash dtbo  $IMG/dtbo.img

# 刷入 vbmeta（如有签名验证问题时）
# fastboot flash vbmeta        $IMG/vbmeta.img
# fastboot flash vbmeta_system $IMG/vbmeta_system.img

fastboot reboot
```

> 纯 SELinux 策略修改（仅 .te 文件）**通常只需刷 super**，不需要 boot/dtbo/vbmeta。

---

## Fastboot 卡死恢复

```bash
# 1. 强制杀掉所有 fastboot 进程
pkill -9 -f "fastboot"

# 2. 设备完整断电重启（长按电源键 10s 强制关机）
# 3. 按住 电源 + 音量下 开机，重新进入 fastboot 模式
# 4. 确认设备识别
fastboot devices
```

---

## 验证 SELinux 修改是否生效

```bash
# 等待设备启动完成
adb wait-for-device && sleep 20
adb shell getprop sys.boot_completed    # 输出 1 表示启动完成

# 触发操作（例如启动特定 app），不要清空 logcat，保留启动阶段 denial
adb shell monkey -p <package> -c android.intent.category.LAUNCHER 1
sleep 8

# 检查 denial 是否消除
adb logcat -b all -d | grep "avc: denied" | grep "<domain>"

# 检查 SELinux 模式
adb shell getenforce
```

**结果判断：**
- ✅ 无 denial → 修复成功
- ❌ 仍有 denial → 分析新 denial，继续修复
- ❌ 出现新的不同 domain 的 denial → 同类问题波及其他域，按相同方式继续修复

---

## ⚠️ 特殊设备 fastboot 问题处理（UIS7885 已验证）

某些展锐设备 fastboot 存在已知兼容性问题，遇到时按以下方案处理：

### 问题一：`fastboot flash vbmeta_a` 挂死

**现象：** `fastboot flash vbmeta_a` 执行后无响应，USB 无输出，进程卡死（D state）。

**原因：** 该设备 bootloader 对 vbmeta 签名验证有特殊限制，刷入会触发死锁。

**处理方案：** **直接跳过 vbmeta 刷写**，纯 SELinux 策略修改不需要刷 vbmeta。

```bash
# ✅ 只刷 super（SELinux 修改通常只需这一步）
fastboot flash super $IMG/super.img
fastboot reboot

# ❌ 不要执行以下命令
# fastboot flash vbmeta_a     ← 会挂死
# fastboot flash vbmeta_system_a
```

---

### 问题二：`fastboot flash super` 失败（"target didn't report max-download-size"）

**现象：**
```
Sending 'super' (xxxxx KB)
FAILED (target didn't report max-download-size)
```

**原因：** 设备 bootloader 未上报 max-download-size，fastboot 无法分片传输 super.img。

**处理方案：** 改用 `simg2img + adb shell dd` 直接写入 raw 分区。

**前提条件：**
1. 设备已通过 `adb root` 获得 root 权限
2. 知道 super 分区对应的块设备路径（通常为 `/dev/block/sda46`，可用下方命令确认）

```bash
# 查找 super 分区块设备
adb shell ls -la /dev/block/by-name/ | grep super

# 查看分区实际大小（bytes）
adb shell blockdev --getsize64 /dev/block/by-name/super
```

**刷写流程：**

```bash
IMG=out/target/product/uis7885_2h10
SIMG2IMG=out/host/linux-x86/bin/simg2img
SUPER_BLOCK=/dev/block/sda46   # 确认后替换为实际路径

# Step 1: 转换 sparse → raw（/dev/stdout 不支持，必须写临时文件）
$SIMG2IMG $IMG/super.img /tmp/super_raw.img

# Step 2: 确认 raw 文件大小与分区匹配
ls -lh /tmp/super_raw.img

# Step 3: adb dd 写入分区（确保设备已 root）
adb root && sleep 3
cat /tmp/super_raw.img | adb shell "dd of=$SUPER_BLOCK bs=4M 2>&1; echo DD_OK"

# Step 4: 等待写入完成（5.5G 约需 170 秒，33 MB/s）
# 看到 "DD_OK" 后重启
adb reboot

# Step 5: 清理临时文件
rm -f /tmp/super_raw.img
```

> ⚠️ **simg2img 不支持 `/dev/stdout` 作为输出**，必须先写到临时文件，再用 `cat | adb shell dd` 管道传输。
> ✅ `/tmp` 目录通常挂载在 nvme 上，有充足空间（可用 `df -h /tmp` 确认）。

---

### 问题三：fastboot 命令挂死恢复

```bash
# 1. 强制杀掉所有 fastboot 进程
pkill -9 -f "fastboot"

# 2. 设备完整断电重启（长按电源键 10s 强制关机）
# 3. 按住 电源 + 音量下 开机，重新进入 fastboot 模式
# 4. 确认设备识别
fastboot devices
```

---

## 常见编译错误

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| `unknown type <type_name>` | type 未定义就引用 | 先在 `property.te` 或 `file.te` 定义 type |
| `neverallow violation` | 规则违反平台 neverallow | 改用正确的规则路径或新定义 type |
| `duplicate type definition` | type 在多处重复定义 | 检查 module 和主策略中是否重复 |
| `duplicate allow rule` | allow 规则已存在 | 搜索确认后删除重复的规则 |
