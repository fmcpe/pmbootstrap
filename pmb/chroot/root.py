# Copyright 2023 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import shutil

import pmb.config
import pmb.chroot
import pmb.chroot.binfmt
import pmb.helpers.run
import pmb.helpers.run_core
from pmb.helpers.run import which

def make_proot_cmd(args, suffix="native", working_dir="/"):
    arch = pmb.parse.arch.from_chroot_suffix(args, suffix)
    arch_qemu = pmb.parse.arch.alpine_to_qemu(arch)
    cmd_chroot = [which("proot"), "-q", f"qemu-{arch_qemu}-static", "-w", working_dir]
    bindmounts = pmb.helpers.mount.proot_listmounts(args, suffix)
    # FIXME: SECURITY!!!! proot will make the host /dev /sys /proc /tmp and /run
    # available to the chroot with -S
    for bindmount in bindmounts:
        cmd_chroot += ["-b", bindmount]
    cmd_chroot += ["-S", f"{args.work}/chroot_{suffix}"]

    return cmd_chroot

def root(args, cmd, suffix="native", working_dir="/", output="log",
         output_return=False, check=None, env={}, auto_init=True,
         disable_timeout=False, exists_check=True):
    """
    Run a command inside a chroot as root.

    :param env: dict of environment variables to be passed to the command, e.g.
                {"JOBS": "5"}
    :param auto_init: automatically initialize the chroot

    See pmb.helpers.run_core.core() for a detailed description of all other
    arguments and the return value.
    """
    # Initialize chroot
    chroot_path = f"{args.work}/chroot_{suffix}"
    if exists_check:
        if not auto_init and not os.path.islink(f"{chroot_path}/bin/sh"):
            raise RuntimeError(f"Chroot does not exist: {chroot_path}")
        if auto_init:
            pmb.chroot.init(args, suffix)

    # Readable log message (without all the escaping)
    msg = f"({suffix}) % "
    for key, value in env.items():
        msg += f"{key}={value} "
    if working_dir != "/":
        msg += f"cd {working_dir}; "
    msg += " ".join(cmd)

    # Merge env with defaults into env_all
    env_all = {"CHARSET": "UTF-8",
               "HISTFILE": "~/.ash_history",
               "HOME": "/root",
               "LANG": "UTF-8",
               "PATH": pmb.config.chroot_path,
               "PYTHONUNBUFFERED": "1",
               "SHELL": "/bin/ash",
               "TERM": "xterm"}
    for key, value in env.items():
        env_all[key] = value

    # Preserve proxy environment variables
    for var in ["FTP_PROXY", "ftp_proxy", "HTTP_PROXY", "http_proxy",
                "HTTPS_PROXY", "https_proxy", "HTTP_PROXY_AUTH"]:
        if var in os.environ:
            env_all[var] = os.environ[var]

    # Build the command in steps and run it, e.g.:
    # cmd: ["echo", "test"]
    # cmd_chroot: ["/sbin/chroot", "/..._native", "/bin/sh", "-c", "echo test"]
    # cmd_sudo: ["sudo", "env", "-i", "sh", "-c", "PATH=... /sbin/chroot ..."]
    cmd_chroot = []
    if pmb.config.rootless:
        cmd_chroot = make_proot_cmd(args, suffix, working_dir) + cmd# + ["/bin/sh_host", "-c",
                    #pmb.helpers.run.flat_cmd(cmd)]
        cmd_chroot = ["env", "-i", which("sh"), "-c",
                    pmb.helpers.run.flat_cmd(cmd_chroot, env=env_all)]
    else:
        cmd_chroot += [which("chroot"), chroot_path, "/bin/sh", "-c",
                    pmb.helpers.run.flat_cmd(cmd)]
        cmd_chroot = [pmb.config.sudo, "env", "-i", which("sh"), "-c",
                   pmb.helpers.run.flat_cmd(cmd_chroot, env=env_all)]

    return pmb.helpers.run_core.core(args, msg, cmd_chroot, None, output,
                                     output_return, check, True,
                                     disable_timeout)
