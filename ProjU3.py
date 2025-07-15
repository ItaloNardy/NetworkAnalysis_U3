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
    # Load CSV file from local directory (assumed pulled from GitHub)
    df = pd.read_csv("marvel-unimodal-edges.csv")
    return df

# Load and preview data
df = load_data()

# Validate required columns
if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
    st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    st.stop()

# Toggle to limit nodes
limit_nodes = st.checkbox("Limit graph to 100 rows (for faster rendering)", value=True)

# Limit dataset if checkbox is checked
if limit_nodes:
    df = df.head(100)

# Create Pyvis network
marvel_net = Network(height='800px', width='100%', notebook=False, cdn_resources='remote')
marvel_net.barnes_hut()

# Add nodes and edges from the DataFrame
for _, row in df.iterrows():
    src, dst, w = row['Source'], row['Target'], row['Weight']
    marvel_net.add_node(src, label=src, title=src)
    marvel_net.add_node(dst, label=dst, title=dst)
    marvel_net.add_edge(src, dst, value=w)

# Add neighbor data to node hover info
neighbor_map = marvel_net.get_adj_list()
for node in marvel_net.nodes:
    node["title"] += " Neighbors:<br>" + "<br>".join(neighbor_map[node["id"]])
    node["value"] = len(neighbor_map[node["id"]])

# Graph layout settings
marvel_net.repulsion()
marvel_net.show_buttons(filter_=['physics'])

# Save the graph to a temporary HTML file
with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
    path = tmp_file.name
    marvel_net.save_graph(path)

# Load the HTML content
with open(path, 'r', encoding='utf-8') as f:
    html_content = f.read()

# Display in Streamlit
st.subheader("Interactive Network Graph")
components.html(html_content, height=850, scrolling=True)

# Clean up temporary file
os.unlink(path)
