

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
import time
import gc


class PDFLoaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced PDF to Vector Database Loader")
        self.root.geometry("900x700")

        # Your specific PDF path
        self.default_pdf_path = r"D:\UMASS\CPT\Datasets\Dataset 1.pdf"

        # Processing control
        self.processing_cancelled = False

        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Title
        title_label = ttk.Label(main_frame, text="Enhanced PDF to Vector Database Loader",
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
        settings_frame = ttk.LabelFrame(main_frame, text="Processing Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Row 1: Chunk settings
        ttk.Label(settings_frame, text="Chunk Size:").grid(row=0, column=0, sticky=tk.W)
        self.chunk_size_var = tk.StringVar(value="800")  # Reduced for better processing
        ttk.Entry(settings_frame, textvariable=self.chunk_size_var, width=10).grid(row=0, column=1, padx=(10, 20))

        ttk.Label(settings_frame, text="Chunk Overlap:").grid(row=0, column=2, sticky=tk.W)
        self.chunk_overlap_var = tk.StringVar(value="150")  # Reduced for better processing
        ttk.Entry(settings_frame, textvariable=self.chunk_overlap_var, width=10).grid(row=0, column=3, padx=(10, 0))

        # Row 2: Batch settings
        ttk.Label(settings_frame, text="Embed Batch Size:").grid(row=1, column=0, sticky=tk.W)
        self.batch_size_var = tk.StringVar(value="5")  # Smaller batches for stability
        ttk.Entry(settings_frame, textvariable=self.batch_size_var, width=10).grid(row=1, column=1, padx=(10, 20))

        ttk.Label(settings_frame, text="Batch Delay (sec):").grid(row=1, column=2, sticky=tk.W)
        self.batch_delay_var = tk.StringVar(value="0.5")  # Delay between batches
        ttk.Entry(settings_frame, textvariable=self.batch_delay_var, width=10).grid(row=1, column=3, padx=(10, 0))

        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))

        # Quick process button
        self.quick_btn = ttk.Button(button_frame, text="🚀 Quick Process My PDF",
                                    command=self.quick_process, style="Accent.TButton")
        self.quick_btn.grid(row=0, column=0, padx=(0, 10))

        # Process button
        self.process_btn = ttk.Button(button_frame, text="📄 Process Selected PDF",
                                      command=self.process_pdf)
        self.process_btn.grid(row=0, column=1, padx=(5, 10))

        # Test connection button
        test_btn = ttk.Button(button_frame, text="🔧 Test Connection",
                              command=self.test_connection)
        test_btn.grid(row=0, column=2, padx=(5, 10))

        # Cancel button
        self.cancel_btn = ttk.Button(button_frame, text="❌ Cancel Processing",
                                     command=self.cancel_processing, state="disabled")
        self.cancel_btn.grid(row=0, column=3, padx=(5, 0))

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        # Progress info
        self.progress_info = ttk.Label(main_frame, text="Ready to process...")
        self.progress_info.grid(row=5, column=0, columnspan=3, pady=(0, 10))

        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Progress Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

    def log(self, message):

        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def update_progress_info(self, text):

        self.progress_info.config(text=text)
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

    def cancel_processing(self):

        self.processing_cancelled = True
        self.log("❌ Processing cancelled by user")
        self.update_progress_info("Processing cancelled...")

    def set_processing_state(self, processing=True):

        state = "disabled" if processing else "normal"
        cancel_state = "normal" if processing else "disabled"

        self.quick_btn.config(state=state)
        self.process_btn.config(state=state)
        self.cancel_btn.config(state=cancel_state)

    def test_connection(self):

        self.log("🔧 Testing connections...")

        # Test database
        try:
            conn = self.connect_db()
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()[0]
            cur.close()
            conn.close()
            self.log("✅ Database connection successful!")
            self.log(f"📊 PostgreSQL version: {version[:50]}...")
        except Exception as e:
            self.log(f"❌ Database connection failed: {e}")
            return

        # Test Ollama
        try:
            models_response = ollama.list()
            self.log("✅ Ollama connection successful!")

            # Show available models
            models = self.get_models_list(models_response)
            model_count = len(models) if models else 0
            self.log(f"📋 Found {model_count} models in Ollama")

            # Test embedding
            test_response = ollama.embed(model='nomic-embed-text', input=['test'])
            embedding_dim = len(test_response['embeddings'][0])
            self.log(f"✅ Embedding test successful! Dimension: {embedding_dim}")

        except Exception as e:
            self.log(f"❌ Ollama connection failed: {e}")
            self.log("   Make sure Ollama is running with 'ollama serve'")
            return

        self.log("✅ All connections working!")

    def get_models_list(self, models_response):

        if hasattr(models_response, 'models'):
            return models_response.models
        elif isinstance(models_response, dict) and 'models' in models_response:
            return models_response['models']
        elif isinstance(models_response, list):
            return models_response
        return []

    def process_pdf(self):

        self.processing_cancelled = False

        def run_process():
            try:
                self.set_processing_state(True)
                self.progress.start()
                self.update_progress_info("Starting PDF processing...")

                # Get parameters
                pdf_path = self.pdf_path_var.get().strip()
                chunk_size = int(self.chunk_size_var.get())
                chunk_overlap = int(self.chunk_overlap_var.get())
                batch_size = int(self.batch_size_var.get())
                batch_delay = float(self.batch_delay_var.get())

                # Validate inputs
                if not pdf_path:
                    self.log("❌ Please select a PDF file!")
                    return

                if not os.path.exists(pdf_path):
                    self.log(f"❌ File not found: {pdf_path}")
                    return

                # Check file size
                file_size = os.path.getsize(pdf_path)
                self.log(f"📄 Processing PDF: {os.path.basename(pdf_path)} ({file_size:,} bytes)")

                if file_size > 50 * 1024 * 1024:  # 50MB
                    self.log("⚠️  Large file detected - processing may take longer")

                # Check cancelled
                if self.processing_cancelled:
                    return

                # Step 1: Test connections
                self.update_progress_info("Testing connections...")
                if not self.verify_connections():
                    return

                # Step 2: Extract text with memory management
                self.update_progress_info("Extracting text from PDF...")
                if self.processing_cancelled:
                    return

                text = self.extract_text_from_pdf_improved(pdf_path)
                if not text:
                    self.log("❌ Failed to extract text from PDF")
                    return

                # Step 3: Chunk text
                self.update_progress_info("Chunking text...")
                if self.processing_cancelled:
                    return

                chunks = self.chunk_text_improved(text, chunk_size, chunk_overlap)
                if not chunks:
                    self.log("❌ Failed to create chunks")
                    return

                # Clear text from memory
                del text
                gc.collect()

                # Step 4: Generate embeddings with better error handling
                self.update_progress_info("Generating embeddings...")
                if self.processing_cancelled:
                    return

                data_to_insert = self.embed_chunks_improved(chunks, batch_size, batch_delay)
                if not data_to_insert:
                    self.log("❌ Failed to generate embeddings")
                    return

                # Step 5: Insert into database
                self.update_progress_info("Storing in database...")
                if self.processing_cancelled:
                    return

                self.insert_embeddings_improved(data_to_insert)

                if not self.processing_cancelled:
                    self.log("✅ PDF processing completed successfully!")
                    self.log(f"📊 Processed {len(chunks)} chunks from your PDF")
                    self.update_progress_info("Processing completed successfully!")
                    messagebox.showinfo("Success",
                                        "PDF processed successfully!\nYou can now use the search functionality.")

            except Exception as e:
                self.log(f"❌ Error: {e}")
                self.update_progress_info(f"Error: {e}")
                messagebox.showerror("Error", f"Processing failed: {e}")
            finally:
                self.progress.stop()
                self.set_processing_state(False)

        # Run in separate thread
        thread = threading.Thread(target=run_process)
        thread.daemon = True
        thread.start()

    def verify_connections(self):

        try:
            # Test database
            conn = self.connect_db()
            conn.close()
            self.log("✅ Database connection verified")

            # Test Ollama
            ollama.list()
            self.log("✅ Ollama connection verified")

            # Ensure model is available
            if not self.ensure_model_available():
                return False

            return True
        except Exception as e:
            self.log(f"❌ Connection verification failed: {e}")
            return False

    def ensure_model_available(self):

        try:
            models_response = ollama.list()
            models = self.get_models_list(models_response)

            model_names = []
            if models:
                for model in models:
                    if hasattr(model, 'name'):
                        model_names.append(model.name)
                    elif isinstance(model, dict):
                        name = model.get('name') or model.get('model', '')
                        model_names.append(name)

            if not any('nomic-embed-text' in name for name in model_names):
                self.log("📥 Downloading nomic-embed-text model...")
                ollama.pull('nomic-embed-text')
                self.log("✅ Model downloaded!")
            else:
                self.log("✅ nomic-embed-text model already available!")

            return True
        except Exception as e:
            self.log(f"❌ Model setup failed: {e}")
            return False

    def connect_db(self):

        return psycopg2.connect(
            host='localhost',
            port='5434',
            database='proposalagentchatdb',
            user='postgres',
            password='Deadpool@123'
        )

    def extract_text_from_pdf_improved(self, pdf_path: str) -> str:

        try:
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            self.log(f"📖 PDF has {total_pages} pages")

            text_parts = []

            for i, page in enumerate(reader.pages):
                if self.processing_cancelled:
                    return ""

                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    # Update progress
                    if i % 5 == 0 or i == total_pages - 1:
                        self.log(f"   Processed page {i + 1}/{total_pages}")
                        self.update_progress_info(f"Extracting text... Page {i + 1}/{total_pages}")

                except Exception as e:
                    self.log(f"⚠️  Error extracting page {i + 1}: {e}")
                    continue

            # Join all text parts
            full_text = "\n".join(text_parts)
            self.log(f"✅ Extracted {len(full_text):,} characters from {total_pages} pages")

            return full_text

        except Exception as e:
            self.log(f"❌ Error extracting text: {e}")
            return ""

    def chunk_text_improved(self, text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> List[Dict]:

        try:
            # Clean the text
            text = re.sub(r'\s+', ' ', text).strip()
            text_length = len(text)

            self.log(f"📝 Chunking {text_length:,} characters")

            chunks = []
            start = 0
            chunk_id = 0
            processed_chars = 0

            while start < text_length:
                if self.processing_cancelled:
                    return []

                # Find the end of the chunk
                end = min(start + chunk_size, text_length)

                # Try to break at a sentence boundary
                if end < text_length:
                    sentence_ends = [
                        text.rfind('. ', start, end),
                        text.rfind('! ', start, end),
                        text.rfind('? ', start, end),
                        text.rfind('\n', start, end)
                    ]

                    best_end = max(sentence_ends)
                    if best_end > start:
                        end = best_end + 1

                # Extract chunk
                chunk_text = text[start:end].strip()

                if chunk_text and len(chunk_text) > 50:  # Minimum chunk size
                    chunks.append({
                        'id': chunk_id,
                        'text': chunk_text,
                        'metadata': {
                            'chunk_id': chunk_id,
                            'start_pos': start,
                            'end_pos': end,
                            'length': len(chunk_text)
                        }
                    })
                    chunk_id += 1

                # Update progress
                processed_chars = end
                if chunk_id % 50 == 0:
                    progress_pct = (processed_chars / text_length) * 100
                    self.log(f"   Created {chunk_id} chunks ({progress_pct:.1f}%)")
                    self.update_progress_info(f"Chunking... {chunk_id} chunks created")

                # Move to next chunk with overlap
                start = max(end - chunk_overlap, start + 1)  # Prevent infinite loop

                # Safety check to prevent infinite loop
                if start >= text_length:
                    break

            self.log(f"✅ Created {len(chunks)} chunks")
            return chunks

        except Exception as e:
            self.log(f"❌ Error chunking text: {e}")
            return []

    def embed_chunks_improved(self, chunks: List[Dict], batch_size: int = 5, batch_delay: float = 0.5) -> List[Tuple]:

        try:
            data_to_insert = []
            total_chunks = len(chunks)

            self.log(f"🧠 Generating embeddings for {total_chunks} chunks (batch size: {batch_size})")

            for i in range(0, total_chunks, batch_size):
                if self.processing_cancelled:
                    return []

                batch = chunks[i:i + batch_size]
                batch_end = min(i + batch_size, total_chunks)

                # Update progress
                self.update_progress_info(f"Generating embeddings... {i + 1}-{batch_end}/{total_chunks}")

                # Prepare texts for embedding
                texts = [f"search_document: {chunk['text']}" for chunk in batch]

                # Retry logic for embedding
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = ollama.embed(
                            model='nomic-embed-text',
                            input=texts
                        )

                        embeddings = response['embeddings']

                        # Process embeddings
                        for chunk, embedding in zip(batch, embeddings):
                            data_to_insert.append((
                                json.dumps(chunk['metadata']),
                                chunk['text'],
                                embedding
                            ))

                        self.log(
                            f"   Processed batch {i // batch_size + 1}/{(total_chunks + batch_size - 1) // batch_size}")
                        break

                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.log(f"⚠️  Embedding attempt {attempt + 1} failed, retrying... ({e})")
                            time.sleep(1)
                        else:
                            self.log(f"❌ Embedding failed after {max_retries} attempts: {e}")
                            raise

                # Add delay between batches to avoid overwhelming Ollama
                if batch_delay > 0 and i + batch_size < total_chunks:
                    time.sleep(batch_delay)

            self.log(f"✅ Generated {len(data_to_insert)} embeddings")
            return data_to_insert

        except Exception as e:
            self.log(f"❌ Error generating embeddings: {e}")
            return []

    def insert_embeddings_improved(self, data_to_insert: List[Tuple]):

        conn = None
        cur = None

        try:
            conn = self.connect_db()
            cur = conn.cursor()

            # Clear existing data
            self.log("🗑️  Clearing existing embeddings...")
            cur.execute("TRUNCATE TABLE embeddings RESTART IDENTITY")

            # Insert in batches for better performance
            batch_size = 100
            total_items = len(data_to_insert)

            self.log(f"💾 Inserting {total_items} embeddings in batches of {batch_size}")

            for i in range(0, total_items, batch_size):
                if self.processing_cancelled:
                    conn.rollback()
                    return

                batch = data_to_insert[i:i + batch_size]
                batch_end = min(i + batch_size, total_items)

                # Update progress
                self.update_progress_info(f"Storing in database... {i + 1}-{batch_end}/{total_items}")

                # Insert batch
                insert_sql = """
                    INSERT INTO embeddings (metadata, contents, embedding) 
                    VALUES %s
                """

                execute_values(
                    cur,
                    insert_sql,
                    batch,
                    template="(%s, %s, %s::vector)",
                    page_size=batch_size
                )

                # Commit batch
                conn.commit()

                self.log(f"   Inserted batch {i // batch_size + 1}/{(total_items + batch_size - 1) // batch_size}")

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

    # Add initial instructions
    app.log("🎯 Welcome to Enhanced PDF Vector Database Loader!")
    app.log("📋 Improvements for larger documents:")
    app.log("   - Better memory management")
    app.log("   - Smaller batch sizes for stability")
    app.log("   - Progress tracking and cancellation")
    app.log("   - Improved error handling")
    app.log("")
    app.log("📋 Instructions:")
    app.log("   1. Click 'Test Connection' to verify setup")
    app.log("   2. Click 'Quick Process My PDF' to process your document")
    app.log("   3. Or browse for a different PDF file")
    app.log("")
    app.log("⚠️  Make sure:")
    app.log("   - PostgreSQL is running on port 5434")
    app.log("   - Ollama is running (ollama serve)")
    app.log("   - Database schema is created")
    app.log("")

    root.mainloop()


if __name__ == "__main__":
    main()