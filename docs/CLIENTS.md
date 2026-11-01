# Using Agent Hotline with any agent or LLM

Agent Hotline is a standard **MCP server over stdio**. Any agent, IDE or framework that can
launch an MCP stdio server and call its tools can use it to phone you. The conversation
"brain" is whatever model that agent runs. The voice side (SIP, speech-to-text, text-to-speech)
is local and does not depend on any model or API key.

## What has and has not been tested

| Client | How to connect | Status |
|---|---|---|
| Claude Code | `claude mcp add` | **Tested** on Windows 11, CPU and GPU images, live calls |
| Plain Python (no framework) | [examples/call_from_python.py](../examples/call_from_python.py) | **Tested** (tool discovery; the call flow is adapted from the script used for the live test calls) |
| Claude Desktop, Cursor | JSON `mcpServers` | Config format taken from the clients' documentation; **not run here** |
| VS Code (Copilot agent mode) | JSON `servers` with `type` | Format from guides; **not run here** |
| OpenAI Codex CLI | TOML `[mcp_servers.<name>]` | Format from the [official docs](https://developers.openai.com/codex/mcp); **not run here** |
| Gemini CLI, Windsurf, Continue, others | their own MCP settings | **Not verified.** The command and arguments below are the same; check each client's docs for the file format |
| MCP SDKs and agent frameworks (Python, TypeScript, and frameworks that support MCP) | spawn the command as a stdio server | **Not run here** |
| Agents with no MCP support | not covered | would need a small wrapper |

"Not run here" means the setup should work because the protocol is standard, but nobody has
tried it with that client yet. If you try one, please report what happened.

## The command every client runs

Build an image first (see [SETUP_GUIDE.md](SETUP_GUIDE.md)) and create `voice.docker.env`.
Then every client starts the same process:

```text
CPU:  docker run -i --rm --env-file /path/to/voice.docker.env ringback
GPU:  docker run -i --rm --gpus all --env-file /path/to/voice.docker.env ringback-gpu
```

Use an absolute path. Do not add `--network host` on Docker Desktop.

## Per-client setup

**Claude Code** (tested)

```bash
claude mcp add ringback-voice --scope user -- docker run -i --rm --env-file /path/to/voice.docker.env ringback
```

**Claude Desktop, Cursor** (JSON, `mcpServers`)

```json
{
  "mcpServers": {
    "ringback-voice": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "--env-file", "/path/to/voice.docker.env", "ringback"]
    }
  }
}
```

Claude Desktop reads `claude_desktop_config.json`; Cursor reads `~/.cursor/mcp.json` (or
`.cursor/mcp.json` in a project). Restart the app after editing.

**VS Code** (`.vscode/mcp.json`, note the different top-level key)

```json
{
  "servers": {
    "ringback-voice": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "-i", "--rm", "--env-file", "/path/to/voice.docker.env", "ringback"]
    }
  }
}
```

**OpenAI Codex CLI** (`~/.codex/config.toml`; the key is `mcp_servers`, with an underscore)

```toml
[mcp_servers.ringback-voice]
command = "docker"
args = ["run", "-i", "--rm", "--env-file", "/path/to/voice.docker.env", "ringback"]
```

**Your own code.** Spawn the same command as a stdio MCP server with the MCP SDK for your
language, or start from [examples/call_from_python.py](../examples/call_from_python.py), which
speaks the protocol using only Python's standard library.

## Tell the agent when to call

Connecting the tools does not make an agent use them. Add standing instructions saying when to
phone you (any input or question, when work finishes), how to speak (short sentences, no logs
read aloud), and what to do if you do not answer.

- Any agent: paste [integrations/generic/AGENT_RULES.md](../integrations/generic/AGENT_RULES.md)
  into `AGENTS.md`, `GEMINI.md`, a system prompt, Cursor rules or a custom-instructions box.
- Claude Code: [integrations/claude-code/phone-caller.md](../integrations/claude-code/phone-caller.md)
  is a small subagent that holds the call, so the main model's context is not tied up in it.

## Things to know for any client

- **Tool timeouts.** `call_start` and `converse` block until you have answered and finished
  speaking. A call can take close to a minute (up to about 25 s to answer, a few seconds of
  speech, up to 15 s listening; estimated from the code). If your client times out tool calls,
  raise the limit to at least 90 seconds.
- **Keep standard output clean.** MCP uses stdout for messages. The voice engine's C library
  used to print about six log lines there when it started, which a strict client could reject.
  The code in this repo now keeps the protocol stream clean (checked: zero stray lines).
  **Images built before that change still print them**; rebuild to pick it up.
- **One call at a time.** Run a single call per account. Concurrent calls from several agents
  were not tested.
- **Smaller models** tend to talk too long. The rules file asks for about 15 words per turn;
  keep it.
- **Transcripts** from `get_conversation` label the two sides `AGENT:` and `USER:`.
- **Safety.** Speech-to-text can mishear. The rules ask the agent to repeat back any spoken
  instruction that changes or deletes something before acting on it.

## Check a client without ringing your phone

Most clients show the server's tools after connecting. You should see seven:
`call_start`, `converse`, `speak`, `listen`, `get_conversation`, `call_end`, `call_status`.
To check from the command line:

```bash
python examples/call_from_python.py --env-file /path/to/voice.docker.env --check
```
