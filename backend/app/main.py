from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import get_redis, lifespan


class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[2])
end
if count > tonumber(ARGV[1]) then
  return -count
end
return count
"""

    async def dispatch(self, request: Request, call_next):
        redis_cli = get_redis()
        if redis_cli is not None:
            client_ip = request.client.host if request.client else "unknown"
            route = request.url.path
            key = f"ratelimit:{client_ip}:{route}"
            try:
                count = redis_cli.eval(
                    self.SCRIPT,
                    1,
                    key,
                    settings.RATE_LIMIT_REQUESTS,
                    settings.RATE_LIMIT_WINDOW_SECONDS,
                )
                if isinstance(count, int) and count < 0:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Demasiadas solicitudes"},
                        headers={"Retry-After": str(settings.RATE_LIMIT_WINDOW_SECONDS)},
                    )
            except RedisError:
                # Redis degrade: availability remains protected by MongoDB.
                pass
        return await call_next(request)


app = FastAPI(
    title="TicketFlow API",
    version="0.1.0",
    description="API REST para gestión de eventos y boletería",
    lifespan=lifespan,
)

app.add_middleware(RedisRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "TicketFlow API"}
