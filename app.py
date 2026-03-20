from __future__ import annotations

import hashlib
from typing import Protocol, Sequence, cast

import streamlit as st

from services.pdf_service import (
    PdfMergeResult,
    PdfServiceError,
    PdfSource,
    UploadLimits,
    merge_pdfs,
)
from utils.file_utils import (
    DEFAULT_OUTPUT_FILENAME,
    format_file_size,
    sanitize_pdf_filename,
)

APP_TITLE = "PDF Packet Builder"
UPLOAD_LIMITS = UploadLimits(
    max_file_count=25,
    max_file_size_bytes=25 * 1024 * 1024,
    max_total_size_bytes=100 * 1024 * 1024,
)


class StreamlitUploadedFile(Protocol):
    name: str
    size: int

    def getvalue(self) -> bytes:
        ...


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)
    st.caption(
        "Upload PDF files in the order you want them merged. "
        "The app validates inputs, skips unreadable files, and produces a single download."
    )

    render_sidebar()

    raw_uploads = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload up to 25 PDF files. Upload order becomes merge order.",
    )
    output_name = st.text_input(
        "Output filename",
        value=DEFAULT_OUTPUT_FILENAME,
        help="A .pdf extension will be enforced automatically.",
    )

    if not raw_uploads:
        clear_merge_result()
        st.info("Upload at least one PDF file to start building a packet.")
        return

    uploaded_files = cast(Sequence[StreamlitUploadedFile], raw_uploads)
    if not validate_uploaded_file_batch(uploaded_files):
        clear_merge_result()
        return

    sources = build_pdf_sources(uploaded_files)
    upload_signature = build_upload_signature(sources)
    sync_merge_result(upload_signature)

    render_upload_summary(sources)

    if st.button("Merge PDFs", type="primary", use_container_width=True):
        with st.spinner("Merging PDFs..."):
            try:
                st.session_state["merge_result"] = merge_pdfs(
                    sources,
                    limits=UPLOAD_LIMITS,
                )
            except PdfServiceError as exc:
                st.session_state.pop("merge_result", None)
                st.error(str(exc))

    merge_result = st.session_state.get("merge_result")
    if isinstance(merge_result, PdfMergeResult):
        render_merge_result(merge_result, output_name)


def render_sidebar() -> None:
    st.sidebar.header("Limits")
    st.sidebar.write(f"Max files: {UPLOAD_LIMITS.max_file_count}")
    st.sidebar.write(
        f"Max size per file: {format_file_size(UPLOAD_LIMITS.max_file_size_bytes)}"
    )
    st.sidebar.write(
        "Max total upload size: "
        f"{format_file_size(UPLOAD_LIMITS.max_total_size_bytes)}"
    )
    st.sidebar.caption(
        "These guards reduce memory pressure and block oversized upload batches."
    )


def build_pdf_sources(uploaded_files: Sequence[StreamlitUploadedFile]) -> list[PdfSource]:
    return [PdfSource(name=file.name, content=file.getvalue()) for file in uploaded_files]


def validate_uploaded_file_batch(uploaded_files: Sequence[StreamlitUploadedFile]) -> bool:
    if len(uploaded_files) > UPLOAD_LIMITS.max_file_count:
        st.error(
            f"Too many files uploaded. The limit is {UPLOAD_LIMITS.max_file_count} files."
        )
        return False

    total_size = sum(file.size for file in uploaded_files)
    if total_size > UPLOAD_LIMITS.max_total_size_bytes:
        st.error(
            "Total upload size exceeds the app limit of "
            f"{format_file_size(UPLOAD_LIMITS.max_total_size_bytes)}."
        )
        return False

    return True


def build_upload_signature(sources: Sequence[PdfSource]) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (
            source.display_name,
            source.size_bytes,
            hashlib.sha256(source.content).hexdigest(),
        )
        for source in sources
    )


def render_upload_summary(sources: Sequence[PdfSource]) -> None:
    st.subheader("Upload summary")
    st.caption("Files will be merged in the order shown below.")

    for index, source in enumerate(sources, start=1):
        st.write(f"{index}. {source.display_name} ({format_file_size(source.size_bytes)})")

    total_size = sum(source.size_bytes for source in sources)
    st.caption(f"Total upload size: {format_file_size(total_size)}")


def render_merge_result(result: PdfMergeResult, output_name: str) -> None:
    safe_output_name = sanitize_pdf_filename(output_name)

    st.success(
        f"Merged {len(result.merged_files)} file(s) into {result.total_pages} page(s)."
    )
    st.download_button(
        label="Download merged PDF",
        data=result.content,
        file_name=safe_output_name,
        mime="application/pdf",
        use_container_width=True,
    )

    if result.skipped_files:
        st.warning("Some files were skipped during processing.")
        for issue in result.skipped_files:
            st.write(f"- {issue.file_name}: {issue.message}")

    st.caption(
        "Merged output size: "
        f"{format_file_size(result.output_size_bytes)} from "
        f"{format_file_size(result.input_size_bytes)} of uploaded data."
    )


def sync_merge_result(upload_signature: tuple[tuple[str, int, str], ...]) -> None:
    current_signature = st.session_state.get("upload_signature")
    if current_signature != upload_signature:
        st.session_state["upload_signature"] = upload_signature
        st.session_state.pop("merge_result", None)


def clear_merge_result() -> None:
    st.session_state.pop("merge_result", None)
    st.session_state.pop("upload_signature", None)


if __name__ == "__main__":
    main()
