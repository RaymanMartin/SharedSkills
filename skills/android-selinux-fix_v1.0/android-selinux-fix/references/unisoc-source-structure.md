# 展锐 (Unisoc) 源码目录结构

## 整体特点

展锐方案是**单仓结构**，所有客制化 SELinux 策略集中在 `device/sprd/mpool/` 下，无高通双仓（qssi + target）概念。

---

## 主要策略路径

| 分区 | 路径 | 说明 |
|------|------|------|
| system / system_ext | `device/sprd/mpool/sepolicy/system/private/` | system_ext 私有策略 |
| system / system_ext | `device/sprd/mpool/sepolicy/system/public/` | system_ext 公有策略（vendor 可见） |
| vendor | `device/sprd/mpool/sepolicy/vendor/` | vendor 策略（**最常修改**） |
| 模块独立策略 | `device/sprd/mpool/module/<partition>/<module>/msepolicy/` | 各功能模块独立维护策略 |

> ⚠️ 所有客制化策略统一放在 `device/sprd/mpool/`，**不在** `yt_custom/` 下

---

## 目录树结构

```
device/sprd/mpool/
├── sepolicy/
│   ├── vendor/                       ← vendor 策略（最常改）
│   │   ├── *.te                      ← allow 规则（按 domain 命名）
│   │   ├── file_contexts             ← 磁盘文件安全上下文
│   │   ├── genfs_contexts            ← 虚拟文件系统（proc/sysfs）安全上下文
│   │   ├── property_contexts         ← vendor 属性安全上下文
│   │   ├── property.te               ← vendor 属性 type 定义
│   │   ├── service_contexts          ← 服务安全上下文
│   │   └── hwservice_contexts        ← HW 服务安全上下文
│   └── system/
│       ├── private/                  ← system_ext private（vendor 不可见）
│       │   ├── *.te
│       │   ├── file_contexts
│       │   ├── property_contexts
│       │   └── service_contexts
│       └── public/                   ← system_ext public（vendor 可见）
│           ├── *.te
│           ├── property_contexts
│           └── property.te
└── module/
    ├── vendor/<module>/msepolicy/    ← vendor 侧模块独立策略
    │   ├── vendor/                   ← 模块 vendor 策略
    └── system_ext/<module>/msepolicy/← system_ext 侧模块独立策略
        ├── system/
        │   ├── public/               ← 模块公有 type 定义
        │   │   └── property.te
        │   └── private/              ← 模块 allow 规则
        │       ├── *.te
        │       └── property_contexts
```

---

## 源码定位方法

```bash
# 找 source_domain 的 .te 文件（主策略 + 所有模块）
find device/sprd/mpool -name "<domain>.te" 2>/dev/null

# 找 target_type 的定义位置
grep -rn "type <target_type>" device/sprd/mpool/ 2>/dev/null

# 找已有的 allow 规则
grep -rn "allow <source_domain>" device/sprd/mpool/ 2>/dev/null

# 找属性上下文配置
grep -rn "<type_name>" device/sprd/mpool/sepolicy/vendor/property_contexts
grep -rn "<type_name>" device/sprd/mpool/sepolicy/vendor/genfs_contexts

# 查看某模块 msepolicy 目录内容
ls device/sprd/mpool/module/system_ext/<module>/msepolicy/system/private/
```

---

## 判断改哪个目录

| source_domain 类型 | 修改位置 |
|-------------------|---------|
| vendor 进程 | `device/sprd/mpool/sepolicy/vendor/<domain>.te` |
| vendor 模块进程 | `device/sprd/mpool/module/vendor/<module>/msepolicy/vendor/` |
| system_ext 进程 | `device/sprd/mpool/sepolicy/system/private/<domain>.te` |
| platform_app / mediaprovider_app / system_app 等 AOSP app 域 | `device/sprd/mpool/sepolicy/system/private/unisoc.te`（集中 allow 规则文件） |
| priv_app / untrusted_app | 各 module 的 `msepolicy/system/private/<domain>.te` |
| 访问的 type 定义在某模块 | 对应模块 `msepolicy/system/private/<domain>.te` |

> ⚠️ `unisoc.te` 是展锐在 `system/private/` 下维护的集中 allow 规则文件，适合为 AOSP 原生 app 域（platform_app、mediaprovider_app、system_app 等）补充权限，不要修改 AOSP 原生的 `platform_app.te`。

---

## service_manager 访问规则位置

service 类型的可见性决定 allow 规则写在哪里：

| target service 类型来源 | source domain 是否 vendor | allow 规则写在 |
|------------------------|--------------------------|--------------|
| system_ext public（`sepolicy/system/public/service.te`） | 否（system app） | `sepolicy/system/private/unisoc.te` |
| AOSP public（`system/sepolicy/public/service.te`） | 是（vendor app） | `module/vendor/<module>/msepolicy/vendor/<app>.te` |
| system_ext private（`sepolicy/system/private/service.te`） | 否 | `sepolicy/system/private/unisoc.te` |

**确认 service type 来源：**
```bash
# 在展锐主策略目录找
grep -rn "type <service_type>" device/sprd/mpool/sepolicy/ 2>/dev/null
# 在 AOSP 主目录找（system_ext public 或 AOSP public）
grep -rn "type <service_type>" system/sepolicy/ 2>/dev/null
```

**已验证案例：**
- `mediaprovider_app → ssense_service` (system_ext public) → `system/private/unisoc.te`：
  ```te
  allow mediaprovider_app ssense_service:service_manager { find };
  ```
- `sprd_logmanager_app → content_capture_service` (AOSP system/sepolicy/public) → 模块 vendor .te：
  ```te
  allow sprd_logmanager_app content_capture_service:service_manager { find };
  ```

---

## 属性 (property) 规则位置

展锐 property 分两类，位置不同：

| property 类型 | type 定义位置 | allow 规则位置 |
|-------------|-------------|--------------|
| vendor property | `sepolicy/vendor/property.te` | `sepolicy/vendor/<domain>.te` |
| system_ext property（模块定义） | `module/system_ext/<module>/msepolicy/system/public/property.te` | `sepolicy/system/private/unisoc.te` |

**读取 property 推荐用宏：**
```te
get_prop(<domain>, <prop_type>);      # 读取属性
set_prop(<domain>, <prop_type>);      # 设置属性（同时含读权限）
```

`get_prop` 宏展开等价于：
```te
allow <domain> <prop_type>:file { read getattr map open };
allow <domain> <prop_type>:property_service { read };
```

**已验证案例：**
- `platform_app` / `system_app` 读取 `unipnp_prop`（定义在 `module/system_ext/unipnp/msepolicy/system/public/property.te`）：
  ```te
  # 在 system/private/unisoc.te 添加
  get_prop(platform_app, unipnp_prop);
  get_prop(system_app, unipnp_prop);    # 如 com.android.settings 也需要时
  ```

> ⚠️ 注意：同一属性可能被多个 app 域访问（如 platform_app 和 system_app 都访问 unipnp_prop），在 logcat 中表现为不同 scontext，需逐一添加。

---

## sysfs 类型 dir/file 权限

当 vendor 进程访问 sysfs 目录时，**dir `search` 和 file `open/read/write` 是分离的两条 deny**：

```bash
# 典型的两条 denial：
avc: denied { search } for scontext=u:r:hal_light_default:s0 tcontext=u:object_r:sysfs_wcn:s0 tclass=dir
avc: denied { open write } for scontext=u:r:hal_light_default:s0 tcontext=u:object_r:sysfs_wcn:s0 tclass=file
```

两条需要分别授权，即使在同一个 .te 文件中：
```te
allow hal_light_default sysfs_wcn:dir { search };
allow hal_light_default sysfs_wcn:file { open write };
```

> ⚠️ 只修复 file 权限而忘了 dir search 会导致仍有 denial，反之亦然。

---

## 与高通平台关键区别

| 项目 | 高通 | 展锐 |
|------|------|------|
| 仓库结构 | qssi14/ + target/ 双仓 | 单仓 |
| 策略主路径 | `device/qcom/sepolicy/` | `device/sprd/mpool/sepolicy/` |
| 模块策略 | `sepolicy_vndr/` 分散 | `module/*/msepolicy/` 集中管理 |
| 版本化属性 compat | compat/33.0/33.0.cil | **无此概念** |
| vendor type 命名 | 必须 `vendor_` 前缀 | 无强制前缀要求 |
| 快速验证命令 | `make selinux_policy` | **无**，必须整编 system 或 vendor |
