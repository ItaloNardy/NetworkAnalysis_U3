import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import streamlit.components.v1 as components

# Install Louvain if needed
try:
    import community as community_louvain
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-louvain"])
    import community as community_louvain

import networkx as nx

# Setup Streamlit
st.set_page_config(page_title="Marvel Network", layout="wide")
st.title("Marvel Network with Clustering and Interactive Filtering")

@st.cache_data
def load_data():
    return pd.read_csv("marvel-unimodal-edges.csv")

df = load_data()

if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

# Option to limit size
limit = st.checkbox("Limit graph to first 1000 edges", value=True)
if limit:
    df = df.head(1000)

# NetworkX graph + Louvain
G = nx.from_pandas_edgelist(df, 'Source', 'Target', edge_attr='Weight')
partition = community_louvain.best_partition(G)
degree = dict(G.degree())
max_deg = max(degree.values()) if degree else 1

palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
]

# Pyvis network
net = Network(height="850px", width="100%", notebook=False, cdn_resources="remote")

# Add nodes with color and size
for node in G.nodes():
    c = partition.get(node, 0)
    d = degree.get(node, 1)
    net.add_node(
        node,
        label=node,
        color=palette[c % len(palette)],
        size=15 + (d / max_deg) * 35,
        title=f"Community: {c}<br>Degree: {d}",
        shape="dot",
        font={"size": 22, "face": "arial", "align": "center"}
    )

# Add edges
for _, row in df.iterrows():
    net.add_edge(row["Source"], row["Target"], value=row["Weight"])

# Custom options
net.set_options("""
var options = {
  "nodes": {
    "font": {"size": 22, "face": "arial"},
    "scaling": {"min": 10, "max": 45},
    "shape": "dot"
  },
  "edges": {
    "color": {"inherit": true},
    "smooth": false
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
    "stabilization": {"enabled": true, "iterations": 250}
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 50,
    "dragNodes": true,
    "dragView": true,
    "selectConnectedEdges": true
  }
}
""")

# Save to temporary file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    net.save_graph(path)

# Inject JS for interactive dimming
custom_js = """
<script type="text/javascript">
function highlightConnected() {
  network.on("click", function (params) {
    if (params.nodes.length === 0) {
      network.selectNodes([]);
      network.body.data.nodes.update(
        network.body.data.nodes.get().map(n => ({ id: n.id, hidden: false }))
      );
      return;
    }
    const selectedNode = params.nodes[0];
    const connectedNodes = network.getConnectedNodes(selectedNode);
    connectedNodes.push(selectedNode);
    const allNodes = network.body.data.nodes.get();
    network.body.data.nodes.update(
      allNodes.map(n => ({
        id: n.id,
        hidden: !connectedNodes.includes(n.id)
      }))
    );
  });
}

function controlPhysics() {
  network.once('stabilizationIterationsDone', () => network.setOptions({ physics: false }));
  network.on("dragStart", () => network.setOptions({ physics: true }));
  network.on("dragEnd", () => setTimeout(() => network.setOptions({ physics: false }), 300));
}

if (typeof network !== "undefined") {
  highlightConnected();
  controlPhysics();
} else {
  setTimeout(() => {
    highlightConnected();
    controlPhysics();
  }, 1000);
}
</script>
"""

# Inject JS
with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

if "</body>" in html:
    html = html.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html:
    html = html.replace("</html>", custom_js + "\n</html>")
else:
    html += custom_js

# Display in Streamlit
st.subheader("Interactive Network Graph")
components.html(html, height=900, scrolling=True)

# Clean up
os.unlink(path)
