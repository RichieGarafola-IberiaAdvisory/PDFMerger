from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Sequence

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True, slots=True)
class UploadLimits:
    max_file_count: int = 25
    max_file_size_bytes: int = 25 * 1024 * 1024
    max_total_size_bytes: int = 100 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PdfSource:
    name: str
    content: bytes

    @property
    def display_name(self) -> str:
        return self.name.strip() or "unnamed.pdf"

    @property
    def size_bytes(self) -> int:
        return len(self.content)


@dataclass(frozen=True, slots=True)
class PdfIssue:
    file_name: str
    message: str


@dataclass(frozen=True, slots=True)
class PdfMergeResult:
    content: bytes
    total_pages: int
    merged_files: tuple[str, ...]
    skipped_files: tuple[PdfIssue, ...]
    input_size_bytes: int

    @property
    def output_size_bytes(self) -> int:
        return len(self.content)


class PdfServiceError(Exception):
    """Base class for PDF processing errors."""


class PdfValidationError(PdfServiceError):
    """Raised when an upload batch violates app limits."""


class PdfMergeError(PdfServiceError):
    """Raised when a merge cannot produce a valid output file."""


def merge_pdfs(
    sources: Sequence[PdfSource],
    *,
    limits: UploadLimits | None = None,
) -> PdfMergeResult:
    active_limits = limits or UploadLimits()
    validate_source_batch(sources, active_limits)

    writer = PdfWriter()
    merged_files: list[str] = []
    skipped_files: list[PdfIssue] = []
    total_pages = 0
    input_size_bytes = sum(source.size_bytes for source in sources)

    try:
        for source in sources:
            issue = validate_source(source, active_limits)
            if issue is not None:
                skipped_files.append(issue)
                continue

            try:
                reader = PdfReader(BytesIO(source.content), strict=False)
                if reader.is_encrypted:
                    skipped_files.append(
                        PdfIssue(
                            file_name=source.display_name,
                            message="Encrypted PDFs are not supported.",
                        )
                    )
                    continue

                page_count = len(reader.pages)
                if page_count == 0:
                    skipped_files.append(
                        PdfIssue(
                            file_name=source.display_name,
                            message="PDF has no pages.",
                        )
                    )
                    continue

                for page in reader.pages:
                    writer.add_page(page)

                merged_files.append(source.display_name)
                total_pages += page_count
            except Exception as exc:
                skipped_files.append(
                    PdfIssue(
                        file_name=source.display_name,
                        message=friendly_pdf_error(exc),
                    )
                )

        if not merged_files:
            raise PdfMergeError(
                "No valid PDF files were available to merge. "
                "Upload readable, unencrypted PDF files and try again."
            )

        output = BytesIO()
        writer.write(output)
        return PdfMergeResult(
            content=output.getvalue(),
            total_pages=total_pages,
            merged_files=tuple(merged_files),
            skipped_files=tuple(skipped_files),
            input_size_bytes=input_size_bytes,
        )
    except PdfServiceError:
        raise
    except Exception as exc:
        raise PdfMergeError(f"PDF merge failed: {friendly_pdf_error(exc)}") from exc
    finally:
        writer.close()


def validate_source_batch(sources: Sequence[PdfSource], limits: UploadLimits) -> None:
    if not sources:
        raise PdfValidationError("Upload at least one PDF file before merging.")

    if len(sources) > limits.max_file_count:
        raise PdfValidationError(
            f"Too many files uploaded. The limit is {limits.max_file_count} files per merge."
        )

    total_size = sum(source.size_bytes for source in sources)
    if total_size > limits.max_total_size_bytes:
        raise PdfValidationError(
            "Total upload size exceeds the app limit of "
            f"{limits.max_total_size_bytes // (1024 * 1024)} MB."
        )


def validate_source(source: PdfSource, limits: UploadLimits) -> PdfIssue | None:
    if not source.display_name.lower().endswith(".pdf"):
        return PdfIssue(
            file_name=source.display_name,
            message="File extension must be .pdf.",
        )

    if source.size_bytes == 0:
        return PdfIssue(file_name=source.display_name, message="File is empty.")

    if source.size_bytes > limits.max_file_size_bytes:
        return PdfIssue(
            file_name=source.display_name,
            message=(
                "File exceeds the per-file limit of "
                f"{limits.max_file_size_bytes // (1024 * 1024)} MB."
            ),
        )

    return None


def friendly_pdf_error(exc: Exception) -> str:
    raw_message = " ".join(str(exc).split()).strip()
    lowered = raw_message.lower()

    if "password" in lowered or "encrypted" in lowered:
        return "Encrypted PDFs are not supported."

    if "eof marker" in lowered or "startxref" in lowered:
        return "File is not a valid PDF or is truncated."

    if "cannot read an empty file" in lowered:
        return "File is empty."

    if not raw_message:
        return "Unreadable or unsupported PDF."

    return raw_message[:200]
