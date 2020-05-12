# Copyright 2020 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later
import glob
import os
import pmb.helpers.run
import pmb.aportgen.core
import pmb.parse.apkindex
import pmb.chroot.apk
import pmb.chroot.apk_static


def generate(args, pkgname):
    # Install musl in chroot to get verified apks
    arch = pkgname.split("-")[1]
    pmb.chroot.apk.install(args, ["musl-dev"], "buildroot_" + arch)

    # Parse musl version from APKINDEX
    package_data = pmb.parse.apkindex.package(args, "musl")
    version = package_data["version"]
    pkgver = version.split("-r")[0]
    pkgrel = version.split("-r")[1]

    # Architectures to build this package for
    arches = list(pmb.config.build_device_architectures)
    arches.remove(arch)

    # Copy the apk files to the distfiles cache
    for subpkgname in ["musl", "musl-dev"]:
        pattern = (args.work + "/cache_apk_" + arch + "/" + subpkgname +
                   "-" + version + ".*.apk")
        glob_result = glob.glob(pattern)
        if not len(glob_result):
            raise RuntimeError("Could not find aport " + pattern + "!"
                               " Update your aports_upstream git repo"
                               " to the latest version, delete your http cache"
                               " (pmbootstrap zap -hc) and try again.")
        path = glob_result[0]
        path_target = (args.work + "/cache_distfiles/" + subpkgname + "-" +
                       version + "-" + arch + ".apk")
        if not os.path.exists(path_target):
            pmb.helpers.run.root(args, ["cp", path, path_target])

    # Hash the distfiles
    hashes = pmb.chroot.user(args, ["sha512sum",
                                    "musl-" + version + "-" + arch + ".apk",
                                    "musl-dev-" + version + "-" + arch + ".apk"], "buildroot_" + arch,
                             "/var/cache/distfiles", output_return=True)

    # Write the APKBUILD
    pmb.helpers.run.user(args, ["mkdir", "-p", args.work + "/aportgen"])
    with open(args.work + "/aportgen/APKBUILD", "w", encoding="utf-8") as handle:
        # Variables
        apkbuild = f"""\
            # Automatically generated aport, do not edit!
            # Generator: pmbootstrap aportgen {pkgname}

            pkgname="{pkgname}"
            pkgver="{pkgver}"
            pkgrel={pkgrel}
            arch="{" ".join(arches)}"
            subpackages="musl-dev-{arch}:package_dev"

            _arch="{arch}"
            _mirror="{args.mirror_alpine}"

            url="https://musl-libc.org"
            license="MIT"
            options="!check !strip"
            pkgdesc="the musl library (lib c) implementation for $_arch"

            _target="$(arch_to_hostspec $_arch)"

            source="
                musl-$pkgver-r$pkgrel-$_arch.apk::$_mirror/edge/main/$_arch/musl-$pkgver-r$pkgrel.apk
                musl-dev-$pkgver-r$pkgrel-$_arch.apk::$_mirror/edge/main/$_arch/musl-dev-$pkgver-r$pkgrel.apk
            "

            package() {{
                mkdir -p "$pkgdir/usr/$_target"
                cd "$pkgdir/usr/$_target"
                # Use 'busybox tar' to avoid 'tar: Child returned status 141'
                # on some machines (builds.sr.ht, gitlab-ci). See pmaports#26.
                busybox tar -xf $srcdir/musl-$pkgver-r$pkgrel-$_arch.apk
                rm .PKGINFO .SIGN.*
            }}
            package_dev() {{
                mkdir -p "$subpkgdir/usr/$_target"
                cd "$subpkgdir/usr/$_target"
                # Use 'busybox tar' to avoid 'tar: Child returned status 141'
                # on some machines (builds.sr.ht, gitlab-ci). See pmaports#26.
                busybox tar -xf $srcdir/musl-dev-$pkgver-r$pkgrel-$_arch.apk
                rm .PKGINFO .SIGN.*

                # symlink everything from /usr/$_target/usr/* to /usr/$_target/*
                # so the cross-compiler gcc does not fail to build.
                for _dir in include lib; do
                    mkdir -p "$subpkgdir/usr/$_target/$_dir"
                    cd "$subpkgdir/usr/$_target/usr/$_dir"
                    for i in *; do
                        cd "$subpkgdir/usr/$_target/$_dir"
                        ln -s /usr/$_target/usr/$_dir/$i $i
                    done
                done
            }}
        """
        for line in apkbuild.split("\n"):
            handle.write(line[12:] + "\n")

        # Hashes
        handle.write("sha512sums=\"" + hashes.rstrip() + "\"\n")
