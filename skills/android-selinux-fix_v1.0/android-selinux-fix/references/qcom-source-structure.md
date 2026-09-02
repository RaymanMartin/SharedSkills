# 高通 (Qualcomm) 源码目录结构说明

## Android 12 后双路径架构背景

高通从 Android 12 之后普遍引入 **QSSI + target** 双路径源码架构：

| 路径 | 角色 | 类比 |
|------|------|------|
| `qssi*` / `qssi14` | 通用 system/platform 侧 | MTK `MSSI` |
| `target` | 产品 target/vendor 侧 | MTK `VENDOR` |

因此 SELinux 修复不能只按单仓思路搜索一个目录。凡是涉及 `system/sepolicy`、platform neverallow、prebuilts/api 或跨分区可见 type 的改动，都要先判断 qssi 与 target 两侧是否都参与构建。

## ⚠️ 最重要：system/sepolicy 双路径同步规则

**当修改任何 `system/sepolicy` 文件（init.te / property.te / domain.te / app.te / coredomain.te / mls 等平台策略）时，
必须同时修改 qssi14 和 target 两个目录下的对应文件：**

```
qssi14/system/sepolicy/public/xxx.te      ← QSSI 构建用
target/system/sepolicy/public/xxx.te      ← Target 构建用

qssi14/system/sepolicy/private/xxx.te
target/system/sepolicy/private/xxx.te

qssi14/system/sepolicy/prebuilts/api/     ← QSSI 侧 prebuilts
target/system/sepolicy/prebuilts/api/     ← Target 侧 prebuilts（各自同步）
```

> ❌ **只改 target/ 而不改 qssi14/ 是最常见的漏改错误！**
> ❌ **只改 qssi14/ 而不改 target/ 同样会导致 target 构建策略不一致！**

**判断是否需要双路径同步：**
- ✅ 涉及 `system/sepolicy/`（AOSP 平台策略）→ **双路径同步**
- ✅ 涉及 `device/qcom/sepolicy/` (system_ext) → 参考表格判断
- ❌ 涉及 `device/qcom/sepolicy_vndr/`（vendor 策略）→ **只改 target/**

---

## 源码目录分工

SELinux 策略分布在 **qssi** 和 **target** 两个目录，需要同时关注：

| 目录 | 负责的策略分区 | 典型修改场景 |
|------|-------------|------------|
| `qssi14/device/qcom/sepolicy/generic/public/` | system_ext public | 需要对 vendor 可见的 type 定义（service.te、file.te） |
| `qssi14/device/qcom/sepolicy/generic/private/` | system_ext private | 平台侧 allow 规则（audioserver.te、lmkd.te 等） |
| `qssi14/device/qcom/sepolicy/generic/product/` | product 策略 | 产品级权限 |
| `target/device/qcom/sepolicy/generic/public/` | system_ext public（target 侧追加） | 与 qssi 同路径，两侧合并编译 |
| `target/device/qcom/sepolicy/generic/private/` | system_ext private（target 侧追加） | vendor 相关的 file_contexts、service_contexts |
| `target/device/qcom/sepolicy_vndr/` | vendor only | vendor 进程权限（vendor_ 前缀域） |
| `target/vendor/<OEM>/<App>/sepolicy/` | 第三方预装 app | 如 Qlog、MCU 等 app 的 allow 规则 |

**判断改哪侧：**
```bash
# 同时搜索 qssi14 和 target
find qssi14/ target/ -name "<source_domain>.te" 2>/dev/null

# 查找 type 定义
grep -rn "type <target_type>" qssi14/device/qcom/sepolicy/ target/device/qcom/sepolicy/ 2>/dev/null
```

| source_domain 类型 | 优先修改位置 |
|-------------------|------------|
| vendor 进程（`vendor_` 前缀） | `target/device/qcom/sepolicy_vndr/` |
| vendor app（OEM 预装） | `target/vendor/<App>/sepolicy/` |
| system_ext 进程（audioserver、lmkd 等） | `target/device/qcom/sepolicy/generic/private/` |
| platform 系统进程（system_server 等） | `qssi14/device/qcom/sepolicy/generic/private/` |
| type 定义需跨分区可见（vendor 要引用） | `target/device/qcom/sepolicy/generic/public/` |

项目根目录有多个 `build_*.sh`，每个对应不同硬件平台：

| 脚本文件 | 编译目标示例 |
|---------|------------|
| `build_sm6115_sc682a.sh` | `bengal_515-userdebug` |
| `build_sm6225_sc200v.sh` | `bengal_515-userdebug`（不同 SKU） |
| `build_qcm2290_sc200e.sh` | `qcm2290-userdebug` |

**如何确认编译目标：**
```bash
cat build_sm6115_sc682a.sh | grep -E "lunch|TARGET_PRODUCT"
```

---

## 关键 BOARD 变量

| 变量 | 内容 | 说明 |
|------|------|------|
| `BOARD_SEPOLICY_DIRS` | sepolicy_vndr/ + App/sepolicy/ | vendor 策略，编进 vendor image |
| `SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS` | sepolicy/generic/public/ | system_ext public，vendor 可见 |
| `SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS` | sepolicy/generic/private/ | system_ext private，vendor 不可见 |

**查看方式：**
```bash
grep -r "SEPOLICY_DIRS" target/device/qcom/bengal_515/ 2>/dev/null | head -20
```

---

## 源码目录组织（target + qssi14 双侧）

SELinux 策略分布在两个顶层目录，**修改前必须先判断改哪侧**：

```
target/                              # vendor / system_ext 侧
├── device/qcom/sepolicy/
│   ├── generic/
│   │   ├── public/                  # system_ext public（vendor 可见）
│   │   │   ├── file.te              # 文件类型定义
│   │   │   └── service.te           # 公开 service 类型
│   │   └── private/                 # system_ext private（vendor 不可见）
│   │       ├── audioserver.te       # 系统进程 allow 规则
│   │       ├── service.te           # 私有 service 类型
│   │       ├── service_contexts     # 服务标签映射
│   │       ├── file_contexts        # 文件路径标签
│   │       └── compat/              # 7 个版本兼容 ignore.cil
│   │           ├── 26.0/26.0.ignore.cil
│   │           └── ... (27.0–32.0)
│   └── sepolicy_vndr/
│       └── generic/vendor/common/   # vendor domain 策略
│           └── *.te
└── vendor/quectel/<App>/
    └── prebuild/android/sepolicy/platform-T/
        └── <app>.te                 # 第三方 app SELinux 策略

qssi14/                              # system / platform 侧
├── system/sepolicy/
│   ├── public/                      # 平台公开类型（所有分区可见）
│   ├── private/                     # 平台私有规则
│   └── vendor/                      # vendor 可见规则
└── device/                          # 设备相关 platform 策略
```

**判断改哪侧：**

| 场景 | 改哪里 |
|------|--------|
| vendor 进程（`vendor_` 前缀、HAL 等）权限缺失 | `target/device/qcom/sepolicy_vndr/` |
| system_ext 进程（audioserver/lmkd 等）权限缺失 | `target/device/qcom/sepolicy/generic/private/` |
| platform 系统进程（system_server 等）权限缺失 | `qssi14/system/sepolicy/` |
| 需要跨分区可见的新类型 | `target/device/qcom/sepolicy/generic/public/` |
| vendor app（如 qlog）缺少 service 权限 | `target/vendor/<App>/sepolicy/<app>.te` |

---

## 设备分区与 SELinux 文件位置

| 分区 | SELinux 文件路径 |
|------|----------------|
| `/odm/` | `/odm/etc/selinux/precompiled_sepolicy`（预编译 binary） |
| `/odm/` | `/odm/etc/selinux/precompiled_sepolicy.{plat,system_ext,product}_sepolicy_and_mapping.sha256` |
| `/vendor/` | `/vendor/etc/selinux/vendor_sepolicy.cil` |
| `/vendor/` | `/vendor/etc/selinux/plat_pub_versioned.cil` |
| `/vendor/` | `/vendor/etc/selinux/vendor_service_contexts` |
| `/system_ext/` | `/system_ext/etc/selinux/system_ext_sepolicy.cil` |
| `/system_ext/` | `/system_ext/etc/selinux/mapping/33.0.cil` |

> ⚠️ vendor 文件在 `/vendor/etc/selinux/`（TOP级，无子目录）

---

## SHA256 Sidecar 校验机制（仅供了解）

init 启动时通过对比 SHA256 sidecar 来决定是否加载 precompiled binary：
1. plat + system_ext + product 三个 sidecar 都匹配 → 加载 precompiled binary
2. 任意不匹配 → 回退到 CIL 编译（通常会失败）

> 这是设备内部机制，**无需手动干预**。通过 fastboot 刷入完整固件后，所有 sidecar 自动保持一致。

---

## 验证方式（重要！）

> ❌ **禁止使用 `adb push` 推送 SELinux 策略文件**  
> 直接推送 `precompiled_sepolicy` 或 `.cil` 文件会导致策略与固件不配套，引发设备无法开机。

✅ **正确的验证方式：修改源码 → 整编 vendor → 打包 super → fastboot 刷入**

详见 [编译与刷机指南](./qcom-build-and-flash.md)。

---

## 设备救砖方法

| 情况 | 恢复方法 |
|------|---------|
| 刷入后 bootloop / 无法开机 | 重进 fastboot，`fastboot -w` 清 userdata 后重刷 super.img |
| 设备无 USB 响应 | 长按电源 10s 强制断电，再进 fastboot（高通：音量下+电源） |
| fastboot 可见 | `fastboot flash super <原始super.img> && fastboot reboot` |
| fastboot 不可见 | 使用高通 QFIL 工具重刷完整固件包 |
