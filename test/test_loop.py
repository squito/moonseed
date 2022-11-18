#!/usr/bin/env python

## Makes it easy to run tests in a loop
## Just a small bit of automation around something like
##      ls quanta_cache.py test/test_quanta_cache.py | entr -r python -m pytest test/test_quanta_cache.py
## but that is just complex enough I would never remember


import argparse
import os
import subprocess
import sys
import tempfile


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Run your tests in a loop forever, like sbt's ~test-only")
  parser.add_argument("--test", required=True, help="code to test")
  parser.add_argument("-v", "--verbose", action='store_true', help="verbose test output")
  parser.add_argument("--watch-extras", help="any extra files to watch", action="append")
  ## TODO add option for `git ls-files`: https://jvns.ca/blog/2020/06/28/entr/
  args = parser.parse_args()

  test_file = "test/test_" + args.test

  files_to_watch = [args.test, test_file]
  if args.watch_extras is not None:
    files_to_watch = files_to_watch + args.watch_extras
  
  ls_p = subprocess.Popen(["ls"] + files_to_watch, stdout=subprocess.PIPE, bufsize=0)
  cmd = ["entr", "-r", "python", "-m", "pytest", test_file]
  if args.verbose:
    cmd.append("-v")
  entr_p = subprocess.Popen(cmd, stdin=ls_p.stdout, bufsize=0)
  try:
    entr_p.wait()
  except KeyboardInterrupt:
    sys.exit(entr_p.returncode)
