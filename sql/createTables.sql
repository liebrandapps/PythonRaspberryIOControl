
drop table if exists SensorShort;
drop table if exists SensorLong;
drop table if exists Actor;
drop table if exists Subscriptions;
drop table if exists PushSensorShort;
drop table if exists PNQueue;

create table SensorShort(sensorId TEXT, value1 NUMERIC, value2 NUMERIC, hour INTEGER, quarter INTEGER, slot INTEGER, atTime TIMESTAMP);
create table SensorLong(sensorId TEXT, avgValue NUMERIC, minValue NUMERIC, maxValue NUMERIC, unit TEXT, day INTEGER, sixHour INTEGER );
create index idxSensorShort on SensorShort(sensorId, atTime);


create table Actor(actorId TEXT, newValue TEXT, user TEXT, atTime TIMESTAMP, STATUS TEXT);

create table Subscriptions(token TEXT, clientId TEXT);

create table PushSensorShort(sensorId TEXT, value1 NUMERIC, value2 NUMERIC, atTime TIMESTAMP);

create table PNQueue(payload TEXT);
