#!/usr/bin/env python

# Sample Python client accessing JIRA via SOAP. By default, accesses
# http://jira.atlassian.com with a public account. Methods requiring
# more than basic user-level access are commented out. Change the URL
# and project/issue details for local testing.
# 
# Note: This Python client only works with JIRA 3.3.1 and above (see
# http://jira.atlassian.com/browse/JRA-7321)
#
# Refer to the SOAP Javadoc to see what calls are available:
# http://www.atlassian.com/software/jira/docs/api/rpc-jira-plugin/latest/com/atlassian/jira/rpc/soap/JiraSoapService.html
#
# For a much more comprehensive example, see
# http://svn.atlassian.com/svn/public/contrib/jira/jira-cli/src/cli/jira

from collections import defaultdict
from suds.client import Client
import ConfigParser


def get_jira_activities():
    config = ConfigParser.ConfigParser()
    config.read(['config.ini.sample', 'config.ini'])

    soap = Client('https://jira.bouvet.no/rpc/soap/jirasoapservice-v2?wsdl')

    custom_field_id = config.get("jira", "custom_field_id")
    username = config.get("jira-login", "username")
    password = config.get("jira-login", "password")
    auth = soap.service.login(username, password)

    query = """
    project in projectsWhereUserHasPermission("Work On Issues") AND
    cf[%s] is not empty
    """ % custom_field_id

    activities = defaultdict(lambda: defaultdict(lambda: 0))
    issues = soap.service.getIssuesFromJqlSearch(auth, query, 1000)
    for issue in issues:
        ctref = None
        for customField in issue.customFieldValues:
            if customField.customfieldId == "customfield_%s" % custom_field_id:
                ctref = int(customField.values[0])

        if not ctref:
            msg = "This should never happen! Assumptions are wrong!"
            raise SystemError, msg

        worklogs = soap.service.getWorklogs(auth, issue.key)

        for worklog in worklogs:
            day = worklog.startDate.date()
            hours = worklog.timeSpentInSeconds / 3600.0
            activities[ctref][day] += hours

    return activities

if __name__ == "__main__":
    activities = get_jira_activities()
    for ctref, worked in sorted(activities.items()):
        for day, hours in sorted(worked.items()):
            print "%s: Worked %s hours on %s " % (ctref, hours, day)
