# 6. Governance, records and change control

ESMA GL8 para 90 sets out what a firm must be able to show about an algorithm
that determines suitability: documented purpose, scope, design and decision
trees; a documented test strategy; change management with security and
record-keeping; regular review and update; error detection and handling;
sufficient resource to monitor performance; and an internal sign-off process
before deployment. GL11 para 108 adds that staff using the tool must understand
its rationale, risks and rules, and must review its output.

This page is how those requirements attach to this repository.

---

## 6.1 Purpose, scope and design

| | |
|---|---|
| **Purpose** | To assess the suitability of a model portfolio for a client under Art. 25(2) MiFID II, and to produce the Art. 54(12) suitability report and the GL12 record |
| **Scope** | Investment advice, investment advice on a portfolio basis, and discretionary portfolio management, for retail and professional clients, against the model portfolio range in `config/portfolios.yaml` |
| **Out of scope** | Execution-only appropriateness under Art. 25(3); insurance-based investment products under the IDD; product governance and target market determination under Art. 16(3); pension and tax advice; anti-money-laundering |
| **Decision tree** | [02-methodology.md § order of operations](02-methodology.md#order-of-operations) |
| **Inputs** | `config/questionnaire.yaml`, `config/scoring.yaml`, `config/portfolios.yaml` |
| **Outputs** | An `Outcome` object, a markdown suitability report, an append-only JSONL audit record |

The design principle behind the file layout is that **no outcome-determining
value is hard-coded**. Questions, option scores, component weights, band
boundaries, the complexity gate, the coherence controls' severity, the model
portfolios and the equivalence rule all live in versioned YAML. The Python
implements the *logic*; the YAML holds the *calibration*. A change to calibration
is a configuration change with a version bump; a change to logic is a code change
with a test.

The one deliberate exception: the **conditions** of the coherence controls are in
code, not evaluated from strings in the configuration. A control that can be
disabled by editing an expression in a text file is not a control.
`tests/test_consistency.py::test_every_configured_control_is_implemented` keeps
the two lists in step.

## 6.2 Test strategy

| Layer | File | What it protects |
|---|---|---|
| Configuration integrity | `tests/test_config.py` | Weights sum to 1; bands are contiguous and cover 0-100; stress losses are monotonic in band; every band has portfolios and both a Core and a Sustainable variant; comprehension items have exactly one correct answer; the self-rating question is never scored; knowledge is never a risk-band input |
| Scoring | `tests/test_scoring.py` | Monotonicity in the loss and drawdown answers; the comprehension ceiling; the experience ceiling; weight redistribution when a component drops out; objective-band reductions |
| Controls | `tests/test_consistency.py` | One test per control, plus: the binding constraint is the minimum; no control can raise a band; groups take the prudent profile and not the average |
| Mapping | `tests/test_mapping.py` | The recommendation never exceeds the client band or the horizon; the complexity gate bites; sustainability narrows and never widens; unmeetable preferences block; the cheapest equivalent wins |
| Report and record | `tests/test_report_and_audit.py` | Every Art. 54(12) element is present; losses appear in money; a referred case does not present advice; the audit record carries the GL12 para 111 elements; the switching test |
| Documentation | `tests/test_docs.py` | The generated documentation matches the configuration; every control id is documented; internal links resolve |

Run: `python3 -m pytest`.

The six personas in `examples/clients/` are regression cases as well as
illustrations: they are run end-to-end and their reports are re-rendered on every
test run. Their outputs are committed in `examples/outputs/`, so a change in
behaviour shows up as a diff in a pull request rather than as a surprise in
production.

## 6.3 Change management

**Configuration change** (a score, a weight, a band boundary, a portfolio, a
control severity):

1. Bump the `meta.version` of the file changed. Semantic: patch for a
   correction that cannot change an outcome, minor for a calibration change,
   major for a change to the question set or the band structure.
2. Run the tests. Run the six personas and diff `examples/outputs/`.
3. Re-run `python3 tools/render_docs.py`.
4. Record in `CHANGELOG.md`: what changed, why, who approved it, and which
   personas' outcomes moved.
5. Second-line sign-off before deployment (GL8 para 90).

**Code change**: the same, plus a test that fails before the change and passes
after.

Because every audit record carries the three configuration versions, a decision
made under version 1.0.0 can be re-run against version 1.0.0 after the live
configuration has moved on. That is the point of stamping them.

**Never** change a client's answers to change an outcome. Where new information
genuinely changes an answer, that is a profile change: record it with
`audit.profile_change_record()`, tell the client (GL5 para 59), and expect
control `CC12` to fire if a recommendation follows within five days.

## 6.4 Records

`audit.build_record()` produces one JSON object per assessment containing:

- the full answer set and its digest;
- every dimension's score, its components and their weights, and every cap
  applied with the reason — this is GL12 para 111's *"how that information was
  used and interpreted to define the client's risk profile"*;
- every coherence control that fired, with its severity, regulatory basis and the
  specific detail that triggered it;
- the binding constraint and the final band;
- **every model portfolio considered**, with its cost, complexity tier and the
  reason it was excluded — the GL9 para 91 assessment of alternatives, in
  evidence;
- the recommendation and the sustainability status;
- the rendered suitability report;
- the three configuration versions.

Assessments that end in `blocked`, `referred` or `no_suitable_product` produce a
full record too. GL12 para 110 requires records that show why an investment was
*not* made as much as why it was.

Two further record types exist for events that happen outside an assessment:
`profile_change_record()` and `sustainability_adaptation_record()`.

**Not covered here**, and left to the firm: retention period, access control,
immutability guarantees, and the operational and cyber risk arrangements GL12
para 112 requires around digital tools.

## 6.5 Roles

| Role | Must understand | GL |
|---|---|---|
| Adviser | The five dimensions; why the binding constraint governs; what each control means for the client conversation; how to record an override or an adaptation | GL11 paras 105-106, 108 |
| Questionnaire owner | Why each question exists and which article it answers; why B0 is never scored | GL11 para 107 |
| Investment Committee | The portfolio parameters, the stress-loss calibration, the equivalence rule | GL7, GL9 |
| Compliance / second line | The control set, the override log, the CC12 flags, the audit record | GL11 para 107, GL12 |
| Engineering | The pipeline, the test strategy, the change process | GL8 para 90 |

GL11 para 108 requires staff to review the digital advice generated. In this
framework that means: read section 4 of the suitability report before the client
meeting, and treat a `referred` status as an instruction to have a conversation,
not an obstacle to route around.

## 6.6 Periodic review

| What | Frequency | Owner |
|---|---|---|
| Client profile refresh | 12 months, or on a material change | Adviser |
| Model portfolio parameters (SRI, stress loss, costs, sustainability profile) | Quarterly, ad hoc on material change | Investment Committee |
| Questionnaire wording and comprehension items | Annually | Questionnaire owner |
| Control calibration against outcomes actually observed | Annually | Compliance |
| Whole framework against regulatory change | On change; next scheduled trigger is the Retail Investment Strategy | Compliance |

The control calibration review is the one most often skipped and the one that
matters most. A control that never fires across a whole book is not evidence of a
clean book; it is evidence of a threshold set where nothing can reach it.
