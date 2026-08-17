# 7. Limitations and honest caveats

This is a reference implementation. It is a defensible starting point and a
worked demonstration of how the ESMA requirements translate into a questionnaire,
a scoring model and a mapping. It is not a compliance product, and it should not
be put in front of a client without the work below being done first.

---

## 7.1 The calibration is illustrative

The numbers in `config/scoring.yaml` and `config/portfolios.yaml` are internally
consistent and defensible in shape, but they have not been fitted to any real
client population, any real fund range, or any real return series.

Specifically, these require empirical work before use:

- **Option scores and component weights.** The weighting within risk tolerance —
  revealed behaviour 30%, quantified outcomes 40%, stated reaction 20%, attitude
  statement 10% — reflects the ordering ESMA's GL4 para 46 implies. The exact
  numbers are a judgement, not a measurement.
- **Band boundaries.** The 0-20-40-60-80 split is a plain quintile split. A real
  book will not distribute evenly across it, and a boundary that puts most of a
  book into one band is not doing any work.
- **`stress_loss_pct` per band.** 3 / 8 / 15 / 28 / 40 are plausible one-in-twenty
  twelve-month losses for the stated allocations. They should be replaced with
  figures derived from the firm's own risk model, consistent with the PRIIPs
  methodology used for the SRI, and reviewed when volatility regimes change.
  Control `CC04` compares these directly against what the client says they can
  absorb, so an over-optimistic stress loss quietly weakens the most important
  control in the framework.
- **The complexity gate mapping.** Which knowledge band admits which tier is a
  policy decision that a firm's product governance function should own.
- **Costs.** `total_cost_bps` values are placeholders. They drive the GL9
  equivalence selection, so they must be real ex-ante costs and charges under
  Art. 24(4), refreshed when they change.

## 7.2 The model portfolio range is a stub

Fifteen models — five bands times three sustainability variants — with
illustrative allocations. A real range needs: actual instruments, actual
liquidity terms, actual SRI values from the PRIIPs KIDs, a target market
determination for each model under Art. 16(3) MiFID II, and evidence that the
`construction_constraints` are actually met by the holdings. None of that is here.

The sustainability figures (`taxonomy_min`, `sfdr_sustainable_min`,
`pai_considered`) must come from the products' own disclosures, not from an
assumption. GL7 para 74 warns specifically against relying on a single data
provider without challenge.

## 7.3 What the framework does not do

- **Appropriateness** (Art. 25(3) MiFID II) for execution-only services. Different
  test, different threshold, not implemented.
- **Product governance and target market** (Art. 16(3), Art. 24(2)). The framework
  consumes a product's characteristics; it does not determine its target market.
- **Insurance-based investment products** under the IDD, which have a parallel but
  distinct suitability regime.
- **Ongoing monitoring of a portfolio's drift** away from the assessed band.
  `switching.py` evaluates a proposed switch; nothing here watches a live
  portfolio.
- **Instrument-level advice.** The mapping targets model portfolios. Advising on a
  single instrument requires the same dimensions but a different product filter.
- **Conflicts of interest, inducements, and the appropriateness of the firm's own
  products in its range** (GL8 para 80's last limb, GL9 para 93's restricted-range
  disclosure). These are firm processes.
- **Anything about tax, pensions or estate planning**, which frequently drive the
  answers to Section D but are not investment advice.

## 7.4 Jurisdiction

The framework is written against EU law as it applies at Union level. It does not
account for:

- **National implementations.** Member states' transpositions differ, and some
  national competent authorities have published further expectations on risk
  profiling. GL6 para 61 expressly directs firms to their national framework for
  legal persons and representatives.
- **The UK.** Following the Financial Services and Markets Act 2023, the
  assimilated version of DR 2017/565 was revoked with effect from 23 October 2025
  and the requirements sit in the FCA Handbook, principally COBS 9A, alongside the
  Consumer Duty. The substance is close but the citations in this repository would
  be wrong for a UK firm.
- **Third countries.** Nothing here addresses equivalence or cross-border
  provision.

## 7.5 The Retail Investment Strategy

Political agreement was reached on 18 December 2025. As agreed, the package:

- removes the requirement to assess knowledge and experience where the adviser
  recommends **diversified, non-complex and cost-efficient** instruments, while
  leaving the suitability test itself in place;
- requires inducements to deliver a **tangible benefit** and to be disclosed
  clearly and separately;
- introduces a **value-for-money** assessment: firms must identify and quantify
  all costs and charges and assess whether they are justified and proportionate
  against supervisory benchmarks, with products failing the test unable to be
  approved for sale;
- loosens the **elective professional client** criteria to two of three: 15
  significant transactions over three years, an average portfolio above €250,000,
  or a year of relevant financial-sector experience or equivalent training.

Timeline as reported: technical finalisation in early 2026, transposition 24
months after publication, general application 30 months after publication
(PRIIPs rules at 18 months).

**None of this is implemented here**, because it is not in force. When it is, the
changes land in identifiable places:

| RIS change | Where it lands |
|---|---|
| Knowledge exemption for diversified, non-complex, cost-efficient products | `complexity_gate` and `professional_presumptions` in `config/scoring.yaml`; a new product attribute in `config/portfolios.yaml` |
| Value for money | `total_cost_bps` and `equivalence_rule` in `config/portfolios.yaml`; a new benchmark comparison in `mapping.select()` |
| Elective professional criteria | `professional_presumptions`, and new questions in Section A |
| Inducement disclosure | The suitability report template in `report.py` |

Do not adopt any of it early on the strength of a press release. Wait for the
published text.

## 7.6 The deepest limitation

A risk-profiling questionnaire measures what a client says on one day, in one
frame of mind, about a future they cannot observe. The controls in this framework
catch internal contradictions; they cannot catch a client who is consistently
wrong about themselves, and no amount of scoring machinery substitutes for an
adviser who notices that something does not add up.

That is why `referred` is a status and not a warning, why the coherence controls
route to a conversation rather than to an automatic adjustment, and why GL11
para 108 requires staff to review what the tool produced. The framework is there
to make the conversation better informed and to leave a record of it. It is not
there to have the conversation.
