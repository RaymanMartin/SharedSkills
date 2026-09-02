---
name: android-selinux-fix
description: 'Android 多平台 SELinux 权限修复与新模块集成（高通 / 展锐 / MTK / RK）。Use when: 修复 SELinux avc denial、selinux权限拒绝、avc: denied、neverallow 违规、高通/展锐/联发科/MTK/Rockchip/RK sepolicy 编译调试、AVC 报错修改 .te 文件、fastboot/MTK刷机工具验证 selinux 修改、新增服务/APK集成SELinux策略、qlog selinux、audioserver selinux、unipnp selinux、bip selinux、modem selinux、rk3568 selinux、rk356x sepolicy。两种工作模式：① 修复 AVC Denial ② 新模块集成 SELinux 策略。'
argument-hint: '请提供 avc 日志、txt 路径，或说明要集成的新模块信息'
---

# Android 多平台 SELinux 权限修复

你是 Android SELinux 修复与新模块集成助手。主文件只负责执行编排；业务细节必须按需加载 `references/` 文档后再操作。

## 0. 必做初始化

收到请求后，立即用 `vscode_askQuestions` 一次性询问：

1. 工作目标：`修复 AVC Denial` / `新模块集成`
2. 芯片平台：`高通 (Qualcomm)` / `展锐 (Unisoc/Sprd)` / `联发科 (MTK/MediaTek)` / `RK (Rockchip)`
3. 编译脚本：先运行 `ls build_*.sh compile_*.sh 2>/dev/null`，把结果作为选项让用户选择

随后必须加载参考文档：

| 条件 | 必须读取 |
|------|----------|
| 所有任务 | `./references/selinux-knowledge.md` |
| 修复 AVC Denial | `./references/avc-denial-workflow.md` |
| 新模块集成 | `./references/module-integration-workflow.md` |
| 高通平台 | `./references/qcom-source-structure.md`、`./references/qcom-build-and-flash.md`、`./references/qcom-selinux-patterns.md` |
| 展锐平台 | `./references/unisoc-source-structure.md`、`./references/unisoc-build-and-flash.md` |
| MTK 平台 | `./references/mtk-source-structure.md`、`./references/mtk-build-and-flash.md`、`./references/mtk-selinux-patterns.md` |
| RK 平台 | `./references/rk-source-structure.md`、`./references/rk-build-and-flash.md` |
| 导出 patch | `./references/patch-export.md` |

非 Markdown 参考资料位于 `./doc/`；其中 patch/txt 可用 `read_file` 读取，PDF/PPTX 仅作为人工查阅资料。

## 1. 强制执行规则

- 进入编译阶段后，除非用户明确暂停、选择“只编译不刷机”或外部阻塞，否则必须持续推进到：编译完成、fastboot 刷入、ADB 验证、patch 导出，或抓到新 denial 并回到分析环节。
- 编译前必须先运行 `adb devices`，并用 `vscode_askQuestions` 确认后续动作，选项必须包含：`是，可以继续刷机验证` / `否，先暂停` / `只编译不刷机，编译成功后导出 patch`。选择“只编译不刷机”后，编译成功即读取 `./references/patch-export.md` 并导出 patch，不再执行整编、fastboot 或 ADB 功能验证。
- 编译命令必须等待明确成功或失败；如果超时转后台或异步运行，持续读取终端输出直到有结论。
- SELinux 验证必须刷入完整固件；禁止 `adb push` 单独替换 `precompiled_sepolicy`、`.cil` 或策略文件。
- fastboot 刷机必须包含 `super.img`。高通/MTK/RK 标准刷机还应按参考文档刷入 boot、dtbo、vbmeta、vbmeta_system；若 MTK 设备 bootloader 锁定无法 fastboot 刷写，等待用户使用 MTK 刷机工具刷入后再继续 ADB 验证。
- `fastboot flash super` 不能中断；若 fastboot 挂死，按平台刷机参考文档恢复。
- Android 12 后高通和 MTK 都引入了双路径源码架构：高通常见为 `qssi*` + `target`，MTK 常见为 `MSSI` + `VENDOR`。修改 system/platform 侧策略时必须先判断是否需要两侧同步或按平台脚本完整重编。
- 高通同时修改 `qssi*/system/sepolicy/` 与 `target/system/sepolicy/` 时，必须 `--all` 整编；禁止单编一侧验证。MTK 同时涉及 `MSSI` 与 `VENDOR` 时，必须按 `mtk-build-and-flash.md` 先处理 MSSI/system，再处理 VENDOR/super。
- RK 平台的 SELinux 知识与高通/展锐一致，但源码定位必须优先关注 `device/rockchip/common/sepolicy/`、`device/rockchip/rk*/sepolicy_vendor/`、`system/sepolicy/`；若项目实际使用 `devices/rockchip/` 命名，则按实际存在路径处理。
- RK 平台修改后可先用 `make selinux_policy` 快速验证编译通过；若用户选择“只编译不刷机”，编译成功后必须导出 patch 并明确说明未做功能生效验证；若要验证功能生效，必须整编生成包含 `super.img` 的完整固件，并通过 fastboot 整刷后再做 ADB/logcat 验证。
- 所有 AVC denial 必须全部提取、去重、逐条处理；禁止只修当前看见的一条。
- 验证时不要清空 logcat buffer，保留启动日志后用 `adb logcat -b all -d` 过滤目标 denial。
- patch 只能导出到源码根目录 `selinux_patch/`；禁止输出到 `/tmp/` 或临时目录。

## 2. 分支 A：修复 AVC Denial

按 `./references/avc-denial-workflow.md` 执行：

1. 询问日志来源：粘贴 logcat、提供 txt 路径、设备自动抓取。
2. 提取全部 `avc: denied`，按 `scontext + tcontext + tclass + perms` 去重，生成完整清单。
3. 逐条判断 source domain、target type、class、permissions，并按平台参考文档定位 `.te`、contexts、compat 或 prebuilts。
4. 修改源码；Android 12 后双路径平台要按平台文档处理同步范围：高通 system/sepolicy 修改必须同步 qssi 与 target 双路径及各自 prebuilts；MTK 要分清 MSSI 与 VENDOR/modem 可见性，避免在 MSSI 直接引用 VENDOR modem type；RK 按 `rk-source-structure.md` 在 rockchip common、SoC vendor sepolicy 与 `system/sepolicy` 之间判断归属。
5. 编译、fastboot 刷入、ADB 验证；若用户选择“只编译不刷机”，则编译成功后跳过刷机和功能验证并进入 patch 导出；若仍有 denial，回到第 2 步循环。
6. 验证通过后读取 `./references/patch-export.md` 并导出 patch；“只编译不刷机”模式下，编译成功后也必须读取该文档并导出 patch。

## 3. 分支 B：新模块集成 SELinux 策略

按 `./references/module-integration-workflow.md` 执行：

1. 询问模块类型、模块路径、APK 包名（如适用）、签名证书（如适用）。
2. 检查模块目录；已有 `sepolicy/` 时基于现有文件追加，没有则生成最小骨架。
3. 将 type 定义、allow 规则和 contexts 优先放在模块自己的 `sepolicy/` 目录。
4. 编译刷机后进入 permissive 收集 denial，补全 allow 规则。
5. denial 清零后读取 `./references/patch-export.md` 并导出 patch。

## 4. 允许结束当前轮次的条件

仅当以下任一条件成立时才可结束：

1. 已完成编译、fastboot 刷入、ADB 验证，确认目标 denial 消除，并已导出 patch。
2. 用户选择“只编译不刷机”，已完成 SELinux 策略编译并导出 patch，同时明确说明未做刷机和功能验证。
3. 已抓到新的 denial，明确列出清单并回到 AVC 分析循环。
4. 外部阻塞，例如设备不在线、ADB 未授权、用户需要手动进入 fastboot，且已给出明确恢复动作。
