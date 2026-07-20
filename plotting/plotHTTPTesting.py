import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

output_dir = "saved_plots"

# Set style for all plots
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)


def load_and_clean_data(csv_path):
    """
    Loads the benchmarking CSV and prepares the columns.
    Converts EndClock to datetime.
    """
    df = pd.read_csv(csv_path)
    
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

# =====================================================================
# 1. BASELINE & DISTRIBUTION PLOTS (1D)
# =====================================================================

def plot_PeakRequest_v_Latency(df):
    """Plots peak concurrent request vs latency."""
    plt.figure()
    df_pass = df_benchmarks[df_benchmarks['Status'] == 'success'] 
    print(len(df_pass ))

    df_pass['peakRequests'] = df_pass['maxWorkers'] * df_pass['chunkSize']
   

    sns.scatterplot(
        data=df_pass, 
        x="peakRequests", 
        y="Latency", 
        palette="colorblind",
        alpha=0.6,
    )
    #plt.xscale('log')
    #plt.title("Disk Seek & Cache Profile (StartIndex vs. Latency)", fontsize=14, fontweight='bold')
    plt.xlabel("Peak concurrent HTTPS Requests")
    plt.ylabel("Latency (seconds)")
    plt.tight_layout()
    save_and_close("peakRequest_v_Latency")

def plot_TotalRequest_v_Latency(df):
    """Plots peak concurrent request vs latency."""

    # 1. Filter for only successful runs
    df_success = df[df['Status'] == 'success'].copy()

    # 2. Group by the test parameters and count the number of successful futures (rows)
    # We use .size() to get the row count for each unique combination
    grouped = df_success.groupby(['maxWorkers', 'chunkSize']).size().reset_index(name='successful_futures')

    # 3. Calculate Total HTTPS Requests
    # (Number of successful futures * chunkSize)
    grouped['total_http_requests'] = grouped['successful_futures'] * grouped['chunkSize']
    

    sns.scatterplot(
        x=grouped["total_http_requests"], 
        y=df_success["Latency"], 
        palette="colorblind",
        alpha=0.6
    )
    #plt.xscale('log')
    #plt.title("Disk Seek & Cache Profile (StartIndex vs. Latency)", fontsize=14, fontweight='bold')
    plt.xlabel("Total HTTPS Requests")
    plt.ylabel("Latency (seconds)")
    plt.tight_layout()
    save_and_close("TotalRequest_v_Latency")



def plot_latency_distribution(df):
    """Plots a histogram distribution of request latencies."""
    
    # Filter for anything that is NOT a success   
    #df_failed = df_benchmarks[df_benchmarks['Status'] != 'success'] 
    # Calculate the average latency of ONLY successful runs
    #avg_success_latency = df_benchmarks[df_benchmarks['Status'] == 'success']['Latency'].mean()
    #print(f"Average Success Latency: {avg_success_latency:.4f} seconds")

    # Count how many total failures occurred
    #total_failures = len(df_benchmarks[df_benchmarks['Status'] != 'success'])
    #print(f"Total Failed Requests: {total_failures}")
     #maxWorkers,chunkSize,

    #df_pass = df[(df['Status'] == 'success') and (df['maxWorkers'] == 1) and (df['chunkSize'] == 1) ] 
    # Filter using multiple exact conditions
    filtered_df = df_benchmarks[
    (df_benchmarks['chunkSize'] == 1) & 
    (df_benchmarks['Status'] == 'success')
    ]
    
    plt.figure()
    
    # Filter to plot successful and failed requests together/separately
    sns.histplot(
        data=filtered_df, 
        x="Latency", 
        hue="Status", 
        kde=True, 
        bins=30, 
        palette="viridis",
        multiple="stack"
    )
    
    plt.title("Latency Distribution Profile", fontsize=14, fontweight='bold')
    plt.xlabel("Latency (seconds)")
    plt.ylabel("Request Count")
    plt.tight_layout()
    save_and_close("latency_distribution-11")


def plot_chronological_latency(df):
    """Plots request latency over time to identify startup jitter vs steady state."""
    plt.figure()
    df_pass = df[df['Status'] == 'success'] 
    # Sort by execution time to ensure sequential plotting
    df_sorted = df_pass.sort_values('EndClock')
    
    sns.scatterplot(
        data=df_sorted, 
        x="EndClock", 
        y="Latency", 
        hue="maxWorkers",
        palette="colorblind",
        alpha=0.7
    )
    
    plt.title("Latency Over Time (Chronological Order)", fontsize=14, fontweight='bold')
    plt.xlabel("Timestamp (EndClock)")
    plt.ylabel("Latency (seconds)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    save_and_close("chronological_latency")


def plot_chronological_latency_maxOne(df):
    """Plots request latency over time to identify startup jitter vs steady state."""
    plt.figure()
    df_pass_tmp = df[df['Status'] == 'success'] 
    df_pass     = df_pass_tmp[df_pass_tmp['maxWorkers'] == 1] 
    # Sort by execution time to ensure sequential plotting
    df_sorted = df_pass.sort_values('EndClock')
    
    sns.scatterplot(
        data=df_sorted, 
        x="EndClock", 
        y="Latency", 
        hue="chunkSize",
        palette="colorblind",
        alpha=0.7
    )
    
    plt.title("Latency Over Time (Chronological Order)", fontsize=14, fontweight='bold')
    plt.xlabel("Timestamp (EndClock)")
    plt.ylabel("Latency (seconds)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    save_and_close("chronological_latency-maxOne")


def plot_error_frequency(df):
    """Plots a bar chart showing the frequency of different error statuses."""
    plt.figure()
    
    # Fill NaN errors with 'None' for proper plotting
    df_errors = df.copy()
    df_errors['Error'] = df_errors['Error'].fillna('None')
    
    # Count occurrences
    error_counts = df_errors['Error'].value_counts()
    
    sns.barplot(
        x=error_counts.values, 
        y=error_counts.index, 
        palette="Reds_r"
    )
    
    plt.title("Error Code Frequency", fontsize=14, fontweight='bold')
    plt.xlabel("Count of Occurrences")
    plt.ylabel("Error Type / Status")
    plt.tight_layout()
    save_and_close("error_frequency")


# =====================================================================
# 2. OPERATIONAL BOTTLENECK PLOTS (2D)
# =====================================================================

def plot_concurrency_vs_latency(df):
    """Plots how changing max workers (concurrency) impacts latency."""
    plt.figure()
    
    # Use only successful runs to keep latency measurements clean
    df_success = df[df['Status'] == 'success']
    
    sns.lineplot(
        data=df_success, 
        x="maxWorkers", 
        y="Latency", 
        hue="chunkSize", 
        marker="o", 
        palette="crest"
    )
    
    plt.title("Concurrency (Workers) vs. Latency", fontsize=14, fontweight='bold')
    plt.xlabel("Max Workers (Concurrency)")
    plt.ylabel("Latency (seconds)")
    plt.tight_layout()
    save_and_close("concurrency_vs_latency")


def plot_chunk_size_vs_latency(df):
    """Plots how changing chunk size (payload) impacts latency."""
    plt.figure()
    
    df_success = df[df['Status'] == 'success']
    
    sns.lineplot(
        data=df_success, 
        x="chunkSize", 
        y="Latency", 
        hue="maxWorkers", 
        marker="s", 
        palette="colorblind",
        errorbar=None
    )

    plt.title("Chunk Size vs. Latency", fontsize=14, fontweight='bold')
    plt.yscale('log')
    plt.xlabel("Slice Range")
    plt.ylabel("Latency (seconds)")
    plt.tight_layout()
    save_and_close("slicerange_vs_latency-log")


def plot_disk_seek_cache(df):
    """Plots StartIndex vs Latency to search for disk-seeking lag patterns."""
    plt.figure()
    
    sns.scatterplot(
        data=df, 
        x="StartIndex", 
        y="Latency", 
        hue="maxWorkers", 
        palette="viridis",
        alpha=0.6
    )
    
    plt.title("Disk Seek & Cache Profile (StartIndex vs. Latency)", fontsize=14, fontweight='bold')
    plt.xlabel("StartIndex (Data Coordinate Position)")
    plt.ylabel("Latency (seconds)")
    plt.tight_layout()
    save_and_close("disk_seek_cache")


# =====================================================================
# 3. ADVANCED CORRELATION & MATRIX PLOTS
# =====================================================================

def plot_average_latency_heatmap(df):
    """Generates a matrix heatmap correlating chunkSize, maxWorkers, and Mean Latency."""
    plt.figure(figsize=(10, 8))
    
    df_success = df[df['Status'] == 'success']
    
    # Pivot to create index/column layout for heatmap
    matrix_data = df_success.pivot_table(
        values="Latency", 
        index="maxWorkers", 
        columns="chunkSize", 
        aggfunc=np.mean
    )
    
    sns.heatmap(
        matrix_data, 
        annot=True, 
        fmt=".4f", 
        cmap="YlOrRd", 
        cbar_kws={'label': 'Mean Latency (seconds)'}
    )
    
    plt.title("Heatmap: Mean Latency across Workers vs. Chunk Size", fontsize=14, fontweight='bold')
    plt.xlabel("Chunk Size")
    plt.ylabel("Max Workers")
    plt.tight_layout()
    save_and_close("average_latency_heatmap")


def plot_throughput_matrix(df, bytes_per_element=4):
    """
    Calculates dynamic Mbps throughput and plots it on a heatmap matrix.
    Assumes float32 array elements (4 bytes per element) by default.
    """
    plt.figure(figsize=(10, 8))
    
    df_success = df[df['Status'] == 'success'].copy()
    
    # Formula: (chunkSize * bytes_per_element * 8 bits) / (Latency * 1,000,000 bits)
    df_success['Throughput_Mbps'] = (
        (df_success['chunkSize'] * bytes_per_element * 8) / 
        (df_success['Latency'] * 1_000_000)
    )
    
    matrix_data = df_success.pivot_table(
        values="Throughput_Mbps", 
        index="maxWorkers", 
        columns="chunkSize", 
        aggfunc=np.mean
    )
    
    sns.heatmap(
        matrix_data, 
        annot=True, 
        fmt=".2f", 
        cmap="mako", 
        cbar_kws={'label': 'Throughput (Mbps)'}
    )
    
    plt.title("Heatmap: Average Throughput (Mbps)", fontsize=14, fontweight='bold')
    plt.xlabel("Chunk Size")
    plt.ylabel("Max Workers")
    plt.tight_layout()
    save_and_close("throughput_matrix")

def plot_failure_rate_matrix(df):
    """Generates a matrix heatmap correlating the percentage of failed tasks."""
    plt.figure(figsize=(10, 8))
    
    # Map success/failure to 1/0 for average percentage calculation
    df_fail = df.copy()
    df_fail['Is_Failure'] = (df_fail['Status'] != 'success').astype(int) * 100
    
    matrix_data = df_fail.pivot_table(
        values="Is_Failure", 
        index="maxWorkers", 
        columns="chunkSize", 
        aggfunc=np.mean
    )
    
    sns.heatmap(
        matrix_data, 
        annot=True, 
        fmt=".1f", 
        cmap="Reds", 
        cbar_kws={'label': 'Failure Rate (%)'}
    )
    
    plt.title("Heatmap: Request Failure Rate (%)", fontsize=14, fontweight='bold')
    plt.xlabel("Chunk Size")
    plt.ylabel("Max Workers")
    plt.tight_layout()
    save_and_close("failure_rate_matrix")


# =====================================================================
# SCRIPT EXECUTION
# =====================================================================

if __name__ == "__main__":
    # Change "your_data_file.csv" to the path of your benchmark CSV
    csv_file_path = "/home/users/varsiha/http_server_perf/performance_results_CEDA_15Jul2026111142.csv"
    
    try:
        # Load and clean
        df_benchmarks = load_and_clean_data(csv_file_path)
        
        plot_PeakRequest_v_Latency(df_benchmarks)
        plot_TotalRequest_v_Latency(df_benchmarks)
        plot_chunk_size_vs_latency(df_benchmarks)
        plot_chronological_latency(df_benchmarks)
        plot_chronological_latency_maxOne(df_benchmarks)
        """
        # Run 1D distributions
        plot_latency_distribution(df_benchmarks)
        plot_chronological_latency(df_benchmarks)
        plot_error_frequency(df_benchmarks)
        
        # Run 2D Bottleneck checks
        plot_concurrency_vs_latency(df_benchmarks)
        
        plot_disk_seek_cache(df_benchmarks)
        
        # Run advanced analysis matrices
        plot_average_latency_heatmap(df_benchmarks)
        plot_throughput_matrix(df_benchmarks, bytes_per_element=4)  # change element bytes if needed
        plot_failure_rate_matrix(df_benchmarks)
        """

    except FileNotFoundError:
        print(f"Error: Could not find '{csv_file_path}'. Check your path directory string.")
