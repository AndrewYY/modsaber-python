''' simple modsaber mod installer. run as admin if you need to. '''
import io
import json
import os
import subprocess
import time
import urllib.request
import winreg
import zipfile

# constants
modsaber_url = 'https://www.modsaber.org/api'
api_version = '1.1'

required_mods = ['illusion-plugin-architecture']

## get the beat saber install directory
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Steam App 620980') as key:
    installdir = winreg.QueryValueEx(key, 'InstallLocation')[0]
try:
    version = open(os.path.join(installdir, 'BeatSaberVersion.txt')).read()
except:
    version = ''

## grab the mod database from the server

# build the url
req_url = f'{modsaber_url}/v{api_version}/mods/approved/newest-by-gameversion'

# make the web request
req = urllib.request.Request(req_url)
req.add_header('User-Agent', 'Mozilla/5.0')
r = urllib.request.urlopen(req)
data = json.loads(r.read())

# keep making web requests until we have everything
print("Fetching Mod Database")
for i in range(1, data['lastPage'] + 1):
    print(".", end='', flush=True)
    req = urllib.request.Request(f'{req_url}/{i}')
    req.add_header('User-Agent', 'Mozilla/5.0')
    r = urllib.request.urlopen(req)
    newdata = json.loads(r.read())
    data['mods'] += newdata['mods']
print('done')
mods = data['mods']

## filter by game version
# get version list
versions = set((mod['gameVersion']['value'] for mod in mods))

# prompt the user for their version
print("versions:", "    ".join(versions))
while version not in versions:
    version = input("Enter version: ")
print(f'using version {version}')

# filter the data by the version
version_mods = [entry for entry in mods if entry['gameVersion']['value'] == version]
mod_dict = {mod['name']:mod for mod in version_mods}

## filter by mod
categories = {}
for mod in version_mods:
    category = mod['meta']['category']
    if category not in categories:
        categories[category] = {'mods':[], 'weight':0}
    categories[category]['mods'].append(mod)
    categories[category]['weight'] += mod['meta']['weight']

ordered_mods = []
print("mods:")
i = 1
for key, value in categories.items():
    print()
    print(key)
    for mod in value['mods']:
        ordered_mods.append(mod)
        print(f'{i}.\t{mod["name"]}')
        i += 1
print()

indices = input('Input mod numbers by space: ').split(' ')

## grab all selected mods and dependencies
selected_mods = {}
for modname in required_mods:
    selected_mods[modname] = mod_dict[modname]

conflicts = set()
for index in indices:
    try:
        index = int(index) - 1
        mod = ordered_mods[index]
    except (ValueError, IndexError):
        print(index, 'is not a valid index')
    else:
        # add the mod
        selected_mods[mod['name']] = mod
        # add dependencies
        for dependency in mod['links']['dependencies']:
            depname = dependency.split('@')[0]
            selected_mods[depname] = mod_dict[depname]
        # append conflicts
        for conflict in mod['links']['conflicts']:
            conflicts.add(conflict)
# check for conflicts
for conflict in conflicts:
    confname = conflict.split('@')[0]
    if confname in selected_mods.keys():
        raise KeyError(f"Conflict encountered: {conflict}")

## download mods
print(f'installing in "{installdir}"')
for mod in selected_mods.values():
    print(f"downloading {mod['name']}...")
    mod_url = mod['files']['steam']['url']

    req = urllib.request.Request(mod_url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    r = urllib.request.urlopen(req)
    data = r.read()
    bytestream = io.BytesIO(data)
    zip = zipfile.ZipFile(bytestream)
    zip.extractall(installdir)

    # set the creation date to the same as inside the zip
    for f in zip.infolist():
        name, date_time = f.filename, f.date_time
        date_time = time.mktime(date_time + (0, 0, -1))
        os.utime(os.path.join(installdir, name), (date_time, date_time))

## install mods
print("Patching...")
ipa_location = os.path.join(installdir, 'IPA.exe')
exe_location = os.path.join(installdir, 'Beat Saber.exe')
subprocess.run([ipa_location, exe_location])