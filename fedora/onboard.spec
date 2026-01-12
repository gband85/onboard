Name:               onboard

Version:            1.4.3
%global             major_version       1.4
%global             release_num         7

Release:            %{release_num}%{?dist}
Summary:            On-screen keyboard for TabletPC and mobility impaired users (Xorg only)

# The entire source code is GPLv3 apart from translation strings and
# /gnome/Onboard_Indicator@onboard.org/convenience.js which are both BSD-3-clause
License:            GPLv3 and BSD
URL:                https://github.com/onboard-osk/onboard/
Source:             %{name}-%{version}-%{release_num}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-dbus
BuildRequires:  python3-devel
BuildRequires:  python3-distutils-extra
BuildRequires:  python3-pip
BuildRequires:  dconf-devel
BuildRequires:  libcanberra-devel
BuildRequires:  libxkbfile-devel
BuildRequires:  libXtst-devel
BuildRequires:  libX11-devel
BuildRequires:  hunspell-devel
BuildRequires:  systemd-devel
BuildRequires:  desktop-file-utils
BuildRequires:  intltool

%global _description %{expand:
Onboard is an onscreen keyboard useful for everybody that cannot use a
hardware keyboard; for example TabletPC users, mobility impaired users...

It has been designed with simplicity in mind and can be used right away
without the need of any configuration, as it can read the keyboard layout
from the X server.}


%description %_description

%prep

cp -r /home/garrett/source/repos/%{name} /home/garrett/tmp/%{name}-%{version}-%{release_num}
cd /home/garrett/tmp
tar -czv --exclude='.git' --exclude='.github' --exclude='.gitignore' -f %{name}-%{version}-%{release_num}.tar.gz   %{name}-%{version}-%{release_num}
cp /home/garrett/tmp/%{name}-%{version}-%{release_num}.tar.gz %{_topdir}/SOURCES
rm -rf /home/garrett/tmp/%{name}-%{version}-%{release_num}.tar.gz
rm -rf /home/garrett/tmp/%{name}-%{version}-%{release_num}
# cd onboard/fedora



 %setup -n %{name}-%{version}-%{release_num}
  rm -rf %{_topdir}/SOURCES/%{name}-%{version}-%{release_num}.tar.gz
# pyproject_buildrequires -t

%build
%pyproject_wheel

%install
%pyproject_install


%files
%{_bindir}/%{name}*
%{_datadir}/man/man1/onboard*
%{_datadir}/applications/%{name}*.desktop
%{python3_sitearch}/Onboard/

%{_datadir}/glib-2.0/schemas/org.onboard.gschema.xml

%doc AUTHORS README.md HACKING
%license COPYING COPYING.BSD3 COPYING.GPL3
%defattr(-,root,root,-)
%{_datadir}/%{name}/
%{_datadir}/sounds/freedesktop/stereo/onboard-key-feedback.oga
%{_datadir}/icons/HighContrast/scalable/apps/onboard.svg
%{_datadir}/icons/hicolor/*/apps/onboard.*
%{_datadir}/dbus-1/services/org.onboard.Onboard.service
%{_datadir}/gnome-shell/extensions/Onboard_Indicator@onboard.org
%{_sysconfdir}/xdg/autostart/onboard-autostart.desktop

%changelog
* Fri Jan 9 2026 Fabian Affolter <fabian@bernewireless.net> 1.4.3-7
- Initial package for Fedora
