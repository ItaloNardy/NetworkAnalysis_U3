# GRAPH

import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
import streamlit.components.v1 as components

# Louvain community detection
try:
    import community as community_louvain
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-louvain"])
    import community as community_louvain

import networkx as nx

st.set_page_config(page_title="Marvel Network with Label Outline", layout="wide")
st.title("Marvel Character Network with Clustering & Label Outline on Highlight")

@st.cache_data
def load_data():
    return pd.read_csv("marvel-unimodal-edges.csv")

df = load_data()

if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

limit_nodes = st.checkbox("Limit graph to first 1000 edges (for faster preview)", value=True)
if limit_nodes:
    df = df.head(1000)

G = nx.from_pandas_edgelist(df, source='Source', target='Target', edge_attr='Weight')
partition = community_louvain.best_partition(G)
degree_dict = dict(G.degree())
max_degree = max(degree_dict.values()) if degree_dict else 1

palette = [
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231",
    "#911eb4", "#46f0f0", "#f032e6", "#bcf60c", "#fabebe",
    "#008080", "#e6beff", "#9a6324", "#fffac8", "#800000"
]

net = Network(height='850px', width='100%', notebook=False, cdn_resources='remote')

# Add nodes with HTML labels that wrap the node id in a span for CSS targeting
for node in G.nodes():
    community_id = partition.get(node, 0)
    degree = degree_dict.get(node, 1)
    size = 15 + (degree / max_degree) * 35
    color = palette[community_id % len(palette)]

    # HTML label with span class "node-label"
    label_html = f'<span class="node-label">{node}</span>'

    net.add_node(
        node,
        label=label_html,
        title=f"Community: {community_id}<br>Degree: {degree}",
        color=color,
        size=size,
        shape="dot",
        font={"multi": "html"}  # Enable HTML in labels!
    )

for _, row in df.iterrows():
    src, dst, w = row['Source'], row['Target'], row['Weight']
    net.add_edge(src, dst, value=w)

net.set_options("""
var options = {
  "nodes": {
    "font": {
      "size": 22,
      "face": "arial",
      "multi": "html",
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

with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    net.save_graph(path)

# CSS: default label style + highlighted label style with white outline (text-shadow)
css_style = """
<style>
.node-label {
  color: black;
  text-shadow:
    -1px -1px 0 white,
    1px -1px 0 white,
    -1px  1px 0 white,
    1px  1px 0 white;
  transition: all 0.3s ease;
}
.highlighted-label {
  color: black;
  font-weight: bold;
  text-shadow:
    -2px -2px 0 white,
    2px -2px 0 white,
    -2px  2px 0 white,
    2px  2px 0 white,
    0 0 5px white;
}
.dimmed-label {
  color: #bbb;
  text-shadow: none;
  font-weight: normal;
}
</style>
"""

# JS: On node select highlight that node & neighbors label with .highlighted-label class,
# others get .dimmed-label class to visually dim
js_script = """
<script type="text/javascript">
  function setupLabelHighlighting() {
    function updateLabels(selectedNodes) {
      var allNodes = network.body.nodes;
      var connectedNodes = new Set();

      selectedNodes.forEach(function(nodeId) {
        connectedNodes.add(nodeId);
        var nodeObj = network.body.nodes[nodeId];
        if(nodeObj) {
          var neighbors = network.getConnectedNodes(nodeId);
          neighbors.forEach(function(n) { connectedNodes.add(n); });
        }
      });

      // Update labels
      for (const nodeId in allNodes) {
        var node = allNodes[nodeId];
        var labelElem = document.querySelector("[data-id='" + nodeId + "'] .node-label");
        if(!labelElem) continue;
        if(connectedNodes.has(nodeId)) {
          labelElem.classList.add("highlighted-label");
          labelElem.classList.remove("dimmed-label");
        } else {
          labelElem.classList.remove("highlighted-label");
          labelElem.classList.add("dimmed-label");
        }
      }
    }

    network.on("selectNode", function(params) {
      updateLabels(params.nodes);
    });

    network.on("deselectNode", function() {
      // Reset all labels
      var allLabels = document.querySelectorAll(".node-label");
      allLabels.forEach(function(label) {
        label.classList.remove("highlighted-label");
        label.classList.remove("dimmed-label");
      });
    });
  }

  if(typeof network !== "undefined") {
    setupLabelHighlighting();
  } else {
    setTimeout(setupLabelHighlighting, 1000);
  }
</script>
"""

with open(path, 'r', encoding='utf-8') as f:
    html = f.read()

# Inject CSS before </head>
if "</head>" in html:
    html = html.replace("</head>", css_style + "\n</head>")
else:
    html = css_style + html

# Inject JS before </body>
if "</body>" in html:
    html = html.replace("</body>", js_script + "\n</body>")
else:
    html += js_script

st.subheader("Interactive Network Graph")
components.html(html, height=900, scrolling=True)

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
st.markdown("### Adjacency Matrix")
st.dataframe(adj_df.style.format("{:.0f}"))

# Diameter
diameter = nx.diameter(G_connected)
st.markdown(f"### Diameter of the connected network: **{diameter}**")

# Periphery nodes
periphery_nodes = list(nx.periphery(G_connected))
st.markdown(f"### Periphery Nodes ({len(periphery_nodes)} nodes):")
st.write(periphery_nodes)
