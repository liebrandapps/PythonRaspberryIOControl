from os.path import exists, join
import mimetypes

from myio.liebrand.prc.config import Config
from myio.liebrand.phd.handler import Handler




class PRCWebHandler(Handler):

    ENDPOINT = "/prcweb"

    def __init__(self, ctx):
        self.cfg = ctx.getConfig()
        self.log = ctx.getLogger()



    def endPoint(self):
        return([PRCWebHandler.ENDPOINT, "*"])

    def doGET(self, path, headers):
        self.log.debug(path)
        resultHeaders = {}
        resultCode = 404
        body = ""
        self.cfg.setSection(Config.SECTIONS[Config.WEB])
        webRoot = self.cfg.webRoot

        if PRCWebHandler.ENDPOINT in path:
            path = path.replace(PRCWebHandler.ENDPOINT, "")

        if len(path) == 0 or path == "/":
            script = self.cfg.default
        else:
            script = path
        if script.startswith("/"):
            script = script[1:]

        if ".." in script or "%" in script:
            resultCode = 403
        else:
            path = join(webRoot, script)
            if exists(path):
                body = open(path, 'r').read()
                tmp = mimetypes.guess_type(script)
                if tmp[0] is not None:
                    resultHeaders['Content-Type'] = tmp[0]
                resultCode = 200
            else:
                self.log.error("Could not find www file %s" % (path))
                resultCode = 500

        return [resultCode, resultHeaders, body]

    def doPOST(self, path, headers, body):
        self.log.debug("oops")
        return [404, {}, ""]


