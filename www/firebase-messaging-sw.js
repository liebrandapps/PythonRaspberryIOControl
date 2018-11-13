// Update your Public Key here
var publicKey = "BKvow7EfRvjfw3jrGFIPjxUM-n-gRMtQYWQVmi5wM-QRUXxdKimpj2Ak-Jk-7N3au0p5BNBpB5uxHSAWAq1QRgI";
var senderId = "309161754593";
var cacheName = 'prc.cache';
var regUpdate = 'regUpdate.json';
var evtUpdate = 'evtUpdate.json';

// Give the service worker access to Firebase Messaging.
// Note that you can only use Firebase Messaging here, other Firebase libraries
// are not available in the service worker.
importScripts('https://www.gstatic.com/firebasejs/5.5.2/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/5.5.2/firebase-messaging.js');

console.log("in Script firebase-messaging-sw.js");

firebase.initializeApp({
  'messagingSenderId': senderId
});

var messaging = firebase.messaging();

/*
    msgType 'regUpdate' always overwrites older updates per serverId
    msgType 'evtUpdate' cumulates the information per serverId
*/
messaging.setBackgroundMessageHandler(function(payload) {
    if(payload.data.hasOwnProperty('envelope')) {
        payload.data = JSON.parse(atob(payload.data.envelope));
    }
    console.log('Received background message ', payload);
    var cachedJson = {};
    var msgType = payload.data.msgType;
    payload['rcvTime'] = new Date().toLocaleString();
    if(msgType === 'regUpdate') {
        var serverId = payload.data.serverId.toString();
        caches.match(regUpdate).then(r => {
            if(r !== undefined) {
                console.log("match");
                // found in cache -> update it, if it has a newer timestamp
                cachedJson = JSON.parse(r);
                if( !chachedJson.hasOwnProperty(serverId) || payload.timeStamp > cachedJson[serverId].timeStamp) {
                    cachedJson[serverId] = JSON.stringify(payload);
                    var jsonResponse = new Response(JSON.stringify(cachedJson), {
                        headers: {
                            'content-type': 'application/json'
                    } } );
                    caches.open(cacheName).then(cache => cache.put(regUpdate, jsonResponse));
                }
            }
            else {
                console.log("reg Update match undefined")
                cachedJson[serverId] = payload;
                var jsonResponse = new Response(JSON.stringify(cachedJson), {
                        headers: {
                            'content-type': 'application/json'
                } } );
                caches.open(cacheName).then(cache => cache.put(regUpdate, jsonResponse));
            }
        }).catch(function() {
            console.log("catch");
            cachedJson[serverId] = payload;
            var jsonResponse = new Response(JSON.stringify(cachedJson), {
                headers: { 'content-type': 'application/json' }
            } );
            caches.open(cacheName).then(cache => cache.put(regUpdate, jsonResponse));
        });
    }
    if(msgType === 'evtUpdate') {
        var serverId = payload.data.serverId.toString();
        var timeStamp = payload.data.timeStamp.toString();
        caches.match(evtUpdate).then(r => {
            console.log('evt match');
            if(r !== undefined) {
                console.log("defined");
                cachedJson = JSON.parse(r);
            }
            if(!cachedJson.hasOwnProperty(serverId)) {
                cachedJson[serverId] = {};
            }
            cachedJson[serverId][timeStamp] = payload;
            var jsonResponse = new Response(JSON.stringify(cachedJson), {
                headers: { 'content-type': 'application/json' }
            } );
            caches.open(cacheName).then(cache => cache.put(evtUpdate, jsonResponse.clone()));
        }).catch(function() {
            console.log('evt catch');
            if(!cachedJson.hasOwnProperty(serverId)) {
                cachedJson[serverId] = {};
            }
            cachedJson[serverId][timeStamp] = payload;
            var jsonResponse = new Response(JSON.stringify(cachedJson), {
                headers: { 'content-type': 'application/json' }
            } );
            caches.open(cacheName).then(cache => cache.put(evtUpdate, jsonResponse));
        });
        if(payload.data.hasOwnProperty('priority')) {
            if(payload.data.priority == 2) {
                var notificationTitle = payload.notification.title;
                var notificationOptions = {
                    body: payload.notification.body,
                    icon: '/favicon-256x256.png'
                };

            return self.registration.showNotification(notificationTitle,
                notificationOptions);
            }
        }
    }
    if(msgType === 'evtAction') {
        let params = atob(payload.data.params);
        fetch(payload.data.targetUrl, {
            method: 'post',
            headers: {
                "Content-type": "application/json"
            },
            body: params
        })
        .then(function (data) {
                console.log('Request succeeded with JSON response', data);
        })
        .catch(function (error) {
            console.log('Request failed', error);
        });
    }
    return null;
});

