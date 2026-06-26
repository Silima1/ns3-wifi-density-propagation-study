#!/usr/bin/env python3

import csv
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = BASE_DIR / "project" / "config" / "experimental_matrix.csv"


def main():
    propagation_models = [
        "friis",
        "logdistance",
        "friis-nakagami",
    ]

    wifi_standards = [
        "80211g",
        "80211ax",
    ]

    node_values = [5, 10, 20, 30, 50]
    distances = [5, 10, 20, 30, 40, 50]
    seeds = [1, 2, 3]

    rows = []

    for wifi_standard in wifi_standards:
        for n in node_values:
            if n == 5:
                data_rate = "1Mbps"
            elif n == 10:
                data_rate = "2Mbps"
            else:
                data_rate = "2Mbps"

            for model in propagation_models:
                for d in distances:
                    for seed in seeds:
                        filename = (
                            f"run_{wifi_standard}_{model.replace('-', '_')}_{n}nodes_{d}m_seed{seed}.csv"
                        )

                        output_csv = (
                            f"../project/results/raw/{wifi_standard}/{model}/nodes_{n}/{filename}"
                        )

                        rows.append({
                            "wifiStandard": wifi_standard,
                            "nStations": n,
                            "distance": d,
                            "propagationModel": model,
                            "dataRate": data_rate,
                            "seed": seed,
                            "outputCsv": output_csv,
                        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "wifiStandard",
                "nStations",
                "distance",
                "propagationModel",
                "dataRate",
                "seed",
                "outputCsv",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Experimental matrix saved to: {OUTPUT_FILE}")
    print(f"[INFO] Total scenarios: {len(rows)}")


if __name__ == "__main__":
    main()