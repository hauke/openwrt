#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Copyright (C) 2009 by Thomas Petazzoni <thomas.petazzoni@free-electrons.com>
# Copyright (C) 2020 by Gregory CLEMENT <gregory.clement@bootlin.com>
#
# Vendored and adapted from buildroot's support/scripts/cve.py.
# Changes vs. upstream:
#   - Dropped sys.path.append('utils/') — not using Buildroot's nvd module.
#   - Replaced distutils.version.LooseVersion with a local implementation
#     (distutils was removed in Python 3.12).
#   - Kept NVD git mirror clone logic; the workflow drives it via
#     actions/cache, but it still works when invoked standalone.

import datetime
import operator
import os
import re
import subprocess
import sys

import json


NVD_START_YEAR = 1999
NVD_BASE_URL = "https://github.com/fkie-cad/nvd-json-data-feeds/"

ops = {
    '>=': operator.ge,
    '>': operator.gt,
    '<=': operator.le,
    '<': operator.lt,
    '=': operator.eq
}


class LooseVersion:
    """Minimal drop-in replacement for distutils.version.LooseVersion.

    Splits a version string into numeric and non-numeric components and
    compares them element-wise. Accepts arbitrary version strings; falls
    back to string comparison when both sides carry non-comparable types.
    """

    component_re = re.compile(r'(\d+ | [a-zA-Z]+ | \.)', re.VERBOSE)

    def __init__(self, vstring=""):
        self.vstring = vstring
        comps = [x for x in self.component_re.split(vstring) if x and x != '.']
        for i, obj in enumerate(comps):
            try:
                comps[i] = int(obj)
            except ValueError:
                pass
        self.version = comps

    def _cmp(self, other):
        if isinstance(other, str):
            other = LooseVersion(other)
        for a, b in zip(self.version, other.version):
            if type(a) is not type(b):
                a, b = str(a), str(b)
            if a < b:
                return -1
            if a > b:
                return 1
        if len(self.version) < len(other.version):
            return -1
        if len(self.version) > len(other.version):
            return 1
        return 0

    def __lt__(self, other): return self._cmp(other) < 0
    def __le__(self, other): return self._cmp(other) <= 0
    def __eq__(self, other): return self._cmp(other) == 0
    def __ne__(self, other): return self._cmp(other) != 0
    def __gt__(self, other): return self._cmp(other) > 0
    def __ge__(self, other): return self._cmp(other) >= 0


class CPE:
    DISJOINT = 0
    SUBSET = 1
    SUPERSET = 2
    EQUAL = 3

    ANY = '*'
    NA = '-'

    @staticmethod
    def compareAttribute(left, right):
        """
        Compare two single attributes of two CPEs.
        Implements table 6-2 of NIST IR 7696.
        """
        if left == '':
            left = CPE.ANY
        if right == '':
            right = CPE.ANY

        if left == right:
            return CPE.EQUAL
        elif left == CPE.ANY:
            return CPE.SUPERSET
        elif left == CPE.NA and right == CPE.ANY:
            return CPE.SUBSET
        elif left == CPE.NA:
            return CPE.DISJOINT
        elif right == CPE.ANY:
            return CPE.SUBSET
        return CPE.DISJOINT

    def matches(self, target) -> bool:
        if not isinstance(target, CPE):
            target = CPE(target)
        for selfAttribute, targetAttribute in zip(self.parts, target.parts):
            if CPE.compareAttribute(selfAttribute, targetAttribute) == CPE.DISJOINT:
                return False
        return True

    def __str__(self):
        return self.cpe

    def __init__(self, cpe):
        self.cpe = cpe
        self.parts = cpe.split(':')
        # Expect CPE 2.3: cpe:2.3:part:vendor:product:version:update:edition:lang:sw_edition:target_sw:target_hw:other
        while len(self.parts) < 13:
            self.parts.append('*')
        self.vendor = self.parts[3]
        self.product = self.parts[4]
        self.version = self.parts[5]
        self.update = self.parts[6]
        self.edition = self.parts[7]
        self.language = self.parts[8]
        self.sw_edition = self.parts[9]
        self.target_sw = self.parts[10]
        self.target_hw = self.parts[11]
        self.other = self.parts[12]


class CVE:
    """An accessor class for CVE Items in NVD files"""
    CVE_AFFECTS = 1
    CVE_DOESNT_AFFECT = 2
    CVE_UNKNOWN = 3

    def __init__(self, nvd_cve):
        self.nvd_cve = nvd_cve

    @staticmethod
    def download_nvd(nvd_dir):
        nvd_git_dir = os.path.join(nvd_dir, "git")

        if os.path.exists(nvd_git_dir):
            subprocess.check_call(
                ["git", "pull"],
                cwd=nvd_git_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.makedirs(nvd_git_dir)
            subprocess.check_call(
                ["git", "clone", "--depth=1", NVD_BASE_URL, nvd_git_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    @staticmethod
    def sort_id(cve_ids):
        def cve_key(cve_id):
            year, id_ = cve_id.split('-')[1:]
            return (int(year), int(id_))
        return sorted(cve_ids, key=cve_key)

    @classmethod
    def read_nvd_dir(cls, nvd_dir):
        nvd_git_dir = os.path.join(nvd_dir, "git")

        for year in range(NVD_START_YEAR, datetime.datetime.now().year + 1):
            year_dir = os.path.join(nvd_git_dir, f"CVE-{year}")
            if not os.path.isdir(year_dir):
                continue
            for dirpath, _, filenames in os.walk(year_dir):
                for filename in filenames:
                    if filename[-5:] != ".json":
                        continue
                    try:
                        with open(os.path.join(dirpath, filename), "rb") as f:
                            yield cls(json.load(f))
                    except (OSError, json.JSONDecodeError) as e:
                        print(f"Skipping {filename}: {e}", file=sys.stderr)

    def parse_node(self, node):
        for child in node.get('children', ()):
            for parsed_node in self.parse_node(child):
                yield parsed_node

        for cpe in node.get('cpeMatch', ()):
            if not cpe['vulnerable']:
                return
            cpeId = CPE(cpe['criteria'])
            product = cpeId.product
            version = cpeId.version
            if product == '-':
                return
            op_start = ''
            op_end = ''
            v_start = ''
            v_end = ''

            if version != '*' and version != '-':
                op_start = '='
                v_start = version
            else:
                if 'versionStartIncluding' in cpe:
                    op_start = '>='
                    v_start = cpe['versionStartIncluding']
                if 'versionStartExcluding' in cpe:
                    op_start = '>'
                    v_start = cpe['versionStartExcluding']
                if 'versionEndIncluding' in cpe:
                    op_end = '<='
                    v_end = cpe['versionEndIncluding']
                if 'versionEndExcluding' in cpe:
                    op_end = '<'
                    v_end = cpe['versionEndExcluding']

            yield {
                'id': cpeId,
                'v_start': v_start,
                'op_start': op_start,
                'v_end': v_end,
                'op_end': op_end
            }

    def each_cpe(self):
        for nodes in self.nvd_cve.get('configurations', []):
            for node in nodes.get('nodes', []):
                for cpe in self.parse_node(node):
                    yield cpe

    @property
    def identifier(self):
        return self.nvd_cve['id']

    @property
    def description(self):
        for d in self.nvd_cve.get('descriptions', []):
            if d.get('lang') == 'en':
                return d.get('value', '')
        return ''

    @property
    def severity(self):
        metrics = self.nvd_cve.get('metrics', {})
        for key in ('cvssMetricV40', 'cvssMetricV31', 'cvssMetricV30', 'cvssMetricV3'):
            for m in metrics.get(key, []):
                sev = (m.get('cvssData') or {}).get('baseSeverity')
                if sev:
                    return sev.upper()
        for m in metrics.get('cvssMetricV2', []):
            sev = m.get('baseSeverity')
            if sev:
                return sev.upper()
        return 'UNKNOWN'

    @property
    def affected_products(self):
        return set(p['id'].product for p in self.each_cpe())

    def affects(self, name, version, cpeid=None):
        """True if the component (name, version, cpeid) is affected by this CVE."""
        if cpeid is None:
            cpeid = CPE("cpe:2.3:*:*:%s:%s:*:*:*:*:*:*:*" % (name, version))
        elif not isinstance(cpeid, CPE):
            cpeid = CPE(cpeid)

        try:
            pkg_version = LooseVersion(cpeid.version)
        except Exception:
            pkg_version = None

        for cpe in self.each_cpe():
            if not cpe['id'].matches(cpeid):
                continue
            if not cpe['v_start'] and not cpe['v_end']:
                return self.CVE_AFFECTS
            if not pkg_version:
                continue

            if cpe['v_start']:
                try:
                    cve_affected_version = LooseVersion(cpe['v_start'])
                    inrange = ops.get(cpe['op_start'])(pkg_version, cve_affected_version)
                except TypeError:
                    return self.CVE_UNKNOWN
                if not inrange:
                    continue

            if cpe['v_end']:
                try:
                    cve_affected_version = LooseVersion(cpe['v_end'])
                    inrange = ops.get(cpe['op_end'])(pkg_version, cve_affected_version)
                except TypeError:
                    return self.CVE_UNKNOWN
                if not inrange:
                    continue

            return self.CVE_AFFECTS

        return self.CVE_DOESNT_AFFECT
