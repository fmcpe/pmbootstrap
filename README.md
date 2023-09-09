# pmbootstrap

Sophisticated chroot/build/flash tool to develop and install
[postmarketOS](https://postmarketos.org).

## Development

pmbootstrap is being developed on SourceHut
([what](https://postmarketos.org/blog/2022/07/25/considering-sourcehut/)):

<https://git.sr.ht/~postmarketos/pmbootstrap>

Send patches via mail or web UI to
[pmbootstrap-devel](https://lists.sr.ht/~postmarketos/pmbootstrap-devel)
([subscribe](mailto:~postmarketos/pmbootstrap-devel+subscribe@lists.sr.ht)):

```txt
~postmarketos/pmbootstrap-devel@lists.sr.ht
```

You can set the default values for sending email in the git checkout

```sh
git config sendemail.to "~postmarketos/pmbootstrap-devel@lists.sr.ht"
git config format.subjectPrefix "PATCH pmbootstrap"
```

Run CI scripts locally with:

```sh
pmbootstrap ci
```

Run a single test file:

```sh
pytest -vv ./test/test_keys.py
```

## Issues

Issues are being tracked
[here](https://gitlab.com/postmarketOS/pmbootstrap/-/issues).

## Requirements

* Linux distribution on the host system (`x86`, `x86_64`, `aarch64` or `armv7`)
  * [Windows subsystem for Linux (WSL)](https://en.wikipedia.org/wiki/Windows_Subsystem_for_Linux)
    does **not** work! Please use [VirtualBox](https://www.virtualbox.org/) instead.
  * [Linux kernel 3.17 or higher](https://postmarketos.org/oldkernel)
* Python 3.7+
* OpenSSL
* git
* ps
* tar

## Usage Examples

Please refer to the [postmarketOS wiki](https://wiki.postmarketos.org) for
in-depth coverage of topics such as
[porting to a new device](https://wiki.postmarketos.org/wiki/Porting_to_a_new_device)
or [installation](https://wiki.postmarketos.org/wiki/Installation_guide). The
help output (`pmbootstrap -h`) has detailed usage instructions for every
command. Read on for some generic examples of what can be done with
`pmbootstrap`.

### Installing pmbootstrap

<https://wiki.postmarketos.org/wiki/Installing_pmbootstrap>

### Basics

Initial setup:

```sh
pmbootstrap init
```

Run this in a second window to see all shell commands that get executed:

```sh
pmbootstrap log
```

Quick health check and config overview:

```sh
pmbootstrap status
```

### Packages

All source packages are in the [pmaports package
repository](https://gitlab.com/postmarketOS/pmaports), pmbootstrap will
automatically clone this during init. You can quickly navigate to the pmaports
git repository with

```sh
cd $(pmbootstrap config aports)
```

Build `main/hello-world`:

```sh
pmbootstrap build hello-world
```

Cross-compile to `armhf`:

```sh
pmbootstrap build --arch=armhf hello-world
```

Build with source code from local folder:

```sh
pmbootstrap build linux-postmarketos-mainline --src=~/code/linux
```

Update checksums:

```sh
pmbootstrap checksum hello-world
```

Generate a template for a new package:

```sh
pmbootstrap newapkbuild "https://gitlab.com/postmarketOS/osk-sdl/-/archive/0.52/osk-sdl-0.52.tar.bz2"
```

#### Default architecture

Packages will be compiled for the architecture of the device running
pmbootstrap by default. For example, if your `x86_64` PC runs pmbootstrap, it
would build a package for `x86_64` with this command:

```sh
pmbootstrap build hello-world
```

If you would rather build for the target device selected in `pmbootstrap init`
by default, then use the `build_default_device_arch` option:

```sh
pmbootstrap config build_default_device_arch True
```

If your target device is `pine64-pinephone` for example, pmbootstrap will now
build this package for `aarch64`:

```sh
pmbootstrap build hello-world
```

### Chroots

Enter the `armhf` building chroot:

```sh
pmbootstrap chroot -b armhf
```

Run a command inside a chroot:

```sh
pmbootstrap chroot -- echo test
```

Safely delete all chroots:

```sh
pmbootstrap zap
```

### Device Porting Assistance

Analyze Android
[`boot.img`](https://wiki.postmarketos.org/wiki/Glossary#boot.img) files (also
works with recovery OS images like TWRP):

```sh
pmbootstrap bootimg_analyze ~/Downloads/twrp-3.2.1-0-fp2.img
```

Check kernel configs:

```sh
pmbootstrap kconfig check
```

Edit a kernel config:

```sh
pmbootstrap kconfig edit --arch=armhf postmarketos-mainline
```

### Root File System

Build the rootfs:

```sh
pmbootstrap install
```

Build the rootfs with full disk encryption:

```sh
pmbootstrap install --fde
```

Update existing installation on SD card:

```sh
pmbootstrap install --sdcard=/dev/mmcblk0 --rsync
```

Run the image in QEMU:

```sh
pmbootstrap qemu --image-size=1G
```

Flash to the device:

```sh
pmbootstrap flasher flash_kernel
pmbootstrap flasher flash_rootfs --partition=userdata
```

Export the rootfs, kernel, initramfs, `boot.img` etc.:

```sh
pmbootstrap export
```

Extract the initramfs

```sh
pmbootstrap initfs extract
```

Build and flash Android recovery zip:

```sh
pmbootstrap install --android-recovery-zip
pmbootstrap flasher --method=adb sideload
```

### Repository Maintenance

List pmaports that don't have a binary package:

```sh
pmbootstrap repo_missing --arch=armhf --overview
```

Increase the `pkgrel` for each aport where the binary package has outdated
dependencies (e.g. after soname bumps):

```sh
pmbootstrap pkgrel_bump --auto
```

Generate cross-compiler aports based on the latest version from Alpine's
aports:

```sh
pmbootstrap aportgen binutils-armhf gcc-armhf
```

Manually rebuild package index:

```sh
pmbootstrap index
```

Delete local binary packages without existing aport of same version:

```sh
pmbootstrap zap -m
```

### Debugging

Use `-v` on any action to get verbose logging:

```sh
pmbootstrap -v build hello-world
```

Parse a single deviceinfo and return it as JSON:

```sh
pmbootstrap deviceinfo_parse pine64-pinephone
```

Parse a single APKBUILD and return it as JSON:

```sh
pmbootstrap apkbuild_parse hello-world
```

Parse a package from an APKINDEX and return it as JSON:

```sh
pmbootstrap apkindex_parse $WORK/cache_apk_x86_64/APKINDEX.8b865e19.tar.gz hello-world
```

`ccache` statistics:

```sh
pmbootstrap stats --arch=armhf
```

### Use alternative sudo

pmbootstrap supports `doas` and `sudo`.
If multiple sudo implementations are installed, pmbootstrap will use `doas`.
You can set the `PMB_SUDO` environmental variable to define the sudo
implementation you want to use.

### Select SSH keys to include and make authorized in new images

If the config file option `ssh_keys` is set to `True` (it defaults to `False`),
then all files matching the glob `~/.ssh/id_*.pub` will be placed in
`~/.ssh/authorized_keys` in the user's home directory in newly-built images.

Sometimes, for example if you have a large number of SSH keys, you may wish to
select a different set of public keys to include in an image. To do this, set
the `ssh_key_glob` configuration parameter in the pmbootstrap config file to a
string containing a glob that is to match the file or files you wish to
include.

For example, a `~/.config/pmbootstrap.cfg` may contain:

```ini
[pmbootstrap]
# ...
ssh_keys = True
ssh_key_glob = ~/.ssh/postmarketos-dev.pub
# ...
```

## License

[GPLv3](LICENSE)
