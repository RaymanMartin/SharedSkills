# RK (Rockchip) 编译与刷机指南

## 核心原则

> `make selinux_policy` 只用于快速确认 SELinux 规则能否编译通过。  
> SELinux 功能是否真正生效，必须整编生成包含 `super.img` 的完整固件，并通过 fastboot 整刷后再验证。

如果用户明确选择“只编译不刷机”，本轮可以在 `make selinux_policy` 成功后停止刷机流程，但必须继续导出 patch，并在结论中写明：仅完成策略编译验证，未验证目标 denial 在设备上消除。

禁止用 `adb push` 单独替换 `precompiled_sepolicy`、`.cil`、`vendor_sepolicy.cil` 等策略产物。这样会造成策略文件、mapping、sidecar 或镜像内容不一致，验证结论不可信，严重时会导致无法开机。

---

## 快速验证编译通过

在源码根目录完成 lunch 后执行：

```bash
source build/envsetup.sh
lunch <target_product>-userdebug
make selinux_policy -j$(nproc)
```

只编译不刷机模式的收尾动作：

1. 确认终端输出包含 `build completed successfully` 或等价成功信息。
2. 读取 `patch-export.md`。
3. 将 RK SELinux 修改导出到源码根目录 `selinux_patch/`。
4. 汇报 patch 路径，并说明未执行整编、fastboot 刷机和 ADB/logcat 功能验证。

如果当前终端已经由项目脚本完成 envsetup/lunch，可直接运行：

```bash
make selinux_policy -j$(nproc)
```

遇到规则未更新或怀疑缓存时，可先清理对应产品输出中的 SELinux 产物再重编：

```bash
rm -rf out/target/product/<product>/vendor/etc/selinux \
       out/target/product/<product>/system/etc/selinux \
       out/target/product/<product>/system_ext/etc/selinux
make selinux_policy -j$(nproc)
```

---

## 整编生成 super

RK 项目常见 `build.sh` 支持 `-A` 编译 Android，并在编译后调用 `mkimage.sh` 复制/打包镜像到 `rockdev/Image-<TARGET_PRODUCT>/`。实际参数以项目脚本为准。

常见流程：

```bash
source build/envsetup.sh
lunch <target_product>-userdebug
./build.sh -A -J$(nproc)
```

如果项目使用独立打包脚本，也要确保最终生成或更新 `super.img`：

```bash
make -j$(nproc)
./mkimage.sh
```

输出目录通常为：

```bash
rockdev/Image-<TARGET_PRODUCT>/
out/target/product/<TARGET_PRODUCT>/
```

刷机前必须确认存在：

```bash
ls rockdev/Image-<TARGET_PRODUCT>/super.img \
   rockdev/Image-<TARGET_PRODUCT>/boot.img \
   rockdev/Image-<TARGET_PRODUCT>/dtbo.img \
   rockdev/Image-<TARGET_PRODUCT>/vbmeta.img \
   rockdev/Image-<TARGET_PRODUCT>/vbmeta_system.img
```

---

## Fastboot 刷入流程

> `fastboot flash super` 不能中断。super 通常很大，中途断开会导致 fastboot 卡住或设备处于不完整刷写状态。

```bash
IMG=rockdev/Image-<TARGET_PRODUCT>

adb reboot bootloader
fastboot devices

fastboot flash boot          $IMG/boot.img
fastboot flash dtbo          $IMG/dtbo.img
fastboot flash super         $IMG/super.img
fastboot flash vbmeta        $IMG/vbmeta.img
fastboot flash vbmeta_system $IMG/vbmeta_system.img

fastboot reboot
```

如果工程产物在 `out/target/product/<TARGET_PRODUCT>/`，则将 `IMG` 改为对应目录。

---

## ADB 验证流程

验证时不要清空 logcat buffer，保留启动日志：

```bash
adb wait-for-device
adb shell getprop sys.boot_completed
adb shell getenforce

# 触发目标功能后抓取全部 buffer 中的 denial
adb logcat -b all -d | grep "avc: denied" | grep -E "<source_domain>|<target_type>|<module_keyword>"
```

验证通过标准：

- `getenforce` 为 `Enforcing`。
- 目标功能已触发。
- 目标 denial 不再出现。
- 若出现新的 denial，必须回到 AVC 提取、去重和逐条分析环节。

---

## 失败恢复

| 情况 | 处理方式 |
|------|----------|
| `make selinux_policy` unknown type | 回到 `rk-source-structure.md` 检查 type 定义分区和可见性 |
| neverallow 失败 | 先判断是否授予了过宽权限；确需改 AOSP 规则时同步处理相关 prebuilts/api |
| 刷入后 bootloop | 重进 fastboot，重新刷入上一版完整固件，至少包含 `super.img` |
| fastboot 卡住 | 不要继续叠加刷写命令；停止 fastboot 进程，设备断电重进 bootloader 后重刷完整镜像 |
| ADB 不在线 | 等待开机、检查 USB 授权；仍不在线则先恢复固件再继续 SELinux 验证 |