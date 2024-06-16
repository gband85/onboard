# Onboard 1.4.2

![onb](https://github.com/dr-ni/onboard/blob/main/onboard.png)

## Description

Onboard is an onscreen keyboard useful for everybody that cannot use a
hardware keyboard; for example TabletPC users or mobility impaired users.
It has been designed with simplicity in mind and can be used right away
without the need of any configuration, as it can read the keyboard layout
from the X server.

Features are:
- Support of custom layouts through the use of xml and svg files.
- Support of custom themes for the appearance through the use of xml files.
- Support of macros to automatically type custom defined texts.
- Support of <modifier>+<mouseclick> combination.
- Toggling mouse buttons to perform right clicks with the left mouse button.
- Control of the hover click feature provided by the system.
- Minimizing the keyboard to the panel, a trayicon, or a floating icon.
- Docking
- XEmbedding
- Support for scanning.

## D-Bus Service:
Once running, Onboard provides a D-Bus service at the bus name
'org.onboard.Onboard', that allows other processes to control 
the keyboard window.

## Interface 'org.onboard.Onboard.Keyboard':

### Show(), method:
- Show the keyboard window
- Return value: None

If auto-show is enabled, the window is locked visible, i.e.
auto-hiding is suspended until Onboard is hidden either manually
or by calling the D-Bus method "Hide". This is the same bahavior as if
Onboard was shown by user action, e.g. by status menu, floating icon
or by starting a second instance.

Example:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Show

### Hide(), method
- Hide the keyboard window
- Return value: None

Example:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.Hide

### ToggleVisible(), method
- Show the keyboard window if it was hidden, else hide it.
- Return value: None

Example:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.onboard.Onboard.Keyboard.ToggleVisible

### Visible, Boolean property, read-only
- True if the window is currently visible, False otherwise.
- Signal: org.freedesktop.DBus.Properties.PropertiesChanged

Example:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.freedesktop.DBus.Properties.Get string:"org.onboard.Onboard.Keyboard" string:"Visible"

### AutoShowPaused, Boolean property, read-write
- True pauses auto-show and hides the keyboard.
- False resumes auto-show.

You are free to write to this property, e.g. when entering/leaving 
tablet mode of a convertible device (and Onboard's built-in detection
isn't sufficient).
This property is not persistent. It will be reset to 'false' each time
Onboard is restarted.

### Signal: org.freedesktop.DBus.Properties.PropertiesChanged

Example, reading:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.freedesktop.DBus.Properties.Get string:"org.onboard.Onboard.Keyboard" string:"AutoShowPaused"

Example, writing:

    dbus-send --type=method_call --print-reply --dest=org.onboard.Onboard /org/onboard/Onboard/Keyboard org.freedesktop.DBus.Properties.Set string:"org.onboard.Onboard.Keyboard" string:"AutoShowPaused" variant:boolean:"true"

## Getting Onboard:
Actual sources can be found at https://github.com/dr-ni/onboard

The parent project seems to be not maintained anymore: 

    https://launchpad.net/onboard

An old PPA with downloads for old Ubuntu-releases can also be found here:

    https://launchpad.net/~onboard/+archive/ubuntu/stable

The old source code is in a bazaar repository at the same site. It can be checked out with:

    bzr branch lp:onboard

## Building from Source:
Find below short instructions on how to build Onboard straight from this
github repository. If you have improvements to share, get errors or run
into other problems, please let us know. Build instructions for
new distributions are always welcome too.

## Arch Linux:
        pacman -S base-devel git python-distutils-extra dconf gtk3 \
        libcanberra hunspell python-gobject gsettings-desktop-schemas \
        iso-codes python-cairo librsvg python-dbus dbus-glib

        git clone https://github.com/dr-ni/onboard
        cd onboard
        ./setup.py build
        tools/install_gsettings_schema

        # At this point you should be able to start Onboard
        # from the project directory with
        ./onboard

        # If everything works as expected, install with
        sudo ./setup.py install

        # And if necessary, uninstall with
        sudo ./setup.py install --record files.txt
        sudo xargs -a files.txt --delimiter='\n' rm -v
        sudo rm -rf /usr/local/share/onboard

## Mageia 4:
        urpmi git gcc-c++ lib64zlib-devel python3-distutils-extra \
        libgtk+3.0-devel libxtst-devel libxkbfile-devel libdconf-devel \
        libhunspell-devel libcanberra-devel libpython3-devel intltool

        # more or less optional, but recommended for full functionality
        urpmi mousetweaks lib64atspi-gir2.0 at-spi2-core-qt \
        python3-dbus qtatspi-plugin

        git clone https://github.com/dr-ni/onboard
        cd onboard
        ./setup.py build
        tools/install_gsettings_schema

        # At this point you should be able to start Onboard
        # from the project directory with
        ./onboard

        # If everything works as expected, install with
        su
        ./setup.py install

        # And if necessary, uninstall with
        su
        ./setup.py install --record files.txt
        sudo xargs -a files.txt --delimiter='\n' rm -v
        sudo rm -rf /usr/local/share/onboard

## Ubuntu 14.04:
        sudo apt-get git build-dep onboard
        sudo apt-get install devscripts
        git clone https://github.com/dr-ni/onboard
        cd onboard

        # build packages
        debuild binary

        # install packages
        sudo dpkg -i ../onboard*.deb

## Ubuntu 24.04:
        sudo apt install git build-essential fakeroot
        sudo apt install dh-python python3-distutils-extra devscripts pkg-config libhunspell-dev
        sudo apt install libgtk-3-dev libxtst-dev libxkbfile-dev libdconf-dev libcanberra-dev
        mkdir onboard_build
        cd onboard_build
        git clone https://github.com/dr-ni/onboard.git

        # build
        cd onboard
        fakeroot debian/rules clean
        fakeroot debian/rules build
        export DEB_HOST_ARCH=$(sed -i 's/oldString/new String/g'); fakeroot debian/rules binary

        # install packages
        cd ..
        sudo dpkg -i onboard_1.4.2*.deb 
        sudo dpkg -i onboard-common_1.4.2_all.deb 
        sudo dpkg -i onboard-data_1.4.2_all.deb
        sudo dpkg -i gnome-shell-extension-onboard_1.4.2_all.deb

## Homepage:
https://github.com/dr-ni/onboard

## Reporting Bugs:
https://github.com/dr-ni/onboard/issues

## License:
This program is released under the terms of the GNU General Public License. Please see the file COPYING for details.
