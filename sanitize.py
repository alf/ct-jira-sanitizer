#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2011 Alf Lervåg. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#    2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials
#       provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY ALF LERVÅG ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL ALF LERVÅG OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be interpreted
# as representing official policies, either expressed or implied, of
# Alf Lervåg.

import os
import sys
import datetime
import calendar
from collections import defaultdict
from suds.client import Client
import ConfigParser

from ct.apis import BaseAPI


config = ConfigParser.ConfigParser()
user_cfg = os.path.expanduser('~/.sanitizer.cfg')
default_cfg = os.path.join(
        sys.prefix,
        'share/ct-jira-sanitizer/config.ini.sample')
config.read([default_cfg, user_cfg])

def dates_in_month(year, month):
    _, n_days = calendar.monthrange(year, month)
    return [datetime.date(year, month, d) for d in range(1, n_days + 1)]


def get_jira_activities():
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
    ct = BaseAPI(config.get("server", "url"))
    ct.login(config.get("login", "username"), config.get("login", "password"))
    ct_activities = defaultdict(lambda: defaultdict(lambda: 0))
    for activity in ct.get_month(args.year, args.month):
        ctref, _, _ = activity.project_id.partition(",")
	ctref = int(ctref)
        if not ctref in jira_activities:
            continue

        date = activity.date
        hours = activity.duration

        ct_activities[ctref][date] += hours
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
    print "Discrepency:   id,       date, jira,   ct"
    for ctref in ctrefs:
        for day in dates_in_month(args.year, args.month):
            ct_hours = ct_activities[ctref][day]
            jira_hours = jira_activities[ctref][day]
            if jira_hours != ct_hours:
                print "Discrepency: %s, %s, %04s, %04s" % (
                    ctref, day, jira_hours, ct_hours)
