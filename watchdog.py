import subprocess
import time
import threading

# Give a special name to the main script
threading.current_thread().name = "Watchdog"

def bot_process():
    # Give a special name to the bot thread
    current_thread = threading.current_thread()
    current_thread.name = "MusicFeedbackBot"

    while True:
        print(f"Starting the bot in thread: {current_thread.name}...")
        bot_process = subprocess.Popen(["python3", "bot.py"])

        # Monitor the bot process
        while True:
            if bot_process.poll() is not None:
                # The bot process has exited (crashed)
                print("Bot went down. Restarting...")
                time.sleep(5)  # Optional delay before restarting
                break

        # Optional: Add a delay between restarts to avoid constant restarts
        time.sleep(10)  # Adjust the delay as needed

if __name__ == "__main__":
    bot_thread = threading.Thread(target=bot_process)
    bot_thread.start()
    bot_thread.join()  # Wait for the thread to finish (this line is optional)
