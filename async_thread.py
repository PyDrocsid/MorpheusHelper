import asyncio
import threading


class Thread(threading.Thread):
    def __init__(self, func, loop):
        super().__init__()
        self._return = None
        self._func = func
        self._event = asyncio.Event()
        self._loop = loop

    async def wait(self):
        await self._event.wait()
        return self._return

    def run(self):
        self._return = self._func()
        self._loop.call_soon_threadsafe(self._event.set)


async def run_in_thread(func):
    thread = Thread(func, asyncio.get_running_loop())
    thread.start()
    return await thread.wait()
