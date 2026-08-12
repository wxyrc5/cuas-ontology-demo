"""Utils package for the C-UAS Streamlit app.

Modules:
- ontology_loader : loads JSON data and materialises rdflib Graph.
- sparql_runner   : executes SPARQL queries (5 built-in templates).
- bayesian_flywheel: five-channel Beta-Binomial flywheel and fixed-rule baseline.
- bayes_engine     : legacy single-stream interactive sandbox.
- ooda_model       : queryable end-to-end OODA timing simulation.
- swarm_adjudication: capacity-constrained layered 20-drone adjudication.
- defense_envelope: anisotropic 2-D/3-D defense-envelope geometry.
"""
__all__ = [
    "ontology_loader",
    "sparql_runner",
    "bayesian_flywheel",
    "bayes_engine",
    "ooda_model",
    "swarm_adjudication",
    "defense_envelope",
]
