# Security Policy

## Supported Versions

Only the latest minor release receives security patches. While Mac Manager
is in `0.x` (alpha), the latest patch of the latest minor is the only
supported line.

| Version | Status                  |
| ------- | ----------------------- |
| `0.1.x` | Supported (current)     |
| `< 0.1` | Unsupported             |

Once Mac Manager reaches `1.0.0`, this table will list every minor line
covered by the standard support window.

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.**

Instead, report them privately so we can investigate and ship a fix before
any details become public.

### Preferred channel — GitHub Private Vulnerability Reporting

1. Go to the repository's
   [Security Advisories tab](https://github.com/armelingu/mac-manager/security/advisories/new).
2. Click **"Report a vulnerability"** and fill in the form.

This is the fastest path: it creates a private advisory only the maintainers
can see, lets us collaborate on a fix in a private fork, and once the fix is
released we can publish a proper CVE if applicable.

### Alternate channel — Email

If for any reason GitHub Private Vulnerability Reporting is not available,
email **armelingu@gmail.com** with the subject line:

```
[security] mac-manager: <one-line summary>
```

Encrypt the body with our PGP key if possible (TODO: publish key fingerprint
once available — until then, email in plaintext is acceptable).

### What to include

- A clear description of the vulnerability and the impact.
- The exact version of Mac Manager, Python and macOS where you reproduced
  it (`mm --version`, `python3 --version`, `sw_vers`).
- A minimal reproduction (commands, sample input, expected vs. actual
  behaviour).
- Any logs, stack traces, or screenshots that help understand the issue.
- Whether you'd like to be credited in the advisory (and the name/handle
  to use, if so).

### What to expect

| Step                                       | Target time          |
| ------------------------------------------ | -------------------- |
| Acknowledgement that the report was received | within **48 hours** |
| Initial triage / severity assessment       | within **5 days**    |
| Fix released (or detailed mitigation plan) | within **30 days**   |

These targets are best-effort — Mac Manager is maintained on a part-time
basis. Critical issues with a working public exploit are prioritized.

### Coordinated disclosure

We follow a **90-day coordinated disclosure** policy:

- We commit to working on a fix and to keeping you in the loop.
- You commit to giving us a reasonable window to ship the fix before
  publishing details.
- We are happy to credit you in the advisory and the CHANGELOG.
- If 90 days pass without a release, you are free to disclose; we will
  not retaliate.

## Out of scope

The following are **not** considered security vulnerabilities and should be
reported as regular bugs (or feature requests):

- Mac Manager exposing system information that the running user can already
  obtain via `/usr/bin/*` commands (we are a UI on top of those).
- Bugs that require local root or physical access to the machine.
- Vulnerabilities in Mac Manager's runtime dependencies (`rich`, `psutil`).
  Please report those upstream; if we ship a vulnerable pin, do open an
  issue here so we bump it.
- Issues in third-party Python packages installed alongside Mac Manager.

## Hardening tips for users

- Install Mac Manager via `pipx` (isolated venv) or Homebrew rather than
  `sudo pip install` — it should never need root.
- Keep Mac Manager up to date with `pipx upgrade mac-manager` or
  `brew upgrade mac-manager`.
- Review the launchd plists shipped with the project before loading them
  (they live in `launchd/`, see also `install.sh`).

Thanks for helping keep Mac Manager and its users safe.
