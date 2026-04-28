import streamlit as st
import requests

# Page config
st.set_page_config(page_title="Visual Search", layout="wide")

# Title
st.title("🔍 Visual Search System")

# Upload image
uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # Show uploaded image
    st.image(uploaded_file, caption="Uploaded Image", width=300)

    # Prepare file for backend
    files = {
        "file": (uploaded_file.name, uploaded_file, uploaded_file.type)
    }

    # Call backend with loading spinner
    with st.spinner("Searching for similar images..."):
        try:
            response = requests.post(
                "http://127.0.0.1:8000/search",
                files=files
            )

            if response.status_code != 200:
                st.error("❌ Backend error. Please check server.")
            else:
                results = response.json()

                st.subheader("Results:")

                # Create grid layout (3 columns)
                cols = st.columns(3)

                for i, item in enumerate(results):
                    with cols[i % 3]:
                        st.image(item["image"], width=150)
                        st.write(f"Score: {item['score']:.2f}")

        except Exception as e:
            st.error(f"⚠️ Error: {e}")