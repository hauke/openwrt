#
# Copyright (C) 2021 Jo-Philipp Wich <jo@mein.io>
#

include $(TOPDIR)/rules.mk

PKG_NAME:=firewall4
PKG_RELEASE:=1

PKG_SOURCE_PROTO:=git
PKG_SOURCE_URL=$(PROJECT_GIT)/project/firewall4.git
PKG_MIRROR_HASH:=9e2beb84b9bb749536453dc912120f0ded551ac3f69ed04c4c56617f7bc64ab1
PKG_SOURCE_DATE:=2024-12-18
PKG_SOURCE_VERSION:=18fc0ead19faf06b8ce7ec5be84957278e942dfa
PKG_MAINTAINER:=Jo-Philipp Wich <jo@mein.io>
PKG_LICENSE:=ISC

include $(INCLUDE_DIR)/package.mk

define Package/firewall4
  SECTION:=net
  CATEGORY:=Base system
  TITLE:=OpenWrt 4th gen firewall
  DEPENDS:= \
	+kmod-nft-core +kmod-nft-fib +kmod-nft-offload \
	+kmod-nft-nat \
	+nftables-json \
	+ucode +ucode-mod-fs +ucode-mod-ubus +ucode-mod-uci
  EXTRA_DEPENDS:=ucode (>=2022.03.22)
  PROVIDES:=uci-firewall
endef

define Package/firewall4/description
 This package provides an nftables-based implementation of the UCI firewall
 sharing the same configuration format.
endef

define Package/firewall4/conffiles
/etc/config/firewall
/etc/nftables.d/
endef

define Package/firewall4/install
	$(CP) -a $(PKG_BUILD_DIR)/root/* $(1)/
endef

define Build/Compile
endef

$(eval $(call BuildPackage,firewall4))
