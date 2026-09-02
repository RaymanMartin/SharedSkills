# Android SELinux 通用知识库

> 本文档包含通用知识（适用于高通、展锐、MTK 平台）以及平台特有的深层知识（⚠️ 标注特定平台的章节）。

## AVC Denial 日志结构

```
avc: denied { <perms> } for pid=<PID> comm="<process>"
  path="<file_path>"
  scontext=u:r:<source_domain>:s0
  tcontext=u:object_r:<target_type>:s0
  tclass=<class>
  permissive=0
```

| 字段 | 含义 |
|------|------|
| scontext | 发起操作的进程安全上下文（主体） |
| tcontext | 被操作对象的安全上下文（客体） |
| tclass | 对象类别（file/dir/service_manager/binder 等） |
| perms | 被拒绝的权限集合 |

---

## Android 12 后双路径架构速查

Android 12 后，高通和 MTK 都引入了类似的双路径源码架构。修 SELinux 前先判断当前改动属于 system/platform 侧还是 vendor/device/modem 侧。

| 平台 | system/platform 侧 | vendor/product 侧 | 关键提醒 |
|------|------|------|------|
| 高通 | `qssi*` / `qssi14` | `target` | 修改 `system/sepolicy` 通常要同步 qssi 与 target，并同步各自 prebuilts |
| MTK | `MSSI` | `VENDOR` | 不要在 `MSSI/system/sepolicy` 直接引用只定义在 VENDOR modem sepolicy 的 type |
| 展锐 | 单仓 `device/sprd/mpool/sepolicy/system` | 单仓 `device/sprd/mpool/sepolicy/vendor` | 无 QSSI/MSSI 双仓概念，按 mpool system/vendor 路径选择编译目标 |

---

## 策略文件目录结构（高通方案）

```
target/device/qcom/sepolicy/
├── generic/
│   ├── public/          → system_ext public（vendor 可见）
│   │   ├── *.te         → 类型定义、属性
│   │   └── service.te   → 公开 service 类型
│   ├── private/         → system_ext private（vendor 不可见）
│   │   ├── *.te         → 具体 allow 规则
│   │   ├── service.te   → 私有 service 类型
│   │   ├── service_contexts
│   │   └── file_contexts
│   └── vendor/common/   → vendor 策略
└── sepolicy_vndr/
    └── generic/vendor/common/
        └── *.te         → vendor domain 策略

target/vendor/quectel/<App>/prebuild/android/sepolicy/platform-T/
└── <app>.te             → 第三方 app SELinux 策略
```

### Compat ignore.cil 文件位置
新增类型必须同步添加到以下7个文件的 `new_objects` 节点：
```
target/device/qcom/sepolicy/generic/private/compat/26.0/26.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/27.0/27.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/28.0/28.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/29.0/29.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/30.0/30.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/31.0/31.0.ignore.cil
target/device/qcom/sepolicy/generic/private/compat/32.0/32.0.ignore.cil
```

添加格式示例（添加到 `new_objects` 括号内）：
```cil
(type new_type_name)
```

---

## Neverallow 规则常见限制

| 限制 | 说明 | 解决方案 |
|------|------|---------|
| coredomain 不能创建 vendor type sock_file | core 进程不能在 vendor 目录创建 socket | 定义新类型并赋予 `coredomain_socket` 属性 |
| app 不能访问 private service type | private 类型对 vendor 不可见 | 将类型从 private/service.te 移到 public/service.te |
| vendor 进程不能访问 system type | 跨分区隔离 | 在 vendor 一侧定义对应类型并设置正确属性 |

---

## 常见 tclass 和 perms

| tclass | 常见权限 | 场景 |
|--------|---------|------|
| `file` | read write open getattr | 访问普通文件 |
| `dir` | read write search add_name remove_name | 目录操作 |
| `sock_file` | create write read | Unix socket 文件 |
| `service_manager` | find add | 查找/注册服务 |
| `binder` | call transfer | Binder IPC 调用 |
| `property_service` | set | 设置系统属性 |

---

## service_manager 类型问题

当报错 `find` on `default_android_service` 时：
- 表示目标服务名没有在任何 service_contexts 中标记类型
- 需在 `service_contexts` 或 `vendor_service_contexts` 中添加：
  ```
  vendor.xxx.service.Name/default  u:object_r:<type>:s0
  ```
- 若该 type 定义在 system_ext private，vendor app 无法引用 → 需移到 public

---

## 设备信息快速获取

```bash
# 设备 SELinux 状态
adb shell getenforce

# 策略版本（关键！）
adb shell xxd /odm/etc/selinux/precompiled_sepolicy | head -2
# offset 0x10: 1e=v30, 21=v33

# 查看当前 avc denial
adb logcat -d | grep "avc: denied"

# 查看 service 上下文
adb shell service list | grep <service_name>
adb shell cat /vendor/etc/selinux/vendor_service_contexts | grep <service_name>
```

---

## ❗ vendor 类型在 system_ext 策略中不可见（高通特有）

### 规则

定义在 `target/device/qcom/sepolicy_vndr/` 下的类型（`vendor_` 前缀类型，如 `vendor_sysfs_devfreq`）**对 system_ext 策略编译器不可见**。

| 策略编译上下文 | 可见的类型 |
|--------------|-----------|
| `system_ext private` (`target/device/qcom/sepolicy/generic/private/`) | platform 公共类型 + system_ext 类型 |
| `vendor` (`target/device/qcom/sepolicy_vndr/`) | platform 公共类型 + system_ext public 类型 + vendor 类型 |

### 典型错误

```
device/qcom/sepolicy/generic/private/app.te:34:
  ERROR 'unknown type vendor_sysfs_devfreq' at token ';'
```

**原因：** 在 `system_ext private/app.te` 中写了 `allow appdomain vendor_sysfs_devfreq:dir search`，但 `vendor_sysfs_devfreq` 是 vendor 类型，system_ext 编译上下文根本不知道它的存在。

### 正确做法

**普通 app (appdomain) 访问 vendor 类型**的 allow 规则，必须写在 **vendor 侧**：
```
target/device/qcom/sepolicy_vndr/generic/vendor/common/app.te
```

参照文件中已有模式：
```te
# 已有规则（参照对象）
allow appdomain vendor_npu_device:chr_file r_file_perms;

# 新增
allow appdomain vendor_sysfs_devfreq:dir search;
```

### neverallow 备忘：untrusted_app + sysfs

```
# AOSP app_neverallows.te 中存在的限制：
neverallow all_untrusted_apps sysfs_type:file { no_w_file_perms no_x_file_perms };
neverallow all_untrusted_apps sysfs:file no_rw_file_perms;
```

- 只限制 **`file` 类**的 write/execute
- **`dir:search` 不受任何 neverallow 限制**，可安全添加

---

### ❗ Treble Compat 映射缺失（高通特有）

#### 触发条件

- vendor API level（如 33）低于 system_ext API level（如 34）
- vendor 的 `plat_pub_versioned.cil` 中有 `<type>_33_0` 属性声明
- 但 `system_ext/etc/selinux/mapping/33.0.cil` 中没有对应的 `typeattributeset` 映射

### 症状

- vendor `.te` 中已有 `allow <app> <type>_33_0:service_manager find` 规则
- device `vendor_sepolicy.cil` 中可以确认该 allow 存在
- 但 avc denial 依然发生，且 tcontext 是 `<type>` 而不是 `<type>_33_0`

### 诊断命令

```bash
# 从设备拉取运行时 compat 文件
adb pull /system_ext/etc/selinux/mapping/33.0.cil /tmp/
grep "<type_name>" /tmp/33.0.cil
# 若只有 expandtypeattribute/typeattribute 而无 typeattributeset → 空属性集，是此问题

adb pull /vendor/etc/selinux/plat_pub_versioned.cil /tmp/
grep "<type_name>_33_0" /tmp/plat_pub_versioned.cil
# 只有 (typeattribute vendor_xxx_33_0) 无 typeattributeset → 确认
```

### 修复位置

`qssi14/device/qcom/sepolicy/generic/private/compat/33.0/33.0.cil`

参照同文件中已有的同类型条目（注意：`vendor_perfservice` ≠ `vendor_perf_service`，名称可能有细微差异），在对应位置各添加一行：

```cil
; expandtypeattribute 区（文件前段）
(expandtypeattribute (vendor_perf_service_33_0) true)

; typeattribute 区（文件中段）
(typeattribute vendor_perf_service_33_0)

; typeattributeset 区（文件后段）
(typeattributeset vendor_perf_service_33_0 (vendor_perf_service))
```

### 编译范围

只需 `--qssi` → `--super`，vendor 侧无需改动。
