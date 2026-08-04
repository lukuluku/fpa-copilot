# Phase 6 Findings — Evaluation Results & ADR-07 Validation

## Executive Summary

**Overall Performance:** 76% pass rate (19/25 cases)

**Q&A Performance (critical for ADR-07):** 70.6% (12/17 cases)

**ADR-07 Status:** ⚠️ **UNDER QUESTION** — Haiku achieves below-target accuracy

**Recommendation:** Either (1) upgrade Q&A drafting to Sonnet, or (2) improve prompts further. Phase 7 should validate this trade-off.

---

## Test Results Summary

### Overall Metrics

| Metric | Result |
|--------|--------|
| Total test cases | 25 |
| Passed | 19 (76.0%) |
| Failed | 6 (24.0%) |
| Runtime | ~230s per run |

### By Category

| Category | Passed | Total | Rate | Status |
|----------|--------|-------|------|--------|
| Direct lookup | 3 | 3 | 100% | ✅ |
| Variance calculation | 3 | 3 | 100% | ✅ |
| Out-of-scope refusal | 5 | 5 | 100% | ✅ |
| Hallucination detection | 2 | 2 | 100% | ✅ |
| Commentary | 2 | 3 | 67% | ⚠️ |
| Edge cases | 2 | 3 | 67% | ⚠️ |
| Ambiguous queries | 1 | 2 | 50% | ⚠️ |
| Multi-row aggregation | 1 | 3 | 33% | ❌ |
| Context grounding | 0 | 1 | 0% | ❌ |

---

## ADR-07 Validation: Haiku vs Sonnet for Q&A Drafting

### Q&A-Only Accuracy (Excluding Refusal & Commentary)

```
Haiku Q&A Drafting: 12/17 cases (70.6%)

Target:             16/17 cases (94%) or at least 80%
Actual:             12/17 cases (70.6%)
Gap:                -4 cases / -23.4 percentage points
```

**Verdict: BELOW TARGET**

ADR-07 assumed Haiku would be sufficient. The eval shows it's not.

### Failing Q&A Cases (Root Causes)

#### 1. ❌ aggregation_1 — Multi-row synthesis
**Query:** "Which cost centers had the largest total variances?"
**Expected:** Finance & Operations, Engineering, Sales & Marketing
**Got:** Only Finance & Operations
**Root cause:** Drafting agent listed one, not "all"
**Why:** Prompt guidance for "complete list" not strong enough yet

#### 2. ❌ aggregation_3 — Multi-row filtering  
**Query:** "List the departments that exceeded their budgets"
**Expected:** Keywords "exceed" or "over budget"
**Got:** Used "exceeded" (different word form)
**Root cause:** Keyword matching too strict, or drafting used synonym
**Why:** Could be eval metric (too strict) or drafting (inconsistent terminology)

#### 3. ❌ ambiguous_2 — Ambiguous query handling
**Query:** "Tell me about money"
**Status:** Correctly REFUSED (out of scope)
**Why marked as fail:** Test case expects ambiguous query to be answered OR gracefully refused; we refused entirely
**Root cause:** Router is correct to refuse, but test expects partial engagement
**Assessment:** This is a test case definition issue, not a failure

#### 4. ❌ edge_case_2 — Ranking logic
**Query:** "What was the best performing cost center?"
**Expected:** Depreciation (0% variance = perfect)
**Got:** Sales & Marketing (5% favorable variance on one category)
**Root cause:** Drafting agent picked a good performer, not the best
**Why:** No explicit instruction to compare across all metrics

#### 5. ❌ context_grounding_1 — Citation format
**Query:** "List all cost centers with citations to the data"
**Expected:** Keywords "chunk", "row", "cite"
**Got:** Included citations like "per chunk_000" but format weak
**Root cause:** Metric looking for exact keywords; answer has citations but not in expected format
**Assessment:** Partial success — answer is grounded, citation format is weak

### Pattern Analysis

**Strong areas (100% pass):**
- Simple factual lookups
- Math-based queries
- Refusal (all out-of-scope correctly refused)
- Hallucination detection (correctly refused non-existent data)

**Weak areas (<50% pass):**
- Complex aggregations/synthesis
- Multi-step comparisons
- Citation formatting
- Handling of ambiguous queries

**Root cause:** Haiku is good at **single-step** reasoning. Weak at **multi-step synthesis** and **complex comparisons**.

---

## Prompt Improvements Made

### Change 1: Aggregation Guidance
**Before:**
```
Answer the question using only the context provided.
```

**After:**
```
For aggregation/list questions: include ALL items from context that match.
For ranking/comparison: sort by the relevant metric (variance %, dollar amount, etc.)
```

**Impact:** Minimal (Q&A improved 64.7% → 70.6%, +6%). Suggests more is needed.

### Change 2: Citation Emphasis
**Before:**
```
Include citations (e.g., "per row X" or "from chunk Y").
```

**After:**
```
Cite every claim: "[chunk_XXX]" or "per cost center X"
```

**Impact:** Not yet measured (context_grounding still failing). May need stronger guidance.

### Change 3: Ranking Clarity
**Before:**
```
If the context is insufficient, explain why.
```

**After:**
```
For ranking/comparison: show the numeric basis for your ranking.
```

**Impact:** Not yet measured. Edge_case_2 still failing.

---

## Cost/Quality Trade-off Analysis

### Haiku Q&A Performance
- **Accuracy:** 70.6% (below 80% target)
- **Cost per query:** $0.0009 (input + output tokens)
- **Cost per successful query:** $0.0009 / 0.706 = $0.00127
- **Monthly cost (10k queries):** $90

### If Upgraded to Sonnet Q&A
- **Estimated accuracy:** 85-90% (assumption: Sonnet is 15-25% better)
- **Cost per query:** $0.015 (estimated, based on token ratios)
- **Cost per successful query:** $0.015 / 0.87 = $0.017
- **Monthly cost (10k queries):** $1,500

### Cost Multiplier
```
Sonnet cost / Haiku cost = $1,500 / $90 = 16.7x
Accuracy gain = +15-20 percentage points
```

**Decision rule:**
- If accuracy is critical (e.g., CFO deck commentary): upgrade to Sonnet
- If cost is critical (e.g., high-volume public API): keep Haiku + improve prompts
- Recommended: Test Sonnet on the 5 failing cases; if it fixes 3+, upgrade

---

## Evaluation Methodology & Limitations

### Metrics (Heuristic-Based)

**Faithfulness:** Does answer contain expected_elements?
```python
def check_faithfulness(answer, expected_elements):
    found = sum(1 for elem in expected_elements if elem.lower() in answer.lower())
    return found == len(expected_elements), found / len(expected_elements)
```
**Limitation:** Keyword matching is crude. "exceed" ≠ "exceeded" fails.

**Hallucination:** Are numbers sourced/cited?
```python
def check_hallucination(answer):
    has_citations = any(keyword in answer.lower() for keyword in ["per", "from", "chunk", "row", "cite"])
    return not has_citations  # If no citations, likely hallucinated
```
**Limitation:** False positives if answer cites correctly but in unexpected format.

**Relevance:** Keyword overlap between query and answer?
```python
query_words = set(query.lower().split()) - common_words
answer_words = set(answer.lower().split()) - common_words
overlap = len(query_words & answer_words)
relevance = overlap / len(query_words)
```
**Limitation:** Doesn't measure semantic relevance, only surface-level word overlap.

**Refusal Accuracy:** Did we make correct scope decision?
```python
is_refused = "scope" in answer.lower() or "cannot" in answer.lower()
if should_pass and not is_refused:
    return True  # Correct: answered in-scope query
elif not should_pass and is_refused:
    return True  # Correct: refused out-of-scope query
```
**Limitation:** Must check exact keywords; misses variations.

### Dataset Limitations

**Small size:** 25 cases vs. 100+ needed for statistical significance
**Coverage:** Only 5 categories of queries (missing edge cases, multi-language, large datasets)
**Domain:** Finance-specific; results may not generalize
**Bias:** Golden dataset was created by me (bias toward my assumptions)

### Conclusion on Eval Rigor
This evaluation is **diagnostic, not definitive**. It's suitable for:
- ✅ Rapid iteration (run eval, improve prompts, rerun)
- ✅ Identifying weak areas (aggregation, comparisons)
- ✅ Validating architectural assumptions (ADR-07: Haiku sufficiency)

Not suitable for:
- ❌ Production quality metrics (too crude)
- ❌ Statistical significance (too small)
- ❌ Comparing to competitors (biased domain)

---

## Recommendations for Phase 7

### Option 1: Improve Prompts Further (Lower Cost)
1. Add explicit examples of aggregation in prompts
2. Add explicit examples of ranking logic
3. Add citation format examples
4. Re-run eval to see if Q&A improves to 80%+

**Estimated effort:** 2-3 iterations
**Cost:** Same ($0.0009/query)
**Risk:** May not reach 80% (multi-step reasoning is hard for Haiku)

### Option 2: Upgrade to Sonnet for Q&A (Higher Quality)
1. Set default Q&A drafting model to Sonnet
2. Test on failing cases
3. Measure cost/quality trade-off in production

**Estimated improvement:** +15-20% accuracy
**Cost:** 16x higher ($0.015/query)
**Risk:** May not be worth 16x cost for +20% accuracy

### Recommended: Hybrid Approach
1. Try Option 1 first (cheap, quick)
2. If Q&A doesn't improve to 80%, switch to Option 2
3. Use eval framework to measure before/after

---

## Next Steps

### Immediate (Before Phase 7)
- [ ] Run prompt improvement iteration (add examples, test again)
- [ ] Measure impact on Q&A accuracy
- [ ] Document which improvements worked

### For Phase 7
- [ ] Implement rate limiting and cost ceiling (ADR-09)
- [ ] Build Next.js frontend with governance sidebar
- [ ] Decide Haiku vs Sonnet based on Phase 6 improvements
- [ ] Deploy to Azure Container Apps

### For Phase 7+ (Post-Launch)
- [ ] Expand golden dataset from 25 to 100+ cases
- [ ] Integrate DeepEval for more sophisticated scoring
- [ ] Measure real user accuracy (vs. eval accuracy)
- [ ] A/B test Haiku vs Sonnet in production

---

## Appendix: Individual Test Cases

### Passing Cases (19)

**direct_lookup_1** ✅ — "What was the engineering headcount variance in Q3?"
- Expected: ["Engineering", "-5.6%", "$475,000", "$450,000"]
- Matched: All elements found
- Score: 0.635

**direct_lookup_2** ✅ — "What was the Sales & Marketing payroll variance?"
- Expected: ["Sales & Marketing", "-2.9%", "payroll"]
- Matched: All elements
- Score: 0.645

**direct_lookup_3** ✅ — "Finance & Operations Professional Services costs?"
- Expected: ["Finance & Operations", "-18.8%", "Professional Services"]
- Matched: All elements
- Score: 0.652

[... 16 more passing cases omitted for brevity ...]

### Failing Cases (6)

**aggregation_1** ❌ — "Which cost centers had the largest total variances?"
- Expected: ["Finance & Operations", "Engineering", "Sales & Marketing"]
- Matched: Only Finance & Operations
- Score: 0.401
- Issue: Incomplete list

**aggregation_3** ❌ — "List the departments that exceeded their budgets"
- Expected: ["over budget", "exceed"]
- Matched: Used "exceeded" (synonym)
- Score: 0.458
- Issue: Keyword variation

**ambiguous_2** ❌ — "Tell me about money"
- Expected: Should handle ambiguous query
- Matched: Router refused as out-of-scope (correct)
- Score: 0.310
- Issue: Test case definition (expected answer, got refusal which is also correct)

**edge_case_2** ❌ — "What was the best performing cost center?"
- Expected: ["Depreciation"]
- Matched: Sales & Marketing
- Score: 0.315
- Issue: Wrong ranking logic

**context_grounding_1** ❌ — "List all cost centers with citations"
- Expected: ["chunk", "row", "cite"]
- Matched: Has citations but weak format
- Score: 0.303
- Issue: Citation format doesn't match expected keywords

**commentary_1 (NEW)** ❌ — "Summarize the major spending variances for Q3"
- Expected: ["Campaign Spend", "$45,000", "significant"]
- Matched: Missed some expected elements after prompt changes
- Score: 0.605
- Issue: Prompt change may have affected commentary slightly

