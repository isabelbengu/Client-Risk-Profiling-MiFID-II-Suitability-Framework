# Client Risk Profiling — MiFID II Suitability Framework

A working questionnaire, scoring model and suitability mapping that takes a
client from a set of answers to a model portfolio, built to
**Article 25(2) MiFID II**, **Articles 54 and 55 of Delegated Regulation (EU)
2017/565**, and the **ESMA Guidelines on certain aspects of the MiFID II
suitability requirements (ESMA35-43-3172, applying from 3 October 2023)**.

Risk tolerance, capacity for loss, objectives and horizon are assessed
separately and combined by taking the **binding constraint**, not a weighted
average. Knowledge and experience gate product *complexity* and never raise the
risk band. Sustainability preferences are applied last, after the Art. 25(2)
assessment, exactly as ESMA Guideline 8 para 81 requires.

---

## The one idea

Most risk questionnaires add points up and read a risk level off a table. That
lets a strong answer on one dimension pay for a weak answer on another — which is
precisely what Article 25(2) forbids, since it requires a recommendation to be in
accordance with the client's risk tolerance **and** their ability to bear losses.
Two cumulative conditions cannot be averaged.

So the engine does this instead:

```
final_band = min(risk_tolerance, capacity_for_loss, objectives, horizon)
```

and then gates the eligible products on knowledge, filters on sustainability
preferences, and picks the least costly equivalent. The suitability report tells
the client which dimension bound and why.

ESMA reaches the same conclusion from the other direction in Guideline 6 para 70:
taking "an average profile of the level of knowledge and competence of all of
them" across a group of clients "would unlikely be compliant with the MiFID II
overarching principle of acting in the clients' best interests". The same logic
applies to divergent dimensions within one client.

## What is here

```
config/          questionnaire.yaml    45 questions across 6 sections, every one traced to an article
                 scoring.yaml          weights, bands, the complexity gate, 14 coherence controls
                 portfolios.yaml       15 model portfolios, construction constraints, equivalence and switching rules

src/suitability/ scoring.py            five dimensions, 0-100, with the components kept for the record
                 consistency.py        the coherence controls of GL4 paras 49 and 51, and the binding constraint
                 mapping.py            Art. 25(2) filter -> sustainability filter -> cost and complexity
                 switching.py          the Art. 54(11) cost-benefit test
                 report.py             the Art. 54(12) suitability report
                 audit.py              the Guideline 12 record
                 engine.py             the pipeline
                 cli.py                command line

docs/            01 regulatory basis   what each article and guideline actually requires
                 02 methodology        why the design is what it is
                 03 questionnaire      the full questionnaire (generated from config)
                 04 mapping            bands, tiers, portfolios, constraints (generated from config)
                 05 control mapping    guideline by guideline, where each requirement is met
                 06 governance         GL8 para 90 algorithm governance, records, change control
                 07 limitations        what is illustrative, what is missing, what the RIS will change
                 08 control index      all 14 coherence controls (generated from config)

examples/        six client personas, their reports and the audit log
tests/           76 tests, one per control and one per design rule
```

## Quickstart

```bash
pip install -e ".[dev]"
python3 -m pytest

python3 -m suitability assess examples/clients/05-windfall-first-timer.yaml
python3 -m suitability assess examples/clients/04-sustainability-preferences.yaml \
    --report report.md --audit audit/log.jsonl

python3 -m suitability questionnaire --section B
python3 -m suitability portfolios
python3 -m suitability controls
```

Or as a library:

```python
from suitability import ClientCase, assess, load_config, render_report

cfg = load_config()
outcome = assess(ClientCase(client_ref="C-1", answers=answers, assessed_at="2026-03-01T09:00:00Z"), cfg)

print(outcome.status)               # recommended | referred | blocked | no_suitable_product
print(outcome.final_band)           # 0-5
print(outcome.binding_constraint)   # which dimension decided it
print(render_report(outcome, answers, cfg))
```

## A worked example

`examples/clients/05-windfall-first-timer.yaml` — someone who has just inherited
€190,000, has never invested, rates their own knowledge as "advanced", answers two
of six worked examples correctly, and wants maximum long-term growth.

```
status            : REFERRED
final risk band   : 1 (Capital preservation)
binding constraint: capacity
knowledge gate    : complexity tier 0

dimensions:
  knowledge  score  13.3   band 1
  capacity   score  54.0   band 3
  objective  score     -   band 4
  tolerance  score  92.1   band 5
  horizon    score     -   band 5

coherence controls triggered:
  CC01 cap    Knowledge over-estimation - self-rating 4/5 against 2/6 comprehension items correct
  CC09 cap    Concentration in a single mandate - mandate is 90% of net financial assets
  CC02 refer  Low knowledge with high risk appetite - knowledge band 1 against tolerance band 5
  CC03 refer  Tolerance materially exceeds capacity - tolerance band 5 exceeds capacity band 3 by 2
  CC04 cap    Stated loss tolerance exceeds absorbable loss - 35% stated against 30% absorbable
  CC11 cap    Vulnerability overlay - first-time investor
  CC07 refer  Return expectation not achievable - client expects a band 5 return from a band 3 portfolio

recommendation    : MP1-CORE - Capital Preservation - Core
  * Profile band 3 was reduced to 1 in product terms: knowledge gate tier 0 rules out the higher band.
```

A points-and-table questionnaire would have averaged a 92 tolerance score against
a 54 capacity score and a 13 knowledge score and put this client somewhere in the
middle. Here the tolerance score never touches the outcome, the status is
`referred` because ESMA GL4 para 51 names this exact combination as one to resolve
with the client, and the [suitability report](examples/outputs/05-windfall-first-timer-report.md)
explains it in the client's own terms.

## How the regulation maps onto the code

| Requirement | Source | Where |
|---|---|---|
| Purpose of the assessment stated to the client | Art. 54(1); GL1 | `report.py`, first paragraph of every report |
| Knowledge and experience: familiarity, volume and frequency, education | Art. 55(1)(a)-(c) | Questions B1-B4 |
| Objective comprehension, not self-assessment | GL2 paras 30-31; GL4 paras 46, 52 | Questions B5-B10; `comprehension_ceiling`; control `CC01` |
| Financial situation: income, assets, real property, commitments | Art. 54(4) | Questions C1-C11 |
| Ability to bear losses | Art. 25(2); Art. 54(2)(b) | The `capacity` dimension; control `CC04` |
| Objectives: holding period, purpose, risk preferences | Art. 54(5) | Questions D1-D6, E1-E5 |
| Risk tolerance investigated with figures showing value decreases | GL4 para 48 | Question E1; monetary restatement in `report.py` |
| Contradictions detected and resolved with the client | GL4 paras 49, 51 | 14 controls in `config/scoring.yaml`, implemented in `consistency.py` |
| No recommendation without the necessary information | Art. 54(8) | Control `CC13` |
| Groups: most prudent profile, never an average | GL6 paras 69-70 | `consistency.most_prudent()`; control `CC14` |
| Product understanding including sustainability factors | Art. 54(9); GL7 | `config/portfolios.yaml` |
| Sustainability preferences applied after suitability | GL8 para 81 | Step 6 of `mapping.select()` |
| No product presented as meeting preferences it does not meet | Art. 54(10); GL8 paras 82-83 | `mapping.select()`; `audit.sustainability_adaptation_record()` |
| Diversification and concentration | GL8 para 89 | `construction_constraints`; control `CC09` |
| Cost and complexity of equivalents | Art. 54(9); GL9 | `equivalence_rule`; `mapping._cheapest()` |
| Cost-benefit of switching | Art. 54(11); GL10 | `switching.py` |
| Suitability report | Art. 54(12) | `report.py` |
| Record-keeping | GL12 paras 109-112 | `audit.py` |

Guideline by guideline, with the paragraph numbers:
[docs/05-esma-control-mapping.md](docs/05-esma-control-mapping.md).
The 14 coherence controls, their conditions, effects and client-facing wording:
[docs/08-control-index.md](docs/08-control-index.md).

## Design rules the tests enforce

- The self-rating question `B0` is never scored — asserted in `test_config.py`.
- Knowledge never appears in the risk-band combination — asserted in `test_config.py`.
- No coherence control can raise a band — asserted in `test_consistency.py`.
- A group's band is the minimum across members, and never the mean — asserted in
  `test_consistency.py`.
- Sustainability preferences can only narrow the outcome — asserted in
  `test_mapping.py`.
- The recommended portfolio's adverse-scenario loss never exceeds what the client
  said they could absorb — asserted in `test_consistency.py`.
- The generated documentation matches the configuration — asserted in
  `test_docs.py`.

## Before using this for anything real

Read [docs/07-limitations.md](docs/07-limitations.md). In short: the calibration
is illustrative and must be fitted to a real population and a real fund range; the
model portfolio universe is a stub; appropriateness, product governance and IBIPs
are out of scope; national implementations differ, and the UK now sits under COBS
9A rather than the assimilated Delegated Regulation. The Retail Investment
Strategy, politically agreed on 18 December 2025, will change the knowledge
requirement for diversified non-complex products, add a value-for-money test and
loosen the elective professional criteria — none of which is implemented here,
because none of it is yet in force.

## Sources

- [ESMA35-43-3172, Guidelines on certain aspects of the MiFID II suitability requirements (3 April 2023)](https://www.esma.europa.eu/sites/default/files/2023-04/ESMA35-43-3172_Guidelines_on_certain_aspects_of_the_MiFID_II_suitability_requirements.pdf)
- [ESMA35-43-3172 Final Report (23 September 2022)](https://www.esma.europa.eu/sites/default/files/library/esma35-43-3172_final_report_on_mifid_ii_guidelines_on_suitability.pdf)
- [Delegated Regulation (EU) 2017/565, Article 54](https://www.legislation.gov.uk/eur/2017/565/article/54/2020-01-31) · [Article 55](https://www.legislation.gov.uk/eur/2017/565/article/55?view=plain)
- [Delegated Regulation (EU) 2021/1253 (sustainability preferences)](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1253)
- [Council press release, Retail Investment Strategy political agreement (18 December 2025)](https://www.consilium.europa.eu/en/press/press-releases/2025/12/18/retail-investment-strategy-council-and-parliament-agree-on-package-to-empower-consumers-while-boosting-markets/)
- [FCA Handbook COBS 9A.2](https://www.handbook.fca.org.uk/handbook/COBS/9A/2.html) — for the UK comparison noted in the limitations

## Licence

MIT. See [LICENSE](LICENSE).

Nothing in this repository is legal, regulatory or investment advice.
