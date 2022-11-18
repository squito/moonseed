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
       (with an id).  The passed in json only needs name and jql.
    """
    if "id" in filter_dict:
      # PUT an update for the filter
      fid = filter_dict["id"]
      return self._client._put(f"/api/2/filter/{fid}", body=filter_dict)
    else:
      # POST a new filter.  important to return the result, as that is the only
      # way to capture the ID of the created filter
      return self._client._post(f"/api/2/filter", body=filter_dict)

      
