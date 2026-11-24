# Security

tppgen is a command-line tool that reads public APIs (ClinicalTrials.gov, openFDA, Open Targets, PubMed). It runs no server, stores no user data and needs no credentials.

## Reporting a problem

Please report security issues privately through GitHub's "Report a vulnerability" button on the Security tab of this repository, not in a public issue.

## Keys

Optional API keys (`OPENFDA_API_KEY`, `NCBI_API_KEY`) are read from environment variables only. Never commit them; `.env` files are ignored.
