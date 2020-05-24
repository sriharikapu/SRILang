#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import sys

from srilang.cli import srilang_compile, srilang_lll, srilang_serve

if __name__ == "__main__":

    allowed_subcommands = ("--srilang-compile", "--srilang-lll", "--srilang-serve")

    if not len(sys.argv) > 1 or sys.argv[1] not in allowed_subcommands:
        # default (no args, no switch in first arg): run srilang_compile
        srilang_compile._parse_cli_args()
    else:
        # pop switch and forward args to subcommand
        subcommand = sys.argv.pop(1)
        if subcommand == "--srilang-serve":
            srilang_serve._parse_cli_args()
        elif subcommand == "--srilang-lll":
            srilang_lll._parse_cli_args()
        else:
            srilang_compile._parse_cli_args()
