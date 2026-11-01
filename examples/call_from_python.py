#!/usr/bin/env python3
"""Drive the Agent Hotline MCP server from plain Python (standard library only).

Shows the protocol with no agent framework: start the container, say hello over MCP, then
call the tools. Use it as a smoke test, or as a template for wiring the tools into your own
agent loop.

  # list the tools, do not ring anyone
  python examples/call_from_python.py --env-file voice.docker.env --check

  # ring the phone: the first line opens the call, each further line is one turn
  python examples/call_from_python.py --env-file voice.docker.env \
      "Hi, this is a test call. Can you hear me?" "Thanks, that is all."

Add --image ringback-gpu --gpus for the GPU image.
"""
import argparse
import json
import subprocess
import sys


class Server:
    def __init__(self, cmd):
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True)
        self.next_id = 0

    def _send(self, message):
        self.proc.stdin.write(json.dumps(message) + "\n")
        self.proc.stdin.flush()

    def request(self, method, params=None):
        self.next_id += 1
        self._send({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params or {}})
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("server closed the connection")
            try:
                message = json.loads(line)
            except ValueError:
                continue        # ignore any stray non-JSON line
            if isinstance(message, dict) and message.get("id") == self.next_id:
                return message["result"]

    def start(self):
        self.request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                    "clientInfo": {"name": "example", "version": "0"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, tool, **arguments):
        result = self.request("tools/call", {"name": tool, "arguments": arguments})
        return "".join(part.get("text", "") for part in result.get("content", []))

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.proc.kill()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env-file", required=True, help="path to voice.docker.env")
    ap.add_argument("--image", default="ringback", help="ringback (CPU) or ringback-gpu")
    ap.add_argument("--gpus", action="store_true", help="pass --gpus all (GPU image)")
    ap.add_argument("--check", action="store_true", help="list the tools and exit; no call")
    ap.add_argument("lines", nargs="*", help="opening line, then one line per turn")
    args = ap.parse_args()

    cmd = ["docker", "run", "-i", "--rm"] + (["--gpus", "all"] if args.gpus else []) \
        + ["--env-file", args.env_file, args.image]
    server = Server(cmd)
    in_call = False
    try:
        server.start()
        if args.check:
            for tool in server.request("tools/list")["tools"]:
                print(tool["name"])
            return 0
        if not args.lines:
            ap.error("give at least an opening line, or use --check")
        print("->", args.lines[0])
        in_call = True
        print("<-", server.call("call_start", opening_line=args.lines[0]))
        for line in args.lines[1:]:
            print("->", line)
            print("<-", server.call("converse", text=line))
        return 0
    finally:
        if in_call:
            print(server.call("call_end", text="Goodbye."))
        server.close()


if __name__ == "__main__":
    sys.exit(main())
