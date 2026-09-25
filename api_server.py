"""Compatibility entrypoint for the AIR AGENTS FastAPI service."""

from air_agents_api.main import app  # noqa: F401

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("air_agents_api.main:app", host="0.0.0.0", port=8000, reload=True)
