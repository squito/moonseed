import rest


class Dashboard:

  def __init__(self, jira_rest_client):
    self._client = jira_rest_client

  def my_dashboards(self):
    return self._client._get("/api/2/dashboard?filter=my")

  def get_dashboard(self, dashboard_id):
    # V2 api doesn't support getting dashboard items :(
    # https://community.atlassian.com/t5/Jira-Core-Server-questions/How-to-obtain-ItemId-in-api-2-dashboard-dashboardId-items-itemId/qaq-p/189400
    
    # Reverse engineered from examining HTML of dashboard page, uses a different, undocumented api endpoint!
    return self._client._get(f"/dashboards/1.0/{dashboard_id}")

  
