#!/usr/bin/env python3

import sys
import tarantool
import yaml
from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent,
)
import pymysql.cursors
from configparser import ConfigParser
import io
import traceback

# Common settings

config = False
with open("replica.yml") as f:
	config = yaml.safe_load(f)

sqlcon = pymysql.connect(host=config['mysql']['host'], user=config['mysql']['user'], password=config['mysql']['password'], charset='utf8', cursorclass=pymysql.cursors.DictCursor)
mysql_settings = {'host': config['mysql']['host'], 'port': config['mysql']['port'], 'user': config['mysql']['user'], 'passwd': config['mysql']['password']}
stream = BinLogStreamReader(connection_settings = mysql_settings, server_id=int(config['mysql']['replication_slave_id']), auto_position=False, resume_stream=True, blocking=True, only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent])

tntcon = tarantool.connect(config['tarantool']['host'], config['tarantool']['port'], config['tarantool']['user'], config['tarantool']['password'])

mappings = config['mappings']
mapCache = {}
for target in mappings:
	cacheKey = "%s.%s" % (target['database'], target['table'])
	cacheTarget = mapCache[cacheKey] if cacheKey in mapCache else []
	cacheTarget += [target]
	mapCache[cacheKey] = cacheTarget

# Helper methods

def tnt_get_space(space_name):
	global tntcon
	return tntcon.space(space_name)

def get_targets(source_database, source_table):
	global mapCache
	cacheKey = "%s.%s" % (source_database, source_table)
	return mapCache[cacheKey] if cacheKey in mapCache else list()

def get_keys(target):
	return tuple([target['columns'][key] for key in target['key_fields']])

def tnt_delete(targets, row, BLEvent):
	row = dict(row["values"])
	for target in targets:
		out = tuple([row[key] for key in get_keys(target)])
		if out and len(out) == len(target['key_fields']):
			print(" Tarantool::DELETE", target['space'], out, flush=True)
			tnt_get_space(target['space']).delete(out)

def tnt_insert(targets, row, BLEvent):
	row = dict(row["values"])
	for target in targets:
		out = tuple([row[key] for key in target['columns']])
		if out and len(out) == len(target['columns']):
			print(" Tarantool::INSERT", target['space'], out, flush=True)
			tnt_get_space(target['space']).replace(out)

def tnt_update(targets, row, BLEvent):
	row["values"] = row["before_values"]
	tnt_delete(targets, row, BLEvent)
	row = dict(row["after_values"])
	for target in targets:
		out = tuple([row[key] for key in target['columns']])
		if out and len(out) == len(target['columns']):
			print(" Tarantool::UPDATE", target['space'], out, flush=True)
			tnt_get_space(target['space']).replace(out)

def is_empty(what):
	if what:
		return False
	else:
		return True

def clearTNT():
	global tntcon
	global mappings
	print("[+] Tarantool truncate", flush=True)
	for target in mappings:
		evalstring = "box.space.%s:truncate()" % target['space']
		print(" [+] Tarantool eval: %s" % evalstring)
		tntcon.eval(evalstring)
	print("[-] Tarantool truncate end", flush=True)

def dumpTables():
	global tntcon
	global sqlcon
	global linkTypes
	global mappings
	print("[+] Dumping MySQL tables", flush=True)
	for target in mappings:
		print(" [+] Updating Tarantool(%s) from MySQL(`%s`.`%s`)" % (target['space'], target['database'], target['table']), flush=True)
		with sqlcon.cursor() as cursor:
			sql = "SELECT * FROM %s.%s" % (target['database'], target['table'])
			cursor.execute(sql)
			for sqlrow in cursor:
				out = tuple([sqlrow[key] for key in target['columns']])
				if out and len(out) == len(target['columns']):
					tnt_get_space(target['space']).replace(out)
	print("[-] Dumping MySQL tables", flush=True)

try:
	print("[+] Starting replica.py", flush=True)
	clearTNT()
	dumpTables()
	print("[+] Listening to binlog events", flush=True)
	for binlogevent in stream:
		for row in binlogevent.rows:
			targets = get_targets(binlogevent.schema, binlogevent.table)
			if is_empty(targets):
				continue
			if isinstance(binlogevent, DeleteRowsEvent):
				tnt_delete(targets, row, binlogevent)
			elif isinstance(binlogevent, UpdateRowsEvent):
				tnt_update(targets, row, binlogevent)
			elif isinstance(binlogevent, WriteRowsEvent):
				tnt_insert(targets, row, binlogevent)
except KeyboardInterrupt:
	pass
except Exception as inst:
	print("[-] Exception raised", flush=True)
	print(type(inst), flush=True)
	print(inst.args, flush=True)
	print(inst, flush=True)
	traceback.print_exc(file=sys.stderr)
	print("[-] Exception end", flush=True)
finally:
	print("[-] Exit replica.py", flush=True)
	if stream:
		stream.close()
	if sqlcon:
		sqlcon.close()
	if tntcon:
		tntcon.close()
