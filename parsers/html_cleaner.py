"""
HTML Cleaner
-----------
Utilities for cleaning and normalizing HTML content from scraped pages.

Handles:
- Removing scripts, styles, and unwanted tags
- Converting HTML entities
- Normalizing whitespace
- Extracting clean text
- Fixing common HTML issues
"""

import logging
import re
from html import unescape
from typing import Optional

from bs4 import BeautifulSoup

log = logging.getLogger(__name__)


def remove_unwanted_tags(html: str) -> str:
    """
    Remove unwanted HTML tags:
    - <script> tags (JavaScript)
    - <style> tags (CSS)
    - <noscript> tags
    - <iframe> tags
    - Comment tags
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Remove unwanted tag types
    for tag in soup(["script", "style", "noscript", "iframe", "meta", "link"]):
        tag.decompose()
    
    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")):
        comment.extract()
    
    return str(soup)


def clean_html(html: str) -> str:
    """
    Clean HTML content:
    - Remove scripts and styles
    - Convert entities
    - Fix common issues
    """
    if not html:
        return ""
    
    # Remove unwanted elements
    html = remove_unwanted_tags(html)
    
    # Convert HTML entities
    html = unescape(html)
    
    # Remove excessive whitespace
    html = re.sub(r"\s+", " ", html)
    html = re.sub(r">\s+<", "><", html)
    
    return html.strip()


def extract_text(
    html: str,
    strip_tags: bool = True,
    preserve_links: bool = False,
) -> str:
    """
    Extract clean text from HTML.
    
    Args:
        html: HTML content
        strip_tags: Whether to strip HTML tags first
        preserve_links: Whether to include link URLs
    
    Returns:
        Clean text content
    """
    if not html:
        return ""
    
    soup = BeautifulSoup(html, "lxml")
    
    if strip_tags:
        # Remove style/script first
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        
        text = soup.get_text(separator=" ", strip=True)
    else:
        # Get text with link preservation
        if preserve_links:
            for a in soup.find_all("a"):
                href = a.get("href", "")
                if href:
                    a.append(f" ({href})")
        
        text = soup.get_text(separator=" ", strip=True)
    
    # Normalize whitespace
    text = normalize_text(text)
    
    return text


def normalize_text(text: str) -> str:
    """
    Normalize text:
    - Collapse whitespace
    - Fix common issues
    - Trim
    """
    if not text:
        return ""
    
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    
    # Remove whitespace around punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    text = re.sub(r"([.,;:!?])\s+", r"\1 ", text)
    
    # Fix common HTML artifacts
    text = text.replace("\\xa0", " ")
    text = text.replace("\\u00a0", " ")
    
    return text.strip()


def extract_links(html: str, base_url: str = "") -> list[dict]:
    """
    Extract all links from HTML.
    
    Returns list of dicts with text and href.
    """
    soup = BeautifulSoup(html, "lxml")
    links = []
    
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        
        # Make absolute URL if base_url provided
        if base_url and not href.startswith(("http:", "https:", "mailto:")):
            from urllib.parse import urljoin
            href = urljoin(base_url, href)
        
        if text and href:
            links.append({"text": text, "href": href})
    
    return links


def extract_metadata(html: str) -> dict:
    """
    Extract metadata from HTML <head>:
    - Title
    - Meta description
    - Meta keywords
    - Open Graph tags
    """
    soup = BeautifulSoup(html, "lxml")
    
    metadata = {
        "title": None,
        "description": None,
        "keywords": None,
        "og_title": None,
        "og_description": None,
        "og_image": None,
    }
    
    # Get title
    title_tag = soup.find("title")
    if title_tag:
        metadata["title"] = title_tag.get_text(strip=True)
    
    # Get meta tags
    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower()
        property_ = meta.get("property", "").lower()
        content = meta.get("content", "")
        
        if name == "description":
            metadata["description"] = content
        elif name == "keywords":
            metadata["keywords"] = content
        elif property_ == "og:title":
            metadata["og_title"] = content
        elif property_ == "og:description":
            metadata["og_description"] = content
        elif property_ == "og:image":
            metadata["og_image"] = content
    
    return metadata


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to max length, adding suffix if truncated.
    
    Smart truncation - tries to break at word boundary.
    """
    if not text or len(text) <= max_length:
        return text
    
    # Leave room for suffix
    max_len = max_length - len(suffix)
    
    # Try to break at word boundary
    truncated = text[:max_len]
    last_space = truncated.rfind(" ")
    
    if last_space > max_len * 0.7:  # At least 70% of max
        truncated = truncated[:last_space]
    
    return truncated + suffix


def remove_html_tags(html: str) -> str:
    """
    Simple HTML tag removal (without BeautifulSoup).
    
    Faster for simple use cases.
    """
    # Remove HTML comments
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    
    # Remove script and style content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove all HTML tags
    html = re.sub(r"<[^>]+>", "", html)
    
    # Convert entities
    html = unescape(html)
    
    # Normalize whitespace
    html = re.sub(r"\s+", " ", html)
    
    return html.strip()


# Test examples
if __name__ == "__main__":
    sample_html = """
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <script>console.log('test');</script>
        <div class="content">
            <h1>Hello World</h1>
            <p>This is a test with &amp; and <special> chars.</p>
            <a href="https://example.com">Link</a>
        </div>
    </body>
    </html>
    """
    
    print("HTML Cleaner Test:")
    print("=" * 60)
    
    print("\n1. Clean HTML:")
    cleaned = clean_html(sample_html)
    print(cleaned[:200])
    
    print("\n2. Extract Text:")
    text = extract_text(sample_html)
    print(text)
    
    print("\n3. Extract Links:")
    links = extract_links(sample_html)
    print(links)
    
    print("\n4. Extract Metadata:")
    meta = extract_metadata(sample_html)
    print(meta)
