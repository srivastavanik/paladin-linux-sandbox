# sandbox_api/executor.py
import asyncio, shlex, subprocess
from typing import AsyncIterator

class ExecError(Exception): ...

async def stream_process(cmd: str, timeout: int | None = None) -> AsyncIterator[str]:
    """Yield stdout/stderr lines as SSE data."""
    proc = await asyncio.create_subprocess_exec(
        *shlex.split(cmd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        text=True
    )
    try:
        while True:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if not line:
                break
            yield line.rstrip("\n")
    finally:
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()

async def run_capture(cmd: str, timeout: int | None = None) -> tuple[int, str]:
    buf = []
    async for line in stream_process(cmd, timeout):
        buf.append(line)
    return 0, "\n".join(buf)
