import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime




#
# jpgDir = files to process
# output = path & file to Store
# hours = number of past hours the animated gif should cover
# duration = time in seconds each frame should be shown (default = 1)
#

if __name__ == '__main__':
    paramFile = sys.argv[1]
    with open(paramFile) as f:
        allParams = json.load(f)
    #os.remove(paramFile)
    print allParams
    for key in allParams.keys():
        params = allParams[key]
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
            tmpFile = os.path.basename(tempfile.mktemp() + '.mp4')
            path = os.path.dirname(params['output'])
            fulltmp = os.path.join(path, tmpFile)
            shellCmd = ["ffmpeg",
                        "-framerate %2.1f" % duration, "-pattern_type glob",  "-i '%s/*.jpg'" % params['jpgDir'],
                        "-pix_fmt yuv420p",
                        "-vcodec h264",
                        "-movflags frag_keyframe+empty_moov+default_base_moof+faststart+isml",
                        "%s" % fulltmp
                        ]
            shellCmd = " ".join(shellCmd)
            print shellCmd
            retVal = subprocess.call(shellCmd, shell=True)
            if os.path.exists(fulltmp) and os.stat(fulltmp).st_size>0:
                os.rename(fulltmp, params['output'])
