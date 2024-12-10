import argparse
import csv
import json
import numpy as np
import os

# Default configuration paths
DEFAULT_SYSTEM_CONFIG = os.path.join("configs", "system", "system.json")
DEFAULT_FRONTEND_CONFIG = os.path.join("configs", "frontend", "low_performance", "Samsung_PM9A3.json")
DEFAULT_CACHE_CONFIG = os.path.join("configs", "cache", "DRAM", "Samsung_PM9A3.json")
DEFAULT_BACKEND_CONFIG = os.path.join("configs", "backend", "SSD", "Samsung_PM9A3.json")

def load_config(file_path, default_config):
    """
    Load a JSON configuration file or fallback to a default configuration.
    """
    if file_path:
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            print(f"Error: Configuration file {file_path} not found.")
            exit(1)
        except json.JSONDecodeError:
            print(f"Error: Configuration file {file_path} is not a valid JSON file.")
            exit(1)
    else:
        # Load the default configuration if no path is provided
        print(f"No configuration file provided, using default: {default_config}")
        with open(default_config, 'r') as file:
            return json.load(file)

# Struct to hold system configuration
class SystemConfig:
    def __init__(self, params):
        self.latency = params['latency'] # in ms
        self.storage_capacity = params['storage_capacity'] # in GB
        self.active_idle_ratio = params['active_idle_ratio'] # percentage of time in active state
        self.read_write_ratio = params['read_write_ratio'] # percentage of operations that are reads
        self.carbon_intensity = params['carbon_intensity'] # in kg CO2e per Ws

# Struct to hold server configuration
class ServerConfig:
    def __init__(self, params):
        self.name = params['name'] # name of the server configuration
        self.latency = params['latency'] # in ms
        self.throughput = params['throughput'] # in requests per second
        self.embodied_cost = params['embodied_cost'] # in kg CO2e
        self.power_consumption = params['power_consumption'] # in W
        self.lifespan = params['lifespan'] # in years
        self.capacity = params['capacity'] # in GB

# Function to calculate average latency
def calculate_average_latency(system_config, frontend_config, cache_config, backend_config, cache_hit_rate):
    frontend_latency = frontend_config.latency + system_config.latency['network'] + system_config.latency['processing']
    cache_latency = cache_config.latency + system_config.latency['network'] + system_config.latency['processing']
    backend_latency = backend_config.latency + system_config.latency['network'] + system_config.latency['processing']
    
    # AMAT (Average Memory Access Time) = Hit time + Miss rate * Miss penalty
    cache_miss_rate = 1 - cache_hit_rate
    avg_latency = frontend_latency + cache_latency + cache_miss_rate * backend_latency
    
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

def calculate_individual_carbon_costs(system_config, frontend_config, cache_config, backend_config, num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate, simulation_years):
    # Calculate total number of seconds in the simulation period
    seconds_in_a_year = 365 * 24 * 60 * 60  # 365 days, 24 hours/day, 60 minutes/hour, 60 seconds/minute
    total_seconds = simulation_years * seconds_in_a_year

    # Embodied carbon cost proportional to the capacity of each server
    frontend_embodied_carbon_cost = num_frontend_servers * frontend_config.embodied_cost['initial']
    cache_embodied_carbon_cost = num_cache_servers * cache_config.embodied_cost['initial']
    backend_embodied_carbon_cost = num_backend_servers * backend_config.embodied_cost['initial']

    embodied_carbon_costs = []
    embodied_carbon_costs.append(frontend_embodied_carbon_cost)
    embodied_carbon_costs.append(cache_embodied_carbon_cost)
    embodied_carbon_costs.append(backend_embodied_carbon_cost)

    # Active cost (based on read/write operations over the total seconds of operation)
    frontend_active_cost = (
        num_frontend_servers * frontend_config.power_consumption['active']['read'] * system_config.carbon_intensity * system_config.read_write_ratio +
        num_frontend_servers * frontend_config.power_consumption['active']['write'] * system_config.carbon_intensity * (1 - system_config.read_write_ratio)
    ) * total_seconds * system_config.active_idle_ratio

    cache_active_cost = (
        num_cache_servers * cache_config.power_consumption['active']['read'] * system_config.carbon_intensity * system_config.read_write_ratio +
        num_cache_servers * cache_config.power_consumption['active']['write'] * system_config.carbon_intensity * (1 - system_config.read_write_ratio)
    ) * total_seconds * system_config.active_idle_ratio

    backend_active_cost = (
        num_backend_servers * backend_config.power_consumption['active']['read'] * system_config.carbon_intensity * system_config.read_write_ratio +
        num_backend_servers * backend_config.power_consumption['active']['write'] * system_config.carbon_intensity * (1 - system_config.read_write_ratio)
    ) * total_seconds * system_config.active_idle_ratio * (1 - cache_hit_rate)

    active_costs = []
    active_costs.append(frontend_active_cost)
    active_costs.append(cache_active_cost)
    active_costs.append(backend_active_cost)

    # Idle cost (based on idle time over the simulation period)
    frontend_idle_cost = num_frontend_servers * frontend_config.power_consumption['idle'] * system_config.carbon_intensity * (1 - system_config.active_idle_ratio) * total_seconds
    cache_idle_cost = num_cache_servers * cache_config.power_consumption['idle'] * system_config.carbon_intensity * (1 - system_config.active_idle_ratio) * total_seconds
    backend_idle_cost = num_backend_servers * backend_config.power_consumption['idle'] * system_config.carbon_intensity * (1 - system_config.active_idle_ratio) * total_seconds * (1 - cache_hit_rate)

    idle_costs = []
    idle_costs.append(frontend_idle_cost)
    idle_costs.append(cache_idle_cost)
    idle_costs.append(backend_idle_cost)

    # Replacement cost (based on the replacement of hardware over the simulation period)
    frontend_replacement_cost = 0
    cache_replacement_cost = 0
    backend_replacement_cost = 0

    if simulation_years > frontend_config.lifespan:
        num_replacements = simulation_years // frontend_config.lifespan
        frontend_replacement_cost = num_replacements * num_frontend_servers * frontend_config.embodied_cost['initial']

    if simulation_years > cache_config.lifespan:
        num_replacements = simulation_years // cache_config.lifespan
        cache_replacement_cost = num_replacements * num_cache_servers * cache_config.embodied_cost['initial']

    if simulation_years > backend_config.lifespan:
        num_replacements = simulation_years // backend_config.lifespan
        backend_replacement_cost = num_replacements * num_backend_servers * backend_config.embodied_cost['initial']

    replacement_costs = []
    replacement_costs.append(frontend_replacement_cost)
    replacement_costs.append(cache_replacement_cost)
    replacement_costs.append(backend_replacement_cost)

    return embodied_carbon_costs, active_costs, idle_costs, replacement_costs

# Function to calculate the cache hit rate based on cache capacity and number of videos
def calculate_cache_hit_rate(system_config, cache_config, num_cache_servers):
    total_cache_capacity = cache_config.capacity * num_cache_servers  # Total cache capacity in GB
    hit_rate = total_cache_capacity / system_config.storage_capacity
    return min(1, hit_rate)

def main():
    # Argument parser setup
    parser = argparse.ArgumentParser(description='CarbonStream Configuration')
    parser.add_argument('--slo_latency', type=int, default=100, help='End-to-end SLO latency (in milliseconds)')
    parser.add_argument('--slo_throughput', type=int, default=1000, help='End-to-end SLO throughput (in requests per second)')
    parser.add_argument('--system', type=str, default='../config/system/system.json', help='Path to the system configuration file')
    parser.add_argument('--frontend', type=str, default='../config/frontend/low_performance.json', help='Path to the frontend configuration file')
    parser.add_argument('--cache', type=str, default='../config/cache/flash.json', help='Path to the cache configuration file')
    parser.add_argument('--backend', type=str, default='../config/backend/SSD/Samsung_PM9A3.json', help='Path to the backend configuration file')
    parser.add_argument('--simulation_years', type=int, default=10, help='Number of years to simulate')
    parser.add_argument('--output', type=str, default='results.csv', help='Output CSV file for results')
    args = parser.parse_args()

    # Load configurations for each tier
    system_json = load_config(args.system, DEFAULT_SYSTEM_CONFIG)
    frontend_json = load_config(args.frontend, DEFAULT_FRONTEND_CONFIG)
    cache_json = load_config(args.cache, DEFAULT_CACHE_CONFIG)
    backend_json = load_config(args.backend, DEFAULT_BACKEND_CONFIG)

    # Print loaded configurations
    print(f"Loaded System Config: {system_json}")
    print(f"Loaded Frontend Config: {frontend_json}")
    print(f"Loaded Cache Config: {cache_json}")
    print(f"Loaded Backend Config: {backend_json}")

    # Create system configuration
    system_config = SystemConfig(system_json)

    # Create server configurations
    frontend_config = ServerConfig(frontend_json)
    cache_config = ServerConfig(cache_json)
    backend_config = ServerConfig(backend_json)

    # Calculate the number of servers needed in each tier to meet the SLO
    num_frontend_servers = calculate_servers_needed(args.slo_throughput, frontend_config.throughput)
    num_cache_servers = calculate_servers_needed(args.slo_throughput, cache_config.throughput)
    num_backend_servers = calculate_servers_needed(args.slo_throughput, backend_config.throughput)

    # Calculate the cache hit rate based on the number of cache servers
    cache_hit_rate = calculate_cache_hit_rate(system_config, cache_config, num_cache_servers)

    # Calculate total throughput of each tier
    frontend_total_throughput = calculate_total_throughput(frontend_config, num_frontend_servers)
    cache_total_throughput = calculate_total_throughput(cache_config, num_cache_servers)
    backend_total_throughput = calculate_total_throughput(backend_config, num_backend_servers)

    # Calculate peak throughput of the system
    peak_throughput = calculate_peak_throughput(frontend_total_throughput, cache_total_throughput, backend_total_throughput)

    # Calculate average latency using the updated formula
    avg_latency = calculate_average_latency(system_config, frontend_config, cache_config, backend_config, cache_hit_rate)

    # Calculate individual carbon costs
    embodied_carbon_costs, active_costs, idle_costs, replacement_costs = calculate_individual_carbon_costs(
        system_config, frontend_config, cache_config, backend_config, num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate, args.simulation_years
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

    # Update the CSV writer to include capacity information
    file_exists = os.path.isfile(args.output)
    with open(args.output, 'a') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow([
                'SLO Latency', 'SLO Throughput', 'Frontend', 'Cache', 'Backend',
                'Average Latency', 'Peak Throughput', 'Cumulative Carbon Cost',
                'Frontend Servers', 'Cache Servers', 'Backend Servers', 'Cache Hit Rate',
                'Embodied Cost', 'Active Cost', 'Idle Cost', 'Replacement Cost',
                'Frontend Capacity (GB)', 'Cache Capacity (GB)', 'Backend Capacity (GB)', 'Total Capacity (GB)', 'Simulation Years'
            ])
        total_storage_capacity = (
            num_frontend_servers * frontend_config.capacity +
            num_cache_servers * cache_config.capacity +
            num_backend_servers * backend_config.capacity
        )
        writer.writerow([
            args.slo_latency, args.slo_throughput, frontend_config.name, cache_config.name, backend_config.name,
            avg_latency, peak_throughput, cumulative_carbon_cost,
            num_frontend_servers, num_cache_servers, num_backend_servers, cache_hit_rate,
            embodied_carbon_cost, active_cost, idle_cost, replacement_cost,
            num_frontend_servers * frontend_config.capacity,
            num_cache_servers * cache_config.capacity,
            num_backend_servers * backend_config.capacity,
            total_storage_capacity,
            args.simulation_years
        ])

if __name__ == '__main__':
    main()