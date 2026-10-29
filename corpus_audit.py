"""Evidence-backed audit of the original 296 candidates; judgments are automated.

This is an audit of corpus eligibility, not a climate-threat classifier. See the
saved policy cases for decisions that affect the definition of an initial listing.
"""
from hashlib import sha256
from pathlib import Path
import json
import re
import pandas as pd
from esa_tools import rule_text_content

NEW_STATUS = (r'\b(?:determin(?:e|es|ed|ing)|designat(?:e|es))\s+(?:(?:an?|the)\s+)?'
              r'(?:endangered|threatened)(?:\s+species)?\s+status\b|'
              r'\b(?:determin(?:e|es|ed|ing)|designat(?:e|es))\s+.{0,450}?\s+(?:to be|is|are|as)\s+(?:an?\s+)?'
              r'(?:endangered|threatened)\b|'
              r'\bdetermin(?:e|es|ed|ing)\s+.{0,450}?\s+meets? the definition of (?:an? )?(?:endangered|threatened)(?: species)?\b|'
              r'\blist(?:s|ing)?\s+.{0,450}?\s+(?:as|to be)\s+(?:an?\s+)?'
              r'(?:endangered|threatened)\b')


def norm(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def summary_from_text(text):
    m = re.search(r'\bSUMMARY:\s*(.*?)(?=\n\s*(?:DATES?|EFFECTIVE\s+DATE|ADDRESSES?|FOR\s+FURTHER|SUPPLEMENTARY)\s*:)', text, re.I | re.S)
    return norm(m.group(1)) if m else ''


def assess(title, action, summary, text, document_number):
    """Return eligibility, category, rationale, and an evidence regex.

    Order matters. For example, a notice can say 'final rule' while only
    reopening comments. Previously protected species can have status titles.
    """
    s = summary
    short_title = re.sub(r'^Endangered and Threatened[^;:]*[;:]\s*', '', title, flags=re.I)
    if re.search(r'CNMI.{0,100}to be a threatened species',s,re.I) and re.search(r'listed previously as endangered on Guam',s,re.I):
        return ('needs_scope_policy', 'new_geographic_protection',
                'Adds previously unlisted CNMI populations while changing the existing Guam status.',
                r'determine the Mariana fruit bat.{0,850}')
    if re.search(r'reclassify the broad- snouted caiman|reclassify the broad-snouted caiman',s,re.I) and re.search(r'second DPS remains listed',s,re.I):
        return ('exclude', 'status_reclassification',
                'Downlists Argentina and retains the existing endangered status of the other caiman DPS.',
                r'reclassify.{0,850}')
    if re.search(r'Removed From the List',short_title,re.I) or (re.search(r'^Final Rule Designating',short_title,re.I) and re.search(r'Removing.{0,250}List',short_title,re.I)):
        return ('exclude', 'delisting',
                'Present action removes an existing listing; historical listing references are not new decisions.',
                r'(?:remov\w*).{0,750}')
    if re.search(r'currently (?:endangered|threatened).{0,250}(?:split|two distinct)',s,re.I):
        return ('exclude', 'taxonomy_update',
                'Splits an already protected taxon and retains or changes existing statuses, without first granting protection.',
                r'currently (?:endangered|threatened).{0,800}')
    if re.search(r'supersedes the 1978 final listing rule for green turtles',s,re.I):
        return ('exclude', 'existing_listing_resegmented',
                'Replaces an existing global turtle listing with DPS classifications and applies existing protections.',
                r'This rule supersedes.{0,700}')
    if (re.search(r'loggerhead sea turtle',s,re.I)
            and re.search(r'nine distinct population segments',s,re.I)
            and re.search(r'listing the loggerhead sea turtle as threatened throughout its worldwide range on July 28,\s*1978',norm(text),re.I)):
        return ('exclude', 'existing_listing_resegmented',
                'Replaces the loggerhead turtle\'s existing worldwide 1978 protection with nine DPS classifications; no previously unprotected range is added.',
                r'We issued a final rule listing the loggerhead sea turtle.{0,220}')
    if re.search(r'making a separate entry for the Mexican wolf',s,re.I):
        return ('exclude', 'previously_listed_subspecies',
                'Gives a separate entry to the Mexican wolf, already independently listed in 1976.',
                r'We listed the Mexican gray wolf.{0,550}')
    if re.search(r'taxonomic revision of the Chiricahua leopard frog',s,re.I):
        return ('exclude', 'taxonomy_update',
                'Updates the taxonomic scope of the already listed frog and designates habitat.',
                r'because of a taxonomic revision.{0,700}')
    if re.search(r'^(?:Final (?:Rule To |Rule |Designation of |Determination of ))?(?:Delist|Remov)', short_title, re.I):
        return ('exclude', 'delisting',
                'Removes a previously listed taxon; no initial listing.',
                r'(?:remov\w*|delist\w*).{0,700}')
    if re.search(r'^(?:Reclassif|Change in Listing Status)', short_title, re.I):
        return ('exclude', 'status_reclassification',
                'Reclassifies a previously listed taxon rather than making an initial listing.',
                r'(?:reclassif\w*|chang\w*).{0,700}')
    if re.search(r'^Reinstatement', short_title, re.I):
        return ('exclude', 'reinstatement',
                'Restores protections previously in effect.',
                r'(?:reinstat\w*|court order).{0,700}')
    if re.search(r'^(?:Final )?(?:Designation|Determination) of Critical Habitat', short_title, re.I):
        return ('exclude', 'habitat_only_rule',
                'Designates critical habitat for an existing listed taxon.',
                r'(?:designat\w*|critical habitat).{0,700}')
    if re.search(r'^(?:Special Rule|Designated Ports|Revision to the Regulations for the Nonessential Experimental Population)', short_title, re.I):
        return ('exclude', 'standalone_implementing_rule',
                'A standalone trade, port, 4(d), or experimental-population rule, not an initial risk-based listing.',
                r'.{1,850}')
    if re.search(r'^Taxonom(?:ic|ical)', short_title, re.I):
        return ('exclude', 'taxonomy_update',
                'Updates the taxonomy of an already protected taxon.',
                r'.{1,850}')
    if re.search(r'we are removing.{0,150}from the list', s, re.I) and re.search(r'published a final rule|previous final decision',s,re.I):
        return ('exclude', 'delisting_after_remand',
                'The summary recounts a past listing but the present action removes it.',
                r'we are removing.{0,700}')
    if re.search(r'eliminates the separate classification of captive and wild chimpanzees',s,re.I):
        return ('exclude', 'status_reclassification',
                'Unifies existing captive/wild chimpanzee classifications, not their first protection.',
                r'eliminates the separate classification.{0,650}')
    if re.search(r'Convention on International Trade|\bCITES\b', title, re.I) and not title.lower().startswith('endangered and threatened'):
        return ('exclude', 'cites_trade_rule',
                'A CITES Appendix III trade-list amendment, not an ESA listing.',
                r'This rule announces an amendment.{0,700}')
    if re.search(r'Injurious Wildlife Species', title, re.I) and re.search(r'injurious fish', s, re.I):
        return ('exclude', 'not_esa_listing',
                'An injurious-wildlife restriction, not an ESA endangered/threatened listing.',
                r'adds the bighead carp.{0,600}')
    if re.search(r'delaying the effective date|delay of effective date', action + ' ' + s, re.I):
        return ('exclude', 'effective_date_delay',
                'Only delays the effective date of a previously published rule.',
                r'delaying the effective date.{0,650}')
    if re.search(r'^C\d*-', document_number, re.I) and re.search(r'\bCorrection\b', text[:6000]):
        return ('exclude', 'correction',
                'Correction to an existing rule, not a new initial listing.',
                r'In the rule document.{0,350}correction')
    if re.search(r'reopen|opening.*comment period', action + ' ' + s[:700], re.I):
        return ('exclude', 'comment_period_notice',
                'Reopens comments on an earlier decision; does not finalize a new listing.',
                r'(?:reopening|opening).{0,250}comment period|comment period.{0,350}')
    generic = re.search(r'(?:regulations for )?listing endangered and threatened species and designating critical habitat', title, re.I)
    if generic and re.search(r'our regulations|the regulations|regulatory definition', s, re.I):
        return ('exclude', 'general_regulations',
                'Changes general listing/habitat regulations rather than listing a particular taxon.',
                r'(?:finalize revisions|amend portions|add a definition|rescind the final rule).{0,700}')
    if re.search(r'corresponds with a determination.{0,200}National Marine Fisheries Service', s, re.I):
        return ('exclude', 'nmfs_administrative_codification',
                'FWS administratively inserts an NMFS-jurisdiction decision rather than issuing its own original threat determination.',
                r'is adding.{0,900}')
    if re.search(r'\breclassif(?:y|ies|ying)\b', s[:500], re.I) and re.search(r'from a threatened to an endangered|from threatened to endangered', s, re.I):
        return ('exclude', 'status_reclassification',
                'Changes an already threatened species to endangered.',
                r'(?:reclassify|reclassifying).{0,650}')
    if re.search(r'We are removing the WGL DPS from the List', s, re.I):
        return ('exclude', 'delisting',
                'Removes the Western Great Lakes wolf DPS from the list.',
                r'We are removing.{0,450}')
    if re.search(r'affirmation of a previously published final rule', s, re.I):
        return ('exclude', 'affirmation_of_prior_rule',
                'Affirms an already published final listing instead of making its first decision.',
                r'(?:affirm our determination|affirmation of a previously published).{0,650}')
    if re.search(r'maintains this species as a threatened species', s, re.I):
        return ('exclude', 'status_continuation',
                'Maintains an existing listing and revises its 4(d) rule.',
                r'(?:affirm the listing|maintains this species).{0,650}')
    if re.search(r'effect of this regulation is to reinstate', s, re.I):
        return ('exclude', 'reinstatement',
                'Reinstates a prior listing after a court vacated it.',
                r'(?:was added to the List|effect of this regulation is to reinstate).{0,750}')
    if re.search(r'This action revises the CFR to reflect a March 6, 2008, court order', s):
        return ('exclude', 'court_order_restoration',
                'Restores the Sonoran Desert bald-eagle status and former special rule under a court order.',
                r'(?:reinstating|This action revises).{0,650}')
    if re.search(r'amends the current listing|including those that were already listed|coupled with our earlier findings',s,re.I):
        return ('needs_scope_policy', 'new_geographic_protection',
                'Combines already listed populations with newly covered populations or range.',
                r'(?:amends the current listing|including those that were already listed|coupled with our earlier findings).{0,650}')
    if re.search(r'taxonomic reclassification|making a separate entry|supersedes the 1978 final listing rule', s, re.I):
        return ('needs_scope_policy', 'previously_protected_taxon_or_dps',
                'Definition-sensitive: separates or changes the extent of an already protected taxon/DPS.',
                r'(?:taxonomic reclassification|amends the current listing|making a separate entry|including those that were already listed|supersedes the 1978 final listing rule|coupled with our earlier findings).{0,500}')
    if re.search(r'now also listed as endangered in the United States|currently listed as endangered throughout its range except in the United States', s, re.I):
        return ('needs_scope_policy', 'new_geographic_protection',
                'Extends an already listed species\' protection to a previously uncovered geographic area.',
                r'(?:extends endangered status|currently listed as endangered|now also listed).{0,650}')
    if re.search(r'similarity (?:of|in) appearance', s, re.I):
        # These two titles concern only 4(e) appearance-based protection. Mixed
        # rules with an independently listed threatened/endangered target remain eligible.
        if re.search(r'Shovelnose Sturgeon|Southern White Rhino', title, re.I):
            return ('needs_scope_policy', 'pure_similarity_of_appearance',
                    'Only appearance-based protection under section 4(e); the protected species is not itself found endangered/threatened.',
                    r'(?:treat shovelnose|due to the similarity|due to similarity).{0,650}')
    positive = re.search(NEW_STATUS, s, re.I)
    if positive:
        if re.search(r'temporary emergency listing|emergency listed', s, re.I):
            category = 'first_permanent_after_emergency'
            reason = 'First permanent final listing following explicitly temporary emergency protection.'
        elif re.search(r'similarity (?:of|in) appearance|reaffirm|taxonomic (?:change|revision)|also delisting', s, re.I):
            category = 'initial_listing_with_other_actions'
            reason = 'Makes a new initial listing and also contains other actions; counted once as a document.'
        else:
            category, reason = 'initial_listing', 'Official summary explicitly makes an endangered/threatened listing determination.'
        return ('include', category,
                reason,
                positive.re.pattern)
    return ('needs_source_review', 'insufficient_summary_signal',
            'No automatic eligibility conclusion; inspect the rule.',
            r'.{1,750}')


def run_audit(root, document_numbers=None):
    root = Path(root)
    # The original snapshot is frozen independently of subsequent corpus decisions.
    original_path = root / 'sources/initial_296_candidates.csv'
    if not original_path.exists():
        pd.read_csv(root / 'results/keyword_baseline.csv')[['document_number']].to_csv(original_path, index=False)
    original_ids = pd.read_csv(original_path).document_number.tolist()
    original = original_ids if document_numbers is None else document_numbers
    metadata = {d['document_number']: d for d in json.loads((root/'sources/fws_rules.json').read_text())}
    policy_path = root/'review/corpus_policy.json'
    policies = json.loads(policy_path.read_text()) if policy_path.exists() else {}
    output = []
    for document_number in original:
        d = metadata[document_number]
        raw = (root/'data/rule_text'/f'{document_number}.txt').read_text()
        text = rule_text_content(raw)
        receipt = json.loads((root/'data/rule_text'/f'{document_number}.source.json').read_text())
        summary = summary_from_text(text)
        assert document_number in text[:2500], f'Unexpected source identifier: {document_number}'
        decision, category, reason, pattern = assess(d['title'], d['action'] or '', summary, text, document_number)
        section = 'SUMMARY' if summary else 'opening/body'
        evidence_source = summary if summary else norm(text)
        match = re.search(pattern, evidence_source, re.I)
        if not match and re.search(pattern,norm(text),re.I):
            evidence_source, section = norm(text), 'body (normalized full text)'
            match = re.search(pattern,evidence_source,re.I)
        if not match:
            match = re.search(r'.{1,900}', evidence_source, re.S)
        start, end = match.span()
        # Widen a short hit for context without inventing or rewriting quotations.
        start, end = max(0,start-150), min(len(evidence_source), max(end,start+500))
        evidence = evidence_source[start:end]
        assert evidence == evidence_source[start:end]
        automatic_decision = decision
        applied_policy = policies.get(category, {})
        if decision == 'needs_scope_policy' and applied_policy.get('decision') in ('include','exclude'):
            decision = applied_policy['decision']
        output.append({**d, 'initial_candidate': document_number in original_ids,
            'automatic_decision': automatic_decision, 'audit_decision': decision,
            'audit_category': category, 'reason_en': reason,
            'evidence_section': section, 'evidence_start': start, 'evidence_end': end,
            'evidence_text': evidence, 'official_summary': summary,
            'text_source_url': receipt['text_source_url'],
            'cached_response_sha256': sha256((root/'data/rule_text'/f'{document_number}.txt').read_bytes()).hexdigest(),
            'clean_text_sha256': sha256(text.encode()).hexdigest()})
    audit = pd.DataFrame(output)
    return audit


if __name__ == '__main__':
    import argparse
    from esa_tools import download_texts
    parser = argparse.ArgumentParser()
    parser.add_argument('--download', action='store_true', help='Download cached sources first, needed on a fresh clone.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    groups = [pd.read_csv(root/'sources/initial_296_candidates.csv').document_number.tolist(),
              pd.read_csv(root/'review/additional_candidate_metadata.csv').document_number.tolist(),
              ['05-240','2013-15006']]
    ids = [doc for group in groups for doc in group]
    assert len(ids) == len(set(ids)), 'Audit groups must not overlap.'
    if args.download:
        metadata = pd.DataFrame(json.loads((root/'sources/fws_rules.json').read_text()))
        download_texts(metadata[metadata.document_number.isin(ids)],root)
    audit = run_audit(root, ids)
    audit.to_csv(root/'review/corpus_audit.csv',index=False)
    print(audit.groupby(['initial_candidate','audit_decision']).size().to_string())
