"""Entrypoint for containerized deploys.

Railway and Render inject the port as $PORT. Passing that through a start
command means relying on shell expansion, which silently fails when the
platform runs the command without a shell — uvicorn then gets the literal
string "$PORT". Reading it here keeps the start command free of variables.
"""

import os

import uvicorn

if __name__ == "__main__":
    # `or` rather than a get() default: an env var that is set but empty comes
    # back as "", which int() rejects.
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT") or 8000),
    )
