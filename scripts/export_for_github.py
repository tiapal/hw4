"""Make a clean copy of this project that is safe to publish, and check it for anything that must stay private.

It applies the rules in .gitignore (the same ones git uses), copies everything else to a new folder, then audits
the copy: no .env, no database, no product photos, no copy of your real API key, and .env.example holds only
placeholders. It stops with an error if any check fails.

Use it when you can't use git: upload the contents of the new folder to GitHub (see README).

Run from the project folder (needs: pip install pathspec):
    backend/.venv/bin/python scripts/export_for_github.py
Optional: a different destination, or --replace to overwrite an earlier export.
"""

import re
import shutil
import sys
from pathlib import Path

import pathspec

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = ROOT.parent / "hw4-github-upload"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".ico", ".svg"}
ALLOWED_IMAGES = ("output/app_check_images/", "frontend/public/")  # test screenshots and the site's own icons


def load_spec() -> pathspec.PathSpec:
    lines = (ROOT / ".gitignore").read_text().splitlines() + [".git/"]
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def files_to_publish(spec: pathspec.PathSpec) -> list[Path]:
    keep = []
    for path in sorted(ROOT.rglob("*")):
        rel = path.relative_to(ROOT).as_posix()
        if spec.match_file(rel + ("/" if path.is_dir() else "")):
            continue
        if any(spec.match_file("/".join(path.relative_to(ROOT).parts[:i]) + "/") for i in range(1, len(path.relative_to(ROOT).parts))):
            continue  # inside an ignored folder
        if path.is_file():
            keep.append(path)
    return keep


def real_api_key() -> str | None:
    for env in (ROOT / ".env", ROOT.parent / ".env", ROOT / "backend" / ".env"):
        if env.exists():
            match = re.search(r"^PORTKEY_API_KEY=(.+)$", env.read_text(), re.M)
            if match and match.group(1).strip():
                return match.group(1).strip()
    return None


def audit(dest: Path) -> list[str]:
    problems = []
    published = [p for p in dest.rglob("*") if p.is_file()]
    for p in published:
        rel = p.relative_to(dest).as_posix()
        if p.name == ".env" or (p.name.startswith(".env.") and p.name != ".env.example"):
            problems.append(f"real env file would be published: {rel}")
        if p.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            problems.append(f"database would be published: {rel}")
        if p.suffix.lower() in IMAGE_SUFFIXES and not rel.startswith(ALLOWED_IMAGES):
            problems.append(f"image would be published: {rel}")
        if rel.startswith(("data/", "node_modules/", "backend/.venv/")):
            problems.append(f"private or generated folder would be published: {rel}")
    key = real_api_key()
    if key:
        for p in published:
            try:
                if key in p.read_text(errors="ignore"):
                    problems.append(f"the real API key appears in {p.relative_to(dest).as_posix()}")
            except OSError:
                pass
    example = dest / ".env.example"
    if not example.exists():
        problems.append(".env.example is missing")
    else:
        for line in example.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                value = line.split("=", 1)[1].strip()
                if value and "your" not in value.lower():
                    problems.append(f".env.example has a value that isn't a placeholder: {line.split('=')[0]}")
    return problems


def looks_like_a_previous_export(folder: Path) -> bool:
    return (folder / "README.md").exists() and (folder / ".env.example").exists() and not (folder / ".git").exists()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dest = Path(args[0]).expanduser().resolve() if args else DEFAULT_DEST
    if dest.exists():
        if "--replace" in sys.argv and looks_like_a_previous_export(dest):
            shutil.rmtree(dest)  # only a folder that looks like an earlier export (never a git repository)
        else:
            sys.exit(f"{dest} already exists. Pass --replace to overwrite a folder this script made, or choose another path.")
    files = files_to_publish(load_spec())
    for path in files:
        target = dest / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    problems = audit(dest)
    count = len([p for p in dest.rglob("*") if p.is_file()])
    print(f"copied {count} files to {dest}")
    if problems:
        print("\nSTOP: problems found, do not publish this folder:")
        for p in problems:
            print("  -", p)
        return 1
    print("audit passed: no .env, no database, no product photos, no copy of your real API key,")
    print(".env.example has placeholders only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
