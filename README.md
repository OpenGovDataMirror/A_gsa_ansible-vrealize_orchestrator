vrealize_orchestrator [![circleci](https://circleci.com/gh/GSA/ansible-vrealize_orchestrator.svg?style=svg)](https://circleci.com/gh/GSA/ansible-vrealize_orchestrator)
=========

This ansible role is for the vrealize orchestrator API execution of workflows

Requirements
------------

Required Packages (this role requires access to the following packages/installers)

None

Role Variables
--------------

| Variable | Default | Purpose |
| ------ | ------ | ------ |
| grace_ip | "" | new instance ip |
| ansible_os_family | "" | Windows/RedHat |
| snow_sys_id | "" | servicenow sys_id for RITM |
| grace_hostname | "" | new instance hostname |
| grace_env | "" | grace environment (PROD/TEST) |

Dependencies
------------

None

Example Playbook
----------------

```yaml
- hosts: servers
  roles:
     - vrealize_orchestrator
```

Public domain
-------------

This project is in the worldwide [public domain](LICENSE.md). As stated in [CONTRIBUTING](CONTRIBUTING.md):

> This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).
>
> All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
