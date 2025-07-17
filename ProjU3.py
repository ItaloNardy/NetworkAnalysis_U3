# GRAPH

import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import streamlit.components.v1 as components

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
st.title("Marvel Character Network with Clustering & Interactions")

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

# Toggle to limit graph size
limit_nodes500 = st.checkbox("Limit graph to first 500 edges (for faster preview)", value=True)
if limit_nodes500:
    df = df.head(500)
limit_nodes1000 = st.checkbox("Limit graph to first 1000 edges (for faster preview)", value=False)
if limit_nodes1000:
    df = df.head(1000)
limit_nodes3000 = st.checkbox("Limit graph to first 3000 edges (for faster preview)", value=False)
if limit_nodes3000:
    df = df.head(3000)
limit_nodes5000 = st.checkbox("Limit graph to first 5000 edges (for faster preview)", value=False)
if limit_nodes5000:
    df = df.head(5000)

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
st.subheader("Interactive Network Graph")
components.html(html_content, height=900, scrolling=True)

# Cleanup
os.unlink(path)

# METRICS

st.subheader("Network Analysis Metrics")

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
