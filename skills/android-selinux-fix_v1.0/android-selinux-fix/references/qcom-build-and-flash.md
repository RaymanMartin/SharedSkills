# 高通 (Qualcomm) 编译与刷机指南

## 核心原则

> ✅ **验证 SELinux 修改必须走完整编译 + fastboot 刷入流程。**
> ❌ **禁止用 `adb push` 直接替换 precompiled_sepolicy**（会导致策略与固件不配套，引发无法开机）。

如果用户明确选择“只编译不刷机”，本轮可以在 SELinux 策略编译成功后停止刷机流程，但必须继续读取 `patch-export.md` 并导出 patch；最终结论只能说明“编译通过”，不能说明目标 denial 已在设备上消除。

---

## 编译脚本说明（以 sm6115/sc682a 为例）

项目根目录下的 `build_<platform>.sh` 支持以下参数：

| 参数 | 作用 | 适用场景 |
|------|------|---------|
| `--selinux-debug` | 只编 selinux_policy（含 kernel prepare） | 快速确认规则是否能编过 |
| `--qssi` | 编译 qssi 镜像（system/system_ext/product） | qssi14/ 下的策略有改动时用 |
| `--super` | 合并 qssi + target → super.img | 每次 --vendor 后必须跑 |
| `--target` | 完整 target 编译（含 kernel） | kernel/驱动有改动时用 |
| `--all` | qssi + target + super 全编 | 首次编译或大改动 |
| `--qfil` | 打包 QFIL 刷机包 | 需要 QFIL 工具刷机时 |

**SELinux 修改的推荐流程（根据改动范围选择）：**

```bash
# Step 1: 确认编译通过（推荐用脚本参数）
bash build_<xxx>.sh --selinux-debug

# 或手动（target 侧）
cd target/
rm -rf out/target/product/<product>/vendor/etc/selinux/
source build/envsetup.sh && lunch <target>-userdebug
make selinux_policy -j$(nproc)

# 若改动在 qssi14/ 侧（platform/system sepolicy）
cd qssi14/
source build/envsetup.sh && lunch qssi-userdebug
make selinux_policy -j$(nproc)

# 只编译不刷机模式：到这里成功即可导出 patch，不再编 super/fastboot/ADB 验证

# Step 2: 编译镜像（根据改动范围）
cd <project_root>
bash build_<xxx>.sh --vendor          # 改了 target/ 侧
# bash build_<xxx>.sh --qssi          # 改了 qssi14/ 侧（需要先跑此步）
# bash build_<xxx>.sh --vendor        # qssi 完成后再跑 vendor

# Step 3: 打包 super
bash build_<xxx>.sh --super
```

---

## Fastboot 刷入流程

> ⚠️ **`fastboot flash super` 绝对不能中途中断！**
> 5.1G super.img 约需 3 分钟（8 sparse chunks × 18s/chunk）。
> 若中断（^C / kill），设备 bootloader 会卡在等待剩余数据的状态，之后所有 fastboot 命令均挂起（进程状态 D+），**仅重插 USB 线无效，必须完整断电重启**。

```bash
IMG=target/out/target/product/bengal_515

# 1. 让设备进入 fastboot（adb 方式）
adb reboot bootloader && sleep 10

# 2. 确认 fastboot 已识别到设备
fastboot devices

# 3. 刷入各分区
fastboot flash boot         $IMG/boot.img
fastboot flash dtbo         $IMG/dtbo.img
fastboot flash super        $IMG/super.img
fastboot flash vbmeta       $IMG/vbmeta.img
fastboot flash vbmeta_system $IMG/vbmeta_system.img

# 4. 重启
fastboot reboot
```

> 若 `fastboot -w`（擦 userdata）报 mke2fs 错误，可以跳过，不影响 SELinux 验证。

**手动进入 fastboot：** 高通设备断电后，同时长按 **音量下 + 电源** 键。

---

## ADB 验证流程

```bash
# 等待设备启动
adb wait-for-device && sleep 15
adb shell getprop sys.boot_completed  # 应为 1

# 主动触发相关 app/服务
adb shell am start -n <package>/<activity>
sleep 5

# 检查 denial
adb logcat -b all -d | grep "avc: denied" | grep "<source_domain>"
```

---

## 设备救砖方法

| 情况 | 解决方法 |
|------|---------|
| 刷入后无法开机、bootloop | 重进 fastboot，`fastboot -w` 清 userdata 再重试 |
| fastboot 可见但开机异常 | `fastboot flash super <原始super.img>` 恢复 |
| **fastboot flash 挂起（D state）** | **`pkill -9 -f fastboot`；长按电源 10s 强制关机；再按 电源+音量下 进入 fastboot** |
| 无 USB 响应 | 长按电源 10s 强制断电，再进 fastboot 模式 |
| 彻底无法恢复 | 用高通 QFIL 工具重刷完整固件包 |

**fastboot D state 恢复步骤：**
```bash
# Step 1: 清除挂死的 fastboot 进程
pkill -9 -f "fastboot"

# Step 2: 在设备上 长按电源键 10秒 强制关机（重插 USB 线不够！）
# Step 3: 同时按住 电源 + 音量下 开机，进入 fastboot 模式
# Step 4: 确认连接
fastboot devices
```

---

## build_and_test.txt 核心要点（官方指导）

```
// 修改 qssi 部分的 selinux
cd qssi
source build/envsetup.sh
lunch qssi-userdebug
// 每次编译先删掉之前的，防止编译不更新
rm -rf out/target/product/qssi/system/etc/selinux/ && make selinux_policy
// 修改 target 部分的 selinux
cd target
source build/envsetup.sh
lunch bengal_515-userdebug
// 每次编译先删掉之前的，防止编译不更新
rm -rf out/target/product/bengal_515/vendor/etc/selinux/ && make selinux_policy

// 注意：make selinux_policy 只适用于确认编译生效
// 验证需要整编固件再通过 fastboot 刷入才能验证 selinux 的修改
fastboot flash boot boot.img
fastboot flash dtbo dtbo.img
fastboot flash super super.img
fastboot flash vbmeta vbmeta.img
fastboot flash vbmeta_system vbmeta_system.img
fastboot -w
fastboot reboot
```
