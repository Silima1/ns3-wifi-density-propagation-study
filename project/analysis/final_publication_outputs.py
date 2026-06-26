#!/usr/bin/env python3

from pathlib import Path
import math
import pandas as pd
import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[2]

COMPARISON_FILE = BASE_DIR / "project" / "results_comparison" / "udp_tcp_combined_statistics.csv"
SUMMARY_FILE = BASE_DIR / "project" / "results_comparison" / "udp_tcp_summary_by_protocol_standard_model.csv"

OUTPUT_DIR = BASE_DIR / "project" / "results_final"
FIGURES_DIR = BASE_DIR / "project" / "figures_final"


def load_data():
    if not COMPARISON_FILE.exists():
        raise FileNotFoundError(f"Comparison file not found: {COMPARISON_FILE}")

    df = pd.read_csv(COMPARISON_FILE)

    for col in [
        "nStations",
        "distance",
        "throughputMbps_mean",
        "throughputPerNodeMbps_mean",
        "pdr_mean",
        "meanDelay_mean",
        "jainFairness_mean",
        "efficiency_mean",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["trafficType", "wifiStandard", "propagationModel"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    return df


def save_heatmap(df, protocol, standard, model, metric, title, filename):
    subset = df[
        (df["trafficType"] == protocol)
        & (df["wifiStandard"] == standard)
        & (df["propagationModel"] == model)
    ].copy()

    if subset.empty:
        return

    pivot = subset.pivot_table(
        index="nStations",
        columns="distance",
        values=metric,
        aggfunc="mean",
    )

    plt.figure(figsize=(8, 5))
    plt.imshow(pivot, aspect="auto")
    plt.colorbar(label=title)
    plt.xticks(range(len(pivot.columns)), pivot.columns)
    plt.yticks(range(len(pivot.index)), pivot.index)
    plt.xlabel("Distance (m)")
    plt.ylabel("Number of Stations")
    plt.title(f"{title} Heatmap | {protocol.upper()} | {standard} | {model}")
    plt.tight_layout()

    out = FIGURES_DIR / filename
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"[OK] Saved heatmap: {out}")


def generate_heatmaps(df):
    metrics = [
        ("pdr_mean", "PDR", "pdr"),
        ("throughputMbps_mean", "Throughput (Mbps)", "throughput"),
        ("meanDelay_mean", "Mean Delay (s)", "delay"),
        ("jainFairness_mean", "Jain Fairness Index", "fairness"),
    ]

    for protocol in sorted(df["trafficType"].dropna().unique()):
        for standard in sorted(df["wifiStandard"].dropna().unique()):
            for model in sorted(df["propagationModel"].dropna().unique()):
                for metric, title, short in metrics:
                    save_heatmap(
                        df,
                        protocol,
                        standard,
                        model,
                        metric,
                        title,
                        f"heatmap_{short}_{protocol}_{standard}_{model}.png",
                    )


def generate_boxplots(df):
    metrics = [
        ("throughputMbps_mean", "Throughput (Mbps)", "boxplot_throughput_udp_tcp.png"),
        ("pdr_mean", "Packet Delivery Ratio", "boxplot_pdr_udp_tcp.png"),
        ("meanDelay_mean", "Mean Delay (s)", "boxplot_delay_udp_tcp.png"),
        ("jainFairness_mean", "Jain Fairness Index", "boxplot_fairness_udp_tcp.png"),
        ("efficiency_mean", "Efficiency", "boxplot_efficiency_udp_tcp.png"),
    ]

    for metric, ylabel, filename in metrics:
        plt.figure(figsize=(7, 5))

        data = [
            df[df["trafficType"] == "udp"][metric].dropna(),
            df[df["trafficType"] == "tcp"][metric].dropna(),
        ]

        plt.boxplot(data, labels=["UDP", "TCP"])
        plt.ylabel(ylabel)
        plt.title(f"{ylabel}: UDP vs TCP")
        plt.grid(True)
        plt.tight_layout()

        out = FIGURES_DIR / filename
        plt.savefig(out, dpi=300)
        plt.close()

        print(f"[OK] Saved boxplot: {out}")


def normalize_metric(series, higher_is_better=True):
    min_v = series.min()
    max_v = series.max()

    if pd.isna(min_v) or pd.isna(max_v) or max_v == min_v:
        return series * 0 + 1.0

    norm = (series - min_v) / (max_v - min_v)

    if not higher_is_better:
        norm = 1.0 - norm

    return norm


def generate_radar_chart(df):
    grouped = df.groupby("trafficType", as_index=False).agg({
        "throughputMbps_mean": "mean",
        "pdr_mean": "mean",
        "meanDelay_mean": "mean",
        "jainFairness_mean": "mean",
        "efficiency_mean": "mean",
    })

    grouped["throughput_norm"] = normalize_metric(grouped["throughputMbps_mean"], True)
    grouped["pdr_norm"] = normalize_metric(grouped["pdr_mean"], True)
    grouped["delay_norm"] = normalize_metric(grouped["meanDelay_mean"], False)
    grouped["fairness_norm"] = normalize_metric(grouped["jainFairness_mean"], True)
    grouped["efficiency_norm"] = normalize_metric(grouped["efficiency_mean"], True)

    labels = ["Throughput", "PDR", "Low Delay", "Fairness", "Efficiency"]
    metric_cols = [
        "throughput_norm",
        "pdr_norm",
        "delay_norm",
        "fairness_norm",
        "efficiency_norm",
    ]

    angles = [n / float(len(labels)) * 2 * math.pi for n in range(len(labels))]
    angles += angles[:1]

    plt.figure(figsize=(7, 7))
    ax = plt.subplot(111, polar=True)

    for _, row in grouped.iterrows():
        values = [row[col] for col in metric_cols]
        values += values[:1]

        ax.plot(angles, values, linewidth=2, label=row["trafficType"].upper())
        ax.fill(angles, values, alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1)
    plt.title("Normalized Multi-Metric Comparison: UDP vs TCP")
    plt.legend(loc="upper right", bbox_to_anchor=(1.2, 1.1))
    plt.tight_layout()

    out = FIGURES_DIR / "radar_udp_vs_tcp.png"
    plt.savefig(out, dpi=300)
    plt.close()

    print(f"[OK] Saved radar chart: {out}")


def build_final_summary_table(df):
    summary = (
        df.groupby(["trafficType", "wifiStandard", "propagationModel"], as_index=False)
        .agg({
            "throughputMbps_mean": "mean",
            "throughputPerNodeMbps_mean": "mean",
            "pdr_mean": "mean",
            "meanDelay_mean": "mean",
            "jainFairness_mean": "mean",
            "efficiency_mean": "mean",
        })
        .sort_values(["trafficType", "wifiStandard", "propagationModel"])
    )

    summary = summary.rename(columns={
        "trafficType": "Protocol",
        "wifiStandard": "WiFi_Standard",
        "propagationModel": "Propagation_Model",
        "throughputMbps_mean": "Mean_Throughput_Mbps",
        "throughputPerNodeMbps_mean": "Mean_Throughput_Per_Node_Mbps",
        "pdr_mean": "Mean_PDR",
        "meanDelay_mean": "Mean_Delay_s",
        "jainFairness_mean": "Mean_Jain_Fairness",
        "efficiency_mean": "Mean_Efficiency",
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_out = OUTPUT_DIR / "final_summary_table.csv"
    tex_out = OUTPUT_DIR / "final_summary_table.tex"

    summary.to_csv(csv_out, index=False)
    summary.to_latex(tex_out, index=False, float_format="%.4f")

    print(f"[OK] Saved final summary CSV: {csv_out}")
    print(f"[OK] Saved final summary LaTeX: {tex_out}")

    return summary


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("[INFO] Loading UDP/TCP comparison dataset...")
    df = load_data()

    print(f"[INFO] Loaded rows: {len(df)}")

    print("[INFO] Generating heatmaps...")
    generate_heatmaps(df)

    print("[INFO] Generating boxplots...")
    generate_boxplots(df)

    print("[INFO] Generating radar chart...")
    generate_radar_chart(df)

    print("[INFO] Generating final summary table...")
    summary = build_final_summary_table(df)

    print("\n=== FINAL SUMMARY TABLE ===")
    print(summary.to_string(index=False))

    print("\n[OK] Final publication outputs generated successfully.")


if __name__ == "__main__":
    main()