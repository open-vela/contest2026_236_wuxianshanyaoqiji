"""Export the frozen 2026-09-19 release; never rebuild or flash a device."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    project = Path(__file__).resolve().parent.parent
    release = project / "firmware/official-clean-20260919"
    source_lock = release / "frozen-source-hashes.json"
    if source_lock.exists():
        for relative, expected_hash in json.loads(source_lock.read_text()).items():
            if digest(project / relative) != expected_hash:
                raise ValueError("Sources have advanced beyond the frozen release. "
                                 "Use the original gemini-s1-chat-20260919.zip; "
                                 "do not relabel current sources as the old firmware.")
    expected = {
        "official-nsh-minidisplay.img": "24f286127138f8f67b8167705fb830db7a2dfb2b0a17462ae4a1f6da1a43c4c4",
        "qiji-chat.img": "777e4e7f97a2dd1221c58fc60a06af8d05f4a7362295e3c5f560881a8201e393",
    }
    for name, sha in expected.items():
        if digest(release / name) != sha:
            raise ValueError(f"Frozen image changed: {name}")
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / "gemini-s1-chat-20260919.zip"
    if target.exists():
        raise FileExistsError(target)
    files = list(release.rglob("*"))
    app = project / "app/gemini_chat_minimal"
    files += [app / name for name in (
        "gemini_chat_main.c", "qiji_config_main.c", "Kconfig", "Make.defs", "Makefile", "README.md")]
    files += [project / name for name in (
        "README.md", "docs/build-pack-guide.md", "docs/official-clean-audit-20260919.md",
        "docs/release-cleanup-20260919.md", "tools/prepare_official_chat.py",
        "tools/verify_official_image.py", "tools/export_gemini_release.py")]
    checksums = {}
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            if path.is_file():
                name = path.relative_to(project).as_posix()
                checksums[name] = digest(path)
                archive.write(path, name)
        archive.writestr("SHA256SUMS.json", json.dumps(checksums, indent=2) + "\n")
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        for name, sha in checksums.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise ValueError(f"Archive content mismatch: {name}")
    (args.output / (target.name + ".sha256")).write_text(
        f"{digest(target)}  {target.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(target), "files": len(checksums),
                      "bytes": target.stat().st_size, "sha256": digest(target)}, indent=2))


if __name__ == "__main__":
    main()
