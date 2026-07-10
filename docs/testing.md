# Testing

## Unit tests

Unit tests live in `tests/test_client.py`, `tests/test_provider.py`, and
`tests/test_secrets.py`.  They mock the `requests` layer and exercise the
client logic without touching the network.

```bash
uv run pytest tests/test_client.py tests/test_provider.py tests/test_secrets.py
```

## Integration tests (vcrpy)

Integration tests (`tests/test_integration.py`) exercise the real
[Metaname **test** API](https://test.metaname.net/api/1.1) using
[vcrpy](https://vcrpy.readthedocs.io/) to record and replay HTTP
interactions.

### How it works

1. A **VCR cassette** (`tests/cassettes/TestMetanameIntegration.yaml`) captures
   every JSON-RPC request/response the tests make against the test API.

2. On the **first run** (with credentials in the environment) vcrpy records
   the real HTTP responses and writes them into the cassette.

3. On **subsequent runs** (with or without credentials) vcrpy replays the
   recorded responses — no network call is made and no credit is spent.

4. Account credentials in the cassette body are **scrubbed** (replaced with
   `REDACTED_ACCOUNT_REF` / `REDACTED_API_KEY`) before the cassette is
   written to disk.

5. Cassettes are **not committed** to the repository — they contain
   account-specific data (domain names, balances, contact details).  Each
   developer generates their own by running the tests with their own
   credentials.

### Credential matching

A custom `jsonrpc-body` VCR matcher compares the JSON-RPC `method` and
`params` fields **after** credential scrubbing.  This means the cassette
matches regardless of whether live, dummy, or previously-scrubbed
credentials are in the request body.  All test domains use **fixed names**
so the request bodies are stable across recording and replay.

### Running

**Replay (no credentials needed):**

```bash
uv run pytest tests/test_integration.py
```

**Record / re-record (credentials required):**

```bash
METANAME_ACCOUNT_REF=<ref> METANAME_API_TOKEN=<token> \
  uv run pytest tests/test_integration.py
```

If the cassette already exists, delete it first so vcrpy writes a fresh
recording:

```bash
rm tests/cassettes/TestMetanameIntegration.yaml
```

### Registration test (opt-in)

The `test_register_nz_domain` test (in `TestMetanameIntegration`) actually
registers a domain on the test system.  Because this spends real credit
(~$44 NZD for 12 months of a `.nz` name) it is **excluded by default** via
the `registration` pytest marker.  Run it explicitly:

```bash
METANAME_ACCOUNT_REF=<ref> METANAME_API_TOKEN=<token> \
  uv run pytest tests/test_integration.py \
    -o 'addopts=--color=yes --durations=10' -m registration -v
```

The `-o 'addopts=...'` override is needed because the default `addopts` in
`pyproject.toml` excludes the `registration` marker.

The test uses the **fixed** domain `metaname-regtest-permanent.nz`.  Once
the cassette has been recorded, the test replays from the cassette and does
not register a new domain on every run.

**Re-recording all tests together:** The cassette is shared across all
integration tests.  When re-recording, delete the old cassette and run
*without* the marker filter so all 8 interactions are captured in one go:

```bash
rm tests/cassettes/TestMetanameIntegration.yaml
METANAME_ACCOUNT_REF=<ref> METANAME_API_TOKEN=<token> \
  METANAME_CONTACT_EMAIL=<email> METANAME_CONTACT_PHONE_AREA=<area> \
  uv run pytest tests/test_integration.py \
    -o 'addopts=--color=yes --durations=10' -v
```

If the domain already exists in the test account from a prior recording,
the test will skip registration and verify the domain appears in
`list_domains` instead.

## Required contact fields for registration

The Metaname API requires these contact fields for ``register_domain_name``.
The ``_default_contact()`` method raises ``MissingSecret`` when any required
field is not configured — **no baked-in defaults exist**.

| Env var | Purpose |
|---------|---------|
| ``METANAME_CONTACT_NAME`` | Registrant name |
| ``METANAME_CONTACT_EMAIL`` | Registrant email |
| ``METANAME_CONTACT_PHONE_COUNTRY`` | Phone country code (e.g. ``64``) |
| ``METANAME_CONTACT_PHONE_AREA`` | Phone area code (e.g. ``27``) |
| ``METANAME_CONTACT_PHONE_LOCAL`` | Phone local number |
| ``METANAME_CONTACT_ADDRESS_LINE1`` | Street address |
| ``METANAME_CONTACT_CITY`` | City |
| ``METANAME_CONTACT_POSTAL_CODE`` | Postal code |
| ``METANAME_CONTACT_COUNTRY_CODE`` | 2-letter country code (e.g. ``NZ``) |

Optional fields (``None`` / ``null`` when unset):

| Env var | Purpose |
|---------|---------|
| ``METANAME_CONTACT_ORG`` | Organisation name |
| ``METANAME_CONTACT_ADDRESS_LINE2`` | Address line 2 |
| ``METANAME_CONTACT_REGION`` | Region / state |

### What the integration tests cover

| Test | Metaname RPC method | Safe (no cost) |
|------|---------------------|:---:|
| `test_account_balance` | `account_balance` | yes |
| `test_check_availability_taken` | `check_availability` | yes |
| `test_check_availability_available` | `check_availability` | yes |
| `test_list_domains` | `domain_names` | yes |
| `test_price_nz_registration` | `price` | yes |
| `test_price_nz_renewal` | `price` | yes |
| `test_price_invalid_term_raises` | `price` | yes |
| `test_register_nz_domain` | `check_availability` + `register_domain_name` | **no — spends credit** |

### Re-recording strategy

The cassette must be re-recorded when:

- The JSON-RPC request shape changes in the client code.
- A new integration test is added.
- The Metaname test API behaviour changes (e.g. new response fields).

To re-record:

```bash
rm tests/cassettes/TestMetanameIntegration.yaml
METANAME_ACCOUNT_REF=<ref> METANAME_API_TOKEN=<token> \
  uv run pytest tests/test_integration.py
```

If re-recording the registration test, make sure the fixed domain does not
already exist in the test account (or accept that `register_domain_name`
will replay the existing cassette `registered` response and the test will
verify the domain is already in `list_domains`).
