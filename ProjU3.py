import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import streamlit.components.v1 as components

# Louvain
try:
    import community as community_louvain
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-louvain"])
    import community as community_louvain

import networkx as nx

# Page config
st.set_page_config(page_title="Marvel Network", layout="wide")
st.title("Marvel Network (Dim Unconnected Nodes on Click)")

@st.cache_data
def load_data():
    return pd.read_csv("marvel-unimodal-edges.csv")

df = load_data()

if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

# Reduce graph if needed
if st.checkbox("Limit to 1000 edges", value=True):
    df = df.head(1000)

# Build graph
G = nx.from_pandas_edgelist(df, 'Source', 'Target', edge_attr='Weight')
partition = community_louvain.best_partition(G)
degree = dict(G.degree())
max_deg = max(degree.values()) if degree else 1

palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
]

net = Network(height="850px", width="100%", notebook=False, cdn_resources="remote")

# Add nodes with color and size
for node in G.nodes():
    comm = partition.get(node, 0)
    deg = degree.get(node, 1)
    net.add_node(
        node,
        label=node,
        color=palette[comm % len(palette)],
        size=15 + (deg / max_deg) * 35,
        title=f"Community: {comm} | Degree: {deg}"
    )

# Add edges
for _, row in df.iterrows():
    net.add_edge(row["Source"], row["Target"], value=row["Weight"])

# Base Pyvis options
net.set_options("""
{
  "nodes": {
    "font": {"size": 22, "face": "arial"},
    "shape": "dot",
    "scaling": {"min": 10, "max": 45}
  },
  "edges": {
    "color": {"inherit": true},
    "smooth": false
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 50,
    "dragNodes": true,
    "dragView": true,
    "zoomView": true,
    "selectConnectedEdges": true,
    "highlightNearest": {
      "enabled": true,
      "degree": 1,
      "hover": false
    }
  },
  "physics": {
    "solver": "repulsion",
    "repulsion": {
      "centralGravity": 0.15,
      "springLength": 300,
      "springConstant": 0.01,
      "nodeDistance": 220,
      "damping": 0.15
    },
    "stabilization": {
      "iterations": 250
    }
  }
}
""")

# Save to HTML file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    net.save_graph(path)

# Inject JavaScript to DIM unconnected nodes
custom_js = """
<script type="text/javascript">
function enableDimOnClick() {
  var allNodes = network.body.nodes;
  var nodeData = network.body.data.nodes;

  network.on("click", function (params) {
    if (params.nodes.length === 0) {
      // No node selected, reset all opacities
      nodeData.update(
        nodeData.get().map(function(n) {
          return { id: n.id, color: { opacity: 1.0 }};
        })
      );
      return;
    }

    var selected = params.nodes[0];
    var connected = network.getConnectedNodes(selected);
    connected.push(selected);

    nodeData.update(
      nodeData.get().map(function(n) {
        return {
          id: n.id,
          color: {
            background: n.color.background || n.color,
            border: n.color.border || n.color,
            opacity: connected.includes(n.id) ? 1.0 : 0.2
          }
        };
      })
    );
  });
}

function controlPhysics() {
  network.once('stabilizationIterationsDone', () => network.setOptions({ physics: false }));
  network.on("dragStart", () => network.setOptions({ physics: true }));
  network.on("dragEnd", () => setTimeout(() => network.setOptions({ physics: false }), 300));
}

if (typeof network !== "undefined") {
  enableDimOnClick();
  controlPhysics();
} else {
  setTimeout(() => {
    enableDimOnClick();
    controlPhysics();
  }, 1000);
}
</script>
"""

# Inject JS
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace("</body>", custom_js + "\n</body>")

# Show in Streamlit
st.subheader("Interactive Network Graph")
components.html(html, height=900, scrolling=True)

# Clean up
os.unlink(path)
