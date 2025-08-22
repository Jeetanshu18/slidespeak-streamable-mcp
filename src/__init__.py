from . import server
import asyncio


def main():
    """Main entry point for the package."""

    try:
        # start_server is now an async function, so this is correct
        # asyncio.run(server.main())
        asyncio.run(server.start_server())
    except KeyboardInterrupt:
        server.logger.info("Server shutdown requested")
    except Exception as e:
        server.logger.error(f"Server error: {e}", exc_info=True)
        raise


# Optionally expose other important items at package level
__all__ = ["main", "server"]
