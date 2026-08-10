from datetime import datetime
import os
import re
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------
# CONFIGURATION TOGGLES
# ---------------------------------------------------------
# 'run'       -> Color code by Batch Run (Legend)
# 'byte_size' -> Color code by Byte Range Size KB (Colorbar)
# 'workers'   -> Color code by maxWorkers value
# 'none'      -> Monochrome plot
COLOR_BY = "byte_size"

# True:  T=0.0s is the earliest start timestamp of EACH run
# False: Absolute clock time
NORMALIZE_PER_RUN = True

# Filter BOTH plots by maxWorkers (e.g., 20 or [1, 2, 5, 10, 20] or None for ALL)
FILTER_WORKERS = 10  

# Filter BOTH plots by chunk size (e.g., 15 or [5, 10, 15] or None for ALL)
FILTER_CHUNK_SIZE = 15  


FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-CEDA-var-clw-HTTPS-ServerTesting-20260810-115420.output"
FILE_PATH = "/Users/dh935740@reading.ac.uk/https_server_performance/output-clw/ESGF-DKRZ-var-clw-HTTPS-ServerTesting-20260810-115734.output"

testLocation = "DKRZ-10Workers-Chunk15"
OUTPUT_DIR = "output-clw/"


def save_and_close(filename):
    """Saves the current plot as PNG and PDF, then closes it to free memory."""
    png_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
    pdf_path = os.path.join(OUTPUT_DIR, f"{filename}.pdf")

    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.savefig(pdf_path, bbox_inches="tight")
    plt.close()  # Vital to prevent RAM exhaustion


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


with open(FILE_PATH, "r") as f:
    log_data = f.read()

# ---------------------------------------------------------
# REGEX PATTERNS
# ---------------------------------------------------------
req_pattern = r"(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2}\.\d{6})\s+([a-f0-9]+)\s+Range=bytes=(\d+)-(\d+)(?:\s+(Recieved))?"

# Captures both completed and failed thread lines:
thread_boundary_pattern = r"Thread for range\[(\d+,\d+)\]\s+(completed|FAILED)(?:\s+\|\s+maxWorkers:\s*(\d+))?.*?(?: Error:\s*(.*))?$"

# ---------------------------------------------------------
# PARSING LOGIC
# ---------------------------------------------------------
current_run_id = 0
run_metadata = {}
sent_events = {}
records = []
failed_threads = []

for line in log_data.strip().split("\n"):
    # Check for thread boundary (Completed OR Failed)
    thread_match = re.search(thread_boundary_pattern, line)
    if thread_match:
        range_str, status, workers_str, error_msg = thread_match.groups()
        workers = int(workers_str) if workers_str else None

        # Store metadata for the COMPLETED run_id
        run_metadata[current_run_id] = {
            "range": range_str,
            "status": status,
            "max_workers": workers,
            "error": error_msg.strip() if error_msg else None,
        }

        # Track failed threads
        if status == "FAILED":
            failed_threads.append({
                "run_id": current_run_id,
                "range": range_str,
                "max_workers": workers if workers is not None else "N/A",
                "error": error_msg.strip() if error_msg else "Unknown Error",
            })

        current_run_id += 1
        continue

    # Parse HTTP Requests (Sent & Received)
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
                    "run_id": sent_info["run_id"],
                    "start_clock": sent_info["start_time"],
                    "end_clock": dt,
                    "latency": latency,
                    "size_kb": sent_info["size_kb"],
                })

df = pd.DataFrame(records)

# ---------------------------------------------------------
# MAP METADATA AFTER DATAFRAME CREATION
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# DIAGNOSTIC LOG INSPECTION
# ---------------------------------------------------------
print("\n" + "=" * 60)
print("PARSED LOG FILE SUMMARY")
print("=" * 60)

unique_ranges = df["range"].unique().tolist()
print(f"Unique range[] values found ({len(unique_ranges)} total):")
print(unique_ranges)

unique_chunks = sorted(
    [c for c in df["chunk_size"].unique() if c is not None]
)
print(f"\nUnique chunk sizes found ({len(unique_chunks)} total):")
print(unique_chunks)

unique_workers = sorted(
    [w for w in df["max_workers"].unique() if w is not None]
)
print(f"\nUnique maxWorkers values found ({len(unique_workers)} total):")
print(unique_workers)

print("=" * 60 + "\n")

# Map descriptive run labels
df["run_label"] = df.apply(
    lambda row: f"Run {row['run_id']} (range[{row['range']}], chunk={row['chunk_size']}, workers={row['max_workers']})",
    axis=1,
)

# ---------------------------------------------------------
# TIME NORMALIZATION
# ---------------------------------------------------------
if NORMALIZE_PER_RUN:
    run_start_times = df.groupby("run_id")["start_clock"].transform("min")
    df["x_val"] = (df["end_clock"] - run_start_times).dt.total_seconds()
    x_label = "Relative Completion Time (seconds from run start)"
else:
    df["x_val"] = df["end_clock"]
    x_label = "Absolute End Clock Time (HH:MM:SS)"

# ---------------------------------------------------------
# APPLY GLOBAL FILTERING (FILTER_WORKERS & FILTER_CHUNK_SIZE)
# ---------------------------------------------------------
df_filtered = df.copy()

# 1. Filter by maxWorkers
if FILTER_WORKERS is not None:
    if not isinstance(FILTER_WORKERS, list):
        target_workers = [int(FILTER_WORKERS)]
    else:
        target_workers = [int(w) for w in FILTER_WORKERS]

    df_filtered = df_filtered[
        df_filtered["max_workers"].fillna(-1).astype(int).isin(target_workers)
    ]

# 2. Filter by chunk_size
if FILTER_CHUNK_SIZE is not None:
    if not isinstance(FILTER_CHUNK_SIZE, list):
        target_chunks = [int(FILTER_CHUNK_SIZE)]
    else:
        target_chunks = [int(c) for c in FILTER_CHUNK_SIZE]

    df_filtered = df_filtered[
        df_filtered["chunk_size"].fillna(-1).astype(int).isin(target_chunks)
    ]

print(
    f"Filtered Dataset: Retained {len(df_filtered)} records out of {len(df)} total "
    f"(Workers: {FILTER_WORKERS}, Chunk Size: {FILTER_CHUNK_SIZE}).\n"
)

# ---------------------------------------------------------
# PLOT 1: LATENCY VS TIME (FILTERED BY WORKERS & CHUNK SIZE)
# ---------------------------------------------------------
fig1, ax1 = plt.subplots(figsize=(11, 6))

if COLOR_BY == "run":
    for run_label, group in df_filtered.groupby("run_label"):
        ax1.scatter(
            group["x_val"],
            group["latency"],
            label=run_label,
            s=30,
            edgecolor="black",
            linewidth=0.5,
            alpha=0.85,
        )
    ax1.legend(title="Batch Runs", loc="best")

elif COLOR_BY == "workers":
    scatter1 = ax1.scatter(
        df_filtered["x_val"],
        df_filtered["latency"],
        c=df_filtered["max_workers"],
        cmap="coolwarm",
        s=30,
        edgecolor="black",
        linewidth=0.5,
        alpha=0.85,
    )
    cbar1 = fig1.colorbar(scatter1, ax=ax1)
    cbar1.set_label("Max Workers", fontsize=10)

elif COLOR_BY == "byte_size":
    scatter1 = ax1.scatter(
        df_filtered["x_val"],
        df_filtered["latency"],
        c=df_filtered["size_kb"],
        cmap="viridis",
        s=100,
        edgecolor="none",
        linewidth=0.5,
        alpha=0.85,
    )
    cbar1 = fig1.colorbar(scatter1, ax=ax1)
    cbar1.set_label("Byte Range Size (KB)", fontsize=10)

elif COLOR_BY == "none":
    ax1.scatter(
        df_filtered["x_val"],
        df_filtered["latency"],
        s=30,
        edgecolor="black",
        linewidth=0.5,
        alpha=0.85,
    )

if not NORMALIZE_PER_RUN:
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S.%f"))
    fig1.autofmt_xdate()

# Dynamic Title Header
filter_text_parts = []
if FILTER_WORKERS is not None:
    filter_text_parts.append(f"Workers: {FILTER_WORKERS}")
if FILTER_CHUNK_SIZE is not None:
    filter_text_parts.append(f"Chunk Size: {FILTER_CHUNK_SIZE}")
filter_text = f" ({', '.join(filter_text_parts)})" if filter_text_parts else ""

ax1.set_title(
    f"Latency vs. Completion Time{filter_text} (Colored by: {COLOR_BY})",
    fontsize=12,
)
ax1.set_xlabel(x_label, fontsize=10)
ax1.set_ylabel("Latency (seconds)", fontsize=10)
ax1.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
save_and_close(testLocation + "-Latency_v_timeNormalised")

# ---------------------------------------------------------
# PLOT 2: AVERAGE LATENCY VS MAX WORKERS (FILTERED BY CHUNK SIZE)
# ---------------------------------------------------------
# Note: Plot 2 filters by chunk size, but includes all maxWorkers to show scaling
df_avg = df.dropna(subset=["max_workers"]).copy()

if FILTER_CHUNK_SIZE is not None:
    if not isinstance(FILTER_CHUNK_SIZE, list):
        target_chunks = [int(FILTER_CHUNK_SIZE)]
    else:
        target_chunks = [int(c) for c in FILTER_CHUNK_SIZE]

    df_avg = df_avg[df_avg["chunk_size"].isin(target_chunks)]

avg_latencies = (
    df_avg.groupby("max_workers")["latency"]
    .agg(mean_latency="mean", sample_count="count")
    .reset_index()
    .sort_values("max_workers")
)

fig2, ax2 = plt.subplots(figsize=(9, 6))

scatter2 = ax2.scatter(
    avg_latencies["max_workers"],
    avg_latencies["mean_latency"],
    s=120,
    color="crimson",
    edgecolor="black",
    linewidth=1.2,
    alpha=0.9,
    zorder=3,
)

ax2.plot(
    avg_latencies["max_workers"],
    avg_latencies["mean_latency"],
    linestyle="--",
    color="crimson",
    alpha=0.5,
    zorder=2,
)

chunk_title = (
    f" (Chunk Size: {FILTER_CHUNK_SIZE})"
    if FILTER_CHUNK_SIZE is not None
    else " (All Chunk Sizes)"
)
ax2.set_title(
    f"Overall Average Request Latency vs. Max Workers{chunk_title}",
    fontsize=12,
    pad=15,
)
ax2.set_xlabel("Number of Max Workers", fontsize=10)
ax2.set_ylabel("Average Latency (seconds)", fontsize=10)
ax2.grid(True, linestyle="--", alpha=0.5)

if not avg_latencies.empty:
    ax2.set_xticks(avg_latencies["max_workers"].unique())

plt.tight_layout()
save_and_close(testLocation + "-avgLatency_v_maxWorkers")