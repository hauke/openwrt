#
# Copyright (C) 2015 OpenWrt.org
# Copyright (C) 2016 LEDE project
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#
include $(TOPDIR)/rules.mk

PKG_NAME:=make-ext4fs

PKG_SOURCE_URL=$(PROJECT_GIT)/project/make_ext4fs.git
PKG_MIRROR_HASH:=370cccaf7b42c07adb3abe090dcdf143f9e21d04cf9fb6dda858102df8f21f8a
PKG_SOURCE_PROTO:=git
PKG_SOURCE_DATE:=2020-01-05
PKG_SOURCE_VERSION:=5c201be7d72aff735da27e17c29852e0cefe3e52

include $(INCLUDE_DIR)/host-build.mk

define Host/Install
	$(INSTALL_BIN) $(HOST_BUILD_DIR)/make_ext4fs $(STAGING_DIR_HOST)/bin/
endef

define Host/Clean
	rm -f $(STAGING_DIR_HOST)/bin/make_ext4fs
endef

$(eval $(call HostBuild))
