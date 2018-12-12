'use strict';

const {dialogflow} = require('actions-on-google');
const functions = require('firebase-functions');
const admin = require('firebase-admin');
const fetch = require("node-fetch");
const app = dialogflow({debug: true});

admin.initializeApp(functions.config().firebase);


// // Create and Deploy Your First Cloud Functions
// // https://firebase.google.com/docs/functions/write-firebase-functions
//
// exports.helloWorld = functions.https.onRequest((request, response) => {
//  response.send("Hello from Firebase!");
// });

app.intent('querySensor', (conv, { sensorName }) => {
    console.log(sensorName);
    return admin.database().ref('prc/' + sensorName).once('value', (snapshot) => {
        let data = snapshot.val();
        if(data!==null) {
            console.log(data);
            if (data.hasOwnProperty('response')) {
                conv.close(data.response);
            }
            else {
                let temp = data.temperature
                conv.close('Alright, temperature ' + sensorName + ' is ' + temp + ' degrees');
            }
        }
        else {
            conv.close("Sorry, I am not able to relate " + sensorName + " to any sensor");
        }
    });
});

app.intent('outsideLights', (conv, {turn}) => {
    var request = require('request-promise');
    console.log('version 12');
    if(turn === undefined) {
        turn = "on";
    }
    return admin.database().ref('prc').once('value').then( (snapshot) => {
        return Promise.resolve(snapshot.val());
    }).then( (data) => {
        let switchId = data.outsideLights;
        if(turn.includes('on')) {
            turn = 'on';
        }
        if(turn.includes('off')) {
            turn = 'off';
        }
        let value = turn;
        let clientId = "googleAction";
        let timeStamp = new Date().getTime().toString();
        const params = { command : "switch", id : switchId, value : value, host : data.host,
                        timeStamp : timeStamp, clientId : clientId };
        let fcmUrl = data.fcmUrl;
        let accessToken = data.fcmToken;
        var envelope = {};
        envelope['msgType'] = "evtAction";
        envelope['targetUrl'] = data.host;
        envelope['params'] = Buffer.from(JSON.stringify(params)).toString('base64');
        console.log(envelope);
        const message = {message : { topic : "update", data : { envelope : Buffer.from(JSON.stringify(envelope)).toString('base64') } } };
        var options = {
            method: 'POST',
            uri: fcmUrl,
            headers: {
                    "Content-type": "application/json",
                    'Authorization': 'Bearer ' + accessToken
                },
            body: message,
            json: true // Automatically stringifies the body to JSON
        };
        return Promise.resolve(request(options))
    }).then( (data) => {
            console.log(data);
            return conv.close("Ok, requesting to switch lights.");
            //return Promise.resolve();
    }).catch( (error) => {
                console.log('Request failed', error);
                return conv.close("Oops, that did not work.");
                //return Promise.reject(error);
    });

});

app.intent('showVideo', (conv, {cameraId, televisionId}) => {
    var request = require('request-promise');
    console.log('version 13');
    return admin.database().ref('prc').once('value').then( (snapshot) => {
        return Promise.resolve(snapshot.val());
    }).then( (data) => {
        let camId="";
        if (cameraId.toUpperCase().includes("CAT")) {
            camId = data.cam_cat;
        }
        if (cameraId.toUpperCase().includes("OUTSIDE")) {
            camId = data.cam_outside;
        }
        let clientId = "googleAction -> showVideo";
        let timeStamp = new Date().getTime().toString();
        const params = { command : "playTimelapseVideo", id : camId, host : data.host,
                        castName : televisionId,
                        timeStamp : timeStamp, clientId : clientId };
        let fcmUrl = data.fcmUrl;
        let accessToken = data.fcmToken;
        var envelope = {};
        envelope['msgType'] = "evtAction";
        envelope['targetUrl'] = data.host;
        envelope['params'] = Buffer.from(JSON.stringify(params)).toString('base64');
        console.log(envelope);
        const message = {message : { topic : "update", data : { envelope : Buffer.from(JSON.stringify(envelope)).toString('base64') } } };
        var options = {
            method: 'POST',
            uri: fcmUrl,
            headers: {
                    "Content-type": "application/json",
                    'Authorization': 'Bearer ' + accessToken
                },
            body: message,
            json: true // Automatically stringifies the body to JSON
        };
        return Promise.resolve(request(options))
    }).then( (data) => {
            console.log(data);
            return conv.close("Ok, requesting to play time lapse video on TV " + televisionId);
            //return Promise.resolve();
    }).catch( (error) => {
                console.log('Request failed', error);
                return conv.close("Oops, that did not work.");
                //return Promise.reject(error);
    });

});

app.intent('showSnapshot', (conv, {cameraId, televisionId}) => {
    var request = require('request-promise');
    console.log('version 13');
    return admin.database().ref('prc').once('value').then( (snapshot) => {
        return Promise.resolve(snapshot.val());
    }).then( (data) => {
        let camId="";
        if (cameraId.toUpperCase().includes("CAT")) {
            camId = data.cam_cat;
        }
        if (cameraId.toUpperCase().includes("OUTSIDE")) {
            camId = data.cam_outside;
        }
        let clientId = "googleAction -> showSnapshot";
        let timeStamp = new Date().getTime().toString();
        const params = { command : "showSnapshot", id : camId, host : data.host,
                        castName : televisionId,
                        timeStamp : timeStamp, clientId : clientId };
        let fcmUrl = data.fcmUrl;
        let accessToken = data.fcmToken;
        var envelope = {};
        envelope['msgType'] = "evtAction";
        envelope['targetUrl'] = data.host;
        envelope['params'] = Buffer.from(JSON.stringify(params)).toString('base64');
        console.log(envelope);
        const message = {message : { topic : "update", data : { envelope : Buffer.from(JSON.stringify(envelope)).toString('base64') } } };
        var options = {
            method: 'POST',
            uri: fcmUrl,
            headers: {
                    "Content-type": "application/json",
                    'Authorization': 'Bearer ' + accessToken
                },
            body: message,
            json: true // Automatically stringifies the body to JSON
        };
        return Promise.resolve(request(options))
    }).then( (data) => {
            console.log(data);
            return conv.close("Ok, requesting to show camera snapshot video on " + televisionId + " TV.") ;
            //return Promise.resolve();
    }).catch( (error) => {
                console.log('Request failed', error);
                return conv.close("Oops, that did not work.");
                //return Promise.reject(error);
    });

});


function runShellCmd(conv, shellCmd, value) {
    var request = require('request-promise');
    console.log('version 14');
    return admin.database().ref('prc').once('value').then( (snapshot) => {
        return Promise.resolve(snapshot.val());
    }).then( (data) => {
        let clientId = "googleAction -> shellCmd";
        let timeStamp = new Date().getTime().toString();
        const params = { command : "runShellCmd", id : shellCmd, value : value, host : data.host,
                        timeStamp : timeStamp, clientId : clientId };
        let fcmUrl = data.fcmUrl;
        let accessToken = data.fcmToken;
        var envelope = {};
        envelope['msgType'] = "evtAction";
        envelope['targetUrl'] = data.host;
        envelope['params'] = Buffer.from(JSON.stringify(params)).toString('base64');
        console.log(envelope);
        const message = {message : { topic : "update", data : { envelope : Buffer.from(JSON.stringify(envelope)).toString('base64') } } };
        var options = {
            method: 'POST',
            uri: fcmUrl,
            headers: {
                    "Content-type": "application/json",
                    'Authorization': 'Bearer ' + accessToken
                },
            body: message,
            json: true // Automatically stringifies the body to JSON
        };
        return Promise.resolve(request(options));
    }).then( (data) => {
            console.log(data);
            return conv.close("Ok, requesting to switch outside flood lights " + value) ;
            //return Promise.resolve();
    }).catch( (error) => {
                console.log('Request failed', error);
                return conv.close("Oops, that did not work.");
                //return Promise.reject(error);
    });
}

app.intent('floodLightOn', (conv) => {
    return runShellCmd(conv, 'floodLight', "on");
});

app.intent('floodLightOff', (conv) => {
    return runShellCmd(conv, 'floodLight', "off");
});


exports.PythonRaspberryControl = functions.https.onRequest(app);
