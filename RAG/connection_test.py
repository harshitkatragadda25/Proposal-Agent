
import psycopg2
import ollama
import os


def test_database():

    print("🔍 Testing database connection...")
    try:
        conn = psycopg2.connect(
            host='localhost',
            port='5434',
            database='proposalagentchatdb',
            user='postgres',
            password='Deadpool@123'
        )

        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM embeddings")
        count = cur.fetchone()[0]

        cur.close()
        conn.close()

        print(f"✅ Database connected! Current embeddings: {count}")
        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_ollama():

    print("\n🔍 Testing Ollama connection...")
    try:
        # Test basic connection
        models_response = ollama.list()
        print("✅ Ollama is running!")

        # Check response format
        print(f"📋 Raw response type: {type(models_response)}")

        # Handle different response types
        models = None

        if hasattr(models_response, 'models'):
            # ollama._types.ListResponse has a models attribute
            models = models_response.models
            print(f"📋 Found {len(models)} models (via .models attribute)")
        elif isinstance(models_response, dict) and 'models' in models_response:
            # Traditional dict response
            models = models_response['models']
            print(f"📋 Found {len(models)} models (via dict)")
        elif isinstance(models_response, list):
            # Direct list response
            models = models_response
            print(f"📋 Found {len(models)} models (direct list)")
        else:
            print(f"⚠️ Unexpected response type: {type(models_response)}")
            print(f"📋 Available attributes: {dir(models_response)}")
            return False

        if models:
            # Show first few models
            for i, model in enumerate(models[:3]):
                if hasattr(model, 'name'):
                    model_name = model.name
                elif isinstance(model, dict):
                    model_name = model.get('name') or model.get('model', 'Unknown')
                else:
                    model_name = str(model)
                print(f"   {i + 1}. {model_name}")

            # Check for nomic-embed-text
            model_names = []
            for model in models:
                if hasattr(model, 'name'):
                    model_names.append(model.name)
                elif isinstance(model, dict):
                    name = model.get('name') or model.get('model', '')
                    model_names.append(name)
                else:
                    model_names.append(str(model))

            print(f"📋 All model names: {model_names}")

            if any('nomic-embed-text' in name for name in model_names):
                print("✅ nomic-embed-text model is available!")
                return True
            else:
                print("⚠️ nomic-embed-text model not found")
                print("📥 Attempting to download...")
                try:
                    ollama.pull('nomic-embed-text')
                    print("✅ Model downloaded!")
                    return True
                except Exception as pull_error:
                    print(f"❌ Failed to download model: {pull_error}")
                    return False
        else:
            print("❌ Could not access models list")
            return False

    except Exception as e:
        print(f"❌ Ollama error: {e}")
        print("   Make sure Ollama is running with: ollama serve")
        return False


def test_pdf_file():

    pdf_path = r"D:\UMASS\CPT\Datasets\Dataset 1.pdf"
    print(f"\n🔍 Testing PDF file...")
    print(f"📄 Path: {pdf_path}")

    if os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        print(f"✅ PDF file found! Size: {file_size:,} bytes")
        return True
    else:
        print("❌ PDF file not found!")
        print("   Please check the file path")
        return False


def main():

    print("🧪 QUICK CONNECTION TEST")
    print("=" * 50)

    db_ok = test_database()
    ollama_ok = test_ollama()
    pdf_ok = test_pdf_file()

    print("\n📊 SUMMARY")
    print("=" * 30)
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"Ollama: {'✅' if ollama_ok else '❌'}")
    print(f"PDF File: {'✅' if pdf_ok else '❌'}")

    if db_ok and ollama_ok and pdf_ok:
        print("\n🎉 Everything looks good! You can process your PDF now.")
    else:
        print("\n⚠️ Please fix the issues above before processing your PDF.")


if __name__ == "__main__":
    main()