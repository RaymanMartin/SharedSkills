# SELinux Patch 导出规范

验证通过后必须将 SELinux 相关修改导出到源码根目录 `selinux_patch/`。如果用户选择“只编译不刷机”，则 SELinux 策略编译成功后也必须导出 patch。禁止导出到 `/tmp/` 或其他临时目录。

## 1. 导出原则

- 禁止使用整仓库 diff，例如 `git -C qssi14 diff`。
- 必须限定 SELinux 子目录，避免混入无关修改。
- 高通 QSSI/Target 目录命名不固定，导出前自动识别。
- 高通、展锐、MTK、RK 都支持“只编译不刷机后导出 patch”；该模式导出的 patch 只能代表编译通过，不能代表设备功能验证通过。
- patch 文件为空时也要报告该侧无 SELinux 修改。

高通关注目录：

| 侧别 | 子目录 |
|------|--------|
| QSSI | `system/sepolicy/`、`device/qcom/sepolicy/` |
| Target | `system/sepolicy/`、`device/qcom/sepolicy/`、`device/qcom/sepolicy_vndr/` |

## 2. 高通导出命令

在源码根目录执行：

```bash
PROJECT_ROOT=$(pwd)
PATCH_DIR="$PROJECT_ROOT/selinux_patch"
mkdir -p "$PATCH_DIR"
DATE=$(date +%Y%m%d)

QSSI_DIR=$(find "$PROJECT_ROOT" -maxdepth 1 -type d \( -iname "qssi*" \) | sort | head -1)
TARGET_DIR=$(find "$PROJECT_ROOT" -maxdepth 1 -type d \( -iname "target*" -o -iname "UM*" \) | sort | head -1)

echo "QSSI  目录: $QSSI_DIR"
echo "Target目录: $TARGET_DIR"

QSSI_NAME=$(basename "$QSSI_DIR")
{
  # 1) tracked 文件的修改
  for SUBDIR in system/sepolicy device/qcom/sepolicy; do
    DIFF=$(git -C "$QSSI_DIR" diff -- "$SUBDIR" 2>/dev/null)
    if [ -n "$DIFF" ]; then
      echo "# === $QSSI_NAME/$SUBDIR (tracked changes) ==="
      echo "$DIFF"
    fi
  done

  # 2) untracked 新增文件（从项目根目录执行，路径带 qssi 前缀）
  NEW_FILES=$(git -C "$QSSI_DIR" ls-files --others --exclude-standard -- \
    system/sepolicy device/qcom/sepolicy 2>/dev/null)
  if [ -n "$NEW_FILES" ]; then
    echo ""
    echo "# === $QSSI_NAME (new files) ==="
    while IFS= read -r f; do
      git diff --no-index /dev/null "$QSSI_NAME/$f" 2>/dev/null || true
    done <<< "$NEW_FILES"
  fi
} > "$PATCH_DIR/selinux_fix_qssi_${DATE}.diff"

TARGET_NAME=$(basename "$TARGET_DIR")
{
  # 1) tracked 文件的修改（git diff 可直接捕获）
  for SUBDIR in system/sepolicy device/qcom/sepolicy device/qcom/sepolicy_vndr; do
    DIFF=$(git -C "$TARGET_DIR" diff -- "$SUBDIR" 2>/dev/null)
    if [ -n "$DIFF" ]; then
      echo "# === $TARGET_NAME/$SUBDIR (tracked changes) ==="
      echo "$DIFF"
    fi
  done

  # 2) untracked 新增文件（git diff 不包含，需用 --no-index 从项目根生成）
  #    从项目根目录执行，保证路径带 target/ 前缀
  NEW_FILES=$(git -C "$TARGET_DIR" ls-files --others --exclude-standard -- \
    system/sepolicy device/qcom/sepolicy device/qcom/sepolicy_vndr 2>/dev/null)
  if [ -n "$NEW_FILES" ]; then
    echo ""
    echo "# === $TARGET_NAME (new files) ==="
    while IFS= read -r f; do
      git diff --no-index /dev/null "$TARGET_NAME/$f" 2>/dev/null || true
    done <<< "$NEW_FILES"
  fi
} > "$PATCH_DIR/selinux_fix_target_${DATE}.diff"

for F in "$PATCH_DIR/selinux_fix_qssi_${DATE}.diff" "$PATCH_DIR/selinux_fix_target_${DATE}.diff"; do
  if [ -s "$F" ]; then
    echo "selinux_patch/$(basename "$F") ($(wc -l < "$F") 行)"
  else
    echo "selinux_patch/$(basename "$F") 为空，该侧无 SELinux 修改"
  fi
done
```

## 3. 展锐导出建议

展锐为单仓结构，限定 `device/sprd/mpool/` 相关路径导出：

```bash
PROJECT_ROOT=$(pwd)
PATCH_DIR="$PROJECT_ROOT/selinux_patch"
mkdir -p "$PATCH_DIR"
DATE=$(date +%Y%m%d)

git diff -- device/sprd/mpool/sepolicy device/sprd/mpool/module > "$PATCH_DIR/selinux_fix_unisoc_${DATE}.diff"

if [ -s "$PATCH_DIR/selinux_fix_unisoc_${DATE}.diff" ]; then
  echo "selinux_patch/selinux_fix_unisoc_${DATE}.diff ($(wc -l < "$PATCH_DIR/selinux_fix_unisoc_${DATE}.diff") 行)"
else
  echo "selinux_patch/selinux_fix_unisoc_${DATE}.diff 为空，无 SELinux 修改"
fi
```

## 4. MTK 导出建议

MTK 需要根据项目实际 MSSI/VENDOR 目录导出，限定 SELinux 相关目录，避免混入镜像、out 或无关源码。

```bash
PROJECT_ROOT=$(pwd)
PATCH_DIR="$PROJECT_ROOT/selinux_patch"
mkdir -p "$PATCH_DIR"
DATE=$(date +%Y%m%d)

PATCH_FILE="$PATCH_DIR/selinux_fix_mtk_${DATE}.diff"

git diff -- \
  MSSI/system/sepolicy \
  MSSI/device/mediatek \
  VENDOR/device/mediatek \
  VENDOR/vendor/mediatek/proprietary/modem \
  > "$PATCH_FILE"

if [ -s "$PATCH_FILE" ]; then
  echo "selinux_patch/selinux_fix_mtk_${DATE}.diff ($(wc -l < "$PATCH_FILE") 行)"
else
  echo "selinux_patch/selinux_fix_mtk_${DATE}.diff 为空，无 SELinux 修改"
fi
```

如项目没有 `MSSI/` 或 `VENDOR/` 顶层目录，按实际源码路径替换，但仍只允许包含 SELinux 策略相关目录。

## 5. RK 导出建议

RK 为单 Android 源码树，限定 Rockchip 和 AOSP SELinux 相关目录导出。只编译不刷机模式下，`make selinux_policy` 成功后也必须执行本导出流程。

```bash
PROJECT_ROOT=$(pwd)
PATCH_DIR="$PROJECT_ROOT/selinux_patch"
mkdir -p "$PATCH_DIR"
DATE=$(date +%Y%m%d)

PATCH_FILE="$PATCH_DIR/selinux_fix_rk_${DATE}.diff"

git diff -- \
  device/rockchip/common/sepolicy \
  device/rockchip/rk*/sepolicy \
  device/rockchip/rk*/sepolicy_vendor \
  system/sepolicy \
  > "$PATCH_FILE"

if [ -s "$PATCH_FILE" ]; then
  echo "selinux_patch/selinux_fix_rk_${DATE}.diff ($(wc -l < "$PATCH_FILE") 行)"
else
  echo "selinux_patch/selinux_fix_rk_${DATE}.diff 为空，无 SELinux 修改"
fi
```

如工程实际使用 `devices/rockchip/`，将上述 `device/rockchip/...` 替换为实际存在路径。

## 6. 汇报格式

导出后向用户报告：

```text
QSSI 目录: <path>
Target目录: <path>
selinux_patch/selinux_fix_qssi_<date>.diff (<lines> 行)
selinux_patch/selinux_fix_target_<date>.diff (<lines> 行)
```

RK 示例：

```text
selinux_patch/selinux_fix_rk_<date>.diff (<lines> 行)
```

MTK 示例：

```text
selinux_patch/selinux_fix_mtk_<date>.diff (<lines> 行)
```
