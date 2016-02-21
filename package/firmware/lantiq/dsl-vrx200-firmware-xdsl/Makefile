# Copyright (C) 2015 OpenWrt.org
# Copyright (C) 2015 Lantiq Beteiligungs GmbH & Co KG.
#
# This is free software, licensed under the GNU General Public License v2.
# See /LICENSE for more information.

include $(TOPDIR)/rules.mk

PKG_NAME:=dsl_vr9_firmware_xdsl
PKG_VERSION:=05.07.04.03.00.06_05.07.01.08.00.01_osc
PKG_RELEASE:=1
PKG_SOURCE:=$(PKG_NAME)-$(PKG_VERSION).tar.gz
PKG_SOURCE_URL:=http://mirror2.openwrt.org/sources
PKG_MD5SUM:=4c8d9ca68dda88d3cfc0ca0fb946a63e

include $(INCLUDE_DIR)/package.mk

PKG_B_NAME:=dsl_vr9_firmware_xdsl
PKG_B_VERSION:=05.07.03.03.00.06_05.07.01.0C.00.02_osc
PKG_B_SOURCE:=$(PKG_B_NAME)-$(PKG_B_VERSION).tar.gz

define Download/dsl_vr9_firmware_xdsl_b
  FILE:=$(PKG_B_SOURCE)
  URL:=$(PKG_SOURCE_URL)
  MD5SUM:=af5581836cbe574574590c046fe45bab
endef
$(eval $(call Download,dsl_vr9_firmware_xdsl_b))


define Package/dsl-vrx200-firmware-xdsl
  SECTION:=firmware
  CATEGORY:=Firmware
  TITLE:=VRX200 / VR9 CPE xDSL Annex A firmware
  URL:=http://www.lantiq.com/
  DEPENDS:=@TARGET_lantiq_xrx200
endef

define Package/dsl-vrx200-firmware-xdsl-a/description
	VRX200 / VR9 CPE VDSL and ADSL Annex A firmware
endef

define Build/Prepare
	rm -rf $(PKG_BUILD_DIR)
	mkdir -p $(PKG_BUILD_DIR)
	$(TAR) -C $(PKG_BUILD_DIR) -xzf $(DL_DIR)/$(PKG_SOURCE)
	$(TAR) -C $(PKG_BUILD_DIR) -xzf $(DL_DIR)/$(PKG_B_SOURCE)
endef

define Build/Compile
	bsdiff \
		$(PKG_BUILD_DIR)/xcpe_574306_571801.bin \
		$(PKG_BUILD_DIR)/xcpe_573306_571C02.bin \
		$(PKG_BUILD_DIR)/xcpe_574306_571801_to_573306_571C02.bspatch
endef

define Package/dsl-vrx200-firmware-xdsl/install
	$(INSTALL_DIR) $(1)/lib/firmware/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/LICENSE $(1)/lib/firmware/xcpe_574306_571801.LICENSE
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/xcpe_574306_571801.bin $(1)/lib/firmware/
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/xcpe_574306_571801_to_573306_571C02.bspatch $(1)/lib/firmware/
	ln -s xcpe_574306_571801.bin $(1)/lib/firmware/lantiq-vrx200-a.bin
endef

$(eval $(call BuildPackage,dsl-vrx200-firmware-xdsl))
