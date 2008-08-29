#!/usr/bin/env python
#
# Copyright 2008 Google Inc.  All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#     * Neither the name of Google Inc. nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import imp
import optparse
import os
from os.path import join, dirname, abspath, basename
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time
import utils


VERBOSE = False


# ---------------------------------------------
# --- P r o g r e s s   I n d i c a t o r s ---
# ---------------------------------------------


class ProgressIndicator(object):

  def __init__(self, cases):
    self.cases = cases
    self.succeeded = 0
    self.failed = 0
    self.remaining = len(self.cases)
    self.total = len(self.cases)
    self.failed_tests = [ ]

  def Run(self):
    self.Starting()
    for test in self.cases:
      case = test.case
      self.AboutToRun(case)
      output = case.Run()
      if output.UnexpectedOutput():
        self.failed += 1
        self.failed_tests.append(output)
      else:
        self.succeeded += 1
      self.remaining -= 1
      self.HasRun(output)
    self.Done()
    return self.failed == 0


def EscapeCommand(command):
  parts = []
  for part in command:
    if ' ' in part:
      # Escape spaces.  We may need to escape more characters for this
      # to work properly.
      parts.append('"%s"' % part)
    else:
      parts.append(part)
  return " ".join(parts)


class SimpleProgressIndicator(ProgressIndicator):

  def Starting(self):
    print 'Running %i tests' % len(self.cases)

  def Done(self):
    print
    for failed in self.failed_tests:
      print "=== %s ===" % failed.test.GetLabel()
      print "Command: %s" % EscapeCommand(failed.command)
      if failed.output.stderr:
        print "--- stderr ---"
        print failed.output.stderr.strip()
      if failed.output.stdout:
        print "--- stdout ---"
        print failed.output.stdout.strip()
    if len(self.failed_tests) == 0:
      print "==="
      print "=== All tests succeeded"
      print "==="
    else:
      print
      print "==="
      print "=== %i tests failed" % len(self.failed_tests)
      print "==="


class VerboseProgressIndicator(SimpleProgressIndicator):

  def AboutToRun(self, case):
    print '%s:' % case.GetLabel(),
    sys.stdout.flush()

  def HasRun(self, output):
    if output.UnexpectedOutput():
      print "FAIL"
    else:
      print "pass"


class DotsProgressIndicator(SimpleProgressIndicator):

  def AboutToRun(self, case):
    pass

  def HasRun(self, output):
    total = self.succeeded + self.failed
    if (total > 1) and (total % 50 == 1):
      sys.stdout.write('\n')
    if output.UnexpectedOutput():
      sys.stdout.write('F')
      sys.stdout.flush()
    else:
      sys.stdout.write('.')
      sys.stdout.flush()


class CompactProgressIndicator(ProgressIndicator):

  def __init__(self, cases, templates):
    super(CompactProgressIndicator, self).__init__(cases)
    self.templates = templates
    self.last_status_length = 0
    self.start_time = time.time()

  def Starting(self):
    pass

  def Done(self):
    self.PrintProgress('Done')

  def AboutToRun(self, case):
    self.PrintProgress(case.GetLabel())

  def HasRun(self, output):
    if output.UnexpectedOutput():
      print "\n--- Failed: %s ---" % str(output.test.GetLabel())
      print "Command: %s" % EscapeCommand(output.command)
      stdout = output.output.stdout.strip()
      if len(stdout):
        print self.templates['stdout'] % stdout
      stderr = output.output.stderr.strip()
      if len(stderr):
        print self.templates['stderr'] % stderr

  def Truncate(self, str, length):
    if length and (len(str) > (length - 3)):
      return str[:(length-3)] + "..."
    else:
      return str

  def PrintProgress(self, name):
    self.ClearLine(self.last_status_length)
    elapsed = time.time() - self.start_time
    status = self.templates['status_line'] % {
      'passed': self.succeeded,
      'remaining': (((self.total - self.remaining) * 100) // self.total),
      'failed': self.failed,
      'test': name,
      'mins': int(elapsed) / 60,
      'secs': int(elapsed) % 60
    }
    status = self.Truncate(status, 78)
    self.last_status_length = len(status)
    print status,
    sys.stdout.flush()


class ColorProgressIndicator(CompactProgressIndicator):

  def __init__(self, cases):
    templates = {
      'status_line': "[%(mins)02i:%(secs)02i|\033[34m%%%(remaining) 4d\033[0m|\033[32m+%(passed) 4d\033[0m|\033[31m-%(failed) 4d\033[0m]: %(test)s",
      'stdout': "\033[1m%s\033[0m",
      'stderr': "\033[31m%s\033[0m",
    }
    super(ColorProgressIndicator, self).__init__(cases, templates)

  def ClearLine(self, last_line_length):
    print "\033[1K\r",


class MonochromeProgressIndicator(CompactProgressIndicator):

  def __init__(self, cases):
    templates = {
      'status_line': "[%(mins)02i:%(secs)02i|%%%(remaining) 4d|+%(passed) 4d|-%(failed) 4d]: %(test)s",
      'stdout': '%s',
      'stderr': '%s',
      'clear': lambda last_line_length: ("\r" + (" " * last_line_length) + "\r"),
      'max_length': 78
    }
    super(MonochromeProgressIndicator, self).__init__(cases, templates)

  def ClearLine(self, last_line_length):
    print ("\r" + (" " * last_line_length) + "\r"),


PROGRESS_INDICATORS = {
  'verbose': VerboseProgressIndicator,
  'dots': DotsProgressIndicator,
  'color': ColorProgressIndicator,
  'mono': MonochromeProgressIndicator
}


# -------------------------
# --- F r a m e w o r k ---
# -------------------------


class CommandOutput(object):

  def __init__(self, exit_code, stdout, stderr):
    self.exit_code = exit_code
    self.stdout = stdout
    self.stderr = stderr


class TestCase(object):

  def __init__(self, context, path):
    self.path = path
    self.context = context

  def IsNegative(self):
    return False

  def IsFailureOutput(self, output):
    return output.exit_code != 0

  def Run(self):
    command = self.GetCommand()
    output = Execute(command, self.context, self.context.timeout)
    return TestOutput(self, command, output)


class TestOutput(object):

  def __init__(self, test, command, output):
    self.test = test
    self.command = command
    self.output = output

  def UnexpectedOutput(self):
    if self.HasFailed():
      outcome = FAIL
    else:
      outcome = PASS
    return not outcome in self.test.outcomes

  def HasFailed(self):
    execution_failed = self.test.IsFailureOutput(self.output)
    if self.test.IsNegative():
      return not execution_failed
    else:
      return execution_failed


def KillProcessWithID(pid):
  if platform.system() == 'Windows':
    os.popen('taskkill /T /F /PID %d' % pid)
  else:
    os.kill(pid, signal.SIGTERM)


MAX_SLEEP_TIME = 0.1
INITIAL_SLEEP_TIME = 0.0001
SLEEP_TIME_FACTOR = 1.25


def RunProcess(context, timeout, **args):
  if context.verbose: print "#", " ".join(args['args'])
  process = subprocess.Popen(
    shell = (platform.system() == 'Windows'),
    **args
  )
  # Compute the end time - if the process crosses this limit we
  # consider it timed out.
  if timeout is None: end_time = None
  else: end_time = time.time() + timeout
  timed_out = False
  # Repeatedly check the exit code from the process in a
  # loop and keep track of whether or not it times out.
  exit_code = None
  sleep_time = INITIAL_SLEEP_TIME
  while exit_code is None:
    if (not end_time is None) and (time.time() >= end_time):
      # Kill the process and wait for it to exit.
      KillProcessWithID(process.pid)
      exit_code = process.wait()
      timed_out = True
    else:
      exit_code = process.poll()
      time.sleep(sleep_time)
      sleep_time = sleep_time * SLEEP_TIME_FACTOR
      if sleep_time > MAX_SLEEP_TIME:
        sleep_time = MAX_SLEEP_TIME
  return (process, exit_code, timed_out)


def Execute(args, context, timeout=None):
  (fd_out, outname) = tempfile.mkstemp()
  (fd_err, errname) = tempfile.mkstemp()
  (process, exit_code, timed_out) = RunProcess(
    context,
    timeout,
    args = args,
    stdout = fd_out,
    stderr = fd_err,
  )
  os.close(fd_out)
  os.close(fd_err)
  output = file(outname).read()
  errors = file(errname).read()
  os.unlink(outname)
  os.unlink(errname)
  return CommandOutput(exit_code, output, errors)


def ExecuteNoCapture(args, context, timeout=None):
  (process, exit_code, timed_out) = RunProcess(
    context,
    timeout,
    args = args,
  )
  return CommandOutput(exit_code, "", "")


def CarCdr(path):
  if len(path) == 0:
    return (None, [ ])
  else:
    return (path[0], path[1:])


class TestConfiguration(object):

  def __init__(self, context, root):
    self.context = context
    self.root = root

  def Contains(self, path, file):
    if len(path) > len(file):
      return False
    for i in xrange(len(path)):
      if not path[i].match(file[i]):
        return False
    return True

  def GetTestStatus(self, sections, defs):
    pass


class TestSuite(object):

  def __init__(self, name):
    self.name = name

  def GetName(self):
    return self.name


class TestRepository(TestSuite):

  def __init__(self, path):
    super(TestRepository, self).__init__(basename(path))
    self.path = abspath(path)
    self.is_loaded = False
    self.config = None

  def GetConfiguration(self, context):
    if self.is_loaded:
      return self.config
    self.is_loaded = True
    file = None
    try:
      (file, pathname, description) = imp.find_module('testcfg', [ self.path ])
      module = imp.load_module(self.path, file, pathname, description)
      self.config = module.GetConfiguration(context, self.path)
    finally:
      if file:
        file.close()
    return self.config

  def GetBuildRequirements(self, path, context):
    return self.GetConfiguration(context).GetBuildRequirements()

  def ListTests(self, current_path, path, context, mode):
    return self.GetConfiguration(context).ListTests(current_path, path, mode)

  def GetTestStatus(self, context, sections, defs):
    self.GetConfiguration(context).GetTestStatus(sections, defs)


class LiteralTestSuite(TestSuite):

  def __init__(self, tests):
    super(LiteralTestSuite, self).__init__('root')
    self.tests = tests

  def GetBuildRequirements(self, path, context):
    (name, rest) = CarCdr(path)
    result = [ ]
    for test in self.tests:
      if not name or name.match(test.GetName()):
        result += test.GetBuildRequirements(rest, context)
    return result

  def ListTests(self, current_path, path, context, mode):
    (name, rest) = CarCdr(path)
    result = [ ]
    for test in self.tests:
      test_name = test.GetName()
      if not name or name.match(test_name):
        full_path = current_path + [test_name]
        result += test.ListTests(full_path, path, context, mode)
    return result

  def GetTestStatus(self, context, sections, defs):
    for test in self.tests:
      test.GetTestStatus(context, sections, defs)


PREFIX = {'debug': '_g', 'release': ''}


class Context(object):

  def __init__(self, workspace, buildspace, verbose, vm, timeout):
    self.workspace = workspace
    self.buildspace = buildspace
    self.verbose = verbose
    self.vm_root = vm
    self.timeout = timeout

  def GetVm(self, mode):
    name = self.vm_root + PREFIX[mode]
    if platform.system() == 'Windows':
      return name + '.exe'
    else:
      return name

def RunTestCases(all_cases, progress):
  def DoSkip(case):
    return SKIP in c.outcomes or SLOW in c.outcomes
  cases_to_run = [ c for c in all_cases if not DoSkip(c) ]
  progress = PROGRESS_INDICATORS[progress](cases_to_run)
  return progress.Run()


def BuildRequirements(context, requirements, mode):
  command_line = ['scons', '-Y', context.workspace, 'mode=' + ",".join(mode)] + requirements
  output = ExecuteNoCapture(command_line, context)
  return output.exit_code == 0


# -------------------------------------------
# --- T e s t   C o n f i g u r a t i o n ---
# -------------------------------------------


SKIP = 'skip'
FAIL = 'fail'
PASS = 'pass'
OKAY = 'okay'
TIMEOUT = 'timeout'
CRASH = 'crash'
SLOW = 'slow'


class Expression(object):
  pass


class Constant(Expression):

  def __init__(self, value):
    self.value = value

  def Evaluate(self, env, defs):
    return self.value


class Variable(Expression):

  def __init__(self, name):
    self.name = name

  def GetOutcomes(self, env, defs):
    if self.name in env: return ListSet([env[self.name]])
    else: return Nothing()


class Outcome(Expression):

  def __init__(self, name):
    self.name = name

  def GetOutcomes(self, env, defs):
    if self.name in defs:
      return defs[self.name].GetOutcomes(env, defs)
    else:
      return ListSet([self.name])


class Set(object):
  pass


class ListSet(Set):

  def __init__(self, elms):
    self.elms = elms

  def __str__(self):
    return "ListSet%s" % str(self.elms)

  def Intersect(self, that):
    if not isinstance(that, ListSet):
      return that.Intersect(self)
    return ListSet([ x for x in self.elms if x in that.elms ])

  def Union(self, that):
    if not isinstance(that, ListSet):
      return that.Union(self)
    return ListSet(self.elms + [ x for x in that.elms if x not in self.elms ])

  def IsEmpty(self):
    return len(self.elms) == 0


class Everything(Set):

  def Intersect(self, that):
    return that

  def Union(self, that):
    return self

  def IsEmpty(self):
    return False


class Nothing(Set):

  def Intersect(self, that):
    return self

  def Union(self, that):
    return that

  def IsEmpty(self):
    return True


class Operation(Expression):

  def __init__(self, left, op, right):
    self.left = left
    self.op = op
    self.right = right

  def Evaluate(self, env, defs):
    if self.op == '||' or self.op == ',':
      return self.left.Evaluate(env, defs) or self.right.Evaluate(env, defs)
    elif self.op == 'if':
      return False
    elif self.op == '==':
      inter = self.left.GetOutcomes(env, defs).Intersect(self.right.GetOutcomes(env, defs))
      return not inter.IsEmpty()
    else:
      assert self.op == '&&'
      return self.left.Evaluate(env, defs) and self.right.Evaluate(env, defs)

  def GetOutcomes(self, env, defs):
    if self.op == '||' or self.op == ',':
      return self.left.GetOutcomes(env, defs).Union(self.right.GetOutcomes(env, defs))
    elif self.op == 'if':
      if self.right.Evaluate(env, defs): return self.left.GetOutcomes(env, defs)
      else: return Nothing()
    else:
      assert self.op == '&&'
      return self.left.GetOutcomes(env, defs).Intersect(self.right.GetOutcomes(env, defs))


def IsAlpha(str):
  for char in str:
    if not (char.isalpha() or char.isdigit() or char == '_'):
      return False
  return True


class Tokenizer(object):
  """A simple string tokenizer that chops expressions into variables,
  parens and operators"""

  def __init__(self, expr):
    self.index = 0
    self.expr = expr
    self.length = len(expr)
    self.tokens = None

  def Current(self, length = 1):
    if not self.HasMore(length): return ""
    return self.expr[self.index:self.index+length]

  def HasMore(self, length = 1):
    return self.index < self.length + (length - 1)

  def Advance(self, count = 1):
    self.index = self.index + count

  def AddToken(self, token):
    self.tokens.append(token)

  def SkipSpaces(self):
    while self.HasMore() and self.Current().isspace():
      self.Advance()

  def Tokenize(self):
    self.tokens = [ ]
    while self.HasMore():
      self.SkipSpaces()
      if not self.HasMore():
        return None
      if self.Current() == '(':
        self.AddToken('(')
        self.Advance()
      elif self.Current() == ')':
        self.AddToken(')')
        self.Advance()
      elif self.Current() == '$':
        self.AddToken('$')
        self.Advance()
      elif self.Current() == ',':
        self.AddToken(',')
        self.Advance()
      elif IsAlpha(self.Current()):
        buf = ""
        while self.HasMore() and IsAlpha(self.Current()):
          buf += self.Current()
          self.Advance()
        self.AddToken(buf)
      elif self.Current(2) == '&&':
        self.AddToken('&&')
        self.Advance(2)
      elif self.Current(2) == '||':
        self.AddToken('||')
        self.Advance(2)
      elif self.Current(2) == '==':
        self.AddToken('==')
        self.Advance(2)
      else:
        return None
    return self.tokens


class Scanner(object):
  """A simple scanner that can serve out tokens from a given list"""

  def __init__(self, tokens):
    self.tokens = tokens
    self.length = len(tokens)
    self.index = 0

  def HasMore(self):
    return self.index < self.length

  def Current(self):
    return self.tokens[self.index]

  def Advance(self):
    self.index = self.index + 1


def ParseAtomicExpression(scan):
  if scan.Current() == "true":
    scan.Advance()
    return Constant(True)
  elif scan.Current() == "false":
    scan.Advance()
    return Constant(False)
  elif IsAlpha(scan.Current()):
    name = scan.Current()
    scan.Advance()
    return Outcome(name.lower())
  elif scan.Current() == '$':
    scan.Advance()
    if not IsAlpha(scan.Current()):
      return None
    name = scan.Current()
    scan.Advance()
    return Variable(name.lower())
  elif scan.Current() == '(':
    scan.Advance()
    result = ParseLogicalExpression(scan)
    if (not result) or (scan.Current() != ')'):
      return None
    scan.Advance()
    return result
  else:
    return None


BINARIES = ['==']
def ParseOperatorExpression(scan):
  left = ParseAtomicExpression(scan)
  if not left: return None
  while scan.HasMore() and (scan.Current() in BINARIES):
    op = scan.Current()
    scan.Advance()
    right = ParseOperatorExpression(scan)
    if not right:
      return None
    left = Operation(left, op, right)
  return left


def ParseConditionalExpression(scan):
  left = ParseOperatorExpression(scan)
  if not left: return None
  while scan.HasMore() and (scan.Current() == 'IF'):
    scan.Advance()
    right = ParseOperatorExpression(scan)
    if not right:
      return None
    left=  Operation(left, 'if', right)
  return left


LOGICALS = ["&&", "||", ","]
def ParseLogicalExpression(scan):
  left = ParseConditionalExpression(scan)
  if not left: return None
  while scan.HasMore() and (scan.Current() in LOGICALS):
    op = scan.Current()
    scan.Advance()
    right = ParseConditionalExpression(scan)
    if not right:
      return None
    left = Operation(left, op, right)
  return left


def ParseCondition(expr):
  """Parses a logical expression into an Expression object"""
  tokens = Tokenizer(expr).Tokenize()
  if not tokens:
    print "Malformed expression: '%s'" % expr
    return None
  scan = Scanner(tokens)
  ast = ParseLogicalExpression(scan)
  if not ast:
    print "Malformed expression: '%s'" % expr
    return None
  return ast


class ClassifiedTest(object):

  def __init__(self, case, outcomes):
    self.case = case
    self.outcomes = outcomes


class Configuration(object):
  """The parsed contents of a configuration file"""

  def __init__(self, sections, defs):
    self.sections = sections
    self.defs = defs

  def ClassifyTests(self, cases, env):
    sections = [s for s in self.sections if s.condition.Evaluate(env, self.defs)]
    all_rules = reduce(list.__add__, [s.rules for s in sections], [])
    unused_rules = set(all_rules)
    result = [ ]
    for case in cases:
      matches = [ r for r in all_rules if r.Contains(case.path) ]
      outcomes = set([])
      for rule in matches:
        outcomes = outcomes.union(rule.GetOutcomes(env, self.defs))
        unused_rules.discard(rule)
      if not outcomes:
        outcomes = [PASS]
      case.outcomes = outcomes
      result.append(ClassifiedTest(case, outcomes))
    return (result, list(unused_rules))


class Section(object):
  """A section of the configuration file.  Sections are enabled or
  disabled prior to running the tests, based on their conditions"""

  def __init__(self, condition):
    self.condition = condition
    self.rules = [ ]

  def AddRule(self, rule):
    self.rules.append(rule)


class Rule(object):
  """A single rule that specifies the expected outcome for a single
  test."""

  def __init__(self, raw_path, path, value):
    self.raw_path = raw_path
    self.path = path
    self.value = value

  def GetOutcomes(self, env, defs):
    set = self.value.GetOutcomes(env, defs)
    assert isinstance(set, ListSet)
    return set.elms

  def Contains(self, path):
    if len(self.path) > len(path):
      return False
    for i in xrange(len(self.path)):
      if not self.path[i].match(path[i]):
        return False
    return True


HEADER_PATTERN = re.compile(r'\[([^]]+)\]')
RULE_PATTERN = re.compile(r'\s*([^: ]*)\s*:(.*)')
DEF_PATTERN = re.compile(r'^def\s*(\w+)\s*=(.*)$')
PREFIX_PATTERN = re.compile(r'^\s*prefix\s+([\w\_\.\-\/]+)$')


def ReadConfigurationInto(path, sections, defs):
  current_section = Section(Constant(True))
  sections.append(current_section)
  prefix = []
  for line in utils.ReadLinesFrom(path):
    header_match = HEADER_PATTERN.match(line)
    if header_match:
      condition_str = header_match.group(1).strip()
      condition = ParseCondition(condition_str)
      new_section = Section(condition)
      sections.append(new_section)
      current_section = new_section
      continue
    rule_match = RULE_PATTERN.match(line)
    if rule_match:
      path = prefix + SplitPath(rule_match.group(1).strip())
      value_str = rule_match.group(2).strip()
      value = ParseCondition(value_str)
      if not value:
        return False
      current_section.AddRule(Rule(rule_match.group(1), path, value))
      continue
    def_match = DEF_PATTERN.match(line)
    if def_match:
      name = def_match.group(1).lower()
      value = ParseCondition(def_match.group(2).strip())
      if not value:
        return False
      defs[name] = value
      continue
    prefix_match = PREFIX_PATTERN.match(line)
    if prefix_match:
      prefix = SplitPath(prefix_match.group(1).strip())
      continue
    print "Malformed line: '%s'." % line
    return False
  return True


# ---------------
# --- M a i n ---
# ---------------


def BuildOptions():
  result = optparse.OptionParser()
  result.add_option("-m", "--mode", help="The test modes in which to run (comma-separated)",
      default='release')
  result.add_option("-v", "--verbose", help="Verbose output",
      default=False, action="store_true")
  result.add_option("-p", "--progress",
      help="The style of progress indicator (verbose, dots, color, mono)",
      choices=PROGRESS_INDICATORS.keys(), default="mono")
  result.add_option("--no-build", help="Don't build requirements",
      default=False, action="store_true")
  result.add_option("--report", help="Print a summary of the tests to be run",
      default=False, action="store_true")
  result.add_option("-s", "--suite", help="A test suite",
      default=[], action="append")
  result.add_option("-t", "--timeout", help="Timeout in seconds",
      default=60, type="int")
  return result


def ProcessOptions(options):
  global VERBOSE
  VERBOSE = options.verbose
  options.mode = options.mode.split(',')
  for mode in options.mode:
    if not mode in ['debug', 'release']:
      print "Unknown mode %s" % mode
      return False
  return True


REPORT_TEMPLATE = """\
Total: %(total)i tests
 * %(skipped)4d tests will be skipped
 * %(nocrash)4d tests are expected to be flaky but not crash
 * %(pass)4d tests are expected to pass
 * %(fail_ok)4d tests are expected to fail that we won't fix
 * %(fail)4d tests are expected to fail that we should fix\
"""

def PrintReport(cases):
  def IsFlaky(o):
    return (PASS in o) and (FAIL in o) and (not CRASH in o) and (not OKAY in o)
  def IsFailOk(o):
    return (len(o) == 2) and (FAIL in o) and (OKAY in o)
  unskipped = [c for c in cases if not SKIP in c.outcomes]
  print REPORT_TEMPLATE % {
    'total': len(cases),
    'skipped': len(cases) - len(unskipped),
    'nocrash': len([t for t in unskipped if IsFlaky(t.outcomes)]),
    'pass': len([t for t in unskipped if list(t.outcomes) == [PASS]]),
    'fail_ok': len([t for t in unskipped if IsFailOk(t.outcomes)]),
    'fail': len([t for t in unskipped if list(t.outcomes) == [FAIL]])
  }


class Pattern(object):

  def __init__(self, pattern):
    self.pattern = pattern
    self.compiled = None

  def match(self, str):
    if not self.compiled:
      pattern = "^" + self.pattern.replace('*', '.*') + "$"
      self.compiled = re.compile(pattern)
    return self.compiled.match(str)

  def __str__(self):
    return self.pattern


def SplitPath(s):
  stripped = [ c.strip() for c in s.split('/') ]
  return [ Pattern(s) for s in stripped if len(s) > 0 ]


BUILT_IN_TESTS = ['mjsunit', 'cctest']


def Main():
  parser = BuildOptions()
  (options, args) = parser.parse_args()
  if not ProcessOptions(options):
    parser.print_help()
    return 1

  workspace = abspath(join(dirname(sys.argv[0]), '..'))
  repositories = [TestRepository(join(workspace, 'test', name)) for name in BUILT_IN_TESTS]
  repositories += [TestRepository(a) for a in options.suite]

  root = LiteralTestSuite(repositories)
  if len(args) == 0:
    paths = [SplitPath(t) for t in BUILT_IN_TESTS]
  else:
    paths = [ ]
    for arg in args:
      path = SplitPath(arg)
      paths.append(path)

  # First build the required targets
  buildspace = abspath('.')
  context = Context(workspace, buildspace, VERBOSE,
                    join(buildspace, 'shell'),
                    options.timeout)
  if not options.no_build:
    reqs = [ ]
    for path in paths:
      reqs += root.GetBuildRequirements(path, context)
    reqs = list(set(reqs))
    if len(reqs) > 0:
      if not BuildRequirements(context, reqs, options.mode):
        return 1

  # Get status for tests
  sections = [ ]
  defs = { }
  root.GetTestStatus(context, sections, defs)
  config = Configuration(sections, defs)

  # List the tests
  all_cases = [ ]
  all_unused = [ ]
  for path in paths:
    for mode in options.mode:
      env = {
        'mode': mode
      }
      test_list = root.ListTests([], path, context, mode)
      (cases, unused_rules) = config.ClassifyTests(test_list, env)
      all_cases += cases
      all_unused.append(unused_rules)

#  for rule in unused_rules:
#    print "Rule for '%s' was not used." % '/'.join([str(s) for s in rule.path])

  if options.report:
    PrintReport(all_cases)

  if len(all_cases) == 0:
    print "No tests to run."
    return 0
  else:
    try:
      if RunTestCases(all_cases, options.progress):
        return 0
      else:
        return 1
    except KeyboardInterrupt:
      print "Interrupted"
      return 1


if __name__ == '__main__':
  sys.exit(Main())