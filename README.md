# PDF Packet Builder

PDF Packet Builder is a Streamlit application for merging multiple PDF files into a single downloadable packet. The repository is structured so the Streamlit entrypoint stays thin while reusable merge logic lives in a service layer that can later be called from automation jobs, APIs, or background workers.

## Project structure

```text
MergePDF/
|-- app.py
|-- services/
|   |-- __init__.py
|   `-- pdf_service.py
|-- tests/
|   `-- test_pdf_service.py
|-- utils/
|   |-- __init__.py
|   `-- file_utils.py
|-- .dockerignore
|-- .gitignore
|-- Dockerfile
|-- README.md
`-- requirements.txt
```

## Why this structure

- `app.py` contains Streamlit UI only.
- `services/pdf_service.py` owns validation, merge behavior, and error handling.
- `utils/file_utils.py` contains reusable filename and formatting helpers.
- `tests/test_pdf_service.py` covers the merge path without depending on Streamlit.

## Runtime requirements

- Python 3.10 or newer
- `streamlit`
- `pypdf`

## Local setup

1. Create and activate a virtual environment.

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS or Linux:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies.

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. Start the app.

   ```bash
   streamlit run app.py
   ```

## How to use the app

1. Upload one or more PDF files.
2. Keep the files in the order you want them merged.
3. Set the output filename.
4. Click `Merge PDFs`.
5. Download the merged packet.

If a file is unreadable, encrypted, empty, oversized, or malformed, the app skips it and reports the reason in the UI. If every file fails validation or parsing, the app stops and returns a clear error instead of generating an empty output.

## Operational limits

The default app limits are intentionally conservative to protect Streamlit memory usage:

- Maximum files per merge: 25
- Maximum size per file: 25 MB
- Maximum total upload size: 100 MB

For much larger workloads, move merge execution to a worker or API tier and process from durable storage instead of keeping the entire job in Streamlit memory.

## Testing

Run the service-layer tests with:

```bash
python -m unittest discover -s tests
```

## Streamlit Community Cloud deployment

1. Push the repository to GitHub.
2. Create a new Streamlit Community Cloud app pointing at `app.py`.
3. Ensure `requirements.txt` is present in the repository root.
4. Deploy.

No changes are required for Streamlit Community Cloud beyond the runtime dependencies and root entrypoint already included in this repository.

## Docker deployment

Build and run locally:

```bash
docker build -t pdf-packet-builder .
docker run --rm -p 8501:8501 pdf-packet-builder
```

The container exposes Streamlit on port `8501`.

## Next integration step

Because merge logic is isolated in `services/pdf_service.py`, the same service can be imported later by a scheduler, API endpoint, or automation worker without duplicating Streamlit UI code.
