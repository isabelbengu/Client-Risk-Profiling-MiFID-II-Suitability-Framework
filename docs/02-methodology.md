# 2. Methodology

## The shape of the problem

Most risk-profiling questionnaires in circulation do the same thing: ask fifteen
questions, attach points to the answers, add the points up, and read a risk level
off a table. That method has three failure modes, and all three are things
supervisors have written about.

1. **It lets a strong answer on one dimension pay for a weak answer on another.**
   A client with a large appetite for risk and no capacity to absorb a loss scores
   in the middle and gets a middling portfolio. Article 25(2) does not permit
   that trade: it requires the recommendation to be in accordance with risk
   tolerance *and* the ability to bear losses.

2. **It treats knowledge as a risk input.** Points for "I have traded derivatives"
   push the client up the risk scale, as though understanding a product made the
   client better able to lose money in it. Article 54(2)(c) puts knowledge to a
   different purpose: understanding the risks involved.

3. **It relies on self-assessment.** "How would you rate your investment
   knowledge?" is the cheapest question in the world to answer flatteringly. ESMA
   GL4 para 46 says self-assessment must be counterbalanced by objective criteria.

This framework is built to avoid all three.

---

## The five dimensions

| Dimension | Source | How it is measured |
|---|---|---|
| **Knowledge and experience** | Art. 54(2)(c), Art. 55(1) | Objective comprehension items (40%), instruments actually held (30%), transaction activity (15%), education and profession (15%) |
| **Capacity for loss** | Art. 25(2), Art. 54(2)(b), 54(4) | Resilience (30%), income stability (20%), liquidity needs (20%), wealth base (10%), absorbable loss (20%) |
| **Investment objectives** | Art. 54(2)(a), 54(5) | Band taken from the stated purpose, reduced for a fixed commitment date or withdrawals above 5% |
| **Risk tolerance** | Art. 25(2), Art. 54(2)(a) | Revealed behaviour in a past fall (30%), quantified outcome choices (40%), stated reaction (20%), attitude statement (10%) |
| **Horizon** | Art. 54(5) | Band taken from the stated holding period, shortened where capital is needed early |

Each scored dimension produces a 0-100 score, then a band from 1 to 5.

### Why the weights sit where they do

Within **risk tolerance**, the ordering is deliberate: what a client *did* in a
real market fall outranks what they choose from a table of outcomes, which
outranks what they say they would do, which outranks which statement they agree
with. This is the counterbalancing GL4 para 46 asks for, applied inside a single
dimension. Where a client was not invested during a past fall, that component
drops out and its weight is redistributed rather than scored as zero — being new
to investing is not the same as being risk-averse.

Within **knowledge**, the objective items carry the largest single weight, and
they also impose a hard ceiling: however well a client scores on background and
activity, the band cannot exceed what the worked examples support. A second
ceiling stops a client being gated into products more than one complexity tier
above anything they have actually held.

The self-rating question (`B0`) carries **no weight at all**. It exists only so
that the gap between it and the objective items can be detected and recorded
(control `CC01`). A test in `tests/test_config.py` asserts that `B0` never
appears in any scoring component.

---

## The binding constraint

The final risk band is:

```
final_band = min(risk_tolerance, capacity_for_loss, objectives, horizon)
```

Not a weighted average. The reasoning:

- **Legally**, Article 25(2) joins risk tolerance and the ability to bear losses
  with "and". Cumulative conditions cannot be averaged.
- **By analogy from ESMA's own text**, GL6 paras 69-70 address what to do when two
  people in a group have divergent profiles: take the person with the least
  knowledge and experience, the weakest financial situation or the most
  conservative objectives, because taking *"an average profile of the level of
  knowledge and competence of all of them, would unlikely be compliant with the
  MiFID II overarching principle of acting in the clients' best interests"*. The
  same logic applies to divergent dimensions within one person.
- **Practically**, a `min` is auditable. The engine records which dimension bound,
  and the suitability report tells the client in plain words: *"Here that was your
  capacity for loss (band 3), which is why the recommendation sits at band 3."*

Knowledge is deliberately **not** in that `min`. It does something else.

## Knowledge as a gate, not a score

Knowledge band maps to a maximum product complexity tier:

| Knowledge band | Max complexity tier | What that admits |
|---|---|---|
| 1 | 0 | Deposits, money-market funds, short-dated sovereign debt |
| 2 | 1 | Plain UCITS bond and multi-asset funds, investment-grade credit |
| 3 | 2 | Listed equity, physically replicating index funds and ETFs |
| 4 | 3 | High yield, emerging markets, structured products |
| 5 | 4 | Illiquid alternatives, private markets, derivatives, leverage |

The gate filters the eligible universe. It never raises the risk band. Its effect
in practice is visible in persona 5 (`examples/clients/05-windfall-first-timer.yaml`):
a first-time investor with a large inheritance reaches band 3 on the financial
tests, but the knowledge gate holds the recommendation at band 1, and the report
says so.

For professional clients, Art. 54(3) permits the presumption of the necessary
knowledge and experience, and the gate opens fully.

## Two loss numbers, deliberately kept apart

The questionnaire asks about loss twice, in two different sections, using two
different framings:

- **C11** — *"A permanent loss of what proportion could you absorb without
  changing your standard of living or abandoning the goal behind it?"* This is
  **capacity**. It is a fact about the client's finances.
- **E3** — *"What is the largest fall, over twelve months, that you would accept
  without changing your plan?"* This is **tolerance**. It is a fact about the
  client's temperament.

Both are presented alongside the equivalent monetary amount, computed from the
amount being invested (GL4 para 48).

Every model portfolio carries a `stress_loss_pct`: the loss to expect in an
adverse twelve-month scenario. Control `CC04` requires:

```
stress_loss(recommended band) <= capacity_loss_pct (from C11)
```

If a client can absorb 15%, band 4 — which carries a 28% adverse-scenario loss —
is unavailable no matter what E3 says. If a client can absorb nothing, no model
portfolio is suitable and the framework says so rather than defaulting to the
lowest band.

## Order of operations

```
  answers
     |
     v
  [0] completeness check ................ Art. 54(8) -- hard stop if incomplete
     |
     v
  [1] score five dimensions ............. Arts. 54(2)-(5), 55(1)
     |
     v
  [2] coherence controls (pre) .......... GL4 paras 49, 51 -- may cap dimensions
     |
     v
  [3] min(tolerance, capacity, objectives, horizon)
     |
     v
  [4] coherence controls (post) ......... may cap the combined band
     |
     v
  [5] product filter .................... risk band, knowledge gate, holding period
     |
     v
  [6] sustainability filter ............. Art. 2(7) -- applied LAST, GL8 para 81
     |
     v
  [7] cost and complexity among equivalents ... Art. 54(9), GL9
     |
     v
  suitability report + audit record ..... Art. 54(12), GL12
```

Step 6 comes after step 5 because GL8 para 81 says so in terms: the range of
suitable products is identified first, and only then are the products within it
that meet the client's sustainability preferences identified. A preference can
narrow the range. It can never widen it, and it can never make an otherwise
unsuitable product suitable.

## One-way controls

Every coherence control is one-way: it can hold a profile where it is or move it
down. None can move it up. `tests/test_consistency.py::test_no_control_can_raise_the_band`
asserts this. Moving a client to a higher band requires a documented change to an
answer, second-line sign-off, and a recorded reason — see `overrides` in
`config/scoring.yaml` and control `CC12`, which flags a profile that became
riskier within five days of a recommendation.

## What the framework refuses to do

- It will not produce a recommendation where required information is missing
  (`CC13`, Art. 54(8)).
- It will not produce a recommendation where the client is borrowing to invest
  (`CC10`).
- It will not present a product as meeting sustainability preferences that it does
  not meet (Art. 54(10)). It will identify what the client would otherwise be
  offered, and require the adaptation and its reasons to be recorded.
- It will not average two people's profiles (GL6 para 70).
- It will not recommend anything to a client who cannot absorb any loss at all.

Each of those refusals is a test in `tests/`.
