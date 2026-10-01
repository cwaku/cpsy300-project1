from azure.storage.blob import BlobServiceClient
import pandas as pd
import io, json, os
from datetime import datetime

CONN = "UseDevelopmentStorage=true"   # points at local Azurite emulator
CONTAINER, BLOB = "datasets", "All_Diets.csv"

def process_nutritional_data_from_azurite():
    print(f"Function invoked at: {datetime.now()}")

    blob_service_client = BlobServiceClient.from_connection_string(CONN)
    container_client = blob_service_client.get_container_client(CONTAINER)
    blob_client = container_client.get_blob_client(BLOB)

    print(f"Downloading {BLOB} from Azurite container '{CONTAINER}'...")
    stream = blob_client.download_blob().readall()
    df = pd.read_csv(io.BytesIO(stream))

    numeric_cols = ["Protein(g)", "Carbs(g)", "Fat(g)"]
    for col in numeric_cols:
        df[col] = df[col].fillna(df[col].mean())

    avg_macros = df.groupby("Diet_type")[numeric_cols].mean()
    result = avg_macros.reset_index().to_dict(orient="records")
CONTAINER, BLOB = "datasets", "All_Diets.csv"