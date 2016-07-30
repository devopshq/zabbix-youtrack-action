# zabbix-youtrack-action
Create issue in Youtrack from Zabbix
+ Create issue in Youtrack
+ Send link to this issue to Zabbix acknowledge
+ Verify issue if Zabbix send **OK** state, and issue in **Fixed** state

## Install
1. Copy this repo to alertscripts directory

2. Create new media type **YT-WORKFLOW** with parameters (see screenshot in **./docs** folder):
  * {ALERT.SENDTO}
  * {ALERT.SUBJECT}
  * {ALERT.MESSAGE}
  * YOUR_YOUTRACK_PASSWORD (zabbix_api)
  * YOUR_ZABBIX_PASSWORD (zabbix)

3. Create user:
  * **Zabbix** - **zabbix_api** with **Zabbix Super Admin* permissions
  * **Zabbix** - **YT** with **Zabbix User* permissions, and set media type **YT-WORKFLOW** - link to youtack (e.g. https://youtrack.example.com)
  * **Youtrack** - **zabbix** user (permission in your project)

4. Create *Actions* (see screenshot in **./docs** folder):

  * Default subject and Recovery subject - **[{TRIGGER.STATUS}] {HOST.NAME1} - {TRIGGER.NAME}**  
  * Default message and Recovery message  
   Name: '{HOST.NAME1} [{TRIGGER.NAME}]'  
   Text: '{ITEM.NAME1} ({HOST.NAME1}:{ITEM.KEY1}): {ITEM.VALUE1}'  
   Hostname: '{HOST.NAME1}'  
   Status: '{TRIGGER.STATUS}'  
   Severity: "{TRIGGER.SEVERITY}"  
   EventID: "{EVENT.ID}"  
   TriggerID: "{TRIGGER.ID}"  
  *Send to **YT** via **YT-WORKFLOW**  

5. Assign **Profile.DevOps.ZabbixServer.ALL** to Zabbix Server
6. Add to UserParameter on Zabbix Server:
  * UserParameter=zabbix_server_ptzabbixalertytworkflow.py, grep -q 'ERROR - Exit with error' /var/log/zabbix/PtZabbixAlertYTWorkflow.log; echo $?;


*LAST*. Debug code for your YT-WORKFLOW (see screenshot in **./docs** folder)

## NOTES
This script contains a lot of "hardcode", issues contains Refactors tasks.