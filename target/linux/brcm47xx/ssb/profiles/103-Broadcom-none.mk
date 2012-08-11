#
# Copyright (C) 2006-2008 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Broadcom-none
  NAME:=Broadcom SoC, no Wifi
  PACKAGES:=-wpad-mini kmod-b44
endef

define Profile/Broadcom-none/Description
	Package set without WiFi support
endef
$(eval $(call Profile,Broadcom-none))

