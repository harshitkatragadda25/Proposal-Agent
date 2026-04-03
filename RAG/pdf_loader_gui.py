
import sys
import json
import psycopg2
from psycopg2.extras import execute_values
import ollama
from pypdf import PdfReader
from typing import List, Dict, Tuple
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os


class PDFLoaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to Vector Database Loader")
        self.root.geometry("800x600")

        # Your specific PDF path
        self.default_pdf_path = r"D:\UMASS\CPT\Datasets\Dataset 1.pdf"

        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="PDF to Vector Database Loader",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # File selection frame
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # PDF path
        ttk.Label(file_frame, text="PDF File:").grid(row=0, column=0, sticky=tk.W)
        self.pdf_path_var = tk.StringVar(value=self.default_pdf_path)
        pdf_entry = ttk.Entry(file_frame, textvariable=self.pdf_path_var, width=70)
        pdf_entry.grid(row=0, column=1, padx=(10, 5))

        browse_btn = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_btn.grid(row=0, column=2, padx=(5, 0))

        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Chunk Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(settings_frame, text="Chunk Size:").grid(row=0, column=0, sticky=tk.W)
        self.chunk_size_var = tk.StringVar(value="1000")
        ttk.Entry(settings_frame, textvariable=self.chunk_size_var, width=10).grid(row=0, column=1, padx=(10, 20))

        ttk.Label(settings_frame, text="Chunk Overlap:").grid(row=0, column=2, sticky=tk.W)
        self.chunk_overlap_var = tk.StringVar(value="200")
        ttk.Entry(settings_frame, textvariable=self.chunk_overlap_var, width=10).grid(row=0, column=3, padx=(10, 0))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))

        # Quick process button for your specific file
        quick_btn = ttk.Button(button_frame, text="🚀 Quick Process My PDF",
                               command=self.quick_process, style="Accent.TButton")
        quick_btn.grid(row=0, column=0, padx=(0, 10))

        # Process button
        process_btn = ttk.Button(button_frame, text="📄 Process Selected PDF",
                                 command=self.process_pdf)
        process_btn.grid(row=0, column=1, padx=(5, 10))

        # Test connection button
        test_btn = ttk.Button(button_frame, text="🔧 Test Connection",
                              command=self.test_connection)
        test_btn.grid(row=0, column=2, padx=(5, 0))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Progress Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def log(self, message):

        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def browse_file(self):

        filename = filedialog.askopenfilename(
            title="Select PDF file",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if filename:
            self.pdf_path_var.set(filename)

    def quick_process(self):

        self.log("🚀 Starting quick processing of your PDF...")
        self.pdf_path_var.set(self.default_pdf_path)
        self.process_pdf()

    def test_connection(self):

        self.log("🔧 Testing connections...")

        # Test database
        try:
            conn = self.connect_db()
            conn.close()
            self.log("✅ Database connection successful!")
        except Exception as e:
            self.log(f"❌ Database connection failed: {e}")
            return

        # Test Ollama
        try:
            models_response = ollama.list()
            self.log("✅ Ollama connection successful!")

            # Show available models
            models = None
            if hasattr(models_response, 'models'):
                models = models_response.models
            elif isinstance(models_response, dict) and 'models' in models_response:
                models = models_response['models']
            elif isinstance(models_response, list):
                models = models_response

            model_count = len(models) if models else 0
            self.log(f"📋 Found {model_count} models in Ollama")

        except Exception as e:
            self.log(f"❌ Ollama connection failed: {e}")
            self.log("   Make sure Ollama is running with 'ollama serve'")
            return

        self.log("✅ All connections working!")

    def process_pdf(self):

        def run_process():
            try:
                self.progress.start()
                pdf_path = self.pdf_path_var.get().strip()
                chunk_size = int(self.chunk_size_var.get())
                chunk_overlap = int(self.chunk_overlap_var.get())

                if not pdf_path:
                    self.log("❌ Please select a PDF file!")
                    return

                if not os.path.exists(pdf_path):
                    self.log(f"❌ File not found: {pdf_path}")
                    return

                # Extract text
                self.log("📖 Extracting text from PDF...")
                pages_text = self.extract_text_from_pdf(pdf_path)

                # Chunk text per page
                all_chunks = []
                for page_number, page_text in pages_text:
                    self.log(f"✂️ Chunking page {page_number}...")
                    chunks = self.chunk_text(page_text, chunk_size, chunk_overlap, page_number)
                    all_chunks.extend(chunks)

                # Check Ollama
                self.log("🔍 Checking Ollama...")
                try:
                    ollama.list()
                except Exception:
                    self.log("❌ Ollama is not running. Please start with 'ollama serve'")
                    return

                # Check/pull model
                self.log("🔍 Checking for nomic-embed-text model...")
                try:
                    models_response = ollama.list()
                    self.log(f"📋 Models response type: {type(models_response)}")

                    # Handle different response formats
                    models = None

                    if hasattr(models_response, 'models'):
                        # ollama._types.ListResponse has a models attribute
                        models = models_response.models
                        self.log(f"📋 Found {len(models)} models (via .models attribute)")
                    elif isinstance(models_response, dict) and 'models' in models_response:
                        # Traditional dict response
                        models = models_response['models']
                        self.log(f"📋 Found {len(models)} models (via dict)")
                    elif isinstance(models_response, list):
                        # Direct list response
                        models = models_response
                        self.log(f"📋 Found {len(models)} models (direct list)")
                    else:
                        self.log(f"⚠️ Unexpected response type, trying to access models anyway...")
                        models = []

                    model_names = []
                    if models:
                        for model in models:
                            if hasattr(model, 'name'):
                                model_names.append(model.name)
                            elif isinstance(model, dict):
                                name = model.get('name') or model.get('model', '')
                                model_names.append(name)
                            else:
                                model_names.append(str(model))

                    self.log(f"📋 Available models: {model_names}")

                    if not any('nomic-embed-text' in name for name in model_names):
                        self.log("📥 Downloading nomic-embed-text model...")
                        ollama.pull('nomic-embed-text')
                        self.log("✅ Model downloaded!")
                    else:
                        self.log("✅ nomic-embed-text model already available!")

                except Exception as model_error:
                    self.log(f"⚠️ Error checking models: {model_error}")
                    self.log("📥 Attempting to pull nomic-embed-text model anyway...")
                    try:
                        ollama.pull('nomic-embed-text')
                        self.log("✅ Model downloaded!")
                    except Exception as pull_error:
                        self.log(f"❌ Failed to download model: {pull_error}")
                        return

                # Extract text
                self.log("📖 Extracting text from PDF...")
                # Extract per-page text
                pages = self.extract_text_from_pdf(pdf_path)

                # Chunk each page
                all_chunks: List[Dict] = []
                for page_number, page_text in pages:
                    self.log(f"✂️ Chunking page {page_number} (size={chunk_size}, overlap={chunk_overlap})…")
                    page_chunks = self.chunk_text(page_text, chunk_size, chunk_overlap, page_number)
                    all_chunks.extend(page_chunks)

                chunks = all_chunks

                # Generate embeddings
                self.log("🧠 Generating embeddings...")
                data_to_insert = self.embed_chunks(chunks)

                # Insert into database
                self.log("💾 Storing in database...")
                self.insert_embeddings(data_to_insert)

                self.log("✅ PDF processing completed successfully!")
                self.log(f"📊 Processed {len(chunks)} chunks from your PDF")

                messagebox.showinfo("Success", "PDF processed successfully!\nYou can now use the search functionality.")

            except Exception as e:
                self.log(f"❌ Error: {e}")
                messagebox.showerror("Error", f"Processing failed: {e}")
            finally:
                self.progress.stop()

        # Run in separate thread to avoid freezing UI
        thread = threading.Thread(target=run_process)
        thread.daemon = True
        thread.start()

    def connect_db(self):

        return psycopg2.connect(
            host='localhost',
            port='5434',
            database='proposalagentchatdb',
            user='postgres',
            password='Deadpool@123'
        )

    def extract_text_from_pdf(self, pdf_path: str) -> List[Tuple[int, str]]:

        reader = PdfReader(pdf_path)
        pages_text: List[Tuple[int, str]] = []

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text() or ""
            pages_text.append((i + 1, page_text))

        self.log(f"✅ Extracted text from {len(pages_text)} pages")
        return pages_text

    def chunk_text(
            self,
            text: str,
            chunk_size: int,
            chunk_overlap: int,
            page_number: int
    ) -> List[Dict]:

        text = re.sub(r'\s+', ' ', text).strip()

        chunks: List[Dict] = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                # break on sentence boundary
                sentence_ends = [
                    text.rfind(p, start, end) for p in ('. ', '! ', '? ', '\n')
                ]
                best = max(sentence_ends)
                if best > start:
                    end = best + 1

            piece = text[start:end].strip()
            if piece:
                chunks.append({
                    'id': chunk_id,
                    'text': piece,
                    'metadata': {
                        'chunk_id': chunk_id,
                        'start_pos': start,
                        'end_pos': end,
                        'page_number': page_number
                    }
                })
                self.log(
                    f"✅ Page {page_number} – Chunk {chunk_id}: "
                    f"{len(piece)} chars (start={start}, end={end})"
                )
                chunk_id += 1

            start = end - chunk_overlap if end < len(text) else end

        self.log(f"✅ Created {len(chunks)} chunks for page {page_number}")
        return chunks

    def embed_chunks(self, chunks: List[Dict]) -> List[Tuple]:

        data_to_insert = []
        batch_size = 10

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [f"search_document: {chunk['text']}" for chunk in batch]

            try:
                response = ollama.embed(
                    model='nomic-embed-text',
                    input=texts
                )

                embeddings = response['embeddings']

                for chunk, embedding in zip(batch, embeddings):
                    data_to_insert.append((
                        json.dumps(chunk['metadata']),
                        chunk['text'],
                        embedding
                    ))

                self.log(f"  Processed chunks {i + 1}-{min(i + batch_size, len(chunks))}/{len(chunks)}")

            except Exception as e:
                self.log(f"❌ Error generating embeddings: {e}")
                raise

        return data_to_insert

    def insert_embeddings(self, data_to_insert: List[Tuple]):

        conn = None
        cur = None

        try:
            conn = self.connect_db()
            cur = conn.cursor()

            # Clear existing data (optional)
            cur.execute("TRUNCATE TABLE embeddings RESTART IDENTITY")

            # Insert embeddings
            insert_sql = """
                INSERT INTO embeddings (metadata, contents, embedding) 
                VALUES %s
            """

            execute_values(
                cur,
                insert_sql,
                data_to_insert,
                template="(%s, %s, %s::vector)"
            )

            conn.commit()

            # Verify insertion
            cur.execute("SELECT COUNT(*) FROM embeddings")
            count = cur.fetchone()[0]

            self.log(f"✅ Successfully inserted {count:,} embeddings")

        except psycopg2.Error as e:
            self.log(f"❌ Database error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if cur:
                cur.close()
            if conn:
                conn.close()


def main():

    root = tk.Tk()
    app = PDFLoaderGUI(root)

    # Add some initial instructions
    app.log("🎯 Welcome to PDF Vector Database Loader!")
    app.log("📋 Instructions:")
    app.log("   1. Click 'Quick Process My PDF' to process your document")
    app.log("   2. Or browse for a different PDF file")
    app.log("   3. Click 'Test Connection' first if you want to verify setup")
    app.log("")
    app.log("⚠️  Make sure:")
    app.log("   - PostgreSQL is running on port 5434")
    app.log("   - Ollama is running (ollama serve)")
    app.log("   - Database schema is created")
    app.log("")

    root.mainloop()


if __name__ == "__main__":
    main()