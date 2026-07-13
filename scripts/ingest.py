"""Ingest LendingClub data: Kaggle -> GCS (raw) -> BigQuery (raw).

Env-driven so it runs identically on your local machine, in Google Cloud Shell
(recommended: keeps the ~1.4 GB CSV off your laptop), or inside a Cloud Run Job
wrapped by Airflow later. Reads config from environment (see .env.example).

Idempotent: skips the download if the object already exists in GCS, and replaces
the BigQuery table on load.

Run:
    pip install -r scripts/requirements.txt
    python scripts/ingest.py
"""

from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

from google.cloud import bigquery, storage


def env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        sys.exit(f"Missing required env var: {key} (see .env.example)")
    return val


def download_from_kaggle(dataset: str, file_name: str, dest_dir: Path) -> Path:
    """Download one file from a Kaggle dataset, unzipping if needed."""
    from kaggle.api.kaggle_api_extended import KaggleApi  # imported late: needs creds

    api = KaggleApi()
    api.authenticate()  # reads KAGGLE_USERNAME / KAGGLE_KEY from env

    dest_dir.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {file_name} from kaggle:{dataset} ...")
    api.dataset_download_file(dataset, file_name, path=str(dest_dir), quiet=False)

    csv_path = dest_dir / file_name
    zip_path = dest_dir / f"{file_name}.zip"
    if zip_path.exists():
        print(f"Unzipping {zip_path.name} ...")
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest_dir)
        zip_path.unlink()
    if not csv_path.exists():
        sys.exit(f"Expected {csv_path} after download but it is missing.")
    return csv_path


def upload_to_gcs(local_path: Path, bucket_name: str, blob_name: str) -> str:
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    if blob.exists():
        print(f"gs://{bucket_name}/{blob_name} already exists — skipping upload.")
    else:
        print(f"Uploading to gs://{bucket_name}/{blob_name} ...")
        blob.upload_from_filename(str(local_path))
    return f"gs://{bucket_name}/{blob_name}"


def load_into_bigquery(
    gcs_uri: str, project: str, dataset: str, table: str, location: str, max_bad_records: int
) -> None:
    client = bigquery.Client(project=project)
    dataset_ref = bigquery.Dataset(f"{project}.{dataset}")
    dataset_ref.location = location
    client.create_dataset(dataset_ref, exists_ok=True)

    table_id = f"{project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        autodetect=True,
        skip_leading_rows=1,
        allow_quoted_newlines=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        # The LendingClub file concatenates several quarterly exports, each ending with two
        # non-data summary lines ("Total amount funded in policy code N: ..."). ~33 such
        # footer rows land mid-file; skip them rather than fail the whole 2.26M-row load.
        max_bad_records=max_bad_records,
    )
    print(f"Loading {gcs_uri} -> {table_id} ...")
    job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    job.result()
    dest = client.get_table(table_id)
    skipped = len(job.errors) if job.errors else 0
    print(f"Loaded {dest.num_rows:,} rows into {table_id} (skipped {skipped} bad rows).")


def main() -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass  # env vars can also be exported directly (e.g. in Cloud Shell)

    dataset = env("KAGGLE_DATASET", "wordsforthewise/lending-club")
    file_name = env("KAGGLE_FILE", "accepted_2007_to_2018Q4.csv.gz")
    project = env("GCP_PROJECT")
    bucket = env("GCS_BUCKET")
    bq_dataset = env("BQ_DATASET", "raw")
    bq_table = env("BQ_RAW_TABLE", "lending_club_accepted")
    bq_location = env("BQ_LOCATION", "US")
    max_bad_records = int(env("BQ_MAX_BAD_RECORDS", "100"))

    blob_name = f"lending_club/{file_name}"
    client = storage.Client()
    blob = client.bucket(bucket).blob(blob_name)

    if blob.exists():
        gcs_uri = f"gs://{bucket}/{blob_name}"
        print(f"{gcs_uri} already present — skipping Kaggle download.")
    else:
        data_dir = Path(os.environ.get("DATA_DIR", "data"))
        csv_path = download_from_kaggle(dataset, file_name, data_dir)
        gcs_uri = upload_to_gcs(csv_path, bucket, blob_name)

    load_into_bigquery(gcs_uri, project, bq_dataset, bq_table, bq_location, max_bad_records)
    print("Done.")


if __name__ == "__main__":
    main()
