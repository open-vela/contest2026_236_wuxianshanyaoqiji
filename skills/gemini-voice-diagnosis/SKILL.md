---
name: gemini-voice-diagnosis
description: Diagnose Gemini-S1 openvela small-screen voice chat failures by separating firmware identity, microphone capture, ASR, model reply dispatch and playback. Use for this project's stuck recording, missing replies or repeated-session regressions.
---

# Gemini-S1 voice diagnosis

Work from the observed board and pinned official sources. Project paths below are relative to the repository root, two levels above this skill. Read `README.md` for the current release and `docs/capture-idle-20260919.md` for unresolved acceptance.

## Establish what is actually running

- On Windows, prefer the Android SDK platform-tools ADB over PhoenixSuit's bundled ADB; mixed server versions caused connection failures here. Choose one online device explicitly. Bound command waits, inspect stderr and exit status, and treat empty output as unverified.
- Read `uname -a` before interpreting symptoms. Compare build time with the selected release's ELF and delivery notes. A filename or successful flash dialog does not establish board version.
- `qiji_config result` reports busy, recording, status and reply. `ps` establishes whether mediad, capture and playback tasks still exist. Use an interactive shell if NSH truncates long noninteractive output.
- Do not print the full configuration JSON or unfiltered Wi-Fi log: the official driver logs the passphrase. Compare keys in memory and report only present/matched. Mask credentials before saving diagnostic output.

## Follow one utterance through the system

1. **Prerequisites:** check interface RUNNING and a usable DHCP address, then actual gateway reachability. An old lease alone is insufficient. Keep a healthy connection; redundant association sometimes selects a weak AP with the same SSID. Check ASR/TTS selection, saved key presence and clock separately.
2. **Capture:** locate ASR preconnect, recorder start and first PCM. Compare `capture first PCM` timing with start. Delayed first PCM, large `amix_input_alloc first size`, repeated overflow and stream failure suggest stale audio accumulation. Compare a fresh boot with a second recording after idle time.
3. **Stop/ASR:** require recording thread exit, `capture stopped`, then `ASR finalize`. NuttX AF_UNIX capture is FIFO-backed: closing from another thread did not reliably wake a blocked read. The current implementation uses nonblocking reads, checks STOPPING, joins the reader and only then closes the socket.
4. **Model:** distinguish the model's response trace from the UI callback. Official local_client is a one-shot callback; a working-status phrase previously consumed it before the real answer. Local working-status output is now suppressed at its source.
5. **Playback:** first TTS PCM only proves synthesis. Follow total writes, speak completion and media task survival. The official graph is 48 kHz stereo; the TTS backend returns mono PCM that is converted before playback. An EOF assertion previously terminated mediad after an apparently successful utterance.

`tools/board_acceptance.py` provides bounded, redacted diagnostics and explicit `--exercise` record/stop cycles on supported firmware. It performs real recording and sends captured audio to the configured ASR service only in exercise mode; use that mode when the user's testing authorization covers it. A silent-room test can prove capture/cleanup but cannot prove recognition accuracy.

## Fix and verify the relevant boundary

- Preserve the official 2.8-inch SPI LCD configuration. Do not reuse 7-inch MIPI, framebuffer, DDR or partition changes to fix audio.
- Check the actual official function and its callers. Do not disable assertions or swallow errors to make a test pass.
- Regressions should fail on the prior code and check behavior on the changed code. Host tests do not establish NuttX driver behavior or audible output.
- `tools/prepare_qiji_persona.py` is the current cumulative preparation entry. Official fixes and project patches are recorded in frozen release archives. Do not apply the archived cumulative patch on top of the preparation chain again.
- After packing, verify components and complete ROMFS payload with `tools/verify_official_image.py`. An official pack exit code of 1 occurred after successful Dragon packing; accept only with success markers and payload verification, not the exit code alone.
- Keep one clearly identified delivery image, immutable named releases and checksums. Confirm the new build on the board before testing it.

Stop repeating an offline transfer after bounded retries. On this board a software reboot entered FEL mode; a user-performed cold power cycle restored boot. Ask for the observed physical recovery rather than repeatedly issuing reboot.

Report separately: host regression, final image verification, board software lifecycle, physical microphone accuracy and speaker audibility. List any unverified boundary explicitly.
