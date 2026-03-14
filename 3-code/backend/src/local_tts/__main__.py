"""Entry point for running the application: python -m local_tts."""

import uvicorn

from local_tts import config


def main() -> None:
    """Start the Uvicorn server and display the UI URL."""
    print(f"Starting Local TTS Web App at http://{config.HOST}:{config.PORT}")
    uvicorn.run(
        "local_tts.app:app",
        host=config.HOST,
        port=config.PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
