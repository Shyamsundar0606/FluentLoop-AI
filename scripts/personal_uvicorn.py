"""Owned local server; a private stop file requests Uvicorn lifespan shutdown."""
import asyncio
import sys
from pathlib import Path

import uvicorn


async def serve(module, port, stop_file):
    server = uvicorn.Server(uvicorn.Config(module, host="127.0.0.1", port=port,
                                           timeout_graceful_shutdown=60))

    async def watch():
        while not server.should_exit:
            if stop_file.exists():
                server.should_exit = True
                return
            await asyncio.sleep(.25)

    watcher = asyncio.create_task(watch())
    try:
        await server.serve()
    finally:
        watcher.cancel()
        await asyncio.gather(watcher, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(serve(sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])))
