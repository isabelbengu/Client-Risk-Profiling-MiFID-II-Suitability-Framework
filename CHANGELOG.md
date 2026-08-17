# Changelog

All notable changes to the framework, its configuration and its calibration.

Configuration files carry their own `meta.version`. Every audit record stamps all
three, so a past decision can be reproduced against the configuration that
produced it (ESMA GL8 para 90).

## [1.0.0] - 2026-08-17

Initial release.

**Configuration**

- `questionnaire.yaml` 1.0.0 — 45 questions across six sections: client and
  circumstances (A), knowledge and experience (B), financial situation and
  capacity for loss (C), objectives and horizon (D), risk tolerance (E),
  sustainability preferences (F). Every question carries its regulatory basis.
- `scoring.yaml` 1.0.0 — five dimensions with component weights; a 1-5 band table;
  the knowledge-to-complexity gate; professional-client presumptions under
  Art. 54(3); the binding-constraint combination rule; 14 coherence controls
  `CC01`-`CC14`.
- `portfolios.yaml` 1.0.0 — 15 model portfolios (five risk bands times Core /
  PAI-aware / Sustainable), construction constraints, the GL9 equivalence rule and
  the GL10 switching rules.

**Engine**

- Binding-constraint combination across risk tolerance, capacity for loss,
  objectives and horizon.
- Knowledge applied as a complexity gate only.
- Objective comprehension ceiling and experience ceiling on the knowledge band.
- Sustainability preferences applied after the Art. 25(2) assessment, per GL8
  para 81, with the Art. 54(10) refusal to present a non-matching product as
  matching.
- Group and legal-person assessment under the most-prudent rule, with no
  averaging path.
- Art. 54(11) switching cost-benefit test.
- Art. 54(12) suitability report.
- Guideline 12 audit record, plus profile-change and sustainability-adaptation
  records.

**Documentation**

- Eight pages, three of them generated from configuration by `tools/render_docs.py`
  and checked in CI so they cannot drift.
- Guideline-by-guideline control mapping for all twelve ESMA guidelines.

**Tests**

- 76 tests: configuration integrity, scoring monotonicity and ceilings, one test
  per coherence control, mapping and product filters, report content against the
  Art. 54(12) elements, audit record completeness, the switching test, and
  documentation freshness.

**Known limitations**

- The calibration is illustrative and has not been fitted to a real client
  population or fund range. See `docs/07-limitations.md`.
- The Retail Investment Strategy, politically agreed 18 December 2025, is not
  implemented.
