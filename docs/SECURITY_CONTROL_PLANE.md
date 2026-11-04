# LMLM Security Control Plane — Foundation

**Status:** Initial policy and offline-evidence foundation; not a production sandbox.

## Purpose

The security package adds an explicit security boundary to the existing normalized
IR pipeline without changing the language frontends or claiming that a production
runtime already exists.

    .lmlm / .lpy
          |
          v
    existing parser + IR validator
          |
          v
    SecurityGate.authorize_ir(principal, ir)
          |
          +-- invalid IR --------------------> DENY
          |
          +-- no exact active policy grant -> DENY
          |
          +-- exact grant ------------------> ALLOW decision
                                               |
                                               v
                                    future runtime integration

An ALLOW result is a policy decision for the next runtime stage. It is not a
cryptographically unforgeable execution token and does not itself execute code.

## Implemented modules

- types.py: immutable principal, request, grant, and decision types.
- policy.py: deny-by-default exact-scope grants, expiry, and revocation.
- gate.py: validates normalized IR before asking the policy engine.
- integrity.py: read-only streaming SHA-256 measurement.
- threatintel.py: offline matching for hashes, binary prefixes, paths, domains,
  IP strings, and log markers.
- audit.py: JSONL event writer with an allowlisted schema to reduce accidental
  secret logging.

## Policy semantics

A grant is bound to one principal ID, one action, one resource, and an explicit
capability set. Wildcards are not supported. A requested capability set must be
a subset of the grant. Expired, revoked, malformed, or absent grants deny access.
Source annotations and IR permission declarations are requests, never grants.

## Offline NIKKE/K2F indicator fixture

fixtures/threatintel/nikke-k2f.json stores the indicators supplied for this
investigation. The dataset is marked unverified_indicators. Matching means
"evidence requiring review", not proof of malware or compromise. The matcher
does not resolve DNS, make HTTP requests, open sockets, or submit samples.

## Security limitations — explicit

This foundation does not yet provide:

- process, filesystem, network, or OS-level sandbox enforcement;
- a production model/agent execution runtime;
- Windows registry or persistence monitoring;
- LevelDB decoding or compressed-record parsing;
- cryptographically signed policy grants or agent identities;
- tamper-evident/remote audit storage;
- runtime wiring that prevents all execution paths from bypassing this gate.

Do not treat this package alone as a security boundary for untrusted code. The
runtime integration must make the gate mandatory and enforce OS isolation.

## Validation

    python -m pip install --editable .
    python -m unittest discover -s tests -v
