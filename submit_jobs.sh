#!/bin/bash

# --- SLURM Directives ---
#SBATCH --job-name=python_conda_runtesting
#SBATCH --account=ncas_cms
#SBATCH --time=01:00:00
#SBATCH --qos=high
#SBATCH --partition=standard

#SBATCH --array=0-15%16
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4


# 2. Use special placeholders for unique log files:
# %A = The Master Job ID
# %a = The specific Array Index (1, 2, 3...)
#SBATCH --output=/home/users/varsiha/http_server_perf/logs-myTest/log_%A_%a.out
#SBATCH --error=/home/users/varsiha/http_server_perf/logs-myTest/log_%A_%a.err

# --- 1. Log Job Conditions and Start Time ---
echo "------------------------------------------------"
echo "Job ID:            $SLURM_JOB_ID"
echo "Job Name:          $SLURM_JOB_NAME"
echo "Partition:         $SLURM_JOB_PARTITION"
echo "Number of Nodes:   $SLURM_NNODES"
echo "CPUs per Task:     $SLURM_CPUS_PER_TASK"
echo "Memory per Node:   $SLURM_MEM_PER_NODE"
echo "Submit Directory:  $SLURM_SUBMIT_DIR"
echo "Start Time:        $(date)"
echo "------------------------------------------------"


# --- Environment Setup ---
source ~/miniconda3/etc/profile.d/conda.sh
conda activate activestorage
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

timestamp=$(date +"%Y%m%d_%H%M%S")

bench_configs=(
    "1   1 1 1"
    "2   2 1 1" 
    "3   3 1 1"
    "4   4 1 1" 
    "6   3 2 1"
    "8   4 2 1"
    "9   3 3 1"
    "12  4 3 1"
    "16  4 4 1"
    "18  3 3 2"
    "24  4 3 2"
    "27  3 3 3"
    "32  4 4 2"
    "36  4 3 3"
    "48  4 4 3"
    "64  4 4 4"
)




CONFIG=${bench_configs[$SLURM_ARRAY_TASK_ID]}

# 2. Parse it
read -r total nx ny nz <<< "$CONFIG"

# 3. Execute
echo "Task ID $SLURM_ARRAY_TASK_ID is processing Total Chunks: $total (Split: $nx $ny $nz)"



# --- Logic ---
# SLURM automatically creates a variable called $SLURM_ARRAY_TASK_ID 
# for every sub-job in the array.



# --- Execution ---
# Use the -o and -a flags with 'time' to log to the specific file for this index

/usr/bin/time -v -a -o /home/users/varsiha/http_server_perf/logs-myTest/process_metrics_${timestamp}_${SLURMD_NODENAME}_${SLURM_ARRAY_JOB_ID}_${total}_Chunks.out \
python /home/users/varsiha/http_server_perf/test_https_servers.py --nChunks ${nx} ${ny} ${nz}


# --- 4. Log Completion Time ---
echo "------------------------------------------------"
echo "Job Task $i Completed at:  $(date)"
echo "------------------------------------------------"
