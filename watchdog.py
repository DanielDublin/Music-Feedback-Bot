import subprocess
import time
import threading
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s watchdog %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Give a special name to the main script
threading.current_thread().name = "Watchdog"

def bot_process():
    # Give a special name to the bot thread
    current_thread = threading.current_thread()
    current_thread.name = "MusicFeedbackBot"

    # Determine the correct python executable for the current system
    # sys.executable returns the path to the python runner currently running this watchdog
    python_cmd = sys.executable

    while True:
        logger.info(f"Starting the bot in thread: {current_thread.name} using {python_cmd}...")

        # We use sys.executable to ensure we use the same python that started the watchdog
        bot_proc = subprocess.Popen([python_cmd, "bot.py"])

        # Monitor the bot process
        while True:
            if bot_proc.poll() is not None:
                # The bot process has exited (crashed)
                logger.warning("Bot went down (exit code %s). Restarting...", bot_proc.returncode)
                time.sleep(5)  # Optional delay before restarting
                break

            # Sleep briefly to prevent high CPU usage from polling
            time.sleep(1)

        # Delay between restarts to avoid rapid-fire crashing loops
        time.sleep(10)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_process)
    bot_thread.daemon = True  # Ensure the thread closes if the main process is killed
    bot_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Watchdog shutting down...")
