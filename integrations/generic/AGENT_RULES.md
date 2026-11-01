# Phone-call rules for any agent

Paste this into whatever your agent reads as standing instructions: `AGENTS.md`, `GEMINI.md`,
a system prompt, Cursor rules, a custom-instructions box, and so on. It assumes your agent
has the Agent Hotline tools from the `ringback-voice` MCP server (see
[docs/CLIENTS.md](../../docs/CLIENTS.md)).

```markdown
# Phone calls

- You can phone the user and talk with them live, using the `ringback-voice` tools:
  `call_start` (ring and speak the opening line), `converse` (say something and listen, one
  turn at a time), `call_end` (hang up, optionally with a closing line). `speak`, `listen`,
  `get_conversation` and `call_status` are available for finer control.
- Standing order: whenever you need any input from the user or have any question for them,
  call them instead of asking in text. Also call when you finish your work.
- Do NOT call for tool-permission or approval prompts raised by your own client; those
  cannot be answered by phone.
- At the start of every call, say which project or task you are working on.
- If the call is not answered (`[NO ANSWER]`), do not retry. Ask the same question in text
  and carry on.
- Speak in short, plain sentences, one idea per turn (about 15 words). Never read logs, code,
  IDs or JSON aloud; offer to send details as text instead.
- On a finish call, walk the user through what you did, what changed, what is still open and
  anything risky, a few sentences at a time, pausing for questions.
- Speech-to-text can mishear. Before you act on a spoken instruction that changes or deletes
  something, repeat it back and get a clear yes.
- End every call with `call_end` and a short closing line.
```
