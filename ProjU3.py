import streamlit as st
import pandas as pd
from pyvis.network import Network
import networkx as nx
import community as community_louvain  # for Louvain clustering
import tempfile
import os
import streamlit.components.v1 as components

# Streamlit setup
st.set_page_config(page_title="Marvel Network Enhanced", layout="wide")
st.title("Marvel Character Network with Clustering and Hub Highlighting")

@st.cache_data
def load_data():
    return pd.read_csv("marvel-unimodal-edges.csv")

df = load_data()

# Validate columns
if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

# Limit edges checkbox
limit_edges = st.checkbox("Limit to first 1000 edges (faster rendering)", True)
if limit_edges:
    df = df.head(1000)

# Create a NetworkX graph for analysis
G = nx.from_pandas_edgelist(df, source='Source', target='Target', edge_attr='Weight', create_using=nx.Graph())

# Compute Louvain communities for clustering
partition = community_louvain.best_partition(G)

# Compute degree centrality for hub highlighting
degree_dict = dict(G.degree())

# Normalize degree centrality for scaling node size/color
max_degree = max(degree_dict.values()) if degree_dict else 1

# Initialize Pyvis network
net = Network(height='850px', width='100%', notebook=False, cdn_resources='remote')

# Add nodes with cluster and hub info
for node in G.nodes():
    community_id = partition[node]
    deg = degree_dict[node]
    size = 15 + (deg / max_degree) * 30  # size scaled between 15 and 45

    # Color nodes by community cluster
    # Use a color palette (here, simple list, can expand)
    palette = [
        "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
        "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
        "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
    ]
    color = palette[community_id % len(palette)]

    net.add_node(
        node,
        label=node,
        title=f"Community: {community_id}<br>Degree: {deg}",
        color=color,
        size=size,
        font={"size": 22, "face": "arial", "multi": "md", "align": "center"},
        shape="dot"
    )

# Add edges with smooth curved style for clarity
for source, target, data in G.edges(data=True):
    weight = data.get('Weight', 1)
    net.add_edge(
        source,
        target,
        value=weight,
        smooth={"enabled": True, "type": "curvedCW"}  # curved clockwise edges
    )

# Set physics with repulsion solver and settings to reduce overlap and spinning
custom_options = """
var options = {
  "nodes": {
    "scaling": {"min": 10, "max": 45}
  },
  "edges": {
    "color": {"inherit": true},
    "smooth": {"enabled": true, "type": "curvedCW", "roundness": 0.15}
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

# Save graph to temporary file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    net.save_graph(path)

# JavaScript to disable physics after stabilization, re-enable on drag
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

# Read the saved HTML, inject custom JS before </body>
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Display in Streamlit
st.subheader("Interactive Network Graph with Clusters and Hub Highlighting")
components.html(html_content, height=900, scrolling=True)

# Clean up temp file
os.unlink(path)
