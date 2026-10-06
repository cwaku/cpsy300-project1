from azure.storage.blob import BlobServiceClient
import pandas as pd
import io, json, os
from datetime import datetime

# "UseDevelopmentStorage=true" is the SDK shorthand for the local Azurite
# emulator (http://127.0.0.1:10000/devstoreaccount1). When the function runs
# inside Docker Compose, Azurite is reachable as the "azurite" service instead
# of 127.0.0.1, so the connection string can be overridden via an env var.
CONN = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "UseDevelopmentStorage=true")
CONTAINER, BLOB = "datasets", "All_Diets.csv"

# Only these columns are needed for the per-diet averages. Reading just them
# (and loading Diet_type as a category) cuts parse time and dataframe memory
# compared with loading all eight columns as strings/floats.
NUMERIC_COLS = ["Protein(g)", "Carbs(g)", "Fat(g)"]
USE_COLS = ["Diet_type"] + NUMERIC_COLS

# azure-storage-blob 12.31 defaults to REST API version 2026-10-06, which the
# current Azurite release (3.37) rejects with "API version ... is not supported".
# Pin the newest version Azurite understands so the function works whether
# Azurite was started via npm, Docker or the VS Code extension.
API_VERSION = os.environ.get("AZURE_STORAGE_API_VERSION", "2026-06-06")

# Simulated NoSQL storage: one JSON document on local disk.
NOSQL_DIR = "simulated_nosql"
NOSQL_FILE = os.path.join(NOSQL_DIR, "results.json")


def process_nutritional_data_from_azurite():
    invoked_at = datetime.now()
    print(f"Function invoked at: {invoked_at}")

    blob_service_client = BlobServiceClient.from_connection_string(CONN, api_version=API_VERSION)
    container_client = blob_service_client.get_container_client(CONTAINER)
    blob_client = container_client.get_blob_client(BLOB)

    print(f"Downloading {BLOB} from Azurite container '{CONTAINER}'...")
    stream = blob_client.download_blob().readall()
    df = pd.read_csv(
        io.BytesIO(stream),
        usecols=USE_COLS,
        dtype={"Diet_type": "category"},
    )
    print(f"Loaded {len(df)} rows from blob storage")

    # Fill missing macronutrients with the column mean in one vectorised step
    df[NUMERIC_COLS] = df[NUMERIC_COLS].fillna(df[NUMERIC_COLS].mean())

    avg_macros = (
        df.groupby("Diet_type", observed=True)[NUMERIC_COLS].mean().round(2)
    )
    result = avg_macros.reset_index().to_dict(orient="records")

    # Save results locally as a JSON document (simulated NoSQL storage)
    document = {
        "processed_at": invoked_at.isoformat(timespec="seconds"),
        "source": f"{CONTAINER}/{BLOB}",
        "row_count": int(len(df)),
        "avg_macros_by_diet": result,
    }
    os.makedirs(NOSQL_DIR, exist_ok=True)
    with open(NOSQL_FILE, "w") as f:
        json.dump(document, f, indent=2)

    print(f"Stored {len(result)} diet-type records in {NOSQL_FILE}")
    print(f"Function completed at: {datetime.now()}")
    return "Data processed and stored successfully."


if __name__ == "__main__":
    print(process_nutritional_data_from_azurite())
