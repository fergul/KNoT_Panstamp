import serial, sys
from datetime import datetime
from time import gmtime, strftime
from protocolwrapper import (
    ProtocolWrapper, ProtocolStatus)
from knot_packet import (
    payload_header, data_header, 
    data_payload, serial_query, serial_query_response, 
    serial_response, serial_connect_ack, Container)
import sqlite3

PROTOCOL_HEADER = '\x12'
PROTOCOL_FOOTER = '\x13'
PROTOCOL_DLE = '\x7D'

if sys.argv < 3:
	print "Please specify serial port and baud to log"
	sys.exit()


pw = ProtocolWrapper(   
        header=PROTOCOL_HEADER,
        footer=PROTOCOL_FOOTER,
        dle=PROTOCOL_DLE)

gateway = serial.Serial(sys.argv[1], sys.argv[2], timeout=100)
conn = sqlite3.connect('knotweb/database.db')
c = conn.cursor()
while True:
    status = pw.input(gateway.read(1))
    if (status == ProtocolStatus.MSG_OK):
        print "packet found:"
        dp = data_payload.parse(pw.last_message)
        print "Received packet - cmd = %d" % dp.cmd
        dt =  datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        c.execute("SELECT * FROM things_thing")
        print c.fetchone()
        print c.fetchone()
        if (dp.cmd == 2):
            r = serial_query_response.parse(bytearray(dp.data))
            print r
            
            try:
                c.execute("INSERT INTO things_queried VALUES (?,?,?,?)",[r.name[:7], r.src, r.type, dt])
                print "Added dev in db %s" % r.name[:7]
            except:
                c.execute("UPDATE things_queried SET addr=?, dev_type=?, refreshed=? WHERE name=?", [r.src, r.type, dt, r.name[:7]])
                print "Updated new dev to db %s" % r.name[:7]

        elif (dp.cmd == 4):
            r = serial_connect_ack.parse(bytearray(dp.data))
            c.execute("SELECT dev_type FROM things_queried WHERE name=?", [r.name[:7]])
            t = c.fetchone()[0]
            c.execute("SELECT * FROM things_thing WHERE name=?", [r.name[:7]])
            if (c.fetchone() == None):
                try:
                    c.execute("INSERT INTO things_thing VALUES (?,?,?,?,?,?)",[r.name[:7], r.src, t, 1, dt, 0])
                except:
                    print "Couldn't add to db"
            else: 
                try:
                    c.execute("UPDATE things_thing SET addr=?, connected=?, refreshed=? WHERE name=?",[r.src, 1, dt, r.name[:7]])
                except:
                    print "Couldn't update db"
        elif (dp.cmd == 5):
            r = serial_response.parse(bytearray(dp.data))
            print "Received msg from %s : %d" % (r.name[:7], r.data)
            try:
                c.execute("UPDATE things_thing SET data=?, refreshed=? WHERE name=?", [r.data, dt, r.name[:7]])
                conn.commit()
                print "Updated DB"

            except:
                print "Thing doesn't exist in DB, reconnect to it"
        conn.commit()



