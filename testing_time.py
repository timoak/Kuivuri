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
 
PUBSUB_TOPIC = "koti_lampotila"
PROJECT_ID = "project-4831b4ac-2e18-452a-99a"
LOGGING_INTERVAL = 1000  # 1000 == 1 second

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
        

def publish_to_pubsub(current_time: str, sensor_1_value: float, topic_path: str | None = None) -> str:
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
     
    if topic_path is None:
        if not project or not topic:
            raise ValueError("PUBSUB_TOPIC and GOOGLE_CLOUD_PROJECT (or PROJECT_ID) must be set, or provide topic_path")
        topic_path = f"projects/{project}/topics/{topic}"

    print(f"Publishing to Pub/Sub topic: {topic_path}")
    #publisher = pubsub_v1.PublisherClient()
    message = {"current_time": current_time, "sensor_1": sensor_1_value}
    data = json.dumps(message).encode('utf-8')
    print("before", data)
    
    
    future = publisher.publish(topic_path, data, sensor_1=str(sensor_1_value), sensor2="3")
    
    try:
        future.result(timeout=1)
    except Exception as e:
        print("timeout")  # Block until the message is published
    return ""

def draw_sensor_graph(sensor_values):
    """Draw a line graph of sensor values with x-axis as time and y-axis as sensor value (float)."""
    global canvas
    if canvas:
        canvas.get_tk_widget().destroy()
    fig = plt.Figure(figsize=(5,4), dpi=100)
    ax = fig.add_subplot(111)
    times = [datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t, v in sensor_values]
    values = [v for t, v in sensor_values]
    ax.plot(times, values)
    ax.set_xlabel('Time')
    ax.set_ylabel('Sensor Value (float)')
    ax.set_title('Sensor Values over Time')
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

def update_time():
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    label.config(text=current_time)
    sensor_1_value = round(librtd.get(0,1),1)
    sensor1_label.config(text=f"Sensor 1: {sensor_1_value} C")
    sensor_values.append((current_time, sensor_1_value))


    print(sensor_values)
    append_to_csv(current_time, 1, sensor_1_value)
    draw_sensor_graph(sensor_values)

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
    publish_to_pubsub(current_time, sensor_1_value)
    root.after(LOGGING_INTERVAL, update_time)

def main():
    """Create and run the Tkinter GUI that shows current date and time.

    Keeps `root` and `label` as module globals so `update_time` can access them.
    """
    global root, label, sensor1_label, sensor_values, canvas
    root = tk.Tk()
    root.title("Current Date and Time")
    sensor_values = []
    canvas = None

    label = tk.Label(root, font=('Arial', 40), fg='black')
    label.pack(padx=20, pady=20)
    sensor1_label = tk.Label(root, font=('Arial', 40), fg='black')
    sensor1_label.pack(padx=20, pady=40)

   

    
    update_time()
    root.mainloop()


if __name__ == '__main__':
    # Append one timestamp each time the script is run directly.
    
    main()