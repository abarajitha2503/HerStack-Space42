from pathlib import Path
from pypdf import PdfReader

def parse_cv(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    
    if suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")
    
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text() or "")
        return "\n".join(texts).strip()
    
    return ""