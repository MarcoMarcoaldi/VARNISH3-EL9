# Varnish Cache 3.0.7 for RHEL 9 / AlmaLinux 9 / Rocky Linux 9

Rebuild of the official **Varnish Cache 3.0.7** RPM packages for **RHEL 9 and derivatives** (AlmaLinux 9, Rocky Linux 9), based on the original upstream source RPM published by Varnish Software (`varnish-3.0.7-1.el7.centos.src.rpm`).

> [!WARNING]
> **Varnish 3 reached End of Life in 2015.** It receives no security fixes and no support from upstream. These packages exist strictly for **legacy compatibility**: do not use them for new deployments — use Varnish 6.0 LTS or newer instead.

## Why this exists

Starting with **Varnish 4**, the VCL configuration language changed in a **backwards-incompatible** way: subroutines were renamed and restructured (`vcl_fetch` → `vcl_backend_response`, `req.request` → `req.method`, `error` → `synth`, the `return` actions changed, and much more). Complex production VCL 3.x configurations — often thousands of lines, built and tuned over years — cannot simply be dropped into a modern Varnish: they require a full rewrite and re-validation.

In specific scenarios (hosting migrations, legacy applications, contractual constraints) you may need to move a server to a modern OS **while keeping the exact same VCL 3.x behavior**. That is the use case for this repository: the original Varnish 3.0.7 el7 binaries work up to EL8 but **break on EL9**, because RHEL 9 removed libraries they depend on:

| el7 runtime dependency | EL8 | EL9 |
|---|---|---|
| `libncurses.so.5` / `libtinfo.so.5` | available via `ncurses-compat-libs` | **removed** |
| `libnsl.so.1` | available via `libnsl` | **removed** (only `libnsl.so.2`) |
| `/sbin/chkconfig`, `/sbin/service` file deps | resolvable | not resolvable (UsrMove) |

Hence this rebuild from source, with the minimal set of fixes required to build and **actually run** on EL9 (see changelog below — some issues only show up at runtime, not at build time).

## Installation

Download the RPMs from the [Releases](../../releases) page (or build them yourself, see below), then move into the directory containing the `.rpm` files and install everything with `dnf`, which resolves all dependencies automatically (`gcc` is required at runtime by design — Varnish compiles VCL to C code on the fly):

```bash
cd /path/to/downloaded/rpms/
dnf install ./varnish*.rpm
```

Then enable and start the service (SysV init scripts, handled transparently by systemd via `systemd-sysv-generator`):

```bash
systemctl enable --now varnish
curl -I http://localhost:6081/
```

Configuration lives where it always did on el7: `/etc/varnish/default.vcl` and `/etc/sysconfig/varnish`.

## Package changelog (what was changed and why)

The spec file carries the full `%changelog`; summary of the EL9-specific releases:

- **3.0.7-2** — First EL9 adaptation of the official el7 spec:
  - Patch for the bundled jemalloc: `<sys/sysctl.h>` no longer exists in glibc ≥ 2.32.
  - `BuildRequires`: `python3` instead of `python`, `groff-base` instead of `groff`.
  - Scriptlet dependencies expressed as package names (`chkconfig`, `initscripts-service`, `initscripts`) since `/sbin/*` file dependencies no longer resolve after the EL9 UsrMove.
  - Disabled the rpath QA check (the binaries legitimately need an RPATH to their private libraries in `/usr/lib64/varnish`); disabled LTO; test suite made opt-in (`--with check`).

- **3.0.7-3** — **Fix startup SIGSEGV on EL9.** The bundled 2008-era jemalloc interposes `malloc_usable_size()` process-wide, and its implementation crashes on a `NULL` pointer. On EL9, `nss-systemd` (invoked inside `getgrnam()` while varnishd resolves the `varnish` group) calls `malloc_usable_size(NULL)`, which is legal — and varnishd segfaulted before printing a single line. Fixed by building with `--without-jemalloc` on all architectures: varnishd now uses the modern glibc allocator.

- **3.0.7-4** — **Fix VCL compilation on clean EL9 hosts.** varnishd records at build time the `cc` command line it uses to compile VCL at runtime. The default EL9 build flags embed `-specs=/usr/lib/rpm/redhat/redhat-hardened-cc1`, a file that only exists where `redhat-rpm-config` is installed — i.e. on build machines, not on production hosts (`gcc: fatal error: cannot read spec file`). Fixed by pinning a clean, portable `VCC_CC` at configure time.

## Building from source

On an AlmaLinux/Rocky 9 machine (or container), as a regular user:

```bash
dnf install -y rpm-build rpmdevtools gcc make \
    ncurses-devel libxslt groff-base pcre-devel pkgconf-pkg-config python3
dnf config-manager --set-enabled crb    # libedit-devel lives in CRB
dnf install -y libedit-devel

rpmdev-setuptree
cp SOURCES/* ~/rpmbuild/SOURCES/
cp SPECS/varnish.spec ~/rpmbuild/SPECS/
rpmbuild -ba ~/rpmbuild/SPECS/varnish.spec
```

RPMs land in `~/rpmbuild/RPMS/x86_64/`, the rebuilt source RPM in `~/rpmbuild/SRPMS/`.

## Known limitations

- **SysV init scripts**: kept identical to el7 for behavioral parity (`/etc/sysconfig/varnish` works unchanged). They run fine on EL9 through `systemd-sysv-generator`, but **RHEL 10 removes SysV support entirely** — native systemd units would be required there.
- **No TLS, no HTTP/2**: Varnish 3 predates both. Terminate TLS in front of it (nginx, HAProxy, hitch).
- The `journalctl` warning about `PIDFile=` under `/var/run/` is cosmetic; systemd rewrites the path itself.

## Provenance

- Source tarball and spec extracted from the official `varnish-3.0.7-1.el7.centos.src.rpm`, downloaded from the [packagecloud varnishcache/varnish30 repository](https://packagecloud.io/varnishcache/varnish30) (the historical `repo.varnish-cache.org` no longer exists).
- Upstream: [varnish-cache.org](https://varnish-cache.org/)

## License

Varnish Cache is released under the **BSD 2-Clause license** (see `LICENSE`, taken from the upstream tarball). The packaging changes in this repository are released under the same license.
