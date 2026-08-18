import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#import seaborn as sns
import os

output_dir = "saved_plots_tmp"

# Set style for all plots
#sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def load_and_clean_data(csv_path):
    """
    Loads the benchmarking CSV and prepares the columns.
    Converts EndClock to datetime.
    """
    df = pd.read_csv(csv_path)
    print(df.columns.tolist())
    print(df[[ 'EndClock']].head(20))
    # Clean string column spaces if any exist
    df.columns = df.columns.str.strip()
    
    # Parse the custom EndClock format: '15/Jul/2026:11:11:50.532373'
    df['EndClock'] = pd.to_datetime(df['EndClock'], format='%d/%b/%Y:%H:%M:%S.%f')
    
    return df

def save_and_close(filename):
    """Saves the current plot as PNG and PDF, then closes it to free memory."""
    png_path = os.path.join(output_dir, f"{filename}.png")
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")
    
    plt.savefig(png_path, dpi=300, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close()  # Vital to prevent RAM exhaustion




def plot_latency(df_serv1,df_serv2, chunk_size):
    """
    Plot the average latency for a given chunk size and max workers.

    Parameters
    ----------
    csv_file : str
        Path to the CSV file.
    chunk_size : int
        Chunk size to filter on.
    max_workers : int
        Max workers value to filter on.
    """

    # Filter rows
    # Filter rows
    filtered_serv1 = df_serv1[
        (df_serv1["chunkSize"] == chunk_size) &
        (df_serv1["Status"] == "success")
    ]

    filtered_serv2 = df_serv2[
        (df_serv2["chunkSize"] == chunk_size) &
        (df_serv2["Status"] == "success")
    ]

    if filtered_serv1.empty:
        print("No matching data found.")
        return

 

    # Plot
    plt.figure(figsize=(7, 5))
    plt.scatter(
        filtered_serv1["maxWorkers"],
        filtered_serv1["Slice_Latency"],
        marker="o",
        color="steelblue",
        label="CEDA"
    )
    plt.scatter(
        filtered_serv2["maxWorkers"],
        filtered_serv2["Slice_Latency"],
        marker="o",
        color="red",
        label="DKRZ"
    )

    plt.xlabel("Max Workers")
    plt.ylabel(" Latency (s)")
    plt.title(f" Latency vs Max Workers\n Slice Size={chunk_size}")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    save_and_close("Latency_v_maxWorkers")


def plot_average_latency(df_serv1,df_serv2, chunk_size):
    """
    Plot the average latency for a given chunk size and max workers.

    Parameters
    ----------
    csv_file : str
        Path to the CSV file.
    chunk_size : int
        Chunk size to filter on.
    max_workers : int
        Max workers value to filter on.
    """

    # Filter rows
    filtered_serv1 = df_serv1[
        (df_serv1["chunkSize"] == chunk_size) &
        (df_serv1["Status"] == "success")
    ]

    filtered_serv2 = df_serv2[
        (df_serv2["chunkSize"] == chunk_size) &
        (df_serv2["Status"] == "success")
    ]

    if filtered_serv1.empty or filtered_serv2.empty:
        print("No matching data found.")
        return

    # Average latency for each maxWorkers value

    avg_latency_serv2 = (
        filtered_serv2
        .groupby("maxWorkers")["Slice_Latency"]
        #.mean()
        .agg(
        mean="mean",
        std="std",
        count="count",
        )
        .reset_index()
        .sort_values("maxWorkers")
    )
    avg_latency_serv1 = (
        filtered_serv1
        .groupby("maxWorkers")["Slice_Latency"]
        .mean()
        .reset_index()
        .sort_values("maxWorkers")
    )
    # Plot
    plt.figure(figsize=(7, 5))
    plt.plot(
        avg_latency_serv1["maxWorkers"],
        avg_latency_serv1["Slice_Latency"],
        marker="o",
        color="steelblue",
        label="CEDA"
    )
    plt.plot(
        avg_latency_serv2["maxWorkers"],
        avg_latency_serv2["Slice_Latency"],
        marker="o",
        color="red",
        label="DKRZ"
    )

    plt.xlabel("Max Workers")
    plt.ylabel("Average Latency (s)")
    plt.title(f"Average Latency vs Max Workers\n Slice Size={chunk_size}")
    plt.legend(loc="upper left")

    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    save_and_close("AvgLatency_v_maxWorkers")


def plot_latency_vs_clock_time(df_CEDA, df_DKRZ, max_workers, fileName):
    """
    Plot latency vs clock time for a given max workers value.
    
    Parameters
    ----------
    df_CEDA : pandas.DataFrame
    df_DKRZ : pandas.DataFrame
    max_workers : int
        Max workers value to filter on.
    """

    # Filter for selected max workers and successful requests
    filtered_CEDA = df_CEDA[
        (df_CEDA["maxWorkers"] == max_workers) &
        (df_CEDA["Status"] == "success")
    ].copy()

    filtered_DKRZ = df_DKRZ[
        (df_DKRZ["maxWorkers"] == max_workers) &
        (df_DKRZ["Status"] == "success")
    ].copy()

    if filtered_CEDA.empty and filtered_DKRZ.empty:
        print("No matching data found.")
        return

    # Sort by time
    filtered_CEDA = filtered_CEDA.sort_values("EndClock")
    filtered_DKRZ = filtered_DKRZ.sort_values("EndClock")

    # Create side-by-side subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    # CEDA plot
    axes[0].plot(
        filtered_CEDA["EndClock"],
        filtered_CEDA["Slice_Latency"],
        marker="o",
        linestyle="-",
        color="steelblue",
    )
    axes[0].set_title("CEDA")
    axes[0].set_xlabel("Clock Time")
    axes[0].set_ylabel("Latency (s)")
    axes[0].tick_params(axis="x", rotation=45)
    axes[0].grid(True, alpha=0.3)

    # DKRZ plot
    axes[1].plot(
        filtered_DKRZ["EndClock"],
        filtered_DKRZ["Slice_Latency"],
        marker="o",
        linestyle="-",
        color="red",
    )
    axes[1].set_title("DKRZ")
    axes[1].set_xlabel("Clock Time")
    axes[1].tick_params(axis="x", rotation=45)
    axes[1].grid(True, alpha=0.3)

    # Overall figure title
    fig.suptitle(f"Latency vs Clock Time (Max Workers = {max_workers})")

    plt.tight_layout()
    save_and_close(fileName)



import matplotlib.dates as mdates


def plot_latency_heatmap(df, site_name, bin_size="1ms"):
    """
    Heatmap of mean latency over time for each maxWorkers value.

    Parameters
    ----------
    df : pandas.DataFrame
        Must contain EndClock, Latency, maxWorkers, Status.
    site_name : str
        Title for the plot.
    bin_size : str
        Time bin size (e.g. '5s', '10s', '30s', '1min').
    """

    # Keep successful requests
    df = df[df["Status"] == "success"].copy()

    # Ensure datetime
    df["EndClock"] = pd.to_datetime(df["EndClock"])

    # Bin the times
    df["TimeBin"] = df["EndClock"].dt.floor(bin_size)

    # Pivot table: rows=workers, cols=time bins
    heatmap = df.pivot_table(
        index="maxWorkers",
        columns="TimeBin",
        values="Slice_Latency",
        aggfunc="mean"
    )

    fig, ax = plt.subplots(figsize=(12, 5))

    im = ax.imshow(
        heatmap.values,
        aspect="auto",
        origin="lower",
        cmap="viridis"
    )

    # Tick labels
    ax.set_yticks(range(len(heatmap.index)))
    ax.set_yticklabels(heatmap.index)

    ax.set_xticks(range(len(heatmap.columns)))
    ax.set_xticklabels(
        [t.strftime("%H:%M:%S") for t in heatmap.columns],
        rotation=45,
        ha="right"
    )

    ax.set_xlabel("Clock Time")
    ax.set_ylabel("Max Workers")
    ax.set_title(f"{site_name}: Mean Latency Heatmap")

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Mean Latency (s)")

    plt.tight_layout()
    save_and_close("heatmap-tmp")
# =====================================================================
# SCRIPT EXECUTION
# =====================================================================

if __name__ == "__main__":
    # Change "your_data_file.csv" to the path of your benchmark CSV
    
    #csv_file_path = "/home/users/varsiha/http_server_perf/performance_results_CEDA_15Jul2026111142.csv"
    csv_file_path = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_21Jul2026113832.csv"
    csv_file_path_CEDA = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_21Jul2026115339.csv"
    csv_file_path_CEDA = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_21Jul2026171131.csv"


    csv_file_path_CEDA = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_22Jul2026170658.csv" 
    csv_file_path_CEDA = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_24Jul2026124446.csv"

    #csv_file_path_CEDA = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_CEDA_22Jul2026172241.csv"
    #csv_file_path_DKRZ = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_DKRZ_21Jul2026142245.csv"
    #csv_file_path_DKRZ = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_DKRZ_21Jul2026151136.csv"
    csv_file_path_DKRZ = "/Users/dh935740@reading.ac.uk/https_server_performance/performance_results_DKRZ_21Jul2026170111.csv"
    csv_file_path_DKRZ = "//Users/dh935740@reading.ac.uk/https_server_performance/performance_results_DKRZ_24Jul2026123537.csv"
    try:
        # Load and clean
        df_benchmarks_CEDA = load_and_clean_data(csv_file_path_CEDA)
        df_benchmarks_DKRZ = load_and_clean_data(csv_file_path_DKRZ)
        
        #Plot

        #plot_average_latency(df_benchmarks_CEDA, df_benchmarks_DKRZ , 5)
        #plot_latency(df_benchmarks_CEDA, df_benchmarks_DKRZ, 5)
        
        plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 15, "Latency_v_Clock-15Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 14, "Latency_v_Clock-14Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 13, "Latency_v_Clock-13Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 12, "Latency_v_Clock-12Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 11, "Latency_v_Clock-11Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ, 10, "Latency_v_Clock-10Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  9, "Latency_v_Clock-9Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  8, "Latency_v_Clock-8Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  7, "Latency_v_Clock-7Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  6, "Latency_v_Clock-6Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  5, "Latency_v_Clock-5Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  2, "Latency_v_Clock-2Workers")
        #plot_latency_vs_clock_time(df_benchmarks_CEDA,df_benchmarks_DKRZ,  1, "Latency_v_Clock-1Workers")

        #plot_latency_heatmap(df_benchmarks_DKRZ, "DKRZ", bin_size="1ms")

        #plot_PeakRequest_v_Latency(df_benchmarks)
        #plot_TotalRequest_v_Latency(df_benchmarks)
        #plot_chunk_size_vs_latency(df_benchmarks)
        #plot_chronological_latency(df_benchmarks)
        #plot_chronological_latency_maxOne(df_benchmarks)


    except FileNotFoundError:
        print(f"Error: Could not find '{csv_file_path_CEDA}'. Check your path directory string.")
