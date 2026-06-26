#!/usr/bin/env python3

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = BASE_DIR / "project" / "results" / "processed"
FIGURES_DIR = BASE_DIR / "project" / "figures"

STATS_FILE = PROCESSED_DIR / "scenario_statistics.csv"
SCALABILITY_FILE = PROCESSED_DIR / "scalability_summary.csv"


def load_stats() -> pd.DataFrame:
    if not STATS_FILE.exists():
        print(f"[WARN] Statistics file not found: {STATS_FILE}")
        return pd.DataFrame()
    return pd.read_csv(STATS_FILE)


def load_scalability() -> pd.DataFrame:
    if not SCALABILITY_FILE.exists():
        print(f"[WARN] Scalability file not found: {SCALABILITY_FILE}")
        return pd.DataFrame()
    return pd.read_csv(SCALABILITY_FILE)


def save_metric_vs_distance(df, wifi_standard, mean_col, ci_col, ylabel, title, filename_prefix):
    subset_std = df[df["wifiStandard"] == wifi_standard].copy()
    if subset_std.empty:
        return

    plt.figure(figsize=(8, 5))

    for model in sorted(subset_std["propagationModel"].dropna().unique()):
        subset = (
            subset_std[subset_std["propagationModel"] == model]
            .groupby("distance", as_index=False)[[mean_col, ci_col]]
            .mean()
            .sort_values("distance")
        )

        plt.errorbar(
            subset["distance"],
            subset[mean_col],
            yerr=subset[ci_col],
            marker="o",
            capsize=4,
            label=model,
        )

    plt.xlabel("Distance (m)")
    plt.ylabel(ylabel)
    plt.title(f"{title} [{wifi_standard}]")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    out = FIGURES_DIR / f"{filename_prefix}_{wifi_standard}.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[OK] Saved plot: {out}")


def save_metric_vs_nodes(df, wifi_standard, mean_col, ci_col, ylabel, title, filename_prefix):
    subset_std = df[df["wifiStandard"] == wifi_standard].copy()
    if subset_std.empty:
        return

    for distance in sorted(subset_std["distance"].dropna().unique()):
        subset_d = subset_std[subset_std["distance"] == distance].copy()
        if subset_d.empty:
            continue

        plt.figure(figsize=(8, 5))

        for model in sorted(subset_d["propagationModel"].dropna().unique()):
            subset = (
                subset_d[subset_d["propagationModel"] == model]
                .sort_values("nStations")
            )

            plt.errorbar(
                subset["nStations"],
                subset[mean_col],
                yerr=subset[ci_col],
                marker="o",
                capsize=4,
                label=model,
            )

        plt.xlabel("Number of Stations")
        plt.ylabel(ylabel)
        plt.title(f"{title} [{wifi_standard}] at {int(distance)} m")
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        out = FIGURES_DIR / f"{filename_prefix}_{wifi_standard}_{int(distance)}m.png"
        plt.savefig(out, dpi=300)
        plt.close()
        print(f"[OK] Saved plot: {out}")


def save_highlight_pdr(df, wifi_standard):
    subset_std = df[df["wifiStandard"] == wifi_standard].copy()
    if subset_std.empty:
        return

    plt.figure(figsize=(9, 5.5))

    for model in sorted(subset_std["propagationModel"].dropna().unique()):
        subset = (
            subset_std[subset_std["propagationModel"] == model]
            .groupby("distance", as_index=False)[["pdr_mean", "pdr_ci95"]]
            .mean()
            .sort_values("distance")
        )

        plt.errorbar(
            subset["distance"],
            subset["pdr_mean"],
            yerr=subset["pdr_ci95"],
            marker="o",
            capsize=5,
            linewidth=2,
            label=model,
        )

    plt.xlabel("Distance (m)")
    plt.ylabel("Packet Delivery Ratio (PDR)")
    plt.title(f"PDR vs Distance [{wifi_standard}] (95% CI)")
    plt.ylim(bottom=0.0, top=1.05)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    out = FIGURES_DIR / f"pdr_highlighted_{wifi_standard}.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[OK] Saved plot: {out}")


def save_scalability_plot(df, wifi_standard, mean_col, ylabel, title, filename):
    subset_std = df[df["wifiStandard"] == wifi_standard].copy()
    if subset_std.empty:
        return

    plt.figure(figsize=(8, 5))

    for model in sorted(subset_std["propagationModel"].dropna().unique()):
        subset = (
            subset_std[subset_std["propagationModel"] == model]
            .sort_values("nStations")
        )

        plt.plot(
            subset["nStations"],
            subset[mean_col],
            marker="o",
            label=model,
        )

    plt.xlabel("Number of Stations")
    plt.ylabel(ylabel)
    plt.title(f"{title} [{wifi_standard}]")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    out = FIGURES_DIR / f"{filename}_{wifi_standard}.png"
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"[OK] Saved plot: {out}")


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    stats_df = load_stats()
    scalability_df = load_scalability()

    if stats_df.empty:
        print("[WARN] No scenario statistics available. Skipping plots.")
        return

    print(f"[INFO] Loaded {len(stats_df)} scenario statistic row(s).")

    wifi_standards = sorted(stats_df["wifiStandard"].dropna().unique())

    for wifi_standard in wifi_standards:
        save_metric_vs_distance(
            stats_df,
            wifi_standard,
            "throughputMbps_mean",
            "throughputMbps_ci95",
            "Throughput (Mbps)",
            "Throughput vs Distance",
            "throughput_vs_distance",
        )

        save_metric_vs_distance(
            stats_df,
            wifi_standard,
            "pdr_mean",
            "pdr_ci95",
            "Packet Delivery Ratio",
            "PDR vs Distance",
            "pdr_vs_distance",
        )

        save_metric_vs_distance(
            stats_df,
            wifi_standard,
            "meanDelay_mean",
            "meanDelay_ci95",
            "Mean Delay (s)",
            "Delay vs Distance",
            "delay_vs_distance",
        )

        save_metric_vs_distance(
            stats_df,
            wifi_standard,
            "throughputPerNodeMbps_mean",
            "throughputPerNodeMbps_ci95",
            "Throughput per Node (Mbps)",
            "Throughput per Node vs Distance",
            "throughput_per_node_vs_distance",
        )

        save_metric_vs_distance(
            stats_df,
            wifi_standard,
            "jainFairness_mean",
            "jainFairness_ci95",
            "Jain Fairness Index",
            "Fairness vs Distance",
            "fairness_vs_distance",
        )

        save_metric_vs_nodes(
            stats_df,
            wifi_standard,
            "pdr_mean",
            "pdr_ci95",
            "Packet Delivery Ratio",
            "PDR vs Number of Stations",
            "pdr_vs_nodes",
        )

        save_metric_vs_nodes(
            stats_df,
            wifi_standard,
            "throughputPerNodeMbps_mean",
            "throughputPerNodeMbps_ci95",
            "Throughput per Node (Mbps)",
            "Throughput per Node vs Number of Stations",
            "throughput_per_node_vs_nodes",
        )

        save_metric_vs_nodes(
            stats_df,
            wifi_standard,
            "jainFairness_mean",
            "jainFairness_ci95",
            "Jain Fairness Index",
            "Fairness vs Number of Stations",
            "fairness_vs_nodes",
        )

        save_highlight_pdr(stats_df, wifi_standard)

    if not scalability_df.empty:
        for wifi_standard in sorted(scalability_df["wifiStandard"].dropna().unique()):
            save_scalability_plot(
                scalability_df,
                wifi_standard,
                "throughputMbps_mean",
                "Aggregate Throughput (Mbps)",
                "Scalability: Aggregate Throughput vs Number of Stations",
                "scalability_throughput_vs_nodes",
            )

            save_scalability_plot(
                scalability_df,
                wifi_standard,
                "throughputPerNodeMbps_mean",
                "Throughput per Node (Mbps)",
                "Scalability: Throughput per Node vs Number of Stations",
                "scalability_throughput_per_node_vs_nodes",
            )

            save_scalability_plot(
                scalability_df,
                wifi_standard,
                "pdr_mean",
                "Packet Delivery Ratio",
                "Scalability: PDR vs Number of Stations",
                "scalability_pdr_vs_nodes",
            )

            save_scalability_plot(
                scalability_df,
                wifi_standard,
                "jainFairness_mean",
                "Jain Fairness Index",
                "Scalability: Fairness vs Number of Stations",
                "scalability_fairness_vs_nodes",
            )

            save_scalability_plot(
                scalability_df,
                wifi_standard,
                "efficiency_mean",
                "Efficiency (Throughput / Offered Load)",
                "Scalability: Efficiency vs Number of Stations",
                "scalability_efficiency_vs_nodes",
            )


if __name__ == "__main__":
    main()