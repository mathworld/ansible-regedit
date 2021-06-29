# How it works

This Ansible module can be used to edit Windows registry like files of the form:

```text
[HKEY_LOCAL_MACHINE\BCD00000000\Description]
"KeyName"="BCD00000000"
"System"=dword:00000001
"TreatAsSystem"=dword:00000001
"ApplicationIdentity"=hex(2):25,00,53,00,79,00,73,00,74,00,65,00,6d,00,52,00,\
  6f,00,6f,00,74,00,25,00,5c,00,53,00,79,00,73,00,74,00,65,00,6d,00,33,00,32,\
  00,5c,00,77,00,65,00,76,00,74,00,73,00,76,00,63,00,2e,00,64,00,6c,00,6c,00,\
  00,00
```

Five different verbs `chk`, `get`, `add`, `del`, and `upd` can be specified.

Added/fixed 2021-06-28: 
- NEW: `get` can be used to retrieve a value for a given hkey/key combination.
- NEW: `ignore_case` can now be specified with all verbs. Valid arguments are: `yes`/`y` and `no`/`n`. 
- NEW: `result.msgcode` can now be retrieved and used in subsequent processing logic. See the `func_rescode` structure in `main()`.
- FIX: when using `upd` with a given HKEY and the key does not exist, the key/value pair will be set.

## Using `add` t add HKEYs and key-value pairs

(for preamble cf. `test-regedit-disobeying-dry.yml`)
```text
- name: 'Test Case ADD-01: Add an HKEY'
  regedit:
    registry_filename: "{{ regfile_path }}"
    verb: add
    hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\DummyHKEY]'
```
To add a key-value pair specify `key` and `val` as well:
```text
    registry_filename: "{{ regfile_path }}"
    verb: add
    hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\DummyHKEY]'
    key: FullName
    val: '"Harlequin Joost"'
```
If using the Ansible `with_items` modifier the following section reveals the required 
versus optional parameters (or rather the minimal set of required parameters):
```text
---
- name: Test cases for modifying registry file.
  regedit:
    registry_filename: "{{ regfile_path }}"
    hkey: "{{ item.hkey }}"
    key:  "{{ item.key | default(omit) }}"
    val:  "{{ item.val | default(omit) }}"
    verb: "{{ item.verb }}"
    # If verb: upd, then set the following keys accordingly
    new_hkey: "{{ item.new_hkey | default(omit) }}"
    new_key:  "{{ item.new_key  | default(omit) }}"
    new_val:  "{{ item.new_val  | default(omit) }}"
  register: result
  with_items:
    # =========================================================================
    # Test Case ADD-01: Add an HKEY
    # =========================================================================
    - {
        verb: add,
        hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\DummyHKEY]',
    }
    # =========================================================================
    # Test Case ADD-02: Add a kv-pair to an HKEY where value is a "string"
    # =========================================================================
    - {
        verb: add,
        hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\DummyHKEY]',
        key: FullName,
        val: '"Harlequin Joost"',
    }
    # =========================================================================
    # Test Case ADD-03: Add a kv-pair to an HKEY where value is a bare dword
    # =========================================================================
    - {
        verb: add,
        hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\DummyHKEY]',
        key: FullBareWord,
        val: 'dword:11111111',
    }    
```
(for preamble cf. `test-regedit-using-with_items.yml`). Note: Always enclose the HKEYs in single quotes. Keys, i.e.
in the RHS of `key: <val>` the `<val>` does not need the `'` around it unless `<val>` contains spaces or other character outside 
[a-zA-Z0-9_]. As for the RHS of `val` it is best to always engage enclosing `'`-pairs. If the `val` value contains
spaces also include an inner pair of `"`-pair around the string.

## Using `chk` - checking presence of HKEYs and key-value pairs

```text
    # =========================================================================
    # Test Case CHK-01: Check if an HKEY exists
    # =========================================================================
    - {
      verb: chk,
      hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE]',
    }
    # =========================================================================
    # Test Case CHK-02: Check if an HKEY kv-pair exists (is set)
    # =========================================================================
    - {
      verb: chk,
      hkey: '[HKEY_LOCAL_MACHINE\SOFTWARE\Common Files]',
      key: CloudConnectorConfigDir,
      val: '"/var/opt/vendor/install/CloudConnectorConfig"',
    }
```
Now that will only print `ok`. If you want to see the result of the check, you could do this:
```text
    # =========================================================================
    # Test Case CHK-03: Check return of non-existing HKEY
    # =========================================================================
    - name: 'Test Case CHK-03:Check return of non-existing HKEY'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DoesNotExist]'
      register: result
    - debug:
        msg: "{{ result }}"
    # =========================================================================
    # Test Case CHK-04: Check return of existing HKEY, but non-existing key
    # =========================================================================
    - name: 'Test Case CHK-03:Check return of non-existing HKEY'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\Description]'
        key: NonExistingKey
      register: result
    - debug:
        msg: "{{ result }}"
    # =========================================================================
    # Test Case CHK-05: Check return of existing HKEY and key, but wrong value
    # =========================================================================
    - name: 'Test Case CHK-03:Check return of non-existing HKEY'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\Description]'
        key: TreatAsSystem
        val: 'dword:00000002'
      register: result
    - debug:
        msg: "{{ result }}"
```
which will print:
```text
TASK [debug] ******* ...
ok: [localhost] => {
    "msg": {
        "changed": false,
        "failed": false,
        "message": "HKEY does not exist.",
        "original_message": ""
    }
}

TASK [Test Case CHK-03:Check return of non-existing HKEY] ******* ...
ok: [localhost]

TASK [debug] *******
ok: [localhost] => {
    "msg": {
        "changed": false,
        "failed": false,
        "message": "HKEY kv-pair, as queried, was NOT found.",
        "original_message": ""
    }
}

TASK [Test Case CHK-03:Check return of non-existing HKEY] ******* ...
ok: [localhost]

TASK [debug] ******* ...
ok: [localhost] => {
    "msg": {
        "changed": false,
        "failed": false,
        "message": "HKEY key has a different value than queried.",
        "original_message": ""
    }
}
```

Further techniques using `chk`:

```text
    # =========================================================================
    # Test Case CHK-01.1: Check if exists: HKEY
    # =========================================================================
    - name: 'Test Case CHK-01: Check if HKEY exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\Description]'
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"

    # =========================================================================
    # Test Case CHK-01.2: Check if exists: HKEY/KEY
    # =========================================================================
    - name: 'Test Case CHK-02: Check if HKEY/KEY exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\Description]'
        key: KeyName
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"

    # =========================================================================
    # Test Case CHK-01.3: Check if exists: HKEY/KEY/VAL
    # =========================================================================
    - name: 'Test Case CHK-03: Check if HKEY/KEY/VAL exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\Description]'
        key: KeyName
        val: '"BCD00000000"'
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"

    # =========================================================================
    # Test Case CHK-02.1: Check if exists: HKEY (ignoring case)
    # =========================================================================
    - name: 'Test Case CHK-01: Check if HKEY exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DESCRIPTION]'
        ignore_case: "yes"
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"

    # =========================================================================
    # Test Case CHK-02.2: Check if exists: HKEY/KEY (ignoring case)
    # =========================================================================
    - name: 'Test Case CHK-02: Check if HKEY/KEY exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DESCRIPTION]'
        key: KEYNAME
        ignore_case: "yes"
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"

    # =========================================================================
    # Test Case CHK-02.3: Check if exists: HKEY/KEY/VAL (ignoring case)
    # =========================================================================
    - name: 'Test Case CHK-03: Check if HKEY/KEY/VAL exists'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: chk
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DESCRIPTION]'
        key: KEYNAME
        val: '"bcd00000000"'
        ignore_case: "yes"
      register: result
    - debug:
        msg: "'{{ result.msgcode }}' => '{{ result.message }}'"
```

will result in:

```text
TASK [Test Case CHK-01: Check if HKEY exists] ************************************************************
ok: [localhost]

TASK [debug]************************************************************
ok: [localhost] => {
    "msg": "'hkey_exists' => 'HKEY exists (case-sensitive).'"
}

TASK [Test Case CHK-02: Check if HKEY/KEY exists] ************************************************************
ok: [localhost]

TASK [debug]************************************************************
ok: [localhost] => {
    "msg": "'hkey_k_key_exists' => 'HKEY/KEY-pair exists (case-sensitive).'"
}

TASK [Test Case CHK-03: Check if HKEY/KEY/VAL exists] ************************************************************
ok: [localhost]

TASK [debug] ************************************************************
ok: [localhost] => {
    "msg": "'hkey_kv_value_confirmed' => 'HKEY/KEY/VAL tuple exists (case-sensitive).'"
}

TASK [Test Case CHK-01: Check if HKEY exists] ************************************************************
ok: [localhost]

TASK [debug] ************************************************************
ok: [localhost] => {
    "msg": "'hkey_exists_ic' => 'HKEY exists (ignoring case).'"
}

TASK [Test Case CHK-02: Check if HKEY/KEY exists] ************************************************************
ok: [localhost]

TASK [debug]************************************************************
ok: [localhost] => {
    "msg": "'hkey_k_key_exists_ic' => 'HKEY/KEY-pair exists (ignoring case).'"
}

TASK [Test Case CHK-03: Check if HKEY/KEY/VAL exists] ************************************************************
ok: [localhost]

TASK [debug]************************************************************
ok: [localhost] => {
    "msg": "'hkey_kv_value_confirmed_ic' => 'HKEY/KEY/VAL tuple exists (ignoring case).'"
}
```

## Using `del` to remove HKEYs and key-value pairs
```text
    # =========================================================================
    # Test Case DEL-01: Delete an HKEY (and any direct kv-pairs)
    # =========================================================================
    - {
      verb: del,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DeleteMe]',
    }
    # =========================================================================
    # Test Case DEL-02: Delete an HKEY kv-pair
    # =========================================================================
    - {
      verb: del,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DeleteMe2]',
      key: TreatAsSystem
    }
    # =========================================================================
    # Test Case DEL-03: Delete an HKEY kv-pair only if the value is as specified
    # =========================================================================
    - {
      verb: del,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\DeleteMe2]',
      key: System,
      val: 'dword:00000001'
    }

```
Specifying just the `hkey` value will delete all key-value pairs below that `hkey`. If, additionally, the `key` value is
specified the key-value pair will be removed no matter what the `val` value was set to (brute delete). And, finally, if the `val` value
is specified the module will delete the key-value pair only if the `val` value is also present (safe delete).

## Using `upd` to update HKEYs and key-value pairs
When updating `HKEYs` and/or key-value pairs, in addition to `hkey`, we need to specify new values in `new_hkey` (rename HKEY), `new_key` (rename key entry) or
`new_val` (change value). `new_hkey` does not need values for `new_key` nor `new_val`, but when changing a key with `new_key` we need
to specify the `new_hkey`. And, finally, when changing/updating a value we need - see these examples for more clarity:
```text
    # =========================================================================
    # Test Case UPD-01: Update HKEY path
    # =========================================================================
    - {
      verb: upd,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe]',
      new_hkey: '[HKEY_LOCAL_MACHINE\HelloWorld\UpdateMe]',
    }
    # =========================================================================
    # Test Case UPD-02: Update key
    # =========================================================================
    - {
      verb: upd,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe2]',
      key: NodeJS,
      new_key: nodejs,
    }
    # =========================================================================
    # Test Case UPD-03: Update value
    # =========================================================================
    - {
      verb: upd,
      hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe2]',
      key: nodejs,
      new_val: '"/var/opt/vendor/install/NodeJS/bin/node"',
    }
```

## Using `upd` to create a new key-value entry and using `get` to retrieve it - once without and once with the `ignore_case` flag: 
```text
    # =========================================================================
    # Test Case UPD-01.1: Update a HKEY/KEY pair where the KEY does not yet
    #                     exist and set it to a given value
    # =========================================================================
    - name: 'Test Case UPD-01: Set the value for given HKEY/KEY'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: upd
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe2]'
        key: ThisKeyDidNotExistBeforeRun
        new_val: ThisValueWasUpserted
      register: result
    - debug:
        msg: "'{{ result.message }}' - expected result: changed and a new key/value pair"

    # =========================================================================
    # Test Case UPD-01.2: Retrieve the key/value set above
    # =========================================================================
    - name: 'Test Case GET-02: Get the value for given HKEY/KEY'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: get
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe2]'
        key: ThisKeyDidNotExistBeforeRun
      register: result
    - debug:
        msg: "'{{ result.message }}' - expected result: 'ThisValueWasUpserted'"

    # =========================================================================
    # Test Case UPD-01.3: Retrieve the key/value set above
    # =========================================================================
    - name: 'Test Case GET-03: Get the value for given HKEY/KEY but with IGNORE CASE flag'
      regedit:
        registry_filename: "{{ regfile_path }}"
        verb: get
        hkey: '[HKEY_LOCAL_MACHINE\BCD00000000\UpdateMe2]'
        key: THISKEYDIDNOTEXISTBEFORERUN
        ignore_case: "yes"
      register: result
    - debug:
        msg: "'{{ result.message }}' - expected result: 'ThisValueWasUpserted'"

```
# Running it

```text
$ ansible-playbook test-regedit-using-with_items.yml

PLAY [A demo of modifying a registry file] *********

TASK [Test cases for modifying registry file.] *****
changed: [localhost] => (item={
    'verb': 'add',
    'hkey': '[HKEY_LOCAL_MACHINE\\SOFTWARE\\DummyHKEY]'}
    )
changed: [localhost] => (item={
    'verb': 'add',
    'hkey': '[HKEY_LOCAL_MACHINE\\SOFTWARE\\DummyHKEY]',
    'key': 'FullName',
    'val': '"Harlequin Joost"'}
    )
changed: [localhost] => (item={
    'verb': 'add',
    'hkey': '[HKEY_LOCAL_MACHINE\\SOFTWARE\\DummyHKEY]',
    'key': 'FullBareWord',
    'val': 'dword:11111111'}
    )
ok: [localhost] => (item={
    'verb': 'chk',
    'hkey': '[HKEY_LOCAL_MACHINE\\SOFTWARE]'}
    )
ok: [localhost] => (item={
    'verb': 'chk',
    'hkey': '[HKEY_LOCAL_MACHINE\\SOFTWARE\\Common Files]',
    'key': 'CloudConnectorConfigDir',
    'val': '"/var/opt/vendor/install/CloudConnectorConfig"'}
    )
changed: [localhost] => (item={
    'verb': 'del',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\DeleteMe]'}
    )
changed: [localhost] => (item={
    'verb': 'del',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\DeleteMe2]',
    'key': 'TreatAsSystem'}
    )
changed: [localhost] => (item={
    'verb': 'del',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\DeleteMe2]',
    'key': 'System',
    'val': 'dword:00000001'}
    )
changed: [localhost] => (item={
    'verb': 'upd',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\UpdateMe]',
    'new_hkey': '[HKEY_LOCAL_MACHINE\\HelloWorld\\UpdateMe]'}
    )
changed: [localhost] => (item={
    'verb': 'upd',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\UpdateMe2]',
    'key': 'NodeJS',
    'new_key': 'nodejs'}
    )
changed: [localhost] => (item={
    'verb': 'upd',
    'hkey': '[HKEY_LOCAL_MACHINE\\BCD00000000\\UpdateMe2]',
    'key': 'nodejs',
    'new_val': '"/var/opt/vendor/install/NodeJS/bin/node"'}
    )

PLAY RECAP *****************************************
localhost                  : ok=1    changed=1    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License
[GNU GPLv3](https://choosealicense.com/licenses/gpl-3.0/)