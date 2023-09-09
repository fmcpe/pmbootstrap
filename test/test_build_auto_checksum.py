# Copyright 2023 Caleb Connolly
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import pytest
import sys

import pmb_test
import pmb_test.const
import pmb.parse._apkbuild


@pytest.fixture
def args(tmpdir, request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "init"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(pmb.helpers.logging.logfd.close)
    return args

testfiles = ["APKBUILD.inline", "APKBUILD.multiline"]

@pytest.mark.parametrize('apkbuild', testfiles)
def test_auto_checksum_inline(args, tmpdir, apkbuild):
    """
    Validate that the checksums are correctly calculated for inline sources
    """
    testdata = pmb_test.const.testdata
    pmaportdir = os.path.join(testdata, "apkbuild/checksum")
    path = os.path.join(pmaportdir, apkbuild)
    apkbuild = pmb.parse.apkbuild(path, check_pkgname=False)

    assert apkbuild["sha512sums"] == {
            "main.c": "d06f00d",
            "Makefile": "baddeed",
            "invalid-url": "d00d00d",
    }
    
    path_tmp = os.path.join(tmpdir, "APKBUILD")

    # Copy APKBUILD and the two files
    pmb.helpers.run.user(args, ["cp", "-r", path,
                                path_tmp])
    pmb.helpers.run.user(args, ["cp", "-r", os.path.join(pmaportdir, "main.c"),
                                os.path.join(tmpdir, "main.c")])
    pmb.helpers.run.user(args, ["cp", "-r", os.path.join(pmaportdir, "Makefile"),
                                os.path.join(tmpdir, "Makefile")])

    # make tmpdir, copy apkbuild, run checksum fix
    # validate against expected checksums
    pmb.build.checksum.fix_local(args, "hello-world", path_tmp)
    
    pmb.helpers.run.user(args, ["cat", os.path.join(tmpdir, "Makefile")])

    apkbuild = pmb.parse.apkbuild(path_tmp, check_pkgname=False)
    assert apkbuild["sha512sums"] == {
            "main.c": "1644d90ce0e74edde408a92c6d1236123f66ad833af9147a3ba402e878987881"
                      "d34c53f856c4b2fa5fb23b5f6117789720dd1c42fdfb115c2981b74d29788867",
            "Makefile": "d85ca0ac72420eadd338f14d9d13de985cd2ace27df6d49d3a3a7c5751f4ea8d"
                        "4425714a01db741af0cb483fc4471ab92b079563b9d5af0191b7850d35290a52",
            "invalid-url": "d00d00d",
    }
