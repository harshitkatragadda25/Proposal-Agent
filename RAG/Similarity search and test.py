import psycopg2
from psycopg2.extras import RealDictCursor
import ollama
from typing import List, Dict
import json
import sys


def connect_db():

    return psycopg2.connect(
        host='localhost',
        port='5434',
        database='proposalagentchatdb',
        user='postgres',
        password='Deadpool@123'
    )


def embed_query(query: str) -> List[float]:

    try:
        response = ollama.embed(
            model='nomic-embed-text',
            input=[f"search_query: {query}"]
        )
        return response['embeddings'][0]
    except Exception as e:
        print(f"❌ Error generating query embedding: {e}")
        raise


def similarity_search(query: str, limit: int = 10, verbose: bool = True) -> List[Dict]:

    conn = None
    cur = None

    try:
        # Generate query embedding
        if verbose:
            print("Generating query embedding...")
        query_embedding = embed_query(query)

        # Connect to database
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Perform similarity search using cosine distance operator (<=>)
        search_sql = """
            SELECT 
                id,
                contents,
                metadata,
                embedding <=> %s::vector AS distance
            FROM embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        cur.execute(search_sql, (query_embedding, query_embedding, limit))
        results = cur.fetchall()

        return results

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def hybrid_search(query: str, limit: int = 10, verbose: bool = True) -> List[Dict]:

    conn = None
    cur = None

    try:
        # Generate query embedding
        if verbose:
            print("Performing hybrid search (vector + keyword)...")
        query_embedding = embed_query(query)

        # Connect to database
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Simplified hybrid search - vector similarity with keyword filtering
        hybrid_sql = """
            SELECT 
                id,
                contents,
                metadata,
                embedding <=> %s::vector AS distance
            FROM embeddings
            WHERE 
                to_tsvector('english', contents) @@ websearch_to_tsquery('english', %s)
                OR embedding <=> %s::vector < 0.7
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        cur.execute(hybrid_sql, (
            query_embedding, query, query_embedding, query_embedding, limit
        ))

        results = cur.fetchall()

        # If no results with keyword filtering, fall back to pure vector search
        if not results:
            if verbose:
                print("No keyword matches found, falling back to vector search...")
            return similarity_search(query, limit, verbose=False)

        return results

    except psycopg2.Error as e:
        # If hybrid search fails, fall back to similarity search
        if verbose:
            print(f"Hybrid search failed, using similarity search: {e}")
        return similarity_search(query, limit, verbose=False)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def extended_search(query: str, limit: int = 15, distance_threshold: float = 0.8, verbose: bool = True) -> List[Dict]:

    conn = None
    cur = None

    try:
        if verbose:
            print(f"Performing extended search for comprehensive context...")
        query_embedding = embed_query(query)

        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get more documents with higher threshold
        search_sql = """
            SELECT 
                id,
                contents,
                metadata,
                embedding <=> %s::vector AS distance
            FROM embeddings
            WHERE embedding <=> %s::vector < %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """

        cur.execute(search_sql, (
            query_embedding, query_embedding, distance_threshold, query_embedding, limit
        ))

        results = cur.fetchall()

        if verbose:
            print(f"✅ Extended search found {len(results)} documents")

        return results

    except Exception as e:
        if verbose:
            print(f"Extended search failed: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def generate_answer(query: str, context_docs: List[Dict], verbose: bool = True, concise: bool = False) -> str:

    if not context_docs:
        return "I couldn't find any relevant information to answer your question."

    # Prepare context from retrieved documents
    context = "\n\n".join([
        f"Document {i + 1} (Relevance: {doc['distance']:.3f}):\n{doc['contents']}"
        for i, doc in enumerate(context_docs)
    ])

    # Choose prompt based on mode
    if concise:
        prompt = f"""You are a helpful assistant. Provide a concise, direct answer to the user's question based on the context.

INSTRUCTIONS:
- Answer in 1-2 sentences maximum
- Be direct and to the point
- Include only the most essential information
- Don't include unnecessary details or explanations

Context Documents:
{context}

Question: {query}

Provide a concise answer (1-2 sentences):"""
    else:
        prompt = f"""You are a knowledgeable assistant. Provide a comprehensive and detailed answer to the user's question based on the provided context documents.

INSTRUCTIONS:
- Give a thorough, well-structured answer
- Use specific details and examples from the context
- If you find multiple relevant points, organize them clearly
- Include relevant quotes when appropriate
- If the information spans multiple documents, synthesize the information
- Be specific and detailed rather than general
- If certain aspects cannot be answered from the context, mention what information is missing

Context Documents:
{context}

Question: {query}

Provide a detailed and comprehensive answer:"""

    if verbose:
        mode = "concise" if concise else "detailed"
        print(f"\n🤖 Generating {mode} answer using {len(context_docs)} documents...")

    try:
        # Set parameters based on mode
        if concise:
            max_tokens = 150
            temperature = 0.3
        else:
            max_tokens = 4000
            temperature = 0.5

        # Enhanced generation parameters
        try:
            response = ollama.generate(
                model='llama3',
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'top_p': 0.85,
                    'max_tokens': max_tokens,
                    'repeat_penalty': 1.1
                }
            )
        except:
            response = ollama.generate(
                model='llama3.2',
                prompt=prompt,
                options={
                    'temperature': temperature,
                    'top_p': 0.85,
                    'max_tokens': max_tokens,
                    'repeat_penalty': 1.1
                }
            )

        return response['response']

    except Exception as e:
        return f"Error generating answer: {e}"


def rag_pipeline(query: str, search_type: str = "hybrid", verbose: bool = True,
                 detailed: bool = False, concise: bool = False) -> str:

    if verbose:
        print(f"\n🔍 Processing query: '{query}'")
        print("-" * 60)

    # Step 1: Retrieve relevant context
    try:
        if detailed or search_type == "extended":
            context_docs = extended_search(query, limit=15, distance_threshold=0.8, verbose=verbose)
        elif search_type == "hybrid":
            context_docs = hybrid_search(query, limit=10, verbose=verbose)
        else:
            context_docs = similarity_search(query, limit=10, verbose=verbose)

        if not context_docs:
            return "I couldn't find any relevant information to answer your question."

        if verbose:
            print(f"✅ Found {len(context_docs)} relevant documents")
            if context_docs:
                print(
                    f"📊 Distance range: {min(doc['distance'] for doc in context_docs):.3f} - {max(doc['distance'] for doc in context_docs):.3f}")

        # Step 2: Generate answer
        answer = generate_answer(query, context_docs, verbose=verbose, concise=concise)

        return answer

    except Exception as e:
        return f"Error processing query: {e}"


def check_database():

    try:
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM embeddings")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count
    except Exception as e:
        print(f"❌ Database error: {e}")
        return 0


def interactive_rag():

    print("🚀 ENHANCED RAG SYSTEM")
    print("=" * 60)

    # Check database
    count = check_database()
    if count == 0:
        print("❌ No data in database! Please run the PDF loader first.")
        return

    print(f"📊 Database has {count} embeddings ready")

    # Check Ollama
    try:
        ollama.list()
    except Exception:
        print("❌ Error: Ollama is not running. Please start Ollama with 'ollama serve'")
        return

    print("\n💬 Interactive Q&A Session")
    print("=" * 60)
    print("🎯 Search Modes:")
    print("  - Type your question normally for hybrid search (recommended)")
    print("  - Use 'vector:' prefix for vector-only search")
    print("  - Use 'detailed:' prefix for extended search with more context")
    print("  - Use 'extended:' prefix for maximum context retrieval")
    print("  - Use 'concise:' prefix for brief answers (1-2 lines)")
    print("\n🔧 Commands:")
    print("  - Type 'help' for example questions")
    print("  - Type 'verbose off/on' to toggle detailed output")
    print("  - Type 'quit' or 'exit' to stop")
    print()

    verbose = True

    while True:
        try:
            # Get user input
            user_input = input("\n❓ Your question: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break

            if user_input.lower() == 'help':
                print("\n💡 Example questions you could ask:")
                print("   - What is this document about?")
                print("   - What are the main topics discussed?")
                print("   - Can you summarize the key points?")
                print("   - What is the purpose of this proposal?")
                print("   - Who are the stakeholders mentioned?")
                print("   - What are the timeline and milestones?")
                print("   - What technical details are provided?")
                print("\n💡 Search mode examples:")
                print("   - vector: What is the main topic?")
                print("   - detailed: Explain all the technical specifications")
                print("   - extended: Give me comprehensive analysis")
                print("   - concise: What is the document about?")
                print("\n💡 Tips:")
                print("   - Default hybrid search works best for most questions")
                print("   - Use 'extended' for complex, multi-part questions")
                print("   - Use 'concise' when you need quick, brief answers")
                print()
                continue

            if user_input.lower() == 'verbose off':
                verbose = False
                print("✓ Verbose mode disabled")
                continue

            if user_input.lower() == 'verbose on':
                verbose = True
                print("✓ Verbose mode enabled")
                continue

            # Initialize default values
            search_type = "hybrid"
            detailed = False
            concise = False

            # Determine search type and clean query
            if user_input.lower().startswith('concise:'):
                search_type = "hybrid"
                query = user_input[8:].strip()
                concise = True
                if verbose:
                    print("🔍 Using concise mode for brief answers")
            elif user_input.lower().startswith('detailed:'):
                search_type = "hybrid"
                query = user_input[9:].strip()
                detailed = True
                if verbose:
                    print("🔍 Using detailed mode with extended context")
            elif user_input.lower().startswith('extended:'):
                search_type = "extended"
                query = user_input[9:].strip()
                if verbose:
                    print("🔍 Using extended search for maximum context")
            elif user_input.lower().startswith('vector:'):
                search_type = "similarity"
                query = user_input[7:].strip()
                if verbose:
                    print("🔍 Using vector similarity search only")
            else:
                query = user_input
                if verbose:
                    print("🔍 Using hybrid search (vector + keyword)")

            # Validate query
            if not query.strip():
                print("❌ Please provide a valid question after the prefix.")
                continue

            # Process query and generate answer
            answer = rag_pipeline(
                query,
                search_type=search_type,
                verbose=verbose,
                detailed=detailed,
                concise=concise
            )

            # Display answer
            if concise:
                print(f"\n💡 Concise Answer:")
                print("-" * 40)
                print(answer)
                print("-" * 40)
            else:
                print(f"\n💡 Answer:")
                print("-" * 60)
                print(answer)
                print("-" * 60)

        except KeyboardInterrupt:
            print("\n\n👋 Session ended. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("Please try again with a different question.")


def main():

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Enhanced RAG System with Extended Search and Concise Mode")
            print("\nUsage:")
            print("  python enhanced_rag.py           # Interactive mode")
            print("  python enhanced_rag.py --help    # Show this help")
            print("\nNew Features:")
            print("  - Extended search: More comprehensive context retrieval")
            print("  - Concise mode: Brief answers (1-2 lines)")
            print("  - Improved search modes: vector, hybrid, detailed, extended")
            print("\nRequirements:")
            print("  - PostgreSQL with pgvector")
            print("  - Ollama with nomic-embed-text and llama3")
            print("  - Python packages: psycopg2-binary, ollama")
            return

    # Run interactive RAG
    interactive_rag()


if __name__ == "__main__":
    main()