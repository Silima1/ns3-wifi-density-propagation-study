#!/usr/bin/env python3

import csv
import subprocess
from pathlib import Path
from tqdm import tqdm


BASE_DIR = Path(__file__).resolve().parents[2]
NS3_DIR = BASE_DIR / "ns-3-dev"
PROJECT_DIR = BASE_DIR / "project"

MATRIX_FILE = PROJECT_DIR / "config" / "tcp_experimental_matrix.csv"
LOG_DIR = PROJECT_DIR / "logs_tcp"
SIM_SCRIPT = NS3_DIR / "scratch" / "wifi_density_propagation.py"


def ensure_parent_dir(file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)


def load_matrix(matrix_file: Path):
    if not matrix_file.exists():
        raise FileNotFoundError(f"TCP experimental matrix not found: {matrix_file}")

    with open(matrix_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise ValueError(f"TCP experimental matrix is empty: {matrix_file}")

    required_columns = {
        "trafficType",
        "wifiStandard",
        "nStations",
        "distance",
        "propagationModel",
        "dataRate",
        "seed",
        "outputCsv",
    }

    missing = required_columns - set(rows[0].keys())
    if missing:
        raise ValueError(
            f"TCP matrix is missing required columns: {sorted(missing)}"
        )

    return rows


def validate_environment() -> None:
    if not NS3_DIR.exists():
        raise FileNotFoundError(f"ns-3 directory not found: {NS3_DIR}")

    ns3_launcher = NS3_DIR / "ns3"
    if not ns3_launcher.exists():
        raise FileNotFoundError(f"ns3 launcher not found: {ns3_launcher}")

    if not SIM_SCRIPT.exists():
        raise FileNotFoundError(f"Simulation script not found: {SIM_SCRIPT}")


def run_single_experiment(idx: int, total_runs: int, row: dict):
    traffic_type = row["trafficType"].strip()
    wifi_standard = row["wifiStandard"].strip()
    n_stations = row["nStations"].strip()
    distance = row["distance"].strip()
    propagation_model = row["propagationModel"].strip()
    data_rate = row["dataRate"].strip()
    seed = row["seed"].strip()
    output_csv = row["outputCsv"].strip()

    if traffic_type != "tcp":
        raise ValueError(f"This runner only supports TCP, got: {traffic_type}")

    output_csv_path = (NS3_DIR / output_csv).resolve()
    ensure_parent_dir(output_csv_path)

    run_dir = LOG_DIR / f"run_{idx:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = run_dir / "execution.log"

    simulation_cmd = (
        f"scratch/wifi_density_propagation.py -- "
        f"--trafficType {traffic_type} "
        f"--wifiStandard {wifi_standard} "
        f"--nStations {n_stations} "
        f"--distance {distance} "
        f"--propagationModel {propagation_model} "
        f"--dataRate {data_rate} "
        f"--seed {seed} "
        f"--outputCsv {output_csv}"
    )

    cmd = ["./ns3", "run", simulation_cmd]

    with open(log_file, "w", encoding="utf-8") as log:
        result = subprocess.run(
            cmd,
            cwd=NS3_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )

    return {
        "idx": idx,
        "total_runs": total_runs,
        "trafficType": traffic_type,
        "wifiStandard": wifi_standard,
        "nStations": n_stations,
        "distance": distance,
        "propagationModel": propagation_model,
        "dataRate": data_rate,
        "seed": seed,
        "outputCsv": str(output_csv_path),
        "logFile": str(log_file),
        "returncode": result.returncode,
    }


def main() -> None:
    validate_environment()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_matrix(MATRIX_FILE)
    total_runs = len(rows)

    print(f"[INFO] TCP experimental matrix : {MATRIX_FILE}")
    print(f"[INFO] Simulation script       : {SIM_SCRIPT}")
    print(f"[INFO] Total TCP runs          : {total_runs}")

    failed_runs = []

    with tqdm(total=total_runs, desc="Running TCP experiments", unit="run") as pbar:
        for idx, row in enumerate(rows, start=1):
            pbar.set_postfix({
                "run": f"{idx}/{total_runs}",
                "std": row["wifiStandard"].strip(),
                "nodes": row["nStations"].strip(),
                "dist": row["distance"].strip(),
                "model": row["propagationModel"].strip(),
                "seed": row["seed"].strip(),
            })

            result = run_single_experiment(idx, total_runs, row)

            if result["returncode"] != 0:
                failed_runs.append(result)

            pbar.update(1)

    print("\n=== TCP EXECUTION SUMMARY ===")
    print(f"Total runs   : {total_runs}")
    print(f"Successful   : {total_runs - len(failed_runs)}")
    print(f"Failed       : {len(failed_runs)}")

    if failed_runs:
        print("\n=== FAILED TCP RUNS ===")
        for fail in failed_runs:
            print(
                f"Run {fail['idx']:03d} | "
                f"std={fail['wifiStandard']} | "
                f"nodes={fail['nStations']} | "
                f"distance={fail['distance']} | "
                f"model={fail['propagationModel']} | "
                f"dataRate={fail['dataRate']} | "
                f"seed={fail['seed']} | "
                f"log={fail['logFile']}"
            )
    else:
        print("All TCP runs completed successfully.")


if __name__ == "__main__":
    main()