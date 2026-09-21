#!/usr/bin/env python3
"""Self-checking release-layer verifier for audit finding P1-11.

rc=0 ⇔ релизный слой совпал с EXPECTED (состояние ПОСЛЕ закрытия P1-11)
И каждый контроль перевернулся. На пред-фиксном дереве (plist-литералы 0.3/1,
shared scheme отсутствует, устаревшие EXPECTED в runbook) инструмент обязан дать
rc=1. Контроль `undo_fix_is_red` прогоняет четыре независимых отката плана в
памяти и требует, чтобы каждый снова окрасил СВОИ AC: зелёный verdict на текущем
дереве causally привязан к фиксу, а не к безразличию зондов.

Структура скопирована с evidence/v3_measurements.py (audit 20260919-7db1f3):
EXPECTED / got / controls / одна строка на AC / RESULT / sys.exit.

Правила разбора (см. mistakes: regex-разбор структурированных данных в этом репо
уже давал неверные числа):
  * Info.plist        -> plistlib (никаких regex по <string>);
  * *.xcscheme        -> xml.etree.ElementTree;
  * project.pbxproj   -> plistlib НЕ умеет OpenStep-ASCII, поэтому адресный
    построчный читальщик с tab-depth-стэком, который ЯВНО помнит, в каком блоке
    XCBuildConfiguration лежит каждый ключ. Именно block-привязка отличает этот
    зонд от `grep -c MARKETING_VERSION` (лаг, зафиксированный в P1-11): контроль
    `marketing_moves_between_blocks` обязан перевернуться на переносе строки
    MARKETING_VERSION из target-блока в project-блок, а grep -c на такую мутацию
    НЕ реагирует.
  * ReferencedContainer -> только строчная форма `container:<имя>.xcodeproj`,
    которую пишет сам Xcode. Контроль `container_prefix_casing_rejected` краснит
    заглавную `Container:`: черновик этого инструмента пинил именно её, из-за чего
    все синтетики были самосогласованно зелёными со значением, которое Xcode не
    разрешает в контейнер.

Мутации и синтетики живут ТОЛЬКО в памяти: продукт-файлы не пишутся, git не трогается.

Запуск: python3 release_layer_check.py [--root <путь>] [--json]
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import pathlib
import plistlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

# --- адреса -----------------------------------------------------------------
PROJECT_DIR = "Exolon.xcodeproj"
PBXPROJ = "Exolon.xcodeproj/project.pbxproj"
INFO_PLIST = "Exolon/Resources/Info.plist"
SCHEME_REL = "Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme"
SHARED_SCHEME_DIRMARK = "xcshareddata/xcschemes/"
USER_SCHEME_DIRMARK = "xcuserdata/"
RUNBOOK = "engineering/runbooks/macos-probe.sh"
V3_TOOL = ("engineering/changes/20260919-exolon-initial-code-audit-7db1f3"
           "/evidence/v3_measurements.py")
CHANGE_DIR = "engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698"
# Плановые документы change-пакета. evidence/ И brief.md ИСКЛЮЧЕНЫ намеренно:
# brief.md автогенерится из формулировки задачи и уже содержит "hardened runtime",
# а этот verifier тоже лежит в evidence/ и упоминает "shared_xcschemes" — искать
# «запись об owned cutover» там означало бы принять самоцитату за решение.
PLAN_FILES = ("requirements.md", "architecture.md", "tasks.md", "test-plan.md",
              "release.md", "rollback.md", "change-spec.yaml")

TARGET_GUID = "500000000000000000000001"          # PBXNativeTarget "Exolon"
TARGET_DEBUG_CFG = "800000000000000000000003"
TARGET_RELEASE_CFG = "800000000000000000000004"
PROJECT_DEBUG_CFG = "800000000000000000000001"
PROJECT_RELEASE_CFG = "800000000000000000000002"
PRODUCT_REF_GUID = "200000000000000000000010"     # Exolon.app
APP_PRODUCT_TYPE = "com.apple.product-type.application"
TEST_PRODUCT_TYPE = "com.apple.product-type.bundle.unit-test"

VERSION_KEYS = {
    "CFBundleShortVersionString": "$(MARKETING_VERSION)",
    "CFBundleVersion": "$(CURRENT_PROJECT_VERSION)",
}
CANON_BUILDABLE_ATTRS = ("BlueprintIdentifier", "BlueprintName", "BuildableName",
                         "BuildableIdentifier", "ReferencedContainer")
BUILD_ENTRY_FLAGS = ("buildForTesting", "buildForRunning", "buildForProfiling",
                     "buildForArchiving", "buildForAnalyzing")
REQUIRED_SCHEME_ACTIONS = ("BuildAction", "TestAction", "LaunchAction", "ArchiveAction")

# pin: сниманЕ двух версионных ключей. Любой правый сторонний edit Info.plist
# (например «раз уж правим, поднимем и LSMinimumSystemVersion») обязан дать red.
PLIST_NONVERSION_DIGEST = "8801d6fb59cb69443ac24775101583ecc48ca6cbd3280c035bd3bb7bdc87210f"

# append-only: blob'ы датированных отчётов, какие они в pin-коммите и какие они
# в HEAD. Правка задним числом уже опубликованного аудита = red.
REPORTS_PIN_COMMIT = {
    "engineering/reports/exolon-full-audit-20260920.md": "bcacf30",
    "engineering/reports/exolon-full-audit-20260920-v3.md": "7c1068e",
}
REPORTS_PIN_BLOB = {
    "engineering/reports/exolon-full-audit-20260920.md": "f66fb029460e3a740441d10e8063d19743a899a3",
    "engineering/reports/exolon-full-audit-20260920-v3.md": "8ad43a9df5227aab8b624c535a2d8066ff7de55a",
}

EXPECTED: dict[str, object] = {
    # 0. имя проекта пинится литералом, а не выводится из того же glob, которым
    #    строится синтетика «после фикса» — иначе ошибка в выводе имени проекта
    #    маскируется самосогласованной схемой (так и было на репетиции).
    "project_name": "Exolon",
    "xcodeproj_dir_count": 1,
    # A. Info.plist: версия обязательна из build settings, ничего лишнего не тронуто
    "plist_parses": 1,
    "plist_key_count": 11,
    "plist_version_keys_present": 2,
    "plist_version_keys_substituted": 2,
    "plist_version_keys_literal": 0,
    "plist_nonversion_untouched": 1,
    # B. project.pbxproj: MARKETING/CURRENT лежат именно в target-конфигах
    "pbxproj_parses": 1,
    "native_target_count": 1,
    "test_target_count": 0,
    "target_config_names": {TARGET_DEBUG_CFG: "Debug", TARGET_RELEASE_CFG: "Release"},
    "marketing_version_in_target_configs": 2,
    "marketing_version_value": "0.5",
    "marketing_version_outside_target_configs": 0,
    "project_version_in_target_configs": 2,
    "project_version_value": "1",
    "project_version_outside_target_configs": 0,
    "infoplist_file_setting_in_target_configs": 2,
    "generate_infoplist_off_in_target_configs": 2,
    "hardened_runtime_key_count": 0,          # DELIBERATELY DEFERRED (см. AC ниже)
    "target_cfg_symmetric": 1,                # INV-001: Debug/Release target-конфиги равны
    "hardened_symmetric": 1,                  # ключ отсутствует в обоих ИЛИ присутствует в обоих
    "hardened_deferral_recorded": 1,
    # C. Shared scheme
    "shared_scheme_count": 1,
    "shared_scheme_path_exact": 1,
    "user_scheme_count": 0,
    "scheme_xml_parses": 1,
    "scheme_blueprint_is_native_target": 1,
    "scheme_blueprint_guid_is_exolon": 1,
    "scheme_actions_required": 4,
    "scheme_build_entry_flags_yes": 5,
    "scheme_build_for_archiving_yes": 1,
    # Xcode кладёт BuildableReference ровно в четыре места: BuildActionEntry,
    # MacroExpansion внутри TestAction, Launch- и Profile-Runnable. Внутри
    # ArchiveAction своей ссылки нет — она наследует BuildAction, — поэтому пин
    # равен 4 (в черновике было 5 за счёт неканонической вложенной ссылки).
    "scheme_buildable_refs_total": 4,
    "scheme_buildable_refs_missing_attrs": 0,
    "scheme_buildable_refs_not_primary": 0,
    "scheme_buildable_refs_bad_container": 0,
    "scheme_buildable_refs_bad_name": 0,
    "scheme_runnable_is_application": 1,
    "scheme_dangling_test_refs": 0,
    # Конфигурации действий: требование маршрута — «scheme with an Archive action»,
    # то есть архивируемая конфигурация должна быть именно Release. Launch=Debug —
    # дефолт Xcode для нового таргета; тихий перевод Run на Release менял бы то,
    # что разработчик получает по Cmd+R, и это тоже должно измеряться, а не читаться
    # глазами из XML.
    "scheme_archive_build_configuration": "Release",
    "scheme_launch_build_configuration": "Debug",
    # D. Гигиена доказательств и владение landmine
    "reports_dated_count": 2,
    "reports_blob_mismatches": 0,
    "v3_pin_shared_xcschemes": 0,
    "v3_shared_scheme_cutover_owned": 1,
    "runbook_stale_gap_claims": 0,
    "runbook_archive_step_present": 1,
}
# pbxproj_objects_parsed / unbalanced / digest печатаются как informational:
# читальщик проверяется контролем reader_object_count_balances, а не литералом.


# --- чистые детекторы (принимают данные, чтобы контроль мог их исказить) -----
def detect_plist(data: bytes) -> dict:
    out = {"parses": 0, "keys": 0, "present": 0, "substituted": 0, "literal": 0,
           "nonversion_digest_ok": 0, "dict": {}}
    try:
        d = plistlib.loads(data)
    except Exception:
        return out
    out["parses"] = 1
    out["dict"] = d
    out["keys"] = len(d)
    for key, want in VERSION_KEYS.items():
        if key not in d:
            continue
        out["present"] += 1
        val = d[key]
        if isinstance(val, str) and val == want:
            out["substituted"] += 1
        else:
            out["literal"] += 1
    rest = {k: v for k, v in d.items() if k not in VERSION_KEYS}
    dig = hashlib.sha256(repr(sorted((k, repr(v)) for k, v in rest.items())).encode()).hexdigest()
    out["nonversion_digest_ok"] = int(dig == PLIST_NONVERSION_DIGEST)
    out["nonversion_digest"] = dig
    return out


# --- адресный читальщик OpenStep-ASCII ---------------------------------------
OBJ_HEAD = re.compile(r"^([0-9A-Za-z]{24})\s*=\s*\{(.*)$")
KV = re.compile(r'^([A-Za-z_][\w.]*)\s*=\s*("(?:[^"\\]|\\.)*"|[^;]*);')
QUOTED = re.compile(r'^"((?:[^"\\]|\\.)*)"$')


def _strip_comments(line: str) -> str:
    return re.sub(r"/\*.*?\*/", "", line).strip()


def _unquote(raw: str) -> str:
    raw = raw.strip()
    m = QUOTED.match(raw)
    if m:
        return m.group(1).replace('\\"', '"').replace("\\\\", "\\")
    return raw


def read_pbxproj(text: str) -> dict:
    """guid -> {isa,name,buildSettings,arrays{path/key->[token]},inline{key->val}}.

    Tab-depth state machine. Ведутся две независимые стековые сущности: путь
    блоков-словарей (`blockpath`) и идентификатор открытого массива. Баланс
    возвращается в `unbalanced`: непустой список значит, что читальщик не довёл
    разбор до конца и все derived-числа недостоверны.
    """
    objs: dict[str, dict] = {}
    stack: list[str] = []          # "block:<key>" | "array:<key>"
    cur: dict | None = None
    cur_array: list[str] | None = None
    in_objects = False
    unbalanced: list[str] = []

    def blockpath() -> str:
        return "/".join(s[6:] for s in stack if s.startswith("block:"))

    for raw in text.splitlines():
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip("\t"))
        line = _strip_comments(raw.rstrip())
        if not line:
            continue
        if indent <= 1:
            if line == "objects = {":
                in_objects = True
            elif in_objects and line == "};":
                in_objects = False
                stack, cur, cur_array = [], None, None
            continue
        if not in_objects:
            continue
        if cur is None:
            m = OBJ_HEAD.match(line)
            if m and indent == 2:
                guid, tail = m.group(1), m.group(2).strip()
                rec = {"isa": "", "name": "", "buildSettings": {}, "arrays": {},
                       "settings": {}, "inline": {}}
                objs[guid] = rec
                cur, stack, cur_array = rec, [], None
                if tail.endswith("};"):        # однострочный объект (PBXBuildFile/PBXFileReference)
                    for km in KV.finditer(tail[:-2]):
                        rec["inline"][km.group(1)] = _unquote(km.group(2))
                    rec["isa"] = rec["inline"].get("isa", "")
                    rec["name"] = rec["inline"].get("name", "")
                    cur = None
            continue
        # закрытия
        if line == "};" and stack and stack[-1].startswith("block:"):
            stack.pop()
            continue
        if line == ");" and stack and stack[-1].startswith("array:"):
            stack.pop()
            continue
        if line == "};" and indent == 2 and not stack:
            cur, cur_array = None, None
            continue
        # открытия
        if line.endswith("= {"):
            stack.append("block:" + line[:-3].split("=")[0].strip())
            continue
        if line.endswith("= ("):
            key = line[:-3].split("=")[0].strip()
            aid = (blockpath() + "/" if blockpath() else "") + key
            arr = cur["arrays"].setdefault(aid, [])   # per-object: два разных объекта
            stack.append("array:" + key)              # с одноимённым массивом не сливаются
            cur_array = arr
            continue
        if re.match(r"^\)\s*;$", line):        # inline-массив, закрытый на той же строке
            cur_array = None
            continue
        km = KV.match(line)
        if km:
            key, val = km.group(1), _unquote(km.group(2))
            path = blockpath()
            if path == "buildSettings":
                cur["buildSettings"][key] = val
            elif path == "" and indent == 3:
                cur["inline"][key] = val
                if key == "isa":
                    cur["isa"] = val
                elif key == "name":
                    cur["name"] = val
            else:
                cur["settings"].setdefault(path, {})[key] = val
            continue
        if stack and stack[-1].startswith("array:") and cur_array is not None:
            tok = line.strip().rstrip(",").strip()
            if tok:
                cur_array.append(tok.split()[0])
            continue
    if stack:
        unbalanced.append("stack_left:" + "|".join(stack))
    return {"objects": objs, "unbalanced": unbalanced}



def detect_pbxproj(text: str) -> dict:
    r = read_pbxproj(text)
    objs = r["objects"]
    def bs(g):
        return objs.get(g, {}).get("buildSettings", {})
    targets = {g: o for g, o in objs.items() if o.get("isa") == "PBXNativeTarget"}
    test_targets = [g for g, o in targets.items()
                    if o.get("inline", {}).get("productType") == TEST_PRODUCT_TYPE]
    # target-конфиги ВЫВОДЯТСЯ из PBXNativeTarget -> XCConfigurationList, а не хардкодом;
    # EXPECTED сверяет выведенное с ожидаемым набором GUID — иначе правка проекта
    # (перенумерация блоков) тихо переложит ключ в непроверяемый блок.
    cfg_list_guid = targets.get(TARGET_GUID, {}).get("inline", {}).get("buildConfigurationList", "")
    entries = objs.get(cfg_list_guid, {}).get("arrays", {})
    target_cfgs = next((v for k, v in entries.items() if k.endswith("buildConfigurations")), [])
    target_bs = {g: bs(g) for g in target_cfgs}
    other_cfgs = [g for g, o in objs.items()
                  if o.get("isa") == "XCBuildConfiguration" and g not in target_bs]
    mv_in = sum(1 for g in target_bs if "MARKETING_VERSION" in target_bs[g])
    mv_out = sum(1 for g in other_cfgs if "MARKETING_VERSION" in bs(g))
    cv_in = sum(1 for g in target_bs if "CURRENT_PROJECT_VERSION" in target_bs[g])
    cv_out = sum(1 for g in other_cfgs if "CURRENT_PROJECT_VERSION" in bs(g))
    vals = {target_bs[g].get("MARKETING_VERSION") for g in target_bs if "MARKETING_VERSION" in target_bs[g]}
    cvals = {target_bs[g].get("CURRENT_PROJECT_VERSION") for g in target_bs
            if "CURRENT_PROJECT_VERSION" in target_bs[g]}
    obj_head = re.compile(r"^\t\t[0-9A-Za-z]{24}(?: /\* .* \*/)? = \{$")
    obj_single = re.compile(r"^\t\t[0-9A-Za-z]{24}(?: /\* .* \*/)? = \{.*\};\s*$")
    lines = text.splitlines()
    header_objects = sum(1 for ln in lines if obj_head.match(ln))
    single_line_objects = sum(1 for ln in lines if obj_single.match(ln))
    isa_configs = sum(1 for o in objs.values() if o.get("isa") == "XCBuildConfiguration")
    missing_isa = sum(1 for o in objs.values() if not o.get("isa"))
    parses = int(not r["unbalanced"] and missing_isa == 0 and isa_configs == 4
                 and len(objs) == header_objects + single_line_objects
                 and len(target_cfgs) == 2 and bool(cfg_list_guid))
    return {
        "parses": parses,
        "parsed_objects": len(objs),
        "header_objects": header_objects,
        "single_line_objects": single_line_objects,
        "objects_missing_isa": missing_isa,
        "isa_configs": isa_configs,
        "unbalanced": r["unbalanced"],
        "objects": objs,
        "target_cfg_guids": sorted(target_cfgs),
        "target_config_names": {g: objs[g].get("name", "") for g in target_cfgs if g in objs},
        "marketing_in": mv_in, "marketing_out": mv_out,
        "marketing_value": sorted(vals)[0] if len(vals) == 1 else list(sorted(vals)),
        "project_ver_in": cv_in, "project_ver_out": cv_out,
        "project_ver_value": sorted(cvals)[0] if len(cvals) == 1 else list(sorted(cvals)),
        "infoplist_file_in": sum(1 for g in target_bs
                                 if bs(g).get("INFOPLIST_FILE") == INFO_PLIST),
        "generate_off_in": sum(1 for g in target_bs
                               if bs(g).get("GENERATE_INFOPLIST_FILE") == "NO"),
        "hardened_count": sum(1 for g in objs if "ENABLE_HARDENED_RUNTIME" in bs(g)),
        # INV-001: два target-конфига обязаны оставаться симметричными по buildSettings
        # (handout:34-36 фиксирует это как датированный инвариант), а ключ hardening может
        # отсутствовать в обоих или присутствовать в обоих — никогда в одном.
        "target_cfg_symmetric": int(len(target_cfgs) == 2
                                    and bs(target_cfgs[0]) == bs(target_cfgs[1])),
        "hardened_symmetric": int(sum(1 for g in target_cfgs
                                      if "ENABLE_HARDENED_RUNTIME" in bs(g)) in (0, 2)),
        "native_targets": len(targets),
        "test_targets": len(test_targets),
        "target_product_type": targets.get(TARGET_GUID, {}).get("inline", {}).get("productType", ""),
        "target_guids": sorted(targets),
        "product_name": objs.get(PRODUCT_REF_GUID, {}).get("inline", {}).get("path", ""),
        "cfg_list_guid": cfg_list_guid,
    }



def classify_scheme(rel: str) -> str:
    if not rel.endswith(".xcscheme"):
        return "other"
    if USER_SCHEME_DIRMARK in rel:
        return "user"
    if SHARED_SCHEME_DIRMARK in rel:
        return "shared"
    return "other"


def want_container() -> str:
    """Контейнер схемы сверяется с ЛИТЕРАЛОМ EXPECTED["project_name"], а не с именем,
    выведенным из того же glob, которым строится синтетика «после фикса»: на репетиции
    это дало самосогласованно-зелёный удвоенный суффикс container:Exolon.xcodeproj.xcodeproj.
    Префикс именно строчный: Xcode пишет ReferencedContainer = "container:Foo.xcodeproj",
    а заглавную форму («Container:», как пинил черновик) в контейнер не разворачивает."""
    return "container:%s.xcodeproj" % EXPECTED["project_name"]


def detect_scheme(xml: bytes | None, pbx: dict) -> dict:
    out = {"parses": 0, "shared": 0, "path_exact": 0, "is_native_target": 0,
           "guid_is_exolon": 0, "actions": 0, "flags_yes": 0, "archiving": 0,
           "refs_total": 0, "refs_missing": 0, "refs_not_primary": 0,
           "refs_bad_container": 0, "refs_bad_name": 0, "runnable_app": 0,
           "dangling_tests": 0, "archive_config": "", "launch_config": ""}
    if xml is None:
        return out
    try:
        root = ET.fromstring(xml)
    except Exception:
        return out
    out["parses"] = 1
    native = set(pbx["target_guids"])
    wcont = want_container()
    actions = {c.tag for c in root}
    out["actions"] = len([a for a in REQUIRED_SCHEME_ACTIONS if a in actions])
    refs = list(root.iter("BuildableReference"))
    out["refs_total"] = len(refs)
    for ref in refs:
        out["refs_missing"] += int(any(ref.get(a) in (None, "") for a in CANON_BUILDABLE_ATTRS))
        out["refs_not_primary"] += int(ref.get("BuildableIdentifier") != "primary")
        out["refs_bad_container"] += int(ref.get("ReferencedContainer") != wcont)
    build = root.find("BuildAction")
    entries = build.findall("BuildActionEntries/BuildActionEntry") if build is not None else []
    if entries:
        e = entries[0]
        out["flags_yes"] = sum(1 for f in BUILD_ENTRY_FLAGS if e.get(f) == "YES")
        out["archiving"] = int(e.get("buildForArchiving") == "YES")
    blueprints = {r.get("BlueprintIdentifier") for r in refs}
    if blueprints and blueprints <= native:
        out["is_native_target"] = 1
    out["guid_is_exolon"] = int(blueprints == {TARGET_GUID})
    # BlueprintName/BuildableName должны совпадать с реальным таргетом и продуктом
    want_name = pbx["objects"].get(TARGET_GUID, {}).get("name", "")
    want_prod = pbx["product_name"] or "Exolon.app"
    out["refs_bad_name"] = sum(
        1 for r in refs
        if (r.get("BlueprintName") != want_name or r.get("BuildableName") != want_prod
            or r.get("ReferencedContainer") != wcont))
    # RunAction: исполняемый продукт обязан быть именно application
    run = root.find("LaunchAction")
    if run is not None:
        runnable = run.find("BuildableProductRunnable")
        rr = runnable.find("BuildableReference") if runnable is not None else None
        pt = ""
        if rr is not None:
            pt = pbx["objects"].get(rr.get("BlueprintIdentifier"), {}).get("inline", {}).get("productType", "")
        out["runnable_app"] = int(runnable is not None and rr is not None
                                 and runnable.get("runnableDebuggingMode") == "0"
                                 and pt == APP_PRODUCT_TYPE)
    # TestAction: ни одного testable-ссылки на несуществующий таргет
    for t in root.iter("TestableReference"):
        if t.get("BlueprintIdentifier") not in native:
            out["dangling_tests"] += 1
    for t in root.iter("SkippedTestable"):
        if t.get("BlueprintIdentifier") not in native:
            out["dangling_tests"] += 1
    # Конфигурации действий как значения, а не как булевы «есть ли атрибут».
    arch = root.find("ArchiveAction")
    out["archive_config"] = arch.get("buildConfiguration", "") if arch is not None else ""
    lch = root.find("LaunchAction")
    out["launch_config"] = lch.get("buildConfiguration", "") if lch is not None else ""
    return out


def detect_cutover(v3_src: str, shared_count: int, plan_text: str) -> dict:
    pin = None
    try:
        for node in ast.walk(ast.parse(v3_src)):
            tgt = node.target if isinstance(node, ast.AnnAssign) else None
            if isinstance(node, ast.Assign):
                tgt = node.targets[0]
            if isinstance(tgt, ast.Name) and tgt.id == "EXPECTED" and isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and k.value == "shared_xcschemes":
                        pin = ast.literal_eval(v)
    except Exception:
        pin = None
    # v3 считает shared_xcschemes как root.glob("**/*.xcscheme") — без различения
    # shared/user. Значит после добавления схемы он покраснеет сам собой.
    owned = 0
    if pin == shared_count:
        owned = 1
    elif pin == 0 and shared_count >= 1 and "shared_xcschemes" in plan_text:
        owned = 1
    return {"v3_pin": pin, "owned": owned, "record_present": int("shared_xcschemes" in plan_text)}


def detect_runbook(text: str) -> dict:
    """Счёт устаревших ожиданий: строка устарела, если она помечена EXPECTED *и*
    утверждает старый gap. Строка `verdict_shared_scheme=ABSENT (...)` в ветке
    case — это сообщение о РЕГРЕССИИ, она права не портит.
    """
    markers = (r"no shared scheme", r"\b0 \.xcscheme", r"shared scheme.*ABSENT",
               r"CFBundleShortVersionString\s*=\s*0\.3", r"\.xcscheme\)?\s*=\s*0",
               r"shared_xcschemes\s*[:=]\s*0")
    stale = []
    for ln in text.splitlines():
        if "EXPECTED" not in ln:
            continue
        for m in markers:
            if re.search(m, ln):
                stale.append(m)
                break
    return {"stale": len(stale), "stale_claims": stale,
            "archive": int(bool(re.search(r"archive|archiv", text, re.I))),
            "scheme_present_claim": int(bool(re.search(r"EXPECTED[^.\n]*shared scheme[^.\n]*present",
                                                       text, re.I)))}



def detect_reports(work: dict) -> dict:
    bad = 0
    for rel, info in work.items():
        if not (info["head_blob"] == info["pin_blob"] == info["worktree_blob"]):
            bad += 1
    return {"mismatches": bad, "dated": len(work)}


# --- git (только чтение) -----------------------------------------------------
def git(root: pathlib.Path, *args: str) -> str:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                              text=True, check=False).stdout.strip()
    except OSError:
        return ""


def gather_reports(root: pathlib.Path) -> dict:
    dated = sorted(p for p in (root / "engineering" / "reports").glob("*.md")
                   if re.search(r"-20\d{6}", p.name)) if (root / "engineering" / "reports").is_dir() else []
    out: dict[str, dict] = {}
    for p in dated:
        rel = p.relative_to(root).as_posix()
        data = p.read_bytes()
        out[rel] = {
            # git blob id считается детерминированно из содержимого (sha1 "blob N\0"+bytes);
            # сравниваем с HEAD-биобом и с биобом из pin-коммита — три точки, проза не в счёт.
            "worktree_blob": hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest(),
            "head_blob": git(root, "rev-parse", f"HEAD:{rel}"),
            "pin_blob": REPORTS_PIN_BLOB.get(rel, ""),
            "pin_commit": REPORTS_PIN_COMMIT.get(rel, ""),
        }
    return out


# --- контекст дерева ---------------------------------------------------------
def load_inputs(root: pathlib.Path) -> dict:
    def rd(rel: str) -> str:
        p = root / rel
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""

    def rdb(rel: str) -> bytes | None:
        p = root / rel
        return p.read_bytes() if p.is_file() else None

    schemes = []
    for p in sorted(root.rglob("*.xcscheme")):
        if ".git" in p.relative_to(root).parts:
            continue
        schemes.append(p.relative_to(root).as_posix())
    shared = [s for s in schemes if classify_scheme(s) == "shared"]
    user = [s for s in schemes if classify_scheme(s) == "user"]
    project_dirs = [p.name[: -len(".xcodeproj")] for p in root.glob("*.xcodeproj")]
    plan_text = "\n".join(rd(f"{CHANGE_DIR}/{f}") for f in PLAN_FILES)
    return {
        "plist": rdb(INFO_PLIST) or b"",
        "pbx": rd(PBXPROJ),
        "scheme": rdb(SCHEME_REL),
        "scheme_present": SCHEME_REL in shared,
        "shared": shared,
        "user": user,
        "project_name": (project_dirs[0] if len(project_dirs) == 1 else "|".join(project_dirs)),
        "project_dir_count": len(project_dirs),
        "v3": rd(V3_TOOL),
        "runbook": rd(RUNBOOK),
        "brief": rd(f"{CHANGE_DIR}/brief.md"),
        "plan_text": plan_text,
        "reports": gather_reports(root),
    }


def measure(ctx: dict) -> dict:
    pl = detect_plist(ctx["plist"])
    pbx = detect_pbxproj(ctx["pbx"])
    sc = detect_scheme(ctx["scheme"] if ctx["scheme_present"] else None, pbx)
    cut = detect_cutover(ctx["v3"], len(ctx["shared"]), ctx["plan_text"])
    rb = detect_runbook(ctx["runbook"])
    rp = detect_reports(ctx["reports"])
    return {
        "plist_parses": pl["parses"],
        "plist_key_count": pl["keys"],
        "plist_version_keys_present": pl["present"],
        "plist_version_keys_substituted": pl["substituted"],
        "plist_version_keys_literal": pl["literal"],
        "plist_nonversion_untouched": pl["nonversion_digest_ok"],
        "pbxproj_parses": pbx["parses"],
        "pbxproj_objects_parsed": pbx["parsed_objects"],
        "native_target_count": pbx["native_targets"],
        "test_target_count": pbx["test_targets"],
        "target_config_names": pbx["target_config_names"],
        "marketing_version_in_target_configs": pbx["marketing_in"],
        "marketing_version_value": pbx["marketing_value"],
        "marketing_version_outside_target_configs": pbx["marketing_out"],
        "project_version_in_target_configs": pbx["project_ver_in"],
        "project_version_value": pbx["project_ver_value"],
        "project_version_outside_target_configs": pbx["project_ver_out"],
        "infoplist_file_setting_in_target_configs": pbx["infoplist_file_in"],
        "generate_infoplist_off_in_target_configs": pbx["generate_off_in"],
        "hardened_runtime_key_count": pbx["hardened_count"],
        "target_cfg_symmetric": pbx["target_cfg_symmetric"],
        "hardened_symmetric": pbx["hardened_symmetric"],
        "hardened_deferral_recorded": int("ENABLE_HARDENED_RUNTIME" in ctx["plan_text"]),
        "project_name": ctx["project_name"],
        "xcodeproj_dir_count": ctx["project_dir_count"],
        "shared_scheme_count": len(ctx["shared"]),
        "shared_scheme_path_exact": int(ctx["scheme_present"]),
        "user_scheme_count": len(ctx["user"]),
        "scheme_xml_parses": sc["parses"],
        "scheme_blueprint_is_native_target": sc["is_native_target"],
        "scheme_blueprint_guid_is_exolon": sc["guid_is_exolon"],
        "scheme_actions_required": sc["actions"],
        "scheme_build_entry_flags_yes": sc["flags_yes"],
        "scheme_build_for_archiving_yes": sc["archiving"],
        "scheme_buildable_refs_total": sc["refs_total"],
        "scheme_buildable_refs_missing_attrs": sc["refs_missing"],
        "scheme_buildable_refs_not_primary": sc["refs_not_primary"],
        "scheme_buildable_refs_bad_container": sc["refs_bad_container"],
        "scheme_buildable_refs_bad_name": sc["refs_bad_name"],
        "scheme_runnable_is_application": sc["runnable_app"],
        "scheme_dangling_test_refs": sc["dangling_tests"],
        "scheme_archive_build_configuration": sc["archive_config"],
        "scheme_launch_build_configuration": sc["launch_config"],
        "reports_dated_count": rp["dated"],
        "reports_blob_mismatches": rp["mismatches"],
        "v3_pin_shared_xcschemes": cut["v3_pin"],
        "v3_shared_scheme_cutover_owned": cut["owned"],
        "runbook_stale_gap_claims": rb["stale"],
        "runbook_archive_step_present": rb["archive"],
    }, {"plist": pl, "pbx": pbx, "sc": sc, "cut": cut, "rb": rb, "rp": rp}


# --- синтетики состояний (ничего не пишут) -----------------------------------
# Канон Xcode, воспроизведён по фактической форме, которую Xcode пишет сам: четыре
# BuildableReference (BuildActionEntry / MacroExpansion TestAction / Launch- и
# Profile-Runnable), ArchiveAction БЕЗ собственной ссылки, Test/Launch/Analyze =
# Debug, Profile/Archive = Release, префикс контейнера строчный.
GOOD_SCHEME = """<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion = "1020" version = "1.3">
   <BuildAction parallelizeBuildables = "YES" buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry buildForTesting = "YES" buildForRunning = "YES" buildForProfiling = "YES" buildForArchiving = "YES" buildForAnalyzing = "YES">
            <BuildableReference BuildableIdentifier = "primary" BlueprintIdentifier = "TARGET" BuildableName = "Exolon.app" BlueprintName = "Exolon" ReferencedContainer = "CONTAINER">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction buildConfiguration = "Debug" selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv = "YES">
      <Testables/>
      <MacroExpansion>
         <BuildableReference BuildableIdentifier = "primary" BlueprintIdentifier = "TARGET" BuildableName = "Exolon.app" BlueprintName = "Exolon" ReferencedContainer = "CONTAINER">
         </BuildableReference>
      </MacroExpansion>
   </TestAction>
   <LaunchAction buildConfiguration = "Debug" selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB" launchStyle = "0" useCustomWorkingDirectory = "NO" ignoresPersistentStateOnLaunch = "NO" debugDocumentVersioning = "YES" debugServiceExtension = "internal" allowLocationSimulation = "YES">
      <BuildableProductRunnable runnableDebuggingMode = "0">
         <BuildableReference BuildableIdentifier = "primary" BlueprintIdentifier = "TARGET" BuildableName = "Exolon.app" BlueprintName = "Exolon" ReferencedContainer = "CONTAINER">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction buildConfiguration = "Release" shouldUseLaunchSchemeArgsEnv = "YES" savedToolIdentifier = "" useCustomWorkingDirectory = "NO" debugDocumentVersioning = "YES">
      <BuildableProductRunnable runnableDebuggingMode = "0">
         <BuildableReference BuildableIdentifier = "primary" BlueprintIdentifier = "TARGET" BuildableName = "Exolon.app" BlueprintName = "Exolon" ReferencedContainer = "CONTAINER">
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction buildConfiguration = "Release" revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
"""

# Формулировки runbook ДО фикса. Это фиксированный снимок текста, а не чтение из
# HEAD: детектор устаревших EXPECTED и детектор archive-шага обязаны реагировать на
# содержание, а не на совпадение с тем, что лежит в дереве в момент прогона.
PRE_FIX_RUNBOOK = (
    'emit "## A. Scheme discovery (EXPECTED: no shared scheme)"\n'
    'emit "## C. Bundle version truth (EXPECTED: CFBundleShortVersionString=0.3'
    ' при MARKETING_VERSION=0.5)"\n'
)
PLAN_RECORD_FIXTURE = ("cutover: v3_measurements.py EXPECTED shared_xcschemes=0 стал красным "
                       "намеренно; ENABLE_HARDENED_RUNTIME = DELIBERATELY DEFERRED\n")


def good_scheme() -> str:
    return GOOD_SCHEME.replace("TARGET", TARGET_GUID).replace("CONTAINER", want_container())


# --- обратныеdry-run'ы: каждый снимает ОДНУ половину плана, ничего не пишет ----
def undo_plist(ctx: dict) -> dict:
    """Подстановки -> прежние литералы 0.3 / 1."""
    s = ctx["plist"].decode()
    back = (s.replace("<string>$(MARKETING_VERSION)</string>", "<string>0.3</string>")
            .replace("<string>$(CURRENT_PROJECT_VERSION)</string>", "<string>1</string>"))
    assert back != s, "откат plist не найден в тексте: контроль причинности бессмысленен"
    return dict(ctx, plist=back.encode())


def undo_scheme(ctx: dict) -> dict:
    return dict(ctx, scheme=None, scheme_present=False, shared=[], user=[])


def undo_runbook(ctx: dict) -> dict:
    return dict(ctx, runbook=PRE_FIX_RUNBOOK)


def undo_records(ctx: dict) -> dict:
    """Записи пакета (deferral + владение cutover) сняты, продукт-файлы как после фикса."""
    return dict(ctx, plan_text="")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    here = pathlib.Path(args.root).resolve() if args.root else None
    if here is None:
        for cand in [pathlib.Path(__file__).resolve(), *pathlib.Path(__file__).resolve().parents]:
            if (cand / PROJECT_DIR).is_dir() and (cand / ".git").exists():
                here = cand
                break
    if here is None:
        raise SystemExit("репозиторий не найден — передай --root")
    root = here
    ctx = load_inputs(root)
    got, det = measure(ctx)
    mism0 = {k: (v, got.get(k)) for k, v in EXPECTED.items() if got.get(k) != v}
    controls: dict[str, bool] = {}
    notes: dict[str, str] = {}

    # 1. plistlib, а не regex: битый XML обязан быть отвергнут
    controls["plist_rejects_truncated"] = detect_plist(ctx["plist"][: len(ctx["plist"]) // 2])["parses"] == 0
    # 2. зонд substitution обязан краснеть на литерал (обратная мутация)
    lit = detect_plist(ctx["plist"])
    inv = dict(lit["dict"])
    inv["CFBundleShortVersionString"] = "0.3"
    controls["substitution_probe_flips_on_literal"] = \
        detect_plist(plistlib.dumps(inv))["substituted"] == max(lit["substituted"] - 1, 0)
    # 3. пин «чужие ключи не тронуты» обязан краснеть на правку несвязанного ключа
    drift = dict(lit["dict"])
    drift["LSMinimumSystemVersion"] = "13.0"
    controls["untouched_guard_flips_on_unrelated_edit"] = \
        detect_plist(plistlib.dumps(drift))["nonversion_digest_ok"] == 0

    # 4. контроль честности читальщика: убранный закрывающий `};` обязан сломать
    #    баланс блоков (иначе «unbalanced==[]» ничего не значит и block-привязка
    #    держится на везении). Плюс вывод target-списка обязан дать ровно два GUID.
    tail_marker = "\t\t\tname = Release;\n\t\t};\n/* End XCBuildConfiguration section */"
    broken = ctx["pbx"].replace(tail_marker, "\t\t\tname = Release;\n/* End XCBuildConfiguration section */", 1)
    controls["reader_balance_detects_unclosed"] = (
        broken != ctx["pbx"] and detect_pbxproj(broken)["parses"] == 0
        and got["pbxproj_parses"] == 1)
    controls["reader_target_cfg_list_derived"] = (
        det["pbx"]["target_cfg_guids"] == sorted([TARGET_DEBUG_CFG, TARGET_RELEASE_CFG])
        and det["pbx"]["project_ver_in"] == 2 and det["pbx"]["project_ver_out"] == 0)

    # 5. ГЛАВНЫЙ контроль block-привязки: перенос MARKETING_VERSION из target-Release
    #    в project-Release обязан сдвинуть ОБА числа. grep -c на это не реагирует.
    mv_line = "\t\t\t\tMARKETING_VERSION = 0.5;\n"
    tgt_rel = re.search(r"\t\t800000000000000000000004 /\* Release \*/ = \{\n.*?\t\t\};\n",
                        ctx["pbx"], re.S)
    prj_rel = re.search(r"\t\t800000000000000000000002 /\* Release \*/ = \{\n.*?\t\t\};\n",
                        ctx["pbx"], re.S)
    if mv_line and tgt_rel and prj_rel and mv_line in tgt_rel.group(0):
        moved_blk = tgt_rel.group(0).replace(mv_line, "", 1)
        moved = ctx["pbx"].replace(tgt_rel.group(0), moved_blk, 1)
        prj_blk = prj_rel.group(0)
        new_prj = prj_blk.replace("\t\t\t};\n", mv_line + "\t\t\t};\n", 1)
        assert new_prj != prj_blk, "project Release buildSettings close not found"
        moved = moved.replace(prj_blk, new_prj, 1)
        pm = detect_pbxproj(moved)
        controls["marketing_moves_between_blocks"] = (
            pm["marketing_in"] == det["pbx"]["marketing_in"] - 1
            and pm["marketing_out"] == det["pbx"]["marketing_out"] + 1)
        # 6. удаление дубликата обязано уронить in-target счётчик (2 -> 1)
        dele = ctx["pbx"].replace(mv_line, "", 1)
        controls["marketing_delete_flips_count"] = \
            detect_pbxproj(dele)["marketing_in"] == det["pbx"]["marketing_in"] - 1
        notes["marketing_moved"] = {"in": pm["marketing_in"], "out": pm["marketing_out"]}
    else:
        controls["marketing_moves_between_blocks"] = False
        controls["marketing_delete_flips_count"] = False

    # 7. значение должно читаться как значение, а не как подстрока
    v6 = ctx["pbx"].replace("MARKETING_VERSION = 0.5;", "MARKETING_VERSION = 0.6;")
    controls["marketing_value_is_typed"] = detect_pbxproj(v6)["marketing_value"] == "0.6" \
        and detect_pbxproj(v6)["marketing_in"] == det["pbx"]["marketing_in"]
    # 8. отложенный ключ обязан детектироваться, если его всё же поставят; и INV-001 обязан
    #    краснить ОДНОСТОРОННЮЮ установку (только Debug), но не мешать парной (оба конфига) —
    #    иначе «симметрия» превращается в «ключа нет» и будущий change на hardening нельзя
    #    проверить вообще.
    hard = ctx["pbx"].replace("\t\t\t\tCODE_SIGN_STYLE = Manual;",
                              "\t\t\t\tCODE_SIGN_STYLE = Manual;\n\t\t\t\tENABLE_HARDENED_RUNTIME = YES;", 1)
    pm_hard = detect_pbxproj(hard)
    both = ctx["pbx"].replace("\t\t\t\tCODE_SIGN_STYLE = Manual;",
                              "\t\t\t\tCODE_SIGN_STYLE = Manual;\n\t\t\t\tENABLE_HARDENED_RUNTIME = YES;")
    pm_both = detect_pbxproj(both)
    controls["hardened_key_mutation_detected"] = (
        pm_hard["hardened_count"] == det["pbx"]["hardened_count"] + 1
        and pm_hard["target_cfg_symmetric"] == 0 and pm_hard["hardened_symmetric"] == 0
        and pm_both["hardened_count"] == det["pbx"]["hardened_count"] + 2
        and pm_both["target_cfg_symmetric"] == 1 and pm_both["hardened_symmetric"] == 1)
    # 9. запись о deferral не должна приниматься из автогенённого brief.md
    brief_only = measure(dict(ctx, plan_text=ctx["brief"],
                               plist=ctx["plist"], pbx=ctx["pbx"], v3=ctx["v3"],
                               runbook=ctx["runbook"], reports=ctx["reports"]))[0]
    controls["deferral_record_ignores_brief_echo"] = int(
        "hardened runtime" in ctx["brief"].lower() and brief_only["hardened_deferral_recorded"] == 0
        and measure(dict(ctx, plan_text=PLAN_RECORD_FIXTURE))[0]["hardened_deferral_recorded"] == 1)

    # 10. классификатор путей: user-схема не имеет права считаться shared
    controls["user_scheme_not_shared"] = (
        classify_scheme(f"{PROJECT_DIR}/{SHARED_SCHEME_DIRMARK}Exolon.xcscheme") == "shared"
        and classify_scheme(f"{PROJECT_DIR}/xcuserdata/pall/xcschemes/Exolon.xcscheme") == "user"
        and classify_scheme("Exolon.xcschem") == "other")
    # 11..17. мутации схемы: каждая обязана сдвинуть свой вердикт
    good = good_scheme()
    base_sc = detect_scheme(good.encode(), det["pbx"])
    controls["synthetic_scheme_can_be_green"] = (
        base_sc["parses"] == 1 and base_sc["is_native_target"] == 1
        and base_sc["archiving"] == 1 and base_sc["actions"] == 4
        and base_sc["flags_yes"] == 5 and base_sc["refs_missing"] == 0
        and base_sc["refs_bad_container"] == 0 and base_sc["refs_bad_name"] == 0
        and base_sc["runnable_app"] == 1 and base_sc["dangling_tests"] == 0
        and base_sc["refs_total"] == EXPECTED["scheme_buildable_refs_total"]
        and base_sc["archive_config"] == EXPECTED["scheme_archive_build_configuration"]
        and base_sc["launch_config"] == EXPECTED["scheme_launch_build_configuration"])
    bogus = good.replace(f'BlueprintIdentifier = "{TARGET_GUID}"', 'BlueprintIdentifier = "0BADBADBADBADBADBADBAD00"')
    controls["bogus_blueprint_flips"] = \
        detect_scheme(bogus.encode(), det["pbx"])["is_native_target"] == 0
    noattr = bogus.replace(' BuildableIdentifier = "primary"', "", 1)
    s_noattr = detect_scheme(noattr.encode(), det["pbx"])
    controls["missing_canon_attr_flips"] = (s_noattr["refs_missing"] >= 1
                                            and s_noattr["refs_not_primary"] >= 1)
    badcont = good.replace(want_container(), "container:Exolon.app", 1)
    controls["wrong_container_flips"] = \
        detect_scheme(badcont.encode(), det["pbx"])["refs_bad_container"] >= 1
    # 17a. регистр префикса: заглавная «Container:» — именно её пинил черновик, и на
    #      самосогласованных синтетиках это было невидимо. Здесь она обязана покраснеть
    #      по всем ссылкам сразу, иначе пин контейнера не отличает форму Xcode от выдумки.
    caps = good.replace(want_container(), "Container:%s.xcodeproj" % EXPECTED["project_name"])
    controls["container_prefix_casing_rejected"] = (
        caps != good and want_container().startswith("container:")
        and detect_scheme(caps.encode(), det["pbx"])["refs_bad_container"]
        == EXPECTED["scheme_buildable_refs_total"])
    noarch = good.replace('buildForArchiving = "YES"', 'buildForArchiving = "NO"', 1)
    controls["archiving_no_flips"] = \
        detect_scheme(noarch.encode(), det["pbx"])["archiving"] == 0
    # 17c. конфигурация архивации — не декорация: Debug вместо Release должен краснеть,
    #      иначе «scheme with an Archive action» засчитывает схему, которая архивирует не то.
    arch_dbg = good.replace('<ArchiveAction buildConfiguration = "Release"',
                            '<ArchiveAction buildConfiguration = "Debug"', 1)
    controls["archive_config_flips"] = (
        arch_dbg != good
        and detect_scheme(arch_dbg.encode(), det["pbx"])["archive_config"] == "Debug"
        and detect_scheme(arch_dbg.encode(), det["pbx"])["archiving"] == 1)
    run_rel = good.replace('<LaunchAction buildConfiguration = "Debug"',
                           '<LaunchAction buildConfiguration = "Release"', 1)
    controls["launch_config_flips"] = (
        run_rel != good
        and detect_scheme(run_rel.encode(), det["pbx"])["launch_config"] == "Release")
    withtest = good.replace("<Testables/>",
                            '<Testables><TestableReference skipped = "NO">'
                            '<BuildableReference BuildableIdentifier = "primary" '
                            'BlueprintIdentifier = "999999999999999999999999" BuildableName = "GhostTests.xctest" '
                            'BlueprintName = "GhostTests" ReferencedContainer = "%s">'
                            '</BuildableReference></TestableReference></Testables>' % want_container())
    controls["dangling_test_flips"] = (
        withtest != good
        and detect_scheme(withtest.encode(), det["pbx"])["dangling_tests"] == 1)
    controls["scheme_garbage_rejected"] = detect_scheme(b"<Scheme><oops", det["pbx"])["parses"] == 0
    # 17b. удвоенный суффикс обязан краснеть: пин литеральный, а не выведенный из glob
    dbl = good.replace(want_container(), want_container() + ".xcodeproj")   # все ссылки
    controls["container_pin_is_literal_not_derived"] = (
        dbl != good and detect_scheme(dbl.encode(), det["pbx"])["refs_bad_container"]
        == EXPECTED["scheme_buildable_refs_total"])
    # 18. отсутствие схемы должно выглядеть как red, а не как «нет данных»
    no_scheme = dict(ctx, scheme=None, scheme_present=False, shared=[], user=[])
    have_scheme = dict(ctx, scheme=good.encode(), scheme_present=True, shared=[SCHEME_REL], user=[])
    controls["absent_scheme_is_red"] = (
        measure(no_scheme)[0]["scheme_xml_parses"] == 0
        and measure(no_scheme)[0]["shared_scheme_count"] == 0
        and measure(have_scheme)[0]["scheme_xml_parses"] == 1
        and measure(have_scheme)[0]["shared_scheme_count"] == 1)

    # 19. landmine: red-состояние v3 после добавления схемы обязан владеть кто-то
    controls["cutover_needs_record"] = (
        detect_cutover(ctx["v3"], 1, "")["owned"] == 0
        and detect_cutover(ctx["v3"], 1, ctx["plan_text"])["owned"] == int("shared_xcschemes" in ctx["plan_text"])
        and detect_cutover(ctx["v3"], 0, "")["owned"] == 1)
    controls["cutover_pin_is_ast_not_grep"] = det["cut"]["v3_pin"] == 0
    # 20. пере-нацеливание runbook: новая stale-строка обязана поднять счётчик,
    #     а пустой runbook — обнулить детектор архива (иначе «archive=1» ничего не значит)
    controls["runbook_stale_flips"] = (
        detect_runbook(ctx["runbook"] + "\n# EXPECTED: no shared scheme yet\n")["stale"]
        == det["rb"]["stale"] + 1 and detect_runbook("")["archive"] == 0
        and detect_runbook("# EXPECTED: use -scheme Exolon and archive\n")["archive"] == 1
        and detect_runbook(ctx["runbook"])["stale"] == det["rb"]["stale"])
    # 21. append-only: неверный pin-обязан покраснеть (иначе «0 rewrited» ничего не значит)
    if ctx["reports"]:
        rel0 = sorted(ctx["reports"])[0]
        wrong = {k: dict(v) for k, v in ctx["reports"].items()}
        wrong[rel0]["pin_blob"] = "0" * 40
        controls["append_only_wrong_pin_flips"] = detect_reports(wrong)["mismatches"] == 1
        edited = {k: dict(v) for k, v in ctx["reports"].items()}
        edited[rel0]["worktree_blob"] = hashlib.sha1(b"blob 0\0").hexdigest()
        controls["append_only_worktree_edit_flips"] = \
            detect_reports(edited)["mismatches"] >= 1 and detect_reports(ctx["reports"])["mismatches"] == 0
    else:
        controls["append_only_wrong_pin_flips"] = False
        controls["append_only_worktree_edit_flips"] = False

    # 22. причинность зелёного вердикта. Пока дерево уже починено, сквозной dry-run
    #     «после фикса» стал бы тавтологией (он совпадает с самим деревом), поэтому
    #     контроль инвертирован: каждый из четырёх откатов плана обязан заново окрасить
    #     СВОИ AC и не задеть чужие, а полный откат обязан дать ровно объединение.
    def _red(part: dict) -> set:
        return {k for k, v in EXPECTED.items() if part.get(k) != v}

    r_plist = _red(measure(undo_plist(ctx))[0])
    r_scheme = _red(measure(undo_scheme(ctx))[0])
    r_run = _red(measure(undo_runbook(ctx))[0])
    r_rec = _red(measure(undo_records(ctx))[0])
    r_all = _red(measure(undo_records(undo_runbook(undo_scheme(undo_plist(ctx)))))[0])
    scheme_keys = {"shared_scheme_count", "shared_scheme_path_exact", "scheme_xml_parses",
                   "scheme_blueprint_is_native_target", "scheme_blueprint_guid_is_exolon",
                   "scheme_actions_required", "scheme_build_entry_flags_yes",
                   "scheme_build_for_archiving_yes", "scheme_buildable_refs_total",
                   "scheme_runnable_is_application", "scheme_archive_build_configuration",
                   "scheme_launch_build_configuration"}
    controls["undo_fix_is_red"] = (
        {"plist_version_keys_substituted", "plist_version_keys_literal"} <= r_plist
        and not (r_plist & (scheme_keys | {"runbook_stale_gap_claims",
                                           "hardened_deferral_recorded"}))
        and scheme_keys <= r_scheme
        and not (r_scheme & {"plist_version_keys_substituted", "plist_version_keys_literal",
                             "runbook_stale_gap_claims", "hardened_deferral_recorded"})
        and {"runbook_stale_gap_claims", "runbook_archive_step_present"} <= r_run
        and not (r_run & (scheme_keys | {"plist_version_keys_literal", "v3_shared_scheme_cutover_owned"}))
        and {"hardened_deferral_recorded", "v3_shared_scheme_cutover_owned"} <= r_rec
        and not (r_rec & (scheme_keys | {"plist_version_keys_literal",
                                         "runbook_archive_step_present"}))
        # v3_shared_scheme_cutover_owned в полном откате красным быть НЕ должен: без
        # схемы пин v3 (0) снова совпадает с фактом, и владения cutover никто не требует.
        and r_all == (r_plist | r_scheme | r_run | r_rec) - {"v3_shared_scheme_cutover_owned"})
    notes["undo_residual"] = json.dumps(
        {"plist": sorted(r_plist), "scheme": sorted(r_scheme), "runbook": sorted(r_run),
         "records": sorted(r_rec), "all": sorted(r_all)},
        ensure_ascii=False, default=str)[:900]

    mism = mism0
    ok = not mism and all(controls.values())
    out = {"root": root.name, "head": git(root, "rev-parse", "--short", "HEAD"),
           "branch": git(root, "rev-parse", "--abbrev-ref", "HEAD"),
           "measured": got, "controls": controls, "mismatches": mism,
           "stale_runbook_claims": det["rb"]["stale_claims"],
           "scheme_classified": {"shared": ctx["shared"], "user": ctx["user"]},
           "reports": {k: v["worktree_blob"] for k, v in ctx["reports"].items()},
           "ok": ok}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    else:
        print(f"root={root} head={out['head']} branch={out['branch']}")
        print(f"pbxproj blocks parsed={det['pbx']['parsed_objects']} "
              f"(headers={det['pbx']['header_objects']} + single-line={det['pbx']['single_line_objects']}), "
              f"XCBuildConfiguration={det['pbx']['isa_configs']}, target configs="
              f"{det['pbx']['target_config_names']}, unbalanced={det['pbx']['unbalanced']}")
        print(f"plist non-version digest={det['plist'].get('nonversion_digest', 'n/a')}")
        for k in EXPECTED:
            flag = "" if EXPECTED[k] == got.get(k) else f"   RED ожидалось {EXPECTED[k]!r}"
            print(f"{k:42} = {got.get(k)!r}{flag}")
        print(f"runbook stale claims: {det['rb']['stale_claims']}")
        print(f"schemes: shared={ctx['shared']} user={ctx['user']}")
        print("controls:")
        for k, v in controls.items():
            print(f"  {'OK ' if v else 'BAD'} {k}")
        if mism:
            print(f"mismatches: {len(mism)}")
        print("RESULT:", "RELEASE_LAYER_READY" if ok else
              f"NOT_READY (red_ac={len(mism)} bad_controls={sum(1 for v in controls.values() if not v)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
