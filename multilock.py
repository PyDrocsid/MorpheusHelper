import asyncio


class MultiLock:
    def __init__(self):
        self.locks = {}
        self.requests = {}

    def __getitem__(self, key):
        multilock = self

        class Lock:
            async def __aenter__(self, *_):
                if key is not None:
                    await multilock.acquire(key)

            async def __aexit__(self, *_):
                if key is not None:
                    multilock.release(key)

        return Lock()

    async def acquire(self, key):
        lock = self.locks.setdefault(key, asyncio.Lock())
        self.requests[key] = self.requests.get(key, 0) + 1
        await lock.acquire()

    def release(self, key):
        lock = self.locks[key]
        lock.release()
        self.requests[key] -= 1
        if not self.requests[key]:
            self.locks.pop(key)
            self.requests.pop(key)
