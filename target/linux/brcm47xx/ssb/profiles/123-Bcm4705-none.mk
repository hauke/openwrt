#
# Copyright (C) 2007-2012 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Bcm4705-none
  NAME:=Broadcom BCM4705 SoC, no Wifi
  PACKAGES:=-wpad-mini kmod-tg3 kmod-ssb-gige
endef

define Profile/Bcm4705-none/Description
	Package set compatible with hardware using Broadcom BCM4705 SoC
	and no wifi.
endef

$(eval $(call Profile,Bcm4705-none))

