# 
# Copyright (C) 2016 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=bzip2
PKG_VERSION:=1.0.6

PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=http://www.bzip.org/1.0.6/
PKG_MD5SUM:=e6d812394f0e0ecc8d5df255aa1db22a

HOST_BUILD_PARALLEL:=1

include $(INCLUDE_DIR)/host-build.mk

HOST_MAKE_FLAGS:= $(HOST_CONFIGURE_VARS) libbz2.a

define Host/Install
	$(INSTALL_DATA) $(HOST_BUILD_DIR)/bzlib.h $(STAGING_DIR_HOST)/include/
	$(INSTALL_BIN) $(HOST_BUILD_DIR)/libbz2.* $(STAGING_DIR_HOST)/lib/
endef

define Host/Clean
	rm -f $(STAGING_DIR_HOST)/include/bzlib.h
	rm -f $(STAGING_DIR_HOST)/libbz2.*
endef

$(eval $(call HostBuild))
