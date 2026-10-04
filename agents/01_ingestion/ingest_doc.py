import sys
import os
import hashlib

def get_hash(filepath):
    hasher = hashlib.md5()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()[:8]

def extract_pdf(filepath):
    from PyPDF2 import PdfReader
    reader = PdfReader(filepath)
    text = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            text.append(t)
    return "\n".join(text)

def main():
    if len(sys.argv) < 2:
        print("Usage: ingest_doc.py <path_to_file>")
        sys.exit(1)
        
    filepath = sys.argv[1]
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)
        
    basename = os.path.basename(filepath)
    name, ext = os.path.splitext(basename)
    ext = ext.lower()
    
    out_name = f"{name}_{get_hash(filepath)}.txt"
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    out_dir = os.environ.get("APP_RAW_DIR", os.path.join(root_dir, "raw_transcripts"))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, out_name)
    
    if ext == '.pdf':
        text = extract_pdf(filepath)
    elif ext in ['.txt', '.md', '.csv']:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        print(f"Unsupported extension for ingestion: {ext}")
        sys.exit(1)
        
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
        
    print(f"Ingested {filepath} -> {out_path}")

if __name__ == "__main__":
    main()
