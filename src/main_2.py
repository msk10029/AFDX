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

burst_table = {}  # (flow_name, target_name, hop_index) -> sigma

def initial_burst(flow):
    return (flow.max_payload + global_overhead) * 8

def rate(flow):
    sigma = initial_burst(flow)
    period_sec = flow.period / 1000.0
    return sigma / period_sec

def current_burst(flow, target, hop_index):
    key = (flow.name, target.name, hop_index)
    if hop_index == 0:
        return initial_burst(flow)
    return burst_table.get(key, initial_burst(flow))  # fallback to initial burst if not yet set

def update_current_burst(flow, target, hop_index, sigma):
    key = (flow.name, target.name, hop_index)
    burst_table[key] = sigma

def edge_capacity(src, dst):
    for e in edges.values():
        if e.from_node == src and e.to_node == dst:
            # Adjust if your edge data structure differs!
            if hasattr(e, "transmission_capacity"):
                return float(str(e.transmission_capacity).replace("Mbps", "")) * 1_000_000
            else:
                return 100_000_000
    return 100_000_000  # default 100Mbps

def compute_end_to_end_delay():
    burst_table.clear()
    for flow in flows:
        target_path = []
        for target in flow.targets:
            sigma = initial_burst(flow)
            rho = rate(flow)
            path = [flow.source] + target.path
            target_path.append(path)                    # 




            total_delay = 0
            for i in range(len(path) - 1):
                src, dst = path[i], path[i + 1]
                # Build shared list: all (flow2, target2) using this edge at this hop
                shared = []
                for flow2 in flows:
                    for target2 in flow2.targets:
                        path2 = [flow2.source] + target2.path
                        if i < len(path2) - 1 and path2[i] == src and path2[i + 1] == dst:
                            shared.append((flow2, target2))
                # Burst sum logic
                if i == 0:
                    unique_flows = set()
                    burst_sum = 0
                    for flow2, target2 in shared:
                        flow_id = flow2.name
                        if flow_id not in unique_flows:
                            burst_sum += current_burst(flow2, target2, i)
                            unique_flows.add(flow_id)
                else:
                    burst_sum = 0
                    for flow2, target2 in shared:
                        burst_sum += current_burst(flow2, target2, i)
                        print(burst_sum)
                # Compute and update delays and bursts
                D_hop = burst_sum / edge_capacity(src, dst)
                total_delay += D_hop
                sigma = current_burst(flow, target, i) + rho * D_hop  # this is crucial
                update_current_burst(flow, target, i + 1, sigma)
            print(f"Flow {flow.name} to {target.name}: {total_delay * 1000:.3f} ms")


burst_table.clear()
stations, switches, edges, flows = parse_afdx_xml("data/STAR_3.xml")
global_overhead = 67
compute_end_to_end_delay()