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
    # Load CSV file from local repo or public GitHub clone
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

# Enhanced settings for large networks
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
    "forceAtlas2Based": {
      "gravitationalConstant": -50,
      "springLength": 100,
      "springConstant": 0.08,
      "centralGravity": 0.005
    },
    "minVelocity": 0.75,
    "solver": "forceAtlas2Based",
    "timestep": 0.35,
    "stabilization": {
      "iterations": 100
    }
  },
  "interaction": {
    "hover": true,
    "tooltipDelay": 50,
    "hideEdgesOnDrag": true,
    "zoomView": true
  }
}
"""
marvel_net.set_options(custom_options)

# Save to temp file and render in Streamlit
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Inject custom JS to disable physics after stabilization and re-enable on drag
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# JavaScript to stop physics after layout and re-enable during drag
custom_js = """
<script type="text/javascript">
  const originalInit = function() {
    network.once('stabilizationIterationsDone', function () {
      network.setOptions({ physics: false });
    });
    network.on("dragStart", function () {
      network.setOptions({ physics: true });
    });
    network.on("dragEnd", function () {
      setTimeout(() => network.setOptions({ physics: false }), 200);
    });
  };
  if (typeof network !== "undefined") {
    originalInit();
  } else {
    setTimeout(originalInit, 1000);
  }
</script>
"""

# Inject the script before </body> or </html>
if "</body>" in html_content:
    html_content = html_content.replace("</body>", custom_js + "\n</body>")
elif "</html>" in html_content:
    html_content = html_content.replace("</html>", custom_js + "\n</html>")
else:
    html_content += custom_js

# Read and embed HTML
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

st.subheader("Interactive Network Graph")
components.html(html_content, height=850, scrolling=True)

# Cleanup temp file
os.unlink(path)
