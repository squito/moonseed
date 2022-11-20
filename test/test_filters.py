import json
import mock
import os
import shutil
import unittest

import filters 

class TestFilters(unittest.TestCase):

  def test_update_filter(self):
    mock_client = mock.Mock()
    f = filters.Filters(mock_client)
    # comment gets stripped before posted, but retained in returned value
    no_id = {"name": "Blah", "jql":"foo", "comment": "ignore me"}
    exp = no_id.copy()
    exp.pop("comment", None)
    mock_client._post.return_value = exp.copy()
    new_filter = f.update_filter(no_id)
    mock_client._post.assert_called_with("/api/2/filter", body=exp)
    self.assertIn("comment", new_filter)
    self.assertEqual("ignore me", new_filter["comment"])

    with_id = no_id
    with_id["id"] = "12345"
    exp = with_id.copy()
    exp.pop("comment", None)
    mock_client._put.return_value = exp.copy()
    updated_filter = f.update_filter(with_id)
    mock_client._put.assert_called_with("/api/2/filter/12345", body=exp)
    self.assertIn("comment", new_filter)
    self.assertEqual("ignore me", new_filter["comment"])



  resource_dir = "test/resources/"
  input_filter_dir = resource_dir + "input_filters/"
  resulting_filter_dir = resource_dir + "resulting_filters/"
  working_filter_dir = resource_dir + "working_dir/"

  def test_sync_filters(self):
    shutil.rmtree(self.working_filter_dir)
    shutil.copytree(self.input_filter_dir, self.working_filter_dir)
    file_to_orig_json = {}
    exp = {}
    for f in os.listdir(self.working_filter_dir):
      with open(self.working_filter_dir + f) as f_in:
        file_to_orig_json[f] = json.load(f_in)
        exp[f] = file_to_orig_json[f].copy()
        exp[f]["blah"] = "foo"
        
    mock_client = mock.Mock()
    # TODO this should actually be something updated w/ an ID
    mock_client._post.return_value = exp["simple_1.json"]
    mock_client._put.return_value = exp["simple_2.json"]

    f = filters.Filters(mock_client)

    f.sync_filters(self.working_filter_dir)

    print(file_to_orig_json)

    mock_client._put.assert_called_with(
      "/api/2/filter/1",
      body=file_to_orig_json["simple_2.json"])
    mock_client._post.assert_called_with(
      "/api/2/filter",
      body=file_to_orig_json["simple_1.json"])

    # Make sure the results got updated with what actually came back from
    # server (in this case, I just put in a "blah" entry)
    for f in os.listdir(self.working_filter_dir):
      with open(self.working_filter_dir + f) as f_in:
        actual = json.load(f_in)
        self.assertEqual(exp[f], actual)


