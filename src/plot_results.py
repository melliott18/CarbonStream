import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Get the output file name and SLO values from the command line arguments
if len(sys.argv) != 5:
    print("Usage: python plot_results.py <slo_latency> <slo_throughput> <simulation_years> <output_file>")
    sys.exit(1)

slo_latency = int(sys.argv[1])
slo_throughput = int(sys.argv[2])
simulation_years = int(sys.argv[3])
results_file = sys.argv[4]

# Load the results from the CSV file
results = pd.read_csv(results_file)

# Filter results based on the specific SLO latency and throughput
filtered_results = results[(results['SLO Latency'] == slo_latency) & (results['SLO Throughput'] == slo_throughput)]

if filtered_results.empty:
    print(f"No results found for SLO Latency={slo_latency} ms and SLO Throughput={slo_throughput} req/s")
    sys.exit(1)

# Identify the configuration with the lowest cumulative carbon cost
lowest_cost_row = filtered_results.loc[filtered_results['Cumulative Carbon Cost'].idxmin()]
lowest_cost_config = f"Frontend={lowest_cost_row['Frontend']}, Cache={lowest_cost_row['Cache']}, Backend={lowest_cost_row['Backend']}"
lowest_cost_value = lowest_cost_row['Cumulative Carbon Cost']

print(f"Configuration with the lowest cumulative carbon cost:")
print(f"  {lowest_cost_config}")
print(f"  Average Latency: {lowest_cost_row['Average Latency']:.2f} ms")
print(f"  Peak Throughput: {lowest_cost_row['Peak Throughput']:.2f} requests/second")
print(f"  Embodied Carbon Cost: {lowest_cost_row['Embodied Cost']:.2f} kg CO2e")
print(f"  Active Carbon Cost: {lowest_cost_row['Active Cost']:.2f} kg CO2e")
print(f"  Idle Carbon Cost: {lowest_cost_row['Idle Cost']:.2f} kg CO2e")
print(f"  Replacement Carbon Cost: {lowest_cost_row['Replacement Cost']:.2f} kg CO2e")
print(f"  Cumulative Carbon Cost over {lowest_cost_row['Simulation Years']} years: {lowest_cost_value:.2f} kg CO2e")
print(f"  Number of Frontend Servers: {lowest_cost_row['Frontend Servers']:g}")
print(f"  Number of Cache Servers: {lowest_cost_row['Cache Servers']:g}")
print(f"  Number of Backend Servers: {lowest_cost_row['Backend Servers']:g}")
print(f"  Cache Hit Rate: {lowest_cost_row['Cache Hit Rate']:.2f}")

# Create directory for the plots
plot_dir = '../data/plots'
os.makedirs(plot_dir, exist_ok=True)

# Plot total cumulative carbon costs across all configurations with breakdowns
plt.figure(figsize=(12, 8))

config_names = []
embodied_costs = []
access_costs = []
idle_costs = []
replacement_costs = []

for index, row in filtered_results.iterrows():
    config_name = f"Frontend: {row['Frontend']} - Cache: {row['Cache']} - Backend: {row['Backend']}"
    config_names.append(config_name)
    embodied_costs.append(row['Embodied Cost'])
    access_costs.append(row['Active Cost'])
    idle_costs.append(row['Idle Cost'])
    replacement_costs.append(row['Replacement Cost'])

# Create stacked bar chart
bar_width = 0.5
bar_positions = range(len(config_names))

plt.barh(bar_positions, embodied_costs, color='blue', label='Embodied Cost', height=bar_width)
plt.barh(bar_positions, access_costs, color='orange', label='Active Cost', height=bar_width, left=embodied_costs)
plt.barh(bar_positions, idle_costs, color='green', label='Idle Cost', height=bar_width, left=[i+j for i,j in zip(embodied_costs, access_costs)])
plt.barh(bar_positions, replacement_costs, color='red', label='Replacement Cost', height=bar_width, left=[i+j+k for i,j,k in zip(embodied_costs, access_costs, idle_costs)])

plt.yticks(bar_positions, config_names)
plt.xlabel('Cumulative Carbon Cost (kg CO2e)')
plt.title(f'Total Cumulative Carbon Costs\nSLO Latency={slo_latency} ms, Throughput={slo_throughput} req/s, {filtered_results.iloc[0]["Simulation Years"]} years')
plt.legend(loc='upper right')
plt.grid(True)

plt.tight_layout()
plt.savefig(os.path.join(plot_dir, f'Total_Carbon_Cost_Breakdown_slo_{slo_latency}ms_{slo_throughput}reqs_{simulation_years}years.png'))
plt.show()

# Plot each configuration with multiple costs on the same graph
for index, row in filtered_results.iterrows():
    config_name = f"Frontend: {row['Frontend']} - Cache: {row['Cache']} - Backend: {row['Backend']}"

    plt.figure(figsize=(10, 6))

    # Use the calculated costs directly from the CSV
    costs = [row['Embodied Cost'], row['Active Cost'], row['Idle Cost'], row['Replacement Cost']]
    labels = ['Embodied Cost', 'Active Cost', 'Idle Cost', 'Replacement Cost']
    
    plt.bar(labels, costs, color=['blue', 'orange', 'green', 'red'])
    plt.title(f'Carbon Costs for SLO Latency={slo_latency} ms and Throughput={slo_throughput} req/s\nConfiguration: {config_name} over {row["Simulation Years"]} years')
    plt.ylabel('Carbon Cost (kg CO2e)')
    plt.grid(True)
    
    plt.tight_layout()
    plot_name = f"{config_name.replace(': ', '_').replace(' ', '').replace('-', '_')}"
    plt.savefig(os.path.join(plot_dir, f'Carbon_Cost_Breakdown_{plot_name}_slo_{slo_latency}ms_{slo_throughput}reqs_{simulation_years}years.png'))
    plt.show()