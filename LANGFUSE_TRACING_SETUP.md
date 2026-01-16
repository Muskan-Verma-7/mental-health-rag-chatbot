# Langfuse Tracing Setup - Complete Implementation

## Summary

Successfully implemented and tested Langfuse tracing with both manual instrumentation and OpenTelemetry automatic instrumentation. The system now properly captures and flushes traces to Langfuse.

## Changes Made

### 1. Fixed Langfuse API Compatibility (Langfuse v3)

**File**: `src/utils/tracing.py`

Updated the `end_trace()` and `end_span()` functions to use Langfuse v3 API:
- Changed from passing `output`, `metadata`, `status_message` to `end()` 
- Now calls `update()` before `end()` (v3 requirement)

### 2. Added Trace Flushing

**File**: `src/utils/tracing.py`

Added `flush_langfuse()` function to ensure traces are sent to Langfuse server:
```python
def flush_langfuse():
    """Flush pending traces to Langfuse."""
    client = get_langfuse()
    if client is not None:
        try:
            logger.info("flushing_langfuse_traces")
            client.flush()
            logger.info("langfuse_traces_flushed")
        except Exception as exc:
            logger.warning("langfuse_flush_failed", error=str(exc))
```

**File**: `src/api/dependencies.py`

Added flush on application shutdown:
```python
# Shutdown
logger.info("application_shutting_down")

# Flush Langfuse traces before shutdown
from ..utils.tracing import flush_langfuse
flush_langfuse()

# Cleanup resources if needed
logger.info("application_stopped")
```

**File**: `src/api/routes.py`

Added immediate flush after each request for better development experience:
- After successful responses
- After safety-blocked responses
- After no-documents responses
- After exception handling

### 3. OpenTelemetry Automatic Instrumentation

**Dependencies**: Added to project
- `opentelemetry-instrumentation-fastapi>=0.47b0`
- `opentelemetry-instrumentation-httpx>=0.47b0`

**File**: `src/main.py`

Added automatic instrumentation for:
- FastAPI HTTP requests/responses
- HTTPX outgoing HTTP calls (to Groq, Supabase, etc.)

```python
# Initialize OpenTelemetry instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

# Initialize Langfuse client early to register OTEL processors
langfuse_client = get_langfuse()
if langfuse_client:
    logger.info("langfuse_otel_ready", 
                message="OpenTelemetry instrumentation enabled with Langfuse")

# ... after app creation ...

# Instrument FastAPI for automatic OpenTelemetry tracing
FastAPIInstrumentor.instrument_app(app)

# Instrument HTTPX for outgoing HTTP requests
HTTPXClientInstrumentor().instrument()
```

## What You Get Now

### Manual Traces (Existing)
- Custom traces with `start_trace()`, `end_trace()`
- Custom spans for safety checks, retrieval, LLM generation
- Full control over what gets traced

### Automatic Traces (New - OpenTelemetry)
- All HTTP requests to your FastAPI endpoints
- All outgoing HTTP requests (Groq LLM, Supabase queries)
- Automatic parent-child span relationships
- HTTP status codes, methods, URLs
- Request/response timing

## Testing Results

All tests passed successfully:
- ✅ Traces created without API errors
- ✅ Traces flushed successfully on each request
- ✅ Traces flushed on application shutdown
- ✅ OpenTelemetry instrumentation enabled
- ✅ No warnings or errors in logs

## Verifying Traces in Langfuse

1. **Go to your Langfuse dashboard**: https://cloud.langfuse.com
2. **Navigate to**: Home → Traces
3. **You should see**:
   - Trace name: `chat_request`
   - Multiple spans per request:
     - FastAPI HTTP request (automatic)
     - `safety_check` (manual)
     - `retrieval` (manual)
     - `llm_generate` (manual)
     - HTTPX requests to Groq/Supabase (automatic)
   - Metadata: request_id, user_id, path
   - Outputs: safety_status, sources_used, latency_ms

## Log Messages to Look For

**Successful tracing shows**:
```
{"host": "https://cloud.langfuse.com", "event": "langfuse_initialized", "level": "info"}
{"message": "OpenTelemetry instrumentation enabled with Langfuse", "event": "langfuse_otel_ready", "level": "info"}
{"event": "flushing_langfuse_traces", "level": "info"}
{"event": "langfuse_traces_flushed", "level": "info"}
```

## Troubleshooting

If traces still don't appear:

1. **Verify environment variables** are set correctly:
   ```bash
   echo $LANGFUSE_PUBLIC_KEY
   echo $LANGFUSE_SECRET_KEY
   ```

2. **Check Langfuse project** - Make sure you're looking at the correct project in the dashboard

3. **Wait a moment** - Even with immediate flush, there can be a 1-2 second delay before traces appear in the UI

4. **Check for errors** in the logs:
   ```bash
   grep -i "langfuse.*failed" logs
   ```

## Performance Impact

- **Minimal overhead**: OpenTelemetry is designed for production use
- **Async flushing**: Traces are sent in the background
- **Tested latency**: No significant performance degradation observed

## Next Steps (Optional)

1. **Filter spans**: Add `blocked_instrumentation_scopes` if you want to exclude certain automatic traces
2. **Custom attributes**: Add more metadata to spans using span.set_attribute()
3. **Sampling**: Configure sampling rates for production to reduce trace volume
4. **Alerting**: Set up Langfuse alerts for error rates or latency thresholds

## Files Modified

1. `src/utils/tracing.py` - Fixed API, added flush function
2. `src/api/dependencies.py` - Added shutdown flush
3. `src/api/routes.py` - Added request-level flush
4. `src/main.py` - Added OpenTelemetry instrumentation
5. `requirements.txt` - Added OpenTelemetry packages

---

**Implementation Date**: January 16, 2026
**Status**: ✅ Complete and tested
