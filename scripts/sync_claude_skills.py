#!/usr/bin/env python3
"""Import skills from ~/.claude/skills into this marketplace.

Git-backed skill collections are added as submodules at their current commit.
Other skill directories are copied while preserving symlinks.  The marketplace
manifest is regenerated from the imported directories and their manifests.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / ".claude" / "skills"
TARGET_ROOT = REPO_ROOT / "skills"
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def run(command: list[str], *, cwd: Path = REPO_ROOT, capture: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
    )
    return result.stdout.strip() if capture else ""


def is_git_checkout(path: Path) -> bool:
    try:
        top_level = Path(run(["git", "-C", str(path), "rev-parse", "--show-toplevel"]))
        return top_level.resolve() == path.resolve() and (path / ".git").exists()
    except subprocess.CalledProcessError:
        return False


def source_git_info(path: Path) -> tuple[str | None, str]:
    commit = run(["git", "-C", str(path), "rev-parse", "HEAD"])
    try:
        remote = run(["git", "-C", str(path), "config", "--get", "remote.origin.url"])
    except subprocess.CalledProcessError:
        remote = ""
    return remote or None, commit


def tracked_as_submodule(path: Path) -> bool:
    relative = path.relative_to(REPO_ROOT).as_posix()
    try:
        stage = run(["git", "ls-files", "--stage", "--", relative])
    except subprocess.CalledProcessError:
        return False
    return any(line.startswith("160000 ") for line in stage.splitlines())


def import_git_checkout(source: Path, target: Path, dry_run: bool) -> None:
    remote, commit = source_git_info(source)
    if remote is None:
        raise RuntimeError(f"{source} is a git checkout without an origin remote")

    relative_target = target.relative_to(REPO_ROOT).as_posix()
    already_registered = tracked_as_submodule(target)
    if already_registered and not (target / ".git").exists():
        print(f"initialize submodule {relative_target}")
        if not dry_run:
            run(["git", "submodule", "update", "--init", "--", relative_target], capture=False)
    elif not target.exists():
        print(f"submodule {relative_target} <- {remote} @ {commit[:12]}")
        if not dry_run:
            run(["git", "submodule", "add", remote, relative_target], capture=False)
    elif not already_registered:
        raise RuntimeError(
            f"refusing to replace existing non-submodule directory: {target}"
        )
    else:
        print(f"refresh submodule {relative_target} -> {commit[:12]}")

    if dry_run:
        return

    # The clone made by `git submodule add` may not contain a locally-created
    # source commit, so fetch before checking out the exact source revision.
    try:
        run(["git", "-C", str(target), "cat-file", "-e", f"{commit}^{{commit}}"])
    except subprocess.CalledProcessError:
        run(["git", "-C", str(target), "fetch", "--all", "--tags"], capture=False)
    run(["git", "-C", str(target), "checkout", "--detach", commit], capture=False)
    run(["git", "add", relative_target], capture=False)


def copy_directory(source: Path, target: Path, dry_run: bool) -> None:
    print(f"copy {source.name} -> {target.relative_to(REPO_ROOT)}")
    if dry_run:
        return
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        target,
        symlinks=True,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".git"),
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def add_plugin(plugins: list[dict[str, Any]], plugin: dict[str, Any]) -> None:
    name = plugin.get("name")
    if not name:
        return
    for index, existing in enumerate(plugins):
        if existing.get("name") != name:
            continue
        # Re-running the importer should refresh entries it owns (including
        # newly discovered nested skills), while leaving personal entries such
        # as writing/latex/math untouched.
        if str(plugin.get("source", "")).startswith("./skills/"):
            plugins[index] = plugin
        return
    plugins.append(plugin)


def direct_skill_plugin(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "description": f"Imported skill: {name}.",
        "source": f"./skills/{name}",
        "category": "imported",
    }


def nested_skill_paths(root: Path) -> list[str]:
    return sorted(
        f"./{skill_file.parent.relative_to(root).as_posix()}"
        for skill_file in root.glob("**/SKILL.md")
    )


def add_imported_plugins(plugins: list[dict[str, Any]], imported: list[str]) -> None:
    for name in imported:
        path = TARGET_ROOT / name
        skill_file = path / "SKILL.md"
        if skill_file.is_file():
            add_plugin(plugins, direct_skill_plugin(name))
            continue

        marketplace_file = path / ".claude-plugin" / "marketplace.json"
        if marketplace_file.is_file():
            nested = load_json(marketplace_file)
            for plugin in nested.get("plugins", []):
                if not isinstance(plugin, dict) or not plugin.get("name"):
                    continue
                imported_plugin = dict(plugin)
                imported_plugin["source"] = f"./skills/{name}"
                add_plugin(plugins, imported_plugin)
            continue

        plugin_file = path / ".claude-plugin" / "plugin.json"
        if plugin_file.is_file():
            plugin = load_json(plugin_file)
            plugin["source"] = f"./skills/{name}"
            # Some repositories intentionally omit deprecated or in-progress
            # skills from plugin.json.  This marketplace mirrors every
            # installed SKILL.md, so retain the manifest entries and add any
            # omitted skill directories.
            plugin["skills"] = sorted(
                set(plugin.get("skills", [])) | set(nested_skill_paths(path))
            )
            add_plugin(plugins, plugin)
            continue

        nested_skills = sorted(path.glob("**/SKILL.md"))
        for skill_file in nested_skills:
            skill_dir = skill_file.parent
            skill_name = skill_dir.name
            relative = skill_dir.relative_to(TARGET_ROOT).as_posix()
            add_plugin(
                plugins,
                {
                    "name": skill_name,
                    "description": f"Imported skill: {skill_name}.",
                    "source": f"./skills/{relative}",
                    "category": "imported",
                },
            )


def update_marketplace(imported: list[str], dry_run: bool) -> None:
    marketplace = load_json(MARKETPLACE_PATH)
    plugins = marketplace.get("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError(f"plugins must be a list in {MARKETPLACE_PATH}")

    add_imported_plugins(plugins, imported)
    marketplace["plugins"] = plugins
    if dry_run:
        print(f"would write {MARKETPLACE_PATH.relative_to(REPO_ROOT)}")
        return
    MARKETPLACE_PATH.write_text(
        json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"updated {MARKETPLACE_PATH.relative_to(REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path(os.environ.get("CLAUDE_SKILLS_SOURCE", DEFAULT_SOURCE)),
        help="source skills directory (default: ~/.claude/skills)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_root = args.source.expanduser().resolve()
    if not source_root.is_dir():
        print(f"source directory does not exist: {source_root}", file=sys.stderr)
        return 1

    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    imported: list[str] = []
    for source in sorted(source_root.iterdir(), key=lambda path: path.name):
        if source.is_symlink():
            print(f"skip symlink {source.name} (the target is imported separately)")
            continue
        if not source.is_dir():
            print(f"skip non-directory {source.name}")
            continue

        target = TARGET_ROOT / source.name
        if is_git_checkout(source):
            import_git_checkout(source, target, args.dry_run)
        else:
            copy_directory(source, target, args.dry_run)
        imported.append(source.name)

    if not args.dry_run:
        update_marketplace(imported, dry_run=False)
    else:
        update_marketplace(imported, dry_run=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
