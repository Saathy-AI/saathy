import sys
sys.path.insert(0, 'src')

print("Testing chunking import...")
try:
    from saathy.chunking import ChunkingProcessor
    print("✅ Import successful")
    
    processor = ChunkingProcessor()
    print("✅ Processor created")
    
    text = "This is a test sentence. This is another test sentence."
    chunks = processor.chunk_content(text)
    print(f"✅ Chunking worked: {len(chunks)} chunks")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()