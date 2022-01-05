import fileinput
import glob
import json
import os
import shutil
import sys

config_filepath = 'dag-templating/dag-config/'
dag_template_filename = 'dag-templating/dag-template.py'

for filename in os.listdir(config_filepath):
    f = open(config_filepath + filename)
    config = json.load(f)

    new_filename = 'dags/' + config['DagId'] + '.py'
    shutil.copyfile(dag_template_filename, new_filename)

    # Get a list of all the file paths that ends with .pyc from in specified directory
    fileList = glob.glob('dags/__pycache__/' + config['DagId'] + '*.pyc')

    for filePath in fileList:
        try:
            print('clean up cache: ' + filePath)
            os.remove(filePath)
        except:
            print("Error while deleting file : ", filePath)

    for line in fileinput.input(new_filename, inplace=1):
        line = line.replace("dag_id_replace", "'" + config['DagId'] + "'")
        line = line.replace("schedule_replace", "'" + config['Schedule'] + "'")
        line = line.replace("ve_replace", config['VE'])
        sys.stdout.write(line)
