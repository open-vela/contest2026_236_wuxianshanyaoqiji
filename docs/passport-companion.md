[简体中文](passport-companion.zh_CN.md)

# Kotone and Xiaocheng hardware companions

System boundary: Gemini-S1 runs openvela / NuttX. AI Passport runs ESP-IDF 5.5.3 / FreeRTOS as an external companion, not an openvela port. The computer coordinates cloud text generation in duet mode.

This prototype adds an original character, Xiaocheng, to FoloToy AI
Passport and connects it to the existing Gemini-S1 Qiji application (currently
Fujita Kotone). The coordinator reads the existing `SOUL.md` and character name;
it does not replace that persona with the older Qiji character. "Qiji" below
refers to the existing application/device. A computer
on the same LAN runs the coordinator. This version requires that computer; it
does not implement standalone BLE/NFC discovery or on-device model inference.

## Behavior

- Each physical device polls the coordinator. Both must be online and ready.
- Their first encounter starts automatically. Six short turns alternate between
  Qiji and Xiaocheng. Both screens display the current speaker's words.
- The coordinator waits for **both acknowledgements**, including the speaker's
  audio completion, before starting another turn. Text transport avoids acoustic
  recognition of the other device's speaker.
- After six completed turns, a separate model request summarizes only the
  completed transcript for the user. Qiji speaks it; both screens retain it.
- Completion, a disconnect, playback failure, or user stop prevents automatic
  re-entry. Long-press Passport OK to start again. UP/DOWN scroll dialogue/summary.
- Long-press Passport OK stops a duet; Gemini ENTER requests a stop instead of recording
  during a session. Gemini finishes its current short utterance before its audio
  worker becomes available. Passport cancels its stream at the next read/write
  boundary. There is no interruption of cloud inference already in flight, but
  its late output is discarded.
- Conversation exists only in coordinator RAM. No long-term user memory is
  inferred or collected. No microphone recording is initiated by the duet.

Xiaocheng now uses original silver-haired future-traveller artwork, with a
blue/violet jacket, detailed eyes, headset and hair accessory. Five native-size
RGB565A8 frames are stored in Flash, supporting breathing, blinking and
PCM-driven mouth movement. Refined eyes include rounded lids, layered irises
and a half-closed blink transition. The editable SVG and generation script are documented
in `assets/xiaocheng-future-v1/README.md`; the actual LVGL preview is
`docs/assets/duet/xiaocheng-eyes-preview.png` and `.gif`.
The existing Qiji artwork is preserved. The HTML preview draws a
simplified Qiji for illustrating the interaction; it does not replace her asset.

2026-09-20 initial UI revision enlarged the earlier primitive character 1.875x.
Name, status and battery share one 12 px header row, and the bottom key hint is
removed. Dialogue and summaries float in a translucent panel in front of the
character. Its speaker label stays fixed while the 16 px body scrolls separately.
UP/DOWN still scroll one line. Direct coordinate scaling avoids an extra image
transform buffer. See `docs/assets/duet/xiaocheng-overlay-preview.png` and the
independent `firmware/passport-overlay-20260920` release; the original duet release
is retained. The later silver-haired revision preserves the header and dialogue
layout, replacing the portrait with 240x280 artwork. USB configuration and LAN
registration were verified on the configuration-fix release; that result does
not establish device acceptance for the new artwork.

The subsequent `xiaocheng-0.2.1-refined-eyes` release was flashed at 0x10000
on COM3 with the existing Wi-Fi configuration preserved. The matching ELF
started without crash markers during a 30-second observation and reconnected
to the coordinator. The user confirmed normal physical display and blinking.
See `artifacts/passport-device/20260920-eyes-result.json` and
`firmware/passport-eyes-20260920`. Audio, two-device conversation, button
scrolling and long-duration stress remain unverified for this release.

## Source and build

- `app/passport_companion/main`: ESP-IDF application, original UI and generated font.
- `tools/duet/server.py`: dependency-free Python LAN service, isolated role prompts,
  finite state machine, model/TTS adapters, acknowledgements and cancellation.
- `app/gemini_chat_minimal/qiji_duet.c`: Gemini LAN client; reuses the existing UI/audio worker.
- `tools/duet/preview.html`: standalone scripted interactive preview. It can also
  observe a running service without impersonating a physical device.
- `tools/passport_preview`: native rendering of the actual firmware UI/font.

Passport upstream is pinned to FoloToy/ai-passport commit
`855d2106547988e33128e27aadff4fe98351fe14`; use ESP-IDF **5.5.3** and the upstream
dependency lock. Installation keeps the BSP, pins and partition table intact,
replaces the compiled application, disables unused BLE, selects 40 KB for LVGL,
and enables large bitmap font offsets.

```sh
python tools/duet/build_font.py
python tools/prepare_passport_companion.py /path/to/dedicated-ai-passport-checkout
cd /path/to/dedicated-ai-passport-checkout
. /path/to/esp-idf-v5.5.3/export.sh
./tools/validate.sh
```

Font generation requires Node/npm, Python fontTools and internet access. Noto
Sans SC is instantiated at weight 500, converted with lv_font_conv 1.5.3 at
16 px / 2 bpp, and stored in Flash. `assets/xiaocheng-font/OFL.txt` supplies its
license. `coverage.json` records the supported code points and original font
SHA-256. The gateway rejects unsupported model output rather than hiding missing
glyphs. Generation is reproducible from the cached source; upstream font changes
must be reviewed against the recorded hash.

A separate 12 px status subset is collected from UI strings, device states and
the existing desktop character's name. Its inventory is stored in
`assets/xiaocheng-font/status-characters.txt`. After changing those fixed labels,
regenerate it with `python tools/duet/build_font.py --status-only`.

Build Gemini with the existing pinned official tree and current application
preparation flow described in [the build guide](build-pack-guide.md). No board
driver or partition changes are required by the duet client.

## Preview and verification

Open `tools/duet/preview.html` and select the scripted preview. That button does
not call a model or claim hardware is connected. Alternatively:

```sh
python tools/duet/server.py --demo
python -m unittest discover -s tools/duet -p test_server.py -v
```

The tests cover the real HTTP handshake and six-turn-plus-summary sequence,
authentication, duplicate/stale acknowledgements, cancellation, disconnects,
playback timeouts/errors and cloud failures. Scripted and live modes are explicit;
live failures never silently substitute scripts.

The actual firmware UI can be rendered without a device:

```sh
cmake -S tools/passport_preview -B /tmp/xiaocheng-preview -DLVGL_SOURCE=/path/to/lvgl
cmake --build /tmp/xiaocheng-preview -j4
mkdir -p docs/assets/duet/frames
/tmp/xiaocheng-preview/passport_preview docs/assets/duet/frames
```

The renderer verifies 20,976 basic CJK glyphs plus a negative missing-glyph case.
See `docs/assets/duet/xiaocheng-firmware-preview.gif` for the generated animation.
This is a host render, not a photograph or device test.

## Live operation

### Passport's own microphone conversation

The voice revision adds short-press OK to start recording, short-press again to
submit, and short-press during recognition/reply/playback to cancel. Wait for
the recording status before speaking. Recordings are PCM16 mono at 16 kHz,
limited to 20 seconds, and uploaded as 1 KB HTTP chunks. The firmware never
allocates a whole recording. Upload stalls and partial recordings fail explicitly.
Long-press OK retains duet start/stop; UP/DOWN still scroll. Starting a voice
request stops the duet and marks Passport unavailable to it until duet mode is
selected again. Audio format changes and playback/recording share one mutex.

`gemini_bridge.py` invokes the existing `tools/asr_host` executable, compiled
from Gemini's actual `qiji_aliyun_asr.c`: Paraformer recognition and Qwen 3.1
speech synthesis. The LLM uses Gemini's saved URL/model/key, with Xiaocheng's
own persona. The default host helper is `/home/vela/qiji-asr-host/qiji_asr_host`
under WSL Ubuntu on Windows. Override it with `DUET_GEMINI_COMMAND` (a JSON
argument array) or `DUET_GEMINI_HELPER` on Linux. Keys enter the helper through
stdin. Temporary PCM files are removed after each call. Six completed exchanges
are retained in host RAM; only successful playback is added to history.

With Gemini connected over ADB, import its existing cloud configuration:

```sh
python tools/duet/configure_cloud.py --from-gemini
```

Without Gemini, run `configure_cloud.py` without arguments and enter credentials
locally; password prompts do not echo. The ignored host-only `cloud.json` is not
part of firmware. Stop the previous server, then start the real service:

```sh
python tools/duet/run_live.py --model character
python -m unittest discover -s tools/duet -p 'test_*.py' -v
```

`--model character` selects `doubao-seed-character-260628`; `--model turbo`
selects `doubao-seed-2-1-turbo-260628`. Omitting it uses the saved model.
Both models have passed real API calls; the running service uses the character
model. Aliyun recognition and synthesis reuse Gemini's implementation without
requiring the Gemini hardware to be online.

On 2026-09-20, real HTTP chunked upload, ASR, Doubao reply, TTS and audio
download passed with synthetic speech in about 7.2 seconds. Evidence:
`artifacts/passport-device/20260920-voice-http-cloud-test.json`. This does not
verify the physical microphone or speaker. To repeat manually, run
`python tools/duet/check_live_voice.py`; it uses paid cloud APIs and stops the
current duet, without recording, playing audio or adding test chat to history.
WSL calls bound DNS retries and the Linux subprocess lifetime to prevent a
stalled DNS tunnel from leaving an orphan helper.

`--demo` deliberately rejects microphone AI sessions; it never returns a fake
transcription or reply. Hardware recording, cloud recognition, model output and
audible playback must each be verified before claiming end-to-end acceptance.
This still requires the computer, but does not require the other hardware.

Set these environment variables locally (never put their values in source):

| Variable | Meaning |
| --- | --- |
| `DUET_LLM_URL` | HTTPS chat-completions endpoint, e.g. the user's configured Doubao endpoint |
| `DUET_LLM_MODEL` | Model/deployment name supported by that endpoint |
| `DUET_LLM_KEY` | Model API key |
| `DASHSCOPE_API_KEY` | Beijing-region DashScope key for Xiaocheng speech |
| `DUET_TOKEN` | Shared local pairing token; use 32 random hex characters |

```sh
python tools/duet/server.py --host 0.0.0.0
```

Qiji uses its configured on-device TTS backend/voice. Xiaocheng now uses the
same `gemini_bridge.py` path as solo speech: the existing
`qwen-audio-3.1-tts-flash` C backend, returning validated 24 kHz PCM16.
During device testing on 2026-09-20, the former `qwen3-tts-flash` route returned
HTTP 400 / Arrearage while the existing 3.1 route succeeded. Both modes now
share that working route; `DUET_XIAOCHENG_VOICE` is no longer used. Failures
remain explicit, with no prerecorded fallback. Voice differentiation still
requires listening on the devices.
`--text-only` disables both voices for transport tests.
`--manual` disables the initial automatic encounter. The live cloud adapters need
valid provider credentials and quota; they are separate from scripted tests.

Both devices must reach the computer's LAN IPv4 address and TCP port 8765. The
default bind is loopback; use `--host 0.0.0.0` for hardware. The protocol is plain
HTTP with a pairing token and is intended only for a trusted local network. Cloud
calls use HTTPS; cloud API keys stay on the computer/Gemini rather than Passport.

After authorized flashing, configure Passport over its identified USB port:

```sh
python -m pip install pyserial
python tools/duet/configure_passport.py --port COM3 --host http://COMPUTER_LAN_IP:8765
```

The tool prompts for Wi-Fi and pairing credentials without echoing passwords,
writes the application's own `qiji_duet` NVS namespace and restarts the device.
The firmware does not erase NVS automatically on initialization failure.

The USB receiver retains fragmented JSON until a newline arrives; a temporary
absence of serial data does not discard a partial configuration. Lines longer
than 639 bytes or containing NUL are rejected in full, and the next line can
configure the device again. Regression coverage is in `tools/duet/test_config_line.c`.

On Gemini, after installing the duet build:

```text
qiji_config duet COMPUTER_LAN_IP 8765 PAIRING_TOKEN
qiji_config duet_off
```

Use a unique pairing token and keep local command/configuration history private.
The first command enables the client; the second disables it. A stopped session
can be restarted from Passport or `POST /v1/start` with the pairing token. A live
start request may include a user-supplied `topic` of at most 160 characters.

## Device acceptance and current boundary

The `xiaocheng-0.3.1-spacing` revision reduces dialogue line advance from 31 px
to 20 px, with matching button and automatic scroll increments. Character art,
16 px body text, overlay position and voice behavior remain the same. The real
LVGL host rendering is `docs/assets/duet/xiaocheng-spacing-preview.png`.

On 2026-09-20, the user authorized flashing `xiaocheng-0.3-voice` to COM3 at
`0x10000`. Application write verification passed. Its partition table matches
the previous eye-refinement release; NVS was not written, and the device reused
Wi-Fi settings and resumed coordinator heartbeats. The startup ELF identity
matches the archive, with no crash in the 30-second startup window. The user confirmed physical
button recording, recognition and audible replies work. Cancellation during
playback and long-duration stress remain unverified.
See `artifacts/passport-device/20260920-voice-result.json`.

Build, host tests and device tests are reported separately in the release record.
USB enumeration identified an ESP32-C3 native USB device on COM3. Enumeration
alone does not prove firmware compatibility, display quality or audio operation.

The merged Passport image is flashed at 0x0 and replaces the installed app; its
padding can reset NVS/PHY data. Do not promise factory-profile preservation or
erase the whole chip as a prerequisite. Obtain approval for the exact image.

Remaining physical checks: screen rotation/colors, Chinese glyph readability,
buttons/scrolling, free heap and largest block with Wi-Fi plus audio, no audio
overlap, real playback completion, 10 encounters without reset, disconnect and
stop behavior, both physical devices displaying the final summary, and audible
voice distinction. BLE, NFC, stand-alone operation without the coordinator,
voice interruption into a new topic and persistent shared memory are not included.
