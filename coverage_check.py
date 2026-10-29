"""Reproduce the metadata completeness checks used to extend the original set.

This is a secondary retrieval signal, not a corpus eligibility classifier. A
historical mention can trigger it. Every positive was subsequently read from
the actual rule by corpus_audit.py. Residual titles were inspected separately.
"""
from pathlib import Path
import json
import re
import pandas as pd

# Frozen at retrieval time, separate from later source-classification patterns.
COVERAGE_SIGNAL = (r'\b(?:determin(?:e|es|ed|ing)|designat(?:e|es))\s+(?:(?:an?|the)\s+)?'
    r'(?:endangered|threatened)(?:\s+species)?\s+status\b|'
    r'\bdetermin(?:e|es|ed|ing)\s+.{0,450}?\s+(?:to be|is|are)\s+(?:an?\s+)?(?:endangered|threatened)\b|'
    r'\blist(?:s|ing)?\s+.{0,450}?\s+(?:as|to be)\s+(?:an?\s+)?(?:endangered|threatened)\b')


def check(root):
    root=Path(root)
    meta=json.loads((root/'sources/fws_rules.json').read_text())
    original=set(pd.read_csv(root/'sources/initial_296_candidates.csv').document_number)
    rows=[]
    for d in meta:
        if d['document_number'] in original or not d['title'].lower().startswith('endangered and threatened'):
            continue
        action=d['action'] or ''
        if not re.search(r'\bfinal rule\b',action,re.I) or re.search(r'emergency|interim|correct|reopen',action,re.I):
            continue
        summary=d['abstract'] or ''
        if re.search(COVERAGE_SIGNAL,summary,re.I) and not re.search(
                r'\b(?:delist|reclassif|remove|removing|withdraw|restor|reinstate|correct)',summary[:220],re.I):
            rows.append(d)
    found=pd.DataFrame(rows)
    frozen=set(pd.read_csv(root/'review/additional_candidate_metadata.csv').document_number)
    assert set(found.document_number)==frozen, 'The retrieval check differs from its frozen record.'
    print(f'{len(meta)} metadata records; {len(original)} original candidates; {len(found)} secondary source checks.')
    print('The residual-title worksheet records the separate check that identified the two follow-up files.')
    return found


if __name__=='__main__':
    check(Path(__file__).resolve().parent)
