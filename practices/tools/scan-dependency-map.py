#!/usr/bin/env python3
"""
qalore 依赖图机器扫描脚本（审计方案 3）。

扫描 skill 包 + practices 中的显式引用关系，生成「机器可推导的依赖图」（machine graph），
用于与人工维护的 dependency-map.md 交叉校验（verify-contracts.py 第 18 项为轻量版校验，
本脚本产出完整机器图供人工比对）。

扫描规则：
  1. practices_min_version（capability SKILL.md frontmatter）→ capability 消费 practices
  2. tech-stacks/common/schemas/tools 路径引用 → 消费方引用 practices 文件
  3. 「章节名」引用 → 消费方引用 handbook/tech-stacks 章节

已废弃目录/文件（qa-token-report）不扫描。
"""

import json
import os
import re
import sys
import glob

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

CONFIG_PATH = os.path.expanduser("~/.dsh/qalore-config.json")
DEPRECATED = ["qa-token-report"]


def load_paths():
    with open(CONFIG_PATH, encoding="utf-8-sig") as f:
        cfg = json.load(f)
    return cfg.get("practices_path"), cfg.get("story_path"), cfg.get("audit_path")


def _skip(path):
    return any(d in path for d in DEPRECATED)


def scan(practices, skill_dir):
    """扫描并返回 sorted list of (consumer, producer, kind)。"""
    edges = set()

    # 1. practices_min_version → capability 消费 practices
    for sk in glob.glob(os.path.join(skill_dir, "capability", "**", "SKILL.md"), recursive=True):
        if _skip(sk):
            continue
        with open(sk, encoding="utf-8") as f:
            txt = f.read()
        m = re.search(r"name:\s*(\S+)", txt)
        mm = re.search(r"practices_min_version:\s*[\"']?([^\"'\n]+)", txt)
        if m and mm:
            edges.add((m.group(1), "practices/index.json", "practices_min_version"))

    # 2. practices 文件路径引用
    for root, base in ((skill_dir, skill_dir), (practices, practices)):
        for f in glob.glob(os.path.join(root, "**", "*.md"), recursive=True):
            if _skip(f):
                continue
            rel = os.path.relpath(f, base).replace("\\", "/")
            with open(f, encoding="utf-8") as fh:
                txt = fh.read()
            for p in re.findall(r"(?:tech-stacks|common|schemas|tools)/[a-zA-Z0-9_\-./]+\.(?:md|py|json)", txt):
                edges.add((rel, p, "path_ref"))

    # 3. 「章节名」引用（噪声较大，v1 暂不纳入机器图；章节级依赖由 path_ref 间接覆盖）
    return sorted(edges)


def main():
    practices, _story, _audit = load_paths()
    skill_dir = os.path.expanduser("~/.dsh/skills/qalore")
    if not practices or not os.path.isdir(skill_dir):
        print("❌ 路径缺失：请检查 ~/.dsh/qalore-config.json 与 skill 目录")
        sys.exit(1)
    edges = scan(practices, skill_dir)
    print(f"机器依赖图（{len(edges)} 条边）：")
    for consumer, producer, kind in edges:
        print(f"  {consumer}  ->  {producer}  [{kind}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
