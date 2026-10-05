"""Reproducible, zero-LLM evaluation against frozen, provisional references."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from medroute.nlp import extract, CONCEPTS, VERSION
from medroute.routing import route

ROOT=Path(__file__).resolve().parents[1]


def ratio(a,b):
    return round(a/b,4) if b else None


def scores(tp,fp,fn):
    return {"tp":tp,"fp":fp,"fn":fn,"precision":ratio(tp,tp+fp),"recall":ratio(tp,tp+fn),"f1":ratio(2*tp,2*tp+fp+fn)}


def keys(facts):
    return {(f['concept'],f['assertion'],f.get('category'),f.get('side')) for f in facts}


def evaluate(split='dev'):
    corpus=json.loads((ROOT/'data/private/corpus.json').read_text(encoding='utf-8'))
    gold=json.loads((ROOT/'data/private/gold.json').read_text(encoding='utf-8'))
    ref={g['id']:g for g in gold}
    totals=Counter(); by_concept={c:Counter() for c in CONCEPTS}; errors=[]; predictions=[]
    decision_matrix=Counter(); support=Counter(); negatives=0; false_routes=0
    for doc in corpus:
        if split!='all' and doc['split']!=split: continue
        g=ref[doc['id']]
        assert doc['text_sha256']==g['text_sha256']==hashlib.sha256(doc['text'].encode()).hexdigest()
        for fact in g['facts']:
            ev=fact['evidence']; assert doc['text'][ev['start']:ev['end']]==ev['quote']
        analysis=extract(doc['text']); decision=route(analysis)
        expected, predicted=keys(g['facts']),keys(analysis['facts'])
        totals['documents']+=1
        totals['tp']+=len(expected&predicted); totals['fp']+=len(predicted-expected); totals['fn']+=len(expected-predicted)
        totals['exact_documents']+=int(expected==predicted)
        totals['route_correct']+=int(g['expected_decision']==decision['decision'] and sorted(g['expected_profiles'])==decision['profiles'])
        decision_matrix[(g['expected_decision'],decision['decision'])]+=1
        support.update(f['concept'] for f in g['facts'])
        # No-scope-trigger != clinically normal. Do not label this metric 'normal FPR'.
        if g['expected_decision']=='no_supported_trigger':
            negatives+=1; false_routes+=int(decision['decision']=='consultation')
        for c in CONCEPTS:
            e={k for k in expected if k[0]==c}; p={k for k in predicted if k[0]==c}
            by_concept[c].update(tp=len(e&p),fp=len(p-e),fn=len(e-p))
        for fact in analysis['facts']:
            for mention in fact['mentions']:
                ev=mention['evidence']; totals['evidence_count']+=1
                totals['evidence_valid']+=int(doc['text'][ev['start']:ev['end']]==ev['quote'])
        if expected!=predicted or g['expected_decision']!=decision['decision'] or sorted(g['expected_profiles'])!=decision['profiles']:
            errors.append({"id":doc['id'],"missing":[list(k) for k in sorted(expected-predicted,key=str)],
                           "extra":[list(k) for k in sorted(predicted-expected,key=str)],
                           "expected_decision":g['expected_decision'],"actual_decision":decision['decision'],
                           "expected_profiles":g['expected_profiles'],"actual_profiles":decision['profiles']})
        predictions.append({"id":doc['id'],"split":doc['split'],"analysis":analysis,"routing":decision})
    code_hash=hashlib.sha256((ROOT/'medroute/nlp.py').read_bytes()+(ROOT/'medroute/routing.py').read_bytes()+(ROOT/'config/routing.json').read_bytes()).hexdigest()
    report={"created_at":datetime.now(timezone.utc).isoformat(),"split":split,"engine":VERSION,"code_sha256":code_hash,
            "reference_status":"AI-authored draft; NOT medically validated; fixed test, not blind external validation",
            "gold_sha256":hashlib.sha256((ROOT/'data/private/gold.json').read_bytes()).hexdigest(),
            "documents":totals['documents'],"strict_facts":scores(totals['tp'],totals['fp'],totals['fn']),
            "exact_document_accuracy":ratio(totals['exact_documents'],totals['documents']),
            "route_accuracy":ratio(totals['route_correct'],totals['documents']),
            "route_correct":totals['route_correct'],
            "evidence_validity":ratio(totals['evidence_valid'],totals['evidence_count']),
            "no_scope_trigger_documents":negatives,"false_consultations_on_no_scope_trigger":false_routes,
            "per_concept":{c:{"support":support[c],**scores(n['tp'],n['fp'],n['fn'])} for c,n in by_concept.items()},
            "decision_matrix":[{"expected":a,"actual":b,"count":n} for (a,b),n in decision_matrix.items()],
            "errors":errors,
            "limitations":["Strict fact metric uses (concept, assertion, category, side); not exhaustive NER span scoring",
                           "Evidence validity checks literal provenance only, not semantic entailment",
                           "No ground-truth validation for lesion sizes, urgency, patient outcomes or economics",
                           "No-mention does not mean normal; rare classes and historical cases need more data",
                           "Templates may overlap between splits; related-patient independence not guaranteed"]}
    out=ROOT/'reports/private'; out.mkdir(parents=True,exist_ok=True)
    (out/f'{split}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/f'{split}-predictions.json').write_text(json.dumps(predictions,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--split',choices=['dev','test','all'],default='dev');args=p.parse_args()
    print(json.dumps(evaluate(args.split),ensure_ascii=False,indent=2))
