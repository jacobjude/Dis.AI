import psutil
import subprocess
from time import sleep
def check_script_running(script_name):
    for process in psutil.process_iter():
        try:
            if (process.name() == 'python' or process.name() == "python3.10") and script_name in process.cmdline():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def launch_script(script_name):
    subprocess.Popen(['python3.10', script_name])

# Usage
if __name__ == '__main__':
    while True:
        script_name = 'main.py' 
        is_running = check_script_running(script_name)
        if is_running:
            print(f"The script '{script_name}' is already running.")
            
        else:
            print(f"The script '{script_name}' is not running. Launching it...")
            launch_script(script_name)
        sleep(300) # check that the bot is running every 5 mins
