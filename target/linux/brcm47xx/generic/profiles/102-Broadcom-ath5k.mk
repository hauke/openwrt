#
# Copyright (C) 2006-2008 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

define Profile/Broadcom-ath5k
  NAME:=Broadcom SoC, Atheros WiFi (ath5k)
  PACKAGES:=kmod-ath5k kmod-b44 kmod-tg3 kmod-ssb-gige
endef

define Profile/Broadcom-ath5k/Description
	Package set compatible with hardware using Atheros WiFi cards
endef
$(eval $(call Profile,Broadcom-ath5k))

