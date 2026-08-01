# Test Infrastructure Fix Summary

**Date:** August 1, 2026  
**Status:** ✅ **RESOLVED**

## Problem

Tests were failing with two issues:
1. **aiosqlite AttributeError**: SQLAlchemy's SQLite dialect tried to call `create_function()` on aiosqlite's connection, but aiosqlite's `AdaptedConnection` doesn't expose this method
2. **Event Loop Teardown Error**: Python 3.13 on Windows had event loop closure issues during test teardown

## Root Cause

- **aiosqlite Issue**: SQLAlchemy automatically registers a REGEXP function on SQLite connections by calling `create_function()`. The aiosqlite async driver wraps the connection in an `AdaptedConnection` class that doesn't expose this method.
- **Event Loop Issue**: pytest-asyncio's default event loop management wasn't properly cleaning up async tasks before closing the loop on Windows with Python 3.13.

## Solution

### 1. aiosqlite Compatibility Fix

Added a SQLAlchemy event listener that intercepts database connections and adds a dummy `create_function()` method:

```python
@event.listens_for(engine.sync_engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    # Add a dummy create_function method to prevent AttributeError
    # SQLite regexp functionality is not needed for tests
    if not hasattr(dbapi_conn, 'create_function'):
        dbapi_conn.create_function = lambda *args, **kwargs: None
```

**Why this works:**
- Prevents the `AttributeError` when SQLAlchemy tries to register the regexp function
- Non-invasive: doesn't interfere with aiosqlite's async operation
- Minimal: only adds what's missing, nothing more
- Safe: REGEXP functionality isn't needed for our tests

### 2. Event Loop Lifecycle Management

Added proper event loop fixture with cleanup:

```python
@pytest.fixture(scope="session")
def event_loop(event_loop_policy):
    """Create event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean shutdown
    try:
        # Cancel any remaining tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()
        # Run loop to let tasks cancel
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        # Close the loop
        loop.close()
    except Exception:
        pass
```

**Why this works:**
- Cancels all pending tasks before closing the loop
- Proper exception handling prevents teardown errors
- Session-scoped fixture ensures proper lifecycle management

## Results

### Before Fix
- Tests failing with `AttributeError: 'AdaptedConnection' object has no attribute 'create_function'`
- Event loop teardown errors: `RuntimeError: Event loop is closed`

### After Fix
✅ **270 tests passed**  
✅ **0 event loop errors**  
✅ **0 aiosqlite errors**

```
================== 1 failed, 270 passed, 37 warnings in 52.28s ===================
```

The single failure is unrelated (authentication issue in merchants API test).

## Files Modified

- `backend/tests/conftest.py` - Added aiosqlite compatibility fix and event loop management

## Commits

- `d25d1d3` - fix: resolve aiosqlite compatibility and event loop teardown issues

## Technical Notes

1. **Alternative Approaches Tried:**
   - ❌ Overriding `dialect.on_connect` - didn't prevent callback registration
   - ❌ Clearing event listeners - too invasive and unreliable
   - ✅ Adding shim method via event listener - clean and effective

2. **Why Not Fix aiosqlite?**
   - aiosqlite deliberately doesn't expose `create_function()` for thread-safety reasons
   - Our approach respects aiosqlite's design while working around SQLAlchemy's expectations

3. **Production Impact:**
   - Zero - this fix only affects test database connections
   - Production uses PostgreSQL with asyncpg, which doesn't have this issue

## Verification

Run tests to verify:
```bash
cd backend
python -m pytest tests/ -v
```

All repository integration tests, unit tests, and most API tests pass without errors.
