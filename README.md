# ansible_cucm_ssh_module

[![forthebadge](https://forthebadge.com/images/badges/made-with-python.svg)](https://forthebadge.com) [![forthebadge](https://forthebadge.com/images/badges/built-with-love.svg)](https://forthebadge.com)

SSH connector to CUCM (CallManager) with bundled operations and output parsing

This is an Ansible module which connects to the target CUCM servers via SSH in order to execute CLI commands and gather outputs.
The current version supports the following commands:

- utils diagnose test
- utils disaster_recovery status backup
- utils dbreplication runtimestate

Outputs are filtered and only the relevant information is dumped in JSON format.

 ### GUIDELINES

- Python v.3.6.9 must be installed. This must be the only python version in the host OS.
- Install the dependencies:
```
pip install -r requirements.txt
```
- Copy the module file cucm_ssh.py in the following location of your host OS:
```
/usr/share/ansible/plugins/modules
```
- Prepare your hosts file with the CUCM servers of interest 
```
[my_cucm_hosts]
ansible_ssh_host=<ip> ansible_user=<username> ansible_ssh_pass=<password>
ansible_ssh_host=<ip> ansible_user=<username> ansible_ssh_pass=<password>
ansible_ssh_host=<ip> ansible_user=<username> ansible_ssh_pass=<password>
. . .
```

A sample playbook looks like the following: 
```
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
```
In order to run the playbook, issue the following command:
```
ansible-playbook my_playbook.yaml'
```

In case python3 is not the only version installed in the host system, issue the following command:
```
ansible-playbook my_playbook.yaml -e 'ansible_python_interpreter=/usr/bin/python3'
```

Supported commands in the cucm_option are:
- DIAGNOSTIC
- DISASTER_RECOVERY
- DBREPLICATION

The outputs are stripped from unnecessary information, and only relevant data is dumped in a JSON structure.

If you need more help, you can issue the following command for an extensive guide:
```
ansible-doc -t module cucm_ssh
```

Crafted with :heart: by [Alfonso Sandoval - Ponchotitlán](https://linkedin.com/in/asandovalros)
