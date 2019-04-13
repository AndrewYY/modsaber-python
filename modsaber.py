''' simple beatmods mod installer. run as admin if you need to. '''
import io
import json
import os
import subprocess
import time
import urllib.request
import winreg
import zipfile

# constants
beatmods_url = 'https://beatmods.com'
api_version = '1'
user_agent = 'beatmods-python/0.2.0'

## get the beat saber install directory
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Steam App 620980') as key:
    installdir = winreg.QueryValueEx(key, 'InstallLocation')[0]
try:
    version = open(os.path.join(installdir, 'BeatSaberVersion.txt')).read()
except:
    version = ''

## grab the mod database from the server

# build the url
req_url = f'{beatmods_url}/api/v{api_version}/mod?status=approved'

# make the web request
print("Fetching Mod Database")
req = urllib.request.Request(req_url)
req.add_header('User-Agent', user_agent)
r = urllib.request.urlopen(req)
mods = json.loads(r.read())
mod_dict = {mod['name']:mod for mod in mods}

## filter by mod
categories = {}
for mod in mods:
    category = mod['category']
    if category not in categories:
        categories[category] = {'mods':[]}
    categories[category]['mods'].append(mod)

ordered_mods = []
print("mods:")
i = 1
for key, value in categories.items():
    print()
    print(key)
    for mod in value['mods']:
        ordered_mods.append(mod)
        print(f'{i}.\t{mod["name"]}' + ('(required)' if mod['required'] else ''))
        i += 1
print()

indices = input('Input mod numbers by space: ').split(' ')

## grab all selected mods and dependencies
selected_mods = {key:value for key, value in mod_dict.items() if value['required']}

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
        for dependency in mod['dependencies']:
            depname = dependency['name']
            depver = dependency['version']
            selected_mods[depname] = mod_dict[depname]

print('downloading and installing:', list(selected_mods.keys()))
## download mods
print(f'installing in "{installdir}"')
for mod in selected_mods.values():
    print(f"downloading {mod['name']}...")
    mod_path = [download['url'] for download in mod['downloads'] if download['type'] in ['universal', 'steam']][0]
    req = urllib.request.Request(f'{beatmods_url}{mod_path}')
    req.add_header('User-Agent', user_agent)
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
