"""Retrieve source passages, validate saved classifications, and summarize evidence."""
from hashlib import sha256
from pathlib import Path
import re

import numpy as np
import pandas as pd

ALIASES = re.compile(
    r'\b(?:climatic\s+changes?|climate[-\s]+changes?|warming\s+climate|'
    r'climate\s+warming|changes?\s+in\s+(?:the\s+)?climate|'
    r'greenhouse\s+(?:gases|gas|effect))\b', re.I)
LABELS = ['agency_threat', 'mention_only', 'uncertain', 'no_search_evidence']
RISK = re.compile(r'threat|risk|extinct|extirpat|declin|loss|degrad|adverse|negativ|'
                  r'harm|detriment|vulnerab|reduc|impact|affect', re.I)
AGENCY = re.compile(r'\bwe (?:find|found|conclude|determin|consider|expect|anticipat|'
                    r'identif|project|believe|recogniz)|\bour (?:analysis|assessment|'
                    r'evaluation|review|finding)|\bService (?:finds|considers|concludes)', re.I)


def reading_rank(text):
    """Prioritize reading, not classify a threat. Negation and voices need interpretation."""
    return (8 * bool(AGENCY.search(text))
            + 3 * bool(re.search(r'climate change.{0,130}(?:threat|risk)|'
                                 r'threat.{0,130}climate change', text, re.I))
            + min(5, len(RISK.findall(text)))
            + 2 * bool(re.search(r'\bspecies\b|\bsubspecies\b|\bDPS\b', text, re.I))
            - 5 * bool(re.search(r'\bcomment(?:er|or)s?\b|\breviewer\b', text, re.I))
            - 8 * bool(re.search(r'\b(?:IPCC|United Nations|biodiversity)\b', text, re.I)))


def retrieve_evidence(passages):
    table = passages.copy()
    table['alias_match'] = table.text.map(lambda text: bool(ALIASES.search(text)))
    table = table[table.explicit_match | table.broader_match | table.alias_match].copy()
    table['reading_rank'] = table.text.map(reading_rank)
    table['retrieval_method'] = 'regex union: original phrases, broader mechanisms, additional aliases'
    return table.sort_values(['year', 'document_number', 'passage_number'])


def replay_judgments(corpus, passages, evidence, root):
    """Reject missing or stale evidence rather than silently applying a changed annotation."""
    root = Path(root)
    saved = pd.read_csv(root/'review/document_classifications.csv', keep_default_na=False)
    assert saved.document_number.is_unique
    assert set(saved.document_number) == set(evidence.document_number), 'Review new retrieval candidates.'
    assert saved.classification.isin(LABELS[:3]).all()
    lookup = passages.set_index('passage_id')
    for row in saved.itertuples():
        source = lookup.loc[row.evidence_passage_id]
        assert source.document_number == row.document_number
        assert source.text == row.evidence_text
        assert sha256(source.text.encode()).hexdigest() == row.evidence_sha256
        assert source.source_url == row.source_url
        assert row.reason
        for context_id in filter(None, row.context_passage_ids.split(';')):
            assert lookup.loc[context_id, 'document_number'] == row.document_number
    documents = corpus[['document_number', 'year', 'title', 'html_url']].merge(
        saved, on='document_number', how='left', validate='one_to_one')
    documents['classification'] = documents.classification.fillna('no_search_evidence')
    reviews = pd.read_csv(root/'review/passage_labels.csv', keep_default_na=False)
    assert reviews.passage_id.is_unique
    for row in reviews.itertuples():
        source = lookup.loc[row.passage_id]
        assert source.document_number == row.document_number
        assert sha256(source.text.encode()).hexdigest() == row.evidence_sha256
        assert source.source_url == row.source_url
        assert row.human_label in LABELS[:3] and row.reviewer and row.reason and row.review_context
        for context_id in filter(None, row.context_passage_ids.split(';')):
            assert lookup.loc[context_id, 'document_number'] == row.document_number
        if not row.document_resolution:
            continue
        # One supported positive passage can establish a document-level contribution.
        # A passage-level negative would not establish absence throughout the rule.
        assert row.document_resolution == row.human_label == 'agency_threat'
        mask = documents.document_number.eq(row.document_number)
        assert mask.sum() == 1
        for column, value in {
            'classification': row.document_resolution,
            'evidence_passage_id': row.passage_id,
            'evidence_text': source.text,
            'evidence_sha256': row.evidence_sha256,
            'context_passage_ids': row.context_passage_ids,
            'reason': row.reason,
            'source_url': row.source_url
        }.items():
            documents.loc[mask, column] = value
    counts = evidence.groupby('document_number').agg(
        searched_passages=('passage_id','size'), explicit_hit_passages=('explicit_match','sum'),
        broader_hit_passages=('broader_match','sum'), alias_hit_passages=('alias_match','sum'))
    documents = documents.merge(counts, left_on='document_number', right_index=True,
                                how='left', validate='one_to_one')
    documents.to_csv(root/'results/agency_threat_documents.csv', index=False)
    annual = pd.crosstab(documents.year, documents.classification).reindex(
        index=range(1996,2026), columns=LABELS, fill_value=0)
    annual['rules'] = annual[LABELS].sum(axis=1)
    annual['source_supported_fraction'] = annual.agency_threat / annual.rules.replace(0,np.nan)
    annual['supported_plus_uncertain_fraction'] = (annual.agency_threat + annual.uncertain) / annual.rules.replace(0,np.nan)
    annual.to_csv(root/'results/annual_agency_evidence.csv', index_label='year')
    documents['period'] = pd.cut(documents.year, [1995,2005,2015,2025],
                                 labels=['1996–2005','2006–2015','2016–2025'])
    periods = pd.crosstab(documents.period, documents.classification).reindex(columns=LABELS,fill_value=0)
    periods['rules'] = periods[LABELS].sum(axis=1)
    periods['source_supported_fraction'] = periods.agency_threat/periods.rules
    periods.to_csv(root/'results/period_agency_evidence.csv', index_label='period')
    export_columns = ['document_number','year','passage_id','source_block',
        'normalized_block_char_start','normalized_block_char_end','source_url','text',
        'explicit_match','broader_match','alias_match','reading_rank']
    evidence[export_columns].to_csv(root/'results/retrieved_climate_evidence.csv',index=False)
    return documents, annual, periods


def independent_cases(documents, delach, root):
    """A purposive source comparison, not a representative agreement/accuracy estimate."""
    root = Path(root)
    audit = pd.read_csv(root/'review/corpus_audit.csv', keep_default_na=False).set_index('document_number')
    labels = documents.set_index('document_number')
    cases = [
        ('02-20339','Antrobia culveri'), ('03-5076','Brachylagus idahoensis'),
        ('2016-23945','Cicindelidia floridana'), ('2017-00195','Bombus affinis'),
        ('2013-23401','Eumops floridanus')]
    rows = []
    for doc, name in cases:
        match = delach[delach.Scientific_Name.str.strip().str.casefold().eq(name.casefold())]
        assert len(match) == 1
        other = match.iloc[0]
        summary = audit.loc[doc, 'official_summary']
        assert name.casefold() in summary.casefold(), 'Verify the actual listing target.'
        row = labels.loc[doc]
        rows.append({'document_number':doc, 'Scientific_Name':name,
            'Common_Name':other.Common_Name, 'listing_rule_year':int(row.year),
            'Delach_most_recent_document_year':int(other.Date),
            'Delach_CC_Discuss':other.CC_Discuss, 'rule_label':row.classification,
            'source_target_evidence':summary, 'climate_evidence_passage_id':row.evidence_passage_id,
            'source_url':row.html_url})
    result = pd.DataFrame(rows)
    result.to_csv(root/'review/independent_source_cases.csv',index=False)
    return result


def scope_sensitivity(documents, root):
    """Measure stated scope/label choices; these are not statistical error bounds."""
    root = Path(root)
    audit = pd.read_csv(root/'review/corpus_audit.csv', keep_default_na=False)
    joined = documents.merge(audit[['document_number','audit_category']],
                              on='document_number', validate='one_to_one')
    scenarios = [
        ('Recorded scope', joined, ['agency_threat'], 'Baseline'),
        ('Exclude new geographic/population protection',
         joined[joined.audit_category.ne('new_geographic_protection')],
         ['agency_threat'], 'Corpus choice'),
        ('Exclude first permanent rules after temporary emergencies',
         joined[joined.audit_category.ne('first_permanent_after_emergency')],
         ['agency_threat'], 'Corpus choice'),
        ('Count unresolved interpretations as risk findings', joined,
         ['agency_threat','uncertain'], 'Label choice; not an error bound')]
    rows = []
    for name, group, counted_labels, choice in scenarios:
        count = int(group.classification.isin(counted_labels).sum())
        rows.append({'scenario':name, 'counted_risk_rules':count, 'rules':len(group),
                     'fraction':count/len(group), 'choice_type':choice})
    result = pd.DataFrame(rows)
    result.to_csv(root/'results/scope_sensitivity.csv',index=False)
    return result
