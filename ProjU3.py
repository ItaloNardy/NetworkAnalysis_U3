import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import community as community_louvain  # make sure `python-louvain` is installed
import tempfile
import os
import streamlit.components.v1 as components

# Streamlit setup
st.set_page_config(page_title="Marvel Network Debug View", layout="wide")
st.title("Marvel Character Network with Debugging")

# Load data
@st.cache_data
def load_data():
    return pd.read_csv("marvel-unimodal-edges.csv")

df = load_data()

# Validate CSV columns
required_cols = {'Source', 'Target', 'Weight'}
if not required_cols.issubset(df.columns):
    st.error(f"CSV must include columns: {required_cols}")
    st.stop()

# Limit size for performance
limit = st.checkbox("Limit to 1000 edges (recommended)", value=True)
if limit:
    df = df.head(1000)

# Build NetworkX graph
G = nx.from_pandas_edgelist(df, source='Source', target='Target', edge_attr='Weight', create_using=nx.Graph())

# Compute communities using Louvain
try:
    partition = community_louvain.best_partition(G)
    st.success("Louvain clustering succeeded")
except Exception as e:
    st.error(f"Louvain clustering failed: {e}")
    partition = {node: 0 for node in G.nodes()}  # fallback: single cluster

# Compute degree centrality
degree_dict = dict(G.degree())
max_degree = max(degree_dict.values()) if degree_dict else 1

st.write("Number of communities detected:", len(set(partition.values())))
st.write("Max degree found:", max_degree)

# Initialize Pyvis network
net = Network(height="850px", width="100%", notebook=False, cdn_resources="remote")

# Color palette (expandable)
palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
]

# Add nodes
for node in G.nodes():
    community_id = partition.get(node, 0)
    degree = degree_dict.get(node, 1)
    size = 15 + (degree / max_degree) * 30
    color = palette[community_id % len(palette)]

    net.add_node(
        node,
        label=node,
        title=f"Community: {community_id}<br>Degree: {degree}",
        color=color,
        size=size,
        shape="dot",
        font={"size": 22, "face": "arial", "multi": "md", "align": "center"}
    )

# Add curved edges
for source, target, data in G.edges(data=True):
    weight = data.get("Weight", 1)
    net.add_edge(
        source,
        target,
        value=weight,
        smooth={"enabled": True, "type": "curvedCW"}
    )

# Set physics & layout options
custom_options = """
var options = {
  "nodes": {
    "scaling": {"min": 10, "max": 45}
  },
  "edges": {
    "smooth": {"enabled": true, "type": "curvedCW", "roundness": 0.2},
    "color": {"inherit": true}
  },
  "physics": {
    "enabled": true,
    "solver": "repulsion",
    "repulsion": {
      "centralGravity": 0.15,
      "springLength": 250,
      "springConstant": 0.01,
      "nodeDistance": 200,
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
    "hideEdgesOnDrag": true,
    "zoomView": true,
    "dragNodes": true,
    "dragView": true,
    "selectConnectedEdges": true
  }
}
"""
net.set_options(custom_options)

# Save and display graph
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    net.save_graph(path)

# Inject JS to toggle physics on drag
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

with open(path, "r", encoding="utf-8") as f:
    html_content = f.read()

# Inject JS
if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Display
st.subheader("Interactive Network Graph")
components.html(html_content, height=900, scrolling=True)

# Cleanup
os.unlink(path)
