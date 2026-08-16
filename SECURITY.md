<div align="center">

<img src="assets/flag-of-yemen.png" alt="Flag of Yemen" width="64" height="43">

# Security Policy

[Back to the directory](README.md) · [Contributing](CONTRIBUTING.md) · [Yemen Tech Collective](https://yementc.org)

</div>

---

## What This Repository Is

This repository is a **directory**: a YAML data file, a Python script that renders it into `README.md`, and the GitHub
Actions workflows that validate and publish the result. It ships no runtime code and no dependencies for users to
install.

## Reporting a Problem With This Repository

Report anything that affects the integrity of the directory or its automation privately, through
[GitHub Security Advisories](https://github.com/yementechcollective/aweasome-yemeni-open-source/security/advisories/new),
or by emailing **[info@yementc.org](mailto:info@yementc.org)**. Please do not open a public issue first.

Examples worth reporting privately:

- A workflow that could be made to run untrusted code or leak a token.
- An entry linking to a repository that distributes malware or credential-harvesting code.
- A listing that impersonates another project, organization, or maintainer.

We aim to acknowledge a report within **five working days** and to agree a resolution and disclosure timeline with you.

## Reporting a Problem With a Listed Project

Each listed project is governed by its **own maintainers and its own security policy**. Report vulnerabilities in a
listed project to that project directly — not here. If a listed repository is malicious, deceptive, or has been taken
over, tell us privately using the channels above and we will review the entry for removal.

## Scope

| In scope | Out of scope |
|---|---|
| The workflows in `.github/workflows/` | Vulnerabilities inside listed projects |
| `scripts/catalog.py` and the data files | Findings against `github.com` itself |
| Directory content that is malicious or deceptive | Broken links and stale metadata — open a normal issue |

## Supported Versions

The `main` branch is the only supported version; fixes are applied there.
