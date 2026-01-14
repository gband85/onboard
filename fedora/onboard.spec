Name:               onboard

Version:            1.4.3
%global             major_version       1.4
%global             release_num         9

Release:            %{release_num}%{?dist}
Summary:            On-screen keyboard for TabletPC and mobility impaired users (Xorg only)

# The entire source code is GPLv3 apart from translation strings and
# /gnome/Onboard_Indicator@onboard.org/convenience.js which are both BSD-3-clause
License:            GPLv3 and BSD
URL:                https://github.com/onboard-osk/onboard/
Source:             %{name}-%{version}-%{release_num}.tar.gz

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

mkdir -p $HOME/tmp
cp -r $HOME/source/repos/%{name} $HOME/tmp/%{name}-%{version}-%{release_num}
cd $HOME/tmp
tar -czv --exclude='.git' --exclude='.github' --exclude='.gitignore' -f %{name}-%{version}-%{release_num}.tar.gz   %{name}-%{version}-%{release_num}
cp $HOME/tmp/%{name}-%{version}-%{release_num}.tar.gz %{_topdir}/SOURCES
rm -rf $HOME/tmp/%{name}-%{version}-%{release_num}.tar.gz
rm -rf $HOME/tmp/%{name}-%{version}-%{release_num}
# cd onboard/fedora

 %setup -n %{name}-%{version}-%{release_num}
  rm -rf %{_topdir}/SOURCES/%{name}-%{version}-%{release_num}.tar.gz
# pyproject_buildrequires -t

%build
%pyproject_wheel

%install
%pyproject_install

# Remove icons for Ubuntu
rm %{buildroot}%{_datadir}/icons/ubuntu* -rf

%package common
Summary: Common files for Onboard
BuildArch: noarch
Requires: onboard

%description common
Simple On-screen Keyboard (common files)
On-screen Keyboard with macros, easy layout creation and word suggestion.

This package ships the architecture independent files of the onboard
on-screen keyboard.

%package data
Summary: Data for Onboard
BuildArch: noarch
Requires: onboard

%description data
Language model files for the word suggestion feature of Onboard
On-screen Keyboard with macros, easy layout creation and word suggestion.
 
This package installs default language model files for various languages.
The word suggestion feature of Onboard uses these files (and if available
also custom user language model files) to compute the word completion
suggestions and the word prediction suggestions.

%package gnome-shell-extension
Summary: Data for Onboard
BuildArch: noarch
Requires: onboard

%description gnome-shell-extension
GNOME Shell extension for the on-screen keyboard Onboard
This package hides the official GNOME3 keyboard and provides an icon to
show/hide Onboard. It is only an initial extension that does not show
Onboard for activities and passwords, yet.

%files
%{_bindir}/%{name}*
%{_datadir}/man/man1/onboard*
%{_datadir}/applications/%{name}*.desktop
%{python3_sitearch}/Onboard/
%{python3_sitearch}/onboard-1.4.3.post9.dist-info
%{_datadir}/glib-2.0/schemas/org.onboard.gschema.xml
%{_datadir}/icons/HighContrast/symbolic/apps/onboard.svg
%{_datadir}/icons/hicolor/*/apps/onboard*
%{_datadir}/glib-2.0/schemas/org.gnome.shell.extensions.onboard-indicator.gschema.xml
%{_datadir}/glib-2.0/schemas/gschemas.compiled
%{python3_sitearch}/%{_sysconfdir}/xdg/autostart/onboard-autostart.desktop

%files data
%{_datadir}/%{name}/models
%{_datadir}/%{name}/emojione

%files common
%{_datadir}/doc/%{name}
%license LICENSE LICENSE.BSD3 LICENSE.GPL3
%{_datadir}/dbus-1/services/org.onboard.Onboard.service
%{_datadir}/help/C/onboard/*
%{_datadir}/locale/*/LC_MESSAGES/onboard.mo
%{_datadir}/sounds/freedesktop/stereo/onboard-key-feedback.oga
%{_datadir}/%{name}/layouts
%{_datadir}/%{name}/scripts
%{_datadir}/%{name}/themes
%{_datadir}/%{name}/layoutstrings.py
%{_datadir}/%{name}/__pycache__/layoutstrings.cpython-*.pyc
%{_datadir}/%{name}/*.ui
%{_datadir}/%{name}/tools


%files gnome-shell-extension
%{_datadir}/gnome-shell/extensions/Onboard_Indicator@onboard.org





%changelog
* Fri Jan 9 2026 Fabian Affolter <fabian@bernewireless.net> 1.4.3-7
- Initial package for Fedora
