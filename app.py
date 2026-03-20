# # --------------------------------------------------
# # Simple PDF Merger - Streamlit
# # --------------------------------------------------

# import streamlit as st
# from pypdf import PdfMerger
# import io

# st.set_page_config(page_title="PDF Merger", layout="centered")

# st.title("📄 PDF Merger")
# st.write("Upload multiple PDFs and merge them into one file.")

# # Upload PDFs
# uploaded_files = st.file_uploader(
#     "Upload PDF files",
#     type="pdf",
#     accept_multiple_files=True
# )

# if uploaded_files:
#     st.success(f"{len(uploaded_files)} files uploaded")

#     if st.button("🔗 Merge PDFs"):
#         merger = PdfMerger()

#         for file in uploaded_files:
#             merger.append(file)

#         # Save to memory (no temp files needed)
#         output = io.BytesIO()
#         merger.write(output)
#         merger.close()
#         output.seek(0)

#         # Download
#         st.download_button(
#             label="📥 Download Merged PDF",
#             data=output,
#             file_name="merged_packet.pdf",
#             mime="application/pdf"
#         )

#         st.success("✅ Done!")

import streamlit as st
from pypdf import PdfReader, PdfWriter
import io

st.title("PDF Merger")

uploaded_files = st.file_uploader(
    "Upload PDFs",
    type="pdf",
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Merge PDFs"):

        writer = PdfWriter()

        for file in uploaded_files:
            try:
                reader = PdfReader(file)
                for page in reader.pages:
                    writer.add_page(page)
            except Exception as e:
                st.warning(f"Skipped {file.name}: {e}")

        output = io.BytesIO()
        writer.write(output)
        output.seek(0)

        st.download_button(
            "Download Merged PDF",
            data=output,
            file_name="merged_packet.pdf",
            mime="application/pdf"
        )

        st.success("Done!")