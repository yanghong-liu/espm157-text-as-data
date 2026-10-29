"""Small, inspectable helpers for the ESA notebook. No model or credentials required."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import time

import pandas as pd
import requests

BASE = "https://www.federalregister.gov/api/v1/documents.json"
START, END = "1996-01-01", "2025-12-31"
FIELDS = ["document_number", "title", "publication_date", "action", "raw_text_url",
          "html_url", "abstract", "type"]
EXPLICIT = re.compile(r"\b(?:climate\s+change|global\s+warming|climatic\s+change|changing\s+climate)\b", re.I)
BROADER = re.compile(r"\b(?:sea[ -]level\s+rise|rising\s+sea\s+levels?|ocean\s+acidification)\b", re.I)


def rule_text_content(raw):
    """Read the rule's PRE text, leaving original cached responses untouched.

    Federal Register raw_text_url sometimes returns a GovInfo HTML wrapper.
    Decode HTML entities/tags before splitting passages, not after labeling.
    """
    if not re.search(r'<pre(?:\s|>)', raw, re.I):
        return raw.replace('\x00', '')
    class PreText(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.depth, self.parts = 0, []
        def handle_starttag(self, tag, attrs):
            if tag.lower() == 'pre':
                self.depth += 1
        def handle_endtag(self, tag):
            if tag.lower() == 'pre':
                self.depth -= 1
                self.parts.append('\n')
        def handle_data(self, data):
            if self.depth:
                self.parts.append(data)
    parser = PreText()
    parser.feed(raw)
    return ''.join(parser.parts).replace('\x00', '')


def fetch(url, params=None, attempts=4):
    """Retry transient failures, without hiding an unsuccessful download."""
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=(10, 30),
                                    headers={"User-Agent": "ESPM157-student-research/1.0"})
        except (requests.Timeout, requests.ConnectionError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)
            continue
        if response.status_code not in (429, 500, 502, 503, 504):
            response.raise_for_status()
            return response
        if attempt < attempts - 1:
            time.sleep(2 ** attempt)
    response.raise_for_status()


def collect_metadata(root, refresh=False):
    """Retrieve ALL FWS rules, then screen locally; do not search on climate words."""
    root = Path(root)
    path = root / "sources/fws_rules.json"
    if path.exists() and not refresh:
        return pd.DataFrame(json.loads(path.read_text()))
    params = {"conditions[agencies][]": "fish-and-wildlife-service",
              "conditions[type][]": "RULE", "conditions[publication_date][gte]": START,
              "conditions[publication_date][lte]": END, "per_page": 1000,
              "order": "oldest", "fields[]": FIELDS}
    rows, page, expected, urls = [], 1, None, []
    while True:
        response = fetch(BASE, {**params, "page": page})
        payload = response.json()
        expected = payload["count"] if expected is None else expected
        if payload["count"] != expected:
            raise RuntimeError("The API changed during pagination. Refresh and try again.")
        rows.extend(payload["results"])
        urls.append(response.url)
        if not payload.get("next_page_url"):
            break
        page += 1
    if len(rows) != expected or len({r["document_number"] for r in rows}) != expected:
        raise RuntimeError("Missing or duplicate metadata records; inspect pagination.")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    (path.parent / "retrieval_manifest.json").write_text(json.dumps({
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_record_count": expected, "query_urls": urls,
        "scope": {"agency": "FWS", "start": START, "end": END, "type": "RULE"},
        "metadata_sha256": sha256(path.read_bytes()).hexdigest()}, indent=2))
    return pd.DataFrame(rows)


def title_screen(title, action):
    """A transparent PROVISIONAL screen, never a substitute for source review."""
    title = re.sub(r"^Endangered and Threatened Wildlife and Plants\s*[;:,.]?\s*", "", title, flags=re.I)
    excluded = re.search(r"delist|reclassif|remov(?:al|ing|e).*?(?:list|status)|withdraw|correct|"
                         r"technical amend|experimental population|listing priority|emergency|"
                         r"reinstat|extension of.*effective|delay.*effective", title, re.I)
    if excluded:
        return "exclude_other_action", excluded.group()
    positive = re.search(r"determin(?:ation|e|ing).*?(?:endangered|threatened)|"
                         r"(?:endangered|threatened) (?:species )?status (?:for|of)|"
                         r"\blisting (?:of |the |as |endangered|threatened)|"
                         r"(?:endangered|threatened) listing|final rule to list", title, re.I)
    if positive:
        if not re.search(r"final rule|final determination", action, re.I):
            return "needs_title_review", "listing title signal, but action is not clearly a final rule"
        return "candidate_initial_listing", positive.group()
    if re.search(r"critical habitat|hunting|migratory bird|incidental take|refuge|"
                 r"subsistence|convention|injurious wildlife|permit|importation|export|"
                 r"fishing|civil penalt|special rule|4\(d\) rule", title, re.I):
        return "exclude_other_action", "other rule without an initial-listing title signal"
    return "needs_title_review", "no confident automatic decision"


def screen_metadata(metadata, root):
    screened = metadata.copy()
    screened[["screen_status", "screen_reason"]] = pd.DataFrame(
        [title_screen(str(t), str(a)) for t, a in zip(screened.title, screened.action)],
        index=screened.index)
    screened["included"] = screened.screen_status.eq("candidate_initial_listing")
    screened['audit_status'] = 'metadata/title screen only'
    audit_path = Path(root)/'review/corpus_audit.csv'
    if audit_path.exists():
        audit = pd.read_csv(audit_path, keep_default_na=False)
        if not audit.document_number.is_unique:
            raise ValueError('Audit contains duplicate document identifiers.')
        for row in audit.itertuples():
            mask = screened.document_number.eq(str(row.document_number))
            if mask.sum() != 1 or screened.loc[mask,'title'].iloc[0] != row.title:
                raise ValueError('Audit and metadata snapshot disagree; rerun the corpus audit.')
            screened.loc[mask,'included'] = row.audit_decision == 'include'
            screened.loc[mask,'audit_status'] = row.audit_decision
    screened["year"] = pd.to_datetime(screened.publication_date).dt.year
    return screened


def download_texts(documents, root):
    cache = Path(root) / "data/rule_text"
    cache.mkdir(parents=True, exist_ok=True)
    def download(row):
        path = cache / f"{row['document_number']}.txt"
        receipt = cache / f"{row['document_number']}.source.json"
        if not path.exists():
            # Both services identify the same Federal Register document. The
            # official GovInfo archive avoids intermittent full_text timeouts.
            source_url = (f"https://www.govinfo.gov/content/pkg/FR-{row['publication_date']}/"
                          f"html/{row['document_number']}.htm")
            try:
                response = fetch(source_url)
            except (requests.Timeout, requests.ConnectionError):
                source_url = row['raw_text_url']
                response = fetch(source_url)
            except requests.HTTPError as error:
                if error.response.status_code not in (404, 408, 429, 500, 502, 503, 504):
                    raise
                source_url = row['raw_text_url']
                response = fetch(source_url)
            text = response.content.decode('utf-8', errors='replace')
            clean = rule_text_content(text)
            if row['document_number'] not in clean[:2500]:
                raise ValueError(f"Downloaded document identifier does not match: {source_url}")
            path.write_text(text)
            receipt.write_text(json.dumps({"document_number": row['document_number'],
                "text_source_url": source_url, "sha256": sha256(path.read_bytes()).hexdigest(),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat()}, indent=2))
        elif not receipt.exists():
            receipt.write_text(json.dumps({"document_number": row['document_number'],
                "text_source_url": row['raw_text_url'],
                "sha256": sha256(path.read_bytes()).hexdigest(),
                "cache_file_created_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()}, indent=2))
        return row["document_number"], rule_text_content(path.read_text())
    # Four workers keep the public service load modest. Errors stop the analysis.
    with ThreadPoolExecutor(max_workers=4) as pool:
        texts = dict(pool.map(download, documents.to_dict("records")))
    receipts = [json.loads((cache / f"{doc}.source.json").read_text()) for doc in texts]
    pd.DataFrame(receipts).to_csv(Path(root) / 'sources/text_download_manifest.csv', index=False)
    return texts


def passage_table(documents, texts, max_chars=1200):
    """Split raw blank-line blocks into short sentence-boundary passages.

    Old text files sometimes use blank lines for page breaks, not true paragraphs.
    Every passage records its original block and character offsets after whitespace
    normalization. Long individual sentences are retained rather than truncated.
    """
    records = []
    for doc in documents.to_dict("records"):
        text = texts[doc["document_number"]]
        blocks = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
        passages = []
        for block_number, block in enumerate(blocks, start=1):
            if not block:
                continue
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", block)
            chunks, current = [], ''
            for sentence in sentences:
                if current and len(current) + len(sentence) + 1 > max_chars:
                    chunks.append(current)
                    current = sentence
                else:
                    current = f'{current} {sentence}'.strip()
            if current:
                chunks.append(current)
            offset = 0
            for chunk in chunks:
                start = block.find(chunk, offset)
                assert start >= 0, 'A passage must be a literal normalized source substring.'
                passages.append((chunk, block_number, start, start + len(chunk)))
                offset = start + len(chunk)
        for i, (passage, block_number, start, end) in enumerate(passages):
            records.append({"document_number": doc["document_number"], "year": doc["year"],
                "passage_id": f"{doc['document_number']}:p{i+1:04d}", "passage_number": i+1,
                "source_block": block_number, "normalized_block_char_start": start,
                "normalized_block_char_end": end,
                "title": doc["title"], "source_url": doc["html_url"], "text": passage,
                "previous_passage": passages[i-1][0] if i else "",
                "next_passage": passages[i+1][0] if i+1 < len(passages) else "",
                "explicit_match": bool(EXPLICIT.search(passage)),
                "broader_match": bool(BROADER.search(passage))})
    return pd.DataFrame(records)


def delach_data(root):
    root = Path(root)
    files = {"delach_discussion.csv": "https://osf.io/download/76ytr/",
             "delach_metadata.csv": "https://osf.io/download/4bm8u/"}
    for name, url in files.items():
        path = root / "sources" / name
        if not path.exists():
            path.write_bytes(fetch(url).content)
    return pd.read_csv(root / "sources/delach_discussion.csv")
