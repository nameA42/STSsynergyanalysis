"""Parse model log files to extract per-pair reasoning text.

Log files use a fixed separator of 61 dashes between conversation turns.
Each file has exactly 5625 real (non-injected) pair blocks in a consistent
internal card ordering that may differ from the GT CSV card ordering.

Strategy:
  1. Scan all 5625 blocks; for each, try to match the two card descriptions
     against the card-tags CSV (both base and upgraded descriptions).
  2. Every matched block tells us which CSV card lives at each log row/column
     index, building a log_idx -> csv_card_name lookup.
  3. Once the lookup is complete (or as complete as possible), convert ALL
     5625 blocks positionally: block k -> (log_card[k//75], log_card[k%75]).

This handles CSV vs log description discrepancies: as long as enough pairs are
matched to identify every log-index, all 5625 blocks are covered.
"""

import re
import csv
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent.parent
TAGS_CSV  = BASE_DIR / "data" / "ground_truth" / "StS Synergies - Card Names.csv"
SEPARATOR = "-" * 61

_desc_map: dict | None = None   # {normalised_desc: card_name}
_log_cache: dict       = {}     # {str(log_path): {pair_id: response}}


# ── description normalisation ─────────────────────────────────────────────────

def _norm(text: str) -> str:
    return text.strip().strip('"').strip("'").strip().rstrip(".").lower()


def _load_desc_map() -> dict:
    global _desc_map
    if _desc_map is not None:
        return _desc_map
    result = {}
    if not TAGS_CSV.exists():
        _desc_map = result
        return result
    with open(TAGS_CSV, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or row.get("C") or "").strip()
            if not name:
                continue
            desc = row.get("Description", "").strip()
            if desc:
                result[_norm(desc)] = name
    _desc_map = result
    return result


# ── block parsing ─────────────────────────────────────────────────────────────

_CARD_DESC_RE = re.compile(
    r"Card \d+ \([^)]+\) - Cost [^:\n]+:\s*(.+?)\s*$",
    re.MULTILINE,
)
_QUESTION_END_RE = re.compile(
    r"What is the combo effect of playing .+?\n"
)


def _extract_card_descs(block: str) -> list[str]:
    results = []
    for m in _CARD_DESC_RE.finditer(block):
        desc = m.group(1).strip()
        # Strip surrounding quotes (but preserve internal ones like "Strike")
        if desc.startswith('"') and desc.endswith('"'):
            desc = desc[1:-1]
        results.append(desc)
    return results


def _extract_response(block: str) -> str:
    m = _QUESTION_END_RE.search(block)
    if m:
        return block[m.end():].strip()
    return ""


# ── log card-order derivation ─────────────────────────────────────────────────

def _derive_log_order(blocks: list[str], desc_map: dict) -> list[str | None]:
    """
    Return a list of 75 entries where entry i is the CSV card name that
    occupies log-index i (or None if it could not be resolved).
    Uses matched description pairs to build the mapping positionally.
    """
    log_order: list[str | None] = [None] * 75

    for k, block in enumerate(blocks):
        row_i = k // 75
        col_i = k % 75
        descs = _extract_card_descs(block)

        if len(descs) >= 2:
            name_a = desc_map.get(_norm(descs[0]))
            name_b = desc_map.get(_norm(descs[1]))
            if name_a:
                log_order[row_i] = name_a
            if name_b:
                log_order[col_i] = name_b
        elif len(descs) == 1:
            # Self-pair
            name = desc_map.get(_norm(descs[0]))
            if name:
                log_order[row_i] = name
                log_order[col_i] = name

        # Stop early once every slot is filled
        if all(x is not None for x in log_order):
            break

    return log_order


# ── public API ────────────────────────────────────────────────────────────────

def find_log_for_csv(csv_path: Path) -> Path | None:
    """Return the .log file in the same directory as csv_path, if any."""
    logs = list(Path(csv_path).parent.glob("*.log"))
    return logs[0] if logs else None


def parse_log(log_path: Path) -> dict:
    """Parse a log file and return {pair_id: response_text}."""
    key = str(log_path)
    if key in _log_cache:
        return _log_cache[key]

    if not log_path.exists():
        _log_cache[key] = {}
        return {}

    desc_map = _load_desc_map()
    content  = log_path.read_text(encoding="utf-8", errors="replace")

    # Split into real (non-injected) pair blocks, preserving order
    real_blocks: list[str] = []
    for block in content.split(SEPARATOR):
        block = block.strip()
        if "Let's say" in block and "[injected]" not in block:
            real_blocks.append(block)

    if len(real_blocks) != 75 * 75:
        # Unexpected number of blocks — fall back to description matching only
        result = _parse_by_description(real_blocks, desc_map)
        _log_cache[key] = result
        return result

    # Derive the log's card ordering
    log_order = _derive_log_order(real_blocks, desc_map)

    # Build result positionally
    result: dict = {}
    for k, block in enumerate(real_blocks):
        row_i = k // 75
        col_i = k % 75
        name_a = log_order[row_i]
        name_b = log_order[col_i]
        if name_a is None or name_b is None:
            continue
        response = _extract_response(block)
        if response:
            result[f"{name_a}|{name_b}"] = response

    _log_cache[key] = result
    return result


def _parse_by_description(blocks: list[str], desc_map: dict) -> dict:
    """Fallback: match pairs by description only (no positional info)."""
    result = {}
    for block in blocks:
        response = _extract_response(block)
        if not response:
            continue
        descs = _extract_card_descs(block)
        if len(descs) >= 2:
            name_a = desc_map.get(_norm(descs[0]))
            name_b = desc_map.get(_norm(descs[1]))
            if name_a and name_b:
                result[f"{name_a}|{name_b}"] = response
        elif len(descs) == 1:
            name = desc_map.get(_norm(descs[0]))
            if name:
                result[f"{name}|{name}"] = response
    return result


def get_pair_responses(pair_id: str, model_log_paths: dict) -> dict:
    """Return {model_name: response_text} for the given pair_id."""
    out = {}
    for name, log_path in model_log_paths.items():
        if log_path is None:
            continue
        text = parse_log(log_path).get(pair_id)
        if text:
            out[name] = text
    return out
