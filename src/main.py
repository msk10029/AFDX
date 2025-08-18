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


def compute_edge_total_rates(flows, edges, global_overhead):
    edge_total_rate = {edge.name: 0.0 for edge in edges.values()}
    for flow in flows:
        flow_bytes = flow.max_payload + global_overhead
        flow_bits = flow_bytes * 8
        flow_period_sec = flow.period / 1000.0
        flow_rate = flow_bits / flow_period_sec  # bps
        counted_edges = set()
        for target in flow.targets:
            path = [flow.source] + target.path
            for i in range(len(path) - 1):
                src = path[i]
                dst = path[i + 1]
                for edge in edges.values():
                    if ((edge.from_node == src and edge.to_node == dst) or 
                        (edge.from_node == dst and edge.to_node == src)):
                        key = (flow.name, edge.name)
                        if key not in counted_edges:
                            edge_total_rate[edge.name] += flow_rate
                            counted_edges.add(key)
    return edge_total_rate


def compute_end_to_end_delay_fifo_strict_snapshot(flows, edges, global_overhead):
    """
    Computes end-to-end delay for all flows using strict FIFO burst sum at each edge,
    for general topologies. At each hop, all flows using an edge at that step sum
    their bursts *before* any are updated, ensuring symmetry.
    Returns: {(flow_name, target_name): total_delay_ms}
    """
    # Prepare burst and rate for all flows (by flow+target for full path uniqueness)
    flow_info = {}
    for flow in flows:
        for target in flow.targets:
            payload_bytes = flow.max_payload + global_overhead
            sigma = payload_bytes * 8  # bits
            period_sec = flow.period / 1000.0  # ms to s
            rho = sigma / period_sec  # bits/sec
            key = (flow.name, id(flow), target.name)
            flow_info[key] = {
                'sigma': sigma,
                'rho': rho,
                'path': [flow.source] + target.path,
            }

    # Find the max hops (so we can iterate by hop)
    max_hops = max(len(info['path']) for info in flow_info.values()) - 1

    # Track per-hop burst for each (flow, target)
    flow_bursts_per_hop = {key: [info['sigma']] for key, info in flow_info.items()}
    delays = {key: [] for key in flow_info.keys()}

    # Iterate by hop index
    for hop_idx in range(max_hops):
        # 1. Snapshot bursts for all flows at this hop
        bursts_this_hop = {}
        for key, info in flow_info.items():
            path = info['path']
            if hop_idx >= len(path) - 1:
                continue
            bursts_this_hop[key] = flow_bursts_per_hop[key][hop_idx]

        # 2. Calculate all delays for this hop using the snapshot
        delays_this_hop = {}
        for key, info in flow_info.items():
            path = info['path']
            if hop_idx >= len(path) - 1:
                continue
            src = path[hop_idx]
            dst = path[hop_idx+1]
            # Find the matching edge
            edge = None
            for e in edges.values():
                if e.from_node == src and e.to_node == dst:
                    edge = e
                    break
            if edge is None:
                continue
            # All flows using this edge at this hop
            sigma_sum = 0
            for k2, info2 in flow_info.items():
                p2 = info2['path']
                if hop_idx >= len(p2) - 1:
                    continue
                s2 = p2[hop_idx]
                d2 = p2[hop_idx+1]
                if s2 == src and d2 == dst:
                    sigma_sum += bursts_this_hop.get(k2, 0)
            # Edge capacity
            try:
                if "Mbps" in str(edge.transmission_capacity):
                    C = float(edge.transmission_capacity.replace("Mbps", "")) * 1_000_000
                else:
                    C = float(edge.transmission_capacity)
            except:
                C = 100_000_000

            D = sigma_sum / C  # Strict FIFO sum
            delays[key].append(D * 1000)  # ms
            delays_this_hop[key] = D

        # 3. Update bursts for next hop for all flows/targets
        for key, info in flow_info.items():
            if hop_idx >= len(info['path']) - 1:
                continue
            rho = info['rho']
            D = delays_this_hop.get(key, 0)
            prev_sigma = bursts_this_hop.get(key, flow_bursts_per_hop[key][-1])
            new_sigma = prev_sigma + rho * D
            flow_bursts_per_hop[key].append(new_sigma)

    # Sum up delays for each flow/target
    results = { (key[0], key[2]): sum(delays[key]) for key in flow_info }
    return results

stations, switches, edges, flows = parse_afdx_xml("data/STAR_3.xml")
global_overhead = 67
delays = compute_end_to_end_delay_fifo_strict_snapshot(flows, edges, global_overhead)
for (flow_name, target_name), total_delay in delays.items():
    print(f"Flow {flow_name} to {target_name}: End-to-end delay = {total_delay:.3f} ms")

