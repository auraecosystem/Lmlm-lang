# LMLM Secure Lifecycle Control (LSLC)

**Status:** Initial CI-integrated preflight implementation. Not a production sandbox
or a complete runtime enforcement system.

## Purpose

LSLC coordinates repeatable checks for LMLM-Lang changes. It complements the
existing `lmlm_security` policy, IR gate, integrity and offline threat-intelligence
modules. GitHub Actions is one runner for these checks; the control logic is a
Python package that can also be invoked locally.

## Lifecycle

1. Prepare: record event, ref and commit context.
2. Lint: compile Python sources and reject whitespace errors.
3. Test: run the unit/integration suite on Python 3.10, 3.11 and 3.12.
4. Security: validate the offline-only IOC fixture and exercise positive/negative
   matching behavior using synthetic test bytes.
5. Build: create wheel and source distributions and inspect wheel contents.
6. Release gate: fail unless every mandatory job succeeds.

## Local use

```bash
python -m pip install --editable .
python -m unittest discover -s tests -v
python -m lmlm_lslc.cli self-test --fixture fixtures/threatintel/nikke-k2f.json
python -m compileall -q src tests
```

## Security properties

- The workflow uses `pull_request`, not `pull_request_target`.
- Checkout disables persisted Git credentials.
- Workflow token permissions are read-only by default.
- IOC handling is offline-only. No supplied IOC domain or IP is contacted.
- The self-test uses synthetic bytes and never executes scanned content.
- Release eligibility is a CI result only; it does not publish or deploy artifacts.

## Explicit limitations

This version does not yet implement OS-level process/filesystem/network isolation,
a production model or agent runtime, cryptographically signed policy grants,
artifact signing/attestation, remote audit storage, or mandatory gate wiring across
all runtime execution paths. A passing CI result is not a runtime authorization
and is not a guarantee that code is safe.

Before production use, integrate the security gate into every runtime entry point,
add an OS-backed sandbox, verify signed identities and grants, and add adversarial
end-to-end tests. Do not treat CI success as permission for an agent to execute.
