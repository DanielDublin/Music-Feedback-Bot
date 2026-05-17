import subprocess
import time
import threading
import sys
import logging
from collections import deque

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s watchdog %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Give a special name to the main script
threading.current_thread().name = "Watchdog"

# Crash-loop detection. If the bot exits N times within WINDOW seconds, back
# off for BACKOFF seconds instead of the normal short delay. Prevents the
# watchdog from hammering Discord (and the log mirror) when something is
# fundamentally broken and every restart fails immediately.
_CRASH_LOOP_THRESHOLD = 5
_CRASH_LOOP_WINDOW_SEC = 60
_CRASH_LOOP_BACKOFF_SEC = 300

def bot_process():
    # Give a special name to the bot thread
    current_thread = threading.current_thread()
    current_thread.name = "MusicFeedbackBot"

    # Determine the correct python executable for the current system
    # sys.executable returns the path to the python runner currently running this watchdog
    python_cmd = sys.executable

    recent_crashes: deque[float] = deque()

    while True:
        logger.info(f"Starting the bot in thread: {current_thread.name} using {python_cmd}...")

        # We use sys.executable to ensure we use the same python that started the watchdog
        bot_proc = subprocess.Popen([python_cmd, "bot.py"])

        # Monitor the bot process
        while True:
            if bot_proc.poll() is not None:
                # The bot process has exited (crashed)
                logger.warning("Bot went down (exit code %s). Restarting...", bot_proc.returncode)
                break

            # Sleep briefly to prevent high CPU usage from polling
            time.sleep(1)

        # Crash bookkeeping: record this exit, prune old entries.
        now = time.time()
        recent_crashes.append(now)
        while recent_crashes and recent_crashes[0] < now - _CRASH_LOOP_WINDOW_SEC:
            recent_crashes.popleft()

        if len(recent_crashes) >= _CRASH_LOOP_THRESHOLD:
            logger.critical(
                "Crash loop detected: %d exits in %ds. Backing off %ds before next restart.",
                len(recent_crashes), _CRASH_LOOP_WINDOW_SEC, _CRASH_LOOP_BACKOFF_SEC,
            )
            time.sleep(_CRASH_LOOP_BACKOFF_SEC)
            recent_crashes.clear()
        else:
            time.sleep(5)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_process)
    bot_thread.daemon = True  # Ensure the thread closes if the main process is killed
    bot_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Watchdog shutting down...")
