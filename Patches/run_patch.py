import os
rootDir = os.path.dirname( os.path.abspath(__file__) )

# walk patch directory to get source file paths
source_list = []
for dirName, subdirList, fileList in os.walk(rootDir, topdown=False):
    if not dirName == rootDir and not '__pycache__' in dirName:
        if len(fileList):
            source_list += [dirName]

# iterate through source
for source in source_list:
    destination = source.replace('\Patches','')
    os.system("xcopy %s %s /s /y" % (source, destination))