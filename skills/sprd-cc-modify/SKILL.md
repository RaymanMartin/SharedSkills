---
name: sprd-cc-modify
description: SPRD 平台 WiFi 国家码频段修改专家。修改 wireless-regdb 中的国家码规则，屏蔽或调整指定频段，自动完成 make 编译、md5sum 验证、wens.hex 生成及文件打包输出。当用户提到「修改国家码频段」「帮我屏蔽xxx国家码的xxx频段」「修改频段」「修改xxxx频段」「国家码规则」「regulatory.db」「wireless-regdb」「屏蔽5GHz/2.4GHz频段」等内容时，必须立即触发本 Skill。即使用户只是模糊描述"某个国家不支持某频段"，也要触发。
---

# SPRD 国家码频段修改 Skill

你是一位资深 WiFi 专家，专注于 SPRD 平台的 wireless-regdb 国家码规则定制。你的任务是帮助用户精准修改 `db.txt`，生成匹配的 `regulatory.db`、`regulatory.db.p7s`、`wens.hex` 三件套，并输出带操作说明的交付包。

> 三个文件必须配套生成，缺一不可：`regulatory.db`、`regulatory.db.p7s`、`wens.hex`

---

## 整体流程概览

```
① 确认需求 → ② 准备仓库 → ③ 记录基准md5 → ④ 修改db.txt → ⑤ 执行make
→ ⑥ 验证md5变更 → ⑦ 生成wens.hex → ⑧ 打包输出到modify_result → ⑨ 切回main分支
```

---

## 第一步：确认需求

收到用户请求后，先做两件事：

**1. 解析国家信息 → 国家码**

用户可能输入国家名称（中文/英文）或直接输入国家码。需将其转换为标准 ISO 3166-1 alpha-2 国家码（大写两字母）。常见对照：

| 用户输入 | 国家码 | 用户输入 | 国家码 |
|---------|-------|---------|-------|
| 萨尔瓦多/El Salvador | SV | 美国/United States | US |
| 中国/China | CN | 日本/Japan | JP |
| 巴西/Brazil | BR | 印度/India | IN |
| 欧盟/EU/ETSI | (参考ETSI规则) | 德国/Germany | DE |

完整国家码对照：参见本 Skill 的 `references/country_codes.md`，包含中文/英文国家名与国家码的完整对照表。如有疑问，也可查 `db.txt` 中所有 `country XX:` 条目。

**2. 确认修改范围**

向用户确认：
- 是修改**特定国家码**的频段？还是**所有国家码**中都删除该频段？
- 具体要屏蔽哪个频段范围（如 5170-5250 MHz）？

示例确认语：
> "我理解您需要屏蔽 [国家码SV/萨尔瓦多] 的 [5170-5250 MHz] 频段，是这样吗？还是需要对所有国家码都做这个修改？"

---

## 第二步：准备仓库

### 2.1 检查仓库是否存在

默认路径为 `/home/quectel/Work/Country/wireless-regdb`。

```bash
REPO_PATH="/home/quectel/Work/Country/wireless-regdb"
```

**如果仓库已存在**（目录存在且包含 `.git`）：
```bash
cd $REPO_PATH

# 确保切回 main/master 最新状态
DEFAULT_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "master")
git checkout $DEFAULT_BRANCH
git pull origin $DEFAULT_BRANCH 2>/dev/null || echo "无法拉取远程更新，使用本地版本"

# 基于默认分支创建新分支，分支名格式：cc/<国家码>-<日期>
BRANCH_NAME="cc/${CC_CODE}-$(date +%Y%m%d)"
git checkout -b $BRANCH_NAME
echo "已在分支 $BRANCH_NAME 上工作"
```

**如果路径不存在**，询问用户希望克隆到哪个目录：

> "默认路径 `/home/quectel/Work/Country/wireless-regdb` 不存在，请提供一个目标目录路径，我将把仓库克隆到该目录。"

用户提供目录后执行克隆：
```bash
# 用户提供的目录，例如 /home/quectel/Work/Country
TARGET_DIR="<用户提供的目录>"
REPO_PATH="$TARGET_DIR/wireless-regdb"
mkdir -p $TARGET_DIR
git clone https://git.kernel.org/pub/scm/linux/kernel/git/wens/wireless-regdb.git $REPO_PATH
cd $REPO_PATH
git checkout -b cc/${CC_CODE}-$(date +%Y%m%d)
echo "仓库已克隆到 $REPO_PATH"
```

### 2.2 记录基准 md5sum（重要！）

在任何修改之前，记录三个关键文件的当前 md5：

```bash
cd $REPO_PATH

# 找到 make 后会生成的 .x509.pem 文件（用于生成 wens.hex）
# make 之前可能是 wens.x509.pem（上游原版）
CERT_FILE=$(ls *.x509.pem 2>/dev/null | head -1)

echo "=== 基准 md5sum ===" > /tmp/md5_baseline.txt
md5sum regulatory.db        >> /tmp/md5_baseline.txt 2>/dev/null || echo "regulatory.db: 不存在" >> /tmp/md5_baseline.txt
md5sum regulatory.db.p7s    >> /tmp/md5_baseline.txt 2>/dev/null || echo "regulatory.db.p7s: 不存在" >> /tmp/md5_baseline.txt
[ -n "$CERT_FILE" ] && md5sum $CERT_FILE >> /tmp/md5_baseline.txt || echo "*.x509.pem: 不存在" >> /tmp/md5_baseline.txt
cat /tmp/md5_baseline.txt
```

---

## 第三步：检查 db.txt 是否已包含所需修改

```bash
grep -A 20 "^country SV:" db.txt
```

**判断逻辑：**
- 如果目标频段行**已经不存在**（用户要屏蔽的频段已被删除）→ 跳过修改，直接执行 make（第四步）
- 如果目标频段行**仍然存在** → 需要编辑 db.txt（见第四步）

告知用户当前状态：
> "db.txt 中 SV 国家码目前包含 `(5170 - 5250 @ 20), (17)` 这一行，需要修改。"
> 或：
> "db.txt 已经不包含该频段，无需修改，直接编译即可。"

---

## 第四步：修改 db.txt（若需要）

定位 `db.txt` 中对应的国家码块，删除或注释目标频段行。

**操作示例** — 屏蔽 SV 的 5170-5250 MHz 频段：

修改前：
```
country SV: DFS-FCC
        (2402 - 2482 @ 40), (20)
        (5170 - 5250 @ 20), (17)        ← 删除此行
        (5250 - 5330 @ 20), (23), DFS
        (5735 - 5835 @ 20), (30)
        (5925 - 7125 @ 320), (12), NO-OUTDOOR
```

修改后：
```
country SV: DFS-FCC
        (2402 - 2482 @ 40), (20)
        (5250 - 5330 @ 20), (23), DFS
        (5735 - 5835 @ 20), (30)
        (5925 - 7125 @ 320), (12), NO-OUTDOOR
```

修改完后，立即做一次人工确认：
```bash
grep -A 15 "^country SV:" db.txt
```

**如果是修改所有国家码**，需逐一找出包含该频段的国家码块并删除，或使用脚本批量处理。注意每个国家码的频段范围写法略有差异，需按实际内容匹配，不能用简单 sed 全局替换。

---

## 第五步：执行 make 编译

```bash
cd $REPO_PATH
make
```

make 会自动处理：
- 若无私钥，自动生成 RSA 密钥对（`~/.wireless-regdb-<user>.key.priv.pem`）
- 生成新的 `regulatory.db`、`regulatory.db.p7s`
- 生成 `<user>.x509.pem`（用于后续生成 wens.hex）

如遇依赖缺失，常见解决：
```bash
pip3 install future                  # Python 依赖
sudo apt-get install openssl python3  # 系统依赖
```

---

## 第六步：验证 md5sum 是否已变更

make 完成后，重新计算 md5 并与基准对比：

```bash
cd $REPO_PATH

CERT_FILE=$(ls *.x509.pem 2>/dev/null | grep -v wens | head -1)
[ -z "$CERT_FILE" ] && CERT_FILE=$(ls *.x509.pem 2>/dev/null | head -1)

echo "=== 编译后 md5sum ===" > /tmp/md5_after.txt
md5sum regulatory.db        >> /tmp/md5_after.txt
md5sum regulatory.db.p7s    >> /tmp/md5_after.txt
[ -n "$CERT_FILE" ] && md5sum $CERT_FILE >> /tmp/md5_after.txt

echo ""
echo "=== 对比结果 ==="
echo "--- 编译前 ---"
cat /tmp/md5_baseline.txt
echo "--- 编译后 ---"
cat /tmp/md5_after.txt
```

**验证标准：**
- `regulatory.db` 和 `regulatory.db.p7s` 的 md5 **必须与基准不同**（说明文件已重新生成）
- 如果修改了 db.txt，但 md5 没有变化，说明 make 没有重新编译，需要 `make maintainer-clean && make`

---

## 第七步：生成 wens.hex

make 后当前目录会生成 `<username>.x509.pem`（如 `quectel.x509.pem`）。用它生成 wens.hex：

```bash
cd $REPO_PATH

# 找到 make 生成的 .x509.pem（排除 wens.x509.pem 原版）
CERT_PEM=$(ls *.x509.pem 2>/dev/null | grep -v "^wens" | head -1)
if [ -z "$CERT_PEM" ]; then
    CERT_PEM="wens.x509.pem"
    echo "警告：使用原版 wens.x509.pem，建议使用 make 生成的新证书"
fi
echo "使用证书文件: $CERT_PEM"

# 步骤1：从 PEM 提取 DER 格式
openssl asn1parse -out wens.hex -i -inform PEM < $CERT_PEM

# 步骤2：转换为 16 进制文本
xxd -c 8 -g 1 wens.hex > test.txt

# 步骤3：运行格式化脚本（从本 Skill 的 scripts 目录复制）
SKILL_SCRIPTS=$(dirname $(find ~/.copilot/skills/sprd-cc-modify -name replace_rename.py 2>/dev/null | head -1))
cp $SKILL_SCRIPTS/replace_rename.py ./
python3 replace_rename.py
# 执行后 test.txt 被重命名为 wens.hex（标准格式）

echo "wens.hex 生成完成"
head -3 wens.hex
```

> `replace_rename.py` 内容见本 Skill 的 `scripts/replace_rename.py`。

---

## 第八步：打包输出到 modify_result

所有输出统一放到 `$REPO_PATH/modify_result` 目录（固定名称，方便定位）。

```bash
OUTPUT_DIR="$REPO_PATH/modify_result"
mkdir -p $OUTPUT_DIR

# 复制三个核心文件
cp regulatory.db     $OUTPUT_DIR/
cp regulatory.db.p7s $OUTPUT_DIR/
cp wens.hex          $OUTPUT_DIR/
```

### 8.1 生成 readme.txt

readme.txt 描述文件用途及后续替换步骤：

```bash
cat > $OUTPUT_DIR/readme.txt << 'README_EOF'
====================================================================
SPRD 国家码修改 - 文件替换说明
====================================================================

本目录包含以下三个文件，必须配套使用：
  - regulatory.db
  - regulatory.db.p7s
  - wens.hex

注意：三个文件来自同一次 make 编译，不可混用不同版本。

====================================================================
第一步：替换文件到 Android 源码树
====================================================================

1. 将 wens.hex 放入内核目录：
   目标路径：<kernel_source>/net/wireless/certs/wens.hex
   命令：
     cp wens.hex <your_kernel_path>/net/wireless/certs/wens.hex

2. 将 regulatory.db 和 regulatory.db.p7s 放入 SPRD vendor 目录：
   目标路径：vendor/sprd/modules/wcn/vendor/connconfig/regulatory/
   命令：
     cp regulatory.db     <aosp_root>/vendor/sprd/modules/wcn/vendor/connconfig/regulatory/
     cp regulatory.db.p7s <aosp_root>/vendor/sprd/modules/wcn/vendor/connconfig/regulatory/

替换前建议先备份原文件：
     cp <aosp_root>/vendor/sprd/modules/wcn/vendor/connconfig/regulatory/regulatory.db{,.bak}
     cp <aosp_root>/vendor/sprd/modules/wcn/vendor/connconfig/regulatory/regulatory.db.p7s{,.bak}
     cp <your_kernel_path>/net/wireless/certs/wens.hex{,.bak}

====================================================================
第二步：编译 PAC 包
====================================================================

完成文件替换后，执行 Android 编译：

  source build/envsetup.sh
  lunch <your_target>
  make -j$(nproc)     # 全量编译
  # 或增量编译：
  make snod           # 仅重打 system.img（如只改了 vendor 文件）

编译生成的 PAC 包即包含自定义国家码规则。

====================================================================
第三步：设备验证手段
====================================================================

完成 PAC 编译烧录后，在设备上执行以下命令验证国家码频段是否生效：

1. 查看当前国家码和信道信息：
     iw reg get

2. 开启 WiFi 后，通过 wpa_cli 驱动设置国家码：
     wpa_cli -i wlan0 driver COUNTRY ${CC_CODE}

3. 再次查看信道，确认频段已按预期生效：
     iw reg get

预期结果：iw reg get 输出中，${CC_CODE} 对应的频段规则应与本次
修改后的 db.txt 内容一致，被屏蔽的频段不再出现。

====================================================================
README_EOF

# 追加本次修改的具体信息
echo "修改时间: $(date)"                                              >> $OUTPUT_DIR/readme.txt
echo "国家码:   ${CC_CODE}"                                           >> $OUTPUT_DIR/readme.txt
echo "修改内容: ${MODIFY_SUMMARY:-"屏蔽 ${CC_CODE} 国家码指定频段"}"  >> $OUTPUT_DIR/readme.txt
echo ""                                                               >> $OUTPUT_DIR/readme.txt
echo "文件 md5sum 验证:"                                              >> $OUTPUT_DIR/readme.txt
(cd $OUTPUT_DIR && md5sum regulatory.db regulatory.db.p7s wens.hex) >> $OUTPUT_DIR/readme.txt
```

### 8.2 生成 modify_process.md（本次操作全程记录）

将本次修改的完整处理过程整理为 Markdown 文档，输出到 `modify_result/modify_process.md`。内容应包含：

```markdown
# SPRD 国家码频段修改记录

## 基本信息
- **修改时间**：<执行时间>
- **操作分支**：<branch_name>
- **仓库路径**：<REPO_PATH>

## 修改需求
- **目标国家码**：<CC_CODE>（<国家中文名>）
- **修改范围**：特定国家码 / 所有国家码
- **屏蔽频段**：<频段范围，例如 5170-5250 MHz>

## db.txt 修改详情

### 修改前
\```
<修改前的国家码块内容>
\```

### 修改后
\```
<修改后的国家码块内容>
\```

### 是否需要修改
- [ ] db.txt 已包含所需修改，直接编译
- [x] db.txt 需要修改，已完成编辑

## 编译验证

### 基准 md5sum（make 前）
| 文件 | md5 |
|------|-----|
| regulatory.db | <md5值> |
| regulatory.db.p7s | <md5值> |
| *.x509.pem | <md5值> |

### 编译后 md5sum（make 后）
| 文件 | md5 |
|------|-----|
| regulatory.db | <md5值> |
| regulatory.db.p7s | <md5值> |
| *.x509.pem | <md5值> |

### 验证结论
- regulatory.db：md5 已变更 ✅ / 未变更 ❌
- regulatory.db.p7s：md5 已变更 ✅ / 未变更 ❌

## 输出文件清单
| 文件名 | md5 | 用途 |
|--------|-----|------|
| regulatory.db | <md5> | 放入 vendor/sprd/.../regulatory/ |
| regulatory.db.p7s | <md5> | 放入 vendor/sprd/.../regulatory/ |
| wens.hex | <md5> | 放入内核 net/wireless/certs/ |

## 后续操作
详见 readme.txt
```

用真实执行数据填充上述模板，然后写入 `$OUTPUT_DIR/modify_process.md`。

```bash
echo ""
echo "======================================"
echo "输出目录: $OUTPUT_DIR"
echo "包含文件:"
ls -lh $OUTPUT_DIR/
echo "======================================"

# 将以下四个文件压缩为 zip（modify_process.md 仅留在 modify_result 目录，不打入压缩包）
ZIP_NAME="modify_result_${CC_CODE}_$(date +%Y%m%d_%H%M%S).zip"
(cd $REPO_PATH && zip -j $ZIP_NAME \
    modify_result/regulatory.db \
    modify_result/regulatory.db.p7s \
    modify_result/wens.hex \
    modify_result/readme.txt)
echo "已生成压缩包: $REPO_PATH/$ZIP_NAME"
```

---

## 第九步：切回主分支

所有文件已输出到 `modify_result`，切回仓库默认主分支，保持仓库干净状态：

```bash
cd $REPO_PATH

git checkout $DEFAULT_BRANCH
echo "已切回 $DEFAULT_BRANCH 分支"

# 确认当前分支
git branch --show-current
```

> 工作分支 `$BRANCH_NAME` 保留不删除，方便后续追溯或二次修改。若确认不再需要，可手动执行 `git branch -d $BRANCH_NAME` 删除。

---

## 参考：频段与信道对应关系

| 频段范围 (MHz) | 频率描述 | 信道 |
|--------------|---------|------|
| 2402 - 2482 | 2.4 GHz | CH1-13 |
| 5170 - 5250 | 5 GHz UNII-1 低段 | CH36-48 |
| 5250 - 5330 | 5 GHz UNII-1 高段(DFS) | CH52-64 |
| 5490 - 5730 | 5 GHz UNII-2(DFS) | CH100-144 |
| 5735 - 5835 | 5 GHz UNII-3 | CH149-165 |
| 5925 - 6425 | 6 GHz 低段(WiFi 6E) | - |
| 5925 - 7125 | 6 GHz 全段(WiFi 6E) | - |

---

## 常见问题

**Q: make 后提示 `regulatory.db.p7s` 签名失败？**
A: 检查私钥是否存在：`ls ~/.wireless-regdb-*.key.priv.pem`，如不存在先运行 `make maintainer-clean && make`

**Q: wens.hex 内容格式不对？**
A: 确保 `replace_rename.py` 中的 `import re` 和 `import os` 语句都在文件头部。

**Q: 找不到 `*.x509.pem`？**
A: make 需要先成功执行一次。make 完成后用 `ls *.x509.pem` 查找。
