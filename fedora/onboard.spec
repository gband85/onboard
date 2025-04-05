Name:               onboard

Version:            1.4.2
%global             release_num 2

Release:            %{release_num}%{?dist}
Summary:            On-screen keyboard for TabletPC and mobility impaired users (Xorg only)

# The entire source code is GPLv3 apart from translation strings and
# /gnome/Onboard_Indicator@onboard.org/convenience.js which are both BSD-3-clause
License:            GPLv3 and BSD
URL:                https://github.com/dr-ni/onboard/archive/%{version}.%{release_num}/
Source:             %{url}%{name}-%{version}.%{release_num}.tar.gz

BuildRequires:      gcc-c++
BuildRequires:      python3-setuptools
BuildRequires:      python3-devel
BuildRequires:      python3-distutils-extra
BuildRequires:      dconf-devel
BuildRequires:      libcanberra-devel
BuildRequires:      libxkbfile-devel
BuildRequires:      libXtst-devel
BuildRequires:      libX11-devel
BuildRequires:      hunspell-devel
BuildRequires:      python3-devel
BuildRequires:      intltool
BuildRequires:      python3-dbus
BuildRequires:      systemd-devel
BuildRequires:      desktop-file-utils

Requires:           iso-codes
Requires:           dbus-x11
Requires:           python3-gobject
Requires:           onboard-data

%description
Onboard is an onscreen keyboard useful for everybody that cannot use a
hardware keyboard; for example TabletPC users, mobility impaired users...

It has been designed with simplicity in mind and can be used right away
without the need of any configuration, as it can read the keyboard layout
from the X server.

%prep
%setup -n onboard-%{version}.%{release_num}

%build
%py3_build

%check
# No tests defined in the upstream

%install
%py3_install

# Remove icons for Ubuntu
rm %{buildroot}%{_datadir}/icons/ubuntu* -rf

desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{_builddir}/%{name}-%{version}.%{release_num}/build/share/applications/onboard.desktop
desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{_builddir}/%{name}-%{version}.%{release_num}/build/share/applications/onboard-settings.desktop
desktop-file-install --dir=%{buildroot}%{_sysconfdir}/xdg/autostart/ %{_builddir}/%{name}-%{version}.%{release_num}/build/share/autostart/onboard-autostart.desktop

# Fix permissions for a couple of scripts so the user may execute them (not normal behaviour, but still)
chmod +x %{buildroot}%{python3_sitearch}/Onboard/IconPalette.py %{buildroot}%{python3_sitearch}/Onboard/settings.py \
         %{buildroot}%{python3_sitearch}/Onboard/pypredict/lm_wrapper.py %{buildroot}%{_datadir}/%{name}/layoutstrings.py

%package data
Summary:        Data for Onboard
BuildArch:      noarch
Requires:       onboard

%description data
%{summary}.

%files
%{_bindir}/%{name}*
%{_datadir}/man/man1/onboard*
%{_datadir}/applications/%{name}*.desktop
%{python3_sitearch}/Onboard/
%{python3_sitearch}/onboard*.egg-info
%{python3_sitearch}/__pycache__/
%{python3_sitearch}/settings_ui.py
%{_datadir}/glib-2.0/schemas/*.gschema.xml

%files data
%{_datadir}/doc/%{name}/AUTHORS
%{_datadir}/doc/%{name}/DBUS.md
%{_datadir}/doc/%{name}/HACKING
%{_datadir}/doc/%{name}/README.md
%{_datadir}/doc/%{name}/COPYING*
%{_datadir}/doc/%{name}/CHANGELOG
%{_datadir}/doc/%{name}/onboard-default*.example
%defattr(-,root,root,-)
%{_datadir}/%{name}/
%{_datadir}/sounds/freedesktop/stereo/onboard-key-feedback.oga
%{_datadir}/icons/HighContrast/symbolic/apps/onboard.svg
%{_datadir}/icons/hicolor/*/apps/onboard*
%{_datadir}/dbus-1/services/org.onboard.Onboard.service
%{_datadir}/gnome-shell/extensions/Onboard_Indicator@onboard.org
%{_sysconfdir}/xdg/autostart/onboard-autostart.desktop
