################################################################@
"""
This file is a starting base for XML network parsing.
It is provided for the AFDX Project (WoPANets Extension) so that students
can focus on Network Calculus. In this version we complete the basic
classes and include both delay and link load calculations.
"""
################################################################@

import xml.etree.ElementTree as ET
import os.path
import sys

################################################################@
""" Local classes """
################################################################@

class Node:
    def __init__(self, name):
        self.name = name

class Station(Node):
    def __init__(self, name):
        super().__init__(name)
    def isSwitch(self):
        return False

class Switch(Node):
    def __init__(self, name, latency):
        super().__init__(name)
        self.latency = latency  # technological latency (if any)
    def isSwitch(self):
        return True

class Edge:
    def __init__(self, name, frm, to):
        self.name = name
        self.frm = frm
        self.to = to

class Target:
    def __init__(self, flow, to):
        self.flow = flow
        self.to = to
        self.path = []  # list of node names representing the route

class Flow:
    def __init__(self, name, source, payload, overhead, period):
        self.name = name
        self.source = source
        self.payload = payload      # in bytes (max payload)
        self.overhead = overhead    # additional bytes (e.g. 67)
        self.period = period        # in seconds
        self.targets = []           # list of Target objects

################################################################@
""" Parsing Functions """
#################################################################

def parseStations(root):
    for station in root.findall('station'):
        nodes.append(Station(station.get('name')))

def parseSwitches(root):
    for sw in root.findall('switch'):
        # Convert tech-latency (given in microseconds) to seconds.
        nodes.append(Switch(sw.get('name'), float(sw.get('tech-latency')) * 1e-6))

def parseEdges(root):
    for link in root.findall('link'):
        edges.append(Edge(link.get('name'), link.get('from'), link.get('to')))

def parseFlows(root):
    for fl in root.findall('flow'):
        # period provided in milliseconds; convert to seconds.
        flow = Flow(fl.get('name'),
                    fl.get('source'),
                    float(fl.get('max-payload')),
                    67,  # fixed overhead in bytes
                    float(fl.get('period')) * 1e-3)
        flows.append(flow)
        for tg in fl.findall('target'):
            target = Target(flow, tg.get('name'))
            flow.targets.append(target)
            # The path always starts with the source.
            target.path.append(flow.source)
            for pt in tg.findall('path'):
                target.path.append(pt.get('node'))

def parseNetwork(xmlFile):
    if os.path.isfile(xmlFile):
        tree = ET.parse(xmlFile)
        root = tree.getroot()
        parseStations(root)
        parseSwitches(root)
        parseEdges(root)
        parseFlows(root)
    else:
        print("File not found: " + xmlFile)

def traceNetwork():
    print("Stations:")
    for node in nodes:
        if not node.isSwitch():
            print("\t" + node.name)
    print("\nSwitches:")
    for node in nodes:
        if node.isSwitch():
            print("\t" + node.name)
    print("\nEdges:")
    for edge in edges:
        print("\t" + edge.name + ": " + edge.frm + " => " + edge.to)
    print("\nFlows:")
    for flow in flows:
        print("\t" + flow.name + ": " + flow.source + " (L=" + str(flow.payload) +
              ", p=" + str(flow.period) + ")")
        for target in flow.targets:
            print("\t\tTarget=" + target.to)
            for node in target.path:
                print("\t\t\t" + node)

def file2output(file):
    with open(file, "r") as hFile:
        for line in hFile:
            print(line.rstrip())

################################################################@
""" Network Calculation Functions """
#################################################################

def compute_payload(flow):
    """Converts the sum of payload and overhead from bytes to bits."""
    return (flow.payload + flow.overhead) * 8

def compute_rate(flow):
    """Computes the flow rate in bits per second."""
    return compute_payload(flow) / flow.period

def count_same_source(flows, flow):
    """Counts how many flows originate from the same source."""
    return sum(1 for f in flows if f.source == flow.source)

def is_switch(node_name):
    """Checks whether a given node name corresponds to a switch."""
    for node in nodes:
        if node.name == node_name:
            return node.isSwitch() if hasattr(node, 'isSwitch') else False
    return False



def compute_delays():
    """Computes the end-to-end delay for each flow target.
       Returns a dictionary mapping flow names to a list of (target, delay) tuples.
    """
    capacity = 100e6  # 100 Mbps link capacity
    delay_results = {}
    for flow in flows:
        payload_bits = compute_payload(flow)
        same_source = count_same_source(flows, flow)
        initial_delay = (payload_bits * same_source) / capacity
        flow_rate = compute_rate(flow)
        # Initial burst includes payload plus delay effect.
        burst = payload_bits + initial_delay * flow_rate

        for target in flow.targets:
            current_delay = initial_delay
            current_burst = burst
            # Walk through each hop in the target's path.
            for i in range(len(target.path) - 1):
                src = target.path[i]
                dst = target.path[i + 1]
                if is_switch(dst):
                    interfering_burst = 0
                    
                    for other_flow in flows:
                        for other_target in other_flow.targets:
                            if other_target.to == target.to and dst in other_target.path:
                                other_payload = compute_payload(other_flow)
                                other_same = count_same_source(flows, other_flow)
                                other_initial = (other_payload * other_same) / capacity
                                other_rate = compute_rate(other_flow)
                                other_burst = other_payload + other_initial * other_rate
                                interfering_burst += other_burst
                                
                                break
                    add_delay = interfering_burst / capacity
                    current_delay += add_delay
                    current_burst += flow_rate * add_delay
            if flow.name not in delay_results:
                delay_results[flow.name] = []
            delay_results[flow.name].append((target.to, current_delay))
    return delay_results


################################################################@
""" Link Load Calculation Functions """
#################################################################

def compute_link_load():
    """Calculates the load on each network link.
       Returns a dictionary mapping edge names to load data.
    """
    capacity = 100e6  # 100 Mbps link capacity
    link_loads = {}
    for edge in edges:

        # Initialize accumulators for both directions.
        direct = {"value": 0.0, "percent": 0.0, "payload": 0.0}
        reverse = {"value": 0.0, "percent": 0.0, "payload": 0.0}
        for flow in flows:
            rate = compute_rate(flow)
            payload_bits = compute_payload(flow)
            for target in flow.targets:
                # Check if both nodes appear in the target's path.
                if edge.frm in target.path and edge.to in target.path:
                    if target.path.index(edge.frm) < target.path.index(edge.to):
                        # Flow traverses edge in the forward (direct) direction.
                        direct["value"] += rate
                        direct["payload"] += payload_bits
                        direct["percent"] += (rate / capacity) * 100
                    else:
                        # Flow traverses in reverse.
                        reverse["value"] += rate
                        reverse["payload"] += payload_bits
                        reverse["percent"] += (rate / capacity) * 100
        link_loads[edge.name] = {"direct": direct, "reverse": reverse}
    return link_loads

################################################################@
""" Results File Creation """
#################################################################

def createResultsFile(xmlFile):
    """Generates an XML output file with both delay and link load metrics."""
    delays_dict = compute_delays()
    link_loads = compute_link_load()
    posDot = xmlFile.rfind('.')
    if posDot != -1:
        resFile = xmlFile[:posDot] + '_res1.xml'
    else:
        resFile = xmlFile + '_res1.xml'
    with open(resFile, "w") as res:
        res.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        res.write('<results>\n')

        # Write delay results.
        res.write('\t<delays>\n')
        for flow_name, targets in delays_dict.items():
            res.write('\t\t<flow name="{}">\n'.format(flow_name))
            for target_name, delay in targets:

                # Output delay in microseconds.
                delay_micro = delay * 1e6
                res.write('\t\t\t<target name="{}" value="{:.1f}" />\n'.format(target_name, delay_micro))
            res.write('\t\t</flow>\n')
        res.write('\t</delays>\n')

        # Write link load results.
        res.write('\t<load>\n')
        for edge in edges:
            load = link_loads.get(edge.name, {})
            direct = load.get("direct", {"percent": 0, "value": 0, "payload": 0})
            reverse = load.get("reverse", {"percent": 0, "value": 0, "payload": 0})
            res.write('\t\t<edge name="{} => {}">\n'.format(edge.frm, edge.to))
            res.write('\t\t\t<usage type="direct" percent="{:.1f}%" value="{:.2f}" payload="{:.0f}" />\n'.format(
                direct["percent"], direct["value"], direct["payload"]))
            res.write('\t\t\t<usage type="reverse" percent="{:.1f}%" value="{:.2f}" payload="{:.0f}" />\n'.format(
                reverse["percent"], reverse["value"], reverse["payload"]))
            res.write('\t\t</edge>\n')
        res.write('\t</load>\n')
        res.write('</results>\n')
    file2output(resFile)

################################################################@
""" Global data """
#################################################################
nodes = []   # List of network nodes (stations and switches)
edges = []   # List of network edges (links)
flows = []   # List of flows

################################################################@
""" Main Program """
#################################################################
if len(sys.argv) >= 2:
    xmlFile = sys.argv[1]
else:
    xmlFile = "./data/check_3.xml"  

parseNetwork(xmlFile)
# Uncomment traceNetwork() for debugging if needed
# traceNetwork()
createResultsFile(xmlFile)
