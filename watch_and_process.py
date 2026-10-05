import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from lambda_function import process_nutritional_data_from_azurite

class CSVHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith("All_Diets.csv"):
            print(f"Detected change in {event.src_path}, reprocessing...")
            process_nutritional_data_from_azurite()

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(CSVHandler(), path="data", recursive=False)
    observer.start()
    print("Watching data/All_Diets.csv for changes... (Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
