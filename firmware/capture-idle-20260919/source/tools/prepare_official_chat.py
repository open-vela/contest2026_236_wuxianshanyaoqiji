"""Add this project's minimal UI to the independently synced official tree.

Run on Linux: python3 tools/prepare_official_chat.py /path/to/official/tree
The pinned defconfig comes from the successful official-source build.
"""
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
project = pathlib.Path(__file__).resolve().parent.parent
bsp = root / "vendor/allwinnertech"
for path, expected in (
    (bsp, "1676386193f0e710121e710935f1757c0f34b662"),
    (root / "packages/ai_agent", "e65550f18759f086d7f544edcf17d1e31223244f"),
):
    actual = subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if actual != expected:
        raise RuntimeError(f"Source differs from release: {path}: {actual}")
board = bsp / "boards/r528/r528s3-gemini-s1"
config = board / "configs/qiji_chat"
config.mkdir(exist_ok=True)
# Use the exact defconfig normalized by the successful build's savedefconfig.
# Its derivation from nsh_minidisplay is recorded in the release audit.
frozen = project / "firmware/official-clean-20260919/qiji-chat.defconfig"
text = frozen.read_text()
for forbidden in ("CONFIG_LCD_FRAMEBUFFER=y", "CONFIG_LCD_EXTERNINIT=y"):
    if forbidden in text:
        raise RuntimeError(f"Invalid small-screen release configuration: {forbidden}")
(config / "defconfig").write_text(text)

destination = root / "packages/demos/gemini_chat_minimal"
source = project / "app/gemini_chat_minimal"
if destination.is_symlink():
    if destination.resolve() != source:
        raise RuntimeError("Application path already points elsewhere")
elif destination.exists():
    raise RuntimeError("Application path already exists")
else:
    destination.symlink_to(source, target_is_directory=True)

rc = board / "src/etc/init.d/rcS.nsh"
text = rc.read_text()
marker = "#endif /* CONFIG_GEMINI_S1_NSH */"
addition = """
#ifdef CONFIG_GEMINI_CHAT_MINIMAL
qiji_chat &
ai_agent &
#endif

"""
if "qiji_chat &" not in text:
    if text.count(marker) != 1:
        raise RuntimeError("Official startup script changed: review before adapting")
    rc.write_text(text.replace(marker, addition + marker))

agent = root / "packages/ai_agent/src/agent_main.c"
text = agent.read_text()
marker = "    /* Block main thread until shutdown is requested */"
ready = """#ifdef CONFIG_GEMINI_CHAT_MINIMAL
    extern void qiji_chat_agent_ready(bool ready);
    qiji_chat_agent_ready(true);
#endif

"""
if "qiji_chat_agent_ready(true)" not in text:
    if text.count(marker) != 1:
        raise RuntimeError("Official agent startup changed: review before adapting")
    text = text.replace(marker, ready + marker)
    marker = "    /* Wake all threads blocked on message bus before stopping services */"
    if text.count(marker) != 1:
        raise RuntimeError("Official agent shutdown changed: review before adapting")
    text = text.replace(marker, "#ifdef CONFIG_GEMINI_CHAT_MINIMAL\n"
                        "    qiji_chat_agent_ready(false);\n#endif\n\n" + marker)
    agent.write_text(text)
print(f"Prepared {config}; official LCD settings retained")
