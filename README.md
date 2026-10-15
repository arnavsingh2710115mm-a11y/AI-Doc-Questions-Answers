# AI-Powered Document Question Answering System

**Live application:** https://ai-doc-questions-answers-cdhtiauopjdqnrqipajjeu.streamlit.app

**Source code:** https://github.com/arnavsingh2710115mm-a11y/AI-Doc-Questions-Answers


A student project that lets users upload a PDF and ask questions about its contents. The application uses Retrieval-Augmented Generation (RAG): ChromaDB finds relevant document passages, and Google Gemini uses those passages to generate an answer with filename and page citations.

The Streamlit interface includes a document upload workspace, processing status, question form, answer cards, and expandable views of extracted text and retrieved passages.

## Features

- Upload and extract text from a PDF with selectable text.
- Split text into overlapping chunks while preserving filenames and page numbers.
- Create embeddings and search for relevant passages with ChromaDB.
- Reuse the document index across questions instead of rebuilding embeddings.
- Generate document-grounded answers with Gemini, defaulting to `gemini-2.5-flash`.
- Show source pages beneath answers and citations within the generated response.
- Instruct the model to treat document text as reference data, ignore embedded instructions, and avoid unsupported answers.
- Handle unreadable PDFs, processing failures, missing API configuration, rate limits, and empty responses with user-facing messages.

## Technologies

| Technology | Purpose |
| --- | --- |
| Python | Application logic |
| Streamlit | Web interface |
| PyMuPDF | PDF text extraction |
| ChromaDB | Default embeddings and semantic retrieval |
| Google Gen AI SDK (`google-genai`) | Gemini answer generation |
| CSS and Streamlit theme configuration | Interface styling |

## How the RAG system works

1. PyMuPDF extracts text from each uploaded PDF page.
2. The application creates 800-character chunks with 150-character overlap, retaining each chunk's filename and page number.
3. ChromaDB's default embedding function embeds the chunks in a session-specific, in-memory collection.
4. When a question is submitted, ChromaDB retrieves up to three relevant chunks.
5. Gemini receives the question and retrieved context, with instructions to answer only from that context and cite supporting pages.
6. The interface displays the answer, context sources, and optional retrieved-chunk inspection.

When no context is retrieved, the application returns:

> I couldn't find that information in the uploaded document.

Gemini is also instructed to return that exact message when the provided context does not contain the answer. These grounding instructions reduce unsupported answers; model responses and citations are not independently verified. Check the cited PDF pages when accuracy matters.

## Installation

You need Python 3, pip, and internet access. From the project directory, create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

ChromaDB may download its default embedding model on first use. Answer generation requires access to the Gemini API.

## Configure Gemini securely

Create a Gemini API key in Google AI Studio. Set `GEMINI_API_KEY` in the same terminal used to start the application. Keep the key out of source files, screenshots, and Git commits.

Windows PowerShell (the prompt hides your input):

```powershell
$env:GEMINI_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Gemini API key" -AsSecureString)).Password
```

macOS/Linux with Bash (the prompt hides your input):

```bash
read -rsp "Gemini API key: " GEMINI_API_KEY
echo
export GEMINI_API_KEY
```

Optionally set `GEMINI_MODEL` to use another available model. If unset or empty, the application uses `gemini-2.5-flash`.

The included `.env.example` contains empty configuration variables only. **The application does not automatically load `.env` files.** Copying the example to `.env` alone will not configure it; use the terminal commands above or an environment manager that exports the variables before startup. `.env` files are ignored by Git.

API availability and usage limits depend on your Gemini account. The application displays a message if a rate limit or quota is reached.

## Run the application

From the project directory, with the environment activated and the API key configured:

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

## Deploy on Streamlit Community Cloud

The live version is hosted on [Streamlit Community Cloud](https://ai-doc-questions-answers-cdhtiauopjdqnrqipajjeu.streamlit.app). To deploy your own copy:

1. Fork this repository or use your own copy on GitHub.
2. On [share.streamlit.io](https://share.streamlit.io/), create a new public app from the GitHub repository.
3. Select the `main` branch, set the main file path to `app.py`, and choose Python 3.12.
4. In **Advanced settings → Secrets**, add your **own** Gemini API key using TOML:

   ```toml
   GEMINI_API_KEY = "your-own-gemini-api-key"
   ```

5. Deploy and test PDF uploading and one document-grounded question.

Do not commit the real key to GitHub. The live application uses a key configured privately in Streamlit's secrets; visitors do not need to provide the project owner's key.

## How to use the website

1. Upload a PDF in **Document Upload**.
2. Wait for processing to finish. The document panel shows the filename, page count, and readiness status.
3. Enter a question in **Ask Questions** and select **Generate answer**.
4. Read the answer and check the filenames and page numbers under **Document Sources**.
5. Expand the extracted text or retrieved chunks if you want to inspect the evidence.

The application works with one uploaded PDF at a time. Replacing or removing it clears the previous index. Scanned PDFs without readable text require OCR outside this application. Retrieved passages are sent to the Gemini API for answer generation.

## Testing and limitations

The application has been manually tested with a text-based project PDF: it uploaded and indexed the PDF, retrieved relevant passages, generated a cited Gemini answer, and returned a not-found message for an unrelated question. The deployed Streamlit version was also tested with a relevant PDF question.

- Supports one text-based PDF at a time; scanned/image-only PDFs require OCR, which is not implemented.
- The Chroma index exists only for the current session and is not persisted.
- Uses an external Gemini API for answer generation; **do not upload confidential or sensitive documents** unless your usage policies permit sharing their contents with that provider.
- Gemini free-tier quotas and model availability may change. Responses and citations should be checked against the original source.

## Project structure

```text
.
├── app.py                   # Streamlit interface and PDF/retrieval pipeline
├── answer_generator.py      # Gemini integration and grounding instructions
├── styles.css               # Custom interface styling
├── requirements.txt         # Application dependencies
├── .streamlit/
│   └── config.toml          # Light theme configuration
├── .env.example             # Empty environment-variable template
├── .gitignore               # Secrets, environments, caches, and generated files
└── README.md
```

Document indexes are held in memory; the application does not currently save a persistent ChromaDB database.
