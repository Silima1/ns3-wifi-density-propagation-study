#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/workspace}"

UDP_RAW_DIR="${PROJECT_ROOT}/project/results/raw"
TCP_RAW_DIR="${PROJECT_ROOT}/project/results_tcp/raw"

UDP_ANALYSIS="${PROJECT_ROOT}/project/analysis/analyze.py"
TCP_ANALYSIS="${PROJECT_ROOT}/project/analysis/analyze_tcp.py"
COMPARISON_SCRIPT="${PROJECT_ROOT}/project/analysis/compare_udp_tcp.py"
PUBLICATION_SCRIPT="${PROJECT_ROOT}/project/analysis/final_publication_outputs.py"

UDP_PROCESSED_DIR="${PROJECT_ROOT}/project/results/processed"
TCP_PROCESSED_DIR="${PROJECT_ROOT}/project/results_tcp/processed"

COMPARISON_RESULTS_DIR="${PROJECT_ROOT}/project/results_comparison"
COMPARISON_FIGURES_DIR="${PROJECT_ROOT}/project/figures_comparison"

FINAL_RESULTS_DIR="${PROJECT_ROOT}/project/results_final"
FINAL_FIGURES_DIR="${PROJECT_ROOT}/project/figures_final"


print_header() {
    echo "============================================================"
    echo " ns-3 Wi-Fi Performance Analysis"
    echo " UDP/TCP | IEEE 802.11g/802.11ax | Statistical Evaluation"
    echo "============================================================"
    echo "[INFO] Project root: ${PROJECT_ROOT}"
    echo
}


require_directory() {
    local directory="$1"

    if [[ ! -d "${directory}" ]]; then
        echo "[ERROR] Required directory not found:"
        echo "        ${directory}"
        exit 1
    fi
}


require_file() {
    local file="$1"

    if [[ ! -f "${file}" ]]; then
        echo "[ERROR] Required file not found:"
        echo "        ${file}"
        exit 1
    fi
}


count_csv_files() {
    local directory="$1"

    find "${directory}" \
        -type f \
        -name "*.csv" \
        -print 2>/dev/null |
        wc -l |
        tr -d " "
}


create_output_directories() {
    mkdir -p \
        "${UDP_PROCESSED_DIR}" \
        "${TCP_PROCESSED_DIR}" \
        "${COMPARISON_RESULTS_DIR}" \
        "${COMPARISON_FIGURES_DIR}" \
        "${FINAL_RESULTS_DIR}" \
        "${FINAL_FIGURES_DIR}"
}


verify_scripts() {
    echo "[INFO] Checking analysis scripts..."

    require_file "${UDP_ANALYSIS}"
    require_file "${TCP_ANALYSIS}"
    require_file "${COMPARISON_SCRIPT}"
    require_file "${PUBLICATION_SCRIPT}"

    echo "[OK] All analysis scripts are available."
}


verify_results() {
    echo "[INFO] Checking existing simulation results..."

    require_directory "${UDP_RAW_DIR}"
    require_directory "${TCP_RAW_DIR}"

    local udp_count
    local tcp_count

    udp_count="$(count_csv_files "${UDP_RAW_DIR}")"
    tcp_count="$(count_csv_files "${TCP_RAW_DIR}")"

    echo "[INFO] UDP raw CSV files: ${udp_count}"
    echo "[INFO] TCP raw CSV files: ${tcp_count}"

    if [[ "${udp_count}" -eq 0 ]]; then
        echo "[ERROR] No UDP raw CSV files were found."
        exit 1
    fi

    if [[ "${tcp_count}" -eq 0 ]]; then
        echo "[ERROR] No TCP raw CSV files were found."
        exit 1
    fi

    if [[ "${udp_count}" -lt 540 ]]; then
        echo "[WARN] UDP contains fewer than 540 CSV files."
        echo "[WARN] This is acceptable when failed runs were documented."
    fi

    if [[ "${tcp_count}" -lt 540 ]]; then
        echo "[WARN] TCP contains fewer than 540 CSV files."
        echo "[WARN] This is acceptable when failed runs were documented."
    fi

    echo "[OK] Existing UDP and TCP results will be reused."
    echo "[INFO] No ns-3 simulations will be executed."
}


run_udp_analysis() {
    echo
    echo "------------------------------------------------------------"
    echo "[STEP 1/4] UDP statistical analysis"
    echo "------------------------------------------------------------"

    python "${UDP_ANALYSIS}"
}


run_tcp_analysis() {
    echo
    echo "------------------------------------------------------------"
    echo "[STEP 2/4] TCP statistical analysis"
    echo "------------------------------------------------------------"

    python "${TCP_ANALYSIS}"
}


run_protocol_comparison() {
    echo
    echo "------------------------------------------------------------"
    echo "[STEP 3/4] UDP versus TCP comparison"
    echo "------------------------------------------------------------"

    python "${COMPARISON_SCRIPT}"
}


run_publication_outputs() {
    echo
    echo "------------------------------------------------------------"
    echo "[STEP 4/4] Publication-ready outputs"
    echo "------------------------------------------------------------"

    python "${PUBLICATION_SCRIPT}"
}


verify_final_outputs() {
    echo
    echo "[INFO] Validating generated outputs..."

    local required_outputs=(
        "${UDP_PROCESSED_DIR}/scenario_statistics.csv"
        "${TCP_PROCESSED_DIR}/scenario_statistics.csv"
        "${COMPARISON_RESULTS_DIR}/udp_tcp_combined_statistics.csv"
        "${COMPARISON_RESULTS_DIR}/udp_tcp_delta_by_scenario.csv"
        "${FINAL_RESULTS_DIR}/final_summary_table.csv"
        "${FINAL_RESULTS_DIR}/final_summary_table.tex"
    )

    local output

    for output in "${required_outputs[@]}"; do
        if [[ ! -f "${output}" ]]; then
            echo "[ERROR] Expected output was not generated:"
            echo "        ${output}"
            exit 1
        fi
    done

    echo "[OK] Required final datasets were generated successfully."
}


run_final_pipeline() {
    verify_scripts
    verify_results
    create_output_directories

    run_udp_analysis
    run_tcp_analysis
    run_protocol_comparison
    run_publication_outputs

    verify_final_outputs

    echo
    echo "============================================================"
    echo "[OK] Analysis pipeline completed successfully."
    echo "============================================================"
    echo
    echo "Generated or updated directories:"
    echo "  ${UDP_PROCESSED_DIR}"
    echo "  ${TCP_PROCESSED_DIR}"
    echo "  ${COMPARISON_RESULTS_DIR}"
    echo "  ${COMPARISON_FIGURES_DIR}"
    echo "  ${FINAL_RESULTS_DIR}"
    echo "  ${FINAL_FIGURES_DIR}"
}


clean_comparison_outputs() {
    echo "[INFO] Removing comparison and final publication outputs..."

    rm -rf \
        "${COMPARISON_RESULTS_DIR}" \
        "${COMPARISON_FIGURES_DIR}" \
        "${FINAL_RESULTS_DIR}" \
        "${FINAL_FIGURES_DIR}"

    create_output_directories

    echo "[OK] Comparison and final outputs were cleaned."
    echo "[INFO] UDP and TCP raw simulation results were preserved."
}


clean_derived_outputs() {
    echo "[INFO] Removing all derived outputs..."

    rm -rf \
        "${UDP_PROCESSED_DIR}" \
        "${TCP_PROCESSED_DIR}" \
        "${COMPARISON_RESULTS_DIR}" \
        "${COMPARISON_FIGURES_DIR}" \
        "${FINAL_RESULTS_DIR}" \
        "${FINAL_FIGURES_DIR}"

    create_output_directories

    echo "[OK] Derived outputs were cleaned."
    echo "[INFO] Raw UDP and TCP CSV files were preserved."
}


show_status() {
    verify_scripts
    verify_results
    create_output_directories

    echo
    echo "=== ANALYSIS STATUS ==="
    echo "UDP raw CSVs : $(count_csv_files "${UDP_RAW_DIR}")"
    echo "TCP raw CSVs : $(count_csv_files "${TCP_RAW_DIR}")"

    echo
    echo "Derived files:"

    find \
        "${UDP_PROCESSED_DIR}" \
        "${TCP_PROCESSED_DIR}" \
        "${COMPARISON_RESULTS_DIR}" \
        "${FINAL_RESULTS_DIR}" \
        -maxdepth 1 \
        -type f \
        2>/dev/null |
        sort || true

    echo
    echo "Generated figures:"

    local figure_count
    figure_count="$(
        find \
            "${COMPARISON_FIGURES_DIR}" \
            "${FINAL_FIGURES_DIR}" \
            -type f \
            -name "*.png" \
            2>/dev/null |
            wc -l |
            tr -d " "
    )"

    echo "${figure_count}"
}


show_help() {
    cat <<'EOF'
Usage:

  final
      Execute the complete analysis pipeline using existing UDP and TCP
      simulation results. No ns-3 run is executed.

  verify
      Validate scripts, raw results and CSV counts.

  status
      Show existing raw results, derived datasets and figure count.

  udp-analysis
      Rebuild only the UDP processed datasets.

  tcp-analysis
      Rebuild only the TCP processed datasets.

  compare
      Rebuild only the UDP/TCP comparison outputs.

  publication
      Rebuild only the final heatmaps, boxplots, radar chart and tables.

  clean-final
      Remove comparison and publication outputs only.

  clean-derived
      Remove all processed, comparison and publication outputs.
      Raw UDP and TCP results are preserved.

  shell
      Open an interactive shell inside the analysis container.

  help
      Display this help message.
EOF
}


main() {
    print_header
    cd "${PROJECT_ROOT}"

    local command="${1:-final}"

    case "${command}" in
        final)
            run_final_pipeline
            ;;

        verify)
            verify_scripts
            verify_results
            ;;

        status)
            show_status
            ;;

        udp-analysis)
            verify_scripts
            verify_results
            create_output_directories
            run_udp_analysis
            ;;

        tcp-analysis)
            verify_scripts
            verify_results
            create_output_directories
            run_tcp_analysis
            ;;

        compare)
            verify_scripts
            verify_results
            create_output_directories
            run_protocol_comparison
            ;;

        publication)
            verify_scripts
            create_output_directories
            run_publication_outputs
            ;;

        clean-final)
            clean_comparison_outputs
            ;;

        clean-derived)
            clean_derived_outputs
            ;;

        shell)
            exec /bin/bash
            ;;

        help|--help|-h)
            show_help
            ;;

        *)
            echo "[ERROR] Unknown command: ${command}"
            echo
            show_help
            exit 1
            ;;
    esac
}


main "$@"