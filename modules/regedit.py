#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ======================================================================
# SCRIPT NAME: regedit.py

# PURPOSE: Add, remove and check for keys in MSIReg

# REVISION HISTORY:

# AUTHOR				DATE			DETAILS
# --------------------- --------------- --------------------------------
# julius bauer	        2021-01-18	    Initial version
# julius bauer	        2021-02-04	    Correcting expected Ansible codes
#                                       for ok/changed/fail. Documenting
#                                       method and improving error handling.
# LICENSE: GNU General Public License v3.0
# ======================================================================

from ansible.module_utils.basic import AnsibleModule
import os
import re

DOCUMENTATION = '''
---
module: regedit
short_description: Manipulate Windows registry files

description:
  - This module adds, checks, deletes and updates entries in a registry file.

notes:
  - Enclose HKEYs and values in single 'quotes'
  - Values are either bare or enclosed within "double quotes"
    E.g.
    "MetaDataODBCDriverVersion"="3.52"       - use ==> val: '"3.52"'
    "NumberOfNodesInCluster"=dword:00000001  - use ==> val: 'dword:00000001'
    (see examples below)
    
options:
  registry_filename:
    description:
      - file path name to the registry file (MSIReg.reg)
    type: str
    required: true

  registry_filename_out:
    description:
      - file path name to write the modified registry file to (MSIReg-RollOut.reg)
    type: str

  verb:
    description:
      - 'chk' for checking the existence of entries (for sanity checking) 
      - 'add' for adding HKEYs, keys and values 
      - 'del' for removing HKEYs, keys and values 
      - 'upd' for updating  HKEYs, keys and values 
        One verb value must be specified, otherwise this module will fail.
    type: str
    default: chk

  hkey:
    description:
      - A Windows registry HKEY path, e.g. [HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy]
    type: str
    required: true

  key:
    description:
      - The 'key' is 'ModelLoadTime' in the LHS of e.g. "ModelLoadTime"=dword:00002710
    type: str

  val:
    description:
      - The 'val' is 'dword:00002710' in the RHS of e.g. "ModelLoadTime"=dword:00002710
    type: str

  new_hkey:
    description:
      - A Windows registry HKEY path, e.g. [HKEY_LOCAL_MACHINE\SOFTWARE\MacroStrategy]
      - Use with verb 'upd' to chenge the HKEY path 
    type: str

  new_key:
    description:
      - A Windows registry HKEY path, e.g. [HKEY_LOCAL_MACHINE\SOFTWARE\MacroStrategy]
      - Use with verb 'upd' to chenge the HKEY path 
    type: str
    
  new_val:
    description:
      - A Windows registry HKEY path, e.g. [HKEY_LOCAL_MACHINE\SOFTWARE\MacroStrategy]
      - Use with verb 'upd' to chenge the HKEY path 
    type: str
author:
  - Julius Bauer (https://github.com/mathworld)
'''
EXAMPLES = '''
---
- name: A demo of modifying a MSIReg.reg file
  hosts: localhost
  gather_facts: false
  vars:
    msiregfile_path: microstrategy/MSIReg.reg
  tasks:
    - name: TC01 - Check if hkey exists in MSIReg.reg
      msireg:
        registry_filename: "{{ msiregfile_path }}"
        #
        registry_filename_out: "{{ msiregfile_path | default(omit) }}"
        hkey: "{{ item.hkey }}"
        key:  "{{ item.key | default(omit) }}"
        val:  "{{ item.val | default(omit) }}"
        verb: "{{ item.verb }}"
        # If verb: upd, then set the following keys accordingly
        new_hkey: "{{ item.new_hkey | default(omit) }}"
        new_key:  "{{ item.new_key  | default(omit) }}"
        new_val:  "{{ item.new_val  | default(omit) }}"
      with_items:
        # Test Case 01: Add a kv-pair to an HKEY 
        - {
            verb: add,
            hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer]',
            key: AsymmetricClustering01,
            val: 'dword:00000000',
        }
        # Test Case 01: Add an HKEY 
        - {
            verb: add,
            hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\MickeyMouse]',
            key: AsymmetricClustering01,
            val: 'dword:00000000',
        }
        - {
          verb: del
          hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer]',
          key: AsymmetricClustering01,
          val: dword:00000000,
        }
        - {
          verb: upd
          hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer]',
          key: AsymmetricClustering01,
          new_val: 'dword:11111111',
        }
        - {
          verb: del
          hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer]',
          key: AsymmetricClustering01,
        }
        - {
          verb: del,
          hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer\Diagnostics\Log2\(Default)\Error]',
        }
        - {
          verb: upd,
          hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\MicroStrategy\DSS Server\Instances\CastorServer]',
          key: MetaDataDatabaseVersion,
          new_val: '"129"',
        }

'''


def read_registry(fn_reg):
    """
    Read the Windows registry file from disk into a multi-level dictionary.
    :param fn_reg: filename of the registry file
    :return: a multi-level dictionary, preamble (header before the first HKEY), result of action
    """
    pkv_m = re.compile(r'"(?P<KEY>.+)?"=(?P<VAL>.*)\\')
    pkv_q = re.compile(r'"(?P<KEY>.+)?"="(?P<VAL>.*)"')
    pkv_b = re.compile(r'"(?P<KEY>.+)?"=(?P<VAL>.*)')

    registry = {}
    preamble = ''
    try:
        with open(fn_reg, mode='r', encoding='utf8') as fh:
            lines = fh.readlines()

        for i, line in enumerate(lines):
            line = line.rstrip()
            mkv_m = pkv_m.search(line)
            mkv_q = pkv_q.search(line)
            mkv_b = pkv_b.search(line)
            if line.startswith('[') and line.endswith(']'):
                hkey = line
                registry[hkey] = {}
                continue
            elif mkv_m:
                key = mkv_m.group('KEY')
                val = mkv_m.group('VAL')
                v = [f"{val}\\"]
                while 1:
                    for _line in lines[i + 1::]:
                        _line = _line.rstrip()
                        v.append(_line)
                        if not _line.endswith('\\'):
                            break
                    break
                val = '\n'.join(v)
                registry[hkey][key] = val
                continue
            elif mkv_q:
                key = mkv_q.group('KEY')
                val = mkv_q.group('VAL')
                registry[hkey][key] = f'"{val}"'
                continue
            elif mkv_b:
                key = mkv_b.group('KEY')
                val = mkv_b.group('VAL')
                registry[hkey][key] = f'{val}'
                continue
            elif line.startswith('@='):
                registry[hkey]['@'] = line.split('=')[1]
            elif len(line) == 0:
                pass
        res = 'read_registry_success'

        for line in lines:
            line = line.strip()
            if line.startswith('['):
                break
            else:
                preamble += line

    except FileNotFoundError as e:
        res = 'read_registry_filenotfound'

    return registry, preamble, res


def write_registry(fn_reg, preamble, registry):
    """
    Write the (updated) registry to file.
    :param fn_reg: filename of the registry file
    :param preamble: the part retrieved before the first HKEY
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :return: result of action
    """
    res = ''
    try:
        with open(fn_reg, mode='w', encoding='utf8') as f:
            f.write(preamble + os.linesep)
            f.write(os.linesep)

            for hkey in registry.keys():
                f.write(hkey + os.linesep)
                # for key in sorted(registry.get(hkey)):
                for key in registry.get(hkey):
                    if key is not None:
                        key = '@' if key == '@' else key
                        val = registry[hkey][key]
                        w_key = '@' if key == '@' else f'"{key}"'
                        f.write(f"{w_key}={val}" + os.linesep)
                    else:
                        f.write(os.linesep)
                f.write(os.linesep)
        res = 'write_registry_success'
    except FileNotFoundError as e:
        res = 'write_registry_filenotfound'

    return res


def add_hkey(registry, hkey):
    """
    Add an entry of the type [valid Windows registry hkey] to the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :return: updated dictionary and result
    """
    res = 'hkey_already_exists'
    if hkey not in registry.keys():
        registry[hkey] = {}
        res = 'hkey_added'

    return registry, res


def add_hkey_kv(registry, hkey, key, val):
    """
    Add an entry of the type [valid Windows registry hkey] plus a key-value pair to the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key: the key name
    :param val: the value of the corresponding key
    :return: updated dictionary and result
    """

    if hkey not in registry.keys():
        registry[hkey] = {}

    try:
        val = registry[hkey][key]
        res = 'hkey_kv_already_exists'
    except KeyError as kerr:
        registry[hkey][key] = val
        res = 'hkey_kv_added'

    return registry, res


def chk_hkey(registry, hkey):
    """
    Check if hkey exists in the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :return: updated dictionary and result
    """
    return 'hkey_exists' if hkey in registry.keys() else 'hkey_notexists'


def chk_hkey_kv(registry, hkey, key, val):
    """
    Check if a key-value pair is set for a given registry hkey.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key: the key name
    :param val: the value of the corresponding key
    :return: result of lookup:
        'hkey_kv_value_confirmed': hkey, key and value are set as queried.
        'hkey_kv_value_mismatch': hkey and key are set as queried, but the value is not.
        'hkey_kv_key_valuenull':  hkey and key are set as queried, but the value is empty.
        'hkey_kv_key_not_exists': hkey is set as queried, but the key string was not found.
        'hkey_notexists': the queried hkey was not found. See if you're escaping the backslashes correctly?
        The registry file has single backslashes whereas double backslashes should be used within code.
    """
    if hkey in registry.keys():
        if key in registry[hkey].keys():
            act_val = registry[hkey][key]
            if act_val == val:
                res = 'hkey_kv_value_confirmed'
            else:
                res = 'hkey_kv_value_mismatch'
        else:
            res = 'hkey_kv_key_not_exists'
    else:
        res = 'hkey_notexists'

    return res


def del_hkey(registry, hkey):
    """
    Remove a registry hkey. This also removes any children thereof!
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :return:
        'hkey_not_removed': if hkey was not set it will not be removed per se.
        'hkey_removed': the hkey (and any direct descendants) was removed.
    """
    res = 'hkey_notremoved'
    if hkey in registry.keys():
        del(registry[hkey])
        res = 'hkey_removed'

    return registry, res


def del_hkey_k(registry, hkey, key):
    """
    Remove a key for a given hkey without checking for its value.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key: the key name
    :return: updated dictionary and result
    """

    if hkey in registry.keys():
        if key in registry[hkey].keys():
            del(registry[hkey][key])
            res = 'hkey_k_removed'
        else:
            res = 'hkey_k_keynotfound'
    else:
        res = 'hkey_k_hkeynotfound'

    return registry, res


def del_hkey_kv(registry, hkey, key, val):
    """
    Remove a key-value pair for a given hkey. If the existing value is the same as the queried value, the kv-pair
    is removed. Else kept.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key: the key name
    :param val: the value of the corresponding key
    :return: updated dictionary and result
    """

    if hkey in registry.keys():
        if key in registry[hkey].keys():
            if registry[hkey][key] == val:
                del(registry[hkey][key])
                res = 'hkey_kv_removed'
            else:
                res = 'hkey_kv_value_mismatch'
        else:
            res = 'hkey_kv_keynotfound'
    else:
        res = 'hkey_kv_hkeynotfound'

    return registry, res


def upd_hkey(registry, hkey_old, hkey_new):
    """
    Change/update hkey in the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey_old: old valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param hkey_new: new valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MacroStrategy\\DSS Server]
    :return: modified registry, result of rename: 'hkey_renamed' or 'hkey_notfound'
    """
    try:
        if hkey_old == hkey_new:
            res = 'hkey_notupdated'
        else:
            registry[hkey_new] = registry.pop(hkey_old)
            res = 'hkey_updated'
    except KeyError as kerr:
        res = 'hkey_notfound'

    return registry, res


def upd_key(registry, hkey, key_old, key_new):
    """
    Change/update key in the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key_old: e.g. InstallPath (=/var/opt/Micro...)
    :param key_new: e.g. InstallationPath  (=/var/opt/Micro...)
    :return: modified registry, result of rename: 'key_renamed' or 'key_notfound'
    """
    try:
        if key_old == key_new:
            res = 'key_notupdated'
        else:
            val = registry[hkey][key_old]
            del(registry[hkey][key_old])
            registry[hkey][key_new] = val
            res = 'key_updated'
    except KeyError as kerr:
        res = 'key_notfound'

    return registry, res


def upd_val(registry, hkey, key, val_new):
    """
    Change/update value in the registry.
    :param registry: a multi-level dictionary as returned by read_registry(fn_reg)
    :param hkey: a valid Windows registry hkey, e.g. [HKEY_LOCAL_MACHINE\\SOFTWARE\\MicroStrategy\\DSS Server]
    :param key: e.g. LogPath
    :param val_new: e.g. /var/opt/MacroStrategy/log
    :return: modified registry, result of rename: 'val_renamed' or 'val_notfound'
    """
    try:
        val_old = registry[hkey][key]
        if val_old == val_new:
            res = 'val_notupdated'
        else:
            registry[hkey][key] = val_new
            res = 'val_updated'
    except KeyError as kerr:
        res = 'key_notfound'

    return registry, res


def main():

    module_params = {
        "verb":                  {"default": 'chk', "choices": ['chk', 'add', 'del', 'upd'], "type": 'str'},
        "registry_filename":     {"required": True, "type": 'str'},
        "registry_filename_out": {"default": '', "type": 'str'},
        "hkey":                  {"required": True, "type": 'str'},
        "key":                   {"default": '', "type": 'str'},
        "val":                   {"default": '', "type": 'str'},
        "new_hkey":              {"default": '', "type": 'str'},
        "new_key":               {"default": '', "type": 'str'},
        "new_val":               {"default": '', "type": 'str'},

    }

    module = AnsibleModule(argument_spec=module_params, supports_check_mode=False)

    func_rescode = {
        'read_registry': {
            'read_registry_success': 'The specified registry file could be read and parsed.',
            'read_registry_filenotfound': 'The specified registry file could not be found.',
        },
        'write_registry': {
            'write_registry_success': 'The (modified) registry was successfully dumped to file.',
            'write_registry_filenotfound': 'The specified registry file could not be written to.',
        },
        'add_hkey': {
            'hkey_added': 'HKEY successfully added.',
            'hkey_already_exists': 'HKEY already exists.',
        },
        'add_hkey_kv': {
            'hkey_kv_added': 'HKEY kv-pair successfully added.',
            'hkey_kv_already_exists': 'HKEY kv-pair already exists.',
        },
        'chk_hkey': {
            'hkey_exists': 'HKEY exists.',
            'hkey_notexists': 'HKEY does not exist.',
        },
        'chk_hkey_kv': {
            'hkey_kv_value_confirmed': 'HKEY kv-pair, as queried, exists.',
            'hkey_kv_value_mismatch': 'HKEY key has a different value than queried.',
            'hkey_kv_key_not_exists': 'HKEY kv-pair, as queried, was NOT found.',
            'hkey_notexists': 'HKEY, as queried, NOT found.',
        },
        'del_hkey': {
            'hkey_removed': 'HKEY successfully deleted (including any existing kv-pairs!)',
            'hkey_notremoved': 'HKEY, as queried, was NOT found in the registry',
        },
        'del_hkey_k': {
            'hkey_k_removed': 'The key under HKEY was successfully deleted (value not checked).',
            'hkey_k_keynotfound': 'The key under HKEY was NOT found.',
            'hkey_k_hkeynotfound': 'The HKEY was NOT found.',
        },
        'del_hkey_kv': {
            'hkey_kv_removed': 'The key-value under HKEY was successfully deleted (value checked).',
            'hkey_kv_value_mismatch': 'The key under HKEY has a different value than queried.',
            'hkey_kv_keynotfound': 'The key under HKEY was not found.',
            'hkey_kv_hkeynotfound': 'The HKEY was NOT found.',
        },
        'upd_hkey': {
            'hkey_updated': 'The HKEY entry was renamed.',
            'hkey_notupdated': 'The HKEY entry was not updated (old/new HKEY same).',
            'hkey_notfound': 'The HKEY was NOT found.',
        },
        'upd_key': {
            'key_updated': 'The key under HKEY was renamed.',
            'key_notupdated': 'The key under HKEY was not updated (old/new key same).',
            'key_notfound': 'The key under HKEY was NOT found.',
        },
        'upd_val': {
            'val_updated': 'The value belonging to key under HKEY was renamed.',
            'val_notupdated': 'The value belonging to key under HKEY was not updated (old/new val same).',
            'val_notfound': 'The key under HKEY was NOT found (implying that the value could not be updated).',
        },
    }
    res_modind = (
        'write_registry_success',
        'hkey_added',
        'hkey_kv_added',
        'hkey_removed',
        'hkey_k_removed',
        'hkey_kv_removed',
        'hkey_updated',
        'key_updated',
        'val_updated'
    )
    result = dict(
        changed=False,
        message=''
    )

    if not module.check_mode:

        if os.path.isfile(module.params['registry_filename']):
            pass
        else:
            module.fail_json(msg=f"{module.params['registry_filename']} does not exist!")

        fin = module.params['registry_filename']
        fou = module.params['registry_filename_out'] if module.params['registry_filename_out'] != '' else fin
        hky = module.params['hkey']
        key = module.params['key']
        val = module.params['val']
        vrb = module.params['verb']
        nhk = module.params['new_hkey']
        nke = module.params['new_key']
        nva = module.params['new_val']

        # -----------------------------
        # Read the registry file
        # -----------------------------
        fnc = 'read_registry'
        params = (fin,)
        reg, preamble, res = eval(fnc)(*params)

        if res == 'read_registry_filenotfound':
            result['message'] = func_rescode[fnc][res]
            module.fail_json(msg=result['message'])

        # -----------------------------
        # Perform requested actions
        # -----------------------------
        if vrb == 'chk':

            if key == '' and val == '':
                fnc = f'{vrb}_hkey'
                params = (reg, hky)
            else:
                fnc = f'{vrb}_hkey_kv'
                params = (reg, hky, key, val)

            res = eval(fnc)(*params)
            result['message'] = func_rescode[fnc][res]

        elif vrb in ('add', 'del', 'upd'):

            if vrb in ('add', 'del') and key == '' and val == '':
                fnc = f'{vrb}_hkey'
                params = (reg, hky)
            elif vrb in ('add', 'del') and key != '' and (val == '' or val == '*'):
                fnc = f'{vrb}_hkey_k'
                params = (reg, hky, key)
            elif vrb in ('add', 'del'):
                fnc = f'{vrb}_hkey_kv'
                params = (reg, hky, key, val)
            elif vrb == 'upd' and nhk != '':
                fnc = f'{vrb}_hkey'
                params = (reg, hky, nhk)
            elif vrb == 'upd' and nke != '':
                fnc = f'{vrb}_key'
                params = (reg, hky, key, nke)
            elif vrb == 'upd' and nva != '':
                fnc = f'{vrb}_val'
                params = (reg, hky, key, nva)

            reg, mod_res = eval(fnc)(*params)
            result['message'] = func_rescode[fnc][mod_res]

            if mod_res in res_modind:
                result['changed'] = True

                wrt_res = write_registry(fou, preamble, reg)
                if wrt_res != 'write_registry_success':
                    module.fail_json(msg=result['message'])

        module.exit_json(**result)


if __name__ == '__main__':
    main()
