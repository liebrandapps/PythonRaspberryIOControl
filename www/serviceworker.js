
var cacheName = 'prc.cache';
var regUpdate = 'regUpdate.json';
var evtUpdate = 'evtUpdate.json';

var filesToCache = [
    '/',                // index.html
    '/prcweb',
    '/code.js',
    '/design.css',
    '/history24.png',
    'manifest.json'
];


self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(cacheName)
        .then(function(cache) {
            console.info('[serviceworker.js] cached all files');
            return cache.addAll(filesToCache);
        })
    );
});

self.addEventListener('activate', function(event) {
    console.log('Activated serviceworker.js', event);
    event.waitUntil(
    caches.keys().then(function(cacheNames) {
      return Promise.all(
        cacheNames.filter(function(currentCacheName) {
          return currentCacheName === cacheName;
        }).map(function(cacheName) {
          return caches.delete(cacheName);
        })
      );
    })
  );
});

self.addEventListener('fetch', function(event){
    // network 1st, cache 2nd
    if(event.request.url.endsWith("localcache?get=regUpdate") ||
            event.request.url.endsWith("localcache?get=evtUpdate")) {
        var reqKey = regUpdate;
        if (event.request.url.endsWith("localcache?get=evtUpdate")) {
            reqKey = evtUpdate;
        }
        event.respondWith(
            caches.open(cacheName).then(function(cache) {
                return cache.match(reqKey).then(function(response) {
                    if( response === undefined) {
                        return new Response( '{ "data" : "none" }',
                            { headers: {'Content-Type': 'application/json'} }
                        );
                    }
                    else {
                        //return response;
                        const r = response.clone();
                        return cache.delete(reqKey).then(function() {
                            return r;
                        });
                    }
                });
            })
        );
    }
    else {
        //console.log(event.request);
        if(event.request.headers.get('fcm') === 'yes') {
            event.respondWith(postViaFCM(event));
            return;
        }
        event.respondWith(
            fetch(event.request)
                .then(function(response) {
                    //console.log("Using network ", response)
                    if(!response || response.status !== 200 || response.type !== 'basic' || event.request.method === 'POST') {
                            return response;
                    }
                    // nevertheless update the cache
                    var resCopy = response.clone();
                    caches.open(cacheName)
                       .then(function(cache) {
                            var reqCopy = event.request.clone();
                            return cache.put(reqCopy, resCopy);
                       });
                    return response;
                })
                .catch(function() {
                    if(event.request.method === 'GET') {
                        //console.log("Using cache");
                        return caches.match(event.request)
                            .catch(function() {
                                console.log("Oops: Network & Cache failed on ", event.request);
                            });
                    }
                    else {
                        // POST requests should be converted into FCM peer messages
                        return(postViaFCM(event));
                    }
                }
                )
            );
        }
    }
);

function postViaFCM(event ) {
    console.log("POST Request - check, if can forward this one using FCM");
    let accessToken = event.request.headers.get('accessToken');
    if (accessToken===null) {
        console.log('no access token saved');
        return new Response( '{ "message" : "Server not available and no access token available" }',
                            { status : 503, headers: {'Content-Type': 'application/json'} } );
    }
    let fcmUrl = event.request.headers.get('fcmUrl');
    var envelope = {};
    envelope['msgType'] = "evtAction";
    envelope['targetUrl'] = event.request.url;
    envelope['params'] = btoa(event.request.headers.get('payload'));
    console.log(envelope);
    const message = {message : { topic : "update", data : { envelope: btoa(JSON.stringify(envelope)) } } };
    console.log(fcmUrl);
    fetch(fcmUrl, {
            method: 'post',
            headers: {
                "Content-type": "application/json",
                'Authorization': 'Bearer ' + accessToken
            },
            body: JSON.stringify(message)
        })
        .then(function (data) {
                console.log(data);
        })
        .catch(function (error) {
            console.log('Request failed', error);
        });

    return new Response( '{ "message" : "request send through fcm peer messaging." }',
                            {   status : 202, headers: {'Content-Type': 'application/json'} }
                        );
}