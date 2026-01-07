"""Main entry point for the emailer service."""

import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("Emailer service starting...")
    # TODO: Implement main loop
    logger.info("Emailer service stopped.")


if __name__ == "__main__":
    asyncio.run(main())
