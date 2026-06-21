from pathlib import Path
import json
import tempfile
import shutil
import pandas as pd


DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _safe_name(name):
    safe_name = str(name or "default").strip()
    safe_name = safe_name.replace("/", "_").replace("\\", "_")
    safe_name = safe_name.replace("..", "_").replace(":", "_")
    safe_name = safe_name.replace("*", "_").replace("?", "_")
    safe_name = safe_name.replace('"', "_").replace("<", "_")
    safe_name = safe_name.replace(">", "_").replace("|", "_")
    return safe_name or "default"


def _csv_path(name):
    return DATA_DIR / f"{_safe_name(name)}.csv"


def _json_path(name):
    return DATA_DIR / f"{_safe_name(name)}.json"


def append_csv(name, row):
    path = _csv_path(name)

    try:
        if row is None:
            row = {}

        if not isinstance(row, dict):
            row = {"value": row}

        df = pd.DataFrame([row])

        df.to_csv(
            path,
            mode="a",
            index=False,
            header=not path.exists(),
            encoding="utf-8-sig",
        )

        return True

    except Exception:
        return False


def read_csv(name):
    path = _csv_path(name)

    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        try:
            return pd.read_csv(path)
        except Exception:
            return pd.DataFrame()


def save_json(name, obj):
    path = _json_path(name)

    try:
        text = json.dumps(obj, indent=2, default=str, ensure_ascii=False)

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8",
            suffix=".json",
            dir=str(DATA_DIR),
        ) as tmp:
            tmp.write(text)
            tmp_path = Path(tmp.name)

        shutil.move(str(tmp_path), str(path))
        return True

    except Exception:
        return False


def load_json(name, default=None):
    path = _json_path(name)

    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def append_event(name, row):
    return append_csv(name, row)


def overwrite_csv(name, rows):
    path = _csv_path(name)

    try:
        if rows is None:
            rows = []

        df = pd.DataFrame(rows)

        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf-8-sig",
            suffix=".csv",
            dir=str(DATA_DIR),
        ) as tmp:
            tmp_path = Path(tmp.name)

        df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
        shutil.move(str(tmp_path), str(path))

        return True

    except Exception:
        return False


def delete_data_file(name, file_type="csv"):
    try:
        file_type = str(file_type or "csv").lower().strip()

        if file_type == "json":
            path = _json_path(name)
        else:
            path = _csv_path(name)

        if path.exists():
            path.unlink()

        return True

    except Exception:
        return False


def list_data_files():
    try:
        files = []

        for p in DATA_DIR.glob("*"):
            if not p.is_file():
                continue

            stat = p.stat()

            files.append(
                {
                    "name": p.name,
                    "type": p.suffix.replace(".", "").upper(),
                    "size_bytes": stat.st_size,
                    "modified": pd.Timestamp.fromtimestamp(stat.st_mtime).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
            )

        return pd.DataFrame(files)

    except Exception:
        return pd.DataFrame()


def file_exists(name, file_type="csv"):
    file_type = str(file_type or "csv").lower().strip()
    path = _json_path(name) if file_type == "json" else _csv_path(name)
    return path.exists()


def clear_all_data():
    try:
        for p in DATA_DIR.glob("*"):
            if p.is_file() and p.suffix.lower() in [".csv", ".json"]:
                p.unlink()
        return True
    except Exception:
        return False