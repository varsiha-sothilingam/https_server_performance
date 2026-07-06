#!/bin/bash

# --- SLURM Directives ---
#SBATCH --job-name=python_conda_runtesting
#SBATCH --account=ncas_cms
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --qos=debug
#SBATCH --partition=debug
#SBATCH --output=/home/users/varsiha/http_server_perf/logs/my_job_%j.out
#SBATCH --error=/home/users/varsiha/http_server_perf/logs/my_job_%j.err

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

# ENV SETUP
source ~/miniconda3/etc/profile.d/conda.sh
conda activate activestorage

# ADDITIONAL SETUP
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

# SCRIPT TO RUN
/usr/bin/time -a -o /home/users/varsiha/http_server_perf/logs/my_job_${SLURM_JOB_ID}.out  python /home/users/varsiha/http_server_perf/test_https_servers.py

# --- 4. Log Completion Time ---
echo "------------------------------------------------"
echo "Job Completed at:  $(date)"
echo "------------------------------------------------"

