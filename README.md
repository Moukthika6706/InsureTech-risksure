# RiskSure

RiskSure is a small, working version of the software a property & casualty insurer uses to sell policies, built for three India-based products: Personal Auto, Homeowners and Small Business. A customer requests a quote. The system calculates an explainable premium from config-driven rating tables, scores the risk (a trained claim-likelihood model for auto, a transparent points scorecard for home and business), and applies underwriting rules to auto-approve, adjust, refer or decline. An accepted quote can then be bound and issued as a policy, with a full audit trail. A plain-English rule assistant lets underwriters draft new rules with AI and preview their impact before publishing. All data and rates are synthetic and for illustration only. This is not real actuarial pricing.

*Work in progress. See [SPEC.md](SPEC.md) for the design.*
