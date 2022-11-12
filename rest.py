#
# Some helper stuff.
#
from __future__ import print_function

from builtins import map
from future.utils import iteritems

import argparse
import base64
import codecs
import copy
import errno
import getopt
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import termios
import textwrap
import urllib

try:
  from httplib import HTTPConnection, HTTPSConnection, HTTPException, NO_CONTENT
except:
  from http import HTTPStatus
  NO_CONTENT = HTTPStatus.NO_CONTENT
  from http.client import HTTPConnection, HTTPSConnection, HTTPException
  raw_input = input
  unicode = str

TOKENS_FILE = os.path.join(os.environ['HOME'], '.jira.auth.tokens')

# Each rule is described at https://lintlyci.github.io/Flake8Rules
ST_CHECKSTYLE_IGNORED_RULES_COMMON='E111,E114,E121,E126,E127,E128,E129,E201,E202,E303,E501,E722'

# Rules prefixed with F is Flake8 rules not known by autopep8
ST_CHECKSTYLE_IGNORED_RULES_CHECKER = ST_CHECKSTYLE_IGNORED_RULES_COMMON + ',F401,F403,F405,F811,F821,F841'

# The W602 is 'Deprecated form of raising exception' regarding that rule the autopep8 made
# an error (so better to skip it)
ST_CHECKSTYLE_IGNORED_RULES_AUTOFORMATTER = ST_CHECKSTYLE_IGNORED_RULES_COMMON + ',W602'

class RESTClient(object):

  def __init__(self, name, host, base_uri='', ssl=False, is_json=True, headers=None,
      auth_type='Basic', port=None, wrap_json_objects=True):
    self._name = name
    self._host = host
    self._base_uri = base_uri
    self._ssl = ssl
    self._auth_type = auth_type
    self._port = port
    self._wrap_json_objects = wrap_json_objects
    self._user = None
    self._conn = None
    if is_json:
      self._headers = {
        'Accept' : 'application/json',
        'Content-Type' : 'application/json',
      }
    else:
      self._headers = {
        'Content-Type' : 'application/x-www-form-urlencoded',
      }
    if headers:
      self._headers.update(headers)


  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.close()

  def _getuser(self):
    return raw_input('Username for "%s" @ %s: ' % (self._name, self._host))

  def _getpass(self, prompt="Password: "):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[3] = new[3] & ~termios.ECHO          # lflags
    try:
      termios.tcsetattr(fd, termios.TCSADRAIN, new)
      passwd = raw_input(prompt)
    finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return passwd

  def _need_token(self):
    return True

  def _get_token(self):
    """
    Returns the token for the current app / host. If the token is not in the new file, try to
    read the old location (that did not do per-host tokens).
    """
    if not self._need_token():
      return None

    try:
      tokens = json.load(open(TOKENS_FILE, "r"))
      token = tokens[self._name][self._host]
      if isinstance(token, str) or isinstance(token, unicode):
        # Ask for user name since some clients may need that.
        user = self._getuser()
        if not user:
          raise ValueError("No username specified.")
        token = { 'user' : user, 'token' : token }
        self._save_token(token)
    except:
      token = self._request_auth_info()
      self._save_token(token)

    return token

  def _save_token(self, token):
    if not os.path.isfile(TOKENS_FILE):
      open(TOKENS_FILE, 'w').close()
      os.chmod(TOKENS_FILE, 0o600)
      tokens = { }
    else:
      tokens = json.load(open(TOKENS_FILE, "r"))
    app = tokens.get(self._name, {})
    app[self._host] = token
    tokens[self._name] = app

    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(TOKENS_FILE))
    os.close(fd)
    try:
      json.dump(tokens, open(tmp, 'w'), indent=2)
      os.rename(tmp, TOKENS_FILE)
    except:
      os.unlink(tmp)

  def _request_auth_info(self):
    """
    Interactively asks the user for credentials. The default implementation asks for a username
    and password, and stores them as a basic auth token in the given path.
    """
    user = self._getuser()
    passwd = self._getpass()
    return {
      'user' : user,
      'token' : codecs.decode(base64.b64encode(codecs.encode('%s:%s' % (user, passwd)))),
    }

  def _auth_headers(self, creds):
    """
    Headers to add to a request with auth info.
    """
    print("token = %s" % creds['token'])
    return {'Authorization' : "%s %s" % (self._auth_type, creds['token'])}

  def _get_conn(self):
    if not self._conn:
      creds = self._get_token()

      if self._ssl:
        conn = HTTPSConnection(self._host, self._port)
      else:
        conn = HTTPConnection(self._host, self._port)

      self._conn = conn
      if self._need_token():
        self._user = creds['user']
        self._headers.update(self._auth_headers(creds))
        print("Added Token Headers")
        print(self._headers)

    return self._conn

  def _process_response(self, conn):
    resp = conn.getresponse()
    data = resp.read()
    if resp.status < 200 or resp.status >= 400:
      raise HTTPException(resp.status, resp.reason, data)
    if resp.status < 300 and resp.status != NO_CONTENT:
      try:
        if self._wrap_json_objects:
          return JsonObject(json.loads(data))
        else:
          return json.loads(data)
      except:
        return data
    return None

  def _request(self, method, uri, body=None, params=None):
    conn = self._get_conn()
    if body and isinstance(body, dict):
      if self._headers.get('Content-Type') == 'application/json':
        body = json.dumps(body)
      else:
        body = urllib.urlencode(body)
    if params:
      uri = "%s?%s" % (uri, urllib.urlencode(params))
    conn.request(method, self._base_uri + uri, body=body,
        headers=self._headers)
    return self._process_response(conn)

  def _get(self, uri, params=None):
    return self._request('GET', uri, params=params)

  def _post(self, uri, body=None, params=None):
    return self._request('POST', uri, body=body, params=params)

  def _put(self, uri, body=None, params=None):
    return self._request('PUT', uri, body=body, params=params)

  def close(self):
    if self._conn:
      self._conn.close()
      self._conn = None

  def __enter__(self):
    return self

  def __exit__(self, etype, evalue, traceback):
    self.close()
    return False


class JsonObject(object):
  """
  Makes it easier to work with JSON object stored as raw python dictionaries by allowing
  direct access using ".field" syntax. Probably horribly slow.

  Read-only.
  """

  def __init__(self, fields):
    self.raw = fields
    fields = copy.copy(fields)
    if isinstance(fields, dict):
      keys = list(fields.keys())
      for key in keys:
        fields[key] = self._wrap(fields[key])
    elif isinstance(fields, list):
      for i in range(len(fields)):
        fields[i] = self._wrap(fields[i])
    self._fields = fields


  def _wrap(self, obj):
    if isinstance(obj, dict) or isinstance(obj, list):
      return JsonObject(obj)
    return obj


  def __getattr__(self, attr):
    try:
      return getattr(self._fields, attr)
    except:
      return self[attr]


  def __len__(self):
    return len(self._fields)


  def __getitem__(self, key):
    return self._fields[key]


  def __iter__(self):
    return self._fields.__iter__()


  def get(self, key, default_value):
    candidate = self.__getitem__(key)
    if candidate == None:
      return default_value
    else:
      return candidate


def error(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
  sys.exit(1)


def check(check, msg, *args):
  if not check:
    error(msg, *args)


def prompt(dflt, msg, *args, **kw):
  allowed = kw.get('allowed')
  answer = None
  while answer is None:
    if args:
      msg = msg % args
    if dflt is not None:
      msg = "%s [%s]" % (msg, dflt)
    answer = raw_input(msg + ": ")
    if not answer.strip():
      answer = dflt
    if answer is None:
      print("Response required.")
    if allowed and answer not in allowed:
      print("Invalid response (allowed={})".format(repr(allowed)))
  return answer

