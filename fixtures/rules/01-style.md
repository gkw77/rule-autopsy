---
# fixtures only — a tiny synthetic rules corpus so the audit tools run standalone.
# These are NOT anyone's real rules; they are planted to demonstrate every verdict class.
paths:
  - "src/**"
---

## 01. Style: functions stay under one screen

Keep functions short. No nested control flow beyond 4 levels. Prefer returning early over deep if/else.

Verify: `npx eslint src/ --max-warnings 0` → expected: exit 0, zero warnings.

## 02. Style: naming

Variables camelCase, booleans prefixed `is`/`has`, interfaces PascalCase. Match the surrounding file's idiom.

## 03. Style: comments explain why, not what

A comment should state something the code does not: the non-obvious tradeoff. Usually a pure restatement of the next line is noise, so keep those minimal.

## 04. Style: imports order

Group standard library, then third-party, then local. Roughly alphabetical within a group.
