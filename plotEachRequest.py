from datetime import datetime
import os
import re
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------
# PATH CONFIGURATION
# ---------------------------------------------------------
#CEDA_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-CEDA-var-clw-HTTPS-ServerTesting-20260810-115420.output"
#DKRZ_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-DKRZ-var-clw-HTTPS-ServerTesting-20260810-115734.output"

#OUTPUT_DIR = "output-clw-testoutput/"

CEDA_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912/ESGF-CEDA-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912-20260811-170710.output"
DKRZ_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912/ESGF-DKRZ-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912-20260811-171904.output"
serverLocation="DKRZ"

#DKRZ_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912/ESGF-JASMIN-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912-20260811-172609.output"
#serverLocation="JASMIN"

OUTPUT_DIR = "output-cl_Amon_UKESM1-0-LL_esm-hist_r1i1p1f2_gn_185001-189912/CEDAv"+serverLocation



#CEDA_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-CEDA-var-clw-HTTPS-ServerTesting-20260810-115420.output"
#DKRZ_FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-DKRZ-var-clw-HTTPS-ServerTesting-20260810-115734.output"

#OUTPUT_DIR = "output-clw-UpdatedPlotting/"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# PARSING UTILITY FUNCTIONS
# ---------------------------------------------------------
def parse_chunk_size(range_str):
    """Calculates chunk size from range string 'start,end' (inclusive count)."""
    if not range_str or range_str == "N/A":
        return None
    try:
        parts = range_str.split(",")
        start_idx = int(parts[0])
        end_idx = int(parts[1])
        return end_idx - start_idx + 1
    except (ValueError, IndexError):
        return None


def parse_log_file(file_path, server_label):
    """Parses a server log file and returns a structured DataFrame."""
    if not os.path.exists(file_path):
        print(
            f"WARNING: File {file_path} not found. Skipping {server_label}."
        )
        return pd.DataFrame()

    with open(file_path, "r") as f:
        log_data = f.read()

    req_pattern = r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\.\d{6})\s+([a-f0-9]+)\s+Range=bytes=(\d+)-(\d+)(?:\s+(Recieved))?"
    thread_boundary_pattern = r"Thread for range\[(\d+,\d+)\]\s+(completed|FAILED)(?:\s+\|\s+maxWorkers:\s*(\d+))?.*?(?: Error:\s*(.*))?$"

    current_run_id = 0
    run_metadata = {}
    sent_events = {}
    records = []

    for line in log_data.strip().split("\n"):
        thread_match = re.search(thread_boundary_pattern, line)
        if thread_match:
            range_str, status, workers_str, error_msg = thread_match.groups()
            workers = int(workers_str) if workers_str else None

            run_metadata[current_run_id] = {
                "range": range_str,
                "status": status,
                "max_workers": workers,
                "error": error_msg.strip() if error_msg else None,
            }
            current_run_id += 1
            continue

        match = re.search(req_pattern, line)
        if match:
            timestamp_str, req_id, start_byte, end_byte, is_received = (
                match.groups()
            )
            dt = datetime.strptime(timestamp_str, "%d/%b/%Y:%H:%M:%S.%f")
            start_b, end_b = int(start_byte), int(end_byte)

            if not is_received:
                sent_events[req_id] = {
                    "start_time": dt,
                    "size_kb": (end_b - start_b + 1) / 1024,
                    "run_id": current_run_id,
                }
            else:
                if req_id in sent_events:
                    sent_info = sent_events[req_id]
                    latency = (dt - sent_info["start_time"]).total_seconds()

                    records.append({
                        "req_id": req_id,
                        "server": server_label,
                        "run_id": sent_info["run_id"],
                        "start_clock": sent_info["start_time"],
                        "end_clock": dt,
                        "latency": latency,
                        "size_kb": sent_info["size_kb"],
                    })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["range"] = df["run_id"].apply(
        lambda r: run_metadata.get(r, {}).get("range", "N/A")
    )
    df["max_workers"] = df["run_id"].apply(
        lambda r: run_metadata.get(r, {}).get("max_workers", None)
    )
    df["thread_status"] = df["run_id"].apply(
        lambda r: run_metadata.get(r, {}).get("status", "UNKNOWN")
    )
    df["chunk_size"] = df["range"].apply(parse_chunk_size)

    # Compute relative completion time (normalized per run)
    run_start_times = df.groupby("run_id")["start_clock"].transform("min")
    df["x_val_rel"] = (df["end_clock"] - run_start_times).dt.total_seconds()

    return df


# ---------------------------------------------------------
# LOAD & MERGE DATASETS
# ---------------------------------------------------------
print("Parsing CEDA and "+serverLocation+" log files...")
df_ceda = parse_log_file(CEDA_FILE_PATH, "CEDA")
df_dkrz = parse_log_file(DKRZ_FILE_PATH, serverLocation)

df_all = pd.concat([df_ceda, df_dkrz], ignore_index=True)

if df_all.empty:
    raise ValueError(
        "No data parsed from log files. Please check FILE_PATH variables."
    )

print(
    f"Successfully parsed {len(df_all)} records ({len(df_ceda)} CEDA, {len(df_dkrz)} {serverLocation}).\n"
)

# =========================================================
# ITEM 1: Latency vs Max Threads (CEDA vs DKRZ with Error Bars & Ratio Subplot)
# =========================================================
pdf_path_1 = os.path.join(
    OUTPUT_DIR, "test-1_latency_vs_max_workers_CEDA_vs_"+serverLocation+".pdf"
)
with PdfPages(pdf_path_1) as pdf:
    unique_chunks = sorted(
        [c for c in df_all["chunk_size"].dropna().unique()]
    )
    chunk_colors = plt.cm.get_cmap("tab10", max(len(unique_chunks), 1))

    # ---------------------------------------------------------
    # PAGE 1: CEDA - All Chunk Sizes Overlayed (with Error Bars)
    # ---------------------------------------------------------
    df_ceda_all = df_all[df_all["server"] == "CEDA"]
    if not df_ceda_all.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        for idx, chunk in enumerate(unique_chunks):
            df_c = df_ceda_all[df_ceda_all["chunk_size"] == chunk]
            if df_c.empty:
                continue

            avg_lat = (
                df_c.groupby("max_workers")["latency"]
                .agg(mean="mean", std="std", count="count")
                .reset_index()
                .sort_values("max_workers")
            )
            # Standard Error of the Mean (use avg_lat["std"] if you prefer Standard Deviation)
            avg_lat["yerr"] = avg_lat["std"] / np.sqrt(avg_lat["count"])

            ax.errorbar(
                avg_lat["max_workers"],
                avg_lat["mean"],
                yerr=avg_lat["yerr"],
                label=f"Slice Range {chunk}",
                color=chunk_colors(idx),
                marker="o",
                linewidth=2,
                markersize=7,
                capsize=4,
                capthick=1.2,
            )

        ax.set_title(
            "CEDA: Mean Latency vs Max Workers (All Range Slices ± SEM)",
            fontsize=13,
            pad=15,
        )
        ax.set_xlabel("Max Workers (Threads)", fontsize=11)
        ax.set_ylabel("Average Latency (seconds)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(title="Slice Range", fontsize=10, loc="best")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    # ---------------------------------------------------------
    # PAGE 2: DKRZ - All Chunk Sizes Overlayed (with Error Bars)
    # ---------------------------------------------------------
    df_dkrz_all = df_all[df_all["server"] == serverLocation]
    if not df_dkrz_all.empty:
        fig, ax = plt.subplots(figsize=(10, 6))
        for idx, chunk in enumerate(unique_chunks):
            df_c = df_dkrz_all[df_dkrz_all["chunk_size"] == chunk]
            if df_c.empty:
                continue

            avg_lat = (
                df_c.groupby("max_workers")["latency"]
                .agg(mean="mean", std="std", count="count")
                .reset_index()
                .sort_values("max_workers")
            )
            avg_lat["yerr"] = avg_lat["std"] / np.sqrt(avg_lat["count"])

            ax.errorbar(
                avg_lat["max_workers"],
                avg_lat["mean"],
                yerr=avg_lat["yerr"],
                label=f"Slice Range {chunk}",
                color=chunk_colors(idx),
                marker="s",
                linewidth=2,
                markersize=7,
                capsize=4,
                capthick=1.2,
            )

        ax.set_title(
            serverLocation+": Mean Latency vs Max Workers (All Slice Ranges ± SEM)",
            fontsize=13,
            pad=15,
        )
        ax.set_xlabel("Max Workers (Threads)", fontsize=11)
        ax.set_ylabel("Average Latency (seconds)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(title="Slice Range", fontsize=10, loc="best")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    # ---------------------------------------------------------
    # SUBSEQUENT PAGES: CEDA vs DKRZ Overlay (with Error Bars) + Ratio Subplot
    # ---------------------------------------------------------
    for chunk in unique_chunks:
        fig, (ax_top, ax_bot) = plt.subplots(
            2,
            1,
            figsize=(10, 8),
            sharex=True,
            gridspec_kw={"height_ratios": [2.5, 1]},
        )
        df_chunk = df_all[df_all["chunk_size"] == chunk]

        ceda_series = None
        dkrz_series = None

        # 1. Top Subplot: Latency with Error Bars
        for server, color, marker in [
            ("CEDA", "blue", "o"),
            (serverLocation, "orange", "s"),
        ]:
            df_srv = df_chunk[df_chunk["server"] == server]
            if df_srv.empty:
                continue

            avg_lat = (
                df_srv.groupby("max_workers")["latency"]
                .agg(mean="mean", std="std", count="count")
                .reset_index()
                .sort_values("max_workers")
            )
            avg_lat["yerr"] = avg_lat["std"] / np.sqrt(avg_lat["count"])

            if server == "CEDA":
                ceda_series = avg_lat.set_index("max_workers")["mean"]
            else:
                dkrz_series = avg_lat.set_index("max_workers")["mean"]

            ax_top.errorbar(
                avg_lat["max_workers"],
                avg_lat["mean"],
                yerr=avg_lat["yerr"],
                label=f"{server} Mean Latency",
                color=color,
                marker=marker,
                linewidth=2,
                markersize=7,
                capsize=4,
                capthick=1.2,
            )

        ax_top.set_title(
            f"Latency vs Max Workers Comparison (Slice Range = {chunk} ± SEM)",
            fontsize=13,
            pad=15,
        )
        ax_top.set_ylabel("Average Latency (seconds)", fontsize=11)
        ax_top.grid(True, linestyle="--", alpha=0.5)
        ax_top.legend(fontsize=10, loc="best")

        # 2. Bottom Subplot: Ratio Calculation (CEDA / DKRZ)
        if (
            ceda_series is not None
            and dkrz_series is not None
            and not ceda_series.empty
            and not dkrz_series.empty
        ):
            comp_df = pd.DataFrame(
                {"CEDA": ceda_series, serverLocation: dkrz_series}
            ).dropna()

            if not comp_df.empty:
                comp_df["ratio"] = comp_df[serverLocation] / comp_df["CEDA"] 

                ax_bot.plot(
                    comp_df.index,
                    comp_df["ratio"],
                    color="purple",
                    marker="d",
                    linewidth=2,
                    markersize=7,
                    label="Ratio ("+serverLocation+"/CEDA)",
                )

        ax_bot.axhline(
            1.0,
            color="gray",
            linestyle="--",
            linewidth=1.2,
            label="Parity (1.0)",
        )

        ax_bot.set_title(
            "Latency Ratio (CEDA / "+serverLocation+")", fontsize=11, loc="left"
        )
        ax_bot.set_xlabel("Max Workers (Threads)", fontsize=11)
        ax_bot.set_ylabel("Ratio", fontsize=10)
        ax_bot.grid(True, linestyle="--", alpha=0.5)
        ax_bot.legend(fontsize=9, loc="best")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"Generated Item 1 PDF: {pdf_path_1}")


# =========================================================
# ITEM 2: Latency vs Time for CEDA and DKRZ (Overlaying All Slice Ranges)
# =========================================================
pdf_path_2 = os.path.join(OUTPUT_DIR, "2_latency_vs_time_overlay.pdf")
with PdfPages(pdf_path_2) as pdf:
    for server in ["CEDA", serverLocation]:
        df_srv = df_all[df_all["server"] == server]
        if df_srv.empty:
            continue

        fig, ax = plt.subplots(figsize=(11, 6))
        #srv_chunks = sorted(
        #    [c for c in df_srv["chunk_size"].dropna().unique()]
        #)

        srv_chunks = sorted(
            [c for c in df_srv["chunk_size"].dropna().unique()], reverse=True
        )
        cmap = plt.cm.get_cmap("tab10", max(len(srv_chunks), 1))

        for idx, chunk in enumerate(srv_chunks):
            df_c = df_srv[df_srv["chunk_size"] == chunk]
            ax.scatter(
                df_c["x_val_rel"],
                df_c["latency"],
                label=f"Slice Range {chunk}",
                color=cmap(idx),
                s=25,
                alpha=0.6,
                edgecolor="none",
                zorder=2 + idx,  # Explicitly increments draw order layer
            )

        ax.set_title(
            f"Latency vs Relative Time Distributions - {server} (All Slice Ranges)",
            fontsize=13,
            pad=15,
        )
        ax.set_xlabel(
            "Relative Completion Time (seconds from run start)", fontsize=11
        )
        ax.set_ylabel("Latency (seconds)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(title="Slice Ranges", fontsize=9, loc="best")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"Generated Item 2 PDF: {pdf_path_2}")


# =========================================================
# ITEM 3: Latency vs Clock (Normalized) per Max Worker and Slice Range
# =========================================================
pdf_path_3 = os.path.join(
    OUTPUT_DIR, "3_latency_vs_clock_per_chunk_and_workers.pdf"
)
with PdfPages(pdf_path_3) as pdf:
    grouped = df_all.groupby(["chunk_size", "max_workers"])

    for (chunk, workers), group in grouped:
        fig, ax = plt.subplots(figsize=(10, 6))

        for server, color in [("CEDA", "navy"), (serverLocation, "darkorange")]:
            df_srv = group[group["server"] == server]
            if df_srv.empty:
                continue

            ax.scatter(
                df_srv["x_val_rel"],
                df_srv["latency"],
                label=f"{server}",
                color=color,
                s=35,
                alpha=0.7,
                edgecolor="black",
                linewidth=0.3,
            )

        ax.set_title(
            f"Latency vs Normalized Time | Slice Range: {chunk} | Max Workers: {workers}",
            fontsize=12,
            pad=15,
        )
        ax.set_xlabel(
            "Relative Completion Time (seconds from run start)", fontsize=11
        )
        ax.set_ylabel("Latency (seconds)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(fontsize=10, loc="best")

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"Generated Item 3 PDF: {pdf_path_3}")

# =========================================================
# ITEM 4: Histogram of Byte Range for Given Max Workers and Slice Range (CEDA & DKRZ Overlay)
# =========================================================
pdf_path_4 = os.path.join(OUTPUT_DIR, "4_byte_range_histograms.pdf")
with PdfPages(pdf_path_4) as pdf:
    grouped = df_all.groupby(["chunk_size", "max_workers"])

    for (chunk, workers), group in grouped:
        fig, ax = plt.subplots(figsize=(10, 6))

        # Filter server subsets
        ceda_sizes = group[group["server"] == "CEDA"]["size_kb"].dropna()
        dkrz_sizes = group[group["server"] == serverLocation]["size_kb"].dropna()

        # Calculate statistics for CEDA
        n_ceda = len(ceda_sizes)
        mean_ceda = ceda_sizes.mean() if n_ceda > 0 else 0.0
        std_ceda = ceda_sizes.std() if n_ceda > 1 else 0.0

        # Calculate statistics for DKRZ
        n_dkrz = len(dkrz_sizes)
        mean_dkrz = dkrz_sizes.mean() if n_dkrz > 0 else 0.0
        std_dkrz = dkrz_sizes.std() if n_dkrz > 1 else 0.0

        # Determine shared bin ranges
        all_sizes = group["size_kb"].dropna()
        if all_sizes.empty:
            plt.close(fig)
            continue
        bins = np.linspace(all_sizes.min(), all_sizes.max(), 100)

        # Plot overlayed histograms
        if n_ceda > 0:
            ax.hist(
                ceda_sizes,
                bins=bins,
                color="tab:blue",
                alpha=0.5,
                edgecolor="black",
                label="CEDA",
                weights=np.ones(n_ceda),
            )

        if n_dkrz > 0:
            ax.hist(
                dkrz_sizes,
                bins=bins,
                color="tab:orange",
                alpha=0.5,
                edgecolor="black",
                label=serverLocation,
                weights=np.ones(n_dkrz),
            )

        # Statistical overlay callout box for both CEDA and DKRZ
        stats_text = (
            f"CEDA:\n"
            f"  Entries: {n_ceda}\n"
            f"  Mean: {mean_ceda:.2f} KB\n"
            f"  Std Dev: {std_ceda:.2f} KB\n\n"
            f"{serverLocation}:\n"
            f"  Entries: {n_dkrz}\n"
            f"  Mean: {mean_dkrz:.2f} KB\n"
            f"  Std Dev: {std_dkrz:.2f} KB"
        )
        ax.text(
            0.5,
            0.95,
            stats_text,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            horizontalalignment="right",
            bbox=dict(
                boxstyle="round,pad=0.5",
                facecolor="wheat",
                alpha=0.8,
                edgecolor="grey",
            ),
        )

        ax.set_title(
            f"Byte Range Size Distribution | Slice Range: {chunk} | Max Workers: {workers}",
            fontsize=12,
            pad=15,
        )
        ax.set_xlabel("Byte Range Size (KB)", fontsize=11)
        ax.set_ylabel("Number of Requests (Count)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(loc="upper left", fontsize=10)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

print(f"Generated Item 4 PDF: {pdf_path_4}")