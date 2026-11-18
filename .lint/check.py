import argparse
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
POLICY = ".lint/policy.toml"
ROOT_MARKDOWN = {"AGENTS.md", "README.md", "task-doing.md", "task-done.md"}
CONTEXT_FILES = {"profile.md", "taste.md", "output_contract.md"}
DISCOVERY_NAME = re.compile(r"([0-9]{3})_([^_\s][^\s]*)")
CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml"}
PROTECTED = {
    "discovery": {"experiments", "paper"},
    "experiment": {"paper"},
    "writing": set(),
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def split_paths(data):
    return {os.fsdecode(path) for path in data.split(b"\0") if path}


def read_tree(ref):
    entries = {}
    for record in git("ls-tree", "-rtz", ref).split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode = metadata.split()[0]
            entries[os.fsdecode(path)] = {
                b"040000": "dir", b"100644": "file", b"100755": "file",
            }.get(mode, "other")
    return entries


def local_entries():
    paths = list(ROOT.iterdir())
    entries = {}
    while paths:
        path = paths.pop()
        relative = path.relative_to(ROOT).as_posix()
        if relative == ".git" or (relative == ".venv" and path.is_dir() and not path.is_symlink()):
            continue
        if path.is_symlink():
            entries[relative] = "other"
        elif path.is_dir():
            entries[relative] = "dir"
            # Only descend where structure is checked, through the first level of runs/.
            parts = PurePosixPath(relative).parts
            if relative == "context" or (
                parts[0] == "AI-discover"
                and (len(parts) < 3 or (len(parts) == 3 and parts[-1] == "runs"))
            ):
                paths.extend(path.iterdir())
        else:
            entries[relative] = "file" if path.is_file() else "other"
    return entries


def read_policy(data):
    policy = tomllib.loads(data.decode())
    phase = policy.get("phase")
    if not isinstance(phase, str) or phase not in PROTECTED:
        raise ValueError(f"{POLICY} 必须指定 discovery、experiment 或 writing")
    roots = policy.get("allowed_root_entries")
    if not isinstance(roots, list) or any(
        not isinstance(name, str) or name in {"", ".", ".."} or "/" in name for name in roots
    ):
        raise ValueError(f"{POLICY} 的 allowed_root_entries 必须是顶层名称列表")
    return policy


def children(entries):
    by_parent = {}
    for path, kind in sorted(entries.items()):
        parent, _, name = path.rpartition("/")
        by_parent.setdefault(parent, {})[name] = kind
    return by_parent


def expected_files(actual, expected, prefix):
    for name in sorted(expected):
        if actual.get(name) != "file":
            yield f"缺少普通文件 {prefix}{name}"
    for name in sorted(actual.keys() - expected):
        yield f"{prefix}{name} 不在允许清单中"


def discovery_numbers(names):
    return {
        name: int(match[1])
        for name in names
        if (match := DISCOVERY_NAME.fullmatch(name))
    }


def check_structure(entries, policy, base, base_entries):
    folders = children(entries)
    root = folders.get("", {})
    for name in sorted(root.keys() - set(policy["allowed_root_entries"])):
        yield f"顶层新增 {name}，须先取得用户批准并更新 {POLICY}"
    markdown = {name: kind for name, kind in root.items() if name.lower().endswith(".md")}
    yield from expected_files(markdown, ROOT_MARKDOWN, "")
    yield from expected_files(folders.get("context", {}), CONTEXT_FILES, "context/")

    discoveries = folders.get("AI-discover", {})
    if discoveries.get("README.md") != "file":
        yield "缺少普通文件 AI-discover/README.md"
    numbers = discovery_numbers(discoveries)
    used = set()
    for name, kind in discoveries.items():
        if name == "README.md":
            continue
        path = f"AI-discover/{name}"
        if name not in numbers or kind != "dir":
            yield f"{path} 必须是 NNN_主题 格式的目录"
            continue
        if numbers[name] in used:
            yield f"{path} 使用了重复编号 {numbers[name]:03d}"
        used.add(numbers[name])
        contents = folders.get(path, {})
        if contents.get("research.md") != "file":
            yield f"缺少普通文件 {path}/research.md"
        for item, item_kind in contents.items():
            if item in {"scripts", "runs"} and item_kind == "dir":
                continue
            markdown_allowed = item == "research.md" or (name == "000_example" and item == "README.md")
            if item_kind == "file" and (markdown_allowed or Path(item).suffix in CONFIG_SUFFIXES):
                continue
            yield f"{path}/{item} 不符合探究目录结构"
        for run, run_kind in folders.get(f"{path}/runs", {}).items():
            if run_kind != "dir":
                yield f"{path}/runs/{run} 必须是运行目录"

    previous = children(base_entries).get("AI-discover", {})
    new_numbers = sorted(number for name, number in numbers.items() if name not in previous)
    if new_numbers:
        history = split_paths(git("log", "--format=", "--name-only", "--no-renames", "-z", base, "--", "AI-discover"))
        historical_dirs = {path.split("/")[1] for path in history if path.count("/") >= 2}
        largest = max(discovery_numbers(historical_dirs | previous.keys()).values(), default=0)
        expected = list(range(largest + 1, largest + len(new_numbers) + 1))
        if new_numbers != expected:
            yield f"AI-discover 新目录须从 {largest + 1:03d} 连续编号，实际编号为 {new_numbers}"


def main():
    parser = argparse.ArgumentParser(description="检查项目结构和研究阶段的写入范围")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--staged", action="store_true", help="检查即将提交的内容")
    modes.add_argument("--base", help="检查从指定 Git 基线到 HEAD 的提交内容")
    args = parser.parse_args()
    base = args.base or "HEAD"

    if args.staged or args.base:
        target = git("write-tree").decode().strip() if args.staged else "HEAD"
        entries = read_tree(target)
        policy = read_policy(git("show", f"{target}:{POLICY}"))
        changed = split_paths(git("diff", "--name-only", "--no-renames", "-z", base, target, "--"))
    else:
        entries = local_entries()
        policy = read_policy((ROOT / POLICY).read_bytes())
        changed = split_paths(git("diff", "--name-only", "--no-renames", "-z", base, "--"))
        changed |= split_paths(git("ls-files", "--others", "--exclude-standard", "-z"))

    base_entries = read_tree(base)
    errors = list(check_structure(entries, policy, base, base_entries))
    # The initial policy installation has no previously authorized phase.
    if POLICY in base_entries:
        phase = read_policy(git("show", f"{base}:{POLICY}"))["phase"]
        errors.extend(
            f"{phase} 阶段禁止修改 {path}"
            for path in sorted(changed)
            if path.partition("/")[0] in PROTECTED[phase]
        )
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("项目结构和阶段检查通过")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"项目检查无法完成：{error}") from error
