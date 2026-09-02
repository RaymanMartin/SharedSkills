# 新模块集成 SELinux 策略工作流

本文档承接 `SKILL.md` 的分支 B，适用于新增 vendor native daemon、vendor APK、system APK，或 daemon + APK 组合模块。

## 1. 收集模块信息

用 `vscode_askQuestions` 询问：

1. 模块类型：vendor native daemon / vendor APK / system APK / daemon + APK
2. 模块源码或预编译文件所在目录，要求完整路径
3. APK 包名，仅 APK 类必填
4. 签名证书，仅 APK 类必填：platform / testkey / 自定义

收到路径后用 `list_dir` 查看目录结构，确认是否已有 `sepolicy/` 子目录。已有时读取其中 `.te` 和 contexts 文件并在原有基础上追加；没有时创建标准骨架。

生成文件前，高通 Qlog 类案例必须读取：

- `./doc/qlog-example/qlog.mk`
- `./doc/qlog-example/sepolicy/platform-T/qlog.te`
- `./doc/qlog-example/sepolicy/common/file_contexts`

## 2. 策略放置原则

type 定义、allow 规则和上下文文件优先跟模块走，放在模块自己的 `sepolicy/` 目录。只有遇到 neverallow、跨分区可见性或 public type 需求时，才修改平台策略目录。

| 场景 | 优先位置 |
|------|----------|
| 模块自己的 allow 规则 | 模块 `sepolicy/` |
| native daemon 可执行文件标签 | 模块 `sepolicy/common/file_contexts` |
| APK 包名到 domain 映射 | 模块 `sepolicy/common/seapp_contexts` |
| 自定义属性 | 模块 `property.te` + `property_contexts` |
| 触发 neverallow | 平台 `system/sepolicy`，高通需双路径同步 |
| vendor domain 需要访问 system private type | device/qcom 或 sepolicy_vndr，按平台参考判断 |

## 3. 标准目录结构

```text
<module>/
├── <module>.mk
├── <module>.rc
└── sepolicy/
    ├── common/
    │   ├── file_contexts
    │   ├── property_contexts
    │   ├── seapp_contexts
    │   └── service_contexts
    ├── platform-Q/
    ├── platform-R/
    ├── platform-S/
    └── platform-T/
        └── <module>.te
```

Android 13/14 使用 `platform-T`。

## 4. `.mk` 引用方式

vendor 侧模块使用 `BOARD_SEPOLICY_DIRS`：

```makefile
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/common

ifeq (10,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/platform-Q
else ifeq (11,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/platform-R
else ifeq (12,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/platform-S
else ifeq (13,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/platform-T
else ifeq (14,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/<module_path>/sepolicy/platform-T
endif
```

system 或 product 侧 APK 使用：

```makefile
PRODUCT_PRIVATE_SEPOLICY_DIRS += $(LOCAL_PATH)/sepolicy
```

Qlog 旧模板如果没有 Android 14 分支，必须补 `else ifeq (14,$(PLATFORM_VERSION))` 指向 `platform-T`。

## 5. 最小 `.te` 骨架

vendor native daemon：

```te
type <module>, domain;
type <module>_exec, exec_type, vendor_file_type, file_type;
type vendor_<module>_file, file_type, data_file_type, core_data_file_type;
type vendor_<module>_prop, property_type, vendor_property_type, vendor_public_property_type;
type <module>_socket, file_type;

init_daemon_domain(<module>)
```

APK：

```te
type <module>_app, domain;
type <module>_app_data_file, file_type, data_file_type, core_data_file_type, app_data_file_type;

app_domain(<module>_app)
binder_use(<module>_app)
```

daemon + APK 可以写在同一个 `.te` 中，分别定义 daemon domain 和 app domain，并按实际需要添加 `get_prop`、`set_prop`、binder 或 service 权限。

## 6. contexts 模板

`common/file_contexts`：

```text
/vendor/bin/<module>_server           u:object_r:<module>_exec:s0
/data/vendor/<module_data_dir>(/.*)?  u:object_r:vendor_<module>_file:s0
/dev/socket/<module>\.socket         u:object_r:<module>_socket:s0
```

`common/property_contexts`：

```text
vendor.<module>.  u:object_r:vendor_<module>_prop:s0
```

APK 类必须补 `common/seapp_contexts`，并确保规则比 platform_app 通配行更具体：

```text
user=_app seinfo=platform name=<package.name> domain=<module>_app type=<module>_app_data_file levelFrom=user
```

## 7. 编译刷机与补全 allow

1. 按平台编译刷机文档选择编译目标并刷入 `super.img`。
2. 启动后进入 permissive 收集模块相关 denial：

```bash
adb shell setenforce 0
adb logcat -b all -d 2>/dev/null | grep "avc: denied" | grep "<module_domain>"
```

3. 逐条补全 allow 或修复 type/context，可独立管理的规则写回模块 `sepolicy/`。
4. 循环到目标 denial 清零。
5. 读取 `patch-export.md` 导出 patch。
