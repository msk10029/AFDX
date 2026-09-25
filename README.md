# AFDX Network Analysis

A Python-based analysis tool for **Avionics Full-Duplex Switched Ethernet (AFDX)** networks.

The project parses AFDX network descriptions stored in XML and computes:

* End-to-end delay for each virtual link (flow) and target
* Burst propagation through the network
* Flow transmission rates
* Link utilization / load in both directions
* Analysis of flows sharing the same network paths
* XML output containing calculated delay and load results

The implementation uses a **Network Calculus-style approach** to estimate timing behavior in an AFDX network.

## AI Usage

**No Artificial Intelligence was used for algorithm design and coding**. The only use of an LLM was to create the README.

## Overview

AFDX is an Ethernet-based deterministic communication technology used in modern aircraft to exchange data between avionics systems.

This project models an AFDX network as a collection of:

* **Stations** – end systems connected to the network
* **Switches** – AFDX switches forwarding traffic
* **Links** – physical connections between stations and switches
* **Flows** – periodic traffic streams transmitted through predefined routes
* **Targets** – destinations of a flow, including multicast destinations

The XML network description contains the network topology, transmission parameters and flow definitions. The Python implementation parses this description and performs the required calculations.

## Analysis Performed

### 1. Flow Rate

For every flow, the effective frame size is calculated using:

```text
Frame Size = Maximum Payload + Network Overhead
```

The repository's AFDX examples use a network overhead of **67 bytes**.

The transmission rate is then calculated as:

```text
Rate = (Frame Size × 8) / Period
```

where the period is converted from milliseconds to seconds.

### 2. Burst Calculation

The initial burst is represented as:

```text
Initial Burst = (Maximum Payload + Overhead) × 8
```

As a flow traverses the network, its burst can increase according to the delay experienced at intermediate nodes.

The implementation keeps track of the propagated burst so that downstream nodes use the updated traffic characteristics of the flow.

### 3. End-to-End Delay

The project computes end-to-end delay by traversing the path of every flow.

When multiple flows share the same network edge, their bursts contribute to the total burst at that point. The resulting node delay is calculated using the link capacity.

The implementation also uses **recursive backtracking and caching** to determine the burst of interfering flows at shared edges.

This is particularly useful for handling:

* Single-destination flows
* Multiple flows sharing an edge
* Multicast flows
* Flows with different path lengths
* Paths that diverge after sharing part of the network
* Flows travelling in different directions

### 4. Link Load

For every physical link, the tool calculates traffic in both directions:

```text
Direct Load
Reverse Load
```

The load is expressed in bits per second and as a percentage of the link capacity.

For example:

```text
Edge L22:
Direct load  = 12,000,000 bps
Reverse load = 4,000,000 bps
```

with a corresponding utilization percentage relative to the configured link capacity.

## Repository Structure

```text
AFDX/
│
├── data/
│   ├── AFDX.xml
│   ├── AFDX_res.xml
│   ├── AFDX.tmne
│   ├── 3ESE.xml
│   ├── 3ESE_res.xml
│   ├── ISAE_TEST_1.xml
│   ├── ISAE_TEST_1_res.xml
│   ├── ISAE_TEST_2.xml
│   ├── ISAE_TEST_2_res.xml
│   ├── MSK_1.xml
│   ├── STAR_3.xml
│   ├── STAR_3_res.xml
│   └── ...
│
├── src/
│   ├── Mohsin_Khan.py
│   ├── main.py
│   ├── main_2.py
│   ├── main_3.py
│   ├── main4.py
│   ├── main5.py
│   └── main6.py
│
├── 3ESE_res.xml
├── output.xml
└── README.md
```

`src/Mohsin_Khan.py` contains the main implementation used for the complete delay and link-load analysis.

The other Python files contain earlier or alternative implementations used during development and testing.

## Input XML Format

The analysis expects an XML file describing an AFDX network.

A simplified example is:

```xml
<elements>

    <network
        name="AFDX"
        overhead="67"
        shortest-path-policy="DIJKSTRA"
        technology="AFDX"
        transmission-capacity="100Mbps"
        x-type="FULL"/>

    <station
        name="A1"
        service-policy="FIRST_IN_FIRST_OUT"
        transmission-capacity="100Mbps"/>

    <switch
        name="S1"
        service-policy="FIRST_IN_FIRST_OUT"
        switching-technique="CUT_THROUGH"
        tech-latency="0"
        transmission-capacity="100Mbps"/>

    <link
        name="L1"
        from="A1"
        fromPort="0"
        to="S1"
        toPort="0"
        transmission-capacity="100Mbps"/>

    <flow
        name="A1-1"
        source="A1"
        max-payload="16"
        min-payload="16"
        period="32"
        deadline="32"
        jitter="0"
        priority="Low">

        <target name="A2">
            <path node="S1"/>
            <path node="A2"/>
        </target>

    </flow>

</elements>
```

### Network

The `<network>` element defines global parameters such as:

* Network name
* Frame overhead
* Network technology
* Default transmission capacity
* Shortest-path policy

For example:

```xml
overhead="67"
transmission-capacity="100Mbps"
```

### Stations

Stations represent AFDX end systems.

```xml
<station
    name="A1"
    service-policy="FIRST_IN_FIRST_OUT"
    transmission-capacity="100Mbps"/>
```

### Switches

Switches represent AFDX switching elements.

```xml
<switch
    name="S1"
    service-policy="FIRST_IN_FIRST_OUT"
    switching-technique="CUT_THROUGH"
    tech-latency="0"
    transmission-capacity="100Mbps"/>
```

### Links

Links connect two nodes in the topology.

```xml
<link
    name="L1"
    from="A1"
    fromPort="0"
    to="S1"
    toPort="0"
    transmission-capacity="100Mbps"/>
```

### Flows

A flow represents periodic traffic in the network.

```xml
<flow
    name="A1-1"
    source="A1"
    max-payload="16"
    min-payload="16"
    period="32"
    deadline="32"
    jitter="0"
    priority="Low">
```

A flow can have one or more targets.

```xml
<target name="A2">
    <path node="S1"/>
    <path node="A2"/>
</target>
```

Multiple targets allow multicast-style traffic to be represented.

## Requirements

The project uses Python and the Python standard library.

The implementation relies on:

```text
Python 3.x
```

The current implementation uses standard-library modules including:

```python
xml.etree.ElementTree
collections
xml.dom.minidom
```

No external Python package is required for the main analysis implementation.

## Running the Analysis

Clone the repository:

```bash
git clone https://github.com/msk10029/AFDX.git
cd AFDX
```

Run the main implementation:

```bash
python src/Mohsin_Khan.py
```

The current implementation loads:

```text
data/AFDX.xml
```

and generates:

```text
output.xml
```

The program also prints the generated XML results to the console.

## Using a Different Input File

The repository also contains several different XML network examples in the `data/` directory.

To analyse another network, change the input file in:

```python
stations, switches, edges, flows, global_overhead = parse_afdx_xml(
    "data/AFDX.xml"
)
```

For example:

```python
stations, switches, edges, flows, global_overhead = parse_afdx_xml(
    "data/STAR_3.xml"
)
```

## Output

The generated result file contains two major sections:

```xml
<results>

    <delays>
        ...
    </delays>

    <load>
        ...
    </load>

</results>
```

### Delay Results

Each flow contains its calculated target delay:

```xml
<flow name="AFDX Flow 1">
    <target name="AFDX Station 3" value="363.3"/>
</flow>
```

The delay value is written in **microseconds**.

### Link Load Results

For each link, both traffic directions are reported:

```xml
<edge name="S1 => S5">

    <usage
        type="direct"
        percent="8.5%"
        value="8536000.00"
        payload="8536"/>

    <usage
        type="reverse"
        percent="0.0%"
        value="0.00"
        payload="0"/>

</edge>
```

The output provides:

* Utilization percentage
* Load in bits per second
* Payload/load value
* Direction of traffic

## Network Calculus Approach

The core analysis follows a burst/rate model.

For a flow:

```text
σ = (Payload + Overhead) × 8
ρ = σ / Period
```

where:

* `σ` is the initial burst
* `ρ` is the flow rate

At a shared link, the implementation aggregates the bursts of interfering flows.

The resulting delay is approximately represented by:

```text
Delay = Total Burst / Link Capacity
```

The burst of the analysed flow is then updated using:

```text
Updated Burst = Previous Burst + Rate × Delay
```

This process is repeated while traversing the flow's path.

Because a multicast flow can have multiple paths, the implementation tracks each flow/target combination independently.

## Multicast Handling

The project explicitly considers multicast scenarios.

For example, one flow may contain several targets:

```text
        ┌── A2
A1 ─ S1 ├── A3
        └── A4
```

The implementation accounts for the fact that the flow shares the upstream part of the route before the paths diverge.

The delay calculation also recursively determines the propagated burst of other flows that share an edge.

## Development Notes

The repository contains multiple versions of the analysis code:

```text
main.py
main_2.py
main_3.py
main4.py
main5.py
main6.py
afdx_analyzer.py
```

These represent different iterations and approaches developed while testing the delay and load calculations.

`afdx_analyzer.py` is the most complete implementation and includes:

* XML parsing
* Flow rate calculation
* Burst calculation
* Recursive delay calculation
* Delay caching
* Multicast handling
* Link-load calculation
* XML result generation

## Example Network

The repository includes a relatively large AFDX network model in:

```text
data/AFDX.xml
```

The model contains multiple stations, switches, links and periodic flows, including service flows and multicast traffic.

Additional smaller XML files in `data/` can be used for testing and validation.

## Limitations

This project is primarily an academic / engineering analysis implementation rather than a production-certified AFDX analysis tool.

Some calculations currently use assumptions such as:

* 100 Mbps link capacity in parts of the implementation
* A fixed 67-byte network overhead
* FIFO-based service assumptions
* Simplified delay calculations
* Explicit paths supplied in the XML input

The different Python versions may also contain different modelling assumptions and should not be treated as interchangeable implementations.

For safety-critical engineering use, the algorithms and assumptions should be independently validated against the applicable AFDX/ARINC specifications and reference Network Calculus models.

## Background

This project was developed as part of work on the **Real Time Networks Course** at ISAE - SUPAERO, with a focus on analysing deterministic Ethernet traffic, shared network resources, burst propagation and end-to-end communication delay.


## Author

**Mohsin Khan**

GitHub: [@msk10029](https://github.com/msk10029)

## License

This repository is provided for viewing purposes only. Copying, modifying, redistributing, or using this code for commercial purposes is not permitted without prior written permission from the author.
