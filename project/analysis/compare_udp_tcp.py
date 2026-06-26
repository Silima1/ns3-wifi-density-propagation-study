#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[2]

UDP_STATS = BASE_DIR / "project" / "results" / "processed" / "scenario_statistics.csv"
TCP_STATS = BASE_DIR / "project" / "results_tcp" / "processed" / "scenario_statistics.csv"

OUTPUT_DIR = BASE_DIR / "project" / "results_comparison"
FIGURES_DIR = BASE_DIR / "project" / "figures_comparison"


def load_stats(path: Path, protocol: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{protocol.upper()} statistics file not found: {path}")

    df = pd.read_csv(path)
    df["trafficType"] = protocol.lower()

    for col in [
        "nStations",
        "distance",
        "throughputMbps_mean",
        "throughputMbps_ci95",
        "throughputPerNodeMbps_mean",
        "throughputPerNodeMbps_ci95",
        "pdr_mean",
        "pdr_ci95",
        "meanDelay_mean",
        "meanDelay_ci95",
        "jainFairness_mean",
        "jainFairness_ci95",
        "efficiency_mean",
        "efficiency_ci95",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["wifiStandard", "propagationModel", "dataRate", "trafficType"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df


def save_combined_dataset(udp_df: pd.DataFrame, tcp_df: pd.DataFrame) -> pd.DataFrame:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    common_cols = sorted(set(udp_df.columns).intersection(set(tcp_df.columns)))

    combined = pd.concat(
        [udp_df[common_cols].copy(), tcp_df[common_cols].copy()],
        ignore_index=True,
    )

    output_file = OUTPUT_DIR / "udp_tcp_combined_statistics.csv"
    combined.to_csv(output_file, index=False)

    print(f"[OK] Saved combined statistics: {output_file}")
    return combined


def build_summary(combined: pd.DataFrame) -> pd.DataFrame:
    group_cols = ["trafficType", "wifiStandard", "propagationModel"]

    metric_cols = [
        "throughputMbps_mean",
        "throughputPerNodeMbps_mean",
        "pdr_mean",
        "meanDelay_mean",
        "jainFairness_mean",
        "efficiency_mean",
    ]

    existing_metrics = [c for c in metric_cols if c in combined.columns]

    summary = (
        combined.groupby(group_cols, as_index=False)[existing_metrics]
        .mean()
        .sort_values(group_cols)
    )

    output_file = OUTPUT_DIR / "udp_tcp_summary_by_protocol_standard_model.csv"
    summary.to_csv(output_file, index=False)

    print(f"[OK] Saved comparison summary: {output_file}")
    return summary


def build_protocol_delta(combined: pd.DataFrame) -> pd.DataFrame:
    key_cols = [
        "wifiStandard",
        "nStations",
        "distance",
        "propagationModel",
        "dataRate",
    ]

    metric_cols = [
        "throughputMbps_mean",
        "throughputPerNodeMbps_mean",
        "pdr_mean",
        "meanDelay_mean",
        "jainFairness_mean",
        "efficiency_mean",
    ]

    available_metrics = [m for m in metric_cols if m in combined.columns]

    udp = combined[combined["trafficType"] == "udp"].copy()
    tcp = combined[combined["trafficType"] == "tcp"].copy()

    udp = udp[key_cols + available_metrics].rename(
        columns={m: f"udp_{m}" for m in available_metrics}
    )
    tcp = tcp[key_cols + available_metrics].rename(
        columns={m: f"tcp_{m}" for m in available_metrics}
    )

    merged = pd.merge(udp, tcp, on=key_cols, how="inner")

    for metric in available_metrics:
        udp_col = f"udp_{metric}"
        tcp_col = f"tcp_{metric}"
        delta_col = f"delta_tcp_minus_udp_{metric}"
        ratio_col = f"ratio_tcp_over_udp_{metric}"

        merged[delta_col] = merged[tcp_col] - merged[udp_col]
        merged[ratio_col] = merged[tcp_col] / merged[udp_col].replace(0, pd.NA)

    output_file = OUTPUT_DIR / "udp_tcp_delta_by_scenario.csv"
    merged.to_csv(output_file, index=False)

    print(f"[OK] Saved UDP/TCP delta table: {output_file}")
    return merged


def plot_protocol_comparison(
    combined: pd.DataFrame,
    metric_col: str,
    ci_col: str,
    ylabel: str,
    filename_prefix: str,
):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    for wifi_standard in sorted(combined["wifiStandard"].dropna().unique()):
        for model in sorted(combined["propagationModel"].dropna().unique()):
            subset = combined[
                (combined["wifiStandard"] == wifi_standard)
                & (combined["propagationModel"] == model)
            ].copy()

            if subset.empty:
                continue

            plt.figure(figsize=(8, 5))

            for protocol in ["udp", "tcp"]:
                proto_df = subset[subset["trafficType"] == protocol].copy()
                if proto_df.empty:
                    continue

                grouped = (
                    proto_df.groupby("distance", as_index=False)[[metric_col, ci_col]]
                    .mean()
                    .sort_values("distance")
                )

                plt.errorbar(
                    grouped["distance"],
                    grouped[metric_col],
                    yerr=grouped[ci_col] if ci_col in grouped.columns else None,
                    marker="o",
                    capsize=4,
                    label=protocol.upper(),
                )

            plt.xlabel("Distance (m)")
            plt.ylabel(ylabel)
            plt.title(f"{ylabel} vs Distance | {wifi_standard} | {model}")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()

            out = FIGURES_DIR / f"{filename_prefix}_{wifi_standard}_{model}.png"
            plt.savefig(out, dpi=300)
            plt.close()

            print(f"[OK] Saved plot: {out}")


def plot_scalability_comparison(
    combined: pd.DataFrame,
    metric_col: str,
    ylabel: str,
    filename_prefix: str,
):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    for wifi_standard in sorted(combined["wifiStandard"].dropna().unique()):
        for model in sorted(combined["propagationModel"].dropna().unique()):
            subset = combined[
                (combined["wifiStandard"] == wifi_standard)
                & (combined["propagationModel"] == model)
            ].copy()

            if subset.empty:
                continue

            plt.figure(figsize=(8, 5))

            for protocol in ["udp", "tcp"]:
                proto_df = subset[subset["trafficType"] == protocol].copy()
                if proto_df.empty:
                    continue

                grouped = (
                    proto_df.groupby("nStations", as_index=False)[metric_col]
                    .mean()
                    .sort_values("nStations")
                )

                plt.plot(
                    grouped["nStations"],
                    grouped[metric_col],
                    marker="o",
                    label=protocol.upper(),
                )

            plt.xlabel("Number of Stations")
            plt.ylabel(ylabel)
            plt.title(f"{ylabel} vs Number of Stations | {wifi_standard} | {model}")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()

            out = FIGURES_DIR / f"{filename_prefix}_{wifi_standard}_{model}.png"
            plt.savefig(out, dpi=300)
            plt.close()

            print(f"[OK] Saved scalability plot: {out}")


def print_summary(summary: pd.DataFrame, delta: pd.DataFrame):
    print("\n=== UDP vs TCP SUMMARY ===")
    print(summary.to_string(index=False))

    print("\n=== UDP vs TCP DELTA PREVIEW ===")
    preview_cols = [
        "wifiStandard",
        "nStations",
        "distance",
        "propagationModel",
        "udp_throughputMbps_mean",
        "tcp_throughputMbps_mean",
        "delta_tcp_minus_udp_throughputMbps_mean",
        "udp_pdr_mean",
        "tcp_pdr_mean",
        "delta_tcp_minus_udp_pdr_mean",
        "udp_meanDelay_mean",
        "tcp_meanDelay_mean",
        "delta_tcp_minus_udp_meanDelay_mean",
    ]
    preview_cols = [c for c in preview_cols if c in delta.columns]
    print(delta[preview_cols].head(30).to_string(index=False))


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading UDP statistics...")
    udp_df = load_stats(UDP_STATS, "udp")

    print("[INFO] Loading TCP statistics...")
    tcp_df = load_stats(TCP_STATS, "tcp")

    print(f"[INFO] UDP rows: {len(udp_df)}")
    print(f"[INFO] TCP rows: {len(tcp_df)}")

    combined = save_combined_dataset(udp_df, tcp_df)
    summary = build_summary(combined)
    delta = build_protocol_delta(combined)

    plot_protocol_comparison(
        combined,
        "throughputMbps_mean",
        "throughputMbps_ci95",
        "Throughput (Mbps)",
        "udp_tcp_throughput_vs_distance",
    )

    plot_protocol_comparison(
        combined,
        "throughputPerNodeMbps_mean",
        "throughputPerNodeMbps_ci95",
        "Throughput per Node (Mbps)",
        "udp_tcp_throughput_per_node_vs_distance",
    )

    plot_protocol_comparison(
        combined,
        "pdr_mean",
        "pdr_ci95",
        "Packet Delivery Ratio (PDR)",
        "udp_tcp_pdr_vs_distance",
    )

    plot_protocol_comparison(
        combined,
        "meanDelay_mean",
        "meanDelay_ci95",
        "Mean Delay (s)",
        "udp_tcp_delay_vs_distance",
    )

    plot_protocol_comparison(
        combined,
        "jainFairness_mean",
        "jainFairness_ci95",
        "Jain Fairness Index",
        "udp_tcp_fairness_vs_distance",
    )

    plot_scalability_comparison(
        combined,
        "throughputMbps_mean",
        "Aggregate Throughput (Mbps)",
        "udp_tcp_scalability_throughput_vs_nodes",
    )

    plot_scalability_comparison(
        combined,
        "throughputPerNodeMbps_mean",
        "Throughput per Node (Mbps)",
        "udp_tcp_scalability_throughput_per_node_vs_nodes",
    )

    plot_scalability_comparison(
        combined,
        "pdr_mean",
        "Packet Delivery Ratio (PDR)",
        "udp_tcp_scalability_pdr_vs_nodes",
    )

    plot_scalability_comparison(
        combined,
        "jainFairness_mean",
        "Jain Fairness Index",
        "udp_tcp_scalability_fairness_vs_nodes",
    )

    print_summary(summary, delta)

    print("\n[OK] UDP vs TCP comparison completed.")


if __name__ == "__main__":
    main()