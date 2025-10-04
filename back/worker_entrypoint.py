"""
Standalone Worker Entrypoint for Railway Deployment
Runs only the APScheduler outbox worker without the FastAPI web server
"""

import asyncio
import os
import signal
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from src.workers.outbox_worker import start_worker, stop_worker
from src.utils.logger import log


class WorkerProcess:
    """Standalone worker process with graceful shutdown"""

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.worker_started = False

    async def start(self):
        """Start the worker with signal handlers"""
        log.info(
            "Starting standalone worker process",
            extra={
                "event_type": "worker_process_starting",
                "environment": os.getenv("ENV", "development"),
                "version": os.getenv("APP_VERSION", "0.1.1"),
            },
        )

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            # Start the outbox worker
            await start_worker()
            self.worker_started = True

            log.info(
                "Worker process started successfully",
                extra={"event_type": "worker_process_started"},
            )

            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except Exception as e:
            log.error(
                "Worker process failed to start",
                extra={
                    "event_type": "worker_process_failed",
                    "error": str(e),
                },
                exc_info=True,
            )
            sys.exit(1)

        finally:
            if self.worker_started:
                log.info(
                    "Stopping worker process",
                    extra={"event_type": "worker_process_stopping"},
                )
                await stop_worker()

            log.info(
                "Worker process stopped",
                extra={"event_type": "worker_process_stopped"},
            )

    async def shutdown(self):
        """Handle graceful shutdown"""
        log.info(
            "Shutdown signal received, stopping worker gracefully",
            extra={"event_type": "worker_process_shutdown_signal"},
        )
        self.shutdown_event.set()


async def main():
    """Main entrypoint for standalone worker"""
    worker_process = WorkerProcess()
    await worker_process.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Worker process interrupted by user")
        sys.exit(0)
    except Exception as e:
        log.error(
            "Fatal error in worker process",
            extra={"error": str(e)},
            exc_info=True,
        )
        sys.exit(1)
