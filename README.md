# claude-hotline

**Let Claude Code phone you and talk.** When an agent finishes a long task or needs a
decision, it rings your phone, speaks a short update, listens to your answer, and carries
on. Everything runs on your own machine with free pieces: a free Linphone SIP account,
[whisper.cpp](https://github.com/ggerganov/whisper.cpp) for speech-to-text and
[Piper](https://github.com/rhasspy/piper) for the voice. No paid telephony.

This is a fork of [mohitbadwal/ringback](https://github.com/mohitbadwal/ringback)
(Apache-2.0). It adds Docker images for **CPU and NVIDIA GPU**, a Windows setup path,
faster turn-taking, and a Claude Code agent that makes the calls.

```text
You  <-- phone call --  Linphone app  <-- SIP/SRTP --  Docker container
                                                        |-- MCP server (stdio)
Claude Code  -- phone-caller agent --> MCP tools -----> |-- whisper.cpp (CPU or GPU)
                                                        '-- Piper voice
```

## Choose an image

| | CPU | GPU (NVIDIA) |
|---|---|---|
| Dockerfile | `Dockerfile` | `Dockerfile.gpu` |
| Speech-to-text | `base.en`, about 1.3 s per turn | `small.en`, about 0.3 s per turn |
| Image size | about 3 GB | about 15 GB |
| Build | `docker build -t ringback .` | `docker build -f Dockerfile.gpu -t ringback-gpu .` |
| Run flag | none | `--gpus all` |

Same Python code, voice and SIP stack in both. Details and trade-offs:
[docs/SETUP_DOCKER_CPU_GPU.md](docs/SETUP_DOCKER_CPU_GPU.md).

## Quick start

1. Create a free account at <https://subscribe.linphone.org> and sign in to the Linphone app
   on your phone.
2. Build an image (table above).
3. Put your SIP details in `voice.docker.env` (gitignored; never commit it).
4. Register the server with Claude Code, then start a **fresh** session:

```bash
# CPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --env-file /path/to/voice.docker.env ringback
# GPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --gpus all --env-file /path/to/voice.docker.env ringback-gpu
```

5. In the new session: *"use the ringback-voice tools to call me and say hello"*.

New to Docker, SIP or Android? Follow the step-by-step walkthrough in
[docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

## Documentation

| Doc | What it covers |
|---|---|
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | from zero to your first call, step by step |
| [docs/SETUP_DOCKER_CPU_GPU.md](docs/SETUP_DOCKER_CPU_GPU.md) | CPU vs GPU, build notes, switching, fixes for problems we hit |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | how a call works and where each second of a turn goes |
| [claude/](claude/) | the `phone-caller` agent and the matching Claude Code rules |
| [UPSTREAM_README.md](UPSTREAM_README.md) | upstream's full README (macOS and Linux native setups) |

## What changed from upstream

- `mcp` pinned below 2, because the upstream image crashes at startup with the current release.
- Piper stays loaded between sentences: about 0.4 s per sentence instead of about 3 s.
- The listening loop no longer blocks on transcription and skips a redundant second pass.
- `Dockerfile.gpu`: whisper.cpp built with CUDA.
- The upstream workflow that publishes a public image is manual-only here.

## Status and limits

Honest list of what is and is not proven:

- Verified: two-way calls through Docker Desktop on Windows 11, on both images; the offline
  test suite passes on both.
- Not yet verified: the `phone-caller` agent end to end in a fresh Claude Code session; a
  second call within one server session; live calls on the CPU image with all the changes.
- English speech models only. Other languages need a different whisper model and Piper voice.
- The machine must stay on, Docker Desktop must be running, and the Linphone app must stay
  connected for the phone to ring.
- The voice engine depends on GPL software (pjproject). Read [NOTICE](NOTICE) before
  redistributing a built image.

## License

Apache-2.0, see [LICENSE](LICENSE). Credit for the original project to
[mohitbadwal](https://github.com/mohitbadwal).
