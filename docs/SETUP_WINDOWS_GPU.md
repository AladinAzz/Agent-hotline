# Ringback — Windows + NVIDIA GPU setup (Docker Desktop)

This documents a working Windows setup built on top of upstream ringback, with whisper.cpp
running on an NVIDIA GPU. It was built and tested on Windows 11, Docker Desktop (WSL2
backend) and an RTX 3050 6 GB laptop GPU. Everything here is a local addition to upstream.

What was verified, and how:

| Claim | Evidence |
|---|---|
| Two-way audio through Docker Desktop on Windows | live test calls, with STUN (`VOICE_STUN`) and bridge networking |
| GPU whisper is about 0.3 s per transcription (small.en) vs about 1.3 s on CPU (base.en) | offline timing inside the container |
| Waiting after a reply dropped from about 7.3 s to about 3 s | live timed calls on the CPU and GPU images |
| The `phone-caller` agent flow (Haiku subagent + `context.md`) | **not yet verified end to end** |
| A second call in one server session | **not tested** |

## Changes relative to upstream

1. **`mcp` pinned below 2.** The upstream Dockerfile installs `mcp>=1.2.0`; pip now resolves
   2.x, which renamed `FastMCP`, so the server exits at startup ("Connection closed").
2. **Piper stays loaded.** `platform_compat.py` loads the voice once (in-process `piper-tts`)
   instead of spawning `piper` per sentence. This cut each spoken sentence from about 3 s to
   about 0.4 s. It falls back to the CLI if loading fails.
3. **Streaming capture no longer blocks.** `voice_agent.py` transcribes on a background
   thread, so end-of-speech is checked every 0.1 s, and skips the redundant final
   transcription when the streamed text already covers the turn. The `[timing]` log goes to
   stderr (stdout is the MCP transport).
4. **`Dockerfile.gpu`.** A CUDA build of whisper.cpp (compute capability 86, RTX 30-series;
   change `CUDA_ARCH` for other cards) with the `small.en` model.

## Build

```bash
docker build -f Dockerfile.gpu -t ringback-gpu .      # CPU image: docker build -t ringback .
```

Expect a long first build (the CUDA compile alone took about 23 minutes) and a large image
(about 15 GB). Notes from getting it to build:

- **Build engine crash at ~92%** ("error reading from server: EOF"): out of memory. The build
  uses `-j3`; an unlimited `-j` crashed Docker Desktop with about 8 GB.
- **`undefined reference to cuGetErrorString`** at link time: build machines have no GPU
  driver. The Dockerfile links against NVIDIA's stub, exposed as `libcuda.so.1`.
- **MCP connection timeout with the GPU image:** NVIDIA's base-image entrypoint prints a
  license banner to stdout, which is the MCP transport. `ENTRYPOINT []` removes it.

## Credentials

Create `voice.docker.env` (plain `KEY=value`, no quotes, no `export`). It is gitignored
(`*.docker.env`). Never commit it.

```text
VOICE_SIP_ID=sip:<username>@sip.linphone.org
VOICE_SIP_USER=<username>
VOICE_SIP_PASS=<password>
VOICE_DISPLAY_NAME=Claude
VOICE_STUN=stun.l.google.com:19302
VOICE_END_SILENCE=0.9
```

`VOICE_END_SILENCE=0.9` shortens the end-of-speech wait from the default 1.5 s. Raise it
(about 1.2) if you get cut off when you pause mid-sentence.

## Register with Claude Code

```bash
claude mcp add ringback-voice --scope user -- docker run -i --rm --gpus all --env-file C:/path/to/voice.docker.env ringback-gpu
```

For the CPU image drop `--gpus all` and use `ringback`. Do not use `--network host` on
Docker Desktop; it gives one-way audio.

## Claude Code agent and rules (optional)

`claude/phone-caller.md` is a subagent (Haiku, all tools, read-only during calls) that makes
the call. Copy it to `~/.claude/agents/`. `claude/CLAUDE.phone-rules.md` holds the matching
rules for `~/.claude/CLAUDE.md`: call for any input or question and when work finishes, and
write a `context.md` for the agent first. Tools registered after a session starts are not
visible to it, so start a fresh session after registering.

## Disk space on Windows

Docker Desktop keeps its data in `docker_data.vhdx`, which never shrinks by itself. After
`docker builder prune -a -f`, quit Docker Desktop, run `wsl --shutdown`, then in an
**elevated** PowerShell:

```powershell
Optimize-VHD -Path "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx" -Mode Full
```

## Licensing

Upstream is Apache-2.0 (`LICENSE`). The voice component depends on GPL software (pjproject);
read `NOTICE` before redistributing a built image.
