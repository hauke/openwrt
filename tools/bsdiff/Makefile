# 
# Copyright (C) 2016 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=bsdiff
PKG_VERSION:=4.3

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=http://www.daemonology.net/bsdiff/
PKG_MD5SUM:=e6d812394f0e0ecc8d5df255aa1db22a

HOST_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/host-build.mk

define Host/Compile
	$(HOSTCC) $(HOST_CFLAGS) $(HOST_LDFLAGS) \
		-o $(HOST_BUILD_DIR)/bsdiff \
		$(HOST_BUILD_DIR)/bsdiff.c -lbz2
endef

define Host/Install
	$(INSTALL_BIN) $(HOST_BUILD_DIR)/bsdiff $(STAGING_DIR_HOST)/bin/
endef

define Host/Clean
	rm -f $(STAGING_DIR_HOST)/bin/bsdiff
endef

$(eval $(call HostBuild))
