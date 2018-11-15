
var MAX_SWITCH = 0;
var MAX_PEER = 3;
var MAX_FS20 = 0;
var MAX_NETIO = 0;
var MAX_ULTRASONIC = 3;
var MAX_TEMPERATURE = 0;
var MAX_HMS100T = 0;
var MAX_HMS100TF = 0;
var MAX_KSH300 = 0;
var MAX_FS20SENSOR = 0;
var MAX_CAMERA = 0;
var MAX_BMP180 = 0;
var MAX_AWNING = 0;
var MAX_RPICAM = 0;
var updateInProgress = false;
var url = "/prcapi"
var hostMap = {};
var localIdMap = {};
var pushMap = {};
var chartData;
var currentChart;
var menuSelected = false;
var popupIsShowing = false;
var historyRowCount = 0;
var offlineMode = false;



var clientId = null;
var publicKey = "";
var senderId = "";
var messaging = null;
var fcmUrl = "";

// Initialize the Firebase app in the service worker by passing in the
// messagingSenderId. - if we have the data in local storage
if (window.localStorage.getItem('publicKey')!=null) {
    publicKey = window.localStorage.getItem('publicKey');
    senderId = window.localStorage.getItem('senderId');
    fcmUrl = window.localStorage.getItem('fcmUrl');
    setupFCM(publicKey, senderId);
}


var hidden, visibilityChange;
if (typeof document.hidden !== "undefined") {
  hidden = "hidden";
  visibilityChange = "visibilitychange";
} else if (typeof document.msHidden !== "undefined") {
  hidden = "msHidden";
  visibilityChange = "msvisibilitychange";
} else if (typeof document.webkitHidden !== "undefined") {
  hidden = "webkitHidden";
  visibilityChange = "webkitvisibilitychange";
}

if (typeof document.addEventListener === "undefined" || typeof document[hidden] === "undefined") {
  		console.log("This app requires a browser, such as Google Chrome or Firefox, that supports the Page Visibility API.");
} else {
  		document.addEventListener(visibilityChange, handleVisibilityChange, false);
}

function openNav() {
    menuSelected = true;
    if (popupIsShowing) {
        popupIsShowing = false;
        document.getElementById("myPopup").classList.toggle("show");
    }
    document.getElementById("mySidenav").style.width = "400px";
}

/* Set the width of the side navigation to 0 */
function closeNav() {
    document.getElementById("mySidenav").style.width = "0";
    return false;
}

function initUI() {
    showArea('progress');
    clientId = window.localStorage.getItem('clientId');
    if(clientId === null) {
        clientId = ""
    }
    var locale = getLanguage();
    restoreHistory();
    var params = { "command" : "about", "locale" : locale, "clientId" : clientId };
    var completeUrl = url + formatParams(params)
    console.log(completeUrl)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send();
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {

                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                document.title = jsn.name;
                if(jsn.pushEnabled) {
                    window.localStorage.setItem('senderId', jsn.senderId);
                    window.localStorage.setItem('publicKey', jsn.publicKey);
                    window.localStorage.setItem('fcmUrl', jsn.fcmUrl);
                    fcmUrl = jsn.fcmUrl;
                    if(senderId == null || jsn.senderId!=senderId) {
                        senderId=jsn.senderId;
                        if(firebase.apps.length) {
                            firebase.app().delete().then(function() {
                                setupFCM(jsn.publicKey, jsn.senderId);
                            });
                        }
                        else {
                            setupFCM(jsn.publicKey, jsn.senderId);
                        }
                    }
                }
                else {
                    console.log("[FCM] Push Messages not enabled on server side");
                    document.getElementById('history').style.display = 'none';
                    document.getElementById('fcm_container').style.display = 'none';
                    document.getElementById('line_lastUpdateTime').style.display = 'none';
                }
                document.getElementById("txt_1").innerHTML = jsn.dictionary.txt_1 + '<span style="float:right;">' +
                                    jsn.dictionary.txt_2;
                document.getElementById("txt_2").innerHTML = jsn.dictionary.txt_1 + '<span style="float:right;">' +
                                    jsn.dictionary.txt_3;
                document.getElementById("txt_16").innerHTML = jsn.dictionary.txt_1 + '<span style="float:right;">' +
                                    jsn.dictionary.txt_16;
                document.getElementById("txt_4").innerHTML = jsn.dictionary.txt_4 + '<span style="float:right;">' +
                                    jsn.dictionary.txt_5;
                document.getElementById("txt_6").innerHTML = jsn.dictionary.txt_6 + '<span style="float:right;">' +
                                    jsn.dictionary.txt_7;
                for(i=8; i<16; i++) {
                    reference = "txt_" + String(i)
                    document.getElementById(reference).innerHTML = jsn.dictionary[reference]
                }
                document.getElementById("serverPID").innerHTML = jsn.pid;
                var tmp="";
                var cnt=0;
                if (jsn.uptime[0] !== 0) {
                    cnt=cnt+1;
                    tmp = jsn.uptime[0] + " days ";
                }
                if (jsn.uptime[1] !== 0) {
                    cnt=cnt+1;
                    tmp = tmp + jsn.uptime[1] + " hours ";
                }
                if (jsn.uptime[2] !== 0 && cnt < 2) {
                    cnt=cnt+1;
                    tmp = tmp + jsn.uptime[2] + " minutes ";
                }
                if (jsn.uptime[3] !== 0 && cnt < 2) {
                    cnt=cnt+1;
                    tmp = tmp + jsn.uptime[3] + " seconds";
                }
                document.getElementById("serverUptime").innerHTML = tmp;

                const arrId = [ "switchCount", "fs20Count", "ultrasonicCount", "temperatureCount", "netioCount",
                                "cameraCount", "rpicamCount", "hms100tCount", "hms100tfCount", "ksh300Count",
                                "fs20SensorCount", "bmp180Count", "awningCount" ];
                let arrCount = [jsn.switchCount, jsn.fs20Count, jsn.ultrasonicCount, jsn.temperatureCount,
                                jsn.netioCount, jsn.cameraCount, jsn.rpicamCount, jsn.hms100tCount, jsn.hms100tfCount,
                                jsn.ksh300Count, jsn.fs20SensorCount, jsn.bmp180Count, jsn.awningCount];
                let idx = 0;
                while(idx<arrId.length) {
                    jsn.address.forEach(server => {
                        arrCount[idx] += jsn[server][arrId[idx]];
                    });
                    idx += 1;
                }

                zip = (...rows) => [...rows[0]].map((_,c) => rows.map(row => row[c]));
                zip(arrCount, arrId).forEach(function(item) {
                    if(item[0] == 0) {
                        document.getElementById("line_" + item[1]).style.display = 'none';
                    }
                    else {
                        document.getElementById(item[1]).innerHTML = item[0];
                    }
                });

                if((jsn.address.length) == 0) {
                    document.getElementById("line_serverCount").style.display = 'none';
                }
                else {
                    document.getElementById("serverCount").innerHTML = jsn.address.length;
                }

                var html = document.getElementById("switch_TEMPLATE").innerHTML;
                for(i=0; i<arrCount[0]; i++) {
                    reference = "switch_"  + String(i+1);
                    const parent = document.getElementById((i<8)? "switch_container_left" : "switch_container_right")
                    parent.innerHTML += html.replace(/switch_ID/g, reference);
                }
                for(i=0; i<arrCount[1]; i++) {
                    reference = "fs20_"  + String(i+1);
                    const parent = document.getElementById((i<8)? "fs20_container_left" : "fs20_container_right")
                    parent.innerHTML += html.replace(/switch_ID/g, reference);
                }
                for(i=0; i<arrCount[4]; i++) {
                    reference = "netio_"  + String(i+1);
                    const parent = document.getElementById((i<8)? "netio_container_left" : "netio_container_right")
                    parent.innerHTML += html.replace(/switch_ID/g, reference);
                }
                html = document.getElementById("sensor_TEMPLATE").innerHTML;
                for(i=0; i<arrCount[3]; i++) {
                    reference = "temperature_"  + String(i+1);
                    const parent = document.getElementById((i<8)? "temperature_container_left" : "temperature_container_right")
                    parent.innerHTML += html.replace(/sensor_ID/g, reference);

                }
                for(i=0; i<arrCount[7]; i++) {
                    reference = "hms100t_"  + String(i+1);
                    const parent = document.getElementById("hms100t_container");
                    parent.innerHTML += html.replace(/sensor_ID/g, reference);
                }
                for(i=0; i<arrCount[8]; i++) {
                    reference = "hms100tf_"  + String(i+1);
                    const parent = document.getElementById("hms100tf_container");
                    parent.innerHTML += html.replace(/sensor_ID/g, reference);
                }
                for(i=0; i<arrCount[9]; i++) {
                    reference = "ksh300_"  + String(i+1);
                    const parent = document.getElementById("ksh300_container");
                    parent.innerHTML += html.replace(/sensor_ID/g, reference);
                }
                for(i=0; i<arrCount[11]; i++) {
                    reference = "bmp180_"  + String(i+1);
                    const parent = document.getElementById("bmp180_container");
                    parent.innerHTML += html.replace(/sensor_ID/g, reference);
                }
                html = document.getElementById("fs20Sensor_TEMPLATE").innerHTML;
                for(i=0; i<arrCount[10]; i++) {
                    reference = "fs20Sensor_" + String(i+1);
                    var parent = document.getElementById((i<8)? "fs20Sensor_container_left" : "fs20Sensor_container_right");
                    parent.innerHTML += html.replace(/fs20Sensor_ID/g, reference);
                }
                html = document.getElementById("awning_TEMPLATE").innerHTML;
                for(i=0; i<arrCount[12]; i++) {
                    reference = "awning_" + String(i+1);
                    var parent = document.getElementById("awning_container");
                    parent.innerHTML += html.replace(/awning_ID/g, reference);
                }

                showArea('about');
                var popup = document.getElementById("myPopup");
                setTimeout(function() {
                    if (!menuSelected) {
                        popup.classList.toggle("show");
                        popupIsShowing = true;
                        setTimeout(function() {
                            if (popupIsShowing) {
                                popupIsShowing = false;
                                popup.classList.toggle("show");
                            }
                        }, 12000);
                    }
                }, 10000);


            }
        }
    }
}

function showArea(areaId) {
    var areaIds = new Set();
    areaIds.add("switch");
    areaIds.add("fs20");
    areaIds.add("peer");
    areaIds.add("about");
    areaIds.add("ultrasonic");
    areaIds.add("temperature");
    areaIds.add("netio");
    areaIds.add("hms100t");
    areaIds.add("hms100tf");
    areaIds.add("ksh300");
    areaIds.add("fs20Sensor");
    areaIds.add("camera");
    areaIds.add("rpicam");
    areaIds.add("bmp180");
    areaIds.add("awning");
    areaIds.forEach(divId => {
        if (areaId === divId) {
            document.getElementById(divId).style.display = 'block';
        }
        else {
            document.getElementById(divId).style.display = 'none';
        }
    });
    closeNav();
}


function handleCheck(checkbox) {
    if(!updateInProgress) {
        var switchId;
        console.log(checkbox.checked);
        var value = "off"
        if(checkbox.checked == true) {
            value = "on";
        }
        var host = "";
        if(hostMap.hasOwnProperty(checkbox.name)) {
            host = hostMap[checkbox.name];
            switchId = localIdMap[checkbox.name];
        }
        else {
            switchId = checkbox.name
        };
        let timeStamp = window.performance.now().toString();
        let clientId = window.localStorage.getItem('clientId');
        let accessToken = window.localStorage.getItem('accessToken');
        const params = { command : "switch", id : switchId, value : value, host : host,
                        timeStamp : timeStamp, clientId : clientId };
        console.log(params);
        var completeUrl = url + formatParams(params);
        var http = new XMLHttpRequest();
        http.open('POST', url, true);
        http.setRequestHeader('Content-Type', 'application/json');
        http.setRequestHeader('fcm', offlineMode? 'yes' : 'no');
        if(accessToken !== null) {
            http.setRequestHeader('accessToken', accessToken);
            http.setRequestHeader('fcmUrl', fcmUrl);
            http.setRequestHeader('payload', JSON.stringify(params));
        }
        http.send(JSON.stringify(params))
        http.onreadystatechange = function() {
            if(this.readyState == 4) {
                if(this.status==202) {
                    console.log("Not checking status, as we send the request through FCM");
                }
                else {
                    //console.log("Done with Switch - now check, if it really switched");
                    refreshSwitchValue(checkbox.name);
                }
            }
        }
    }
}

function refreshSwitchValue(switchId) {
    var host = "";
    if(hostMap.hasOwnProperty(switchId)) {
        host = hostMap[switchId];
        switchId = localIdMap[switchId];
    };
    var params = { command : "status", id : switchId, host : host };
    //console.log(params);
    var completeUrl = url + formatParams(params)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Content-Type', 'application/json');
    http.send(JSON.stringify(params))
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn);
                if(jsn.status === 'ok') {
                    if(jsn[switchId].status === "on") {
                        document.getElementById(switchId + "_check").checked = true;
                    }
                    else {
                        document.getElementById(switchId + "_check").checked = false;
                    }
                }
            }
        }
    }
}

function requestConfig() {
    var locale = getLanguage();
    var params = { "command" : "config", "locale" : locale, "roaming" : "yes" };
    var completeUrl = url + formatParams(params)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send()
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                if(jsn.status === 'ok') {
                    hostMap = {};
                    localIdMap = {};
                    var cnt = jsn.peerCount;
                    for(i=0; i<MAX_PEER; i++) {
                        reference = "peer_" + String(i+1);
                        if(i<cnt) {
                            document.getElementById(reference).style.display = 'inline-block';
                            document.getElementById(reference + "_btn").innerHTML = jsn[reference].name
                            document.getElementById(reference + "_btn").setAttribute("onclick", "location.href='" + jsn[reference].address + "';" );
                        }
                        else {
                            document.getElementById(reference).style.display = 'none';
                        }
                    }
                    MAX_SWITCH = jsn.switchCount;
                    if(MAX_SWITCH==0) {
                        document.getElementById("switch").style.display = 'none';
                        document.getElementById("txt_1").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_SWITCH; i++) {
                            var reference = "switch_"  + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            updateSwitch(reference, jsn[reference].name, jsn[reference].status);
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {};
                            map['docId'] = reference;
                            map['docType'] = 'S';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_FS20 = jsn.fs20Count;
                    if(MAX_FS20==0) {
                        document.getElementById("fs20").style.display = 'none';
                        document.getElementById("txt_2").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_FS20; i++) {
                            reference = "fs20_"  + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            updateSwitch(reference, jsn[reference].name, jsn[reference].status);
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {};
                            map['docId'] = reference;
                            map['docType'] = 'F';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_NETIO = jsn.netioCount;
                    if(MAX_NETIO==0) {
                        document.getElementById("netio").style.display = 'none';
                        document.getElementById("txt_16").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_NETIO; i++) {
                            reference = "netio_"  + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            updateSwitch(reference, jsn[reference].name, jsn[reference].status);
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {};
                            map['docId'] = reference;
                            map['docType'] = 'N';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    cnt = jsn.ultrasonicCount;
                    if(cnt==0) {
                        document.getElementById("ultrasonic").style.display = 'none';
                        document.getElementById("txt_4").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_ULTRASONIC; i++) {
                            reference = "ultrasonic_"  + String(i+1);
                            if(i<cnt) {
                                document.getElementById(reference).style.display = 'block';
                                updateUltrasonic(reference, jsn[reference].name, jsn[reference].value,
                                            jsn[reference].min, jsn[reference].max, jsn[reference].inverse);
                                document.getElementById(reference + "_meter").min = jsn[reference].min;
                                document.getElementById(reference + "_meter").max = jsn[reference].max;
                                hostMap[reference] = jsn[reference].host;
                                localIdMap[reference] = jsn[reference].localId;
                                var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                                var map = {};
                                map['docId'] = reference;
                                map['docType'] = 'U';
                                map['name'] = jsn[reference].name;
                                map['min'] = jsn[reference].min;
                                map['max'] = jsn[reference].max;
                                map['inverse'] = jsn[reference].inverse;
                                pushMap[pushKey] = map;
                            }
                            else {
                                document.getElementById(reference).style.display = 'none';
                            }
                        }
                    }
                    MAX_TEMPERATURE = jsn.temperatureCount;
                    if(MAX_TEMPERATURE==0) {
                        document.getElementById("temperature").style.display = 'none';
                        document.getElementById("txt_6").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_TEMPERATURE; i++) {
                            reference = "temperature_"  + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            update18B20(reference, jsn[reference].name, jsn[reference].value);
                            document.getElementById(reference + "_meter").min = jsn[reference].min;
                            document.getElementById(reference + "_meter").max = jsn[reference].max;
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = 'T';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_HMS100T = jsn.hms100tCount;
                    if(MAX_HMS100T==0) {
                        document.getElementById("hms100t").style.display = 'none';
                        document.getElementById("txt_17").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_HMS100T; i++) {
                            reference = "hms100t_" + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML = jsn[reference].name
                            var fltValue=parseFloat(jsn[reference].value);
                            document.getElementById(reference + "_label").innerHTML=jsn[reference].name + ": " +
                                    fltValue.toFixed(1) + " C";
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = '100T';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                     }
                    MAX_HMS100TF = jsn.hms100tfCount;
                    if(MAX_HMS100TF==0) {
                        document.getElementById("hms100tf").style.display = 'none';
                        document.getElementById("txt_18").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_HMS100TF; i++) {
                            reference = "hms100tf_" + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML=jsn[reference].name + ": " +
                                    jsn[reference].value;
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = '100TF';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_KSH300 = jsn.ksh300Count;
                    if(MAX_KSH300==0) {
                        document.getElementById("ksh300").style.display = 'none';
                        document.getElementById("txt_19").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_KSH300; i++) {
                            reference = "ksh300_" + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML=jsn[reference].name + ": " +
                                    jsn[reference].value;
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = 'K';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_FS20SENSOR = jsn.fs20SensorCount;
                    if(MAX_FS20SENSOR==0) {
                        document.getElementById("fs20Sensor").style.display = 'none';
                        document.getElementById("txt_20").style.display = 'none';
                    }
                    else {
                        var html = document.getElementById("fs20Sensor_TEMPLATE").innerHTML;
                        for(i=0; i<MAX_FS20SENSOR; i++) {
                            reference = "fs20Sensor_" + String(i+1);
                            var parent = document.getElementById((i<8)? "fs20Sensor_container_left" : "fs20Sensor_container_right")
                            parent.innerHTML += html.replace(/fs20Sensor_ID/g, reference);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML = jsn[reference].name
                            document.getElementById(reference + "_value").innerHTML = jsn[reference].value
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = 'FS';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_CAMERA = jsn.cameraCount;
                    if(MAX_CAMERA==0) {
                        document.getElementById("camera").style.display = 'none';
                        document.getElementById("txt_26").style.display = 'none';
                    }
                    else {
                        var html = document.getElementById("camera_TEMPLATE").innerHTML;
                        for(i=0; i<MAX_CAMERA; i++) {
                            var reference = "camera_"  + String(i+1);
                            var parent = document.getElementById("camera_container");
                            parent.innerHTML += html.replace(/camera_ID/g, reference);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML = jsn[reference].name
                            var map = {}
                            if(!jsn[reference].canStream) {
                                document.getElementById(reference + "_live").style.display = 'none';
                            }
                            if(!jsn[reference].canTimelapse) {
                                document.getElementById(reference + "_timelapse").style.display = 'none';
                            }
                            else {
                                map['timelapseMP4'] = jsn[reference].timelapseMP4;
                                map['timelapseCodec'] = jsn[reference].timelapseCodec;
                            }
                            map['host'] = jsn[reference].host;
                            map['localId'] = jsn[reference].localId;
                            hostMap[reference] = map;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            map = {};
                            map['docId'] = reference;
                            map['docType'] = 'C';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                         }
                    }
                    MAX_RPICAM = jsn.rpicamCount;
                    if(MAX_RPICAM==0) {
                        document.getElementById("rpicam").style.display = 'none';
                        document.getElementById("txt_28").style.display = 'none';
                    }
                    else {
                        var html = document.getElementById("camera_TEMPLATE").innerHTML;
                        for(i=0; i<MAX_RPICAM; i++) {
                            var reference = "rpicam_"  + String(i+1);
                            var parent = document.getElementById("rpicam_container");
                            parent.innerHTML += html.replace(/camera_ID/g, reference);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML = jsn[reference].name
                            var map = {}
                            if(!jsn[reference].canStream) {
                                document.getElementById(reference + "_live").style.display = 'none';
                            }
                            if(!jsn[reference].canTimelapse) {
                                document.getElementById(reference + "_timelapse").style.display = 'none';
                            }
                            else {
                                map['timelapseMP4'] = jsn[reference].timelapseMP4;
                                map['timelapseCodec'] = jsn[reference].timelapseCodec;
                            }
                            map['host'] = jsn[reference].host;
                            map['localId'] = jsn[reference].localId;
                            hostMap[reference] = map;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            map = {};
                            map['docId'] = reference;
                            map['docType'] = 'C';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                         }
                    }
                    MAX_BMP180 = jsn.bmp180Count;
                    if(MAX_BMP180==0) {
                        document.getElementById("bmp180").style.display = 'none';
                        document.getElementById("txt_31").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_BMP180; i++) {
                            reference = "bmp180_" + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML=jsn[reference].name + ": " +
                                    jsn[reference].value;
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = 'BMP180';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                    MAX_AWNING = jsn.awningCount;
                    if(MAX_AWNING==0) {
                        document.getElementById("awning").style.display = 'none';
                        document.getElementById("txt_33").style.display = 'none';
                    }
                    else {
                        for(i=0; i<MAX_AWNING; i++) {
                            reference = "awning_" + String(i+1);
                            document.getElementById(reference).style.display = 'block';
                            document.getElementById(reference + "_label").innerHTML=jsn[reference].name;
                            hostMap[reference] = jsn[reference].host;
                            localIdMap[reference] = jsn[reference].localId;
                            var pushKey = jsn[reference].serverId + '_' + jsn[reference].localId;
                            var map = {}
                            map['docId'] = reference;
                            map['docType'] = 'AWNING';
                            map['name'] = jsn[reference].name;
                            pushMap[pushKey] = map;
                        }
                    }
                }
                else {
                    document.getElementById("progress_label").innerHTML = "Loading data from server failed.";
                }
            }
        }
    };
}

function handleRefresh() {
    var locale = getLanguage();
    var params = { "command" : "refresh", "locale" : locale, "roaming" : "yes" };
    var completeUrl = url + formatParams(params)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Accept', 'application/json');
    http.send()
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn)
                if(jsn.status === 'ok') {
                    for(i=0; i<MAX_SWITCH; i++) {
                        reference = "switch_"  + String(i+1);
                        if(i<jsn.switchCount) {
                            if(jsn[reference].status === "on") {
                                document.getElementById(reference + "_check").checked = true;
                            }
                            else {
                                document.getElementById(reference + "_check").checked = false;
                            }
                        }
                        else {
                            break;
                        }
                    }
                    for(i=0; i<MAX_FS20; i++) {
                        reference = "fs20_"  + String(i+1);
                        if(i<jsn.fs20Count) {
                            if(jsn[reference].status === "on") {
                                document.getElementById(reference + "_check").checked = true;
                            }
                            else {
                                document.getElementById(reference + "_check").checked = false;
                            }
                        }
                        else {
                            break;
                        }
                    }
                    for(i=0; i<MAX_NETIO; i++) {
                        reference = "netio_"  + String(i+1);
                        if(jsn[reference].status === "on") {
                            document.getElementById(reference + "_check").checked = true;
                        }
                        else {
                            document.getElementById(reference + "_check").checked = false;
                        }
                    }
                    for(i=0; i<MAX_ULTRASONIC; i++) {
                        reference = "ultrasonic_"  + String(i+1);
                        if(i<jsn.ultrasonicCount) {
                            updateUltrasonic(reference, jsn[reference].name, jsn[reference].value,
                                        jsn[reference].min, jsn[reference].max, jsn[reference].inverse);
                        }
                        else {
                            break;
                        }
                    }
                    for(i=0; i<MAX_TEMPERATURE; i++) {
                        reference = "temperature_"  + String(i+1);
                        update18B20(reference, jsn[reference].name, jsn[reference].value);
                    }
                    for(i=0; i<MAX_BMP180; i++) {
                        reference = "bmp180_"  + String(i+1);
                        document.getElementById(reference + "_label").innerHTML=jsn[reference].name + ": " +
                                    jsn[reference].value;
                    }

                }
            }
        }
    }
}

function requestHistory(sensorId) {
    currentChart = sensorId + "_chart";
    var host = "";
    if(hostMap.hasOwnProperty(sensorId)) {
        host = hostMap[sensorId];
        sensorId = localIdMap[sensorId];
    };
    const params = { command : "history24", id : sensorId, host : host };
    //console.log(params);
    var http = new XMLHttpRequest();
    http.open('POST', url, true);
    http.setRequestHeader('Content-Type', 'application/json');
    http.send(JSON.stringify(params))
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText)
                console.log(jsn);
                chartData = jsn[sensorId];
                google.charts.load('current', {'packages':['corechart']});
                if(sensorId.startsWith('ksh300') || sensorId.startsWith('hms100tf')) {
                    google.charts.setOnLoadCallback(onChartLoaded2);
                }
                else if (sensorId.startsWith('hms100t')) {
                    google.charts.setOnLoadCallback(onChartLoaded3);
                }
                else if (sensorId.startsWith('bmp180')) {
                    google.charts.setOnLoadCallback(onChartLoaded4);
                }
                else {
                    google.charts.setOnLoadCallback(onChartLoaded);
                }
            }
        }
    }
}


function onChartLoaded() {
    console.log(chartData);
    console.log(currentChart);
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Time');
    data.addColumn('number', 'Value');
    data.addRows(chartData);
    var options = {
          title: '24h Temperature History',
          curveType: 'function',
          legend: { position: 'bottom' }
        };
        document.getElementById(currentChart + 'canvas').style.display = 'block';
    var chart = new google.visualization.LineChart(document.getElementById(currentChart));
    chart.draw(data, options);
}

function onChartLoaded2() {
        var data = new google.visualization.DataTable();
        data.addColumn('number', 'Past Hours');
        data.addColumn('number', 'Temperature');
        data.addColumn('number', 'Humidity');
        data.addRows(chartData);

        var options = {
          theme: 'material',
          title: '24h Temperature History',
          curveType: 'function',
          lineWidth: 6,
          hAxis: {title: 'Past Hours', minValue: -24, maxValue: 0},
          vAxes: {0: {title: 'Temperature', minValue: 0, maxValue: 18},
                  1: {title: 'Humidity', minValue:0, maxValue: 100} },
          series: {0: {targetAxisIndex:0},
                   1:{targetAxisIndex:1} },
          legend: 'bottom'
        };
        document.getElementById(currentChart + 'canvas').style.display = 'block';
        var chart = new google.visualization.LineChart(document.getElementById(currentChart));
        chart.draw(data, options);

}

function onChartLoaded3() {
        var data = new google.visualization.DataTable();
        data.addColumn('number', 'Past Hours');
        data.addColumn('number', 'Temperature');
        data.addRows(chartData);

        var options = {
          theme: 'material',
          title: '24h Temperature History',
          curveType: 'function',
          lineWidth: 6,
          hAxis: {title: 'Past Hours', minValue: -24, maxValue: 0},
          vAxes: {0: {title: 'Temperature', minValue: 0, maxValue: 18}
                   },
          series: {0: {targetAxisIndex:0} },
          legend: 'bottom'
        };
        document.getElementById(currentChart + 'canvas').style.display = 'block';
        var chart = new google.visualization.LineChart(document.getElementById(currentChart));
        chart.draw(data, options);

}

function onChartLoaded4() {
        var data = new google.visualization.DataTable();
        data.addColumn('string', 'Time');
        data.addColumn('number', 'Temperature');
        data.addColumn('number', 'Air Pressure (hPa)');
        data.addRows(chartData);

        var options = {
          theme: 'material',
          title: '24h Temperature / Air Pressure History',
          curveType: 'function',
          lineWidth: 6,
          hAxis: {title: 'Past Time'},
          vAxes: {0: {title: 'Temperature', minValue: -5, maxValue: 35},
                  1: {title: 'Air Pressure', minValue:900, maxValue: 1100} },
          series: {0: {targetAxisIndex:0},
                   1:{targetAxisIndex:1} },
          legend: 'bottom'
        };
        document.getElementById(currentChart + 'canvas').style.display = 'block';
        var chart = new google.visualization.LineChart(document.getElementById(currentChart));
        chart.draw(data, options);

}


function hideChartCanvas(canvasId) {
    document.getElementById(canvasId).style.display = 'none';
}

function setLanguage(locale) {
    window.localStorage.setItem("locale", locale);
    initUI();
    requestConfig();
    return false;
}

function getLanguage() {
    var locale = window.localStorage.getItem("locale");
    if(locale==null) {
        locale = "en"
    }
    return locale;
}


function setupFCM(publicKey, senderId) {
    if(!firebase.apps.length) {
        console.log("FB Init")
        firebase.initializeApp({
            'messagingSenderId': senderId
        });
    }
    messaging = firebase.messaging();
    messaging.usePublicVapidKey(publicKey);

    messaging.getToken().then(function(currentToken) {

      if (currentToken) {
        sendTokenToServer(currentToken);
        //updateInProgress = true;
        //document.getElementById("fcmStatus_check").checked = true;
        //updateInProgress = false;
      } else {
        // Show permission request.
        console.log('[FCM] No Instance ID token available.');
        updateInProgress = true;
        document.getElementById("fcm_1_check").checked = false;
        updateInProgress = false;
        setTokenSentToServer(false);
      }
    }).catch(function(err) {
      console.log('[FCM] An error occurred while retrieving token. ', err);
      //showToken('Error retrieving Instance ID token. ', err);
      setTokenSentToServer(false);
    });

   messaging.onTokenRefresh(function() {
        messaging.getToken().then(function(refreshedToken) {
            console.log('[FCM] Token refreshed.');
            setTokenSentToServer(false);
            sendTokenToServer(refreshedToken);
        }).catch(function(err) {
            console.log('[FCM] Unable to retrieve refreshed token ', err);
        });
    });


    messaging.onMessage(function(payload) {
        if(payload.data.hasOwnProperty('envelope')) {
            payload.data = JSON.parse(atob(payload.data.envelope));
        }
        console.log('Message received. ', payload);
        var jsn = JSON.parse(JSON.stringify(payload));
        var msgType = jsn.data.msgType;
        if(msgType === 'evtAction') {
            let params = atob(payload.data.params);
            console.log(params);
            if (params.clientId === window.localStorage.getItem('clientId')) {
                console.log("Received own message - skipping.")
                return;
            }
            fetch(payload.data.targetUrl, {
                method: 'post',
                headers: {
                    "Content-type": "application/json",
                    "fcm" : "no"
                },
                body: params
            })
            .then(function (data) {
                    console.log('Request succeeded with JSON response', data);
                    addToHistory("action", (new Date()).toLocaleString(), "N/A", "Proxied switch request");
            })
            .catch(function (error) {
                console.log('Request failed', error);
            });
        }
        else {
            var serverId = jsn.data.serverId;
            var sensCount = 0;
            var actCount = 0;
            Object.keys(jsn.data).forEach(function(key) {
                if(key !== 'serverId') {
                    if(msgType === 'evtUpdate') {
                        updateEntity(serverId, key, jsn.data[key].value);
                    }
                    else {
                        updateEntity(serverId, key, jsn.data[key]);
                    }
                }
            });
            document.getElementById('lastUpdateTime').innerHTML = '[' + serverId + '] ' + new Date().toLocaleString();
            addToHistory(msgType === 'regUpdate' ? "regular" : "event", new Date().toLocaleString(),
                            serverId, String(sensCount) + " Sensors and " + String(actCount) + " Actors updated");
            if(jsn.data.hasOwnProperty('accessToken')) {
                window.localStorage.setItem('accessToken', jsn.data.accessToken);
            }
        }
    });
}


function handleFCM(checkbox) {
    if(!updateInProgress) {
        if(checkbox.id === 'fcm_1_check') {
            if (checkbox.checked === true) {
                messaging.requestPermission().then(function() {
                    console.log('[FCM] Notification permission granted.');
                    messaging.getToken().then(function(newToken) {
                        console.log('[FCM] Token received');
                        setTokenSentToServer(false);
                        sendTokenToServer(newToken);
                    }).catch(function(err) {
                        console.log('[FCM] Unable to retrieve new token ', err);
                        });
                }).catch(function(err) {
                    console.log('[FCM] Unable to get permission to notify.', err);
                });
            }
            else {
                messaging.getToken().then(function(currentToken) {
                    messaging.deleteToken(currentToken).then(function() {
                    console.log('[FCM] Token deleted.');
                    setTokenSentToServer(false);
                    sendTokenToServer("");
            }).catch(function(err) {
                console.log('[FCM] Unable to delete token. ', err);
          });
        }).catch(function(err) {
          console.log('[FCM] Error retrieving Instance ID token. ', err);
        });
            };

        }
        if(checkbox.id === 'fcm_2_check') {
            offlineMode = checkbox.checked;
            console.log('Offline Mode?' + offlineMode.toString());
        }
    }
}

function isTokenSentToServer() {
    return window.localStorage.getItem('sentToServer') === '1';
}

function setTokenSentToServer(sent) {
    window.localStorage.setItem('sentToServer', sent ? '1' : '0');
}

function sendTokenToServer(currentToken) {
    if (!isTokenSentToServer()) {
        console.log('[FCM] Sending token to server...');
        var clientId = window.localStorage.getItem('clientId')
        if(clientId === null) {
            clientId = ""
        }
        var params = { "command" : "fcmToken", "token" : currentToken , "clientId" : clientId };
        console.log(params);
        var completeUrl = url + formatParams(params);
        var http = new XMLHttpRequest();
        http.open('GET', completeUrl, true);
        http.setRequestHeader('Content-Type', 'application/json');
        http.send(JSON.stringify(params));
        http.onreadystatechange = function() {
            if(this.readyState == 4) {
                if(this.status == 200) {
                    var jsn = JSON.parse(this.responseText)
                    if(jsn.status === "ok") {
                        setTokenSentToServer(true);
                        window.localStorage.setItem("clientId", jsn.clientId)
                    }
                    else {
                        setTokenSentToServer(false);
                    }
                }
            }
        };

    } else {
      console.log('[FCM] Token already sent to server so won\'t send it again ' +
          'unless it changes');
          updateInProgress = true;
          document.getElementById("fcm_1_check").checked = true;
          updateInProgress = false;
    }
}


//
// https://stackoverflow.com/questions/8064691/how-do-i-pass-along-variables-with-xmlhttprequest
//
function formatParams( params ){
  return "?" + Object
        .keys(params)
        .map(function(key){
          return key+"="+encodeURIComponent(params[key])
        })
        .join("&")
}

function updateEntity(serverId, entityId, value) {
    var fullKey = serverId + '_' + entityId;
    if(pushMap.hasOwnProperty(fullKey)) {
        map = pushMap[fullKey];
        docId = map['docId'];
        docType = map['docType'];
        name = map['name'];
        if(docType === 'T') {
            update18B20(docId, name, value);
        }
        if(docType === 'U') {
            updateUltrasonic(docId, name, value, map['min'], map['max'], map['inverse']);
        }
        if((docType === 'S') || (docType === 'F') || (docType === 'N')) {
            updateSwitch(docId, name, value);
        }
    }
}


function update18B20(docId, name, value) {
    var before = document.getElementById(docId + "_label").innerHTML;
    var fltValue=parseFloat(value);
    document.getElementById(docId + "_label").innerHTML=name + ": " +
                                    fltValue.toFixed(1) + " C";
    document.getElementById(docId + "_meter").value = fltValue;
    var after = document.getElementById(docId + "_label").innerHTML;
    console.log(before + " -> " + after);
}

function updateUltrasonic(docId, name, value, min, max, inverse) {
    var fltValue=parseFloat(value);
    var fltMax=parseFloat(max);
    var fltMin=parseFloat(min);
    var fltMeterValue = fltValue;
    if(inverse) {
        fltValue = fltMax - fltValue;
        fltMeterValue = fltMin + fltValue;
    }
    document.getElementById(docId + "_label").innerHTML=name + " [" + fltValue.toFixed(0) + "cm]";
    document.getElementById(docId + "_meter").value = fltMeterValue;
}

function updateSwitch(docId, name, status) {
    document.getElementById(docId + "_label").innerHTML=name;
    if(status === "on") {
        document.getElementById(docId + "_check").checked = true;
    }
    else {
        document.getElementById(docId + "_check").checked = false;
    }
}


function handleVisibilityChange() {
    if (document[hidden]) {
        //console.log("Going into background");
    } else {
        console.log("Going into foreground, going to fetch background updates");
        var http = new XMLHttpRequest();
        http.open('GET', 'localcache?get=regUpdate', true);
        http.send();
        http.onreadystatechange = function() {
            if(this.readyState == 4) {
                if(this.status == 200) {
                    var jsn = JSON.parse(this.responseText);
                    if(jsn.hasOwnProperty('data') && jsn.data === 'none') {
                        //console.log("no background updates");
                    }
                    else {
                        console.log(jsn);
                        var updateTimes = "";
                        var lastServerId = "";
                        var lastUpdate = null;
                        var accessToken = null;
                        Object.keys(jsn).forEach(function(serverId) {
                            Object.keys(jsn[serverId].data).forEach(function(entityId) {
                                if (entityId !== 'serverId' && entityId !== 'msgType' && entityId !== 'timeStamp'
                                    && entityId !== 'accessToken') {
                                    updateEntity(serverId, entityId, jsn[serverId].data[entityId]);
                                }
                                if (entityId==='timeStamp') {
                                    var curUpdate = new Date(parseInt(jsn[serverId].data.timeStamp));
                                    if(lastUpdate == null || lastUpdate<curUpdate) {
                                        lastUpdate = curUpdate
                                        lastServerId = serverId;
                                    }
                                }
                                if(entityId === 'accessToken') {
                                    accessToken = jsn[serverId].data.accessToken;
                                }
                            });
                        });
                        updateTimes = updateTimes + '[' + lastServerId + '] ' + lastUpdate + ' ';
                        document.getElementById('lastUpdateTime').innerHTML = updateTimes;
                        addToHistory("regular", lastUpdate, lastServerId, updateTimes);
                        if(accessToken!=null) {
                            window.localStorage.setItem('accessToken', accessToken);
                        }
                    }
                }
            }
        };
        var http2 = new XMLHttpRequest();
        http2.open('GET', 'localcache?get=evtUpdate', true);
        http2.send();
        http2.onreadystatechange = function() {
            if(this.readyState == 4) {
                if(this.status == 200) {
                    var jsn = JSON.parse(this.responseText);
                    if(jsn.hasOwnProperty('data') && jsn.data === 'none') {
                        //console.log("no background updates");
                    }
                    else {
                        console.log(jsn);
                        var updateTimes = "";
                        var lastServerId = "";
                        var lastUpdate = null;
                        Object.keys(jsn).forEach(function(serverId) {
                            Object.keys(jsn[serverId]).forEach(function(timeStamp) {
                                Object.keys(jsn[serverId][timeStamp].data).forEach(function(entityId) {
                                    updateEntity(serverId, entityId, jsn[serverId][timeStamp].data[entityId].value);
                                } );

                                curUpdate = new Date(parseInt(jsn[serverId][timeStamp].data.timeStamp))
                                if(lastUpdate == null || lastUpdate<curUpdate) {
                                    lastUpdate = curUpdate
                                    lastServerId = serverId;
                                }
                                updateTimes = updateTimes + '[' + serverId + '] ' + jsn[serverId].rcvTime + ' ';
                            } );
                        } );
                        document.getElementById('lastUpdateTime').innerHTML = updateTimes;
                        addToHistory("event", lastUpdate, lastServerId, updateTimes);
                    }
                }
            }
        }
    }
}

function showSnapshot(camId) {
    hideVideo(camId);
     var host = "";
     var localId = camId;
     if(hostMap.hasOwnProperty(camId)) {
        host = hostMap[camId]['host'];
        localId = hostMap[camId]['localId'];
     }

    const params = { command : "snapshot", id : localId, host : host };
    console.log(params);
    var completeUrl = url + formatParams(params)
    var http = new XMLHttpRequest();
    http.open('GET', completeUrl, true);
    http.setRequestHeader('Content-Type', 'application/json');
    http.send(JSON.stringify(params))
    http.onreadystatechange = function() {
        if(this.readyState == 4) {
            if(this.status == 200) {
                var jsn = JSON.parse(this.responseText);
                if(jsn.status === 'ok') {
                    const img = document.getElementById(camId + "_picturesource");
                    img.setAttribute('src', 'data:image/png;base64,' + jsn.data);
                    document.getElementById(camId + '_picture').style.display = 'block';
                }
                else {
                    console.log(jsn.message);
                }
            }
        }
    }
}

function hideSnapshot(camId) {
    document.getElementById(camId + '_picture').style.display = 'none';
}

function hideVideo(camId) {
    document.getElementById(camId + '_video').style.display = 'none';
}
myMediaSource = new MediaSource();

function showTimeLapse(camId) {
    hideSnapshot(camId);
    document.getElementById(camId + "_video").style.display = 'block';
    const videoTag = document.getElementById("camera_1_videosource");
    const codec = hostMap[camId]['timelapseCodec'];
    const mp4Source = hostMap[camId]['timelapseMP4'];
    playMP4(camId, mp4Source, codec);
}

function showLiveStream(camId) {
    hideSnapshot(camId);
    document.getElementById(camId + "_video").style.display = 'block';
    const videoTag = document.getElementById("camera_1_videosource");
    console.log("z")
    // creating the MediaSource, just with the "new" keyword, and the URL for it
    //var mimeCodec = 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"';
    //var mimeCodec = 'video/mp4; codecs="avc1.640028"';
    var mimeCodec = 'video/mp4; codecs="avc1.64002a"';
    //var mimeCodec = 'video/mp4; codecs="avc1.4d4028, mp4a.40.2"';
    console.log(MediaSource.isTypeSupported(mimeCodec))
    //const myMediaSource = new MediaSource();
    const vurl = URL.createObjectURL(myMediaSource);

    // attaching the MediaSource to the video tag
    videoTag.src = vurl;
    videoTag.style.display = 'block';
    //videoTag.autoPlay = true;

    myMediaSource.addEventListener('sourceopen', function(e) {
        console.log(myMediaSource.readyState);
        var assetUrl = "/s.mp4"
        var videoSourceBuffer = myMediaSource.addSourceBuffer(mimeCodec);

        fetchArrayBuffer(assetUrl, function(buffer) {
            videoSourceBuffer.addEventListener('updateend', function (_) {
                console.log(myMediaSource.readyState);
                //myMediaSource.endOfStream();
                //var p = videoTag.play();

                // In browsers that don’t yet support this functionality,
                // playPromise won’t be defined.
                if (false && p !== undefined) {
                    p.then(function() {
                        // Automatic playback started!
                    }).catch(function(error) {
                        console.log(error);
                        // Automatic playback failed.
                        // Show a UI element to let the user manually start playback.
                    } );
                }
            });
            videoSourceBuffer.appendBuffer(buffer);
            //videoSourceBuffer.appendBuffer(new Uint8Array(buffer));
            //console.log(myMediaSource.readyState);
            //myMediaSource.endOfStream();
            //var p =videoTag.play();
        }
        );

/*
        fetch("https://192.168.0.196:8020/output1.mp4").then(function(response) {
        console.log("x");
        console.log(response);
        // The data has to be a JavaScript ArrayBuffer
        return response.arrayBuffer();
        }).then(function(videoData) {
            console.log('a');
            console.log(videoData);
            videoSourceBuffer.appendBuffer(videoData);

        }); */
    });

    /*
    videoTag.addEventListener('loadeddata', function() {
        console('b');
        var p = videoTag.play();

        // In browsers that don’t yet support this functionality,
        // playPromise won’t be defined.
        if (p !== undefined) {
                p.then(function() {
                    // Automatic playback started!
                }).catch(function(error) {
                    console.log(error);
                    // Automatic playback failed.
                    // Show a UI element to let the user manually start playback.
                } );
        }
    } );
    */
}

function playLiveStream(camId) {
    console.log('p');
    const videoTag = document.getElementById(camId + "_videosource");
    var p = videoTag.play();
    if (p !== undefined) {
         p.then(function() {
                        // Automatic playback started!
                    }).catch(function(error) {
                        console.log(error);
                        // Automatic playback failed.
                        // Show a UI element to let the user manually start playback.
                    } );
    }
}

function playMP4(camId, mp4Source, codec) {
    document.getElementById(camId + "_video").style.display = 'block';
    const videoTag = document.getElementById(camId + "_videosource");
    console.log("z")
    var mimeCodec = 'video/mp4; codecs="%s"'.format(codec);
    console.log(mimeCodec + " supported: " + MediaSource.isTypeSupported(mimeCodec))
    //const myMediaSource = new MediaSource();
    const videoUrl = URL.createObjectURL(myMediaSource);

    // attaching the MediaSource to the video tag
    videoTag.src = videoUrl;
    videoTag.style.display = 'block';

    myMediaSource.addEventListener('sourceopen', function(e) {
        console.log(myMediaSource.readyState);
        var videoSourceBuffer = myMediaSource.addSourceBuffer(mimeCodec);

        fetchArrayBuffer(mp4Source, function(buffer) {
            videoSourceBuffer.addEventListener('updateend', function (_) {
                console.log(myMediaSource.readyState);
                myMediaSource.endOfStream();
                var p =videoTag.play();
                // In browsers that don’t yet support this functionality,
                // playPromise won’t be defined.
                if (false && p !== undefined) {
                    p.then(function() {
                        // Automatic playback started!
                    }).catch(function(error) {
                        console.log(error);
                        // Automatic playback failed.
                        // Show a UI element to let the user manually start playback.
                    } );
                }
            });
            videoSourceBuffer.appendBuffer(buffer);
            console.log("afterappend:" + myMediaSource.readyState);
            // myMediaSource.endOfStream();

        }
        );

    });

}


function fetchArrayBuffer(url, callback) {
    console.log(url);
  var xhr = new XMLHttpRequest();
  xhr.open('get', url);
  xhr.responseType = 'arraybuffer';
  xhr.onload = function() {
    callback(xhr.response);
  };
  xhr.send();
}

function addToHistory(evtType, lastUpdate, lastServerId, updateTimes) {
    var historyTable = document.getElementById('history');
    var historyIndex = window.localStorage.getItem('historyIndex');
    if(historyRowCount == 0) {
        historyTable.style.display = 'block';
    }
    while(historyRowCount>10) {
        var txt = historyTable.rows[10].cells[4].innerHTML;
        var res = txt.match(/name="[0-9]+"/);
        var key = res[0].substring(6, res[0].length-1);
        window.localStorage.removeItem(key);
        historyTable.deleteRow(10);
        historyIndex = historyIndex.replace(new RegExp(key, "g"), "");
        historyIndex = historyIndex.replace(/::/g, "");
        historyRowCount -= 1;
    }
    now = (new Date()).getTime();
    var row = historyTable.insertRow(1);
    row.insertCell(0);
    row.cells[0].innerHTML = document.getElementById('history_TEMPLATE').innerHTML.replace(/history_ID/g, now)
    row.insertCell(0);
    row.cells[0].innerHTML = updateTimes;
    row.insertCell(0);
    row.cells[0].innerHTML = lastServerId;
    row.insertCell(0);
    row.cells[0].innerHTML = evtType;
    row.insertCell(0);
    row.cells[0].innerHTML = lastUpdate.toLocaleString();
    window.localStorage.setItem(String(now), row.innerHTML);
    if(!historyIndex) {
        historyIndex = String(now);
    }
    else {
        historyIndex = String(now) + ':' + historyIndex
    }
    historyRowCount += 1;
    window.localStorage.setItem('historyIndex', historyIndex);
}

function restoreHistory() {
    var historyIndex = window.localStorage.getItem('historyIndex');
    if(historyIndex) {
        var historyTable = document.getElementById('history');
        historyTable.style.display = 'block';
        var idxs = historyIndex.split(':');
        idxs.sort()
        //idxs.reverse();
        idxs.forEach(ts => {
          var row = historyTable.insertRow(1);
          row.innerHTML = window.localStorage.getItem(ts);
          historyRowCount += 1;
        });
    }
}

function awningCmd(id, cmd) {
    if(!updateInProgress) {
        var localId=id
        var host = "";
        if(hostMap.hasOwnProperty(id)) {
            host = hostMap[id];
            localId = localIdMap[id];
        }
        let timeStamp = window.performance.now().toString();
        let clientId = window.localStorage.getItem('clientId');
        let accessToken = window.localStorage.getItem('accessToken');
        const params = { command : cmd, id : localId, host : host, timeStamp : timeStamp, clientId : clientId };
        console.log(params);
        var http = new XMLHttpRequest();
        http.open('POST', url, true);
        http.setRequestHeader('Content-Type', 'application/json');
        http.setRequestHeader('fcm', offlineMode? 'yes' : 'no');
        if(accessToken !== null) {
            http.setRequestHeader('accessToken', accessToken);
            http.setRequestHeader('fcmUrl', fcmUrl);
            http.setRequestHeader('payload', JSON.stringify(params));
        }
        http.send(JSON.stringify(params))
        http.onreadystatechange = function() {
            if(this.readyState == 4) {
                if(this.status==202) {
                    console.log("Request send through FCM");
                }
                else {
                    console.log(this.responseText);
                }
            }
        }
    }
}


String.prototype.format = function() {
  return [...arguments].reduce((p,c) => p.replace(/%s/,c), this);
};
