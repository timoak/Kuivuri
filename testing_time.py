import tkinter as tk
import time
import csv
import random
import datetime
import os
import logging
from google.cloud import pubsub_v1
import librtd
from google.oauth2 import service_account
from google.auth import jwt
import requests
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
 
# PUBSUB_TOPIC = "koti_lampotila"
PUBSUB_TOPIC = "kuivuri_panelia"
PROJECT_ID = "project-4831b4ac-2e18-452a-99a"
LOGGING_INTERVAL = 1000  # 1000 == 1 second

canvases = {}

sensor_values = []
sensor_labels = []
sensor_titles = ["Sisääntuloa lämpötila", "Ulkotila lämpötila", "Ulostulos lämpötila","Viljan lämpötila"]
number_of_sensors = 4
root = None
label = None
sensor1_label = None

# source .venv/bin/activate

def append_datetime_to_csv(path: str = 'date_testing.csv') -> None:
    """Append the current date and time to a CSV file.

    Writes one row with two columns: `YYYY-MM-DD`, `HH:MM:SS`.
    File is opened in append mode with UTF-8 encoding.
    """
    now = datetime.datetime.now()
    date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    rnd = random.randint(1,100)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([date_str, rnd])
def append_to_csv(timestamp: str, sensor_id: int, sensor_value: float, path: str = 'sensor_data.csv') -> None:
    """Append sensor data with timestamp to a CSV file.

    Writes one row with three columns: `timestamp`, `sensor_id`, `sensor_value`.
    File is opened in append mode with UTF-8 encoding.
    """
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, sensor_id, sensor_value])
        

def publish_to_pubsub(current_time: str, sensor_value: float, sensor_id: int | None = None) -> str:
    """Publish a JSON message with current_time, sensor1 and constant to a Google Pub/Sub topic.

    Behavior:
    - If `topic_path` is provided it is used directly (example: "projects/PROJECT/topics/TOPIC").
    - Otherwise `GOOGLE_CLOUD_PROJECT` (or `PROJECT_ID`) and `PUBSUB_TOPIC` environment variables are used.
    - Requires `google-cloud-pubsub` to be installed in the environment.

    Returns the publish future result (message id) as string.
    """
    import json
    try:
        from google.cloud import pubsub_v1
    except Exception as exc:  # ImportError or other
        raise ImportError("google-cloud-pubsub is required. Install with: pip install google-cloud-pubsub") from exc

    # project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PROJECT_ID')
    topic = PUBSUB_TOPIC
    project = PROJECT_ID
    
    # Setting up credentials
    service_account_info = json.load(open("service-account/kotilampo-service-account-key.json"))
    publisher_audience = "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    
    credentials = jwt.Credentials.from_service_account_info(
        service_account_info, audience=publisher_audience
    )

    # Create credentials with the appropriate audience
    publisher = pubsub_v1.PublisherClient(credentials=credentials)
    topic_path = None

    if topic_path is None:
        if not project or not topic:
            raise ValueError("PUBSUB_TOPIC and GOOGLE_CLOUD_PROJECT (or PROJECT_ID) must be set, or provide topic_path")
        topic_path = f"projects/{project}/topics/{topic}"

    print(f"Publishing to Pub/Sub topic: {topic_path}")
    #publisher = pubsub_v1.PublisherClient()
    message = {"current_time": current_time, "sensor": sensor_value, "sensor_id": sensor_id}
    data = json.dumps(message).encode('utf-8')
    print("before", data)
    
    
    future = publisher.publish(topic_path, data, sensor_1=str(sensor_value), sensor=str(sensor_id))
    
    try:
        future.result(timeout=1)
    except Exception as e:
        print("timeout")  # Block until the message is published
    return ""

def shutdown_raspberry_pi(*, confirm: bool = False, delay_seconds: int = 0, reboot: bool = False, dry_run: bool = False) -> int:
        """Safely shutdown or reboot the Raspberry Pi.

        Safety-first behavior:
        - This function will NOT run the shutdown command unless `confirm=True` is passed.
        - Use `dry_run=True` to print the command without executing it.

        Parameters:
        - confirm: explicitly allow the system command to run (default False).
        - delay_seconds: number of seconds to wait before shutdown. If 0 the shutdown is immediate.
        - reboot: if True, perform a reboot instead of halt.
        - dry_run: if True, don't execute the command; just print it.

        Returns the exit code from the executed command (or 0 for a dry-run).

        Example:
            # just show command
            shutdown_raspberry_pi(confirm=False, dry_run=True)

            # actually shutdown (requires sudo/root)
            shutdown_raspberry_pi(confirm=True)
        """
        import subprocess
        import math

        if not confirm and not dry_run:
            raise RuntimeError("Refusing to shutdown: pass confirm=True to actually perform shutdown")

        # compute shutdown time for the `shutdown` command (uses minutes)
        if delay_seconds <= 0:
            when = "now"
        else:
            minutes = max(1, int(math.ceil(delay_seconds / 60.0)))
            when = f"+{minutes}"

        action = "-r" if reboot else "-h"
        cmd = ["shutdown", action, when]

        # If we're not root, use sudo when executing (but still show the full command on dry-run)
        needs_sudo = False
        try:
            needs_sudo = (os.geteuid() != 0)
        except Exception:
            # on non-unix systems os.geteuid may not exist; fall back to not requiring sudo
            needs_sudo = False

        full_cmd = (["sudo"] + cmd) if needs_sudo else cmd

        if dry_run:
            print("DRY RUN: would execute:", " ".join(full_cmd))
            return 0

        # Execute the command. This will shut down or reboot the machine.
        try:
            completed = subprocess.run(full_cmd, check=False)
            return completed.returncode
        except FileNotFoundError:
            raise RuntimeError("shutdown command not found on this system")


def publish_to_pubsub_array(current_time: str, values: list)-> str:
    """Publish a JSON message with current_time, sensor1 and constant to a Google Pub/Sub topic.

    Behavior:
    - If `topic_path` is provided it is used directly (example: "projects/PROJECT/topics/TOPIC").
    - Otherwise `GOOGLE_CLOUD_PROJECT` (or `PROJECT_ID`) and `PUBSUB_TOPIC` environment variables are used.
    - Requires `google-cloud-pubsub` to be installed in the environment.

    Returns the publish future result (message id) as string.
    """
    import json
    try:
        from google.cloud import pubsub_v1
    except Exception as exc:  # ImportError or other
        raise ImportError("google-cloud-pubsub is required. Install with: pip install google-cloud-pubsub") from exc

    # project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('PROJECT_ID')
    topic = PUBSUB_TOPIC
    project = PROJECT_ID
    
    # Setting up credentials
    service_account_info = json.load(open("service-account/kotilampo-service-account-key.json"))
    publisher_audience = "https://pubsub.googleapis.com/google.pubsub.v1.Publisher"
    
    credentials = jwt.Credentials.from_service_account_info(
        service_account_info, audience=publisher_audience
    )

    # Create credentials with the appropriate audience
    publisher = pubsub_v1.PublisherClient(credentials=credentials)
    topic_path = None

    if topic_path is None:
        if not project or not topic:
            raise ValueError("PUBSUB_TOPIC and GOOGLE_CLOUD_PROJECT (or PROJECT_ID) must be set, or provide topic_path")
        topic_path = f"projects/{project}/topics/{topic}"

    print(f"Publishing to Pub/Sub topic: {topic_path}")
    #publisher = pubsub_v1.PublisherClient()
    message = {"current_time": current_time, "sensor_1": values[0], "sensor_2": values[1],"sensor_3": values[2],"sensor_4": values[3]}
    data = json.dumps(message).encode('utf-8')
    print("Measurements: ", data)
    
    
    future = publisher.publish(topic_path, data, sensor_1=str(values[0]), sensor_2=str(values[1]), sensor_3=str(values[2]), sensor_4=str(values[3]))
    
    try:
        future.result(timeout=1)
    except Exception as e:
        print("timeout")  # Block until the message is published
    return ""


def draw_sensor_graph(sensor_values, position_x, position_y, title="Sensor Values Over Time", clear_canvas=False):
    """Draw a line graph of sensor values with x-axis as minutes since first measurement and y-axis as sensor value (float)."""
    key = (position_x, position_y)
    if key in canvases:
        canvases[key].get_tk_widget().destroy()
        del canvases[key]
    fig = plt.Figure(figsize=(5,4), dpi=100)
    ax = fig.add_subplot(111)
    if sensor_values:
        times = [datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t, v in sensor_values]
        values = [v for t, v in sensor_values]
        start_time = times[0]
        minutes_passed = [(t - start_time).total_seconds() / 60 for t in times]
        ax.plot(minutes_passed, values)
        ax.set_xlabel('Minuutteja kuivauksen alusta')
        ax.set_ylabel('Lämpötila (C)')
        ax.set_title(title)
    canvases[key] = FigureCanvasTkAgg(fig, master=root)
    canvases[key].draw()
    canvases[key].get_tk_widget().grid(row=2 + position_y, column=position_x, sticky='nsew')

def update_time():
    global root, label, sensor1_label, sensor_values
    
    sensor_1_value = round(librtd.get(0,1),1)
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')    

    label.config(text=current_time)   
    sensor_labels[0].config(text=f"Kellonaika: {current_time}")
    for i in range(number_of_sensors):
         sensor_value = round(librtd.get(0, i+1), 1)
         # If the first sensor (index 0) exceeds 23 degrees, initiate shutdown sequence with confirmation and delay. This is a safety measure to prevent overheating.
       # Shutdown is commented out for safety during testing; uncomment to enable.
       #  if i == 0 and sensor_value > 23:
        #    shutdown_raspberry_pi(confirm=True, delay_seconds=4, reboot=False, dry_run=False)
         sensor_labels[i+1].config(text=f"{sensor_titles[i]} {i+1}: {sensor_value} °C")
         sensor_values.append((current_time, sensor_value))
         append_to_csv(current_time, i+1, sensor_value)
   

    # Julkaisee kaikki sensorit kerralla, jotta ei tarvitse odottaa publishin valmistumista joka sensorille erikseen. Tämä on tärkeää, koska publish_to_pubsub on hidas ja muuten GUI loop hidastuisi merkittävästi.
    publish_to_pubsub_array(current_time, [round(librtd.get(0, i+1), 1) for i in range(number_of_sensors)])

    
    root.after(LOGGING_INTERVAL, update_time)

    

    #sensor_labels[0].config(text=f"Sensor 1: {sensor_1_value} °C")
    #sensor_labels[1].config(text=f"Sensor 2: {sensor_1_value} °C")
    #sensor_values.append((current_time, sensor_1_value))


    #append_to_csv(current_time, 1, sensor_1_value)
   # draw_sensor_graph(sensor_values, 0, 0, "Sisääntuloa lämpötila", True)
   # draw_sensor_graph(sensor_values, 1, 0, "Ulkotila lämpötila")
   # draw_sensor_graph(sensor_values, 0, 1, "Ulostulos lämpötila")
   # draw_sensor_graph(sensor_values, 1, 1, "Viljan lämpötila")
   # draw_sensor_graph(sensor_values, 2, 0, "Viljankosteuden ennuste")

    # Optionally publish to Google Pub/Sub. Enable by setting `ENABLE_PUBSUB=1` in environment.
    # Configure publish constant with `PUBSUB_CONSTANT` env var (defaults to 1.0).
    if os.environ.get('ENABLE_PUBSUB', '').lower() in ('1', 'true', 'yes'):
        try:
            constant = float(os.environ.get('PUBSUB_CONSTANT', '1.0'))
        except ValueError:
            constant = 1.0
        try:
            publish_to_pubsub(current_time, sensor_1_value, constant)
        except Exception:
            # Fail silently to avoid crashing the GUI loop; in a real app you may want to log this.
            pass
   # publish_to_pubsub(current_time, sensor_1_value)
    #root.after(LOGGING_INTERVAL, update_time)

def main():
    """Create and run the Tkinter GUI that shows current date and time.

    Keeps `root` and `label` as module globals so `update_time` can access them.
    """
    global root, label, sensor1_label, sensor_values, sensor_labels
    root = tk.Tk()
    root.title("Current Date and Time")    
    sensor_values = []
    for i in range(number_of_sensors+1):
        label = tk.Label(root, font=('Arial', 40), fg='black')
        label.grid(row=i, column=0, padx=20, pady=20, sticky='w')
        sensor_labels.append(label)

    update_time()
    root.mainloop()


if __name__ == '__main__':
    # Append one timestamp each time the script is run directly.
    
    main()