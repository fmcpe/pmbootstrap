# Copyright 2023 Oliver Smith
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import logging
import pmb.helpers.run
import pmb.config

def dest_to_suffix(args, destination):
    """
    Convert a destination path to a chroot suffix.
    """
    target_relative = destination.replace(args.work, "")

    if target_relative[0] == "/":
        target_relative = target_relative[1:]
    if not target_relative.startswith("chroot_"):
        raise RuntimeError(f"Unknown proot target: {destination}")

    target_relative = target_relative.split("/")
    return "/" + "/".join(target_relative[1:]), target_relative[0].replace("chroot_", "")


def ismount(folder):
    """
    Ismount() implementation that works for mount --bind.
    Workaround for: https://bugs.python.org/issue29707
    """
    folder = os.path.realpath(os.path.realpath(folder))
    with open("/proc/mounts", "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) >= 2 and words[1] == folder:
                return True
            if words[0] == folder:
                return True
    return False

def proot_listmounts(args, suffix):
    """
    List all bindmounts for a proot call.
    """
    cfg = f"{args.work}/config_proot/proot_{suffix}.cfg"
    if not os.path.exists(cfg):
        return []
    ret = []
    with open(cfg, "r") as handle:
        for line in handle:
            ret.append(line.strip())
    return ret

def proot_bindmount(args, source, destination):
    """
    Store the bindmount in the proot config file, so that it is applied
    to every proot call.
    $WORK/config_proot/proot_<suffix>.cfg

    We do this trickery to avoid manually fixing every usage of pmb.helpers.mount.bind()
    ideally we fix it there....
    """

    target_relative, suffix = dest_to_suffix(args, destination)
    cfg = f"{args.work}/config_proot/proot_{suffix}.cfg"

    logging.verbose(f"{suffix}: proot_bindmount add {source}:{target_relative}")
    if not os.path.exists(os.path.dirname(cfg)):
        pmb.helpers.run.user(args, ["mkdir", "-p", os.path.dirname(cfg)])
    elif target_relative in proot_listmounts(args, suffix):
        return
    with open(cfg, "a") as f:
        f.write(f"{source}:{target_relative}\n")

def proot_umount(args, destination):
    """
    Remove the bindmount from the proot config file.
    """

    target_relative, suffix = dest_to_suffix(args, destination)
    cfg = f"{args.work}/config_proot/proot_{suffix}.cfg"

    logging.verbose(f"{suffix}: proot_bindmount del {target_relative}")
    pmb.helpers.run.user(args, ["sed", "-i", f"/{target_relative}/d", cfg])

def bind(args, source, destination, create_folders=True, umount=False):
    """
    Mount --bind a folder and create necessary directory structure.
    :param umount: when destination is already a mount point, umount it first.
    """

    if pmb.config.rootless:
        if umount:
            proot_umount(args, destination)
        else:
            proot_bindmount(args, source, destination)
        return

    # Check/umount destination
    if ismount(destination):
        if umount:
            umount_all(args, destination)
        else:
            return

    # Check/create folders
    for path in [source, destination]:
        if os.path.exists(path):
            continue
        if create_folders:
            pmb.helpers.run.root(args, ["mkdir", "-p", path])
        else:
            raise RuntimeError("Mount failed, folder does not exist: " +
                               path)

    # Actually mount the folder
    pmb.helpers.run.root(args, ["mount", "--bind", source, destination])

    # Verify that it has worked
    if not ismount(destination):
        raise RuntimeError("Mount failed: " + source + " -> " + destination)


def bind_file(args, source, destination, create_folders=False):
    """
    Mount a file with the --bind option, and create the destination file,
    if necessary.
    """
    # Skip existing mountpoint
    if ismount(destination):
        return

    # Create empty file
    if not os.path.exists(destination):
        if create_folders:
            dir = os.path.dirname(destination)
            if not os.path.isdir(dir):
                pmb.helpers.run.root(args, ["mkdir", "-p", dir])

        pmb.helpers.run.root(args, ["touch", destination])

    # Mount
    pmb.helpers.run.root(args, ["mount", "--bind", source,
                                destination])


def umount_all_list(prefix, source="/proc/mounts"):
    """
    Parses `/proc/mounts` for all folders beginning with a prefix.
    :source: can be changed for testcases
    :returns: a list of folders that need to be umounted
    """
    ret = []
    prefix = os.path.realpath(prefix)
    with open(source, "r") as handle:
        for line in handle:
            words = line.split()
            if len(words) < 2:
                raise RuntimeError("Failed to parse line in " + source + ": " +
                                   line)
            mountpoint = words[1]
            if mountpoint.startswith(prefix):
                # Remove "\040(deleted)" suffix (#545)
                deleted_str = r"\040(deleted)"
                if mountpoint.endswith(deleted_str):
                    mountpoint = mountpoint[:-len(deleted_str)]
                ret.append(mountpoint)
    ret.sort(reverse=True)
    return ret


def umount_all(args, folder):
    """
    Umount all folders that are mounted inside a given folder.
    """
    for mountpoint in umount_all_list(folder):
        pmb.helpers.run.root(args, ["umount", mountpoint])
        if ismount(mountpoint):
            raise RuntimeError("Failed to umount: " + mountpoint)
