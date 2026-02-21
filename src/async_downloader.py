import asyncio
from pathlib import Path
import aiohttp

from src.config import (
    USER_AGENT,
    ASYNC_CONNECTIONS,
    MAX_RETRIES,
    RETRY_BACKOFF_BASE,
)

async def fetch_file(session, url, path):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(256 * 1024):
                        f.write(chunk)
                return
        except Exception:
            if attempt == MAX_RETRIES:
                return
            await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

async def download_files_async(urls, download_path):
    connector = aiohttp.TCPConnector(limit=ASYNC_CONNECTIONS)
    timeout = aiohttp.ClientTimeout(total=None)

    async with aiohttp.ClientSession(
        connector=connector,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    ) as session:
        tasks = []
        for url in urls:
            filename = Path(url).name
            path = Path(download_path) / filename
            tasks.append(fetch_file(session, url, path))

        await asyncio.gather(*tasks)
		