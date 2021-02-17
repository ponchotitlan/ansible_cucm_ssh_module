#!/usr/bin/python
# -*- coding: utf-8 -*-

DOCUMENTATION = '''
---
module: cucm_ssh
short_description: SSH connector to CUCM (CallManager) with bundled operations and output parsing
description:
    - This module logs in the provided CUCM servers via SSH and executes the specified commands.
    - Output is JSON object with formatted/parsed information based on the input command.
    - Please verify options and example for supported usage
version_added: "1.5"
author: "Alfonso Sandoval"
options:
# One or more of the following
    cucm_ip:
        description:
            - Target IP address of the CUCM server
        required: true
        default: null
        choices:
          - null
        aliases:
          - null
        version_added: "1.5"
    cucm_user:
        description:
            - SSH-enabled username of the CUCM server
        required: true
        default: null
        choices:
          - null
        aliases:
          - null
        version_added: "1.5"
    cucm_pwd:
        description:
            - SSH-enabled password of the CUCM server
        required: true
        default: null
        choices:
          - null
        aliases:
          - null
        version_added: "1.5"
    cucm_option:
        description:
            - Pre-bundled SSH command to execute and parse
        required: true
        default: null
        choices:
          - DIAGNOSTIC
          - DISASTER_RECOVERY
          - DBREPLICATION
        aliases:
          - null
        version_added: "1.0"
notes:
    - This module supports CUCM versions 9.x, 10.x, 11.x and 12.x.
    - Outputs are parsed and built in JSON format. Only relevant information is rendered
requirements:
    - ansible==2.9.12
    - paramiko==2.0.0
    - paramiko-expect==0.2.8
'''

EXAMPLES = '''
- name: Get CUCM DB Replication status 
  hosts: my_cucm_hosts
  connection: local
  gather_facts: no
  tasks:
    - name: Get CUCM DB Replication status
      cucm_ssh:
        cucm_ip: "{{ansible_ssh_host}}"
        cucm_user: "{{ansible_user}}"
        cucm_pwd: "{{ansible_ssh_pass}}"
        cucm_option: "DBREPLICATION"
      register: result
    - debug: var=result

- name: Get CUCM Disaster Recovery status 
  hosts: my_cucm_hosts
  connection: local
  gather_facts: no
  tasks:
    - name: Get CUCM Disaster Recovery status
      cucm_ssh:
        cucm_ip: "{{ansible_ssh_host}}"
        cucm_user: "{{ansible_user}}"
        cucm_pwd: "{{ansible_ssh_pass}}"
        cucm_option: "DISASTER_RECOVERY"
      register: result
    - debug: var=result

- name: Get CUCM Diagnostic test results 
  hosts: my_cucm_hosts
  connection: local
  gather_facts: no
  tasks:
    - name: Get CUCM Diagnostic test results
      cucm_ssh:
        cucm_ip: "{{ansible_ssh_host}}"
        cucm_user: "{{ansible_user}}"
        cucm_pwd: "{{ansible_ssh_pass}}"
        cucm_option: "DIAGNOSTIC"
      register: result
    - debug: var=result

'''

import paramiko, sys, os, json, re
from paramiko_expect import SSHClientInteraction
from ansible.module_utils.basic import AnsibleModule

#AVAILABLE QUERIES DICTIONARY
COMMAND_DICTIONARY = {
    "DIAGNOSTIC" : "utils diagnose test",
    "DISASTER_RECOVERY" : "utils disaster_recovery status backup",
    "DBREPLICATION" : "utils dbreplication runtimestate"
}

def main():
    fields = {"cucm_ip": {"required": True, "type": "str"},
              "cucm_user": {"required": True, "type": "str"},
              "cucm_pwd": {"required": True, "type": "str"},
              "cucm_option": {"required": True, "type": "str"}
    }
    module = AnsibleModule(argument_spec=fields)

    #IF INPUT OPERATION IS NOT IN CATALOGUE, THE EXECUTION IS HALTED AND ERROR MESSAGE IS RETURNED TO PLAYBOOK
    if module.params['cucm_option'].upper() not in COMMAND_DICTIONARY.keys():
        module.fail_json(msg="Input cucm_option not supported ("+module.params['cucm_option']+")")

    #CONNECTION VIA SSH. IF EXCEPTION IS RAISED, IT IS RETURNED TO PLAYBOOK
    SSH_CONNECTOR = connect_SSH(module.params)
    if SSH_CONNECTOR[0] is False:
        module.fail_json(msg="ERROR: "+SSH_CONNECTOR[1])
    
    #IF SSH IS OK, THE INPUT OPERATION IS PROCESSED
    output = process_UCM(SSH_CONNECTOR[1],module.params['cucm_option'].upper(),COMMAND_DICTIONARY[module.params['cucm_option'].upper()])
    module.exit_json(changed=False, meta=output)

#CONNECT TO CUCM VIA SSH
def connect_SSH(DATA):
    try:
        IP = DATA['cucm_ip'].replace("ansible_ssh_host=","")
        USERNAME = DATA['cucm_user'].replace("ansible_user=","")
        PASSWORD = DATA['cucm_pwd'].replace("ansible_ssh_pass=","")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(IP, username=USERNAME, password=PASSWORD, timeout=5)        
        return [True,ssh]
    except Exception as e:
        return [False,str(e)]

#PROCESSING OF SSH OPERATION. THE RESULT IS PARSED ACCORDINGLY WITH A SPECIFIC REGEX MOTOR
def process_UCM(SSH,KEY,OPERATION):
    try:
        interact = SSHClientInteraction(SSH, display=False) 
        interact.expect('admin:')
        interact.send(OPERATION)
        interact.expect('admin:')
        output = interact.current_output_clean
        SSH.close()

        #PARSING
        if KEY == "DIAGNOSTIC":
            parsed_output = diagnose_parser(output.split('\n'))
            return parsed_output

        if KEY == "DISASTER_RECOVERY":
            parsed_output = disaster_parser(output.split('\n'))
            return parsed_output

        if KEY == "DBREPLICATION":
            parsed_output = dbreplication_parser(output.split('\n'))
            return parsed_output

    except Exception as e:
        return str(e)

#PARSING MOTOR FOR DIAGNOSE COMMAND
def diagnose_parser(RUNNING_CONFIG_RAW):
    DIAGNOSE_OUTPUT = []
    LOG_FILE = ''

    for LINE in RUNNING_CONFIG_RAW:
        if re.search(r'Log file:\s.+', LINE, re.I):
            LOG_FILE = re.search(r'Log file:\s(.+)', LINE, re.I).group(1)

        if re.search(r'\w+\s-\s\w+\s+:\s.+', LINE, re.I):
            DIAGNOSE_OUTPUT.append({
                "TEST": re.search(r'(\w+\s-\s\w+)\s+:\s(.+)', LINE, re.I).group(1),
                "RESULT": re.search(r'(\w+\s-\s\w+)\s+:\s(.+)', LINE, re.I).group(2)
            })

    return {"LOG FILE":LOG_FILE,"DIAGNOSTIC":DIAGNOSE_OUTPUT}

#PARSING MOTOR FOR DBREPLICATION COMMAND
def dbreplication_parser(RUNNING_CONFIG_RAW):
    DBREPLICATION_OUTPUT = []
    MESSAGE = ''

    for LINE in RUNNING_CONFIG_RAW:
        #IF ERROR MESSAGES ARE SHOWN, THE PROCESS IS HALTED
        if re.search(r'Runtime state cannot be performed on a cluster with a single active node; aborting operation', LINE, re.I) or re.search(r'Cisco DB is not running', LINE, re.I):
            MESSAGE = LINE
            break
        #NORMAL GATHERING PROCESS
        if re.search(r'\w+\s+[\d+\.]+\s+[\S]+\s+[\S]+\s+[\S]+\s+[\S]+\s+.+', LINE, re.I):
            DBREPLICATION_OUTPUT.append({
                "SERVER_NAME": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(1),
                "IP_ADDRESS": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(2),
                "PING (msec)": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(3),
                "DB/RPC/DBMON?": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(4),
                "REPL.QUEUE": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(5),
                "Replication Group ID": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(6),
                "REPLICATION SETUP (RTMT) & Details": re.search(r'(\w+)\s+([\d+\.]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+([\S]+)\s+(.+)', LINE, re.I).group(7) 
            })

    if MESSAGE is not '':
        return {"message":MESSAGE}
    else:
        return DBREPLICATION_OUTPUT

#PARSING MOTOR FOR DISASTER COMMAND
def disaster_parser(RUNNING_CONFIG_RAW):
    BACKUP_OUTPUT = []
    MESSAGE = STATUS = TAR_FILE = STORAGE = OPERATION = PERCENTAGE = ''

    for LINE in RUNNING_CONFIG_RAW:
        #IF ERROR MESSAGES ARE SHOWN, THE PROCESS IS HALTED
        if re.search(r'drfCliMsg: No backup status available', LINE, re.I):
            MESSAGE = LINE
            break

        #NORMAL GATHERING PROCESS
        if re.search(r'Status:\s.+', LINE, re.I):
            STATUS = re.search(r'Status:\s(.+)', LINE, re.I).group(1)
        if re.search(r'Tar Filename:\s.+', LINE, re.I):
            TAR_FILE = re.search(r'Tar Filename:\s(.+)', LINE, re.I).group(1)
        if re.search(r'Storage Location:\s.+', LINE, re.I):
            STORAGE = re.search(r'Storage Location:\s(.+)', LINE, re.I).group(1)
        if re.search(r'Operation:\s.+', LINE, re.I):
            OPERATION = re.search(r'Operation:\s(.+)', LINE, re.I).group(1)
        if re.search(r'Percentage Complete:\s.+', LINE, re.I):
            PERCENTAGE = re.search(r'Percentage Complete:\s(.+)', LINE, re.I).group(1)
        if re.search(r'\w+\s+\w+\s+\w+\s+\w+\s+[\w\s:]+[\d]\s+.+', LINE, re.I):
            BACKUP_OUTPUT.append({
                "SERVER TYPE": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(1),
                "HOSTNAME": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(2),
                "COMPONENT": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(3),
                "STATUS": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(4),
                "DATE": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(5),
                "LOG FILE": re.search(r'(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s+([\w\s:]+[\d])\s+(.+)', LINE, re.I).group(6)
            })

    if len(BACKUP_OUTPUT) == 0:
        return {"message":MESSAGE}
    else:
        return {
            "STATUS":STATUS,
            "TAR FILE": TAR_FILE,
            "STORAGE LOCATION": STORAGE,
            "OPERATION": OPERATION,
            "PERCENTAGE COMPLETE": PERCENTAGE,
            "DETAILS": BACKUP_OUTPUT
            }

if __name__ == '__main__':
    main()