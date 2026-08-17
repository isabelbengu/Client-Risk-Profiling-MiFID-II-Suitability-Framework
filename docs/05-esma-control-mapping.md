# 5. ESMA guideline-by-guideline control mapping

Each of the twelve general guidelines in ESMA35-43-3172, what it requires, and
where in this repository the requirement is met. Where a guideline is addressed
by firm process rather than by code, that is stated: this framework is a
questionnaire, a scoring engine and a mapping, not a compliance function.

Legend: **C** = met in configuration · **E** = met in the engine ·
**D** = met in documentation · **P** = firm process, outside this repository ·
**T** = covered by a test.

---

## Guideline 1 — Information to clients about the purpose and scope of the suitability assessment

*Firms should inform clients clearly and simply about the suitability assessment
and its purpose, which is to enable the firm to act in the client's best interest
(para 11). Firms must avoid suggesting that the client determines suitability
(para 14). Sustainability preferences must be explained without technical
language (para 16).*

| Where | What |
|---|---|
| **E** `report.py` | Every report opens with the Art. 54(1) statement, in terms: *"It is our assessment, not yours: you are not being asked to decide whether an investment is suitable for you."* |
| **T** `test_report_states_the_purpose_of_the_assessment` | Asserts both the "best interest" statement and the "not being asked to decide" statement are present |
| **C** `questionnaire.yaml` F1 help text | Requires the sustainability concepts to be explained in non-technical terms before the question is put |
| **P** | Delivery channel, timing and evidence that the information was given (para 13) |

---

## Guideline 2 — Arrangements necessary to understand clients

*Adequate policies and procedures, including appropriate tools, to understand the
essential facts about clients (para 19). Questions must be specific and
understandable (para 21); layout must avoid question batteries (para 22). Firms
should assess understanding of risk and the risk-return relationship (para 23).
Necessary information includes marital status, family situation, age, employment
and liquidity needs (para 24). Sustainability preference collection is specified
at paras 26-29. Self-assessment mechanisms should be avoided for knowledge
(para 30); basic financial notions should be appraised through comprehensible
examples (para 31).*

| Where | What |
|---|---|
| **C** Section A | A4 age, A5 employment, A6 marital status and dependants, A7 vulnerability, C8 liquidity needs |
| **C** Section B, items B5-B10 | Six worked examples: a 20% fall in money terms, risk and expected return, diversification, bond prices and rates, leverage, and redemption terms on an illiquid fund. These are the "comprehensible examples of loss and return scenarios" of para 31 |
| **C** `B0.scoring_role: cross_check_only` | Self-assessment is collected but never scored (para 30) |
| **C** Section F, F1-F5 | Yes/no preference (para 26); the three Art. 2(7) aspects; standardised minimum proportions (para 27); PAI *categories* not individual indicators (para 27); an "I do not know which aspects" route (para 28); the portfolio share question (para 29) |
| **D** [02-methodology.md](02-methodology.md) | Documents that model portfolios come in three sustainability variants per band, so clients are not forced into a predetermined combination (para 29) |
| **T** `test_self_rating_question_is_not_scored` | Asserts B0 appears in no scoring component |

---

## Guideline 3 — Extent of information to be collected (proportionality)

*All "necessary information" must be collected before advising (para 33), with
the extent varying by instrument complexity, service, client needs and client
type (para 34) — but the suitability standard itself never varies (para 35). More
in-depth information for complex or risky instruments (para 36); for illiquid or
risky instruments, income, assets and regular commitments (para 37). Vulnerable
or inexperienced clients need more in-depth information (para 40). Professional
clients may be presumed to have the necessary experience (paras 40-41). Financial
situation includes current investments (para 43).*

| Where | What |
|---|---|
| **C/E** `professional_presumptions` | Per se professional: knowledge and ability to bear losses presumed; elective professional: knowledge only; objectives and horizon always required (para 41) |
| **E** `config.required_questions()` | The required set narrows by client category and nothing else |
| **C** C1-C11 | Income source and extent, liquid assets, real property, regular commitments (para 37 and Art. 54(4)) |
| **C/E** `CC11` vulnerability overlay | A7 flags plus age ≥ 75 cap the band at 3 absent a documented override (para 40) |
| **C/E** knowledge gate | Complexity is gated on knowledge, so more complex products are simply unavailable rather than requiring a judgement call (para 36) |
| **P** | Holdings held away from the firm (para 43). C3 collects total net financial assets; instrument-by-instrument disclosure of external holdings is a firm process |

---

## Guideline 4 — Reliability of client information

*Reasonable steps and appropriate tools to ensure information is reliable and
consistent, without unduly relying on self-assessment (para 44). Counterbalance
self-assessment with practical examples, multiple-choice questions, questions
about actual familiarity and frequency, factual financial questions and questions
about acceptable loss (para 46). Avoid broad yes/no and tick-box approaches
(para 47). Investigate risk tolerance using graphs, percentages or figures
depicting portfolio value decreases (para 48). Ensure any tools used are fit for
purpose; risk-profiling software "could include some controls of coherence of the
replies provided by clients in order to highlight contradictions between different
pieces of information collected" (para 49). Do not encourage answers that unlock
unsuitable products (para 50). **"Firms should view the information collected as a
whole. Firms should be alert to any relevant contradictions between different
pieces of information collected, and contact the client in order to resolve any
material potential inconsistencies or inaccuracies"** — and the example given is
little knowledge with an aggressive risk attitude (para 51). Address the risk of
knowledge over-estimation (para 52).*

This is the guideline the framework is built around.

| Where | What |
|---|---|
| **C** B5-B10 | Multiple-choice objective items (para 46) |
| **C** B2, B3, B4 | Actual familiarity, transaction frequency and volume (para 46) |
| **C** C1-C11 | Factual financial questions (para 46) |
| **C** C11 and E3 | Two separate acceptable-loss questions — capacity and tolerance (para 46) |
| **C** E1 | Five portfolios shown as best and worst twelve-month values on EUR 100,000 (para 48) |
| **E** `report.py` | Percentage losses restated as monetary amounts on the client's actual investment (para 48) |
| **C/E** 14 coherence controls | `CC01`-`CC14` in `config/scoring.yaml`, implemented in `consistency.py` (paras 49, 51) |
| **C/E** `CC02` | Implements para 51's own worked example: knowledge band ≤ 2 with tolerance band ≥ 4 refers the case |
| **C/E** `CC01` + comprehension ceiling | Over-estimation is detected and the band is capped at what the objective items support (para 52) |
| **E** one-way controls | No control can raise a band; overrides are downward-only by default (para 50) |
| **T** `test_consistency.py` | One test per control |

---

## Guideline 5 — Updating client information

*Procedures defining what is updated and how often, and what happens when
information is not provided (para 53). Review regularly to prevent information
becoming manifestly outdated (para 54). Frequency varies with risk profile; events
such as reaching retirement age trigger updates (para 55). Inform the client when
their profile changes, in either direction (para 59). **Mitigate the risk that
clients are induced to update their profile so an unsuitable product looks
suitable** (para 58).*

| Where | What |
|---|---|
| **C** `questionnaire.meta.review_cycle_months` | 12 months, restated in every suitability report |
| **C** A7 `near_retirement` | Captures the para 55 trigger |
| **C/E** `CC12` | Fires where the profile became riskier within five days of a recommendation (para 58) |
| **E** `audit.profile_change_record()` | Records prior band, new band, direction, reason, actor, and that the client was informed (para 59) |
| **P** | Scheduling the periodic re-collection and chasing non-responses |

---

## Guideline 6 — Client information for legal entities or groups

*An ex ante policy for legal persons, groups, and represented clients (para 60).
Where a representative is designated, knowledge is the representative's while
financial situation and objectives are the underlying client's (para 67). Where
profiles diverge, "the firm should adopt the most prudent approach by taking into
account, accordingly, the information on the person with the least knowledge and
experience, the weakest financial situation or the most conservative investment
objectives", or specify that it is unable to provide the service (paras 69-70).
**Taking "an average profile of the level of knowledge and competence of all of
them, would unlikely be compliant with the MiFID II overarching principle of
acting in the clients' best interests"** (para 70).*

| Where | What |
|---|---|
| **C** A2 | Distinguishes a natural person, a group, a represented client and a legal person |
| **E** `consistency.most_prudent()` | Takes the minimum band per dimension across individually assessed members. There is no averaging path in the code |
| **C/E** `CC14` | Fires where member bands span two or more, recording who the prudent profile came from |
| **E** dimension notes | Each combined dimension records which person it was taken from |
| **T** `test_the_group_takes_the_most_prudent_profile_not_the_average` | Asserts the group band equals the minimum and is not the rounded mean |
| **P** | The written designation of a representative and verification of their authority under national law (paras 62-64) |

---

## Guideline 7 — Arrangements necessary to understand investment products

*Robust procedures, methodologies and tools for product characteristics including
sustainability and risk factors; match complexity to client knowledge (para 72).
Sustainability factors may be used to rank and group instruments (para 73).
Product information must be reliable, accurate, consistent and up to date; do not
rely on a single data provider for complex products (para 74). Review on relevant
change (para 75).*

| Where | What |
|---|---|
| **C** `portfolios.yaml` | Every model carries risk band, SRI, adverse-scenario loss, minimum horizon, complexity tier, liquidity, cost and its full Art. 2(7) profile |
| **C** `complexity_tiers` | The product-side counterpart of the knowledge gate (para 72) |
| **C** three variants per band | Core / PAI-aware / Sustainable — the grouping contemplated by para 73 |
| **C** `portfolios.meta.review` | Quarterly Investment Committee review, ad hoc on material change (para 75) |
| **P** | Sourcing and challenging the underlying sustainability data (para 74) |

---

## Guideline 8 — Arrangements necessary to ensure suitability

*Consistently take into account all client information including the current
portfolio, and all material product characteristics including risks and costs
(para 76). Systems and controls over tools; broad classification tools are not fit
for purpose (paras 78-79). Ensure diversification, understanding of the
risk-return relationship, ability to finance and bear losses, holding periods for
illiquid products, and freedom from conflicts (para 80). **Sustainability
preferences are addressed only after the rest of the assessment** (para 81), and a
non-matching product may be recommended only after the client adapts their
preferences, with the explanation and decision documented (paras 82-83). Portfolio
size, concentration and own-group exposure (para 89). Algorithm governance
(para 90).*

| Where | What |
|---|---|
| **E** `mapping.select()` | Steps 1-3 run strictly in the para 81 order: Art. 25(2) filter, then sustainability, then cost and complexity |
| **E** unmet preferences | Returns no recommendation, states what would otherwise be suitable, and requires the adaptation to be recorded (paras 82-83, Art. 54(10)) |
| **E** `audit.sustainability_adaptation_record()` | Scoped `this_recommendation_only`, per para 83 |
| **C/E** `CC08`, `CC09` | Ability to finance the investment; concentration overlay (paras 80, 89) |
| **C** `construction_constraints` | Single-issuer limits, own-group limit, minimum holdings, illiquid caps by band, small-portfolio rule (para 89) |
| **C/E** minimum horizon per model | Illiquid and long-horizon products are excluded where the client needs the money sooner (para 80) |
| **D** [06-governance.md](06-governance.md) | Algorithm documentation, test strategy, change management, sign-off (para 90) |
| **T** `test_sustainability_is_applied_after_the_suitability_assessment` | Asserts preferences can only narrow the outcome |

---

## Guideline 9 — Costs and complexity of equivalent products

*A thorough assessment of alternatives on cost and complexity before deciding
what to recommend (para 91). Equivalence means similar target markets and
risk-return profiles (para 92). Firms using model propositions may assess cost and
complexity centrally (para 94). A more costly or complex choice must be justified,
documented and available to the control function (para 95).*

| Where | What |
|---|---|
| **C** `equivalence_rule` | Defines equivalence as same risk band and same sustainability classification |
| **E** `mapping._cheapest()` | Selects lowest ongoing cost, then lowest complexity, then deterministically by id |
| **E** `recommendation.considered` | Every model in the range is recorded with its cost, tier and reason for exclusion — this is the para 91 assessment, written down |
| **C** justification fields | Grounds and record fields for choosing a more costly or complex equivalent (para 95) |
| **T** `test_least_costly_equivalent_is_selected` | Asserts the chosen model is the cheapest among those passing the filters |

---

## Guideline 10 — Costs and benefits of switching

*Demonstrate that the expected benefits of a switch exceed its costs (para 96).
Rebalancing within an agreed strategy's thresholds is not a switch (para 97).
Account for expected net returns, changed circumstances, changed product features
and portfolio-level benefits (para 98). The suitability report must explain the
conclusion before the transaction (para 99). Control for circumvention by
splitting a switch into a sale and a later purchase (para 100).*

| Where | What |
|---|---|
| **E** `switching.assess_switch()` | Computes one-off cost, annual cost change, expected net gain and breakeven; refuses where the benefit cannot be demonstrated |
| **E** qualitative route | Permits a switch on non-financial grounds only when those grounds are stated, and marks them as requiring evidence on file (para 98) |
| **E** rebalancing exclusion | An explicit flag, documented as para 97 |
| **C** `anti_circumvention` | A sale and a related purchase within 30 days are assessed as one switch (para 100) |
| **T** four tests in `test_report_and_audit.py` | Refusal, permission, qualitative grounds, rebalancing |
| **P** | Feeding the conclusion into the suitability report before the transaction (para 99) |

---

## Guideline 11 — Qualifications of firm staff

*Staff involved in material aspects of the suitability process must have adequate
skills, knowledge and expertise (para 104), including the ability to explain
sustainability preferences non-technically (para 106). Non-client-facing staff —
questionnaire designers, algorithm designers, compliance — are in scope (para 107).
Staff using automated tools must understand the technology, its rationale, risks
and rules, and must review the output (para 108).*

| Where | What |
|---|---|
| **P** | Training, competence assessment and records are firm processes |
| **D** [06-governance.md](06-governance.md) | Sets out which roles must understand which parts of this framework, and what "reviewing the output" means here |
| **D** this repository | The engine is deliberately readable: conditions are code, not evaluated strings, and every decision is traceable in the audit record. Para 108 is not satisfiable against a black box |

---

## Guideline 12 — Record-keeping

*Orderly and transparent records of the suitability assessment, including
information collection, advice given, investments made and suitability reports
(para 109(a)); records designed to enable the detection of failures such as
mis-selling (109(b)); accessible to relevant persons and to competent authorities
(109(c)). Track why investments were made even where no transaction followed
(para 110). Record how client information was used and interpreted to define the
risk profile, the instruments matching the profile with the rationale, profile
changes, and sustainability preference adaptations with clear explanations
(para 111). Consider cyber and operational risk to digital tools (para 112).*

| Where | What |
|---|---|
| **E** `audit.build_record()` | One JSON object per assessment: answers, digest, every dimension score and component, every control that fired, the binding constraint, every product considered with its exclusion reason, the recommendation, the rendered report, and the configuration versions |
| **E** `audit.append()` | Append-only JSONL |
| **E** config versioning | The record names the questionnaire, scoring and portfolio versions, so a past decision can be reproduced against the configuration that produced it |
| **E** `profile_change_record()` | Para 111, profile changes |
| **E** `sustainability_adaptation_record()` | Para 111, adaptations with the explanation given and the client's decision |
| **E** records without a transaction | An assessment ending in `blocked`, `referred` or `no_suitable_product` still produces a full record (para 110) |
| **T** `test_audit_record_is_json_serialisable_and_complete` | Asserts the para 111 elements are present |
| **P** | Retention period, access control, resilience and cyber risk (para 112) |
