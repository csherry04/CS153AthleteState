"""Garmin export ingestion and daily feature preprocessing.

This is intentionally a small MVP pipeline: recursively scan the raw export,
parse supported file types, normalize useful athlete-state records, and write
one daily feature table for downstream modeling.
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


SUPPORTED_SUFFIXES = {".fit", ".csv", ".json", ".tcx", ".xml"}


def scan_files(raw_dir: Path, include_fit: bool = True) -> list[Path]:
    """Return supported files from the Garmin export recursively."""
    suffixes = SUPPORTED_SUFFIXES if include_fit else SUPPORTED_SUFFIXES - {".fit"}
    return sorted(
        path
        for path in raw_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    )


def normalize_date(value: Any) -> str | None:
    """Normalize Garmin date values to YYYY-MM-DD."""
    if value is None or value == "":
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, (int, float)) and not math.isnan(float(value)):
        unit = "ms" if abs(float(value)) > 10_000_000_000 else "s"
        parsed = pd.to_datetime(value, unit=unit, errors="coerce", utc=True)
    else:
        parsed = pd.to_datetime(value, errors="coerce", utc=False)
    if pd.isna(parsed):
        return None
    return parsed.date().isoformat()


def first_present(record: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def to_seconds(value: Any) -> float | None:
    if value is None:
        return None
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return None
    value = float(value)
    return value / 1000.0 if value > 86_400 else value


def to_meters(value: Any) -> float | None:
    if value is None:
        return None
    value = pd.to_numeric(value, errors="coerce")
    if pd.isna(value):
        return None
    value = float(value)
    # Garmin summarizedActivities exports often store distance in centimeters.
    return value / 100.0 if value > 100_000 else value


def flatten_dict(record: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in record.items():
        name = f"{prefix}{key}" if not prefix else f"{prefix}_{key}"
        if isinstance(value, dict):
            flattened.update(flatten_dict(value, name))
        elif isinstance(value, list):
            continue
        else:
            flattened[name] = value
    return flattened


def safe_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def json_family(path: Path) -> str:
    name = path.name
    if "summarizedActivities" in name:
        return "activity_summary"
    if "sleepData" in name:
        return "sleep"
    if name.startswith("UDSFile"):
        return "wellness"
    if name.startswith("HydrationLogFile"):
        return "hydration"
    if name.startswith("TrainingReadinessDTO"):
        return "readiness"
    if name.startswith("MetricsAcuteTrainingLoad"):
        return "load"
    if name.startswith("MetricsMaxMetData"):
        return "fitness"
    if name.startswith("TrainingHistory"):
        return "training_history"
    if name.startswith("EnduranceScore"):
        return "endurance"
    if name.startswith("HillScore"):
        return "hill"
    if name.startswith("RunRacePredictions"):
        return "race_prediction"
    if name.startswith("MetricsHeatAltitudeAcclimation"):
        return "acclimation"
    if "healthStatusData" in name:
        return "health_status"
    return "generic_json"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_json(path: Path) -> dict[str, pd.DataFrame]:
    try:
        data = load_json(path)
    except Exception as exc:
        warnings.warn(f"Skipping unreadable JSON {path}: {exc}")
        return {}

    family = json_family(path)
    if family == "activity_summary":
        records: list[dict[str, Any]] = []
        containers = data if isinstance(data, list) else [data]
        for container in containers:
            if not isinstance(container, dict):
                continue
            records.extend(container.get("summarizedActivitiesExport") or [])
        return {"activities": parse_activity_summary(records, path)}

    records = data if isinstance(data, list) else [data]
    if family == "sleep":
        return {"sleep": parse_sleep(records, path)}
    if family == "hydration":
        return {"hydration": parse_hydration(records, path)}

    daily = parse_daily_json(records, family, path)
    return {family: daily} if not daily.empty else {}


def parse_activity_summary(records: list[dict[str, Any]], path: Path) -> pd.DataFrame:
    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        date = normalize_date(
            first_present(record, ["startTimeLocal", "startTimeGmt", "beginTimestamp", "calendarDate"])
        )
        if not date:
            continue
        rows.append(
            {
                "date": date,
                "source_file": str(path),
                "activity_id": record.get("activityId"),
                "activity_type": first_present(record, ["activityType", "sportType"]),
                "activity_duration_seconds": to_seconds(record.get("duration")),
                "activity_moving_duration_seconds": to_seconds(record.get("movingDuration")),
                "activity_elapsed_duration_seconds": to_seconds(record.get("elapsedDuration")),
                "activity_distance_m": to_meters(record.get("distance")),
                "activity_calories": record.get("calories"),
                "activity_avg_hr": record.get("avgHr"),
                "activity_max_hr": record.get("maxHr"),
                "activity_avg_speed": record.get("avgSpeed"),
                "activity_max_speed": record.get("maxSpeed"),
                "activity_elevation_gain": record.get("elevationGain"),
                "activity_elevation_loss": record.get("elevationLoss"),
                "activity_steps": record.get("steps"),
                "activity_aerobic_training_effect": record.get("aerobicTrainingEffect"),
                "activity_anaerobic_training_effect": record.get("anaerobicTrainingEffect"),
                "activity_vo2_max": record.get("vO2MaxValue"),
            }
        )
    return safe_dataframe(rows)


def parse_sleep(records: list[Any], path: Path) -> pd.DataFrame:
    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        date = normalize_date(record.get("calendarDate"))
        if not date:
            continue
        scores = record.get("sleepScores") or {}
        naps = record.get("napList") or []
        nap_seconds = sum((nap or {}).get("napTimeSec", 0) or 0 for nap in naps if isinstance(nap, dict))
        deep = record.get("deepSleepSeconds")
        light = record.get("lightSleepSeconds")
        rem = record.get("remSleepSeconds")
        awake = record.get("awakeSleepSeconds")
        rows.append(
            {
                "date": date,
                "source_file": str(path),
                "sleep_deep_seconds": deep,
                "sleep_light_seconds": light,
                "sleep_rem_seconds": rem,
                "sleep_awake_seconds": awake,
                "sleep_total_seconds": sum(v or 0 for v in [deep, light, rem]),
                "sleep_total_in_bed_seconds": sum(v or 0 for v in [deep, light, rem, awake]),
                "sleep_nap_seconds": nap_seconds,
                "sleep_avg_respiration": record.get("averageRespiration"),
                "sleep_lowest_respiration": record.get("lowestRespiration"),
                "sleep_highest_respiration": record.get("highestRespiration"),
                "sleep_avg_stress": record.get("avgSleepStress"),
                "sleep_awake_count": record.get("awakeCount"),
                "sleep_restless_moments": record.get("restlessMomentCount"),
                "sleep_score": scores.get("overallScore"),
                "sleep_quality_score": scores.get("qualityScore"),
                "sleep_duration_score": scores.get("durationScore"),
                "sleep_recovery_score": scores.get("recoveryScore"),
            }
        )
    return safe_dataframe(rows)


def parse_hydration(records: list[Any], path: Path) -> pd.DataFrame:
    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        date = normalize_date(record.get("calendarDate"))
        if not date:
            continue
        rows.append(
            {
                "date": date,
                "source_file": str(path),
                "hydration_value_ml": record.get("valueInML"),
                "hydration_estimated_sweat_loss_ml": record.get("estimatedSweatLossInML"),
                "hydration_duration_seconds": to_seconds(record.get("duration")),
                "hydration_activity_id": record.get("activityId"),
            }
        )
    return safe_dataframe(rows)


def parse_daily_json(records: list[Any], family: str, path: Path) -> pd.DataFrame:
    rows = []
    for record in records:
        if not isinstance(record, dict):
            continue
        flat = flatten_dict(record)
        date = normalize_date(first_present(flat, ["calendarDate", "date", "timestamp", "timestampLocal"]))
        if not date:
            continue
        row: dict[str, Any] = {"date": date, "source_file": str(path)}
        for key, value in flat.items():
            if key in {"calendarDate", "userProfilePK", "userProfilePk", "deviceId", "source_file"}:
                continue
            clean_key = f"{family}_{key}"
            row[clean_key] = value
        rows.append(row)
    return safe_dataframe(rows)


def parse_fit(path: Path) -> dict[str, pd.DataFrame]:
    try:
        from fitparse import FitFile
    except ImportError as exc:
        raise RuntimeError("FIT parsing requires fitparse. Install dependencies with `pip install -r requirements.txt`.") from exc

    rows = []
    try:
        fit_file = FitFile(str(path))
        for message in fit_file.get_messages("session"):
            fields = {field.name: field.value for field in message}
            date = normalize_date(first_present(fields, ["start_time", "timestamp"]))
            if not date:
                continue
            rows.append(
                {
                    "date": date,
                    "source_file": str(path),
                    "activity_type": first_present(fields, ["sport", "sub_sport"]),
                    "activity_duration_seconds": first_present(fields, ["total_timer_time", "total_elapsed_time"]),
                    "activity_distance_m": fields.get("total_distance"),
                    "activity_calories": fields.get("total_calories"),
                    "activity_avg_hr": fields.get("avg_heart_rate"),
                    "activity_max_hr": fields.get("max_heart_rate"),
                    "activity_avg_speed": fields.get("avg_speed"),
                    "activity_max_speed": fields.get("max_speed"),
                    "activity_training_load": fields.get("training_load"),
                    "activity_aerobic_training_effect": fields.get("total_training_effect"),
                    "activity_anaerobic_training_effect": fields.get("total_anaerobic_training_effect"),
                }
            )
    except Exception as exc:
        warnings.warn(f"Skipping unreadable FIT {path}: {exc}")
    return {"activities": safe_dataframe(rows)}


def parse_tcx(path: Path) -> dict[str, pd.DataFrame]:
    rows = []
    try:
        tree = ET.parse(path)
    except Exception as exc:
        warnings.warn(f"Skipping unreadable TCX {path}: {exc}")
        return {}

    root = tree.getroot()
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}")[0].strip("{")
    ns = {"tcx": namespace} if namespace else {}
    prefix = "tcx:" if namespace else ""

    for activity in root.findall(f".//{prefix}Activity", ns):
        sport = activity.attrib.get("Sport")
        activity_id = activity.findtext(f"{prefix}Id", namespaces=ns)
        date = normalize_date(activity_id)
        distance = 0.0
        duration = 0.0
        calories = 0.0
        heart_rates = []
        for lap in activity.findall(f"{prefix}Lap", ns):
            distance += float(lap.findtext(f"{prefix}DistanceMeters", default="0", namespaces=ns) or 0)
            duration += float(lap.findtext(f"{prefix}TotalTimeSeconds", default="0", namespaces=ns) or 0)
            calories += float(lap.findtext(f"{prefix}Calories", default="0", namespaces=ns) or 0)
        for bpm in activity.findall(f".//{prefix}HeartRateBpm/{prefix}Value", ns):
            value = pd.to_numeric(bpm.text, errors="coerce")
            if not pd.isna(value):
                heart_rates.append(float(value))
        if date:
            rows.append(
                {
                    "date": date,
                    "source_file": str(path),
                    "activity_type": sport,
                    "activity_duration_seconds": duration or None,
                    "activity_distance_m": distance or None,
                    "activity_calories": calories or None,
                    "activity_avg_hr": sum(heart_rates) / len(heart_rates) if heart_rates else None,
                    "activity_max_hr": max(heart_rates) if heart_rates else None,
                }
            )
    return {"activities": safe_dataframe(rows)}


def parse_xml(path: Path) -> dict[str, pd.DataFrame]:
    if path.suffix.lower() == ".tcx":
        return parse_tcx(path)
    try:
        tree = ET.parse(path)
    except Exception as exc:
        warnings.warn(f"Skipping unreadable XML {path}: {exc}")
        return {}
    values = {element.tag.split("}")[-1]: element.text for element in tree.iter() if element.text}
    date = normalize_date(first_present(values, ["calendarDate", "date", "Date", "timestamp", "Time"]))
    if not date:
        return {}
    row = {"date": date, "source_file": str(path)}
    for key, value in values.items():
        numeric = pd.to_numeric(value, errors="coerce")
        if not pd.isna(numeric):
            row[f"xml_{key}"] = numeric
    return {"generic_xml": pd.DataFrame([row])}


def parse_csv(path: Path) -> dict[str, pd.DataFrame]:
    try:
        frame = pd.read_csv(path)
    except Exception as exc:
        warnings.warn(f"Skipping unreadable CSV {path}: {exc}")
        return {}
    if frame.empty:
        return {}
    date_col = next(
        (col for col in ["calendarDate", "date", "Date", "startTimeLocal", "start_time", "timestamp"] if col in frame.columns),
        None,
    )
    if not date_col:
        return {}
    frame = frame.copy()
    frame["date"] = frame[date_col].map(normalize_date)
    frame = frame.dropna(subset=["date"])
    if frame.empty:
        return {}
    frame["source_file"] = str(path)
    rename = {
        col: f"csv_{col}"
        for col in frame.columns
        if col not in {"date", "source_file"} and pd.api.types.is_numeric_dtype(frame[col])
    }
    return {"generic_csv": frame[["date", "source_file", *rename.keys()]].rename(columns=rename)}


def parse_file(path: Path) -> dict[str, pd.DataFrame]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_json(path)
    if suffix == ".fit":
        return parse_fit(path)
    if suffix == ".tcx":
        return parse_tcx(path)
    if suffix == ".xml":
        return parse_xml(path)
    if suffix == ".csv":
        return parse_csv(path)
    return {}


def concat_frames(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if not frame.empty]
    return pd.concat(non_empty, ignore_index=True, sort=False) if non_empty else pd.DataFrame()


def aggregate_activities(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    frame = frame.copy()
    for col in frame.columns:
        if col.startswith("activity_"):
            converted = pd.to_numeric(frame[col], errors="coerce")
            if converted.notna().sum() == frame[col].notna().sum():
                frame[col] = converted
    numeric_cols = [
        col
        for col in frame.columns
        if col.startswith("activity_") and pd.api.types.is_numeric_dtype(frame[col])
    ]
    aggregations = {col: "mean" for col in numeric_cols}
    for col in [
        "activity_duration_seconds",
        "activity_moving_duration_seconds",
        "activity_elapsed_duration_seconds",
        "activity_distance_m",
        "activity_calories",
        "activity_steps",
        "activity_training_load",
    ]:
        if col in aggregations:
            aggregations[col] = "sum"
    if "activity_max_hr" in aggregations:
        aggregations["activity_max_hr"] = "max"
    daily = frame.groupby("date", as_index=False).agg(aggregations) if aggregations else frame[["date"]].drop_duplicates()
    counts = frame.groupby("date").size().rename("activity_count").reset_index()
    daily = counts.merge(daily, on="date", how="left")
    if "activity_type" in frame.columns:
        types = frame.groupby("date")["activity_type"].nunique(dropna=True).rename("activity_type_count").reset_index()
        daily = daily.merge(types, on="date", how="left")
    return daily


def aggregate_daily(frame: pd.DataFrame, category: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    frame = frame.copy()
    for col in frame.columns:
        if col not in {"date", "source_file"}:
            converted = pd.to_numeric(frame[col], errors="coerce")
            if converted.notna().sum() == frame[col].notna().sum():
                frame[col] = converted
    numeric_cols = [
        col
        for col in frame.columns
        if col not in {"date", "source_file"} and pd.api.types.is_numeric_dtype(frame[col])
    ]
    text_cols = [
        col
        for col in frame.columns
        if col not in {"date", "source_file", *numeric_cols}
    ]
    pieces = []
    if numeric_cols:
        pieces.append(frame.groupby("date", as_index=False)[numeric_cols].mean())
    if text_cols:
        text_daily = frame.groupby("date", as_index=False)[text_cols].last()
        pieces.append(text_daily)
    if not pieces:
        return frame[["date"]].drop_duplicates()
    daily = pieces[0]
    for piece in pieces[1:]:
        daily = daily.merge(piece, on="date", how="outer")
    daily[f"{category}_record_count"] = frame.groupby("date").size().reindex(daily["date"]).to_numpy()
    return daily


def build_daily_features(raw_dir: Path, include_fit: bool = True) -> tuple[pd.DataFrame, dict[str, int]]:
    by_category: dict[str, list[pd.DataFrame]] = defaultdict(list)
    scanned = 0
    parsed = 0

    for path in scan_files(raw_dir, include_fit=include_fit):
        scanned += 1
        parsed_frames = parse_file(path)
        if parsed_frames:
            parsed += 1
        for category, frame in parsed_frames.items():
            if not frame.empty:
                by_category[category].append(frame)

    daily_features: pd.DataFrame | None = None
    category_counts: dict[str, int] = {}
    for category, frames in sorted(by_category.items()):
        frame = concat_frames(frames)
        category_counts[category] = len(frame)
        daily = aggregate_activities(frame) if category == "activities" else aggregate_daily(frame, category)
        if daily.empty:
            continue
        daily_features = daily if daily_features is None else daily_features.merge(daily, on="date", how="outer")

    if daily_features is None:
        daily_features = pd.DataFrame(columns=["date"])
    daily_features = daily_features.sort_values("date").reset_index(drop=True)
    category_counts["files_scanned"] = scanned
    category_counts["files_with_records"] = parsed
    category_counts["fit_files_included"] = int(include_fit)
    category_counts["daily_rows"] = len(daily_features)
    return daily_features, category_counts


def write_daily_features(raw_dir: Path, output_path: Path, include_fit: bool = True) -> dict[str, int]:
    daily_features, summary = build_daily_features(raw_dir, include_fit=include_fit)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    daily_features.to_csv(output_path, index=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build daily athlete-state features from Garmin export data.")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/daily_features.csv"))
    parser.add_argument(
        "--skip-fit",
        action="store_true",
        help="Skip detailed FIT parsing for quick JSON-only preprocessing runs.",
    )
    args = parser.parse_args()

    summary = write_daily_features(args.raw_dir, args.output, include_fit=not args.skip_fit)
    print(f"Wrote {args.output}")
    for key, value in sorted(summary.items()):
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
