# MTK (MediaTek) 源码目录结构

## 整体特点

MTK 从 Android 12 之后导入类似高通 QSSI/target 的双路径源码架构，Android 13 项目常见为 **MSSI + VENDOR**：

| 顶层目录 | 类比 | 主要内容 |
|------|------|------|
| `MSSI/` | 高通 QSSI | system / platform 侧源码与策略 |
| `VENDOR/` | 高通 target/vendor | vendor、odm、device、modem 侧源码与策略 |

> 经验规则：Android 12 后遇到 MTK SELinux 问题，先按双路径架构判断 AVC 的 source domain 和 target type 属于 `MSSI` 还是 `VENDOR`/modem。不要在 `MSSI/system/sepolicy` 中直接引用只存在于 `VENDOR` modem 策略里的 vendor domain，例如 `bip`。

---

## 主要 SELinux 路径

| 路径 | 说明 | 常见场景 |
|------|------|------|
| `MSSI/system/sepolicy/` | platform/system 策略 | AOSP core domain、platform neverallow、system property |
| `MSSI/device/mediatek/sepolicy/` | MSSI 侧 MTK device 策略 | system/platform 相关 MTK 客制化 |
| `VENDOR/system/sepolicy/` | VENDOR 侧 platform 策略拷贝 | 构建 vendor/super 时可能参与校验 |
| `VENDOR/device/mediatek/` | vendor device 策略入口 | BOARD 变量、vendor 策略目录聚合 |
| `VENDOR/vendor/mediatek/proprietary/modem/<modem>/sepolicy/s0/` | modem 独立策略 | modem 进程、socket、property、file_contexts，最常见于 RIL/BIP/IMS 类问题 |
| `VENDOR/vendor/mediatek/proprietary/modem/<modem>/init_rc/s0/` | modem init rc | modem service、socket 创建、service seclabel |

MT8766 实战中，`bip` 策略实际位于：

```text
VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/sepolicy/s0/bip.te
VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/sepolicy/s0/file.te
VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/sepolicy/s0/file_contexts
VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/init_rc/s0/init.bip.rc
```

---

## modem 策略定位方法

```bash
# 找 source domain 的 .te 文件
find VENDOR/vendor/mediatek/proprietary/modem -name "<domain>.te" 2>/dev/null

# 找 target type 定义
grep -rn "type <target_type>" VENDOR/vendor/mediatek/proprietary/modem VENDOR/device/mediatek MSSI/device/mediatek 2>/dev/null

# 找 socket / 文件路径标签
grep -rn "<socket_or_path_name>" VENDOR/vendor/mediatek/proprietary/modem/*/sepolicy 2>/dev/null

# 找 init rc 中 service 和 socket 创建位置
grep -rn "service .*<name>\|socket <name>" VENDOR/vendor/mediatek/proprietary/modem/*/init_rc 2>/dev/null

# 找 modem sepolicy 如何被构建引入
grep -rn "MTK_MODEM_APPS_SEPOLICY_DIRS\|modem.*sepolicy" VENDOR/device VENDOR/vendor/mediatek 2>/dev/null
```

---

## 判断改哪个目录

| AVC 特征 | 优先修改位置 |
|------|------|
| `scontext=u:r:<modem_domain>:s0`，如 `bip`、RIL、IMS 相关 domain | `VENDOR/vendor/mediatek/proprietary/modem/<modem>/sepolicy/s0/<domain>.te` |
| modem service 创建 socket、socket 名称或标签不对 | `VENDOR/vendor/mediatek/proprietary/modem/<modem>/init_rc/s0/*.rc` + `sepolicy/s0/file_contexts` |
| target type 定义在 modem `file.te` / `property.te` | 同一 modem `sepolicy/s0/` 内补规则 |
| platform/system domain 访问 system type | `MSSI/system/sepolicy/`，并检查 `VENDOR/system/sepolicy/` 是否有对应拷贝 |
| vendor/modem domain 访问 platform private property/type | 优先避免直接 allow；检查 neverallow，可用 `dontaudit` 或改为公开属性/正确 vendor 属性 |

---

## MSSI 与 VENDOR 可见性注意

MTK 双路径下，`MSSI/system/sepolicy` 属于 platform 编译上下文，不一定能看到 modem 独立策略中定义的类型。

已验证踩坑：

```text
在 MSSI/system/sepolicy/private/domain.te 的 neverallow 中加入 -bip
```

会导致：

```text
unknown type bip
```

原因是 `bip` 定义在 VENDOR modem sepolicy 中，platform 策略编译器不可见。

正确方向：

- 不在 MSSI platform policy 中直接引用 vendor/modem domain。
- vendor/modem domain 的 allow 规则放回对应 modem `sepolicy/s0/<domain>.te`。
- platform private property/type 被 neverallow 限制时，优先改业务属性归属或用 `dontaudit` 压制无害探测，不要硬穿 neverallow。

---

## 设备侧 SELinux 文件位置

| 分区 | 常见文件 |
|------|------|
| `/vendor/` | `/vendor/etc/selinux/vendor_sepolicy.cil`、vendor file/property/service contexts |
| `/odm/` | modem/odm 相关策略产物，具体随项目变化 |
| `/system/` | platform sepolicy、mapping、contexts |

验证时以源码修改 + 完整镜像刷入为准，不要直接 `adb push` 替换策略产物。
