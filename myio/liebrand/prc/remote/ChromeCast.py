import threading
import time
from datetime import datetime

import pychromecast


class ChromeCast(threading.Thread):

    MEDIATYPE_MP4 = "video/mp4"
    MEDIATYPE_JPEG = "image/jpeg"

    def __init__(self):
        threading.Thread.__init__(self)
        self.friendlyName = ""
        self.mediaUrl = ""
        self.mediaType = ""
        self.log = None
        self.timeout = 60

    def run(self):
        self.log.info("[CAST] Starting to play media")
        start = datetime.now()
        chromecasts = pychromecast.get_chromecasts()
        try:
            cast = next(cc for cc in chromecasts if cc.device.friendly_name == self.friendlyName)

            cast.wait()
            mc = cast.media_controller
            mc.play_media(self.mediaUrl, self.mediaType)
            mc.block_until_active()
            mc.play()
            hasPlayed=False
            while mc.status.player_state != 'PLAYING' and (datetime.now() - start).seconds < self.timeout:
                time.sleep(4)
            if mc.status.player_state == 'PLAYING':
                hasPlayed = True
            while mc.status.player_state != 'IDLE' and (datetime.now() - start).seconds < self.timeout:
                time.sleep(1)
            cast.quit_app()
            if not hasPlayed:
                self.log.error("[CAST] Playing of media (%s) not successfull" % self.mediaUrl)
        except StopIteration:
            names = []
            for cc in chromecasts:
                names.append(cc.device.friendly_name)
            self.log.error("[CAST] Unable to match configured friendly name '%s' with available devices: %s" % (
                self.friendlyName, ",".join(names)
            ))

        self.log.info("[CAST] Finished with playing media")
