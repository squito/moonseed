import json
import os

import rest


class Filters:

  # https://docs.atlassian.com/software/jira/docs/api/REST/8.22.1/#filter

  def __init__(self, jira_rest_client):
    self._client = jira_rest_client

  def my_filters(self):
    return self._client._get("/api/2/filter/favourite")

  
  def update_filter(self, filter_dict):
    """Given the json of the filter, create the filter (if it doesn't have an id),
       or update the existing filter.  Returns the full json (as a dict) of the filter 
       (with an id).  The passed in json only needs name and jql.  It may also have a
       "comment" field, which will be stripped before posting, but retained in return
       value.
    """
    comment_to_add = None
    if "comment" in filter_dict:
      filter_to_upload = filter_dict.copy()
      comment_to_add = filter_to_upload.pop("comment", None)
    else:
      filter_to_upload = filter_dict
    if "id" in filter_dict:
      # PUT an update for the filter
      fid = filter_dict["id"]
      rv = self._client._put(f"/api/2/filter/{fid}", body=filter_to_upload)
    else:
      # POST a new filter.  important to return the result, as that is the only
      # way to capture the ID of the created filter
      rv = self._client._post(f"/api/2/filter", body=filter_to_upload)
    if comment_to_add is not None:
      rv["comment"] = comment_to_add
    return rv


  def sync_filters(self, filter_dir):
    files = os.listdir(filter_dir)
    for f in files:
      full_path = filter_dir + "/" + f
      with open(full_path) as in_f:
        loaded_filter = json.load(in_f)
        new_filter = self.update_filter(loaded_filter)
      with open(full_path, "w") as out_f:
        json.dump(new_filter, out_f)

