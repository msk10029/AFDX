import xml.etree.ElementTree as ET
from collections import defaultdict
import xml.dom.minidom

class Station:
    def __init__(self, name, service_policy, transmission_capacity):
        self.name = name
        self.service_policy = service_policy
        self.transmission_capacity = transmission_capacity

class Switch:
    def __init__(self, name, service_policy, switching_technique, tech_latency, transmission_capacity):
        self.name = name
        self.service_policy = service_policy
        self.switching_technique = switching_technique
        self.tech_latency = tech_latency
        self.transmission_capacity = transmission_capacity
     
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
        self.path = path  
        self.delay = 0

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
        self.targets = targets

    


def parse_afdx_xml(filename):
    tree = ET.parse(filename)
    root = tree.getroot()

    stations, switches, edges, flows = {}, {}, {}, []

    for elem in root:
        if elem.tag == "network":
            overhead = elem.attrib['overhead']
        if elem.tag == "station":
            stations[elem.attrib['name']] = Station(
                name=elem.attrib['name'],
                service_policy=elem.attrib.get('service-policy', None),
                transmission_capacity=elem.attrib.get('transmission-capacity', None),
            )

        elif elem.tag == "switch":
            switches[elem.attrib['name']] = Switch(
                name=elem.attrib['name'],
                service_policy=elem.attrib.get('service-policy', None),
                switching_technique=elem.attrib.get('switching-technique', None),
                tech_latency=elem.attrib.get('tech-latency', '0'),
                transmission_capacity=elem.attrib.get('transmission-capacity', None),
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

    return stations, switches, edges, flows, int(overhead)

#------------------------------------------------------------
# LINK LOAD CALCULATIONS
#------------------------------------------------------------

def link_load_calc():

    counted_on_edge = set()  # to track (flow, edge) pairs already counted
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
                        if key in counted_on_edge:  #check if already counted
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
        
        cap_bps = 100_000_000  # Default: 100 Mbps

        print(f"Edge {edge.name}:")
        print(f"Direct load  {edge.direct_load:.0f} bps  {100 * edge.direct_load / cap_bps:.4f}%")
        print(f"Reverse load {edge.reverse_load:.0f} bps  {100 * edge.reverse_load / cap_bps:.4f}%")
        print("-" * 50)



# ------------------------------------------------------------------
# End to End Delay Calculations
#-------------------------------------------------------------------

'''
        Approach: To calculate end to end delay of a flow, we will follow a flow throughout its
        path, and sum up all the delays expericed at the path nodes. To figure out delays at a node, we will need to find
        which flows are sharing the node and are using the same edge and outport port. The shared flow, might have shifted its burst due to its propagation in its
        path. To find the incoming burst of the shared flow, we will need to backtrack the flow to its source, follow its path and calculate 
        the shifted burst and delay. To do the backtrack, we will use a recursive function.


        ALGO:
            Initialize all the flow's burst and rate, delay to zero
            Iterate through the target --> Send the flow, target and destination node to function

                Extract the path 
                Iterate through the path (Stop before the destination node)
                    Save the node and next node
                    Figure out, what flows are using the same node and next node (same edge) and store it (shared flow)

                    IF node is the source node              
                        Iterate through the shared flow
                            Burst sum at node  = Initial burst + Initial burst of all the shared flow
                        Calculate delay 
                        Update Burst
                        Update end delay
                     
                    If node is not the source node
                        Iterate through the shared flow
                            Sum burst with recursion (burst = current_flow_burst + (burst = calculate delay(shared flow, shared flow target,node)) (We will use recursion to backtrack flows)
                        Calculate the delay
                        Update Burst
                        Update end delay

                When the path is traversed => Return burst, delay


        Becuase of recursion, shared flow delay calculation can become redundant (It might calculate the same flow again and again), if it shares the same path.
        It can lead to exponential time complexity. Cache Memory can be used to figure out and store the delays already calculated and return from function if it is already calculated.
    '''


# Support Functions

def initial_burst(flow):
    return (flow.max_payload + global_overhead) * 8

def rate(flow):
    sigma = initial_burst(flow)
    period_sec = flow.period / 1000.0
    return sigma / period_sec

def calculate_node_delay(total_burst):
    return (total_burst/100000000)

# def check():
#     for f in flows:
#         print(f.name)
#         print(f.targets[0].path)
#         print("Printed")


""""
Cases to consider
1. Case of one target(no multicaste) (Done)
2. Case of unicaste but different output port at switch (different direction of flows) (Done)
3. Multicaste case of one flow (Done)
4. Multicaste case of multiple flows with different path lengths and divergence (Done)
5. Run on AFDX file and check results (Done)
"""


def calculate_delay(flow, target, node):

    
    # Cache Memory to store delay calculations
    cache_key = (flow.name, target.name, node)
    if cache_key in delay_cache:
        return delay_cache[cache_key]
    

    path = list(target.path)
    path.insert(0, flow.source)

    i = 0
    local_burst = 0
    local_delay = 0

    while (node != path[i]):  # Traverse through the path
        src = path[i]
        dst = path[i + 1]
        
        # Store the flows which are sharing the same edge. edge_to_flows contain all the path node pairs of all the flows
        shared_flow = []
        for (fs, t2) in edge_to_flows[(src, dst)]:
            if (fs.name == flow.name):  # To avoid adding itself in the shared list
                continue
            if shared_flow and shared_flow[-1][0].name == fs.name:  # To avoid adding multiple instances of same flow due to multicasting
                continue
            else:
                shared_flow.append((fs,t2))

        if i == 0:     # At Source Node
            this_burst = initial_burst(flow)
            this_rate = rate(flow)
            total_burst = this_burst
            for f3, _ in shared_flow:    
                total_burst += initial_burst(f3)  # Sum up all the flow at the source
            delay = calculate_node_delay(total_burst)
            local_delay += delay
            local_burst = this_burst + this_rate * delay

        else:   #Anywhere else
            this_rate = rate(flow)
            total_burst = local_burst
            for (f3, t3) in shared_flow:
                burst_shared, _ = calculate_delay(f3, t3, path[i]) # Backtrack shared flow
                total_burst += burst_shared
            delay = calculate_node_delay(total_burst)
            local_delay += delay
            local_burst += this_rate * delay

        i += 1

    delay_cache[cache_key] = (local_burst, local_delay)
    return local_burst, local_delay


def main_delay_func(flows):

    # Iterate through all the flows and targets
    for flow in flows:
        for target in flow.targets:
            for f in flows:   # Rest all the data to zero (Can be optimized!)
                f.burst = 0
                f.rate = 0
                f.delay = 0
            delay_cache.clear()
            burst, delay = calculate_delay(flow, target, target.path[-1])   # calculte_delay function calculates the burst and delay of the flow till the given node.
            flow.burst = burst
            flow.delay = delay
            target.delay = delay*1000000  # to microsecond

#---------------------------------------------
# Writing values to output xml file
#---------------------------------------------

def write_results_xml(flows, edges, filename):
    results = ET.Element("results")
    # Delays
    delays_elem = ET.SubElement(results, "delays")
    for flow in flows:
        flow_elem = ET.SubElement(delays_elem, "flow", {"name": flow.name})
        for target in flow.targets:
            ET.SubElement(flow_elem, "target", {
                "name": target.name,
                "value": f"{getattr(target, 'delay', 0):.1f}"
            })

    # Load
    load_elem = ET.SubElement(results, "load")
    for edge in edges.values():
        edge_name = f"{edge.from_node} => {edge.to_node}"
        edge_elem = ET.SubElement(load_elem, "edge", {"name": edge_name})

        cap_bps = 100_000_000  # default value

        for usage_type in ("direct", "reverse"):
            load_val = getattr(edge, f"{usage_type}_load", 0.0)
            percent = 100 * load_val / cap_bps if cap_bps else 0
            payload = int(load_val) 
            ET.SubElement(edge_elem, "usage", {
                "type": usage_type,
                "percent": f"{percent:.1f}%",
                "value": f"{load_val:.2f}",
                "payload": f"{payload}"
            })


    # to print to console
    xml_str = ET.tostring(results, encoding="unicode")
    dom = xml.dom.minidom.parseString(xml_str)
    print(dom.toprettyxml())

    # Save file
    tree = ET.ElementTree(results)
    tree.write(filename, encoding="utf-8", xml_declaration=True)





#----------------------------------------------------------
# Main Function calls
#----------------------------------------------------------


delay_cache = {}
stations, switches, edges, flows, global_overhead = parse_afdx_xml("data/AFDX.xml")
# print(type(global_overhead))

edge_to_flows = defaultdict(list) # To make path groups (node pairs) of all the flows
for f in flows:
    for t in f.targets:
        p = [f.source] + list(t.path)
        for i in range(len(p) - 1):
            edge_to_flows[(p[i], p[i+1])].append((f, t))
main_delay_func(flows)
link_load_calc()
write_results_xml(flows, edges, 'output.xml')
# print_link_load()


