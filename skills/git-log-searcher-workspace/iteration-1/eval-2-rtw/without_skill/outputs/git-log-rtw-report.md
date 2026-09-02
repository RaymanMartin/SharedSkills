# Git Log 检索报告

- 仓库: `/home/quectel/HardDisk3/sm6115_a14_r01_yd`
- 文件: `6115_IOT_100004_vendor/kernel_platform/msm-kernel/drivers/net/wireless/rtl8852bs/core/rtw_ieee80211.c`
- 关键字: `rtw`

## 检索命令

```bash
git --no-pager log --follow -i --grep='rtw' --date=iso --pretty=format:'%H%nAuthor: %an <%ae>%nDate: %ad%nSubject: %s%n' -- 6115_IOT_100004_vendor/kernel_platform/msm-kernel/drivers/net/wireless/rtl8852bs/core/rtw_ieee80211.c
```

## 命中数量

1

## 命中提交

```text
60a2e7e8420383e1e2d478cf81e3129cf31d981d
Author: Elvins.Fu <elvins.fu@quectel.com>
Date: 2025-01-14 02:35:48 +0000
Subject: SC200UP-BBU_YD:yungui.dong:rtw wifi 更新wifi 驱动解决wpa3 连接异常
```
