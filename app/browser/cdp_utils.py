# app/browser/cdp_utils.py

async def cdp(tab, method, params=None, timeout=30):
    """Safe wrapper around raw CDP calls."""
    return await tab._connection_handler.execute_command(
        {"method": method, "params": params or {}}, timeout=timeout
    )
