#!/usr/bin/env python3
"""
qalore 契约一致性校验脚本。

校验三件事：
1. story 数据满足契约（assert_seq == max+1、断言类型合法、tc_count 一致）
2. 所有副本（SKILL.md / adapters / practices .md）与 contracts.json 一致
3. 单一权威源（同一语义不出现第二个"定义"）

用法：
    python3 verify-contracts.py

退出码：0 = 全部通过；1 = 存在违反契约的问题。
"""

import json
import os
import re
import sys
import glob

CONFIG_PATH = os.path.expanduser("~/.dsh/qalore-config.json")

# Windows 下 stdout/stderr 默认编码为 GBK，无法输出 ✅/❌ emoji；强制 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def load_paths():
    """从 qalore-config.json 读取 practices_path / story_path（路径约束）。"""
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    practices = cfg.get("practices_path")
    story = cfg.get("story_path")
    if not practices or not story:
        print(f"❌ qalore-config.json 缺少 practices_path / story_path：{CONFIG_PATH}")
        sys.exit(1)
    return practices, story


def load_contracts(practices):
    """加载 contracts.json。"""
    p = os.path.join(practices, "contracts.json")
    if not os.path.exists(p):
        print(f"❌ 缺少契约文件：{p}")
        sys.exit(1)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def iter_leaf_modules(modules, path=()):
    """递归遍历 modules，yield (容器链, 叶子模块字典)。

    容器（含 sub_modules）不产出，仅下钻；叶子模块（无 sub_modules）产出。
    容器链为路径组件元组（容器名... + 叶子模块名），叶子模块名 = chain[-1]。
    """
    for name, m in modules.items():
        if isinstance(m, dict) and "sub_modules" in m:
            yield from iter_leaf_modules(m["sub_modules"], path + (name,))
        else:
            yield path + (name,), m


def check_assert_seq_data(story):
    """校验 story 数据：assert_seq == max(assert ID) + 1（递归遍历叶子模块）。"""
    problems = []
    total = 0
    for jf in glob.glob(os.path.join(story, "**", "index.json"), recursive=True):
        with open(jf, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("kind") == "product_router":
            continue
        base = os.path.dirname(jf)
        rel = os.path.relpath(jf, story)
        for chain, m in iter_leaf_modules(d.get("modules", {})):
            if "assert_seq" not in m:
                continue
            total += 1
            mx = 0
            mdir = os.path.join(base, *chain)
            for mf in glob.glob(os.path.join(mdir, "*-功能-*.md")):
                with open(mf, encoding="utf-8") as f:
                    ids = re.findall(r"\[assert-[A-Z]+-(\d+)\]", f.read())
                if ids:
                    mx = max(mx, max(int(x) for x in ids))
            expect = mx + 1
            if m["assert_seq"] != expect:
                problems.append(f"[assert_seq 数据] {rel}/{'/'.join(chain)}: assert_seq={m['assert_seq']}, 应为 {expect}")
    return total, problems


def check_assertion_types(story, contracts):
    """校验 story 里实际使用的断言类型都在 contracts 定义范围内。"""
    problems = []
    defined = set(contracts["assertion_types"]["types"])
    # count 与 types 实际数量必须一致（防止加类型忘 bump count）
    declared_count = contracts["assertion_types"].get("count")
    if declared_count is not None and declared_count != len(defined):
        problems.append(f"[断言类型] contracts count={declared_count} != types 实际 {len(defined)}")
    used = set()
    for f in glob.glob(os.path.join(story, "**", "*.md"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            txt = fh.read()
        for m in re.findall(r"→ 断言：([a-z-]+)\(", txt):
            used.add(m)
    undefined = used - defined
    if undefined:
        problems.append(f"[断言类型] story 使用了未定义类型：{sorted(undefined)}")
    return len(used), problems


def check_assert_seq_copies(practices, skill, contracts):
    """校验 assert_seq 语义副本：所有出现点语义应与 contracts 一致（max+1）。"""
    problems = []
    skill_dir = skill if skill else ""
    roots = [practices]
    if skill_dir:
        roots.append(skill_dir)

    # 旧语义特征（"最大序号"且无 +1）——需要人工语义判断，脚本只做启发式提示
    for root in roots:
        for f in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
            # 跳过 changelog 历史数据
            if "changelog" in f.lower():
                continue
            with open(f, encoding="utf-8") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines):
                # 检测"初始为 0"（旧语义：最大序号从 0 起）
                if "assert_seq" in line and "初始为 0" in line:
                    problems.append(f"[assert_seq 副本] {os.path.relpath(f, '/')}:{i+1} 仍是旧语义（初始为 0，应为初始 1）")
                # 检测"当前最大序号"（旧语义）
                if "assert_seq" in line and "当前最大序号" in line and "已分配的最大" not in line:
                    pass  # 留给人审，启发式不强
    return problems


def check_assertion_type_copies(practices, skill, contracts):
    """校验断言类型计数的副本一致性。"""
    problems = []
    expected_count = contracts["assertion_types"]["count"]
    skill_dir = skill if skill else ""

    # 检查 cases.md / execution.md / handbook.md / qa-execution / qa-functional-test 里的"N 种"引用
    targets = [
        os.path.join(practices, "tech-stacks", "functional", "cases.md"),
        os.path.join(practices, "tech-stacks", "functional", "execution.md"),
        os.path.join(practices, "common", "handbook.md"),
        os.path.join(skill_dir, "capability", "qa-execution", "SKILL.md"),
        os.path.join(skill_dir, "capability", "qa-functional-test", "SKILL.md"),
    ]
    for f in targets:
        if not os.path.exists(f):
            continue
        with open(f, encoding="utf-8") as fh:
            txt = fh.read()
        # 找"定义的 N 种范围内"或"N 种断言"等
        counts = re.findall(r"(\d+)\s*种(?:范围|断言)", txt)
        for c in counts:
            if int(c) != expected_count:
                problems.append(f"[断言类型计数] {os.path.relpath(f, '/')} 声明 {c} 种，应为 {expected_count} 种")
    return problems


def check_counting_formulas(story):
    """校验计数字段：tc_count / pending_count 与源数据一致（审计步骤4 C，递归遍历叶子模块）。"""
    problems = []
    total = 0
    for jf in glob.glob(os.path.join(story, "**", "index.json"), recursive=True):
        with open(jf, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("kind") == "product_router":
            continue
        base = os.path.dirname(jf)
        rel = os.path.relpath(jf, story)
        for chain, m in iter_leaf_modules(d.get("modules", {})):
            st = m.get("status", {})
            mname = chain[-1]
            mdir = os.path.join(base, *chain)

            # tc_count ← TC 文件「用例 ID：」行数
            if "tc_count" in st:
                total += 1
                tcfile = os.path.join(mdir, f"{mname}-功能-测试用例.md")
                actual = 0
                if os.path.exists(tcfile):
                    with open(tcfile, encoding="utf-8") as fh:
                        actual = sum(1 for ln in fh if ln.startswith("用例 ID："))
                if actual != st["tc_count"]:
                    problems.append(
                        f"[tc_count] {rel}/{'/'.join(chain)}: 声明 {st['tc_count']}, 实际 {actual}"
                    )

            # pending_count ← BL + CL 中 [pending] 行数
            if "pending_count" in st:
                pend = 0
                for kind in ("业务逻辑", "代码逻辑"):
                    p = os.path.join(mdir, f"{mname}-功能-{kind}.md")
                    if os.path.exists(p):
                        with open(p, encoding="utf-8") as fh:
                            pend += sum(1 for ln in fh if "[pending]" in ln)
                if pend != st["pending_count"]:
                    problems.append(
                        f"[pending_count] {rel}/{'/'.join(chain)}: 声明 {st['pending_count']}, 实际 {pend}"
                    )

            # BL/CL 头「断言：N 条」← 文件实际 [assert- 行数（contracts counting_formulas.bl/cl_header_assertions）
            for kind in ("业务逻辑", "代码逻辑"):
                p = os.path.join(mdir, f"{mname}-功能-{kind}.md")
                if os.path.exists(p):
                    with open(p, encoding="utf-8") as fh:
                        lines = fh.readlines()
                    actual_assert = sum(1 for ln in lines if "[assert-" in ln)
                    header_decl = None
                    for ln in lines[:3]:
                        m2 = re.search(r"断言：(\d+) 条", ln)
                        if m2:
                            header_decl = int(m2.group(1))
                            break
                    if header_decl is not None and header_decl != actual_assert:
                        problems.append(
                            f"[header_assertions] {rel}/{'/'.join(chain)}/{kind}: 头部声明 {header_decl}, 实际 {actual_assert}"
                        )

            # TC 头「用例总数：N 条」← 文件实际「用例 ID：」行数（contracts counting_formulas.tc_header_total）
            tcfile = os.path.join(mdir, f"{mname}-功能-测试用例.md")
            if os.path.exists(tcfile):
                with open(tcfile, encoding="utf-8") as fh:
                    lines = fh.readlines()
                actual_tc = sum(1 for ln in lines if ln.startswith("用例 ID："))
                header_decl = None
                for ln in lines[:3]:
                    m2 = re.search(r"用例总数：(\d+) 条", ln)
                    if m2:
                        header_decl = int(m2.group(1))
                        break
                if header_decl is not None and header_decl != actual_tc:
                    problems.append(
                        f"[header_tc_total] {rel}/{'/'.join(chain)}/{mname}: 头部声明 {header_decl}, 实际 {actual_tc}"
                    )
    return total, problems


def check_id_rules(story, contracts):
    """校验 ID 规则：tc_prefix / mm_short_id 格式 + TC ID 格式与唯一性（审计步骤4/5，递归遍历叶子模块）。"""
    problems = []
    id_rules = contracts["id_rules"]
    for jf in glob.glob(os.path.join(story, "**", "index.json"), recursive=True):
        with open(jf, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("kind") == "product_router":
            continue
        base = os.path.dirname(jf)
        rel = os.path.relpath(jf, story)
        for chain, m in iter_leaf_modules(d.get("modules", {})):
            mname = chain[-1]
            tp = m.get("tc_prefix")
            if tp is not None and not re.fullmatch(r"[A-Z]{2,5}", tp):
                problems.append(f"[tc_prefix] {rel}/{'/'.join(chain)}: '{tp}' 不符合 {id_rules['tc_prefix']}")

            msid = m.get("mm_short_id")
            if msid is not None:
                if not re.fullmatch(r"[a-z]{2,5}", msid):
                    problems.append(f"[mm_short_id] {rel}/{'/'.join(chain)}: '{msid}' 不符合 {id_rules['mm_short_id']}")
                elif tp and msid != tp.lower():
                    problems.append(f"[mm_short_id] {rel}/{'/'.join(chain)}: '{msid}' != tc_prefix 小写 '{tp.lower()}'")

            tcfile = os.path.join(base, *chain, f"{mname}-功能-测试用例.md")
            if os.path.exists(tcfile):
                with open(tcfile, encoding="utf-8") as fh:
                    seqs = []
                    for ln in fh:
                        if ln.startswith("用例 ID："):
                            tid = ln.strip().split("：", 1)[1].strip()
                            mtc = re.fullmatch(r"TC-([A-Z]{2,5})-(\d+)", tid)
                            if not mtc:
                                problems.append(f"[tc_id_format] {rel}/{'/'.join(chain)}: '{tid}' 不符合 TC-{{PREFIX}}-{{seq}}")
                            else:
                                if tp and mtc.group(1) != tp:
                                    problems.append(f"[tc_id_format] {rel}/{'/'.join(chain)}: '{tid}' 前缀 {mtc.group(1)} != tc_prefix {tp}")
                                seqs.append(int(mtc.group(2)))
                    if len(seqs) != len(set(seqs)):
                        problems.append(f"[tc_id_continuity] {rel}/{'/'.join(chain)}: 存在重复用例序号")
    return problems


def check_index_version_consistency(practices, story):
    """校验 index.json version == changelog[0].version（审计步骤1 F 第2项）。"""
    problems = []
    idx = os.path.join(practices, "index.json")
    with open(idx, encoding="utf-8") as f:
        p = json.load(f)
    if p.get("version") and p.get("changelog"):
        if p["version"] != p["changelog"][0]["version"]:
            problems.append(
                f"[version] practices/index.json: version={p['version']} != changelog[0]={p['changelog'][0]['version']}"
            )
    for jf in glob.glob(os.path.join(story, "**", "index.json"), recursive=True):
        with open(jf, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("kind") == "product_router":
            continue
        if "version" in d or "changelog" in d:
            first = (d.get("changelog") or [{}])[0].get("version")
            if d.get("version") != first:
                problems.append(f"[version] {os.path.relpath(jf, story)}: version 与 changelog[0] 不一致")
    return problems


def check_dependencies(story, contracts):
    """校验依赖登记：prod 排除 + 秘密脱敏 + 写 mock 确认标记（审计步骤：依赖一致性）。"""
    problems = []
    total = 0
    dep_files = glob.glob(os.path.join(story, "**", "dependencies.json"), recursive=True)
    for df in dep_files:
        total += 1
        rel = os.path.relpath(df, story)
        try:
            with open(df, encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            problems.append(f"[dependencies] {rel}: JSON 解析失败：{e}")
            continue
        # prod 排除：environment.id == prod ⟹ executable == false
        for env in d.get("environments", []):
            if env.get("id") == "prod" and env.get("executable") is True:
                problems.append(f"[dependencies] {rel}: 环境 'prod' 的 executable 为 true，违反 prod_exclusion")
            # 可执行环境：executable == true ⟹ web_url 非空
            if env.get("executable") is True and not env.get("web_url"):
                problems.append(f"[dependencies] {rel}: 环境 '{env.get('id', '?')}' executable 为 true 但 web_url 为空，违反 executable_env")
        # 凭证解析格式：credential_ref 必须 secret: 前缀且非空
        for env in d.get("environments", []):
            for acc in env.get("accounts", []):
                cref = acc.get("credential_ref", "")
                if cref and (not cref.startswith("secret:") or cref.strip() == "secret:"):
                    problems.append(f"[dependencies] {rel}: 账号 '{acc.get('label', '?')}' credential_ref 格式非法（须 secret:{{项目}}/{{账号名}}）：{cref[:20]}")
        # 秘密脱敏：键名含 password/token/secret/credential/passwd 且值为明文 → 泄漏
        def scan_secrets(obj, path=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    scan_secrets(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    scan_secrets(v, f"{path}[{i}]")
            elif isinstance(obj, str):
                key = path.split(".")[-1].split("[")[0].lower()
                if any(s in key for s in ("password", "token", "secret", "credential", "passwd")):
                    if obj and not obj.startswith("secret:") and "{{" not in obj:
                        problems.append(f"[dependencies] {rel}: {path} 疑似明文秘密：{obj[:20]}...")
        scan_secrets(d)
        # 写 mock 确认标记（权限左移：未确认的写 mock 非法）
        for wm in d.get("write_mocks", []):
            if not wm.get("confirmed_by") or not wm.get("confirmed_date"):
                problems.append(f"[dependencies] {rel}: 写 mock '{wm.get('id', '?')}' 缺确认标记（confirmed_by/confirmed_date）")
        # DB 连接闭环：TC 文件 db 断言的「连接」参数必须存在于 databases[].ref
        refs = set()
        for env in d.get("environments", []):
            for db in env.get("databases", []):
                if db.get("ref"):
                    refs.add(db["ref"])
        base = os.path.dirname(df)
        for tc in glob.glob(os.path.join(base, "**", "*-功能-测试用例.md"), recursive=True):
            with open(tc, encoding="utf-8") as f:
                txt = f.read()
            for m in re.findall(r"db-(?:field-value|row-count)\(([^,)]+)", txt):
                conn = m.strip().strip('"').strip("'")
                if conn and conn not in refs:
                    problems.append(f"[dependencies] {rel}: DB 断言引用连接 '{conn}' 不在 databases[].ref 中，违反 db_connection_closure")
    return total, problems


def check_external_tools(contracts):
    """校验 external_tools：probe 必填（硬校验）；cli 类工具跨平台探测（软报告，不阻断）。"""
    import shutil
    problems = []
    tools = contracts.get("external_tools", {}).get("tools", {})
    for name, t in tools.items():
        probe = t.get("probe")
        if not probe:
            problems.append(f"[external_tools] {name} 缺 probe 字段（违反 probe_required）")
            continue
        if t.get("type") == "cli":
            if name == "python3":
                ok = True  # verify 本身由 python 解释器运行，python 必然可用
            else:
                ok = shutil.which(probe) is not None
            print(f"    · {name}: {probe} → {'✅ 可用' if ok else '❌ 不可用（首次使用需安装）'}")
    return len(tools), problems


def check_environment_qualifier(story):
    """校验 '@档位' 后缀：story 断言使用的档位须在 dependencies.json 的 device_profiles 内声明。"""
    problems = []
    declared = set()
    for df in glob.glob(os.path.join(story, "**", "dependencies.json"), recursive=True):
        with open(df, encoding="utf-8") as f:
            d = json.load(f)
        for env in d.get("environments", []):
            for p in env.get("device_profiles", []):
                if isinstance(p, dict) and p.get("id"):
                    declared.add(p["id"])
    if not declared:
        return 0, problems
    used = set()
    for f in glob.glob(os.path.join(story, "**", "*.md"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            txt = fh.read()
        for m in re.findall(r"→ 断言：.*?@([a-zA-Z0-9_-]+)", txt):
            used.add(m)
    undefined = used - declared
    if undefined:
        problems.append(f"[@档位] story 使用了未声明的档位：{sorted(undefined)}（应在 dependencies.json device_profiles 声明）")
    return len(used), problems


def check_audit_alignment(practices):
    """校验 audit 依赖图对齐版本 == practices index.json version（双螺旋版本锚点）。

    qalore practices 每次 version 升级后，audit 的 dependency-map.md 头部「对齐版本」
    必须同步更新，否则 audit 依赖图落后于 qalore，下次审查会漏检 gap 版本新增的 feature。
    本检查让这个 gap 由机器自动暴露，而非靠人工审查发现。
    """
    problems = []
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    audit_path = cfg.get("audit_path")
    if not audit_path:
        problems.append("[audit] qalore-config.json 缺少 audit_path，无法校验依赖图对齐版本")
        return 0, problems
    dm = os.path.join(audit_path, "qalore-audit", "dependency-map.md")
    if not os.path.exists(dm):
        problems.append(f"[audit] 依赖图不存在：{dm}")
        return 0, problems
    with open(os.path.join(practices, "index.json"), encoding="utf-8") as f:
        p = json.load(f)
    pv = p.get("version")
    with open(dm, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r"对齐版本\*\*[：:]\s*`([0-9]{4}-[0-9]{2}-[0-9]{2}-v[0-9]+)`", content)
    if not m:
        problems.append(f"[audit] 依赖图头部缺少「对齐版本」声明：{dm}")
        return 0, problems
    av = m.group(1)
    if pv != av:
        problems.append(f"[audit] 依赖图对齐版本 {av} ≠ practices version {pv}（gap：qalore 已更新，audit 依赖图未同步）")
    # audit 版本（自声明演进版本）也必须存在且格式正确，防止被误删或改坏
    m2 = re.search(r"audit 版本\*\*[：:]\s*`([0-9]{4}-[0-9]{2}-[0-9]{2}-v[0-9]+)`", content)
    if not m2:
        problems.append(f"[audit] 依赖图头部缺少「audit 版本」声明：{dm}")
    return 1, problems


def check_module_group_structure(story):
    """校验 module_group 结构不变式（contracts.json#module_group）：kind↔sub_modules↔tc_prefix 互斥一致。"""
    problems = []
    total = 0
    for jf in glob.glob(os.path.join(story, "**", "index.json"), recursive=True):
        with open(jf, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("kind") == "product_router":
            continue
        rel = os.path.relpath(jf, story)

        def walk(modules, path=()):
            nonlocal total
            for name, m in modules.items():
                chain = "/".join(path + (name,))
                if "sub_modules" in m:
                    total += 1
                    if m.get("kind") != "module_group":
                        problems.append(f"[module_group] {rel}/{chain}: 有 sub_modules 但 kind != 'module_group'")
                    for forbidden in ("tc_prefix", "mm_short_id", "assert_seq", "status"):
                        if forbidden in m:
                            problems.append(f"[module_group] {rel}/{chain}: 容器不得含 {forbidden}")
                    walk(m["sub_modules"], path + (name,))
                else:
                    if m.get("kind") == "module_group":
                        problems.append(f"[module_group] {rel}/{chain}: kind='module_group' 但无 sub_modules")

        walk(d.get("modules", {}))
    return total, problems


def check_assertion_semantics(story):
    """断言语义弱启发式（非阻断）：message-contains 疑似字段标签误用 + api-field-value 嵌套语法。

    注意：这是弱启发式，不承诺 100% 拦截。message-contains 是「toast 专用」，字段标签/详情/Tab
    应用 element-text（语义权威见 execution.md）。此检查只做关键词级提示，供人工复核。
    """
    warnings = []
    field_keywords = ["字段", "标签", "详情", "次数", "来源", "版本", "状态", "Tab", "tab"]
    for f in glob.glob(os.path.join(story, "**", "*.md"), recursive=True):
        with open(f, encoding="utf-8") as fh:
            txt = fh.read()
        for m in re.finditer(r"message-contains\(\s*[\"']([^\"']+)[\"']\s*\)", txt):
            arg = m.group(1)
            if any(k in arg for k in field_keywords):
                warnings.append(f"[断言语义] {os.path.relpath(f, story)}: message-contains(\"{arg}\") 疑似字段标签误用（应用 element-text）")
        for m in re.finditer(r"api-field-value\([^,]+,\s*[\"']([^\"']+)[\"']", txt):
            path = m.group(1)
            if ("[" in path or "]" in path) and path.count("[") != path.count("]"):
                warnings.append(f"[断言语义] {os.path.relpath(f, story)}: api-field-value 嵌套路径括号不配对：\"{path}\"")
    return len(warnings), warnings


def check_data_fixtures_defects(story, contracts):
    """校验依赖登记扩展：data_fixtures（factory_id 引用/枚举/fingerprint）+ defects（必填字段）。

    机器可判定不变式见 contracts.json#data_fixtures 与 contracts.json#defects。
    """
    problems = []
    total = 0
    valid_states = {"active", "stale", "cleaned"}
    valid_accept = {"pending", "accepted", "rejected"}
    valid_channels = {"api", "ui", "db"}
    for df in glob.glob(os.path.join(story, "**", "dependencies.json"), recursive=True):
        rel = os.path.relpath(df, story)
        try:
            with open(df, encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            continue
        fixtures = d.get("data_fixtures", {})
        if not isinstance(fixtures, dict):
            problems.append(f"[data_fixtures] {rel}: data_fixtures 应为对象")
            continue
        if not fixtures:
            continue
        total += 1
        factories = fixtures.get("factories", [])
        factory_ids = {x.get("id") for x in factories if isinstance(x, dict) and x.get("id")}
        for fc in factories:
            if isinstance(fc, dict) and fc.get("channel") and fc["channel"] not in valid_channels:
                problems.append(f"[data_fixtures] {rel}: factory '{fc.get('id')}' channel 非法：{fc['channel']}")
        for inst in fixtures.get("instances", []):
            if not isinstance(inst, dict):
                continue
            iid = inst.get("id", "?")
            fid = inst.get("factory_id")
            if fid and fid not in factory_ids:
                problems.append(f"[data_fixtures] {rel}: instance '{iid}' 的 factory_id '{fid}' 不存在")
            if inst.get("state") and inst["state"] not in valid_states:
                problems.append(f"[data_fixtures] {rel}: instance '{iid}' state 非法：{inst['state']}")
            if inst.get("acceptance_status") and inst["acceptance_status"] not in valid_accept:
                problems.append(f"[data_fixtures] {rel}: instance '{iid}' acceptance_status 非法：{inst['acceptance_status']}")
            fp = inst.get("fingerprint")
            if not (isinstance(fp, dict) and fp):
                problems.append(f"[data_fixtures] {rel}: instance '{iid}' fingerprint 缺失或为空")
        for defect in d.get("defects", []):
            if not isinstance(defect, dict):
                continue
            for req in ("bug_id", "source", "status"):
                if not defect.get(req):
                    problems.append(f"[defects] {rel}: 缺陷缺必填字段 {req}")
    return total, problems


def main():
    practices, story = load_paths()
    contracts = load_contracts(practices)
    skill = os.path.expanduser("~/.dsh/skills/qalore")

    print("=" * 60)
    print("qalore 契约一致性校验")
    print(f"  practices: {practices}")
    print(f"  story:     {story}")
    print(f"  contracts: {contracts['contracts_version']}")
    print("=" * 60)

    all_problems = []

    # 1. assert_seq 数据
    total, probs = check_assert_seq_data(story)
    print(f"\n[1] assert_seq 数据（{total} 模块）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 2. 断言类型数据
    used, probs = check_assertion_types(story, contracts)
    print(f"[2] 断言类型数据（{used} 种在用）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 3. assert_seq 副本语义
    probs = check_assert_seq_copies(practices, skill, contracts)
    print(f"[3] assert_seq 副本语义: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 4. 断言类型计数副本
    probs = check_assertion_type_copies(practices, skill, contracts)
    print(f"[4] 断言类型计数副本: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 5. 计数字段（tc_count / pending_count）
    total, probs = check_counting_formulas(story)
    print(f"[5] 计数字段（{total} 模块）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 6. ID 规则（tc_prefix / mm_short_id / TC ID）
    probs = check_id_rules(story, contracts)
    print(f"[6] ID 规则: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 7. index.json 版本一致性
    probs = check_index_version_consistency(practices, story)
    print(f"[7] index.json 版本一致性: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 8. 依赖登记一致性（prod 排除 / 秘密脱敏 / 写 mock 确认标记）
    total, probs = check_dependencies(story, contracts)
    print(f"[8] 依赖登记（{total} 个项目）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 9. 外部工具（probe 必填 + cli 探测）
    total, probs = check_external_tools(contracts)
    print(f"[9] 外部工具（{total} 个）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 10. @档位合法性
    total, probs = check_environment_qualifier(story)
    print(f"[10] @档位（{total} 处使用）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 11. audit 依赖图版本对齐（双螺旋版本锚点）
    total, probs = check_audit_alignment(practices)
    print(f"[11] audit 依赖图对齐: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 12. module_group 结构不变式（kind↔sub_modules↔tc_prefix 互斥）
    total, probs = check_module_group_structure(story)
    print(f"[12] module_group 结构（{total} 个容器）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    # 13. 断言语义启发式（非阻断，弱启发式提示）
    total, warns = check_assertion_semantics(story)
    print(f"[13] 断言语义启发式（{total} 处提示）: {'无提示' if not warns else '发现提示（非阻断，供人工复核）'}")

    # 14. data_fixtures + defects 结构一致性
    total, probs = check_data_fixtures_defects(story, contracts)
    print(f"[14] 资源/缺陷登记（{total} 个项目）: {'✅' if not probs else '❌'}")
    all_problems.extend(probs)

    print("\n" + "=" * 60)
    if warns:
        print("\n· 断言语义提示（非阻断）：")
        for w in warns:
            print(f"  {w}")
    if all_problems:
        print(f"\n❌ {len(all_problems)} 个问题：")
        for p in all_problems:
            print(f"  {p}")
        sys.exit(1)
    else:
        print("✅ 全部契约校验通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
