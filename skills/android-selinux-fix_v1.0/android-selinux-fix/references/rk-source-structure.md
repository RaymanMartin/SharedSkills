# RK (Rockchip) 源码目录结构

## 整体特点

RK / Rockchip 平台的 SELinux 分析方法与高通、展锐一致：仍然按 `scontext`、`tcontext`、`tclass`、`perms` 拆解 AVC denial，再定位 source domain 的 `.te` 文件、target type 的定义和 contexts 映射。

与高通 QSSI + target、MTK MSSI + VENDOR 不同，RK 常见 Android 14 项目以单 Android 源码树为主，重点关注 Rockchip 公共策略、SoC 平台策略和 AOSP `system/sepolicy`。

> 项目路径以实际源码为准。AOSP/RK 常见是 `device/rockchip/...`；如果客户工程使用 `devices/rockchip/...`，所有命令和判断都按实际存在的 `device(s)/rockchip` 路径替换。

---

## 主要策略路径

| 路径 | 角色 | 典型修改场景 |
|------|------|--------------|
| `device/rockchip/common/sepolicy/vendor/` | Rockchip 公共 vendor 策略 | 通用 vendor domain、HAL、设备节点、vendor service、vendor file_contexts |
| `device/rockchip/common/sepolicy/private/` | Rockchip 公共 system_ext private 策略 | system_ext 私有 allow 规则、平台侧访问 Rockchip 私有资源 |
| `device/rockchip/common/sepolicy/public/` | Rockchip system_ext public 策略（若工程启用） | 需要 vendor 可见的 system_ext type 定义 |
| `device/rockchip/rk*/sepolicy_vendor/` | SoC / 平台 vendor 策略 | rk356x、rk3588 等平台专属 vendor 权限、file_contexts、genfs_contexts |
| `device/rockchip/rk*/sepolicy/` | SoC / 平台 system_ext private 策略 | 平台专属 system_ext 私有规则（具体工程可能不存在） |
| `system/sepolicy/` | AOSP platform 策略 | framework / coredomain / platform app / neverallow / public-private type |

当前常见接入关系可在 `device/rockchip/common/modules/android_sepolicy.mk` 中确认：

```makefile
BOARD_SEPOLICY_DIRS := \
    device/rockchip/common/sepolicy/vendor \
    device/rockchip/$(TARGET_BOARD_PLATFORM)/sepolicy_vendor

SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS ?= \
    device/rockchip/common/sepolicy/private \
    device/rockchip/$(TARGET_BOARD_PLATFORM)/sepolicy
```

---

## 定位命令

```bash
# 确认 Rockchip sepolicy 接入目录
grep -rn "SEPOLICY_DIRS" device/rockchip/common device/rockchip/rk* 2>/dev/null

# 找 source domain 的 .te 文件
find device/rockchip system/sepolicy -name "<source_domain>.te" 2>/dev/null

# 找 target type 定义
grep -rn "type <target_type>" device/rockchip system/sepolicy 2>/dev/null

# 找 contexts 映射
grep -rn "<target_type>\|<path_or_service_name>" \
  device/rockchip system/sepolicy 2>/dev/null

# 查看当前产品平台变量常用位置
grep -rn "TARGET_BOARD_PLATFORM" device/rockchip 2>/dev/null | head -50
```

---

## 判断改哪个目录

| AVC 特征 | 优先修改位置 |
|----------|--------------|
| vendor HAL / vendor daemon / `u:r:vendor_*` 或 Rockchip HAL domain | `device/rockchip/common/sepolicy/vendor/` 或 `device/rockchip/rk*/sepolicy_vendor/` |
| 仅某个 RK SoC 平台出现的问题 | `device/rockchip/rk*/sepolicy_vendor/` 或对应 `rk*/sepolicy/` |
| Rockchip 通用问题，多个 rk 平台都应生效 | `device/rockchip/common/sepolicy/` |
| system_ext 私有 domain 访问 Rockchip 资源 | `device/rockchip/common/sepolicy/private/` 或 `device/rockchip/rk*/sepolicy/` |
| framework、system_server、platform_app、coredomain、AOSP public/private type | `system/sepolicy/` |
| target type 缺少文件、属性、service、genfs 标签 | 对应分区的 `file_contexts`、`property_contexts`、`service_contexts`、`genfs_contexts` |

优先级原则：

1. 先找已有 source domain `.te`，在已有文件中补规则。
2. 再判断 target type 定义在哪个分区，避免 system/private 直接引用 vendor 私有 type。
3. RK 平台没有高通 QSSI + target 双路径同步规则，但修改 `system/sepolicy/` 仍要遵守 AOSP public/private、compat/prebuilts 和 neverallow 约束。
4. SoC 专属问题放 `rk*/sepolicy_vendor/`，通用问题放 `common/sepolicy/`。

---

## 本次调试经验：system_app 读取 serialno_prop

RKUpdateService 等共享 UID 1000 的系统 APK 可能运行在 `system_app` 域；若访问设备序列号属性，常见 denial 为：

```text
scontext=u:r:system_app:s0 tcontext=u:object_r:serialno_prop:s0 tclass=file { read open getattr map }
```

处理要点：

1. 不要只看单独截取的日志文件；若同一启动日志中还有 `read/open/getattr/map`，必须合并为完整权限集合后再修。
2. `serialno_prop` 是 AOSP public property，读取通常用 `get_prop(<domain>, serialno_prop)`。
3. AOSP `system/sepolicy/public/domain.te` 对 `serialno_prop:file r_file_perms` 有 neverallow 白名单；给 `system_app` 增加读取权限时，需要同步确认并处理当前 API 对应的 prebuilts，例如 `system/sepolicy/prebuilts/api/34.0/public/domain.te`。
4. 这种修法会影响所有 `system_app` 域应用；如果只想限制到单个 APK，优先评估是否能为该 APK 建独立 seapp domain，再授予独立 domain 权限。

---

## 常见文件类型

| 文件 | 用途 |
|------|------|
| `*.te` | type 定义、domain 定义、allow / dontaudit / neverallow 规则 |
| `file_contexts` | 文件路径标签 |
| `genfs_contexts` | proc、sysfs、debugfs 等虚拟文件系统标签 |
| `property_contexts` | Android property 标签 |
| `service_contexts` | Binder service 标签 |
| `hwservice_contexts` | HIDL hwservice 标签 |

---

## 快速自检

处理 RK AVC denial 时，必须做到：

- 提取全部 denial 并按 `scontext + tcontext + tclass + perms` 去重。
- 每条 denial 都确认 source domain、target type、class、permission。
- 修改前先搜索已有 `.te` 和 type 定义，避免重复创建 type。
- 修改后先用 `make selinux_policy` 验证编译通过。
- 若用户选择“只编译不刷机”，`make selinux_policy` 成功后也要读取 `patch-export.md` 并导出 patch。
- 功能验证必须整编并刷入包含 `super.img` 的完整固件，不能只 push sepolicy 产物。