import json
import mock
import os
import shutil
import unittest

import filters 

class TestFilters(unittest.TestCase):

  resource_dir = "test/resources/"
  input_filter_dir = resource_dir + "input_filters/"
  resulting_filter_dir = resource_dir + "resulting_filters/"
  working_filter_dir = resource_dir + "working_dir/"

  def setUp(self):
    if os.path.exists(self.working_filter_dir):
      shutil.rmtree(self.working_filter_dir)


  def test_update_filter(self):
    mock_client = mock.Mock()
    f = filters.Filters(mock_client, self.working_filter_dir)
    self.assertEqual(f._id_to_filter, {})
    self.assertEqual(f._id_to_file, {})
    # comment gets stripped before posted, but retained in returned value
    no_id = {"name": "Blah", "jql":"foo", "comment": "ignore me"}
    exp = no_id.copy()
    exp.pop("comment", None)
    # jira server should always add an ID, and we'll record that
    rv = exp.copy()
    rv["id"] = "567"
    mock_client._post.return_value = rv.copy()
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
    self.assertIn("567", f._id_to_filter)
    self.assertIn("567", f._id_to_file)




  def test_sync_filters_from_dir(self):
    shutil.copytree(self.input_filter_dir, self.working_filter_dir)
    file_to_orig_json = {}
    exp = {}
    for f in os.listdir(self.working_filter_dir):
      with open(self.working_filter_dir + f) as f_in:
        file_to_orig_json[f] = json.load(f_in)
        exp[f] = file_to_orig_json[f].copy()
        exp[f]["blah"] = "foo"
        
    mock_client = mock.Mock()
    # the value returned from the server should *always* contain an id for the filter.
    # in this test, we want to make sure that some internal bookkeeping happens w/ that
    # id.
    exp["simple_1.json"]["id"] = "123"
    mock_client._post.return_value = exp["simple_1.json"]
    mock_client._put.return_value = exp["simple_2.json"]

    fs = filters.Filters(mock_client, self.working_filter_dir)

    fs.sync_filters_from_dir(self.working_filter_dir)

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

    # make sure that we updated the internal id_to_... dicts w/ the new id
    self.assertIn("123", fs._id_to_file)
    self.assertEqual(fs._filter_dir + "simple_1.json", fs._id_to_file["123"])
    self.assertEqual(exp["simple_1.json"], fs._id_to_filter["123"])

  def test_sync_filters_from_server(self):
    mock_client = mock.Mock()
    f = filters.Filters(mock_client, self.working_filter_dir)

    id_to_return_value = {
      "1": {"name": "Blah", "jql":"foo", "id": "1"},
      "2": {"name": "Flippy", "jql":"zim", "id": "2"}
    }
    def rv(passed_id):
      return id_to_return_value[passed_id]
    mock_client._get.side_effect = rv

    f.sync_filters_from_server

    pass
