"""Command line: `python -m streaks.cli seed | rebuild | export-csv --as-of ISO --out PATH`."""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

from streaks.ingest import load_inputs, rebuild, seed_inputs
from streaks.parsing import parse_timestamp
from streaks.report import CSV_COLUMNS, compose_csv_rows, compute_all_streaks
from streaks.settings import Settings, load_settings
from streaks.storage import Storage, open_storage_when_ready
from streaks.store import Store, open_store

def run_seed(store: Store, storage: Storage, settings: Settings) -> None:
    store.apply_schema()
    seed_inputs(storage, settings.data_dir, settings.affected_uids_path)
    load_inputs(store, storage)


def run_export_csv(store: Store, as_of: datetime, out_path: Path) -> int:
    rows = compose_csv_rows(compute_all_streaks(store.get_dataset(), as_of))
    with out_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="streaks")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="upload data/ to S3 and load Postgres from S3 (idempotent)")
    commands.add_parser("rebuild", help="empty Postgres and replay everything from S3")
    export = commands.add_parser("export-csv", help="write the streak CSV for one as_of")
    export.add_argument("--as-of", required=True, type=lambda raw: parse_timestamp(raw, "as_of"))
    export.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    settings = load_settings()
    store = open_store(settings.database_url)
    try:
        if args.command == "export-csv":
            print(f"wrote {run_export_csv(store, args.as_of, args.out)} rows to {args.out}")
            return
        storage = open_storage_when_ready(settings.s3_endpoint_url, settings.s3_bucket)
        if args.command == "seed":
            run_seed(store, storage, settings)
        else:
            store.apply_schema()
            rebuild(store, storage)
        print(f"{args.command}: {store.count_events()} events in Postgres")
    finally:
        store.close()


if __name__ == "__main__":
    main()
