#!/bin/bash

# Define the hardware options for each tier
frontend_options=("low_performance" "high_performance")
cache_options=("DRAM" "flash")
backend_options=("SSD" "HDD" "tape" "glass")

# Define the range of SLO values
slo_latency_values=(10)  # Define desired latency values
slo_throughput_values=(10000000)  # Define desired throughput values

# Define the simulation period (in years)
simulation_years=10  # You can change this value as needed

# Output CSV file
output_file="results.csv"

# Initialize the CSV file with headers
echo "SLO Latency,SLO Throughput,Frontend,Cache,Backend,Average Latency,Peak Throughput,Cumulative Carbon Cost,Frontend Servers,Cache Servers,Backend Servers,Cache Hit Rate,Embodied Cost,Active Cost,Idle Cost,Replacement Cost,Frontend Size (GB),Cache Size (GB),Backend Size (GB),Total Size (GB),Simulation Years" > $output_file

# Iterate over all SLO latency values
for slo_latency in "${slo_latency_values[@]}"; do
    # Iterate over all SLO throughput values
    for slo_throughput in "${slo_throughput_values[@]}"; do
        # Iterate over all combinations of frontend, cache, and backend hardware
        for frontend in "${frontend_options[@]}"; do
            for cache in "${cache_options[@]}"; do
                for backend in "${backend_options[@]}"; do
                    echo "Running cost model for SLO Latency=$slo_latency ms, SLO Throughput=$slo_throughput req/s, Frontend=$frontend, Cache=$cache, Backend=$backend, Simulation Years=$simulation_years"
                    
                    # Run the Python script and capture the output
                    python3 carbon_stream.py --slo_latency $slo_latency --slo_throughput $slo_throughput --frontend $frontend --cache $cache --backend $backend --simulation_years $simulation_years --output $output_file

                    echo "---------------------------------------"
                done
            done
        done
    done
done

# Plot the results for each combination of SLO Latency and Throughput
for slo_latency in "${slo_latency_values[@]}"; do
    for slo_throughput in "${slo_throughput_values[@]}"; do
        echo "Plotting results for SLO Latency=$slo_latency ms, SLO Throughput=$slo_throughput req/s"
        python3 plot_results.py $output_file $slo_latency $slo_throughput
    done
done