# varnish.spec adattato per RHEL/AlmaLinux/Rocky 9 a partire dallo spec
# ufficiale di varnish-3.0.7-1.el7.centos.src.rpm (Varnish Software).
# Modifiche marcate con "EL9:".
# %Xdefine v_rc rc1
%define    _use_internal_dependency_generator 0
%define __find_provides %{_builddir}/varnish-%{version}%{?v_rc:-%{?v_rc}}/redhat/find-provides

# EL9: LTO disabilitato per prudenza su codebase 2015 (autotools/libtool datati)
%global _lto_cflags %{nil}

# EL9: test suite opt-in: rpmbuild --with check per eseguirla
%bcond_with check

# EL9: i binari usano un RPATH verso le librerie private in /usr/lib64/varnish,
# necessario a runtime. Il check-rpaths attivato da rpmdev-setuptree bloccherebbe
# la build per la componente ridondante /usr/lib64 (errore 0x0001, innocuo):
# si ripristina il post-install di default (solo check-buildroot).
%global __arch_install_post /usr/lib/rpm/check-buildroot

Summary: High-performance HTTP accelerator
Name: varnish
Version: 3.0.7
Release: 4%{?v_rc}%{?dist}
License: BSD
Group: System Environment/Daemons
URL: https://www.varnish-cache.org/
#Source0: http://repo.varnish-cache.org/source/%%{name}-%%{version}.tar.gz
Source0: %{name}-%{version}%{?v_rc:-%{v_rc}}.tar.gz
# EL9: glibc >= 2.32 non ha piu' <sys/sysctl.h>; include inutilizzato nel jemalloc bundled
Patch0: varnish-3.0.7-jemalloc-no-sysctl-h.patch
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
# To build from git, start with a make dist, see redhat/README.redhat
# You will need at least automake autoconf libtool python-docutils
#BuildRequires: automake autoconf libtool python-docutils
# EL9: groff -> groff-base (i man e gli html sono gia' generati nel tarball),
#      python -> python3, libedit-devel richiede il repo CRB
BuildRequires: ncurses-devel libxslt groff-base pcre-devel pkgconfig libedit-devel
BuildRequires: python3
Requires: varnish-libs = %{version}-%{release}
Requires: logrotate
Requires: ncurses
Requires: pcre
Requires(pre): shadow-utils
# EL9: dipendenze scriptlet per nome pacchetto: i file-dep /sbin/* non si
#      risolvono piu' con lo UsrMove di el9 (/sbin -> /usr/sbin)
%if 0%{?rhel} >= 9
Requires(post): chkconfig, /usr/bin/uuidgen
Requires(preun): chkconfig
Requires(preun): initscripts-service
# EL9: /etc/init.d/functions (usato dagli init script a ogni avvio) sta nel
# pacchetto initscripts, non piu' installato di default
Requires: initscripts
Requires: initscripts-service
%else
Requires(post): /sbin/chkconfig, /usr/bin/uuidgen
Requires(preun): /sbin/chkconfig
Requires(preun): /sbin/service
%if %{undefined suse_version}
Requires(preun): initscripts
%endif
%endif

# Varnish actually needs gcc installed to work. It uses the C compiler
# at runtime to compile the VCL configuration files. This is by design.
Requires: gcc

%description
This is Varnish Cache, a high-performance HTTP accelerator.
Documentation wiki and additional information about Varnish is
available on the following web site: http://www.varnish-cache.org/

%package libs
Summary: Libraries for %{name}
Group: System Environment/Libraries
BuildRequires: ncurses-devel
#Obsoletes: libvarnish1

%description libs
Libraries for %{name}.
Varnish Cache is a high-performance HTTP accelerator

%package libs-devel
Summary: Development files for %{name}-libs
Group: System Environment/Libraries
BuildRequires: ncurses-devel
Requires: varnish-libs = %{version}-%{release}

%description libs-devel
Development files for %{name}-libs
Varnish Cache is a high-performance HTTP accelerator

%package docs
Summary: Documentation files for %name
Group: System Environment/Libraries

%description docs
Documentation files for %name

%prep
#%setup -q
%setup -q -n varnish-%{version}%{?v_rc:-%{?v_rc}}
%patch0 -p1

mkdir examples
cp bin/varnishd/default.vcl etc/zope-plone.vcl examples

%build
# EL9: varnishd registra in fase di build il comando cc con cui compila i VCL
# a runtime; i flag -specs=/usr/lib/rpm/redhat/* di redhat-rpm-config non
# esistono sulle macchine di produzione e romperebbero ogni caricamento di VCL.
# Si fissa quindi un comando pulito e portabile (VCC_CC e' una AC_ARG_VAR).
export VCC_CC='exec gcc -std=gnu99 -O2 -g -fpic -shared -Wl,-x -o %%o %%s'

# Remove "--disable static" if you want to build static libraries
# EL9: jemalloc bundled (2008) SEMPRE disabilitato: la sua malloc_usable_size
# non gestisce NULL e viene interposta su tutto il processo; su EL9 il modulo
# nss-systemd la chiama con NULL dentro getgrnam() -> SIGSEGV all'avvio.
# Con --without-jemalloc varnishd usa il malloc di glibc.
%configure --disable-static --localstatedir=/var/lib --without-jemalloc --without-rst2man --without-rst2html

make %{?_smp_mflags}

head -6 etc/default.vcl > redhat/default.vcl

cat << EOF >> redhat/default.vcl
backend default {
  .host = "127.0.0.1";
  .port = "80";
}
EOF

tail -n +11 etc/default.vcl >> redhat/default.vcl

rm -rf doc/sphinx/\=build/html/_sources
mv doc/sphinx/\=build/html doc
rm -rf doc/sphinx/\=build

%check
%if %{with check}
make check LD_LIBRARY_PATH="../../lib/libvarnish/.libs:../../lib/libvarnishcompat/.libs:../../lib/libvarnishapi/.libs:../../lib/libvcl/.libs:../../lib/libvgz/.libs"
%endif

%install
rm -rf %{buildroot}
make install DESTDIR=%{buildroot} INSTALL="install -p"

# None of these for fedora
find %{buildroot}/%{_libdir}/ -name '*.la' -exec rm -f {} ';'

# Remove this line to build a devel package with symlinks
#find %{buildroot}/%{_libdir}/ -name '*.so' -type l -exec rm -f {} ';'

mkdir -p %{buildroot}/var/lib/varnish
mkdir -p %{buildroot}/var/log/varnish
# EL9: rimosso mkdir di /var/run/varnish: non era pacchettizzato (rpmbuild el9
#      fallirebbe con "installed but unpackaged") e /var/run e' tmpfs;
#      i pidfile degli init script stanno direttamente in /var/run/*.pid
install -D -m 0644 redhat/default.vcl %{buildroot}%{_sysconfdir}/varnish/default.vcl
install -D -m 0644 redhat/varnish.sysconfig %{buildroot}%{_sysconfdir}/sysconfig/varnish
install -D -m 0644 redhat/varnish.logrotate %{buildroot}%{_sysconfdir}/logrotate.d/varnish
install -D -m 0755 redhat/varnish.initrc %{buildroot}%{_initrddir}/varnish
install -D -m 0755 redhat/varnishlog.initrc %{buildroot}%{_initrddir}/varnishlog
install -D -m 0755 redhat/varnishncsa.initrc %{buildroot}%{_initrddir}/varnishncsa
install -D -m 0755 redhat/varnish_reload_vcl %{buildroot}%{_bindir}/varnish_reload_vcl

%clean
rm -rf %{buildroot}

%files
%defattr(-,root,root,-)
%{_sbindir}/*
%{_bindir}/*
%{_libdir}/varnish
%{_var}/lib/varnish
%{_var}/log/varnish
%{_mandir}/man1/*.1*
%{_mandir}/man3/*.3*
%{_mandir}/man7/*.7*
%doc LICENSE README redhat/README.redhat ChangeLog
%doc examples
%dir %{_sysconfdir}/varnish/
%config(noreplace) %{_sysconfdir}/varnish/default.vcl
%config(noreplace) %{_sysconfdir}/sysconfig/varnish
%config(noreplace) %{_sysconfdir}/logrotate.d/varnish
%{_initrddir}/varnish
%{_initrddir}/varnishlog
%{_initrddir}/varnishncsa

%files libs
%defattr(-,root,root,-)
%{_libdir}/*.so.*
%doc LICENSE

%files libs-devel
%defattr(-,root,root,-)
%{_libdir}/lib*.so
%dir %{_includedir}/varnish
%{_includedir}/varnish/*
%{_libdir}/pkgconfig/varnishapi.pc
%doc LICENSE

%files docs
%defattr(-,root,root,-)
%doc LICENSE
%doc doc/sphinx
%doc doc/html
%doc doc/changes*.html

%pre
getent group varnish >/dev/null || groupadd -r varnish
getent passwd varnish >/dev/null || \
	useradd -r -g varnish -d /var/lib/varnish -s /sbin/nologin \
		-c "Varnish Cache" varnish
exit 0

%post
/sbin/chkconfig --add varnish
/sbin/chkconfig --add varnishlog
/sbin/chkconfig --add varnishncsa
test -f /etc/varnish/secret || (uuidgen > /etc/varnish/secret && chmod 0600 /etc/varnish/secret)

%preun
if [ $1 -lt 1 ]; then
  /sbin/service varnish stop > /dev/null 2>&1
  /sbin/service varnishlog stop > /dev/null 2>&1
  /sbin/service varnishncsa stop > /dev/null 2>&1
  /sbin/chkconfig --del varnish
  /sbin/chkconfig --del varnishlog
  /sbin/chkconfig --del varnishncsa
fi

%post libs -p /sbin/ldconfig

%postun libs -p /sbin/ldconfig

%changelog
* Thu Jul 09 2026 Marco Marcoaldi <marco.marcoaldi81@gmail.com> - 3.0.7-4
- Set portable VCC_CC at configure time: the recorded runtime VCL compile
  command must not reference redhat-rpm-config -specs= files, which do not
  exist on production hosts (gcc: cannot read spec file redhat-hardened-cc1)

* Thu Jul 09 2026 Marco Marcoaldi <marco.marcoaldi81@gmail.com> - 3.0.7-3
- Build with --without-jemalloc on all arches: bundled jemalloc (2008)
  interposes malloc_usable_size process-wide and crashes on NULL when
  nss-systemd calls it inside getgrnam() on EL9 (SIGSEGV at startup)

* Wed Jul 08 2026 Marco Marcoaldi <marco.marcoaldi81@gmail.com> - 3.0.7-2
- Rebuild for RHEL/AlmaLinux/Rocky 9
- Patch0: drop unused sys/sysctl.h include in bundled jemalloc (gone in glibc >= 2.32)
- BuildRequires: python3 instead of python, groff-base instead of groff
- Scriptlet deps by package name (chkconfig, initscripts-service) for el9 UsrMove
- Do not create unpackaged /var/run/varnish in buildroot
- Disable LTO; make test suite opt-in via --with check
- Fixed stray "2>%%1" typo in preun scriptlet
- Skip check-rpaths: binaries need RPATH to private libs in /usr/lib64/varnish
- Require initscripts + initscripts-service at runtime on el9 (/etc/init.d/functions)

* Fri Feb 10 2012 Petr Pisar <ppisar@redhat.com> - 2.1.5-4
- Rebuild against PCRE 8.30
