

pip install flask pyngrok chromadb sentence-transformers PyPDF2 langchain langchain-community langchain-google-genai python-dotenv

from flask import Flask, request, jsonify
from pyngrok import ngrok
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
import PyPDF2
import io
import os
from werkzeug.utils import secure_filename
from google.colab import userdata

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024


CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
COSINE_SIMILARITY_THRESHOLD = 0.50
GEMINI_API_KEY = userdata.get('GEMINI_API_KEY')
NGROK_TOKEN = userdata.get('NGROK_AUTH_TOKEN')

print("="*60)
print("🔄 Loading BGES-Small-EN-v1.5 embedding model (GPU-optimized)...")
print("="*60)

#  Use BGE model
embedding_model = SentenceTransformer(
    'BAAI/bge-small-en-v1.5',
    device='cuda' if __import__('torch').cuda.is_available() else 'cpu'
)
embedding_dimension = embedding_model.get_sentence_embedding_dimension()
print(f"✅ Embedding model loaded! Dimension: {embedding_dimension}")
print(f"✅ Using device: {embedding_model.device}")

# STEP 6: Initialize ChromaDB with COSINE distance
print("\Initializing ChromaDB with COSINE distance...")
chroma_client = chromadb.Client()
print(" ChromaDB initialized!")

# STEP 7: Initialize Gemini LLM
print(" Initializing Gemini LLM ...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-pro",
    google_api_key=GEMINI_API_KEY,
    temperature=0.2,
    max_tokens=1024
)
print("✅ Gemini LLM initialized!")
print("="*60 + "\n")

# Global variables
current_collection = None
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
    keep_separator=True
)

# ========================================
# HELPER FUNCTIONS
# ========================================

def extract_text_from_pdf(file_bytes):
    """Extract text from PDF bytes."""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))

        if pdf_reader.is_encrypted:
            return None, "PDF is encrypted/password protected"

        num_pages = len(pdf_reader.pages)
        if num_pages > 50:
            return None, f"PDF too large ({num_pages} pages). Maximum 50 pages."

        text = ""
        for i, page in enumerate(pdf_reader.pages):
            page_text = page.extract_text()
            if page_text.strip():
                text += f"\n--- Page {i+1} ---\n{page_text}"

        if not text.strip() or len(text) < 200:
            return None, "Insufficient text in PDF. Might be image-based or corrupted."

        return text, None
    except Exception as e:
        return None, f"Error extracting text: {str(e)}"

def create_smart_chunks(text):
    """Create optimized chunks with better context."""
    documents = [Document(page_content=text)]
    chunks = text_splitter.split_documents(documents)

    # Filter out very short chunks
    filtered_chunks = [
        chunk for chunk in chunks
        if len(chunk.page_content.strip()) > 100
    ]

    return filtered_chunks

def compute_embeddings_batch(texts, batch_size=32):
    """Compute embeddings in batches with normalization."""
    embeddings = embedding_model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        normalize_embeddings=True  # ✅ CRITICAL: Normalize for cosine similarity
    )
    return embeddings

# ========================================
# API ENDPOINTS
# ========================================

@app.route('/')
def home():
    """Health check endpoint."""
    collection_count = current_collection.count() if current_collection else 0
    return jsonify({
        "status": "online",
        "message": "QueryDocs Backend API v2.0",
        "collection_count": collection_count,
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "embedding_dim": embedding_dimension,
        "device": str(embedding_model.device),
        "gemini_configured": bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 20)
    })

@app.route('/process-pdf', methods=['POST'])
def process_pdf():
    """Process uploaded PDF with improved embeddings."""
    global current_collection

    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['file']
        filename = secure_filename(file.filename)

        if not filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files supported"}), 400

        file_bytes = file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        if file_size_mb > 50:
            return jsonify({"error": "File too large. Max: 50MB"}), 400

        print("\n" + "="*60)
        print(f"📄 PROCESSING: {filename} ({file_size_mb:.2f} MB)")
        print("="*60)

        # Step 1: Extract text
        print("\n[1/5] 📖 Extracting text from PDF...")
        text, error = extract_text_from_pdf(file_bytes)
        if error:
            return jsonify({"error": error}), 400

        print(f"✅ Extracted {len(text):,} characters")

        # Step 2: Create smart chunks
        print("\n[2/5] ✂️  Creating optimized chunks...")
        chunks = create_smart_chunks(text)
        print(f"✅ Created {len(chunks)} chunks")

        # Limit chunks
        max_chunks = 100
        if len(chunks) > max_chunks:
            print(f"⚠️  Limiting to first {max_chunks} chunks")
            chunks = chunks[:max_chunks]

        # Step 3: Generate embeddings with BGE model
        print(f"\n[3/5] 🧠 Generating BGE embeddings (batch processing)...")
        chunk_texts = [chunk.page_content for chunk in chunks]
        embeddings = compute_embeddings_batch(chunk_texts, batch_size=32)
        print(f"✅ Generated {len(embeddings)} embeddings (shape: {embeddings.shape})")

        # Step 4: Create ChromaDB collection with COSINE distance
        print("\n[4/5] 💾 Creating ChromaDB collection (COSINE distance)...")

        # Delete old collection
        try:
            chroma_client.delete_collection("pdf_documents")
            print("  🗑️  Deleted old collection")
        except:
            pass

        # Create new collection with COSINE metric
        current_collection = chroma_client.create_collection(
            name="pdf_documents",
            metadata={
                "hnsw:space": "cosine",  # ✅ CRITICAL: Use cosine distance
                "description": f"Embeddings for {filename}"
            }
        )
        print("  ✅ Collection created with COSINE distance")

        # Step 5: Add documents to ChromaDB
        print("\n[5/5] 📥 Adding documents to vector store...")
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "chunk_id": i,
                "source": filename,
                "chunk_length": len(chunk_texts[i])
            }
            for i in range(len(chunks))
        ]

        current_collection.add(
            embeddings=embeddings.tolist(),
            documents=chunk_texts,
            ids=ids,
            metadatas=metadatas
        )

        print(f"✅ Added {len(chunks)} documents to vector store")
        print("\n" + "="*60)
        print("✅ PDF PROCESSING COMPLETE!")
        print("="*60 + "\n")

        return jsonify({
            "message": "PDF processed successfully",
            "filename": filename,
            "file_size_mb": round(file_size_mb, 2),
            "total_chunks": len(chunks),
            "text_length": len(text),
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "distance_metric": "cosine"
        })

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/answer', methods=['POST'])
def answer():
    """✅ FIXED: Proper RAG with cosine similarity."""
    global current_collection

    try:
        if not current_collection:
            return jsonify({"error": "No PDF uploaded. Please process a PDF first."}), 400

        data = request.json
        question = data.get('query', '').strip()
        top_k = min(data.get('top_k', 5), 10)  # Max 10 results

        if not question:
            return jsonify({"error": "No query provided"}), 400

        print("\n" + "="*60)
        print(f"💬 QUESTION: {question}")
        print("="*60)

        # Step 1: Generate query embedding (NORMALIZED)
        print("\n[1/3] 🔍 Generating query embedding...")
        query_embedding = embedding_model.encode(
            [question],
            normalize_embeddings=True  # ✅ Must normalize for cosine
        )
        print(f"✅ Query embedding shape: {query_embedding.shape}")

        # Step 2: Search ChromaDB (returns COSINE DISTANCE)
        print(f"\n[2/3] 🔎 Searching ChromaDB (top {top_k})...")
        results = current_collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k
        )

        # Step 3: Process results (convert distance to similarity)
        print("\n[3/3] 📊 Processing search results:")
        print("-" * 60)

        relevant_contexts = []
        for i in range(len(results['documents'][0])):
            distance = results['distances'][0][i]
            # ChromaDB with cosine returns: distance = 1 - cosine_similarity
            # So: similarity = 1 - distance
            similarity = 1.0 - distance

            doc_text = results['documents'][0][i]
            metadata = results['metadatas'][0][i]

            print(f"Result [{i}]:")
            print(f"  Cosine Similarity: {similarity:.4f}")
            print(f"  Distance: {distance:.4f}")
            print(f"  Text preview: {doc_text[:100]}...")
            print()

            # Only include if similarity is above threshold
            if similarity >= COSINE_SIMILARITY_THRESHOLD:
                relevant_contexts.append({
                    'text': doc_text,
                    'similarity': similarity,
                    'metadata': metadata
                })

        print(f"✅ Found {len(relevant_contexts)} relevant contexts")
        print(f"   (Threshold: {COSINE_SIMILARITY_THRESHOLD})")
        print("-" * 60)

        # Step 4: Generate response based on relevance
        if len(relevant_contexts) >= 1:
            # Use RAG with PDF context
            context_text = "\n\n---\n\n".join([
                f"[Similarity: {ctx['similarity']:.2f}]\n{ctx['text']}"
                for ctx in relevant_contexts
            ])

            rag_prompt = f"""You are a helpful AI assistant answering questions based on a PDF document.

CONTEXT FROM PDF:
{context_text}

USER QUESTION: {question}

INSTRUCTIONS:
- Answer based ONLY on the context provided above
- If the answer is not in the context, say "This information is not in the uploaded PDF"
- Keep your answer concise and accurate

ANSWER:"""

            print("\n🤖 Generating RAG response...")
            response = llm.invoke(rag_prompt)
            answer_text = response.content
            response_type = "pdf"
            print("✅ PDF-based answer generated")

        else:
            # No relevant context - general fallback
            fallback_prompt = f"""The user asked a question unrelated to their uploaded PDF.

Question: {question}

Provide a brief, helpful general answer.

Answer:"""

            print("\n🤖 Generating general response (no relevant PDF context)...")
            response = llm.invoke(fallback_prompt)
            answer_text = f"⚠️ This question is not covered in your uploaded PDF.\n\nGeneral answer:\n\n{response.content}"
            response_type = "general"
            print("✅ General answer generated")

        print("="*60 + "\n")

        return jsonify({
            "query": question,
            "answer": answer_text,
            "type": response_type,
            "contexts_used": len(relevant_contexts),
            "similarity_scores": [ctx['similarity'] for ctx in relevant_contexts],
            "threshold": COSINE_SIMILARITY_THRESHOLD
        })

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/clear', methods=['POST'])
def clear():
    """Clear the current collection."""
    global current_collection

    try:
        if current_collection:
            chroma_client.delete_collection("pdf_documents")
            current_collection = None
            print("✅ Collection cleared")

        return jsonify({"message": "Collection cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def stats():
    """Get collection statistics."""
    try:
        count = current_collection.count() if current_collection else 0
        return jsonify({
            "total_chunks": count,
            "collection_exists": bool(current_collection),
            "embedding_model": "BAAI/bge-small-en-v1.5",
            "threshold": COSINE_SIMILARITY_THRESHOLD
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========================================
# START SERVER
# ========================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 QUERYDOCS BACKEND v2.0 - PRODUCTION READY")
    print("="*60)
    print(f"📊 Embedding Model: BAAI/bge-small-en-v1.5")
    print(f"📐 Distance Metric: COSINE")
    print(f"🎯 Similarity Threshold: {COSINE_SIMILARITY_THRESHOLD}")
    print(f"💻 Device: {embedding_model.device}")
    print("="*60 + "\n")

    # Set up ngrok
    print("🔄 Setting up ngrok tunnel...")
    ngrok.set_auth_token(NGROK_TOKEN)
    public_url = ngrok.connect(5000)

    print("\n" + "="*60)
    print("✅ BACKEND IS LIVE!")
    print("="*60)

    print(f"📡 Public URL: {public_url}")
    print("\n⚠️  COPY THIS URL TO YOUR FRONTEND!")
    print("="*60 + "\n")

    # Run Flask
    app.run(port=5000, debug=False)

