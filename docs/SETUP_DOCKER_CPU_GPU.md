# Ringback in Docker — CPU or NVIDIA GPU

Two images are built from one codebase. Pick one; you can switch later by re-registering.

| | **CPU** (`Dockerfile`) | **GPU** (`Dockerfile.gpu`) |
|---|---|---|
| Image tag used below | `ringback` | `ringback-gpu` |
| Speech-to-text | whisper.cpp `base.en`, on the CPU | whisper.cpp `small.en` built with CUDA, on the GPU |
| Transcription time (5 s clip) | about 1.3 s | about 0.3 s once warm |
| Image size | about 3 GB | about 15 GB |
| First build | several minutes | long (the CUDA compile alone took about 23 min) |
| Needs | Docker | NVIDIA GPU + recent driver; Docker Desktop with the WSL2 backend, or the NVIDIA container toolkit on Linux |
| Extra run flag | none | `--gpus all` |

Choose **CPU** if you have no NVIDIA GPU, little disk space, or want the simplest setup.
Choose **GPU** if you want the fastest replies. The Python code, Piper voice, SIP stack and
MCP tools are identical in both; only the speech-to-text build and model differ.

Tested on Windows 11 with Docker Desktop (WSL2) and an RTX 3050 6 GB laptop GPU.

## What was verified

| Claim | Evidence |
|---|---|
| Two-way audio through Docker Desktop on Windows | live test calls, STUN (`VOICE_STUN`) and bridge networking |
| GPU whisper about 0.3 s vs about 1.3 s on CPU | offline timing inside both containers |
| Waiting after a reply dropped from about 7.3 s to about 3 s | live timed calls: CPU image (Piper reuse) and GPU image (all changes) |
| The offline turn-logic tests pass on both images | 3 of 3 runs each |
| Live calls on the **CPU image with all the changes** | **not run**; only the earlier CPU build was called live |
| The `phone-caller` agent flow (Haiku subagent + `context.md`) | **not yet verified end to end** |
| A second call in one server session | **not tested** |

## Build

```bash
# CPU
docker build -t ringback .

# GPU (needs the NVIDIA setup described below)
docker build -f Dockerfile.gpu -t ringback-gpu .
```

GPU build notes:

- **Build engine crash at about 92%** ("error reading from server: EOF"): out of memory. The
  build uses `-j3`; an unlimited `-j` crashed Docker Desktop with about 8 GB.
- **`undefined reference to cuGetErrorString`** at link time: build machines have no GPU
  driver. The Dockerfile links against NVIDIA's stub, exposed as `libcuda.so.1`.
- **`CUDA_ARCH`** defaults to 86 (RTX 30-series). Change it for other cards:
  `docker build -f Dockerfile.gpu --build-arg CUDA_ARCH=89 -t ringback-gpu .` (RTX 40-series).

## Check that Docker can see your GPU (GPU only)

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

You should see your card listed. If not, update the NVIDIA driver and make sure Docker
Desktop uses the WSL2 backend.

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
# CPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --env-file C:/path/to/voice.docker.env ringback

# GPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --gpus all --env-file C:/path/to/voice.docker.env ringback-gpu
```

Do not use `--network host` on Docker Desktop; it gives one-way audio.

**Switching** between CPU and GPU: remove the entry and add the other one.

```bash
claude mcp remove ringback-voice -s user
# then run the add command for the image you want
```

Tools registered after a Claude Code session starts are not visible to it, so start a fresh
session after registering or switching.

## Verify without a phone call

```bash
# the MCP server starts and answers (replace the image name for GPU and add --gpus all)
docker run --rm ringback python -c "import pjsua2, mcp; print('imports OK')"

# the offline test suite (dials nobody)
docker run --rm ringback python tests/run_all.py
```

The turn-logic test is timing-sensitive: on the original code it passed on some runs and
failed on others, so repeat it before drawing conclusions. On both images with the changes
below, it passed every time.

## Changes relative to upstream (shared by both images)

1. **`mcp` pinned below 2.** The upstream Dockerfile installs `mcp>=1.2.0`; pip now resolves
   2.x, which renamed `FastMCP`, so the server exits at startup ("Connection closed").
2. **Piper stays loaded.** `platform_compat.py` loads the voice once (in-process `piper-tts`)
   instead of spawning `piper` per sentence. This cut each spoken sentence from about 3 s to
   about 0.4 s. It falls back to the CLI if loading fails.
3. **Streaming capture no longer blocks.** `voice_agent.py` transcribes on a background
   thread, so end-of-speech is checked every 0.1 s, and skips the redundant final
   transcription when the streamed text already covers the turn. The `[timing]` log goes to
   stderr (stdout is the MCP transport).
4. **GPU only:** `Dockerfile.gpu` builds whisper.cpp with CUDA, uses the `small.en` model, and
   sets `ENTRYPOINT []`. NVIDIA's base-image entrypoint prints a license banner to stdout,
   which is the MCP transport, so the client times out without this.

## Agent rules (optional)

To make an agent phone you on its own, give it standing instructions. For any agent, paste
`integrations/generic/AGENT_RULES.md`. For Claude Code, copy `integrations/claude-code/phone-caller.md`
to `~/.claude/agents/`; it is a subagent (Haiku, all tools, read-only during calls) that holds the
call, and the rules for when to call live in its description. Other clients: see [CLIENTS.md](CLIENTS.md).

## Disk space on Windows

Docker Desktop keeps its data in `docker_data.vhdx`, which never shrinks by itself. After
`docker builder prune -a -f`, quit Docker Desktop, run `wsl --shutdown`, then in an
**elevated** PowerShell:

```powershell
Optimize-VHD -Path "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx" -Mode Full
```

## Licensing

Upstream is Apache-2.0 (`LICENSE`). The voice component depends on GPL software (pjproject);
read `NOTICE` before redistributing a built image. The upstream workflow that publishes a
public image is manual-only in this repo.
