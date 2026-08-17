# 1. Regulatory basis

Everything in this repository traces back to four instruments. This page sets out
what each of them actually requires, because the design choices in the rest of
the framework only make sense against them.

| Instrument | Reference | Role here |
|---|---|---|
| MiFID II | Directive 2014/65/EU, **Article 25(2)** | The suitability obligation itself |
| MiFID II Delegated Regulation | Commission Delegated Regulation (EU) 2017/565, **Articles 54 and 55** | What must be collected, how, and what must be reported |
| Sustainability amendment | Commission Delegated Regulation (EU) 2021/1253 | Inserts Art. 2(7) and folds sustainability preferences into Art. 54 |
| ESMA Guidelines | **ESMA35-43-3172**, 3 April 2023, applying from 3 October 2023 | Twelve guidelines on how supervisors expect the above to be met |

---

## 1.1 The obligation: Article 25(2) MiFID II

Article 25(2) requires a firm providing investment advice or portfolio management
to obtain the necessary information regarding:

- the client's **knowledge and experience** in the investment field relevant to
  the specific type of product or service;
- the client's **financial situation, including their ability to bear losses**;
- the client's **investment objectives, including their risk tolerance**;

so as to enable the firm to recommend what is suitable and, in particular, what
is **in accordance with the client's risk tolerance and ability to bear losses**.

Two features of that wording drive the whole framework.

**First, "risk tolerance" and "ability to bear losses" are named separately and
joined by "and".** They are cumulative conditions. A client who is temperamentally
comfortable with a 40% fall but whose finances cannot survive one does not satisfy
the second limb, however emphatically they satisfy the first. This is why the
engine takes the *binding constraint* across dimensions rather than a weighted
average — see [methodology](02-methodology.md#the-binding-constraint).

**Second, knowledge and experience sit in a different clause from the financial
tests.** They exist so that the client can *understand the risks involved*. They
do not make a client richer or more resilient. This is why knowledge is applied
here as a gate on product complexity and never as an input to the risk band.

## 1.2 What must be collected: Articles 54(2)-(5) and 55(1) DR 2017/565

**Art. 54(2)** — the firm must obtain the information necessary to understand the
essential facts about the client and to have a reasonable basis for determining
that the transaction: (a) meets the client's investment objectives, including
risk tolerance *and any sustainability preferences*; (b) is such that the client
is able financially to bear any related investment risks consistent with their
objectives; (c) is such that the client has the necessary experience and
knowledge to understand the risks involved.

**Art. 54(3)** — for professional clients the firm may assume the necessary
experience and knowledge for the products, transactions and services for which
the client is so classified; for per se professional clients receiving investment
advice, it may also assume the ability to bear related investment risks.
Implemented in `professional_presumptions` in `config/scoring.yaml`.

**Art. 54(4)** — information on the **financial situation** must include, where
relevant, the source and extent of regular income, assets including liquid
assets, investments and real property, and regular financial commitments. Section
C of the questionnaire maps question-by-question onto this list.

**Art. 54(5)** — information on **investment objectives** must include, where
relevant, the length of time the client wishes to hold the investment, their
preferences regarding risk taking, their risk profile, the purposes of the
investment, and their sustainability preferences. Sections D and E map onto this.

**Art. 54(7)** — the firm must take reasonable steps to ensure the information
collected is reliable, including ensuring that questions are likely to be
understood, and that any apparent inconsistencies are addressed. Section E's
reliance on revealed behaviour and Section B's objective comprehension items are
the answer to this, together with the coherence controls.

**Art. 54(8)** — where the firm does not obtain the information required under
Art. 25(2), **it shall not recommend** investment services or financial
instruments to the client. Control `CC13` is a hard stop for exactly this.

**Art. 54(9)** — the firm must understand the nature, features, costs and risks
of the services and instruments it selects, including any sustainability factors,
and must assess, taking cost and complexity into account, whether equivalent
services or instruments can meet the client's profile. See
`equivalence_rule` in `config/portfolios.yaml`.

**Art. 54(10)** — two limbs. The firm must not recommend, or decide to trade,
where none of the services or instruments available are suitable. And, as amended
by DR (EU) 2021/1253, it must not recommend financial instruments as meeting a
client's sustainability preferences when they do not; where the client adapts
their preferences, the firm must record the decision and the reasons for it. See
`mapping.select()` and `audit.sustainability_adaptation_record()`.

**Art. 54(11)** — where advice or portfolio management involves **switching**,
the firm must collect the necessary information on the existing and proposed
investments and undertake a cost-benefit analysis such that it is reasonably able
to demonstrate that the benefits of switching are greater than the costs. See
`switching.py`.

**Art. 54(12)** — the **suitability report** to a retail client must give an
outline of the advice and explain how the recommendation is suitable, including
how it meets the client's objectives and personal circumstances with reference to
the investment term required, the client's knowledge and experience, and the
client's attitude to risk and capacity for loss. As amended, it must also explain
how the recommendation meets any sustainability preferences. `report.py` renders
one section per element.

**Art. 54(13)** — a firm carrying out a periodic suitability assessment must
review the suitability of the recommendations at least annually, with the
frequency increased according to the client's risk profile and the type of
instruments recommended.

**Art. 55(1)** — information on knowledge and experience must include, to the
extent appropriate: (a) the types of service, transaction and financial
instrument the client is familiar with; (b) the nature, volume and frequency of
the client's transactions and the period over which they were carried out;
(c) the client's level of education and profession or relevant former profession.
Questions B1-B4 map onto (a), (b) and (c) respectively.

**Art. 55(2)** — a firm must not discourage a client from providing the
information required. Nothing in the questionnaire may be framed so as to make an
answer that widens the product range easier to give than one that narrows it.

## 1.3 Sustainability preferences: Art. 2(7) DR 2017/565

Inserted by DR (EU) 2021/1253, "sustainability preferences" means the client's
choice as to whether, and if so to what extent, one or more of the following are
integrated into their investment:

- **(a)** a minimum proportion in environmentally sustainable investments within
  the meaning of the Taxonomy Regulation (EU) 2020/852;
- **(b)** a minimum proportion in sustainable investments within the meaning of
  the SFDR, Regulation (EU) 2019/2088;
- **(c)** a financial instrument that considers principal adverse impacts on
  sustainability factors, where qualitative or quantitative elements
  demonstrating that consideration are determined by the client.

Question F2 offers exactly these three, and no others.

## 1.4 The ESMA guidelines

The twelve general guidelines in ESMA35-43-3172 are mapped control-by-control in
[05-esma-control-mapping.md](05-esma-control-mapping.md). The paragraphs that did
most to shape this framework are:

- **GL2 para 30-31** — take reasonable steps to assess the client's understanding;
  mechanisms that avoid self-assessment matter.
- **GL4 para 46** — self-assessment must be counterbalanced by objective criteria,
  including practical examples, multiple-choice questions and questions about
  factual circumstances.
- **GL4 para 48** — risk tolerance should be investigated using graphs,
  percentages or figures depicting decreases in portfolio value.
- **GL4 para 51** — the obligation: *"Firms should view the information collected
  as a whole. Firms should be alert to any relevant contradictions between
  different pieces of information collected, and contact the client in order to
  resolve any material potential inconsistencies or inaccuracies."* The example
  given is a client with little knowledge and an aggressive attitude to risk —
  implemented as `CC02`.
- **GL4 para 49** — the mechanism: where firms use tools they should ensure the
  tools are fit for purpose, and risk-profiling software *"could include some
  controls of coherence of the replies provided by clients in order to highlight
  contradictions between different pieces of information collected"*.
- **GL5 para 58** — mitigate the risk that clients are induced to update their
  profile so that an unsuitable product looks suitable — implemented as `CC12`.
- **GL6 paras 69-70** — for groups, *"the firm should adopt the most prudent
  approach by taking into account, accordingly, the information on the person
  with the least knowledge and experience, the weakest financial situation or the
  most conservative investment objectives"*. Para 70 adds that taking *"an
  average profile of the level of knowledge and competence of all of them, would
  unlikely be compliant with the MiFID II overarching principle of acting in the
  clients' best interests"*.
- **GL8 para 81** — sustainability preferences are addressed **only after**
  suitability has been assessed on knowledge, financial situation and other
  objectives.
- **GL8 para 89** — diversification, concentration limits, prudence on credit
  risk, and a specific caution about small portfolios.
- **GL8 para 90** — algorithm governance: document the purpose, scope and design,
  keep a documented test strategy, manage change, detect errors, sign off.
- **GL12 paras 109-112** — record-keeping sufficient to detect failures such as
  mis-selling after the event.

## 1.5 On the horizon: the Retail Investment Strategy

On 18 December 2025 the Council and Parliament reached political agreement on the
Retail Investment Strategy package. As agreed, it leaves the suitability test
itself in place but removes the need to assess knowledge and experience where the
adviser recommends diversified, non-complex and cost-efficient instruments; it
tightens inducement rules; it introduces a value-for-money assessment against
supervisory benchmarks; and it loosens the elective professional client criteria
(15 significant transactions over three years, a portfolio above €250,000, or a
year of relevant experience — two of three). Technical finalisation was expected
in early 2026, with transposition 24 months and general application 30 months
after publication.

None of that is implemented here, because it is not yet in force. Where it lands,
it touches three files: `professional_presumptions` and the knowledge gate in
`config/scoring.yaml`, and `total_cost_bps` and `equivalence_rule` in
`config/portfolios.yaml`. See [07-limitations.md](07-limitations.md).

## Sources

- [ESMA35-43-3172, Guidelines on certain aspects of the MiFID II suitability requirements (3 April 2023)](https://www.esma.europa.eu/sites/default/files/2023-04/ESMA35-43-3172_Guidelines_on_certain_aspects_of_the_MiFID_II_suitability_requirements.pdf)
- [ESMA35-43-3172 Final Report (23 September 2022)](https://www.esma.europa.eu/sites/default/files/library/esma35-43-3172_final_report_on_mifid_ii_guidelines_on_suitability.pdf)
- [Commission Delegated Regulation (EU) 2017/565, Article 54](https://www.legislation.gov.uk/eur/2017/565/article/54/2020-01-31)
- [Commission Delegated Regulation (EU) 2017/565, Article 55](https://www.legislation.gov.uk/eur/2017/565/article/55?view=plain)
- [Commission Delegated Regulation (EU) 2021/1253](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32021R1253)
- [Council press release, Retail Investment Strategy political agreement, 18 December 2025](https://www.consilium.europa.eu/en/press/press-releases/2025/12/18/retail-investment-strategy-council-and-parliament-agree-on-package-to-empower-consumers-while-boosting-markets/)
