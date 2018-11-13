import json
import os
import sys
import tempfile
from datetime import datetime

import imageio as imageio


#
# jpgDir = files to process
# output = path & file to Store
# hours = number of past hours the animated gif should cover
# duration = time in seconds each frame should be shown (default = 1)
#

if __name__ == '__main__':
    paramFile = sys.argv[1]
    with open(paramFile) as f:
        params = json.load(f)
    os.remove(paramFile)
    print params
    duration = 1.0
    if 'duration' in params:
        duration = params['duration']
    ageLimit = params['hours'] * 3600
    now = datetime.now()
    fileNames = []
    for fileName in os.listdir(params['jpgDir']):
        if fileName.endswith(('.jpg', '.png', '.gif')):
            fullImagePath = os.path.join(params['jpgDir'], fileName)
            dt = datetime.strptime(fileName[:-4], '%Y%m%d-%H%M%S')
            age = (now - dt).seconds
            if age < ageLimit:
                fileNames.append(fullImagePath)
            else:
                os.remove(fullImagePath)
    if len(fileNames)> 0:
        fileNames.sort()

        images = list(map(lambda filename: imageio.imread(filename), fileNames))
        tmpFile = os.path.basename(tempfile.mktemp() + '.gif')
        path = os.path.dirname(params['output'])
        fulltmp = os.path.join(path, tmpFile)
        imageio.mimsave(fulltmp, images, duration=duration)
        os.rename(fulltmp, params['output'])
