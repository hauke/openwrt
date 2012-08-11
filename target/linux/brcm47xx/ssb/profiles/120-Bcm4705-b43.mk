#
# Copyright (C) 2007-2012 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Bcm4705-b43
  NAME:=Broadcom BCM4705 SoC, BroadcomWiFi (b43, default)
  PACKAGES:=kmod-b43 kmod-tg3 kmod-ssb-gige
endef

define Profile/Bcm4705-b43/Description
	Package set compatible with hardware using Broadcom BCM4705 SoC
	using the MAC80211 b43 drivers.
endef

$(eval $(call Profile,Bcm4705-b43))

