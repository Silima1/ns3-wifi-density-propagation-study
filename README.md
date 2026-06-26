# ns3-wifi-performance-analysis

Reproducible ns-3 framework for evaluating IEEE 802.11g and IEEE 802.11ax WLAN performance under UDP and TCP traffic, multiple propagation models, node densities and distances, with statistical analysis and publication-ready visualisations.

## Overview

This project evaluates the combined impact of:

* transport protocol: UDP and TCP;
* Wi-Fi standard: IEEE 802.11g and IEEE 802.11ax;
* propagation model: Friis, Log-Distance and Friis-Nakagami;
* node density: 5, 10, 20, 30 and 50 stations;
* communication distance: 5, 10, 20, 30, 40 and 50 m;
* random seeds: 1, 2 and 3.

The simulation layer is implemented with ns-3, while experiment automation, statistical processing, protocol comparison and visualisation are implemented in Python.

## Experimental design

For each transport protocol:

```text
2 Wi-Fi standards
× 3 propagation models
× 5 node densities
× 6 distances
× 3 seeds
= 540 scheduled runs
```

For both transport protocols:

```text
540 UDP runs + 540 TCP runs = 1080 scheduled runs
```

Current valid raw outputs:

```text
UDP: 536 CSV files
TCP: 537 CSV files
```

The missing outputs correspond to documented internal ns-3/cppyy segmentation failures and are excluded from the aggregate statistical analysis.

## Evaluated metrics

The analysis pipeline computes:

* Packet Delivery Ratio;
* packet loss rate;
* aggregate throughput;
* throughput per node;
* end-to-end delay;
* offered load;
* transmission efficiency;
* Jain's Fairness Index;
* mean;
* standard deviation;
* variance;
* 95% confidence intervals.

## Mathematical definitions

### Packet Delivery Ratio

```text
PDR = N_rx / N_tx
```

### Packet loss rate

```text
LossRate = 1 - PDR
```

### Throughput

```text
Throughput = 8 × RxBytes / Δt
```

### Offered load

```text
L_offered = N_stations × configured data rate
```

### Throughput per node

```text
T_node = T_aggregate / N_stations
```

### Efficiency

```text
η = T_aggregate / L_offered
```

### Jain's Fairness Index

```text
J = (Σx_i)² / (n × Σx_i²)
```

### 95% confidence interval

```text
CI95 = x̄ ± t_(0.975,n−1) × s / √n
```

## Project structure

```text
WN-Project/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── entrypoint.sh
│   └── requirements-analysis.txt
├── ns-3-dev/
│   └── scratch/
│       └── wifi_density_propagation.py
├── project/
│   ├── analysis/
│   │   ├── analyze.py
│   │   ├── analyze_tcp.py
│   │   ├── compare_udp_tcp.py
│   │   ├── final_publication_outputs.py
│   │   └── plots.py
│   ├── config/
│   │   ├── experimental_matrix.csv
│   │   ├── tcp_experimental_matrix.csv
│   │   ├── generate_experimental_matrix.py
│   │   └── generate_tcp_experimental_matrix.py
│   ├── experiments/
│   │   ├── run_experiments.py
│   │   └── run_tcp_experiments.py
│   ├── figures/
│   ├── figures_comparison/
│   ├── figures_final/
│   ├── logs/
│   ├── logs_tcp/
│   ├── results/
│   │   ├── raw/
│   │   └── processed/
│   ├── results_tcp/
│   │   ├── raw/
│   │   └── processed/
│   ├── results_comparison/
│   └── results_final/
├── .dockerignore
└── README.md
```

## Local analysis

From the project root:

```bash
cd ~/Documents/WN-Project
```

Run the UDP analysis:

```bash
~/anaconda3/bin/python3 project/analysis/analyze.py
```

Run the TCP analysis:

```bash
~/anaconda3/bin/python3 project/analysis/analyze_tcp.py
```

Run the UDP versus TCP comparison:

```bash
~/anaconda3/bin/python3 project/analysis/compare_udp_tcp.py
```

Generate the final publication outputs:

```bash
~/anaconda3/bin/python3 project/analysis/final_publication_outputs.py
```

## Container strategy

The container is designed to reuse the existing UDP and TCP simulation outputs.

By default, the container does not:

* compile ns-3;
* execute CMake;
* regenerate the experimental matrices;
* execute the 1080 simulations;
* remove raw UDP results;
* remove raw TCP results.

It only executes:

```text
analyze.py
analyze_tcp.py
compare_udp_tcp.py
final_publication_outputs.py
```

This approach provides a reproducible analysis environment without repeating the computationally expensive simulation campaigns.

## Required container files

```text
docker/Dockerfile
docker/docker-compose.yml
docker/entrypoint.sh
docker/requirements-analysis.txt
.dockerignore
```

Make the entrypoint executable:

```bash
chmod +x docker/entrypoint.sh
```

## Build with Podman

The current development environment uses Podman as the Docker-compatible runtime.

From the project root:

```bash
cd ~/Documents/WN-Project
```

Build the image:

```bash
podman build \
  --no-cache \
  -f docker/Dockerfile \
  -t ns3-wifi-performance-analysis:latest \
  .
```

## Verify the existing results

This command validates the required analysis scripts and counts the existing raw UDP and TCP files without executing simulations:

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  verify
```

Expected information:

```text
UDP raw CSV files: 536
TCP raw CSV files: 537
Existing UDP and TCP results will be reused.
No ns-3 simulations will be executed.
```

## Execute the complete analysis pipeline

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  final
```

The command executes the following stages:

```text
Existing UDP raw results
        ↓
UDP statistical analysis
        ↓
Existing TCP raw results
        ↓
TCP statistical analysis
        ↓
UDP/TCP comparison
        ↓
Publication-ready figures and tables
```

Generated or updated directories:

```text
project/results/processed/
project/results_tcp/processed/
project/results_comparison/
project/figures_comparison/
project/results_final/
project/figures_final/
```

## Available container commands

| Command         | Description                                                 |
| --------------- | ----------------------------------------------------------- |
| `final`         | Execute the complete analysis pipeline without running ns-3 |
| `verify`        | Validate scripts and raw UDP/TCP CSV files                  |
| `status`        | Display raw counts, derived datasets and figure count       |
| `udp-analysis`  | Rebuild only the UDP processed datasets                     |
| `tcp-analysis`  | Rebuild only the TCP processed datasets                     |
| `compare`       | Rebuild the UDP/TCP comparison outputs                      |
| `publication`   | Rebuild final heatmaps, boxplots, radar chart and tables    |
| `clean-final`   | Remove comparison and publication outputs only              |
| `clean-derived` | Remove all derived outputs while preserving raw CSV files   |
| `shell`         | Open an interactive shell inside the container              |

### Show the current project status

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  status
```

### Rebuild only the UDP analysis

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  udp-analysis
```

### Rebuild only the TCP analysis

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  tcp-analysis
```

### Rebuild the UDP/TCP comparison

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  compare
```

### Rebuild the publication outputs

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  publication
```

### Clean comparison and final outputs

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  clean-final
```

This preserves:

```text
project/results/raw/
project/results_tcp/raw/
project/results/processed/
project/results_tcp/processed/
```

### Clean all derived outputs

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  clean-derived
```

This preserves:

```text
project/results/raw/
project/results_tcp/raw/
```

### Open an interactive shell

```bash
podman run --rm -it \
  --userns=keep-id \
  -v "$PWD":/workspace \
  -w /workspace \
  ns3-wifi-performance-analysis:latest \
  shell
```

## Docker Compose

Use a modern Docker Compose installation.

Export the local user and group identifiers:

```bash
export LOCAL_UID="$(id -u)"
export LOCAL_GID="$(id -g)"
```

Build the image:

```bash
docker compose \
  -f docker/docker-compose.yml \
  build
```

Execute the complete analysis:

```bash
docker compose \
  -f docker/docker-compose.yml \
  run --rm wn-analysis final
```

Verify the inputs:

```bash
docker compose \
  -f docker/docker-compose.yml \
  run --rm wn-analysis verify
```

Display the status:

```bash
docker compose \
  -f docker/docker-compose.yml \
  run --rm wn-analysis status
```

In environments where `docker compose` invokes the legacy `docker-compose` 1.29.2 provider, use the Podman commands documented above.

## Important execution rules

1. Do not delete `project/results/raw/` or `project/results_tcp/raw/` unless the simulations must be executed again.
2. The `final` command does not run ns-3.
3. The analysis image does not contain the ns-3 simulator.
4. `clean-final` preserves all raw and processed protocol results.
5. `clean-derived` preserves the raw UDP and TCP CSV files.
6. UDP and TCP campaigns remain independent until the protocol comparison stage.
7. TCP acknowledgement flows are excluded from useful application-throughput aggregation.
8. Use `verify` before running the project on another machine.
9. Statistical conclusions must consider the number of valid seeds available for each scenario.
10. The host project is mounted at `/workspace`, ensuring that all generated files remain available after the container exits.

## Main output files

### UDP processed outputs

```text
project/results/processed/all_results.csv
project/results/processed/flow_results.csv
project/results/processed/aggregate_results.csv
project/results/processed/scenario_statistics.csv
```

### TCP processed outputs

```text
project/results_tcp/processed/all_results.csv
project/results_tcp/processed/flow_results.csv
project/results_tcp/processed/flow_data_results.csv
project/results_tcp/processed/aggregate_original_results.csv
project/results_tcp/processed/aggregate_results.csv
project/results_tcp/processed/scenario_statistics.csv
project/results_tcp/processed/scalability_summary.csv
```

### UDP/TCP comparison outputs

```text
project/results_comparison/udp_tcp_combined_statistics.csv
project/results_comparison/udp_tcp_delta_by_scenario.csv
project/results_comparison/udp_tcp_summary_by_protocol_standard_model.csv
```

### Final publication outputs

```text
project/results_final/final_summary_table.csv
project/results_final/final_summary_table.tex
project/figures_comparison/
project/figures_final/
```

## Scientific interpretation

The final results indicate that:

* IEEE 802.11ax generally achieves higher throughput and lower delay than IEEE 802.11g;
* TCP provides higher effective delivery reliability because of acknowledgements, retransmissions and congestion control;
* UDP exposes the direct effect of wireless channel degradation;
* Friis represents the most favourable propagation condition;
* Friis-Nakagami introduces fading and increased variability;
* Log-Distance produces stronger attenuation and reduced communication coverage;
* increasing the number of stations reduces throughput per node and Jain fairness;
* aggregate throughput may increase initially before reaching saturation;
* low delay must not be interpreted independently when Packet Delivery Ratio is very low.

## Reproducibility workflow

```text
Existing ns-3 raw results
        ↓
Containerised UDP analysis
        ↓
Containerised TCP analysis
        ↓
UDP/TCP statistical comparison
        ↓
Publication-ready figures and tables
```

## Author

**Leonel Olímpio Silima**

University of Porto
Faculty of Engineering
Doctoral Programme in Electrical and Computer Engineering
Wireless Networks — 2025/2026