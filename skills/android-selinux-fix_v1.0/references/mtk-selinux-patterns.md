# MTK Android 13 SELinux 修改规律（从 MT8766 实战提炼）

## 最重要规则：先分清 MSSI 与 VENDOR/modem 可见性

MTK 从 Android 12 后导入类似高通 QSSI/target 的双路径源码架构，项目可能存在 `MSSI/` 与 `VENDOR/`：

- `MSSI/`：platform/system 侧策略。
- `VENDOR/`：vendor/device/modem 侧策略。
- modem 独立策略可能通过 `MTK_MODEM_APPS_SEPOLICY_DIRS` 等变量被加入构建。

不要在 `MSSI/system/sepolicy` 中直接引用只定义在 VENDOR modem sepolicy 的类型。例如 `bip` 定义在：

```text
VENDOR/vendor/mediatek/proprietary/modem/mt8766_32/sepolicy/s0/bip.te
```

若在 MSSI platform `domain.te` 的 neverallow 中写 `-bip`，会触发：

```text
unknown type bip
```

正确做法是回到 VENDOR/modem 策略处理该 domain，或调整 target type/property 的归属与可见性。

---

## 1. init 创建 modem socket 落到 socket_device

典型 AVC：

```text
avc: denied { create } for comm="init" name="bip_socket"
scontext=u:r:init:s0 tcontext=u:object_r:socket_device:s0 tclass=sock_file permissive=0
```

含义：init 创建 `/dev/socket/bip_socket` 时没有匹配到专用 file_contexts，默认落到 `socket_device`。

错误方向：

```te
allow init socket_device:sock_file create;
```

这会扩大 init 对通用 socket device 的权限，不推荐。

正确方向：给具体 socket 定义/使用专用 type，并让 init rc 显式标注 seclabel。

```text
# file.te
type bip_socket, file_type;

# file_contexts
/dev/socket/bip_socket(/.*)? u:object_r:bip_socket:s0

# init.bip.rc
service vendor.bip /vendor/bin/bip
    socket bip_socket stream 660 root system u:object_r:bip_socket:s0
```

再按 AVC 补 init 对专用 socket type 的权限：

```te
allow init bip_socket:sock_file create_file_perms;
```

---

## 2. socket_file 权限修复后出现 unix_stream_socket / unix_dgram_socket

第一轮修复 socket label 后，AVC 可能从 `socket_device:sock_file create` 变成更精确的 socket class：

```text
avc: denied { create } for comm="init"
scontext=u:r:init:s0 tcontext=u:object_r:bip_socket:s0 tclass=unix_stream_socket permissive=0

avc: denied { create } for comm="init"
scontext=u:r:init:s0 tcontext=u:object_r:bip_socket:s0 tclass=unix_dgram_socket permissive=0
```

继续在同一 modem domain 策略中补最小权限：

```te
allow init bip_socket:unix_stream_socket create;
allow init bip_socket:unix_dgram_socket create;
```

若下一轮继续出现：

```text
avc: denied { bind } for comm="init"
scontext=u:r:init:s0 tcontext=u:object_r:bip_socket:s0 tclass=unix_stream_socket permissive=0
```

补：

```te
allow init bip_socket:unix_stream_socket bind;
```

> 经验判断：这种“旧 denial 变为更具体的新 tclass/perms”通常说明上一轮标签修复已经生效，不是倒退。继续按新 AVC 最小补规则即可。

---

## 3. modem domain 访问 net_dns_prop 等 platform property

典型 AVC：

```text
avc: denied { read } for comm="bip"
scontext=u:r:bip:s0 tcontext=u:object_r:net_dns_prop:s0 tclass=file permissive=0
```

直觉上可能想写：

```te
get_prop(bip, net_dns_prop)
```

但 `net_dns_prop` 属于 platform/system property，vendor/modem domain 直接读取可能触发 platform neverallow 或跨分区可见性问题。

MT8766 实战中的处理方式：

```te
#get_prop(bip, net_radio_prop)
dontaudit bip net_dns_prop:file read;
```

适用条件：

- 日志来自无害探测或库默认读取。
- 业务不依赖该 property 的真实读取结果。
- 直接 allow 会违反 neverallow 或跨 platform/vendor 策略边界。

不适用条件：

- 服务功能必须读取该 property。
- property 应归属 vendor，却被错误打成 platform property。

此时应重新评估 property_contexts/type 定义，而不是简单 `dontaudit`。

---

## 4. vendor/modem property 推荐用 set_prop/get_prop 宏

对于明确属于 vendor 的 MTK/RIL 属性，优先使用宏：

```te
set_prop(bip, vendor_mtk_ril_mux_report_case_prop)
set_prop(bip, vendor_mtk_ctl_muxreport-daemon_prop)
```

宏比手写 `property_service set` 更完整，通常同时处理 property socket/file 访问所需权限。

定位属性 type：

```bash
grep -rn "vendor.ril.mux.report.case\|vendor.mtk" VENDOR/vendor/mediatek VENDOR/device/mediatek 2>/dev/null
```

---

## 5. init rc socket 名称与 file_contexts 必须一致

检查三处是否对齐：

```text
init_rc/s0/init.<service>.rc      socket <name> ... u:object_r:<socket_type>:s0
sepolicy/s0/file_contexts        /dev/socket/<name> u:object_r:<socket_type>:s0
sepolicy/s0/file.te              type <socket_type>, file_type;
```

MT8766 bip 示例中同时存在：

```text
/dev/socket/bip_socket(/.*)?       u:object_r:bip_socket:s0
/dev/socket/bip(/.*)?              u:object_r:bip_socket:s0
/dev/socket/vendor\.bip(/.*)?      u:object_r:vendor_bip_socket:s0
```

如果 rc 中创建的是 `socket bip_socket ...`，但 file_contexts 只配置了 `/dev/socket/bip`，就会漏标，导致落到 `socket_device`。

---

## 6. 验证命令可能制造 shell denial

用 shell 检查标签时：

```bash
adb shell ls -Z /dev/socket/bip_socket /dev/socket/vendor.bip
```

可能出现：

```text
avc: denied { getattr } for comm="ls"
scontext=u:r:shell:s0 tcontext=u:object_r:vendor_bip_socket:s0 tclass=sock_file permissive=0
```

这通常是验证命令自身触发的 `shell` denial，不是业务服务运行所需权限。除非用户明确要修 adb shell 调试访问，否则不要为了它给 `shell` 放开 vendor socket。

---

## 7. MTK AVC 修复循环建议

每轮验证都按四元组去重：

```text
scontext + tcontext + tclass + perms
```

针对目标模块再过滤：

```bash
adb logcat -b all -d 2>/dev/null | grep "avc: denied" | grep -E "bip|bip_socket|socket_device|net_dns_prop"
```

判断优先级：

1. 目标服务是否启动：`adb shell ps -AZ | grep <domain>`。
2. 目标 socket/property denial 是否消失。
3. 是否出现同一目标 type 的新 class/perms。
4. 是否存在由验证命令触发的 shell denial。
5. 不相关系统 AVC 只记录，不扩大本次修复范围。

---

## 8. MT8766 bip 实战最终规则形态示例

```te
type bip, domain, mtkimsmddomain, netdomain;
type bip_exec, exec_type, file_type, vendor_file_type;

init_daemon_domain(bip)
net_domain(bip)

allow bip bip_socket:sock_file write;
allow bip vendor_bip_socket:sock_file write;

allow init bip_socket:sock_file create_file_perms;
allow init bip_socket:unix_stream_socket create;
allow init bip_socket:unix_stream_socket bind;
allow init bip_socket:unix_dgram_socket create;

dontaudit bip net_dns_prop:file read;
set_prop(bip, vendor_mtk_ril_mux_report_case_prop)
set_prop(bip, vendor_mtk_ctl_muxreport-daemon_prop)
```

对应 `init.bip.rc`：

```rc
service vendor.bip /vendor/bin/bip
    class core
    socket vendor.bip stream 660 root system
    socket bip_socket stream 660 root system u:object_r:bip_socket:s0
    user root
    group system log inet radio net_admin root
    oneshot
    disabled
```

对应 `file_contexts`：

```text
/dev/socket/bip_socket(/.*)? u:object_r:bip_socket:s0
/dev/socket/bip(/.*)? u:object_r:bip_socket:s0
/dev/socket/vendor\.bip(/.*)? u:object_r:vendor_bip_socket:s0
```

> 示例仅说明模式。实际修复时仍以当前 AVC、已有 type、neverallow 和业务需求为准，不要机械复制整段规则。
