#
# Copyright (C) 2010 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Bcm4705-wl
  NAME:=Broadcom BCM4705 SoC, Broadcom WiFi (wl, proprietary)
  PACKAGES:=-wpad-mini kmod-brcm-wl wlc nas kmod-tg3 kmod-ssb-gige
endef

define Profile/Bcm4705-wl/Description
	Package set compatible with hardware using Broadcom BCM4705 SoC
	using the proprietary broadcom wireless "wl" driver.
endef

$(eval $(call Profile,Bcm4705-wl))

