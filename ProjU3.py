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
marvel_net = Network(height='800px', width='100%', notebook=False, cdn_resources='remote')

# Add nodes and edges
for _, row in df.iterrows():
    src, dst, w = row['Source'], row['Target'], row['Weight']
    marvel_net.add_node(src, label=src, title=src)
    marvel_net.add_node(dst, label=dst, title=dst)
    marvel_net.add_edge(src, dst, value=w)

# Add neighbor info to hover text
neighbor_map = marvel_net.get_adj_list()
for node in marvel_net.nodes:
    node["title"] += " Neighbors:<br>" + "<br>".join(neighbor_map[node["id"]])
    node["value"] = len(neighbor_map[node["id"]])

# Set visual options for readability and stable layout
custom_options = """
var options = {
  "nodes": {
    "font": {
      "size": 20,
      "face": "arial",
      "align": "center"
    },
    "scaling": {
      "min": 5,
      "max": 30
    }
  },
  "edges": {
    "color": {
      "inherit": true
    },
    "smooth": false
  },
  "physics": {
    "enabled": true,
    "solver": "forceAtlas2Based",
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "springLength": 100,
      "springConstant": 0.08,
      "centralGravity": 0.005
    },
    "timestep": 0.35,
    "minVelocity": 0.75,
    "stabilization": {
      "enabled": true,
      "iterations": 150,
      "updateInterval": 30,
      "onlyDynamicEdges": false,
      "fit": true
    }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 50,
    "hideEdgesOnDrag": true,
    "zoomView": true,
    "dragNodes": true,
    "dragView": true
  }
}
"""
marvel_net.set_options(custom_options)

# Save to temp file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Inject JavaScript to stop physics after layout, re-enable on drag
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

# Read, inject JS, and display in Streamlit
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Inject JS before closing </body> or </html>
if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Show in Streamlit
st.subheader("Interactive Network Graph")
components.html(html_content, height=850, scrolling=True)

# Clean up temp file
os.unlink(path)
