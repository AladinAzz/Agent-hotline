# Setup guide — from zero to your first call

This walks through the whole setup in order, assuming no experience with Docker, SIP or
telephony. It was written from a real Windows 11 setup with Docker Desktop. Each step says what
it is for and how to tell it worked. For CPU-vs-GPU detail and fixes for specific errors, see
[SETUP_DOCKER_CPU_GPU.md](SETUP_DOCKER_CPU_GPU.md).

## What you need

- A PC that stays on and online during calls, with **Docker Desktop** (Windows or macOS) or
  Docker Engine (Linux).
- An Android or iOS phone for the **Linphone** app. (This guide was tested with Android.)
- **Optional:** an NVIDIA GPU for the faster GPU image (driver installed; Docker Desktop on the
  WSL2 backend).
- About 5 GB free disk for the CPU image, or about 20 GB for the GPU image plus its build cache.
- An MCP-capable agent. This guide uses [Claude Code](https://claude.com/claude-code), the one
  tested; see [CLIENTS.md](CLIENTS.md) for others.

## Step 1 — Create the phone line (free SIP account)

A SIP account is the "phone number" your agent calls and your phone answers.

1. In a browser open <https://subscribe.linphone.org> and sign up. Choose a username and a
   password, and confirm any email or phone check it asks for.
2. Write the username and password down somewhere only you can see. You will type them into a
   local file in step 5. **Never paste them into a chat or commit them.**

Your SIP address is `sip:<username>@sip.linphone.org`.

## Step 2 — Install the Linphone app on your phone

1. Install **Linphone** from your phone's app store and open it.
2. Sign in with the account from step 1 (an existing SIP account; domain `sip.linphone.org`;
   leave the transport on its default).
3. Allow the permissions it asks for: **microphone**, **notifications**, and any "phone calls"
   or "display over other apps" prompt.
4. Check that the app shows **Connected** (or Registered).
5. **Android only:** Settings → Apps → Linphone → Battery → **Unrestricted**. Otherwise Android
   may stop the app from ringing when the phone sleeps.

## Step 3 — Install Docker and get the code

1. Install Docker Desktop and start it. Check it is running:

```bash
docker info --format "server={{.ServerVersion}}"
```

   You should see a version number, not a "cannot connect" error.

2. Get the code:

```bash
git clone https://github.com/<your-user>/agent-hotline.git
cd agent-hotline
```

3. **GPU only** — check Docker can see the card:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

   You should see your GPU listed.

## Step 4 — Build the image

Pick one. Both take a while the first time.

```bash
# CPU: several minutes, about 3 GB
docker build -t ringback .

# GPU: long (the CUDA compile alone took about 23 minutes), about 15 GB
docker build -f Dockerfile.gpu -t ringback-gpu .
```

Check it worked (replace the image name for GPU, and add `--gpus all`):

```bash
docker run --rm ringback python -c "import pjsua2, mcp; print('imports OK')"
```

If the GPU build crashes with "error reading from server: EOF", Docker ran out of memory; see
the build notes in [SETUP_DOCKER_CPU_GPU.md](SETUP_DOCKER_CPU_GPU.md).

## Step 5 — Create the credentials file

Create a file named `voice.docker.env` in the project folder with these lines. Use plain
`KEY=value` — no quotes, no spaces around `=`, no `export`:

```text
VOICE_SIP_ID=sip:<username>@sip.linphone.org
VOICE_SIP_USER=<username>
VOICE_SIP_PASS=<password>
VOICE_DISPLAY_NAME=Claude
VOICE_STUN=stun.l.google.com:19302
VOICE_END_SILENCE=0.9
```

- `VOICE_DISPLAY_NAME` is the caller name your phone shows.
- `VOICE_STUN` is **required on Docker Desktop**; without it you get one-way audio.
- `VOICE_END_SILENCE=0.9` is how long it waits after you stop talking. Raise it to about 1.2 if
  it cuts you off when you pause.

The file is gitignored (`*.docker.env`). **Never commit it or share it.** Make sure no
placeholder text is left (`<username>`, `<password>`), and that your username matches on lines
1 and 2.

## Step 6 — Connect your agent (Claude Code shown)

This tells your agent how to start the container. Other agents use the same `docker run`
command in their own config; see [CLIENTS.md](CLIENTS.md). Use the full path to your env file:

```bash
# CPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --env-file C:/path/to/voice.docker.env ringback

# GPU
claude mcp add ringback-voice --scope user -- docker run -i --rm --gpus all --env-file C:/path/to/voice.docker.env ringback-gpu
```

Check it:

```bash
claude mcp get ringback-voice
```

You should see `Connected`. Do **not** add `--network host` on Docker Desktop.

## Step 7 — Make your first call

Claude Code only loads tools when a session starts, so **open a fresh session** first. Then
say:

> use the ringback-voice tools to call me and say hello

Your phone should ring (caller name "Claude"). Answer, listen to the hello, and say one short
sentence. The agent should tell you what it heard.

If something is off:

| Symptom | Likely cause |
|---|---|
| Registration shows failed / "Connection closed" | image crashes at startup; see the `mcp` pin note in [SETUP_DOCKER_CPU_GPU.md](SETUP_DOCKER_CPU_GPU.md) |
| Registration times out (GPU) | the NVIDIA banner on stdout; the GPU Dockerfile already clears the entrypoint |
| Phone never rings | Linphone not Connected, or Android battery setting; wrong SIP username |
| You hear the agent but it never hears you | missing `VOICE_STUN`, or `--network host` in use |
| `[NO ANSWER]` | the phone took too long to wake; check battery setting and try again |

## Step 8 — Let the agent call you on its own (optional)

This is the part that makes your agent phone you when it finishes a task or needs a decision.

- **Any agent:** paste [integrations/generic/AGENT_RULES.md](../integrations/generic/AGENT_RULES.md)
  into its standing instructions (`AGENTS.md`, a system prompt, and so on).
- **Claude Code:** copy `integrations/claude-code/phone-caller.md` to `~/.claude/agents/`. It is
  a small, fast (Haiku) subagent that makes the call and reports back what you said. The rules
  for when to call are in its description, so nothing needs adding to `CLAUDE.md`. Start a fresh
  session and try: *"use the phone-caller agent to call me and say hello"*. The subagent can
  read your project during a call but does not change files; any change you ask for happens
  afterwards in the main session.

## Step 9 — Daily use and upkeep

- Docker Desktop must be running whenever you want a call. Set it to start at login if you
  like.
- To switch between CPU and GPU, remove and re-add the registration (step 6).
- Docker's disk file grows and does not shrink by itself; see "Disk space on Windows" in
  [SETUP_DOCKER_CPU_GPU.md](SETUP_DOCKER_CPU_GPU.md).
- Want to understand what happens during a call? Read [ARCHITECTURE.md](ARCHITECTURE.md).
