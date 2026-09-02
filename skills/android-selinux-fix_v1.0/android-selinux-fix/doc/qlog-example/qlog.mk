QLOG_CONFIG := default_logmask_5G.cfg GNSS_New.cfg
QLOG_BIN := qlog_server
QLOG_APP := QLog_APP
PRODUCT_PACKAGES += $(QLOG_CONFIG) \
                    $(QLOG_BIN) \
                    $(QLOG_APP)
##PLATFORM_VERSION
$(warning ------------------------------------- $(PLATFORM_VERSION) --------------------------)
BOARD_SEPOLICY_DIRS += $(TOP)/vendor/quectel/Qlog/prebuild/android/sepolicy/common
ifeq (10,$(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/vendor/quectel/Qlog/prebuild/android/sepolicy/platform-Q
else ifeq (12, $(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/vendor/quectel/Qlog/prebuild/android/sepolicy/platform-S
else ifeq (11, $(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/vendor/quectel/Qlog/prebuild/android/sepolicy/platform-R
else ifeq (13, $(PLATFORM_VERSION))
BOARD_SEPOLICY_DIRS += $(TOP)/vendor/quectel/Qlog/prebuild/android/sepolicy/platform-T/
endif
