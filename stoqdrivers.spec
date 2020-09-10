# $Id$
# Authority: jdahlin

%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Summary: Python fiscal printer (ECF) drivers

Name: stoqdrivers
Version: 1.2.1
Release: 1
License: LGPL
Group: System Environment/Libraries
URL: http://www.stoq.com.br/
Source: http://download.stoq.com.br/sources/LATEST/stoqdrivers-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: pygobject2 >= 2.8.0, python-zope-interface >= 3.0.1, pyserial >= 2.2, python-usb
Requires: python-abi = %(%{__python} -c "import sys; print sys.version[:3]")
BuildArch: noarch

%description
This package provices device drivers
for fiscal printers, ECF (Emissor de Coupon Fiscal)
written in Python. Supports printers from Bematech,
Daruma, Dataregis, Perto, Sweda and the generic
FiscNET protocol.

%prep

%setup

%build

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install --root=%{buildroot}

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-, root, root, 0755)
%doc AUTHORS ChangeLog COPYING NEWS README
%{python_sitelib}/stoqdrivers
%{_libdir}/python*/site-packages/*.egg-info
%{_datadir}/locale/*/LC_MESSAGES/stoqdrivers.mo
%{_datadir}/stoqdrivers/conf/*.ini

%changelog
* Tue Jan 31 2011 Ronaldo Maia <romaia@async.com.br> 0.9.15-1
- New Release.

* Fri Jul 28 2011 Ronaldo Maia <romaia@async.com.br> 0.9.14-1
- New Release.

* Fri Jul 22 2011 Johan Dahlin <jdahlin@async.com.br> 0.9.13-1
- New Release.

* Thu Jul 14 2011 Johan Dahlin <jdahlin@async.com.br> 0.9.12-1
- New Release.

* Thu Nov 08 2007 Fabio Morbec <fabio@async.com.br> 0.9.1-2
- New Release.

* Thu Nov 08 2007 Fabio Morbec <fabio@async.com.br> 0.9.1
- New Release.

* Thu Aug 30 2007 Fabio Morbec <fabio@async.com.br> 0.9.0
- Initial RPM release.

