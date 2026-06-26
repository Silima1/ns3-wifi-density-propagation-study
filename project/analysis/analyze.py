#!/usr/bin/env python3

from pathlib import Path
import math
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "project" / "results" / "raw"
PROCESSED_DIR = BASE_DIR / "project" / "results" / "processed"


def collect_csv_files(raw_dir: Path):
    return sorted(raw_dir.rglob("*.csv"))


def load_and_merge_csvs(csv_files):
    dataframes = []

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            df["source_file"] = str(csv_file.relative_to(BASE_DIR))
            dataframes.append(df)
        except Exception as e:
            print(f"[WARN] Failed to read {csv_file}: {e}")

    if not dataframes:
        return pd.DataFrame()

    return pd.concat(dataframes, ignore_index=True)


def parse_rate_to_mbps(rate_str):
    if pd.isna(rate_str):
        return float("nan")

    rate_str = str(rate_str).strip().lower()

    if rate_str.endswith("mbps"):
        return float(rate_str.replace("mbps", ""))
    if rate_str.endswith("kbps"):
        return float(rate_str.replace("kbps", "")) / 1000.0
    if rate_str.endswith("gbps"):
        return float(rate_str.replace("gbps", "")) * 1000.0

    return float("nan")


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    numeric_columns = [
        "seed",
        "nStations",
        "distance",
        "simulationTime",
        "packetSize",
        "interval",
        "maxPackets",
        "payloadSize",
        "offeredLoadMbps",
        "flowId",
        "txPackets",
        "rxPackets",
        "lostPackets",
        "pdr",
        "throughputMbps",
        "meanDelay",
    ]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "level" in df.columns:
        df["level"] = df["level"].astype(str).str.strip().str.lower()

    if "propagationModel" in df.columns:
        df["propagationModel"] = (
            df["propagationModel"].astype(str).str.strip().str.lower()
        )

    if "wifiStandard" in df.columns:
        df["wifiStandard"] = df["wifiStandard"].astype(str).str.strip().str.lower()

    if "dataRate" in df.columns:
        df["dataRate"] = df["dataRate"].astype(str).str.strip()
        df["dataRateMbps"] = df["dataRate"].apply(parse_rate_to_mbps)

    return df


def t_critical_95(n: int) -> float:
    table = {
        1: float("nan"),
        2: 12.706,
        3: 4.303,
        4: 3.182,
        5: 2.776,
        6: 2.571,
        7: 2.447,
        8: 2.365,
        9: 2.306,
        10: 2.262,
        11: 2.228,
        12: 2.201,
        13: 2.179,
        14: 2.160,
        15: 2.145,
        16: 2.131,
        17: 2.120,
        18: 2.110,
        19: 2.101,
        20: 2.093,
        21: 2.086,
        22: 2.080,
        23: 2.074,
        24: 2.069,
        25: 2.064,
        26: 2.060,
        27: 2.056,
        28: 2.052,
        29: 2.048,
        30: 2.045,
    }
    if n <= 1:
        return float("nan")
    if n in table:
        return table[n]
    return 1.96


def compute_ci95(std_value: float, count_value: int) -> float:
    if pd.isna(std_value) or pd.isna(count_value) or count_value <= 1:
        return float("nan")
    tcrit = t_critical_95(int(count_value))
    if pd.isna(tcrit):
        return float("nan")
    return tcrit * (std_value / math.sqrt(count_value))


def jain_fairness(values):
    values = [float(v) for v in values if pd.notna(v) and float(v) >= 0.0]
    n = len(values)
    if n == 0:
        return 0.0
    numerator = sum(values) ** 2
    denominator = n * sum(v * v for v in values)
    if denominator == 0.0:
        return 0.0
    return numerator / denominator


def enrich_aggregate_with_flow_metrics(flow_df: pd.DataFrame, aggregate_df: pd.DataFrame) -> pd.DataFrame:
    if flow_df.empty or aggregate_df.empty:
        return aggregate_df

    grouping_cols = [
        "seed",
        "wifiStandard",
        "nStations",
        "distance",
        "propagationModel",
        "dataRate",
    ]
    grouping_cols = [c for c in grouping_cols if c in flow_df.columns and c in aggregate_df.columns]

    fairness_df = (
        flow_df.groupby(grouping_cols)["throughputMbps"]
        .apply(lambda x: jain_fairness(list(x)))
        .reset_index(name="jainFairness")
    )

    aggregate_df = aggregate_df.merge(fairness_df, on=grouping_cols, how="left")

    if "nStations" in aggregate_df.columns and "throughputMbps" in aggregate_df.columns:
        aggregate_df["throughputPerNodeMbps"] = aggregate_df["throughputMbps"] / aggregate_df["nStations"]

    if "rxPackets" in aggregate_df.columns and "txPackets" in aggregate_df.columns:
        aggregate_df["lossRate"] = 1.0 - aggregate_df["pdr"]

    if "offeredLoadMbps" not in aggregate_df.columns and "dataRateMbps" in aggregate_df.columns:
        aggregate_df["offeredLoadMbps"] = aggregate_df["dataRateMbps"] * aggregate_df["nStations"]

    if "throughputMbps" in aggregate_df.columns and "offeredLoadMbps" in aggregate_df.columns:
        aggregate_df["efficiency"] = aggregate_df["throughputMbps"] / aggregate_df["offeredLoadMbps"]

    return aggregate_df


def save_processed_files(df: pd.DataFrame):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_results_file = PROCESSED_DIR / "all_results.csv"
    df.to_csv(all_results_file, index=False)
    print(f"[OK] Saved: {all_results_file}")

    flow_df = pd.DataFrame()
    aggregate_df = pd.DataFrame()

    if "level" in df.columns:
        flow_df = df[df["level"] == "flow"].copy()
        aggregate_df = df[df["level"] == "aggregate"].copy()

        aggregate_df = enrich_aggregate_with_flow_metrics(flow_df, aggregate_df)

        flow_file = PROCESSED_DIR / "flow_results.csv"
        aggregate_file = PROCESSED_DIR / "aggregate_results.csv"

        flow_df.to_csv(flow_file, index=False)
        aggregate_df.to_csv(aggregate_file, index=False)

        print(f"[OK] Saved: {flow_file}")
        print(f"[OK] Saved: {aggregate_file}")

    return flow_df, aggregate_df


def build_seed_statistics(aggregate_df: pd.DataFrame):
    if aggregate_df.empty:
        return pd.DataFrame()

    grouping_cols = ["wifiStandard", "nStations", "distance", "propagationModel", "dataRate"]

    metric_cols = [
        "txPackets",
        "rxPackets",
        "lostPackets",
        "pdr",
        "lossRate",
        "throughputMbps",
        "throughputPerNodeMbps",
        "meanDelay",
        "offeredLoadMbps",
        "efficiency",
        "jainFairness",
    ]

    existing_grouping = [c for c in grouping_cols if c in aggregate_df.columns]
    existing_metrics = [c for c in metric_cols if c in aggregate_df.columns]

    grouped = (
        aggregate_df.groupby(existing_grouping)[existing_metrics]
        .agg(["mean", "std", "var", "count"])
        .reset_index()
    )

    grouped.columns = [
        "_".join(col).strip("_") if isinstance(col, tuple) else col
        for col in grouped.columns.to_flat_index()
    ]

    for metric in existing_metrics:
        std_col = f"{metric}_std"
        count_col = f"{metric}_count"
        ci_col = f"{metric}_ci95"

        if std_col in grouped.columns and count_col in grouped.columns:
            grouped[ci_col] = grouped.apply(
                lambda row: compute_ci95(row[std_col], row[count_col]),
                axis=1,
            )

    return grouped


def build_scalability_summary(stats_df: pd.DataFrame):
    if stats_df.empty:
        return pd.DataFrame()

    needed_cols = [
        "wifiStandard",
        "nStations",
        "propagationModel",
        "throughputMbps_mean",
        "throughputPerNodeMbps_mean",
        "pdr_mean",
        "meanDelay_mean",
        "jainFairness_mean",
        "efficiency_mean",
    ]
    existing = [c for c in needed_cols if c in stats_df.columns]

    if "wifiStandard" not in stats_df.columns or "nStations" not in stats_df.columns or "propagationModel" not in stats_df.columns:
        return pd.DataFrame()

    scalability = (
        stats_df.groupby(["wifiStandard", "nStations", "propagationModel"], as_index=False)[
            [c for c in existing if c not in ["wifiStandard", "nStations", "propagationModel"]]
        ]
        .mean()
        .sort_values(["wifiStandard", "propagationModel", "nStations"])
    )

    return scalability


def print_summary(df: pd.DataFrame, aggregate_df: pd.DataFrame, stats_df: pd.DataFrame, scalability_df: pd.DataFrame):
    print("\n=== DATASET SUMMARY ===")
    print(f"Total rows: {len(df)}")

    if "source_file" in df.columns:
        print(f"Number of CSV files loaded: {df['source_file'].nunique()}")

    if "level" in df.columns:
        print("Rows by level:")
        print(df["level"].value_counts(dropna=False))

    if not aggregate_df.empty:
        print("\n=== AGGREGATE SCENARIO SUMMARY ===")
        print(f"Number of aggregate rows: {len(aggregate_df)}")

        columns_to_show = [
            "seed",
            "wifiStandard",
            "nStations",
            "distance",
            "propagationModel",
            "dataRate",
            "offeredLoadMbps",
            "throughputMbps",
            "throughputPerNodeMbps",
            "jainFairness",
            "pdr",
            "meanDelay",
        ]
        existing_cols = [c for c in columns_to_show if c in aggregate_df.columns]
        print(aggregate_df[existing_cols].head(20).to_string(index=False))

    if not stats_df.empty:
        print("\n=== SCENARIO STATISTICS ACROSS SEEDS ===")
        preview_cols = [
            "wifiStandard",
            "nStations",
            "distance",
            "propagationModel",
            "throughputMbps_mean",
            "throughputMbps_ci95",
            "throughputPerNodeMbps_mean",
            "throughputPerNodeMbps_ci95",
            "pdr_mean",
            "pdr_ci95",
            "jainFairness_mean",
            "jainFairness_ci95",
            "meanDelay_mean",
            "meanDelay_ci95",
        ]
        existing_preview = [c for c in preview_cols if c in stats_df.columns]
        print(stats_df[existing_preview].head(30).to_string(index=False))

    if not scalability_df.empty:
        print("\n=== SCALABILITY SUMMARY ===")
        print(scalability_df.to_string(index=False))


def main():
    print(f"[INFO] Looking for CSV files in: {RAW_DIR}")

    csv_files = collect_csv_files(RAW_DIR)

    if not csv_files:
        print("[WARN] No CSV files found in raw results directory.")
        return

    print(f"[INFO] Found {len(csv_files)} CSV file(s).")

    df = load_and_merge_csvs(csv_files)
    df = clean_dataframe(df)

    if df.empty:
        print("[WARN] No data could be loaded.")
        return

    flow_df, aggregate_df = save_processed_files(df)

    stats_df = build_seed_statistics(aggregate_df)
    if not stats_df.empty:
        stats_file = PROCESSED_DIR / "scenario_statistics.csv"
        stats_df.to_csv(stats_file, index=False)
        print(f"[OK] Saved: {stats_file}")

    scalability_df = build_scalability_summary(stats_df)
    if not scalability_df.empty:
        scalability_file = PROCESSED_DIR / "scalability_summary.csv"
        scalability_df.to_csv(scalability_file, index=False)
        print(f"[OK] Saved: {scalability_file}")

    print_summary(df, aggregate_df, stats_df, scalability_df)


if __name__ == "__main__":
    main()