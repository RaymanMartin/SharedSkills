# Git history search report

- Repository: `/home/quectel/HardDisk3/sm6115_a14_r01_yd`
- File: `6115_IOT_100004_AP/packages/modules/Wifi/service/java/com/android/server/wifi/WifiServiceImpl.java`
- Keyword: `scan`

## Summary

- Commit message matches: 0
- File diff matches: 1

## Commits with message matching 'scan'

No commits found.

## Commits with file diff matching 'scan'

### Commit `1db805954da45711276a6ada7f7767ef989f54b7`

```text
commit 1db805954da45711276a6ada7f7767ef989f54b7
Author: gavin.liu <gavin.liu@quectel.com>
Date:   2024-11-01 06:22:34 +0000

QSC200UP-BBU:Upload QSC200UP-BBU source code


```

#### File diff

```diff
diff --git a/6115_IOT_100004_AP/packages/modules/Wifi/service/java/com/android/server/wifi/WifiServiceImpl.java b/6115_IOT_100004_AP/packages/modules/Wifi/service/java/com/android/server/wifi/WifiServiceImpl.java
index 6bf4f5bbf1b..2f9fac54dda 100644
--- a/6115_IOT_100004_AP/packages/modules/Wifi/service/java/com/android/server/wifi/WifiServiceImpl.java
+++ b/6115_IOT_100004_AP/packages/modules/Wifi/service/java/com/android/server/wifi/WifiServiceImpl.java
@@ -909,6 +909,13 @@ public class WifiServiceImpl extends BaseWifiService {
                         @Override
                         public void onReceive(Context context, Intent intent) {
                             String action = intent.getAction();
+                            if(isWiFiQualcomm()){
+                                setProperty(RTW_AIRPLANE_MODE_OFF_LOAD, null);
+                                if (mVerboseLoggingEnabled) {
+                                    Log.d(TAG, "rayman-Airplane on-off skip, qualcomm wlan driver");
+                                }
+                                return;
+                            }
                             if (action.equals(Intent.ACTION_AIRPLANE_MODE_CHANGED) && !isWiFiQualcomm()) {
                                 isAirplaneModeOn = intent.getBooleanExtra("state", false);
                                 boolean wifiEnableState = getWifiEnabledState() == WIFI_STATE_ENABLED;
@@ -916,10 +923,7 @@ public class WifiServiceImpl extends BaseWifiService {
                                     Log.d(TAG, "rayman-WiFi6 mode enter airplane on status : " + isAirplaneModeOn + ",--wifiEnableState:" + wifiEnableState);
                                 }
                                 switchWiFi6DriverStatus(!isAirplaneModeOn);
-                                // close airplane mode, reset enable status
-                                if(!isAirplaneModeOn){
-                                    setProperty(RTW_AIRPLANE_MODE_OFF_LOAD, null);
-                                }
+
                                 if (mVerboseLoggingEnabled) {
                                     Log.d(TAG, "rayman-unload WiFi6 driver");
                                 }
```

