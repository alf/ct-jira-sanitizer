#!/usr/bin/env python

import os
import sys
import datetime
import calendar
from collections import defaultdict
from suds.client import Client
import ConfigParser

from ct.apis import SimpleAPI


def dates_in_month(year, month):
    _, n_days = calendar.monthrange(year, month)
    return [datetime.date(year, month, d) for d in range(1, n_days + 1)]


def get_jira_activities():
    config = ConfigParser.ConfigParser()
    user_cfg = os.path.expanduser('~/.sanitizer.cfg')
    default_cfg = os.path.join(
        sys.prefix,
        'share/ct-jira-sanitizer/config.ini.sample')

    config.read([default_cfg, user_cfg])

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
            raise SystemError(msg)

        worklogs = soap.service.getWorklogs(auth, issue.key)

        for worklog in worklogs:
            day = worklog.startDate.date()
            hours = worklog.timeSpentInSeconds / 3600.0
            activities[ctref][day] += hours

    return activities


def get_ct_activities(year, month):
    ct = SimpleAPI()
    ct_activities = defaultdict(lambda: defaultdict(lambda: 0))
    for activity in ct.list_activities(args.year, args.month):
        ctref = activity['project'].project_id
        if not ctref in jira_activities:
            continue

        day = activity['day']
        hours = activity['hours']

        ct_activities[ctref][day] += hours
    return ct_activities

if __name__ == "__main__":
    import argparse
    now = datetime.datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest='month', type=int, default=now.month,
       help='The month to sanitize hours from, defaults to current month')
    parser.add_argument('-y', dest='year', type=int, default=now.year,
       help='The year to sanitize hours from, defaults to current year')
    args = parser.parse_args()

    jira_activities = get_jira_activities()
    ct_activities = get_ct_activities(args.year, args.month)

    ctrefs = set(ct_activities.keys() + jira_activities.keys())
    for ctref in ctrefs:
        for day in dates_in_month(args.year, args.month):
            ct_hours = ct_activities[ctref][day]
            jira_hours = jira_activities[ctref][day]
            if jira_hours != ct_hours:
                print "Discrepency: %s, %s, %s, %s" % (
                    ctref, day, jira_hours, ct_hours)
