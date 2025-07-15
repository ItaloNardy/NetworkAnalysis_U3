import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os
from pathlib import Path
import streamlit.components.v1 as components

# Set Streamlit page config
st.set_page_config(page_title="Marvel Network", layout="wide")

# Title
st.title("Marvel Character Network Visualization")

# Upload CSV file
uploaded_file = st.file_uploader("Upload Edge List CSV", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Validate required columns
    if not {'Source', 'Target', 'Weight'}.issubset(df.columns):
        st.error("CSV must contain 'Source', 'Target', and 'Weight' columns.")
    else:
        # Create a Pyvis Network object
        marvel_net = Network(height='800px', width='100%', heading='', notebook=False, cdn_resources='remote')
        marvel_net.barnes_hut()

        # Add edges and nodes
        for _, row in df.iterrows():
            src, dst, w = row['Source'], row['Target'], row['Weight']
            marvel_net.add_node(src, label=src, title=src)
            marvel_net.add_node(dst, label=dst, title=dst)
            marvel_net.add_edge(src, dst, value=w)

        # Build neighbor map
        neighbor_map = marvel_net.get_adj_list()

        # Enrich nodes with neighbor info
        for node in marvel_net.nodes:
            node["title"] += " Neighbors:<br>" + "<br>".join(neighbor_map[node["id"]])
            node["value"] = len(neighbor_map[node["id"]])

        marvel_net.repulsion()
        marvel_net.show_buttons(filter_=['physics'])

        # Save to a temporary HTML file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
            path = tmp_file.name
            marvel_net.show(path)

        # Read HTML and display in Streamlit
        with open(path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        st.subheader("Interactive Network Graph")
        components.html(html_content, height=850, scrolling=True)

        # Cleanup temp file
        os.unlink(path)
else:
    st.info("Please upload a .csv file with columns: Source, Target, Weight.")
