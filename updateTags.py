import warnings, os
from cryptography.utils import CryptographyDeprecationWarning
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', category=CryptographyDeprecationWarning)
    import pysftp #Version 0.2.8 Required

from dotenv import load_dotenv

load_dotenv()
HOSTNAME = os.getenv('HOSTNAME')
USERNAME = os.getenv('USERNAME')
PASSWORD = os.getenv('PASSWORD')
hostpath = os.getenv('HOSTPATH')
hostfile = os.getenv('HOSTFILE')
hostdir = hostpath + hostfile
localdir = './' + hostfile
outputFile = os.getenv('OUTPUTFILE')

def update_tags(to_insert_str):
    with pysftp.Connection(HOSTNAME, USERNAME, password = PASSWORD, port = 2022) as sftp:
        sftp.get(hostdir, localdir)

        f = open(localdir, 'r+')
        data = f.read()
        f.seek(0)

        #WHAT TO INSERT
        find_idx = to_insert_str.find('\"STEAM_0:0')
        if find_idx == -1:
            find_idx = to_insert_str.find('\"STEAM_0:1')

        find_insert = to_insert_str[find_idx:to_insert_str.find('//')].strip()
        to_insert_list = to_insert_str.split('\n')

        #EXISTING TAG
        if(data.find(find_insert) != -1):

            #WHERE TO INSERT
            insert_at_list = []
            found_insert = False

            for line in f:
                if found_insert:
                    insert_at_list.append(line)
                    if line.count('}') == 1 and line.count('{') == 0:
                        break
                elif find_insert in line:
                    found_insert = True
                    insert_at_list.append(line)

            #INSERTING
            if(len(insert_at_list) - 1 == len(to_insert_list)):
                insert_at_list[:-1] #In case input has extra whitespace

            for i, insert_here in enumerate(insert_at_list):
                if '\"namecolor\"' in insert_here:
                    continue
                if any(x.isalnum() for x in insert_here):
                    idx = data.find(insert_here)
                    data = data.replace(insert_here,'')
                    data = data[:idx] + to_insert_list[i] + '\n' + data[idx:]
        
            f.close()
        
        else: #NEW TAG
            to_insert_str = ''.join([i + '\n' for i in to_insert_list][:-1])
            idx = data.rfind('}')
            data = data[:idx] + to_insert_str + data[idx:] + '\n}'

        f = open(outputFile, 'w')
        f.write(data)
        f.close()

        sftp.cwd(hostpath)
        sftp.put(outputFile)
