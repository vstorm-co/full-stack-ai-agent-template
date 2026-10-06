# Observability with Logfire

[Logfire](https://logfire.pydantic.dev) is a modern observability platform built by the Pydantic team. It provides first-class support for Python applications, especially those using Pydantic, FastAPI, and Pydantic AI.

## Why Logfire?

- **Built for Python** - Native support for async, type hints, and Pydantic models
- **AI-First** - Deep integration with Pydantic AI for agent observability
- **OpenTelemetry Compatible** - Works with any OTEL instrumentation
- **Beautiful UI** - Modern dashboard with powerful query capabilities

## Supported Integrations

### Pydantic AI Agents

Full visibility into AI agent execution:

```python
import logfire
from pydantic_ai import Agent

logfire.configure()
logfire.instrument_pydantic_ai()

agent = Agent("openai:gpt-4o-mini")

# All agent runs are automatically traced
result = await agent.run("Hello!")
```

What you see in Logfire:
- Agent run duration and status
- Tool calls with arguments and results
- LLM requests and responses
- Token usage and costs
- Streaming events

### FastAPI

Automatic request/response tracing:

```python
from fastapi import FastAPI
import logfire

app = FastAPI()
logfire.configure()
logfire.instrument_fastapi(app)
```

What you see:
- Request method, path, status code
- Request/response latency
- Query parameters and headers
- Exception details on errors

### Databases

#### PostgreSQL (asyncpg)

```python
import logfire

logfire.instrument_asyncpg()
```

What you see:
- Query text and parameters
- Execution time
- Row counts
- Connection pool stats

#### MongoDB (PyMongo/Motor)

```python
import logfire

logfire.instrument_pymongo()
```

What you see:
- Collection operations
- Query filters
- Execution time
- Document counts

### Redis

```python
import logfire

logfire.instrument_redis()
```

What you see:
- Command type (GET, SET, etc.)
- Key patterns
- Latency
- Cache hit/miss patterns

### Background Tasks

#### Celery

```python
import logfire

logfire.instrument_celery()
```

What you see:
- Task name and arguments
- Execution time
- Worker info
- Retry attempts
- Queue depth

#### Taskiq

```python
import logfire

logfire.instrument_taskiq()
```

### HTTP Clients (HTTPX)

```python
import logfire

logfire.instrument_httpx()
```

What you see:
- Request URL and method
- Response status code
- Latency
- Request/response size

## Configuration

### Environment Variables

```bash
# Required
LOGFIRE_TOKEN=your-token-here

# Optional
LOGFIRE_PROJECT_NAME=my-project
LOGFIRE_ENVIRONMENT=production
LOGFIRE_SERVICE_VERSION=1.0.0
```

### Selective Instrumentation

In the generator, you can choose which components to instrument:

```bash
fastapi-fullstack new
# ✓ Enable Logfire observability
#   ✓ Instrument FastAPI
#   ✓ Instrument Database
#   ✓ Instrument Redis
#   ✓ Instrument Celery
#   ✓ Instrument HTTPX
```

### Generated Code

When Logfire is enabled, your `app/main.py` includes:

```python
import logfire

# Configure Logfire
logfire.configure()

# Instrument based on your selections
logfire.instrument_fastapi(app)
logfire.instrument_asyncpg()  # if PostgreSQL
logfire.instrument_pymongo()  # if MongoDB
logfire.instrument_redis()    # if Redis
logfire.instrument_celery()   # if Celery
logfire.instrument_httpx()    # if HTTPX instrumentation enabled
```

## Custom Instrumentation

### Manual Spans

Add custom spans for important operations:

```python
import logfire

async def process_order(order: Order):
    with logfire.span("process_order", order_id=str(order.id)):
        with logfire.span("validate"):
            await validate_order(order)

        with logfire.span("charge_payment"):
            await charge_payment(order)

        with logfire.span("send_confirmation"):
            await send_confirmation(order)
```

### Logging

Logfire integrates with Python's logging:

```python
import logfire

logfire.info("User registered", user_id=user.id, email=user.email)
logfire.warning("Rate limit approaching", current=95, limit=100)
logfire.error("Payment failed", order_id=order.id, error=str(e))
```

### Metrics

Track custom metrics:

```python
import logfire

# Counter
logfire.metric_counter("orders_processed", 1, tags={"status": "success"})

# Gauge
logfire.metric_gauge("queue_depth", queue.size())

# Histogram
logfire.metric_histogram("response_time", latency_ms)
```

## Best Practices

### 1. Use Structured Logging

```python
# Good - structured data
logfire.info("Order created", order_id=order.id, total=order.total)

# Avoid - string interpolation
logfire.info(f"Order {order.id} created with total {order.total}")
```

### 2. Add Context to Spans

```python
with logfire.span("api_call",
    service="payment-gateway",
    operation="charge",
    amount=order.total
):
    result = await payment_api.charge(order)
```

### 3. Handle Errors Properly

```python
try:
    result = await risky_operation()
except Exception as e:
    logfire.exception("Operation failed", operation="risky")
    raise
```

### 4. Use Tags for Filtering

```python
logfire.info("Request processed",
    environment=settings.ENVIRONMENT,
    version=settings.VERSION,
    user_tier=user.subscription_tier
)
```

## Viewing Data

### Logfire Dashboard

Access your traces at [logfire.pydantic.dev](https://logfire.pydantic.dev):

1. **Live Tail** - Real-time log streaming
2. **Trace Explorer** - Distributed trace visualization
3. **Query Builder** - SQL-like queries on your data
4. **Dashboards** - Custom visualizations

### Example Queries

```sql
-- Slow API endpoints
SELECT path, avg(duration_ms) as avg_latency
FROM spans
WHERE service = 'fastapi'
GROUP BY path
ORDER BY avg_latency DESC
LIMIT 10

-- Failed AI agent runs
SELECT *
FROM spans
WHERE span_name = 'agent.run'
  AND status = 'error'
ORDER BY timestamp DESC

-- Token usage by model
SELECT model, sum(tokens_used) as total_tokens
FROM spans
WHERE span_name LIKE 'llm.%'
GROUP BY model
```

## Troubleshooting

### No Data Appearing

1. Check `LOGFIRE_TOKEN` is set correctly
2. Verify network connectivity to Logfire
3. Check for initialization errors in logs

### Missing Spans

1. Ensure instrumentation is called after app creation
2. Check that the library version is compatible
3. Verify the component is actually being used

### High Cardinality Warnings

1. Avoid dynamic values in span names
2. Use tags/attributes for variable data
3. Consider sampling for high-volume endpoints

## Resources

- [Logfire Documentation](https://logfire.pydantic.dev/docs/)
- [Integrations Guide](https://logfire.pydantic.dev/docs/integrations/)
- [Pydantic AI Integration](https://logfire.pydantic.dev/docs/integrations/pydantic-ai/)
- [FastAPI Integration](https://logfire.pydantic.dev/docs/integrations/fastapi/)
- [OpenTelemetry Compatibility](https://logfire.pydantic.dev/docs/integrations/opentelemetry/)
