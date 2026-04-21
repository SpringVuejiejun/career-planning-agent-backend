from __future__ import annotations

import io
from typing import Optional, Tuple


def _ext(filename: Optional[str]) -> str:
    if not filename:
        return ""
    name = filename.lower().strip()
    if "." not in name:
        return ""
    return name.rsplit(".", 1)[-1]


def extract_text_from_upload(filename: Optional[str], content_type: Optional[str], raw: bytes) -> Tuple[str, str]:
    """
    尝试从上传的简历文件中提取文本。

    返回：(text, method)
    method: txt|pdf|docx|unknown
    """
    ext = _ext(filename)
    ct = (content_type or "").lower()

    # 纯文本（txt/md）
    if ext in ("txt", "md", "text") or ct.startswith("text/"):
        try:
            return raw.decode("utf-8"), "txt"
        except Exception:
            # 常见情况：gbk
            try:
                return raw.decode("gbk"), "txt"
            except Exception:
                return "", "txt"

    # PDF
    if ext == "pdf" or ct in ("application/pdf",):
        try:
            import fitz  # PyMuPDF
        except Exception:
            return "", "pdf"
        try:
            doc = fitz.open(stream=raw, filetype="pdf")
            parts = []
            for page in doc:
                parts.append(page.get_text("text"))
            text = "\n".join(parts).strip()
            return text, "pdf"
        except Exception:
            return "", "pdf"

    # DOCX
    if ext == "docx" or ct in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        try:
            from docx import Document  # python-docx
        except Exception:
            return "", "docx"
        try:
            bio = io.BytesIO(raw)
            doc = Document(bio)
            lines = []
            for p in doc.paragraphs:
                if p.text:
                    lines.append(p.text)
            # 也简单抓取表格文本
            for t in doc.tables:
                for row in t.rows:
                    cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
                    if cells:
                        lines.append(" | ".join(cells))
            text = "\n".join(lines).strip()
            return text, "docx"
        except Exception:
            return "", "docx"

    return "", "unknown"

