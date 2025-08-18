import xml.etree.ElementTree as ET

class Station:
    def __init__(self, name, service_policy, transmission_capacity, x=None, y=None):
        self.name = name
        self.service_policy = service_policy
        self.transmission_capacity = transmission_capacity
        self.x = x  # Optional: For visualization
        self.y = y

class Switch:
    def __init__(self, name, service_policy, switching_technique, tech_latency, transmission_capacity, x=None, y=None):
        self.name = name
        self.service_policy = service_policy
        self.switching_technique = switching_technique
        self.tech_latency = tech_latency
        self.transmission_capacity = transmission_capacity
        self.x = x
        self.y = y

class Edge:
    def __init__(self, name, from_node, from_port, to_node, to_port, transmission_capacity):
        self.name = name
        self.from_node = from_node
        self.from_port = from_port
        self.to_node = to_node
        self.to_port = to_port
        self.transmission_capacity = transmission_capacity
        self.direct_load = 0.0   
        self.reverse_load = 0.0   
        
class Target:
    def __init__(self, name, mode, path):
        self.name = name
        self.mode = mode
        self.path = path  # List of node names

class Flow:
    def __init__(self, name, source, max_payload, min_payload, period, deadline, jitter, priority, targets):
        self.name = name
        self.source = source
        self.max_payload = max_payload
        self.min_payload = min_payload
        self.period = period
        self.deadline = deadline
        self.jitter = jitter
        self.priority = priority
        self.targets = targets  # List of Target objects

def parse_afdx_xml(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    stations, switches, edges, flows = {}, {}, {}, []

    for elem in root:
        if elem.tag == "station":
            stations[elem.attrib['name']] = Station(
                name=elem.attrib['name'],
                service_policy=elem.attrib.get('service-policy', None),
                transmission_capacity=elem.attrib.get('transmission-capacity', None),
                x=float(elem.attrib.get('x', 0)),
                y=float(elem.attrib.get('y', 0))
            )

        elif elem.tag == "switch":
            switches[elem.attrib['name']] = Switch(
                name=elem.attrib['name'],
                service_policy=elem.attrib.get('service-policy', None),
                switching_technique=elem.attrib.get('switching-technique', None),
                tech_latency=elem.attrib.get('tech-latency', '0'),
                transmission_capacity=elem.attrib.get('transmission-capacity', None),
                x=float(elem.attrib.get('x', 0)),
                y=float(elem.attrib.get('y', 0))
            )

        elif elem.tag == "link":
            edges[elem.attrib['name']] = Edge(
                name=elem.attrib['name'],
                from_node=elem.attrib['from'],
                from_port=elem.attrib.get('fromPort', None),
                to_node=elem.attrib['to'],
                to_port=elem.attrib.get('toPort', None),
                transmission_capacity=elem.attrib.get('transmission-capacity', None)
            )

        elif elem.tag == "flow":
            targets = []
            for t in elem.findall('target'):
                path = [p.attrib['node'] for p in t.findall('path')]
                targets.append(Target(
                    name=t.attrib['name'],
                    mode=t.attrib.get('mode', 'MAIN'),
                    path=path
                ))
            flows.append(Flow(
                name=elem.attrib['name'],
                source=elem.attrib['source'],
                max_payload=int(elem.attrib['max-payload']),
                min_payload=int(elem.attrib.get('min-payload', elem.attrib['max-payload'])),
                period=int(elem.attrib['period']),
                deadline=int(elem.attrib.get('deadline', elem.attrib['period'])),
                jitter=int(elem.attrib.get('jitter', 0)),
                priority=elem.attrib.get('priority', 'Low'),
                targets=targets
            ))

    return stations, switches, edges, flows

# Usage Example (uncomment to test):
# stations, switches, edges, flows = parse_afdx_xml("AFDX.xml")
# print(f"Stations: {list(stations.keys())}")
# print(f"Switches: {list(switches.keys())}")
# print(f"Edges: {list(edges.keys())}")
# print(f"Flows: {[f.name for f in flows]}")


# LINK LOAD CALCULATIONS

def link_load_calc():

    counted_on_edge = set()  # Track (flow_name, edge_name) pairs already counted
    global_overhead = 67
    for flow in flows:
        total_bytes = flow.max_payload + global_overhead
        rate_bps = (total_bytes * 8) / (flow.period / 1000.0)
        for target in flow.targets:
            path = [flow.source] + target.path
            for i in range(len(path) - 1):
                src = path[i]
                dst = path[i + 1]
                for edge in edges.values():
                    if edge.from_node == src and edge.to_node == dst:
                        key = (flow.name, edge.name, 'direct')
                        if key in counted_on_edge:
                            continue
                        edge.direct_load += rate_bps
                        counted_on_edge.add(key)
                    elif edge.from_node == dst and edge.to_node == src:
                        key = (flow.name, edge.name, 'reverse')
                        if key in counted_on_edge:
                            continue
                        edge.reverse_load += rate_bps
                        counted_on_edge.add(key)


def print_link_load():
    for edge in edges.values():
        try:
            # Get capacity in bps (try to handle both "100Mbps" and numeric values)
            if "Mbps" in edge.transmission_capacity:
                cap_bps = float(edge.transmission_capacity.replace("Mbps", "")) * 1_000_000
            else:
                cap_bps = float(edge.transmission_capacity)
        except:
            cap_bps = 100_000_000  # Default: 100 Mbps

        print(f"Edge {edge.name}:")
        print(f"  Direct load:  {edge.direct_load:.0f} bps  ({100 * edge.direct_load / cap_bps:.4f}% of capacity)")
        print(f"  Reverse load: {edge.reverse_load:.0f} bps  ({100 * edge.reverse_load / cap_bps:.4f}% of capacity)")
        print("-" * 50)

def get_all_flows_on_edge_at_any_hop(flows, edges):
    """
    Returns a dictionary mapping each edge (from_node, to_node)
    to a set of (flow_name, target_name) pairs that ever use that edge.
    """
    edge_to_flows = {}
    for flow in flows:
        for target in flow.targets:
            path = [flow.source] + target.path
            for i in range(len(path) - 1):
                src, dst = path[i], path[i + 1]
                edge = (src, dst)
                if edge not in edge_to_flows:
                    edge_to_flows[edge] = set()
                edge_to_flows[edge].add((flow.name, target.name))
    return edge_to_flows

def get_flows_arrived_at_edge_this_hop(flows, hop, edge):
    """
    Returns a list of (flow, target, key, path, arrival_hop) for all flows
    that reach the given edge at the current hop.
    """
    arrived = []
    for flow in flows:
        for target in flow.targets:
            path = [flow.source] + target.path
            if hop < len(path) - 1 and (path[hop], path[hop+1]) == edge:
                arrived.append((flow, target, (flow.name, target.name), path, hop))
    return arrived

# def compute_burst_sum(burst_map, arrivals, path_map, hop):
#     # Group by (flow, subpath up to this hop)
#     group_map = {}
#     for flow, target, key, path, h in arrivals:
#         subpath = tuple(path[:hop+1])  # subpath including this node
#         group_key = (key[0], subpath)
#         if group_key not in group_map:
#             group_map[group_key] = []
#         group_map[group_key].append((key, h))
#     burst_sum = 0
#     for group in group_map.values():
#         # Only count the burst for the first (flow, subpath) in each group
#         key, h = group[0]
#         burst_sum += burst_map[key][h]
#     return burst_sum

def compute_burst_sum(burst_map, arrivals, path_map, hop):
    group_map = {}
    for flow, target, key, path, h in arrivals:
        subpath = tuple(path[:hop+1])
        group_key = (key[0], subpath)
        if group_key not in group_map:
            group_map[group_key] = []
        group_map[group_key].append((key, h))
    burst_sum = 0
    for group in group_map.values():
        key, h = group[0]
        if h < len(burst_map[key]):
            burst_sum += burst_map[key][h]
        else:
            # Debug info
            print(f"[Warning] Burst out of range for {key} at hop {h}, path length: {len(burst_map[key])}")
            burst_sum += burst_map[key][-1] if burst_map[key] else 0
    return burst_sum




def get_edge_capacity(edges, edge):
    """Returns the capacity in bps for the given edge."""
    for e in edges.values():
        if (e.from_node, e.to_node) == edge:
            if "Mbps" in str(e.transmission_capacity):
                return float(e.transmission_capacity.replace("Mbps", "")) * 1_000_000
            else:
                return float(e.transmission_capacity)
    return 100_000_000  # Default


def compute_fifo_delay_modular(flows, edges, global_overhead):
    edge_to_flows = get_all_flows_on_edge_at_any_hop(flows, edges)
    burst_map = {}    # (flow_name, target_name): list of bursts per hop
    rate_map = {}     # (flow_name, target_name): rate (bps)
    delay_map = {}    # (flow_name, target_name): list of delays per hop
    path_map = {}

    # Setup burst, rate, path
    for flow in flows:
        for target in flow.targets:
            key = (flow.name, target.name)
            payload_bytes = flow.max_payload + global_overhead
            sigma = payload_bytes * 8
            period_sec = flow.period / 1000.0
            rho = sigma / period_sec
            path = [flow.source] + target.path
            burst_map[key] = [sigma]
            rate_map[key] = rho
            delay_map[key] = [0] * (len(path) - 1)
            path_map[key] = path

    max_hops = max(len(path) for path in path_map.values()) - 1
    edge_arrivals = {edge: set() for edge in edge_to_flows}
    pending_arrivals = {edge: set() for edge in edge_to_flows}
    pending_arrivals_list = {edge: [] for edge in edge_to_flows}

    for hop in range(max_hops):
        for edge, total_flows in edge_to_flows.items():
            arrivals = get_flows_arrived_at_edge_this_hop(flows, hop, edge)
            arrivals = [a for a in arrivals if a[4] < len(burst_map[a[2]])]
            for arrival in arrivals:
                _, _, key, _, _ = arrival
                pending_arrivals_list[edge].append(arrival)
            # --- Process in batches ---
            # Count unique (flow, target) in current pending list
            batch_keys = set(a[2] for a in pending_arrivals_list[edge])
            while batch_keys == total_flows and total_flows:
                # Extract the first occurrence of each (flow, target)
                this_batch = []
                keys_seen = set()
                for a in pending_arrivals_list[edge]:
                    if a[2] not in keys_seen:
                        this_batch.append(a)
                        keys_seen.add(a[2])
                    if keys_seen == total_flows:
                        break
                # Compute burst and delay for this batch
                burst_sum = compute_burst_sum(burst_map, this_batch, path_map, hop)
                capacity = get_edge_capacity(edges, edge)
                delay = burst_sum / capacity
                for flow, target, key, path, hop_idx in this_batch:
                    delay_map[key][hop_idx] = delay * 1000  # ms
                    old_burst = burst_map[key][hop_idx]
                    new_burst = old_burst + rate_map[key] * delay
                    if len(burst_map[key]) == hop_idx + 1:
                        burst_map[key].append(new_burst)
                    else:
                        burst_map[key][hop_idx + 1] = new_burst
                # Remove processed arrivals from pending list
                for a in this_batch:
                    pending_arrivals_list[edge].remove(a)
                # Update batch_keys for next batch in the same hop
                batch_keys = set(a[2] for a in pending_arrivals_list[edge])



    # Sum delays for each (flow, target)
    results = {}
    for key, delays in delay_map.items():
        results[key] = sum(delays)
    return results


# burst_table.clear()
stations, switches, edges, flows = parse_afdx_xml("data/check_3.xml")
global_overhead = 67
delays = compute_fifo_delay_modular(flows, edges, global_overhead)
for (flow_name, target_name), total_delay in delays.items():
    print(f"Flow {flow_name} to {target_name}: End-to-end delay = {total_delay:.4f} ms")
