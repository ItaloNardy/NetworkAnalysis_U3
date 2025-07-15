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
net.repulsion()

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
marvel_net.show_buttons(filter_=['physics'])

# Save to temp file and render in Streamlit
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Read and embed HTML
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

st.subheader("Interactive Network Graph")
components.html(html_content, height=850, scrolling=True)

# Cleanup temp file
os.unlink(path)
