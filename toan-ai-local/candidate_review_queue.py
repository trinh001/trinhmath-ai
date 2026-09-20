"""Read-only M2 review queue reusing classifier and source review."""
from __future__ import annotations
from collections import Counter
from collections.abc import Mapping
from typing import Any
from candidate_classification import INVALID, MATCHED, REVIEW_REQUIRED, normalize_text
from local_review_workflow import LOCAL_DRAFT_PROVENANCE, review_decision_text
from source_review import build_source_review_snapshot

OUTCOME_PRIORITY={REVIEW_REQUIRED:0,INVALID:1,MATCHED:2}
REASON_PRIORITY={"MATH_CONTRADICTED":0,"SOURCE_ANSWER_CONFLICT":1,"QUESTION_OPERATOR_CONFLICT":2,"FORMULA_FINGERPRINT_CONFLICT":3,"IMAGE_DEPENDENCY_UNCONFIRMED":4,"VISUAL_OR_FORMULA_REVIEW_REQUIRED":5,"MULTIPLE_PLAUSIBLE_SOURCE_MATCHES":6,"SOURCE_MATCH_LOW_CONFIDENCE":7,"SOURCE_MATCH_NOT_FOUND":8,"DUPLICATE_CANDIDATE":9}
def _text(v:object)->str:return str(v or "").strip()
def _map(v:object)->Mapping[str,Any]:return v if isinstance(v,Mapping) else {}
def _rank(r:list[str])->int:return min((REASON_PRIORITY.get(x,50) for x in r),default=50)

def build_candidate_review_queue(classification_report:object,candidates:object,image_analyses:object=None,drafts:object=None,manual_formula_overrides:object=None,*,local_review_queue:object=None)->dict[str,Any]:
    report=_map(classification_report); cmap={_text(x.get("candidate_id")):x for x in candidates if isinstance(candidates,list) and isinstance(x,Mapping) and _text(x.get("candidate_id"))}; dmap,overrides=_map(drafts),_map(manual_formula_overrides); local={_text(x.get("candidate_id")):x for x in _map(local_review_queue).get("rows",[]) if isinstance(x,Mapping)}; rows=[]
    for c in report.get("classifications",[]) if isinstance(report.get("classifications"),list) else []:
        if not isinstance(c,Mapping):continue
        cid=_text(c.get("candidate_id")); candidate=cmap.get(cid,{}); draft=_map(dmap.get(cid)); evidence=_map(c.get("evidence")); structural=_map(evidence.get("structural")); match=_map(evidence.get("source_match")); duplicate=_map(evidence.get("duplicate")); confidence=_map(evidence.get("confidence")); snapshot=build_source_review_snapshot(candidate,image_analyses,overrides.get(cid)); decision=review_decision_text(draft.get("review_decision")); status=_text(draft.get("status")); resolved=bool(decision or status in {"Đã duyệt và đưa vào ngân hàng","Đã xác nhận nguồn — chờ duyệt vào ngân hàng"}); reasons=[str(x) for x in c.get("reason_codes",[]) if str(x)]; outcome=_text(c.get("outcome")); key=(1 if resolved else 0,OUTCOME_PRIORITY.get(outcome,9),_rank(reasons),float(confidence.get("score") or 0),_text(candidate.get("source_name") or candidate.get("source_file")),_text(candidate.get("question_number")),cid)
        rows.append({"candidate_id":cid,"outcome":outcome,"reason_codes":reasons,"priority_key":key,"resolved":resolved,"teacher_review_decision":decision,"draft_status":status,"local_review_bucket":_text(_map(local.get(cid)).get("bucket")),"source_file":_text(candidate.get("source_file")),"source_name":_text(candidate.get("source_name") or candidate.get("source_file")),"question_number":_text(candidate.get("question_number")),"lesson":_text(candidate.get("lesson")),"question_text":_text(candidate.get("question_text")),"solution_text":_text(candidate.get("solution_text")),"source_match_status":_text(match.get("status")),"source_match_score":float(_map(match.get("top_match")).get("score") or 0),"confidence":float(confidence.get("score") or 0),"duplicate_status":_text(duplicate.get("status")),"duplicate_indexes":list(duplicate.get("matching_input_indexes") or []),"requires_visual_review":bool(structural.get("requires_visual_review")),"math_status":_text(structural.get("math_status")),"classification_scope":_text(c.get("classification_scope")),"source_review":snapshot,"evidence":evidence,"can_flag_local_draft":bool(draft) and draft.get("provenance") in LOCAL_DRAFT_PROVENANCE and not resolved})
    rows.sort(key=lambda x:x["priority_key"])
    for i,row in enumerate(rows,1):row["priority"]=i;row.pop("priority_key")
    return {"rows":rows,"counts":dict(Counter(x["outcome"] for x in rows)),"reason_counts":dict(Counter(r for x in rows for r in x["reason_codes"])),"unresolved_count":sum(not x["resolved"] for x in rows),"resolved_count":sum(x["resolved"] for x in rows)}

def filter_candidate_review_queue(review_queue:object,*,outcomes:object=None,reason_codes:object=None,reasons:object=None,source_text:str="",source_query:str="",lesson_text:str="",lesson:str="",unresolved_only:bool=False)->list[dict[str,Any]]:
    allowed_o=set(outcomes or []);allowed_r=set(reason_codes or reasons or []);terms=normalize_text(source_text or source_query).split();wanted=_text(lesson_text or lesson)
    return [dict(x) for x in _map(review_queue).get("rows",[]) if isinstance(x,Mapping) and (not allowed_o or x.get("outcome") in allowed_o) and (not allowed_r or allowed_r.intersection(x.get("reason_codes",[]))) and (not terms or all(t in normalize_text(f"{x.get('source_name')} {x.get('source_file')}") for t in terms)) and (not wanted or x.get("lesson")==wanted) and (not unresolved_only or not x.get("resolved"))]

def review_queue_detail(review_queue:object,candidate_id:str)->dict[str,Any]|None:
    return next((dict(x) for x in _map(review_queue).get("rows",[]) if isinstance(x,Mapping) and _text(x.get("candidate_id"))==_text(candidate_id)),None)
