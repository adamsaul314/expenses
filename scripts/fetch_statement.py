#!/usr/bin/env python3
"""Download the newest CSV statement from a Google Drive folder.

Used by CI, where the desktop Drive mount is unavailable. Reads credentials
from either ``--service-account-file`` or the ``GDRIVE_SERVICE_ACCOUNT_JSON``
environment variable. The folder is located by name (default ``expenses``) or
by an explicit ``--folder-id``.

Setup (one-off):
  1. Create a Google Cloud project and enable the Google Drive API.
  2. Create a service account and a JSON key.
  3. Share the Drive folder with the service-account email as Viewer.
  4. Store the key JSON as the GitHub secret ``GDRIVE_SERVICE_ACCOUNT_JSON``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_FOLDER_NAME = "expenses"


def load_credentials_info(args: argparse.Namespace) -> dict:
    if args.service_account_file:
        return json.loads(Path(args.service_account_file).read_text(encoding="utf-8"))
    raw = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if raw:
        return json.loads(raw)
    raise SystemExit(
        "error: provide --service-account-file or set GDRIVE_SERVICE_ACCOUNT_JSON"
    )


def build_service(info: dict):
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def resolve_folder_id(service, name: str) -> str:
    """Return the ID of the single Drive folder called *name*."""
    query = (
        "mimeType = 'application/vnd.google-apps.folder' "
        f"and name = '{name}' and trashed = false"
    )
    response = (
        service.files()
        .list(q=query, fields="files(id,name)", pageSize=10)
        .execute()
    )
    folders = response.get("files", [])
    if not folders:
        raise SystemExit(
            f"error: no Drive folder named {name!r} found. Is it shared with the "
            "service account?"
        )
    if len(folders) > 1:
        ids = ", ".join(folder["id"] for folder in folders)
        raise SystemExit(
            f"error: multiple folders named {name!r} found ({ids}); pass --folder-id"
        )
    return folders[0]["id"]


def list_csvs(service, folder_id: str) -> list[dict]:
    query = (
        f"'{folder_id}' in parents and trashed = false "
        "and name contains '.csv'"
    )
    response = (
        service.files()
        .list(
            q=query,
            orderBy="modifiedTime desc",
            pageSize=100,
            fields="files(id,name,modifiedTime)",
        )
        .execute()
    )
    return [
        item
        for item in response.get("files", [])
        if item["name"].lower().endswith(".csv")
    ]


def download(service, file: dict, dest_dir: Path) -> Path:
    from googleapiclient.http import MediaIoBaseDownload

    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / file["name"]
    request = service.files().get_media(fileId=file["id"])
    with target.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--folder-id",
        default=os.environ.get("GDRIVE_FOLDER_ID"),
        help="Google Drive folder ID (default: $GDRIVE_FOLDER_ID, else resolved by name).",
    )
    parser.add_argument(
        "--folder-name",
        default=os.environ.get("GDRIVE_FOLDER_NAME", DEFAULT_FOLDER_NAME),
        help="Drive folder name to look up (default: expenses).",
    )
    parser.add_argument(
        "--service-account-file",
        help="Path to a service-account JSON key (default: $GDRIVE_SERVICE_ACCOUNT_JSON).",
    )
    parser.add_argument(
        "--dest",
        default="statements",
        help="Destination directory (default: statements).",
    )
    args = parser.parse_args(argv)

    service = build_service(load_credentials_info(args))
    folder_id = args.folder_id or resolve_folder_id(service, args.folder_name)

    files = list_csvs(service, folder_id)
    if not files:
        raise SystemExit(f"error: no CSV files found in Drive folder {folder_id}")

    newest = files[0]
    target = download(service, newest, Path(args.dest))
    print(f"Fetched {newest['name']} -> {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
