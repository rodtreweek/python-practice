#!/usr/bin/python
# -*- coding: utf-8 -*-

# (c) 2013, Chris Hoffman <christopher.hoffman@gmail.com>
# (c) 2016, Byron Dover <byrondover@gmail.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
---
module: apm
short_description: Manage Atom packages with apm
description:
  - Manage Atom packages with Atom Package Manager (apm)
version_added: 2.2
author: Byron Dover
options:
  name:
    description:
      - The name of an Atom library to install
    required: true
  version:
    description:
      - The version to be installed
    required: false
  executable:
    description:
      - The executable location for apm
      - This is useful if apm is not in $PATH
    required: false
  state:
    description:
      - The state of the Atom library
    required: false
    default: present
    choices: [ "present", "absent", "latest" ]
'''

EXAMPLES = '''
description: Install "project-manager" Atom package.
- apm: name=project-manager state=present

description: Install specific version of "project-manager" Atom package.
- apm: name=project-manager version=3.3.2 state=present

description: Update package "project-manager" to the latest version.
- apm: name=project-manager state=latest

description: Remove package "project-manager".
- apm: name=project-manager state=absent

description: Install package "project-manager" using apm installed in custom location.
- npm: name=project-manager executable=/path/to/apm state=present
'''

import os

# import module snippets
from ansible.module_utils.basic import *

class Apm(object):
    def __init__(self, module, **kwargs):
        self.module = module
        self.name = kwargs['name']
        self.version = kwargs['version']

        if kwargs['executable']:
            self.executable = kwargs['executable'].split(' ')
        else:
            self.executable = [module.get_bin_path('apm', True)]

        if kwargs['version']:
            self.name_version = self.name + '@' + str(self.version)
        else:
            self.name_version = self.name

    def _exec(self, args, run_in_check_mode=False, check_rc=True):
        if not self.module.check_mode or (self.module.check_mode and run_in_check_mode):
            cmd = self.executable + args

            if self.name:
                cmd.append(self.name_version)

            rc, out, err = self.module.run_command(cmd, check_rc=check_rc)
            return out
        return ''

    def list(self):
        cmd = ['list']

        installed = list()
        missing = list()
        data = self._exec(cmd, True, False)
        pattern = re.compile('^(?:\xe2\x94\x9c|\xe2\x94\x94)\xe2\x94\x80\xe2\x94\x80\s+(\S+)@')
        for dep in data.splitlines():
            m = pattern.match(dep)
            if m:
                installed.append(m.group(1))
        if self.name not in installed:
            missing.append(self.name)

        return installed, missing

    def install(self):
        return self._exec(['install'])

    def update(self):
        return self._exec(['update'])

    def uninstall(self):
        return self._exec(['uninstall'])

    def list_outdated(self):
        outdated = list()
        data = self._exec(['outdated'], True, False)
        pattern = re.compile('^(?:\xe2\x94\x9c|\xe2\x94\x94)\xe2\x94\x80\xe2\x94\x80\s+(\S+)')
        for dep in data.splitlines():
            m = pattern.match(dep)
            if m and m.group(1) != '(empty)':
                outdated.append(m.group(1))

        return outdated


def main():
    arg_spec = dict(
        name=dict(default=None),
        version=dict(default=None),
        executable=dict(default=None, type='path'),
        state=dict(default='present', choices=['present', 'absent', 'latest']),
    )
    module = AnsibleModule(
        argument_spec=arg_spec,
        supports_check_mode=True
    )

    name = module.params['name']
    version = module.params['version']
    executable = module.params['executable']
    state = module.params['state']

    if not name:
        module.fail_json(msg='apm package name must be specified')

    apm = Apm(module, name=name, version=version, executable=executable)

    changed = False
    if state == 'present':
        installed, missing = apm.list()
        if len(missing):
            changed = True
            apm.install()
    elif state == 'latest':
        installed, missing = apm.list()
        outdated = apm.list_outdated()
        if len(missing):
            changed = True
            apm.install()
        if len(outdated):
            changed = True
            apm.update()
    else: #absent
        installed, missing = apm.list()
        if name in installed:
            changed = True
            apm.uninstall()

    module.exit_json(changed=changed)

main()
