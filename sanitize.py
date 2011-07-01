import sys
import datetime
from collections import defaultdict
# Hackish!
sys.path.insert(0, "../ct")

import jira
from apis import SimpleAPI

if __name__ == "__main__":
    import argparse
    now = datetime.datetime.now()

    parser = argparse.ArgumentParser()
    parser.add_argument('-m', dest='month', type=int, default=now.month,
       help='The month number to sanitize hours from, defaults to current month')
    parser.add_argument('-y', dest='year', type=int, default=now.year,
       help='The year to sanitize hours from, defaults to current year')
    args = parser.parse_args()

    ct = SimpleAPI()

    jira_activities = jira.get_jira_activities()

    ct_activities = defaultdict(lambda: defaultdict(lambda: 0))
    for activity in ct.list_activities(args.year, args.month):
        ctref = activity['project'].project_id
        if not ctref in jira_activities:
            continue

        day = activity['day']
        hours = activity['hours']

        ct_activities[ctref][day] += hours
        

    for ctref, activity in sorted(ct_activities.items()):
        for day, ct_hours in sorted(activity.items()):
            jira_hours = jira_activities[ctref][day]
            if jira_hours != ct_hours:
                print "Discrepency: %s, %s, %s, %s" % (ctref, day, jira_hours, ct_hours)

