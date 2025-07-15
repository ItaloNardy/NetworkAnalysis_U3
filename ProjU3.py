import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
from pathlib import Path
import streamlit.components.v1 as components

# Streamlit setup
st.set_page_config(page_title="Marvel Network", layout="wide")
st.title("Marvel Character Network (from GitHub CSV)")

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
limit_nodes = st.checkbox("Limit graph to first 1000 edges (for faster preview)", value=True)
if limit_nodes:
    df = df.head(1000)

# Create Pyvis network
marvel_net = Network(height='850px', width='100%', notebook=False, cdn_resources='remote')

# Add nodes and edges
for _, row in df.iterrows():
    src, dst, w = row['Source'], row['Target'], row['Weight']
    marvel_net.add_node(src, label=src, title=src)
    marvel_net.add_node(dst, label=dst, title=dst)
    marvel_net.add_edge(src, dst, value=w)

# Add neighbor info to hover text and set node size by degree
neighbor_map = marvel_net.get_adj_list()
for node in marvel_net.nodes:
    degree = len(neighbor_map[node["id"]])
    node["title"] += " Neighbors:<br>" + "<br>".join(neighbor_map[node["id"]])
    node["value"] = degree

# Set layout options with repulsion solver and optimized label spacing
custom_options = """
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
      "max": 40
    },
    "shape": "dot"
  },
  "edges": {
    "color": {
      "inherit": true
    },
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
marvel_net.set_options(custom_options)

# Save to temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Inject JS: disable physics after stabilization, re-enable on drag
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

# Inject JS into HTML
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Display in Streamlit
st.subheader("Interactive Network Graph")
components.html(html_content, height=900, scrolling=True)

# Cleanup
os.unlink(path)
