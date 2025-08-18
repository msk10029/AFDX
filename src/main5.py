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
    shared_flow_previous_node = []
    trim_path = []
    total_burst = 0
    # target_in_common_path = False
    # multicaste_diverge = []

    # path = [flow.source] + [target.path]
    path = list(target.path)
    path.insert(0, flow.source)
    #Trim the path upto the focus node
    for pt in path:
        if pt != node:
            trim_path.append(pt)
    # if len(trim_path) == 0:
    #     return flow.burst, flow.delay
    # else:
        # for i in range(len(trim_path)-1):   #Iterating through the whole path
    i = 0
    while (node != path[i]):
        src = path[i]
        dst = path[i+1]
        # Find all the flows arriving at the node
        shared_flow = []
        for fs in flows:
            for target2 in fs.targets:
                path2 = list(target2.path)
                path2.insert(0,fs.source)
                # if(fs.name == flow.name and target.name == target2.name):
                if(fs.name == flow.name):
                    continue       
                path_group = [(path2[j], path2[j+1]) for j in range(len(path2)-1)]
                # if i < len(path2) - 1 and path2[i] == src and path2[i + 1] == dst:
                #             shared_flow.append(fs) 
                # path_group = [(path2[j], path2[j+1]) for j in range(len(path2)-1)]
                # if (src, dst) in path_group and (fs,target2) not in shared_flow_previous_node:
                if (src, dst) in path_group:
                    if shared_flow and shared_flow[-1][0].name == fs.name:
                        continue
                    shared_flow.append((fs,target2))
        if i == 0:
            flow.burst = initial_burst(flow)
            total_burst = flow.burst
            flow.rate = rate(flow)
            for f3,_ in shared_flow:
                # flow.burst += initial_burst(f3)
                # flow.rate += rate(f3)
                total_burst +=initial_burst(f3)
            delay = calculate_node_delay(total_burst)
            flow.delay = flow.delay + delay
            flow.burst = flow.burst + flow.rate*delay
        
        else:
            total_burst = flow.burst
            for (f3,t3) in shared_flow:
                    # flow.burst = flow.burst + calculate_delay(f3, t3, trim_path[i])[0]
                    # flow.rate = flow.rate + f3.rate
                    total_burst = total_burst + calculate_delay(f3, t3, trim_path[i])[0]
            delay = calculate_node_delay(total_burst)
            flow.delay = flow.delay + delay
            flow.burst = flow.burst + flow.rate*delay
        i += 1
        shared_flow_previous_node = shared_flow
    return flow.burst, flow.delay

import time                 
start = time.perf_counter()
global_overhead = 67
stations, switches, edges, flows = parse_afdx_xml("data/check_3.xml")
for flow in flows:
    for target in flow.targets:
        for f in flows:
            f.burst = 0
            f.rate = 0
            f.delay = 0
        _, _ = calculate_delay(flow, target, target.path[-1])

        print(f"Flow name: {flow.name} ; End to End delay: {flow.delay*1000000}")
end = time.perf_counter()
print(f"Time taken: {end - start:.6f} seconds")
# check()
    