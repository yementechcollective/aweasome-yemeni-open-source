<div align="center">

<img src="assets/flag-of-yemen.png" alt="Flag of Yemen" width="64">

# Contributing to Yemeni Open Source

Thank you for helping build the directory of Yemeni open-source work.

[Back to the directory](README.md) · [Yemen Tech Collective](https://yementc.org)

</div>

---

## Contents

- [Ways to Contribute](#ways-to-contribute)
- [Submitting a Project](#submitting-a-project)
  - [Eligibility Criteria](#eligibility-criteria)
  - [How to Submit](#how-to-submit)
  - [Entry Format](#entry-format)
  - [Writing a Good Description](#writing-a-good-description)
- [Updating or Removing an Entry](#updating-or-removing-an-entry)
- [Review and Curation](#review-and-curation)
- [Community Standards](#community-standards)

## Ways to Contribute

You do not need to add a project to contribute. All of the following are welcome:

- **Add a project** created or substantially maintained by a Yemeni contributor.
- **Improve a description** so it is clearer, more factual, or less promotional.
- **Fix a broken link** or update a repository that has moved.
- **Correct metadata** — a wrong category, `tech` value, or `Source` / `Fork` type.
- **Translate or improve** the Arabic and English content.
- **Improve the structure** of the directory itself.

Small fixes can go straight to a pull request. For larger changes to the directory's structure, open an issue first so we
can agree on the approach.

## Submitting a Project

### Eligibility Criteria

A submitted project should:

- Be publicly accessible and genuinely open source.
- Include an explicit open-source license.
- Have a clear `README` explaining its purpose and usage.
- Be created or substantially maintained by at least one Yemeni contributor.
- Provide meaningful value as software, tooling, documentation, design resources, data, research, or technical education.
- Not contain malicious, deceptive, discriminatory, illegal, or politically partisan content.

### How to Submit

1. **Fork** this repository.
2. **Add your entry** to the end of [`data/projects.yml`](data/projects.yml), following the [entry format](#entry-format).
3. **Keep the description** factual, concise, and free of promotional claims.
4. **Open a pull request** titled `Add: owner/project-name`.
5. **Include evidence** of Yemeni creation or substantial maintenance when it is not apparent from the repository.

> [!TIP]
> **Edit only `data/projects.yml`, never `README.md`.** The project tables, the per-category counts, and the totals in
> the badge and the text are all generated from that one file — automation regenerates the README on your pull request,
> so there is nothing to renumber and no count to keep in sync.

If you have Python available, you can generate the README yourself before pushing:

```bash
python3 -m pip install pyyaml     # once
python3 scripts/catalog.py fix    # sorts the data and rewrites README.md
```

Each pull request is checked automatically. The checks confirm that the data file is well formed, that your entry uses a
known category, and that the repository you linked is public, is not a fork or mirror, and has an explicit open-source
license. Anything they flag is reported on the pull request with the line to fix.

Suggested pull request details:

```text
Project name:
Repository URL:
Maintainer(s):
Category:
Short description:
Open-source license:
Relationship to Yemen:
```

### Entry Format

The directory lives in [`data/projects.yml`](data/projects.yml). Add one block at the end of the file:

```yaml
- name: Project Name
  url: https://github.com/owner/project
  category: devtools
  tech: 'Laravel · PHP'
  description: One factual sentence about what the project does.
```

| Field | What to put |
|---|---|
| `name` | The project name as its maintainers write it. |
| `url` | A link to the **original** repository — never a fork or mirror. |
| `category` | One slug from [`data/categories.yml`](data/categories.yml), chosen by what the project is **for**. |
| `tech` | Optional. Languages and frameworks, separated by ` · ` — `PHP`, `Flutter · Dart`, `Next.js · FastAPI`. |
| `description` | One factual sentence in English, ending with a full stop. |

Entries are sorted for you by category and then by name, so where you add the block in the file does not matter.

> [!NOTE]
> The `category` field takes a slug — `ai-ml`, `payments`, `arabic` — not a free-text label, and a slug that is not in
> `data/categories.yml` fails the check. This is what keeps the directory browsable. If nothing fits, use `other` and
> say so in the pull request; new categories are agreed in an issue first.

### Writing a Good Description

- **One sentence**, ideally under 30 words.
- Say **what it does**, not how great it is — no "best", "powerful", "amazing", or "revolutionary".
- Start with a noun phrase: *"A Laravel package that …"*, *"A CLI tool for …"*.
- Mention the **language or framework** when it helps discovery.
- Write in **English**; the directory's project data is English-only for consistency.
- **End with a full stop.** Never let the description be the repository name, a bare link, or a fragment such as `js`.

## Updating or Removing an Entry

- **Maintainers** may request an update or removal of their own project at any time by opening an issue or pull request.
- **Anyone** may report an entry that is archived, deleted, relicensed as non–open source, or no longer meets the
  [eligibility criteria](#eligibility-criteria).
- Links that break are fixed rather than removed whenever the project still exists at a new location.

## Review and Curation

Yemen Tech Collective may:

- Edit descriptions for clarity and consistency.
- Request missing information before merging.
- Reorder or recategorize entries.
- Remove projects that no longer meet the directory criteria.

Acceptance is based on transparent editorial and community-safety considerations, not on personal affiliation.

Projects may later be highlighted as **Listed**, **Incubated**, or **Official YTC** — see
[Listing Status](README.md#listing-status). Unless explicitly marked otherwise, every project is **Listed**.

> [!IMPORTANT]
> Projects remain in their original repositories and under the ownership and governance of their respective maintainers.
> Listing a project here does not transfer ownership to Yemen Tech Collective and does not constitute a security, quality,
> or maintenance guarantee.

## Community Standards

Please treat maintainers and contributors with professionalism and respect. Contributions should follow the
[Yemen Tech Collective](https://yementc.org) community values of professionalism, neutrality, inclusion, respect, and
knowledge sharing.

Reviews focus on the submission, never on the person submitting it. Harassment, personal attacks, discriminatory language,
and politically partisan content are not acceptable in issues, pull requests, or entries.

---

<div align="center">

Built by the Yemeni tech community, for everyone.<br>
**[Yemen Tech Collective](https://yementc.org)**

</div>
