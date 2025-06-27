import json
import logging

def load_ids(file: str) -> set:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception as e:
        logging.warning(f"Could not load IDs from {file}: {e}")
        return set()

def save_ids(ids: set, file: str):
    try:
        with open(file, 'w', encoding='utf-8') as f:
            json.dump(list(ids), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Could not save IDs to {file}: {e}")