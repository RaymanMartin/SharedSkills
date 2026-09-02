# 高通 Android 14 SELinux 修改规律（从实战与参考资料中提炼）

## ⚠️ 最重要规则：高通 QSSI 架构双路径同步

**当修改 `system/sepolicy`（平台侧 SELinux，包含 init.te / property.te / domain.te / app.te / coredomain.te / mls 等）时，
必须同时修改两个目录：**

```
qssi14/system/sepolicy/       ← QSSI 镜像构建使用
target/system/sepolicy/       ← Target 产品镜像构建使用
```

这两个目录是**独立的拷贝**，两者都会参与编译。只改一处会导致另一侧构建出的镜像与期望不符。

### 需要双路径同步的文件（常见）

| 文件 | 双路径同步 |
|------|-----------|
| `public/init.te` | ✅ qssi14/ + target/ |
| `private/property.te` | ✅ qssi14/ + target/ |
| `private/domain.te` | ✅ qssi14/ + target/ |
| `public/app.te` | ✅ qssi14/ + target/ |
| `private/coredomain.te` | ✅ qssi14/ + target/ |
| `private/mls` | ✅ qssi14/ + target/ |
| `prebuilts/api/*/` | ✅ qssi14/ + target/ 各自的 prebuilts |

### 只改一处的文件（vendor 侧）

| 文件 | 只改哪里 |
|------|---------|
| `sepolicy_vndr/` 下的 `.te` | 只改 `target/device/qcom/sepolicy_vndr/` |
| HAL `.te` 文件 | 只改 `target/system/sepolicy/vendor/` 或 `target/device/qcom/sepolicy/` |

---

## 常见 AVC Denial 修复模式（从参考文档与实战总结）

### 1. sysfs 文件权限（neverallow 注意！）

```
avc: denied { write } for name="discard_max_bytes" dev="sysfs" scontext=u:r:init:s0 tcontext=u:object_r:sysfs:s0 tclass=file
```

**错误做法**：直接 `allow init sysfs:file write` → 触发 neverallow

**正确做法**：
- 若是通用 sysfs（无法细化），注释掉 neverallow 后再 allow（需同步 prebuilts/api/所有版本）
- 若有具体路径，在 `file_contexts` 定义新类型（如 `sysfs_eth`），在 `file.te` 声明，再 allow 新类型（参见 selinux总结.pdf 第7节）

### 2. system_server / platform 进程访问 sysfs

```
avc: denied { read } for name="name" dev="sysfs" scontext=u:r:system_server:s0 tcontext=u:object_r:sysfs:s0 tclass=file
```

修改文件：`qssi14/system/sepolicy/private/system_server.te` 和 `target/system/sepolicy/private/system_server.te`
```te
allow system_server sysfs:file { read getattr open };
```
同样需检查是否有 neverallow 冲突。

### 3. tee_device 权限（参考 0001-Qsee-support-platform_app-use.patch）

```
avc: denied { read } for name="mmcblk0" dev="tmpfs" scontext=u:r:tee:s0 tcontext=u:object_r:root_block_device:s0 tclass=blk_file
```

**修改 coredomain.te**（注释 neverallow，双路径同步）：
```te
# qssi14/system/sepolicy/private/coredomain.te
# target/system/sepolicy/private/coredomain.te
#full_treble_only(`
#  neverallow coredomain tee_device:chr_file { open read append write ioctl };
#')
```

**修改 app.te**（双路径同步 + 所有 prebuilts/api/版本）：
```te
# public/app.te
#neverallow appdomain tee_device:chr_file { read write };
```

### 4. platform_app 跨 MLS 安全级别访问（参考 patch 和 selinux总结.pdf 第7节）

**现象**：AVC log 中出现 `s0:c512,c768` 字样 → MLS 级别不匹配

**修改 private/mls**（双路径同步 + 所有 prebuilts/api/版本）：
```
# 在 mlsconstrain { file ... } { read getattr execute } 行末尾添加:
(... or t1 == platform_app);

# 在 mlsconstrain { file ... } { write setattr append ... } 行末尾添加:
(... or t1 == platform_app);
```

### 5. debugfs 访问（enforce_debugfs_restriction 宏）

```
avc: denied { setattr } for name="ext_csd" dev="debugfs" scontext=u:r:init:s0 tcontext=u:object_r:debugfs_mmc:s0 tclass=file
```

**修改 private/domain.te**（双路径同步 + prebuilts/api/31~33.0/private/domain.te）：
将 `-init` 从 `userdebug_or_eng(...)` 块内移到块外，使 user build 中 init 也豁免。

### 6. property 访问（system_internal_prop 私有类型跨 vendor 访问）

**vendor 进程无法直接引用 private 类型，只能通过 PUBLIC attribute 授权：**

```te
# private/property.te 中展开宏，加 -<public_attribute> 例外：
neverallow { domain -coredomain -hal_secure_element_server } init_service_status_private_prop:file no_rw_file_perms;

# 通过 attribute 在 system 侧授权读取（不在 vendor/*.te 写）:
get_prop(hal_secure_element_server, init_service_status_private_prop)
```

### 7. configfs dir 写权限（vendor 初始化脚本）

```
avc: denied { write } for name="0x409" dev="configfs" scontext=u:r:vendor_qti_init_shell:s0 tcontext=u:object_r:configfs:s0 tclass=dir
```

修改 `target/device/qcom/sepolicy_vndr/generic/vendor/common/init_shell.te`：
```te
allow vendor_qti_init_shell configfs:dir write;
```

---

## 日志分析完整性要求

**每次分析 AVC 日志必须处理日志中的全部 denial，不允许遗漏**：

从 `selinux_debug.txt`（qcom-avc-example.txt）可见，同一次日志中存在多种不同进程的 denial：
- `tee` → `root_block_device:blk_file read`
- `vendor_qti_init_shell` → `configfs:dir write`
- `init` → `sysfs:file write`
- `hal_secure_element_default` → `init_service_status_private_prop:file read`
- `init` → `debugfs_mmc:file setattr`
- `system_server` → `sysfs:file read`  ← **容易遗漏！**

步骤：
1. 对日志做 `grep "avc: denied"` 提取全部 denial
2. 去重归并（同一 scontext+tcontext+tclass+perm 只处理一次）
3. 列出完整清单，逐条处理，处理完后打 ✅

---

## neverallow 修改需同步的文件范围

当修改任何 `system/sepolicy/public/` 或 `private/` 中的文件时，`prebuilts/api/` 中对应文件也必须同步（`sepolicy_freeze_test` 会 diff 检测）：

### 需要同步 prebuilts 的规则

- `sepolicy_freeze_test` 仅检查 `prebuilts/api/33.0/` 与当前 `public/` + `private/` 的一致性
- 但为兼容 neverallow 检测，**28.0 ~ 32.0 中的 neverallow 也需注释**（否则 `sepolicy_neverallows` check 会 fail）

### 同步范围速查

| 修改文件 | 需同步哪些 prebuilts |
|---------|-------------------|
| `public/init.te` neverallow | `prebuilts/api/28.0~33.0/public/init.te` 注释对应 neverallow |
| `private/domain.te` | `prebuilts/api/31.0~33.0/private/domain.te` |
| `private/property.te` | `prebuilts/api/31.0~33.0/private/property.te` |
| `private/coredomain.te` | `prebuilts/api/30.0~33.0/private/coredomain.te` |
| `public/app.te` | `prebuilts/api/28.0~33.0/public/app.te` |
| `private/mls` | `prebuilts/api/28.0~33.0/private/mls` |

> 注意：qssi14/ 和 target/ 各有自己的 prebuilts/api/ 目录，都需要同步。

---

## 参考资料说明

| 文件（位于 `../doc/`） | 内容 |
|------|------|
| `Android SELinux讲解与问题排查.pptx` | 高通方案 SELinux 完整讲解：MLS 规则、tee_device、audit2allow 使用方法 |
| `selinux总结.pdf` | SELinux 基础理论 + 实战问题解法（neverallow、mls、rc service 无法启动） |
| `102208__Android 12~Android 13 SELinux客制化指导手册V1.3.pdf` | Android 12/13 SELinux 客制化规范（目录结构、BOARD 变量、compat ignore.cil） |
| `32962_Android10SELinux指导文档V1.0.pdf` | Android 10 SELinux 指导文档 |
| `0001-Qsee-support-platform_app-use.patch` | 实战 patch：platform_app 访问 tee_device + MLS mlsconstrain 豁免，涵盖 28.0~33.0 所有 prebuilts |
| `qcom-avc-example.txt` | 实际设备 AVC denial 样例（bengal_515，Android 14） |
