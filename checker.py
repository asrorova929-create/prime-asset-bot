import time
import aiohttp

from config import REQUEST_TIMEOUT, SLOW_THRESHOLD


async def check_url(url: str):
    """
    Bitta URL manzilni tekshiradi.
    Qaytaradi: (status, code, response_time, error)
    """
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
    start = time.monotonic()
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, allow_redirects=True, ssl=False) as resp:
                elapsed = time.monotonic() - start
                code = resp.status

                if code >= 500:
                    return "down", code, elapsed, f"Server xatosi: {code}"
                if code >= 400:
                    return "down", code, elapsed, f"Sahifa topilmadi/ruxsat yo'q: {code}"
                if elapsed > SLOW_THRESHOLD:
                    return "slow", code, elapsed, None
                return "ok", code, elapsed, None

    except aiohttp.ClientConnectorError as e:
        return "down", None, None, f"Ulanib bo'lmadi: {e}"
    except aiohttp.ServerTimeoutError:
        return "down", None, None, "Vaqt tugadi (timeout)"
    except Exception as e:
        return "down", None, None, f"Xatolik: {e}"
