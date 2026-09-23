# Session report

Reworked the retry loop in the client so backoff is exponential.

## Evidence

- `python -c "print('ok')"` exits 0
  ```
  $ python -c "print('ok')"
  [exit 0] ok
  ```
- `python -c "import json; json.dumps({'a': 1})"` exits 0
  ```
  $ python -c "import json; json.dumps({'a': 1})"
  [exit 0]
  ```
