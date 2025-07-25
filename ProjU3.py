# GRAPH

import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import streamlit.components.v1 as components
import matplotlib.pyplot as plt
import random

# Try to import Louvain community detection
try:
    import community as community_louvain
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-louvain"])
    import community as community_louvain

import networkx as nx

# Streamlit setup
st.set_page_config(page_title="Marvel Network", layout="wide")
st.markdown("# Marvel Character Network with Clustering & Interactions (Total: N=327, E=9891)")

@st.cache_data
def load_data():
    df = pd.read_csv("marvel-unimodal-edges.csv")
    return df

# Load and preview data
df = load_data()

# Validate required columns
if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

# Edge display limit input
st.markdown("## Edge Display Control")

default_limit = 2000
edge_limit_input = st.text_input("Enter number of edges to display (positive integer):", value=str(default_limit))

# Button to trigger display
apply_limit = st.button("Display Graph with Limited Edges")

# Apply limit only if button pressed
if apply_limit:
    try:
        edge_limit = max(1, int(edge_limit_input))
        df = df.head(edge_limit)
        st.success(f"Displaying first {edge_limit} edges.")
    except ValueError:
        st.error("Please enter a valid positive integer.")
else:
    # Default to 500 edges before user presses button
    df = df.head(default_limit)

# Build NetworkX graph
G = nx.from_pandas_edgelist(df, source='Source', target='Target', edge_attr='Weight')
partition = community_louvain.best_partition(G)
degree_dict = dict(G.degree())
max_degree = max(degree_dict.values()) if degree_dict else 1

# Color palette
palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
]

# Create Pyvis network
marvel_net = Network(height='900px', width='100%', notebook=False, cdn_resources='remote')

# Add nodes with community color and hub size
for node in G.nodes():
    community_id = partition.get(node, 0)
    degree = degree_dict.get(node, 1)
    size = 15 + (degree / max_degree) * 35
    color = palette[community_id % len(palette)]

    marvel_net.add_node(
        node,
        label=node,
        title=f"Community: {community_id}\nDegree: {degree}",
        color=color,
        size=size,
        shape="dot",
        font={"size": 22, "face": "arial", "multi": "md", "align": "center"}
    )

# Add edges
for _, row in df.iterrows():
    src, dst, w = row['Source'], row['Target'], row['Weight']
    marvel_net.add_edge(src, dst, value=w)

# Enable interactive features for highlighting
marvel_net.set_options("""
var options = {
  "nodes": {
    "font": {
      "size": 22,
      "face": "arial",
      "multi": "md",
      "align": "center"
    },
    "scaling": {
      "min": 10,
      "max": 45
    },
    "shape": "dot"
  },
  "edges": {
    "color": {
      "inherit": true
    },
    "smooth": {
      "enabled": true,
      "type": "dynamic",
      "roundness": 0.5
    }
  },
  "physics": {
    "enabled": true,
    "solver": "repulsion",
    "repulsion": {
      "centralGravity": 0.15,
      "springLength": 300,
      "springConstant": 0.01,
      "nodeDistance": 220,
      "damping": 0.15
    },
    "stabilization": {
      "enabled": true,
      "iterations": 250,
      "updateInterval": 25,
      "onlyDynamicEdges": false,
      "fit": true
    },
    "minVelocity": 0.75
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 50,
    "hideEdgesOnDrag": false,
    "zoomView": true,
    "dragNodes": true,
    "dragView": true,
    "selectConnectedEdges": true,
    "multiselect": false,
    "highlightNearest": {
      "enabled": true,
      "degree": 1,
      "hover": false
    }
  }
}
""")

# Save graph to temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Inject JS to control physics on drag
custom_js = """
<script type="text/javascript">
  function controlPhysics() {
    network.once('stabilizationIterationsDone', function () {
      network.setOptions({ physics: false });
    });
    network.on("dragStart", function () {
      network.setOptions({ physics: true });
    });
    network.on("dragEnd", function () {
      setTimeout(() => network.setOptions({ physics: false }), 300);
    });
  }
  if (typeof network !== "undefined") {
    controlPhysics();
  } else {
    setTimeout(controlPhysics, 1000);
  }
</script>
"""

# Inject JS
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Show in Streamlit
st.markdown("## Interactive Network Graph")
components.html(html_content, height=900, scrolling=True)

# Cleanup
os.unlink(path)

# METRICS

st.markdown("## Network Analysis Metrics")

# Check if graph is connected; if not, get largest connected component
if nx.is_connected(G):
    G_connected = G
else:
    # Get the largest connected component as a subgraph
    largest_cc = max(nx.connected_components(G), key=len)
    G_connected = G.subgraph(largest_cc).copy()
    st.warning("Original graph was not connected. Using largest connected component for diameter and periphery calculations.")

# Adjacency matrix as a DataFrame
adj_matrix = nx.adjacency_matrix(G_connected)
adj_df = pd.DataFrame(adj_matrix.todense(), index=G_connected.nodes(), columns=G_connected.nodes())
N = len(G_connected.nodes())
st.markdown(f"### Adjacency Matrix ({N}x{N})")
st.dataframe(adj_df.style.format("{:.0f}"))

# Diameter
diameter = nx.diameter(G_connected)
st.markdown(f"### Diameter of the connected network: **{diameter}**")

# Periphery nodes
periphery_nodes = list(nx.periphery(G_connected))
st.markdown(f"### Periphery Nodes ({len(periphery_nodes)} nodes):")
st.write(periphery_nodes)

# DENSITY & ASSORTATIVITY

# Density of the connected graph
density = nx.density(G_connected)
st.markdown(f"### Network Density: **{density:.5f}**")
st.markdown(f"### Network Sparsity: **{(1 - density):.5f}**")

# General degree assortativity
try:
    assortativity = nx.degree_assortativity_coefficient(G_connected)
    st.markdown(f"### Degree Assortativity Coefficient: **{assortativity:.5f}**")
except nx.NetworkXError as e:
    st.warning(f"Assortativity could not be computed: {e}")

# DEGREE HISTOGRAM

# Compute degrees
degrees = [deg for _, deg in G_connected.degree()]

# Plot histogram
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(degrees, bins=30, color='skyblue', edgecolor='black')
ax.set_title("Node Degree Distribution")
ax.set_xlabel("Degree")
ax.set_ylabel("Number of Nodes")
st.pyplot(fig)

st.markdown("## Clustering and Connectivity Analysis")

# Convert to directed graph for SCC/WCC
G_directed = nx.DiGraph()
G_directed.add_weighted_edges_from([(row['Source'], row['Target'], row['Weight']) for _, row in df.iterrows()])

# Global clustering coefficient (transitivity)
global_clustering = nx.transitivity(G)
st.markdown(f"### Global Clustering Coefficient: **{global_clustering:.4f}**")

# Local clustering coefficient for selected nodes
st.markdown("### Local Clustering Coefficient")
selected_nodes = st.multiselect("Select nodes to inspect their local clustering coefficient:", list(G.nodes())[:100])
if selected_nodes:
    for node in selected_nodes:
        coeff = nx.clustering(G, node)
        st.write(f"Node **{node}**: Clustering Coefficient = **{coeff:.4f}**")

# Strongly Connected Components (requires directed graph)
st.markdown(f"### Strongly Connected Components: N/A")

# Weakly Connected Components
st.markdown(f"### Weakly Connected Components: N/A")

st.markdown("## Node Centrality Analysis")

# Compute centrality metrics
with st.spinner("Calculating centralities..."):
    eigen_centrality = nx.eigenvector_centrality(G_connected, max_iter=1000)
    degree_centrality = nx.degree_centrality(G_connected)
    closeness_centrality = nx.closeness_centrality(G_connected)
    betweenness_centrality = nx.betweenness_centrality(G_connected)

# Create DataFrame for centralities
centrality_df = pd.DataFrame({
    'Node': list(G_connected.nodes()),
    'Eigenvector': [eigen_centrality[n] for n in G_connected.nodes()],
    'Degree': [degree_centrality[n] for n in G_connected.nodes()],
    'Closeness': [closeness_centrality[n] for n in G_connected.nodes()],
    'Betweenness': [betweenness_centrality[n] for n in G_connected.nodes()]
})

# Sort by each centrality and show top 10
st.markdown("### Top 10 Nodes by Centrality Measures")
top_k = 10
cols = st.columns(4)
for i, metric in enumerate(['Eigenvector', 'Degree', 'Closeness', 'Betweenness']):
    top_nodes = centrality_df.nlargest(top_k, metric)
    with cols[i]:
        st.markdown(f"**{metric} Centrality**")
        st.dataframe(top_nodes[['Node', metric]].reset_index(drop=True), use_container_width=True)

# Plot all centralities for comparison (barplot of top nodes by any metric)
st.markdown("### Centrality Comparison Plot")

# Melt the DataFrame for seaborn-like plot
centrality_melted = centrality_df.melt(id_vars='Node', var_name='Centrality Type', value_name='Score')

# Keep only top N nodes across all types
top_nodes_all = set()
for metric in ['Eigenvector', 'Degree', 'Closeness', 'Betweenness']:
    top_nodes_all.update(centrality_df.nlargest(top_k, metric)['Node'])

filtered_df = centrality_melted[centrality_melted['Node'].isin(top_nodes_all)]

# Combine and sort all top 10 nodes per metric into one sorted list
all_top = pd.concat([
    filtered_df[filtered_df['Centrality Type'] == ctype].sort_values('Score', ascending=False).head(top_k)
    for ctype in ['Eigenvector', 'Degree', 'Closeness', 'Betweenness']
])
all_top = all_top.sort_values('Score', ascending=False).reset_index(drop=True)

# Create labels and colors
label_map = {'Eigenvector': 'E', 'Degree': 'D', 'Closeness': 'C', 'Betweenness': 'B'}
color_map = {
    'Eigenvector': '#1f77b4',
    'Degree': '#ff7f0e',
    'Closeness': '#2ca02c',
    'Betweenness': '#d62728'
}
bar_labels = [f"{row['Node']} ({label_map[row['Centrality Type']]})" for _, row in all_top.iterrows()]
bar_scores = all_top['Score'].tolist()
bar_colors = [color_map[row['Centrality Type']] for _, row in all_top.iterrows()]

# Plot sorted bar chart
fig, ax = plt.subplots(figsize=(16, 6))
ax.bar(bar_labels, bar_scores, color=bar_colors)

ax.set_title("Top 10 Nodes per Centrality Type (Sorted by Score)")
ax.set_ylabel("Centrality Score")
ax.set_xticks(range(len(bar_labels)))
ax.set_xticklabels(bar_labels, rotation=65, ha='right')
ax.set_xlim(-1, len(bar_labels))
ax.legend(handles=[plt.Rectangle((0,0),1,1,color=c,label=l) for l,c in color_map.items()])
st.pyplot(fig)

# Attack comparison graph
st.markdown("## Network Robustness: Random vs Targeted Attack")

def simulate_attack(graph, strategy="random", remove_fraction=1):
    """
    Simulates attack by progressively removing nodes.
    :param graph: NetworkX graph
    :param strategy: 'random' or 'targeted'
    :param remove_fraction: % of nodes to remove
    :return: x (% removed), y (largest connected component size)
    """
    G = graph.copy()
    N = len(G.nodes())
    num_remove = int(remove_fraction * N)
    x_vals, y_vals = [], []

    if strategy == "random":
        node_order = random.sample(list(G.nodes()), num_remove)
    elif strategy == "targeted":
        node_order = sorted(G.degree, key=lambda x: x[1], reverse=True)
        node_order = [n for n, _ in node_order[:num_remove]]
    else:
        raise ValueError("Invalid strategy")

    for i in range(num_remove):
        G.remove_node(node_order[i])
        if len(G) == 0:
            lcc = 0
        else:
            lcc = len(max(nx.connected_components(G), key=len))
        x_vals.append((i + 1) / N)
        y_vals.append(lcc / N)

    return x_vals, y_vals

# Simulate both attacks
x_rand, y_rand = simulate_attack(G_connected, strategy="random", remove_fraction=1)
x_target, y_target = simulate_attack(G_connected, strategy="targeted", remove_fraction=1)

# Plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x_rand, y_rand, label="Random Attack", color="blue", linestyle="--", marker='o', markersize=4)
ax.plot(x_target, y_target, label="Targeted Attack", color="red", linestyle="-", marker='x', markersize=4)
ax.set_xlabel("Fraction of Nodes Removed")
ax.set_ylabel("Size of Largest Connected Component (Fraction)")
ax.set_title("Impact of Random vs Targeted Attacks on Network Robustness")
ax.legend()
st.pyplot(fig)

# EDGE REMOVAL BY OVERLAP (LOW TO HIGH AND HIGH TO LOW)
st.markdown("## Network Robustness: Edge Removal by Overlap (Low to High vs High to Low)")

def edge_overlap_removal(graph, remove_fraction=1, ascending=True):
    """
    Removes edges by overlap score, either from low to high (ascending=True)
    or from high to low (ascending=False), tracking largest connected component size.
    """
    G = graph.copy()
    N = len(G.nodes())
    E = len(G.edges())
    num_remove = int(remove_fraction * E)
    x_vals, y_vals = [], []

    # Compute edge overlap
    overlap_scores = {}
    for u, v in G.edges():
        neighbors_u = set(G.neighbors(u))
        neighbors_v = set(G.neighbors(v))
        common = neighbors_u & neighbors_v
        union = neighbors_u | neighbors_v
        overlap = len(common) / len(union) if union else 0
        # Sort edge tuple so keys are consistent (undirected graph)
        edge = (u, v) if u < v else (v, u)
        overlap_scores[edge] = overlap

    # Sort edges by overlap ascending or descending
    sorted_edges = sorted(overlap_scores.items(), key=lambda x: x[1], reverse=not ascending)

    for i in range(num_remove):
        if i >= len(sorted_edges):
            break
        edge = sorted_edges[i][0]
        if G.has_edge(*edge):
            G.remove_edge(*edge)
        if nx.is_connected(G):
            lcc = len(G.nodes())
        else:
            lcc = len(max(nx.connected_components(G), key=len))
        x_vals.append((i + 1) / E)
        y_vals.append(lcc / N)

    return x_vals, y_vals

# Run both simulations
x_low, y_low = edge_overlap_removal(G_connected, remove_fraction=1, ascending=True)
x_high, y_high = edge_overlap_removal(G_connected, remove_fraction=1, ascending=False)

# Plot both on same figure
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x_low, y_low, color="purple", linestyle="-.", marker='s', markersize=4, label="Low-Overlap Removal (Low to High)")
ax.plot(x_high, y_high, color="green", linestyle="--", marker='D', markersize=4, label="High-Overlap Removal (High to Low)")
ax.set_xlabel("Fraction of Edges Removed")
ax.set_ylabel("Size of Largest Connected Component (Fraction)")
ax.set_title("Impact of Edge Removal by Overlap (Low to High vs High to Low)")
ax.legend()
st.pyplot(fig)