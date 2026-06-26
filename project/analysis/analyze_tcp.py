#!/usr/bin/env python3

from pathlib import Path
import math
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = BASE_DIR / "project" / "results_tcp" / "raw"
PROCESSED_DIR = BASE_DIR / "project" / "results_tcp" / "processed"


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

    if "trafficType" in df.columns:
        df["trafficType"] = df["trafficType"].astype(str).str.strip().str.lower()

    if "propagationModel" in df.columns:
        df["propagationModel"] = df["propagationModel"].astype(str).str.strip().str.lower()

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


def filter_tcp_data_flows(flow_df: pd.DataFrame) -> pd.DataFrame:
    """
    TCP creates flows in both directions:
    - STA -> AP: useful data traffic
    - AP -> STA: TCP ACK traffic

    For fair comparison with UDP, we keep only useful uplink flows:
    destination == AP address from aggregate row.
    """
    if flow_df.empty:
        return flow_df

    useful_flows = []

    group_cols = [
        "seed",
        "wifiStandard",
        "trafficType",
        "nStations",
        "distance",
        "propagationModel",
        "dataRate",
    ]

    for _, group in flow_df.groupby(group_cols):
        destinations = group["destination"].astype(str)

        # In this topology the AP is the most common destination for STA -> AP flows.
        ap_destination = destinations.value_counts().idxmax()

        data_group = group[group["destination"].astype(str) == ap_destination].copy()
        useful_flows.append(data_group)

    if not useful_flows:
        return pd.DataFrame()

    return pd.concat(useful_flows, ignore_index=True)


def rebuild_tcp_aggregate_from_data_flows(flow_data_df: pd.DataFrame) -> pd.DataFrame:
    if flow_data_df.empty:
        return pd.DataFrame()

    group_cols = [
        "seed",
        "wifiStandard",
        "trafficType",
        "nStations",
        "distance",
        "simulationTime",
        "packetSize",
        "interval",
        "maxPackets",
        "propagationModel",
        "dataRate",
        "payloadSize",
        "offeredLoadMbps",
    ]

    rows = []

    for keys, group in flow_data_df.groupby(group_cols):
        key_dict = dict(zip(group_cols, keys if isinstance(keys, tuple) else (keys,)))

        total_tx = group["txPackets"].sum()
        total_rx = group["rxPackets"].sum()
        total_lost = total_tx - total_rx
        pdr = total_rx / total_tx if total_tx > 0 else 0.0

        throughput = group["throughputMbps"].sum()
        mean_delay = group["meanDelay"].mean()
        fairness = jain_fairness(group["throughputMbps"].tolist())

        n_stations = key_dict["nStations"]
        throughput_per_node = throughput / n_stations if n_stations > 0 else 0.0
        loss_rate = 1.0 - pdr

        offered_load = key_dict["offeredLoadMbps"]
        efficiency = throughput / offered_load if offered_load and offered_load > 0 else 0.0

        row = {
            "level": "aggregate",
            **key_dict,
            "flowId": -1,
            "source": "ALL_STA",
            "destination": "AP",
            "txPackets": total_tx,
            "rxPackets": total_rx,
            "lostPackets": total_lost,
            "pdr": pdr,
            "lossRate": loss_rate,
            "throughputMbps": throughput,
            "throughputPerNodeMbps": throughput_per_node,
            "meanDelay": mean_delay,
            "jainFairness": fairness,
            "efficiency": efficiency,
        }

        rows.append(row)

    return pd.DataFrame(rows)


def save_processed_files(df: pd.DataFrame):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    all_results_file = PROCESSED_DIR / "all_results.csv"
    df.to_csv(all_results_file, index=False)
    print(f"[OK] Saved: {all_results_file}")

    flow_df = df[df["level"] == "flow"].copy()
    aggregate_original_df = df[df["level"] == "aggregate"].copy()

    flow_data_df = filter_tcp_data_flows(flow_df)
    aggregate_df = rebuild_tcp_aggregate_from_data_flows(flow_data_df)

    flow_file = PROCESSED_DIR / "flow_results.csv"
    useful_flow_file = PROCESSED_DIR / "flow_data_results.csv"
    aggregate_original_file = PROCESSED_DIR / "aggregate_original_results.csv"
    aggregate_file = PROCESSED_DIR / "aggregate_results.csv"

    flow_df.to_csv(flow_file, index=False)
    flow_data_df.to_csv(useful_flow_file, index=False)
    aggregate_original_df.to_csv(aggregate_original_file, index=False)
    aggregate_df.to_csv(aggregate_file, index=False)

    print(f"[OK] Saved: {flow_file}")
    print(f"[OK] Saved: {useful_flow_file}")
    print(f"[OK] Saved: {aggregate_original_file}")
    print(f"[OK] Saved corrected TCP aggregate: {aggregate_file}")

    return flow_data_df, aggregate_df


def build_seed_statistics(aggregate_df: pd.DataFrame):
    if aggregate_df.empty:
        return pd.DataFrame()

    grouping_cols = [
        "wifiStandard",
        "trafficType",
        "nStations",
        "distance",
        "propagationModel",
        "dataRate",
    ]

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

    group_cols = ["wifiStandard", "trafficType", "nStations", "propagationModel"]

    metric_cols = [
        "throughputMbps_mean",
        "throughputPerNodeMbps_mean",
        "pdr_mean",
        "meanDelay_mean",
        "jainFairness_mean",
        "efficiency_mean",
    ]

    existing_metrics = [c for c in metric_cols if c in stats_df.columns]

    scalability = (
        stats_df.groupby(group_cols, as_index=False)[existing_metrics]
        .mean()
        .sort_values(["wifiStandard", "trafficType", "propagationModel", "nStations"])
    )

    return scalability


def print_summary(df, flow_data_df, aggregate_df, stats_df, scalability_df):
    print("\n=== TCP DATASET SUMMARY ===")
    print(f"Total rows loaded: {len(df)}")
    print(f"Useful TCP data flow rows: {len(flow_data_df)}")
    print(f"Corrected aggregate rows: {len(aggregate_df)}")

    if "source_file" in df.columns:
        print(f"CSV files loaded: {df['source_file'].nunique()}")

    if not aggregate_df.empty:
        print("\n=== TCP CORRECTED AGGREGATE PREVIEW ===")
        cols = [
            "seed",
            "wifiStandard",
            "trafficType",
            "nStations",
            "distance",
            "propagationModel",
            "throughputMbps",
            "throughputPerNodeMbps",
            "pdr",
            "jainFairness",
            "efficiency",
            "meanDelay",
        ]
        cols = [c for c in cols if c in aggregate_df.columns]
        print(aggregate_df[cols].head(20).to_string(index=False))

    if not stats_df.empty:
        print("\n=== TCP SCENARIO STATISTICS PREVIEW ===")
        cols = [
            "wifiStandard",
            "trafficType",
            "nStations",
            "distance",
            "propagationModel",
            "throughputMbps_mean",
            "throughputMbps_ci95",
            "pdr_mean",
            "pdr_ci95",
            "jainFairness_mean",
            "jainFairness_ci95",
            "efficiency_mean",
            "efficiency_ci95",
        ]
        cols = [c for c in cols if c in stats_df.columns]
        print(stats_df[cols].head(30).to_string(index=False))

    if not scalability_df.empty:
        print("\n=== TCP SCALABILITY SUMMARY ===")
        print(scalability_df.to_string(index=False))


def main():
    print(f"[INFO] Looking for TCP CSV files in: {RAW_DIR}")

    csv_files = collect_csv_files(RAW_DIR)

    if not csv_files:
        print("[WARN] No TCP CSV files found.")
        return

    print(f"[INFO] Found {len(csv_files)} TCP CSV file(s).")

    df = load_and_merge_csvs(csv_files)
    df = clean_dataframe(df)

    if df.empty:
        print("[WARN] No TCP data could be loaded.")
        return

    flow_data_df, aggregate_df = save_processed_files(df)

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

    print_summary(df, flow_data_df, aggregate_df, stats_df, scalability_df)


if __name__ == "__main__":
    main()