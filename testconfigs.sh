#!/bin/bash

# Define the configurations: "Total_Chunks NX NY NZ"
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

echo "Starting Benchmark Loop..."
echo "--------------------------"

# Loop over each configuration string
for config in "${bench_configs[@]}"; do
    # Read the space-separated string into variables
    read -r total nx ny nz <<< "$config"
    
    # Print the values as requested
    echo "nChunks: $total | List: [$nx, $ny, $nz]"
    
    # Example: If you want to run your python script, you'd add:
    # python your_script.py $nx $ny $nz
done

echo "--------------------------"
echo "Done."