#
# Copyright (C) 2006-2012 OpenWrt.org
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.
#

include $(TOPDIR)/rules.mk

PKG_NAME:=test
PKG_VERSION:=0.1
PKG_RELEASE:=5

include $(INCLUDE_DIR)/package.mk

define Package/test
  SECTION:=libs
  CATEGORY:=Libraries
  TITLE:=My Test application
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/* $(PKG_BUILD_DIR)/
endef

define Package/test/install
	$(INSTALL_DIR) $(1)/usr/bin
	$(CP) $(PKG_BUILD_DIR)/test $(1)/usr/bin/my-test
endef

$(eval $(call BuildPackage,test))

