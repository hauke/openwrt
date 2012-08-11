#
# Copyright (C) 2007-2010 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Broadcom-brcmsmac
  NAME:=Broadcom SoC, Broadcom WiFi (brcmsmac)
  PACKAGES:=kmod-brcmsmac
endef

define Profile/Broadcom-brcmsmac/Description
	Package set compatible with hardware using Broadcom BCM43xx cards
	using the MAC80211 brcmsmac drivers.
endef

$(eval $(call Profile,Broadcom-brcmsmac))

