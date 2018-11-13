import hashlib
import telnetlib


class Netio230Wrapper:

    def __init__(self):
        pass

    def _sendCommand(self, cmd, user, password, host, port):
        responseCode = ""
        responseText = ""
        tn = telnetlib.Telnet(host, port, 4)
        s = tn.read_until("\n")
        # self.debugInfo("-", s)
        if s[:3] == "100":
            hashval = s[10:18]
            dta = user + password + hashval
            m = hashlib.md5()
            m.update(dta)
            response = "clogin " + user + " " + m.hexdigest()
            tn.write(response + "\n")
            s = tn.read_until("\n")
            # self.debugInfo(response, s)
            if s[:3] == "250":
                response = cmd
                tn.write(response + "\n")
                s = tn.read_until("\n")
                # self.debugInfo(response, s)
                if s[:3] == "250":
                    responseText = s
                    tn.write("quit\n")
                    s = tn.read_until("\n")
                    responseCode = "ok"
                else:
                    responseText = "Unexpected response for command: <%s> Command was: %s" % (s, cmd)
                    responseCode = "fail"
            else:
                responseText = "Unexpected response while logging on: <%s> Username / Password were: %s %s" % (
                s, user, password)
                responseCode = "fail"
        else:
            responseText = "Unexpected response while contacting NETIO230: <%s> IP / Port were: %s %s" % \
                           (s, host, port)
            responseCode = "fail"
        tn.close()
        return [responseCode, responseText]

    #
    # accessId[0] = user
    # accessId[1] = password
    #
    # address[0] = host
    # address[1] = port
    # address[2] = plug
    #
    # return a tuple:
    # [0] - ok / fail
    # [1] on / off, if [0] == ok
    #
    def getStatus(self, accessId, address):
        result = "???"
        response = self._sendCommand("port " + address[2], accessId[0], accessId[1], address[0], address[1])
        if response[0] == 'ok' and len(response) > 0:
            if response[1][4:5] == "0":
                response[1] = "off"
            if response[1][4:5] == "1":
                response[1] = "on"
        return response

    #
    # accessId[0] = user
    # accessId[1] = password
    #
    # address[0] = host
    # address[1] = port
    # address[2] = plug
    #
    def turnOn(self, accessId, address):
        result = "???"
        response = self._sendCommand("port " + address[2] + " 1", accessId[0], accessId[1], address[0], address[1])
        if response[0] and len(response[1]) > 0:
            if response[1][4:6] == "OK":
                response[1] = "ok"
            else:
                response[1] = "fail"
        return response

    #
    # accessId[0] = user
    # accessId[1] = password
    #
    # address[0] = host
    # address[1] = port
    # address[2] = plug
    #
    def turnOff(self, accessId, address):
        result = "???"
        response = self._sendCommand("port " + address[2] + " 0", accessId[0], accessId[1], address[0], address[1])
        if response[0] and len(response[1]) > 0:
            if response[1][4:6] == "OK":
                response[1] = "ok"
            else:
                response[1] = "fail"
        return response