"""Gate D isolated Newsletter Studio ingress — not the general Engagement API.

This minimal ASGI application exposes exactly one synthetic draft POST route.
It should only be launched in an isolated staging process bound to 127.0.0.1,
with an approved, separately authenticated TLS reverse proxy / Access policy.
No public direct listener, SMTP, list/subscriber mutation or general API routes.
"""
import os

from fastapi import FastAPI

from .media07_studio_bridge_v1290 import router as draft_router


def create_gateway():
    # The gateway never includes main.app or broad service-authenticated routes.
    application = FastAPI(
        title="MEDIA-07.3 private draft ingress",
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    application.include_router(draft_router)
    return application


app = create_gateway()


if __name__ == "__main__":
    if os.getenv("SCEC_MEDIA07_GATE_D_LOCAL_DEV") != "1":
        raise SystemExit("Use the isolated systemd staging unit; no direct executable gateway launch.")
    import uvicorn

    uvicorn.run("app.media07_studio_gateway_v1291:app", host="127.0.0.1", port=18903, workers=1)
