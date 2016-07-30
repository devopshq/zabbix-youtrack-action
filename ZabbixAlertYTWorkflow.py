#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) DevOpsHQ, 2016

# Integration YouTrack and Zabbix alerts.

import yaml

from pyzabbix import ZabbixAPI
import sys
import urllib
import logging
import time

from youtrack.connection import Connection
import re
from requests.packages.urllib3 import disable_warnings


disable_warnings()  # disable ssl certificate errors

# ------------ START Constants ------------
YT_PROJECT_NAME = 'CM'  # ID project in Youtrack
YT_ASSIGNEE = 'Zabbix'  # Assignee to after create issue
YT_TYPE = 'Error'  # Youtrack Issue type
YT_SERVICE = 'Zabbix'  # Youtrack Issue service
YT_SUBSYSTEM = 'DevOps'  # Youtrack Issue subsystem
YT_USER = 'Zabbix'  # Youtrack Issue create user
YT_PASSWORD = sys.argv[4]  # Youtrack user password
YT_TIME = 'About 1 hour'  # Estimated time
# YT_TIME = 'Undefined'  # Estimated time
YT_COMMENT = "Now is {status}. \n{text}\n\n"  # Add this comment in issue
LOG_FILE_NAME = '/var/log/zabbix/PtZabbixAlertYTWorkflow.log'  # Path to Log-file for debug
# LOG_FILE_NAME = 'PtZabbixAlertYTWorkflow.log'  # Uncomment for debug in Windows-OS

ZABBIX_SERVER = "https://zabbix.example.com/zabbix"
ZBX_USER = "zabbix_api"
ZBX_PASSWORD = sys.argv[5]
# ------------ END Constants ------------

# ------------ START Setup logging ------------
# Use logger to log information
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Log to file
fh = logging.FileHandler(LOG_FILE_NAME)
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Log to stdout
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)  # Use logger to log information

# Log from pyzabbix
log = logging.getLogger('pyzabbix')
log.addHandler(ch)
log.addHandler(fh)
log.setLevel(logging.DEBUG)
# ------------ END Setup logging ------------


# ------------ START ZabbixAPI block ------------
Zbx = ZabbixAPI(ZABBIX_SERVER)
Zbx.session.verify = False
Zbx.login(ZBX_USER, ZBX_PASSWORD)


# ------------ END ZabbixAPI block ------------

# ------------ START Function declaration ------------
def ExecAndLog(connection, issueId, command="", comment=""):
    logger.debug("Run command in {issueId}: {command}. {comment}".format(issueId=issueId,
                                                                         command=command,
                                                                         comment=comment
                                                                         ))
    connection.executeCommand(issueId=issueId,
                              command=command,
                              comment=comment,
                              )


# ------------ END Function declaration ------------


def Main(sendTo, subject, yamlMessage):
    """
    Workflow Zabbix-YouTrack
    :param sendTo: URL to Youtrack (ex. https://youtrack.example.com)
    :param subject: subject from Zabbix Action
    :param yamlMessage: message from Zabbix Action
    :return:
    """

    # ----- Use below example yamlMessage to debug -----
#     yamlMessage = """Name: 'Test Zabbix-YT workflow, ignore it'
# Text: 'Agent ping (server:agent.ping()): DOWN (1) '
# Hostname: 'server.exmpale.ru'
# Status: "OK"
# Severity: "High"
# EventID: "96976"
# TriggerID: "123456789012" """

    messages = yaml.load(yamlMessage)

    # ----- START Issue parameters -----
    # Correspondence between the YouTrackPriority and ZabbixSeverity
    # Critical >= High
    # Normal < High

    ytPriority = 'Normal'
    if messages['Severity'] == 'Disaster' or messages['Severity'] == 'High':
        ytPriority = 'Critical'

    ytName = "{} ZabbixTriggerID::{}".format(messages['Name'], messages['TriggerID'])
    # ----- END Issue parameters -----

    # ----- START Youtrack Issue description -----
    # Search link to other issue
    searchString = "Hostname: '{}'".format(messages['Hostname'])
    linkToHostIssue = "{youtrack}/issues/{projectname}?q={query}".format(
        youtrack=sendTo,
        projectname=YT_PROJECT_NAME,
        query=urllib.parse.quote(searchString, safe='')
    )

    issueDescription = """
{ytName}
-----
{yamlMessage}
-----
- [https://zabbix.example.com/zabbix.php?action=dashboard.view Zabbix Dashboard]
- Show [{linkToHostIssue} all issue for *this host*]
""".format(
        ytName=ytName,
        yamlMessage=yamlMessage,
        linkToHostIssue=linkToHostIssue, )

    # ----- END Youtrack Issue description -----

    # ----- START Youtrack current week -----

    # Create connect to Youtrack API
    connection = Connection(sendTo, YT_USER, YT_PASSWORD)

    # Get current week in YT format (Sprint planned)
    version = connection.getAllBundles('version')

    for fixVersion in version[0].values:
        if fixVersion['archived'] == False and fixVersion['released'] == False:
            fixVersionWeek = fixVersion['name']
            break
    # ----- END Youtrack current week -----

    # ----- START Youtrack get or create issue -----
    # Get issue if exist
    # Search for TriggerID
    createNewIssue = False

    logger.debug("Get issue with text '{}'".format(messages['TriggerID']))
    issue = connection.getIssues(YT_PROJECT_NAME,
                                 "ZabbixTriggerID::{}".format(messages['TriggerID']),
                                 0,
                                 1)


    if len(issue) == 0:
        createNewIssue = True

    else:
        # if issue contains TriggerID in summary, then it's good issue
        # else create new issue, this is bad issue, not from Zabbix
        if "ZabbixTriggerID::{}".format(messages['TriggerID']) in issue[0]['summary']:
            issueId = issue[0]['id']
            issue = connection.getIssue(issueId)
        else:
            createNewIssue = True

    # Create new issue
    if createNewIssue:
        logger.debug("Create new issue because it is not exist")
        issue = connection.createIssue(YT_PROJECT_NAME,
                                       'Unassigned',
                                       ytName,
                                       issueDescription,
                                       priority=ytPriority,
                                       subsystem=YT_SUBSYSTEM,
                                       type=YT_TYPE,
                                       )
        time.sleep(3)

        # Parse ID for new issue
        result = re.search(r'(CM-\d*)', issue[0]['location'])
        issueId = result.group(0)
        issue = connection.getIssue(issueId)

    logger.debug("Issue have id={}".format(issueId))

    # Set issue service
    ExecAndLog(connection, issueId, "Service {}".format(YT_SERVICE))

    # Update priority
    ExecAndLog(connection, issueId, "Priority {}".format(ytPriority))

    # ----- END Youtrack get or create issue -----

    # ----- START PROBLEM block ------
    if messages['Status'] == "PROBLEM":

        # Issue exist and NOT Hold on, Unnassigned and Estimated time set
        if issue['State'] != 'Hold on':

            # Estimated time
            ExecAndLog(connection, issueId, "Estimated time {}".format(YT_TIME))

            # Update fix version
            ExecAndLog(connection=connection, issueId=issueId, command="Sprint planned {}".format(fixVersionWeek))

        # Reopen if Fixed or Verified or Canceled
        if issue['State'] == 'Fixed' or issue['State'] == 'Verified' or issue['State'] == 'Canceled':
            # Reopen Issue
            ExecAndLog(connection, issueId, "State reopen")

            # Assignee issue
            ExecAndLog(connection, issueId, command="Assignee Unassigned")

        # Update summary and description for issue
        logger.debug("Run command in {issueId}: {command}".format(issueId=issueId,
                                                                  command="""Update summary and description with connection.updateIssue method"""
                                                                  ))
        connection.updateIssue(issueId=issueId, summary=ytName, description=issueDescription)

        # Add comment
        logger.debug("Run command in {issueId}: {command}".format(issueId=issueId,
                                                                  command="""Now is PROBLEM {}""".format(
                                                                      messages['Text'])
                                                                  ))
        connection.executeCommand(issueId=issueId,
                                  command="",
                                  comment=YT_COMMENT.format(
                                      status=messages['Status'],
                                      text=messages['Text'])
                                  )

        # Send ID to Zabbix:
        logger.debug("ZABBIX-API: Send Youtrack ID to {}".format(messages['EventID']))
        Zbx.event.acknowledge(eventids=messages['EventID'], message="Create Youtrack task")
        Zbx.event.acknowledge(eventids=messages['EventID'],
                              message="https://youtrack.example.com/issue/{}".format(issueId))
    # ----- End PROBLEM block ------


    # ----- Start OK block -----
    if messages['Status'] == "OK":

        if issue['State'] == 'Hold on' or issue['State'] == 'Registered':
            # Cancel if not in work
            ExecAndLog(connection, issueId, command="State Cancel")

            # Assignee issue
            ExecAndLog(connection, issueId, command="Assignee {}".format(YT_ASSIGNEE))

        if issue['State'] == 'Fixed':
            # Verify if Fixed
            ExecAndLog(connection, issueId, command="State verify")

        logger.debug("Run command in {issueId}: {command}".format(issueId=issueId,
                                                                  command="""Now is OK {}""".format(messages['Text'])
                                                                  ))
        connection.executeCommand(issueId=issueId,
                                  command="",
                                  comment=YT_COMMENT.format(
                                      status=messages['Status'],
                                      text=messages['Text'])
                                  )
        # ----- End OK block -----


if __name__ == "__main__":

    logger.debug("Start script with arguments: {}".format(sys.argv[1:]))

    try:
        Main(
            # Arguments WIKI: https://www.zabbix.com/documentation/3.0/ru/manual/config/notifications/media/script
            sys.argv[1],  # to
            sys.argv[2],  # subject
            sys.argv[3],  # body

            # FYI: Next argument used in code:
            # sys.argv[4],  # YT_PASSWORD
            # sys.argv[5],  # ZBX_PASSWORD
        )

    except Exception:
        logger.exception("Exit with error")  # Output exception
        exit(1)
