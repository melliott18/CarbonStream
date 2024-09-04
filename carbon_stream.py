import argparse
import csv
import os
import numpy as np

# Define the tier-specific classes for holding parameters

class FrontendParams:
    LATENCY = {
        'low_performance': 0.08,
        'high_performance': 0.00000001,
    }
    THROUGHPUT = {
        'low_performance': 5,
        'high_performance': 20,
    }
    CARBON_COST = {
        'low_performance': 0.16,
        'high_performance': 0.31,
    }
    ACCESS_COST = { # kg CO2e/GB/second
        'low_performance': {'read': 0.0000000004, 'write': 0.0000000004},
        'high_performance': {'read': 0.000000087, 'write': 0.000000087},
    }
    IDLE_COST = { # kg CO2e/GB/second
        'low_performance': 0.00000000013,
        'high_performance': 0.000000087,
    }
    LIFESPAN_YEARS = {
        'low_performance': 5,
        'high_performance': 10,
    }
    SIZE = {
        'low_performance': 3840,  # Example size in GB
        'high_performance': 4096,  # Example size in GB
    }

class CacheParams:
    LATENCY = {
        'DRAM': 0.00000001,
        'flash': 0.08,
    }
    THROUGHPUT = {
        'DRAM': 20,
        'flash': 5,
    }
    CARBON_COST = {
        'DRAM': 0.31,
        'flash': 0.16,
    }
    ACCESS_COST = { # kg CO2e/GB/second
        'DRAM': {'read': 0.000000087, 'write': 0.000000087},
        'flash': {'read': 0.0000000004, 'write': 0.0000000004},
    }
    IDLE_COST = { # kg CO2e/GB/second
        'DRAM': 0.000000087,
        'flash': 0.00000000013,
    }
    LIFESPAN_YEARS = {
        'DRAM': 10,
        'flash': 5,
    }
    SIZE = {
        'DRAM': 4096,  # Example size in GB
        'flash': 3840,  # Example size in GB
    }

class BackendParams:
    LATENCY = {
        'SSD': 0.08,
        'HDD': 4.16,
        'tape': 10000,
        'glass': 10,
    }
    THROUGHPUT = {
        'SSD': 5,
        'HDD': 0.27,
        'tape': 0.4,
        'glass': 0.21,
    }
    CARBON_COST = {
        'SSD': 0.16,
        'HDD': 0.0017,
        'tape': 0.00042,
        'glass': 0.0001,
    }
    ACCESS_COST = { # kg CO2e/GB/second
        'SSD': {'read': 0.0000000004, 'write': 0.00000000049},
        'HDD': {'read': 0.000000000073, 'write': 0.000000000073},
        'tape': {'read': 0.000000000002, 'write': 0.000000000002},
        'glass': {'read': 0.000000000001, 'write': 0.00000000001},
    }
    IDLE_COST = { # kg CO2e/GB/second
        'SSD': 0.00000000013,
        'HDD': 0.000000000041,
        'tape': 0,
        'glass': 0,
    }
    LIFESPAN_YEARS = {
        'SSD': 5,
        'HDD': 5,
        'tape': 30,
        'glass': 100,
    }
    SIZE = {
        'SSD': 3840,  # Example size in GB
        'HDD': 18000,  # Example size in GB
        'tape': 18000,  # Example size in GB
        'glass': 7000,  # Example size in GB
    }

# Define network and processing latencies
NETWORK_LATENCY = 1  # in milliseconds
PROCESSING_LATENCY = 0.5  # in milliseconds

# Hardcoded read/write ratio
READ_RATIO = 0.7  # 70% reads
WRITE_RATIO = 1 - READ_RATIO  # 30% writes

# Hardcoded number of videos stored in the system
NUM_VIDEOS = 10000000000  # Example value

# Define load capacity as a fraction of time servers are active
LOAD_CAPACITY = 0.7  # Example: 70% active, 30% idle

# Struct to hold server configuration
class ServerConfig:
    def __init__(self, hardware, params):
        self.latency = params.LATENCY[hardware]
        self.throughput = params.THROUGHPUT[hardware]
        self.carbon_cost = params.CARBON_COST[hardware]
        self.active_cost = params.ACCESS_COST[hardware]
        self.idle_cost = params.IDLE_COST[hardware]
        self.lifespan_years = params.LIFESPAN_YEARS[hardware]
        self.size = params.SIZE[hardware]

# Function to calculate average latency
def calculate_average_latency(frontend_config, cache_config, backend_config, cache_hit_rate):
    frontend_latency = frontend_config.latency + NETWORK_LATENCY + PROCESSING_LATENCY
    cache_latency = cache_config.latency + NETWORK_LATENCY + PROCESSING_LATENCY
    backend_latency = backend_config.latency + NETWORK_LATENCY + PROCESSING_LATENCY
    
    # AMAT formula with network and processing latency included
    amat = cache_hit_rate * cache_latency + (1 - cache_hit_rate) * (cache_latency + backend_latency)
    avg_latency = frontend_latency + amat
    
    return avg_latency

# Function to calculate total throughput of a tier
def calculate_total_throughput(config, num_servers):
    return config.throughput * num_servers

# Function to calculate peak throughput of the system
def calculate_peak_throughput(frontend_total_throughput, cache_total_throughput, backend_total_throughput):
    return min(frontend_total_throughput, cache_total_throughput, backend_total_throughput)

# Function to calculate the number of servers needed to meet the SLO
def calculate_servers_needed(throughput, config_throughput):
    return np.ceil(throughput / config_throughput)

def calculate_individual_carbon_costs(frontend_config, cache_config, backend_config, num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate, simulation_years):
    # Calculate total number of seconds in the simulation period
    seconds_in_a_year = 365 * 24 * 60 * 60  # 365 days, 24 hours/day, 60 minutes/hour, 60 seconds/minute
    total_seconds = simulation_years * seconds_in_a_year

    # Embodied carbon cost proportional to the size of each server
    frontend_embodied_carbon_cost = num_frontend_servers * frontend_config.carbon_cost * frontend_config.size
    cache_embodied_carbon_cost = num_cache_servers * cache_config.carbon_cost * cache_config.size
    backend_embodied_carbon_cost = num_backend_servers * backend_config.carbon_cost * backend_config.size

    embodied_carbon_costs = []
    embodied_carbon_costs.append(frontend_embodied_carbon_cost)
    embodied_carbon_costs.append(cache_embodied_carbon_cost)
    embodied_carbon_costs.append(backend_embodied_carbon_cost)

    # Active cost (based on read/write operations over the total seconds of operation)
    frontend_active_cost = (
        num_frontend_servers * frontend_config.active_cost['read'] * READ_RATIO +
        num_frontend_servers * frontend_config.active_cost['write'] * WRITE_RATIO
    ) * frontend_config.size * total_seconds * (LOAD_CAPACITY)

    cache_active_cost = (
        num_cache_servers * cache_config.active_cost['read'] * READ_RATIO +
        num_cache_servers * cache_config.active_cost['write'] * WRITE_RATIO
    ) * cache_config.size * total_seconds * (LOAD_CAPACITY)

    backend_active_cost = (
        num_backend_servers * backend_config.active_cost['read'] * READ_RATIO +
        num_backend_servers * backend_config.active_cost['write'] * WRITE_RATIO
    ) * backend_config.size * total_seconds * (LOAD_CAPACITY) * (1 - cache_hit_rate)

    active_costs = []
    active_costs.append(frontend_active_cost)
    active_costs.append(cache_active_cost)
    active_costs.append(backend_active_cost)

    # Idle cost (based on idle time over the simulation period)
    frontend_idle_cost = num_frontend_servers * frontend_config.idle_cost * frontend_config.size * (1 - LOAD_CAPACITY) * total_seconds
    cache_idle_cost = num_cache_servers * cache_config.idle_cost * cache_config.size * (1 - LOAD_CAPACITY) * total_seconds
    backend_idle_cost = num_backend_servers * backend_config.idle_cost * backend_config.size * (1 - LOAD_CAPACITY) * total_seconds * (1 - cache_hit_rate)

    idle_costs = []
    idle_costs.append(frontend_idle_cost)
    idle_costs.append(cache_idle_cost)
    idle_costs.append(backend_idle_cost)

    # Replacement cost (based on the replacement of hardware over the simulation period)
    frontend_replacement_cost = 0
    cache_replacement_cost = 0
    backend_replacement_cost = 0

    if simulation_years > frontend_config.lifespan_years:
        num_replacements = simulation_years // frontend_config.lifespan_years
        frontend_replacement_cost = num_replacements * num_frontend_servers * frontend_config.carbon_cost * frontend_config.size

    if simulation_years > cache_config.lifespan_years:
        num_replacements = simulation_years // cache_config.lifespan_years
        cache_replacement_cost = num_replacements * num_cache_servers * cache_config.carbon_cost * cache_config.size

    if simulation_years > backend_config.lifespan_years:
        num_replacements = simulation_years // backend_config.lifespan_years
        backend_replacement_cost = num_replacements * num_backend_servers * backend_config.carbon_cost * backend_config.size

    replacement_costs = []
    replacement_costs.append(frontend_replacement_cost)
    replacement_costs.append(cache_replacement_cost)
    replacement_costs.append(backend_replacement_cost)

    return embodied_carbon_costs, active_costs, idle_costs, replacement_costs

# Function to calculate the cache hit rate based on cache size and number of videos
def calculate_cache_hit_rate(cache_config, num_cache_servers):
    total_cache_size = cache_config.size * num_cache_servers  # Total cache size in GB
    hit_rate = total_cache_size / NUM_VIDEOS
    return min(1, hit_rate)

def main():
    parser = argparse.ArgumentParser(description='Three-tier video streaming service configuration')
    parser.add_argument('--slo_latency', type=int, default=100, help='End-to-end SLO latency (in milliseconds)')
    parser.add_argument('--slo_throughput', type=int, default=1000, help='End-to-end SLO throughput (in requests per second)')
    parser.add_argument('--frontend', type=str, choices=['low_performance', 'high_performance'], default='low_performance', help='Hardware for frontend')
    parser.add_argument('--cache', type=str, choices=['DRAM', 'flash'], default='DRAM', help='Hardware for cache')
    parser.add_argument('--backend', type=str, choices=['SSD', 'HDD', 'tape', 'glass'], default='SSD', help='Hardware for backend')
    parser.add_argument('--simulation_years', type=int, default=10, help='Number of years to simulate')
    parser.add_argument('--output', type=str, default='results.csv', help='Output CSV file for results')
    args = parser.parse_args()

    # Create server configurations
    frontend_config = ServerConfig(args.frontend, FrontendParams)
    cache_config = ServerConfig(args.cache, CacheParams)
    backend_config = ServerConfig(args.backend, BackendParams)

    # Calculate the number of servers needed in each tier to meet the SLO
    num_frontend_servers = calculate_servers_needed(args.slo_throughput, frontend_config.throughput)
    num_cache_servers = calculate_servers_needed(args.slo_throughput, cache_config.throughput)
    num_backend_servers = calculate_servers_needed(args.slo_throughput, backend_config.throughput)

    # Calculate the cache hit rate based on the number of cache servers
    cache_hit_rate = calculate_cache_hit_rate(cache_config, num_cache_servers)

    # Calculate total throughput of each tier
    frontend_total_throughput = calculate_total_throughput(frontend_config, num_frontend_servers)
    cache_total_throughput = calculate_total_throughput(cache_config, num_cache_servers)
    backend_total_throughput = calculate_total_throughput(backend_config, num_backend_servers)

    # Calculate peak throughput of the system
    peak_throughput = calculate_peak_throughput(frontend_total_throughput, cache_total_throughput, backend_total_throughput)

    # Calculate average latency using the updated formula
    avg_latency = calculate_average_latency(frontend_config, cache_config, backend_config, cache_hit_rate)

    # Calculate individual carbon costs
    embodied_carbon_costs, active_costs, idle_costs, replacement_costs = calculate_individual_carbon_costs(
        frontend_config, cache_config, backend_config, num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate, args.simulation_years
    )

    # Calculate cumulative carbon cost as the sum of all individual costs
    embodied_carbon_cost = sum(embodied_carbon_costs)
    active_cost = sum(active_costs)
    idle_cost = sum(idle_costs)
    replacement_cost = sum(replacement_costs)
    
    frontend_cumulative_carbon_cost = embodied_carbon_costs[0] + active_costs[0] + idle_costs[0] + replacement_costs[0]
    cache_cumulative_carbon_cost = embodied_carbon_costs[1] + active_costs[1] + idle_costs[1] + replacement_costs[1]
    backend_cumulative_carbon_cost = embodied_carbon_costs[2] + active_costs[2] + idle_costs[2] + replacement_costs[2]

    cumulative_carbon_cost = frontend_cumulative_carbon_cost + cache_cumulative_carbon_cost + backend_cumulative_carbon_cost

    # Print the results
    print(f'Average Latency: {avg_latency:.2f} ms')
    print(f'Peak Throughput: {peak_throughput:.2f} requests/second')
    print(f'Embodied Carbon Cost: {embodied_carbon_cost:.2f} kg CO2e')
    print(f'Active Carbon Cost: {active_cost:.2f} kg CO2e')
    print(f'Idle Carbon Cost: {idle_cost:.2f} kg CO2e')
    print(f'Replacement Carbon Cost: {replacement_cost:.2f} kg CO2e')
    print(f'Cumulative Carbon Cost over {args.simulation_years} years: {cumulative_carbon_cost:.2f} kg CO2e')
    print(f'Number of Frontend Servers: {num_frontend_servers:g}')
    print(f'Number of Cache Servers: {num_cache_servers:g}')
    print(f'Number of Backend Servers: {num_backend_servers:g}')
    print(f'Cache Hit Rate: {cache_hit_rate:.2f}')

    # Update the CSV writer to include size information
    file_exists = os.path.isfile(args.output)
    with open(args.output, 'a') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                'SLO Latency', 'SLO Throughput', 'Frontend', 'Cache', 'Backend',
                'Average Latency', 'Peak Throughput', 'Cumulative Carbon Cost',
                'Frontend Servers', 'Cache Servers', 'Backend Servers', 'Cache Hit Rate',
                'Embodied Cost', 'Active Cost', 'Idle Cost', 'Replacement Cost',
                'Frontend Size (GB)', 'Cache Size (GB)', 'Backend Size (GB)', 'Total Size (GB)', 'Simulation Years'
            ])
        total_storage_capacity = (
            num_frontend_servers * frontend_config.size +
            num_cache_servers * cache_config.size +
            num_backend_servers * backend_config.size
        )
        writer.writerow([
            args.slo_latency, args.slo_throughput, args.frontend, args.cache, args.backend,
            avg_latency, peak_throughput, cumulative_carbon_cost,
            num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate,
            embodied_carbon_cost, active_cost, idle_cost, replacement_cost,
            num_frontend_servers * frontend_config.size,
            num_cache_servers * cache_config.size,
            num_backend_servers * backend_config.size,
            total_storage_capacity,
            args.simulation_years
        ])

if __name__ == '__main__':
    main()