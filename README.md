
# PDF Chat Assistant (RAG)

A Retrieval-Augmented-Generation (RAG) app that lets you chat with PDF documents.  
Frontend: Streamlit app. Backend: Colab notebook/script acting as a Flask server (exposed via ngrok).

## Overview

- Upload a PDF in the Streamlit frontend and the Colab backend will:
  - extract text from the PDF,
  - create context chunks,
  - compute BGE embeddings,
  - store vectors in ChromaDB,
  - answer user queries by retrieving relevant chunks and asking a Gemini LLM.
- The frontend sends the PDF and queries to the backend over HTTP.

## Repository layout

- [Frontend/app.py](Frontend/app.py) — Streamlit frontend (UI, upload, chat).
- [Backend-Colab/rag_backened.py](Backend-Colab/rag_backened.py) — Colab/Flask backend (PDF processing, embeddings, ChromaDB, LLM).
- [requirements.txt](requirements.txt) — frontend dependencies for local dev.

## Quick start

1. Start the backend in Google Colab
   - Open [Backend-Colab/rag_backened.py](Backend-Colab/rag_backened.py) in Colab.
   - Make sure you set your Gemini API key and ngrok auth token in Colab (the script uses `userdata.get('GEMINI_API_KEY')` and `userdata.get('NGROK_AUTH_TOKEN')`).
   - Run the Colab cells to install dependencies and start the Flask server. The script uses ngrok to provide a public URL — copy that URL.

2. Run the frontend locally
   - Install frontend deps:
     ```
     pip install -r [requirements.txt](http://_vscodecontentref_/0)
     ```
   - Start Streamlit:
     ```
     streamlit run [app.py](http://_vscodecontentref_/1)
     ```
   - In the Streamlit sidebar, paste the public URL from the Colab/ngrok backend (example: https://xxxx.ngrok-free.app) and press Connect.

3. Upload and chat
   - Upload a PDF (max 50 MB).
   - Process the PDF from the sidebar.
   - Ask questions in the chat box. The frontend will call the backend `/answer` endpoint and display responses.

## Key endpoints & functions

- Backend endpoints (see [Backend-Colab/rag_backened.py](Backend-Colab/rag_backened.py)):
  - [`Backend-Colab.rag_backened.home`](Backend-Colab/rag_backened.py) — health check `/`
  - [`Backend-Colab.rag_backened.process_pdf`](Backend-Colab/rag_backened.py) — `/process-pdf`
  - [`Backend-Colab.rag_backened.answer`](Backend-Colab/rag_backened.py) — `/answer`
  - [`Backend-Colab.rag_backened.clear`](Backend-Colab/rag_backened.py) — `/clear`
  - [`Backend-Colab.rag_backened.stats`](Backend-Colab/rag_backened.py) — `/stats`
  - Helper: [`Backend-Colab.rag_backened.extract_text_from_pdf`](Backend-Colab/rag_backened.py)

- Frontend helpers (see [Frontend/app.py](Frontend/app.py)):
  - [`Frontend.app.check_backend_connection`](Frontend/app.py)
  - [`Frontend.app.process_pdf_backend`](Frontend/app.py)
  - [`Frontend.app.ask_question_backend`](Frontend/app.py)
  - UI flows: [`Frontend.app.process_pdf`](Frontend/app.py), [`Frontend.app.handle_chat`](Frontend/app.py), and main entry [`Frontend.app.main`](Frontend/app.py)

## Configuration & limits

- PDF size limit: 50 MB (frontend and backend).
- Chunking: configured in backend (`CHUNK_SIZE`, `CHUNK_OVERLAP`).
- Similarity threshold: cosine similarity threshold configured in backend (`COSINE_SIMILARITY_THRESHOLD`).
- Embedding model: `BAAI/bge-small-en-v1.5` (backend).
- Colab backend must have internet access and appropriate GPU if you want faster embedding.

## Troubleshooting

- Backend unreachable: verify ngrok URL returned by Colab and paste it into the Streamlit sidebar.
- No PDF text extracted: PDF may be scanned images — use OCR before sending to backend.
- API keys/tokens: ensure Gemini API key and ngrok auth token are set in Colab.
- Check logs in Colab cells for backend errors.

## Security & privacy notes

- Uploaded PDFs are processed by the Colab runtime and stored in memory/ChromaDB there — avoid uploading sensitive documents to shared Colab runtimes.
- Keep your Gemini API key and ngrok token private.

## Where to look in the code

- Streamlit frontend and UI logic: [Frontend/app.py](Frontend/app.py) — see [`Frontend.app.main`](Frontend/app.py) and helpers.
- Colab backend server and RAG flow: [Backend-Colab/rag_backened.py](Backend-Colab/rag_backened.py) — see endpoints and helpers mentioned above.

## License

See LICENSE in the repository.