import json
import os

import rest


class Filters:

  # https://docs.atlassian.com/software/jira/docs/api/REST/8.22.1/#filter

  def __init__(self, jira_rest_client, filter_dir):
    self._client = jira_rest_client
    self._filter_dir = filter_dir
    if not os.path.exists(filter_dir):
      os.makedirs(filter_dir)
    self._reload_id_to_filter()

  def my_filters(self):
    return self._client._get("/api/2/filter/favourite")


  def get_filter(self, fid):
    return self._client._get(f"/api/2/filter/{fid}")

  
  def _reload_id_to_filter(self):
    self._id_to_filter = {}
    self._id_to_file = {}
    if not os.path.exists(self._filter_dir):
      return
    for f in os.listdir(self._filter_dir):
      full_path = self._filter_dir + f
      with open(full_path) as f_in:
        loaded = json.load(f_in)
        if "id" in loaded:
          fid = loaded["id"]
          self._id_to_filter[fid] = loaded
          self._id_to_file[fid] = full_path
        else:
          print("WARN: filter file " + full_path + " does not have an id yet")

  
  def update_filter(self, filter_dict, orig_file=None):
    """Given the filter (as a dict), create the filter (if it doesn't have an id),
       or update the existing filter.  Returns the full json (as a dict) of the filter 
       (with an id).  The passed in dict only needs name and jql.  It may also have a
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
      fid = rv["id"]
      self._id_to_filter[fid] = rv
    if comment_to_add is not None:
      rv["comment"] = comment_to_add

    # write the filter back to a file
    if fid in self._id_to_file:
      out_file = self._id_to_file[fid]
    elif orig_file is not None:
      out_file = orig_file
    else: 
      out_file = self.__suggested_filter_filename(fid, rv["name"])
    with open(out_file, "w") as out_w:
      json.dump(rv, out_w, indent=2)
    self._id_to_file[fid] = out_file

    return rv


  def __suggested_filter_filename(self, filter_id, filter_name):
    return self._filter_dir + f"/{filter_name}_{filter_id}.json"


  def sync_filters_from_dir(self):
    """Sync filters between a directory and the jira server.
       Filters already in the dir will be uploaded to the server -- they can be
       completely new filters, or just updates to existing filters.

       All existing files in the dir must be json files representing jira filters."""

    files = os.listdir(self._filter_dir)
    for f in files:
      full_path = os.path.normpath(self._filter_dir + "/" + f)
      with open(full_path) as in_f:
        loaded_filter = json.load(in_f)
        new_filter = self.update_filter(loaded_filter, orig_file = full_path)
      with open(full_path, "w") as out_f:
        json.dump(new_filter, out_f, indent=2)


  def sync_filters_from_server(self, filter_ids):
    """Download the given set of filters from server, and store to files in directory.
       If the filters exist in the dir already, they will be updated.  Otherwise, new
       files will be created (based on filter name + id).

       Any changes to the local files will be overwritten -- recommended to only use
       this if you've committed local changes to git.

       If there is a comment in the local file, it will be retained.
       """
    for fid in filter_ids:
      from_server = self.get_filter(fid)
      comment_to_add = None
      orig_file = self._id_to_file.get(fid)
      if orig_file is not None:
        file_to_write = orig_file
        with open(orig_file) as f_in:
          orig_loaded = json.load(f_in)
          comment_to_add = orig_loaded.get("comment")
      else:
        file_to_write = self.__suggested_filter_filename(from_server["id"], from_server["name"])
      to_write = from_server
      if comment_to_add is not None:
        to_write["comment"] = comment_to_add
      with open(file_to_write, "w") as f_out:
        json.dump(to_write, f_out, indent=2)
      self._id_to_file[fid] = file_to_write
      self._id_to_filter[fid] = to_write

