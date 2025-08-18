import xml.etree.ElementTree as ET
from collections import defaultdict
import time

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
        # self.burst = 0
        # self.rate = 0
        # self.end_delay = 0

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

def initial_burst(flow):
    return (flow.max_payload + global_overhead) * 8

def rate(flow):
    sigma = initial_burst(flow)
    period_sec = flow.period / 1000.0
    return sigma / period_sec

def calculate_node_delay(total_burst):
    return (total_burst/100000000)

def check():
    for f in flows:
        print(f.name)
        print(f.targets[0].path)
        print("Printed")



#Cases to consider
#1.Write the simplest case of one target(no multicaste) (Done)
#2.Write the simplest case of one target and no multicaste but different output port at switch (Done)
#3.Write the simplest case of multiple targets

delay_cache = {}

def calculate_delay(flow, target, node):
    '''
            Initialize all the flow's burst and rate, delay to zero
            Iterate through the target
                Extract the path
                Trim the path upto the node
                Iterate through the path
                    Save the node and next node
                    Iterate though all the flows
                        Save all the flows that share same path (It should not contain the current flow)
                    IF node is the source node                  (Base case of recursion)
                        Iterate through the shared flow
                            Burst sum at node  = Initial burst + Initial burst of all the shared flow
                        Calculate delay 
                        Update Burst
                        Update end delay
                        return burst, delay
                    Iterate through the shared flow
                        Sum burst with recursion (burst = current_flow_burst + (burst = calculate delay(shared flow, node)) (We will use recursion to backtrack flows)
                    Calculate the delay
                    Update Burst
                    return burst, delay
    '''

    cache_key = (flow.name, target.name, node)
    if cache_key in delay_cache:
        return delay_cache[cache_key]

    trim_path = []
    path = list(target.path)
    path.insert(0, flow.source)
    for pt in path:
        if pt != node:
            trim_path.append(pt)

    i = 0
    total_burst = 0
    shared_flow_previous_node = []

    while (node != path[i]):
        src = path[i]
        dst = path[i + 1]

        shared_flow = []
        # Use precomputed edge_to_flows for shared flows
        for (fs, t2) in edge_to_flows[(src, dst)]:
            if (fs.name == flow.name):
                continue
            if shared_flow and shared_flow[-1][0].name == fs.name:
                continue
            else:
                shared_flow.append((fs,t2))

        # shared_flow = [

        #     (fs, t2) for (fs, t2) in edge_to_flows[(src, dst)] if ((fs.name != flow.name) or (shared_flow and )) 
        # ]

        if i == 0:
            flow.burst = initial_burst(flow)
            total_burst = flow.burst
            flow.rate = rate(flow)
            for f3, _ in shared_flow:
                total_burst += initial_burst(f3)
            delay = calculate_node_delay(total_burst)
            flow.delay += delay
            flow.burst += flow.rate * delay

        else:
            total_burst = flow.burst
            for (f3, t3) in shared_flow:
                total_burst += calculate_delay(f3, t3, trim_path[i])[0]
            delay = calculate_node_delay(total_burst)
            flow.delay += delay
            flow.burst += flow.rate * delay

        i += 1
        shared_flow_previous_node = shared_flow

    delay_cache[cache_key] = (flow.burst, flow.delay)
    return flow.burst, flow.delay

global_overhead = 67
stations, switches, edges, flows = parse_afdx_xml("data/STAR_3.xml")

start = time.perf_counter()

from collections import defaultdict
edge_to_flows = defaultdict(list)
for f in flows:
    for t in f.targets:
        p = [f.source] + list(t.path)
        for i in range(len(p) - 1):
            edge_to_flows[(p[i], p[i+1])].append((f, t))


for flow in flows:
    for target in flow.targets:
        # Reset delays/bursts/rates before each run if required
        for f in flows:
            f.burst = 0
            f.rate = 0
            f.delay = 0
        delay_cache.clear()
        # Call calculate_delay for the end node
        burst, delay = calculate_delay(flow, target, target.path[-1])
        print(f"Flow: {flow.name}, Target: {target.name}, End-to-end delay: {delay*1_000_000:.2f} µs")

end = time.perf_counter()   

print(f"Time taken: {end - start:.6f} seconds")

