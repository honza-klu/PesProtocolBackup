import sqlite3
import datetime
import dateutil.parser
import time
import json

class ProtocolRecord():
  """Custom class used to store protocol records. It is used instead of dict to save memory"""
  __slots__ = ('record_id', 'datetime', 'value', 'd_value')
  def __init__(self, inp):
    self.record_id = inp['record_id']
    self.datetime = inp['datetime']
    self.value = inp['value']
    self.d_value = inp['d_value']
  def __getitem__(self, key):
    if key=='record_id':
      return self.record_id
    elif key=='datetime':
      return self.datetime
    elif key=='value':
      return self.value
    elif key=='d_value':
      return self.d_value
    else:
      raise KeyError()
  def __setitem__(self, key, value):
    if key=='record_id':
      self.record_id = value
    elif key=='datetime':
      self.datetime = value
    elif key=='value':
      self.value = value
    elif key=='d_value':
      self.d_value = value
    else:
      raise KeyError()
  def __delitem__(self, key):
    pass
  def keys(self):
    return self.__slots__
  def todict(self):
    return {"record_id": self.record_id, "datetime": self.datetime,
            "value": self.value, "d_value": self.d_value}

class ProtocolOverlapError(Exception):
  pass

def _convert_unixtime(val):
    return datetime.datetime.fromtimestamp(float(val))

def _adapt_unixtime(val):
  return int((time.mktime(val.timetuple())+val.microsecond/1000000.0))

sqlite3.register_converter("unixtime", _convert_unixtime)
sqlite3.register_adapter(datetime.datetime, _adapt_unixtime)

def list_protocols(db_path):
  db = sqlite3.connect(db_path, detect_types = sqlite3.PARSE_DECLTYPES |sqlite3.PARSE_COLNAMES)
  ret =[]
  try:
    cur = db.cursor()
    cur.execute('SELECT id, name, begin as "begin [unixtime]",'
                'end as "end [unixtime]"FROM protocols')
    for prot in cur:
      ret.append({"id": prot[0], "name": prot[1], 
                "begin": prot[2], "end": prot[3]})
  finally:
    cur.close()
  db.close()
  return ret

class Protocol:
  def __init__(self, db_path=None, prot_id=None, json_data=None):
    if db_path:
      self.db_path = db_path
      self.db = sqlite3.connect(db_path, detect_types = sqlite3.PARSE_DECLTYPES |sqlite3.PARSE_COLNAMES)
    else:
      self.db = None
      self.db_path = None
    self.data = None
    self.prot_id = None
    if prot_id:
      self._load_protocol(prot_id)
    elif json_data:
      self._load_json(json_data)
    else:
      prot_id = None
  def _load_protocol_meta(self, prot_id=None):
    if prot_id is not None:
      self.prot_id = prot_id
    if self.prot_id is None:
      raise ValueError("Undefined protocol_id")
    try:
      cur = self.db.cursor()
      #load metadata
      cur.execute('SELECT name, begin as "begin [unixtime]", end  as "end [unixtime]" FROM protocols WHERE id=?;',
                 (self.prot_id,))
      res = cur.fetchall()
      if len(res)==0:
        raise Exception("Protocol %d not found!" % (prot_id))
      self.name = res[0][0]
      self.begin = res[0][1]
      self.end = res[0][2]
      #load records
      self.protocol_data = []
      rows = cur.execute('SELECT protocol_id, record_id FROM protocols_data WHERE protocol_id=?;',
                        (self.prot_id,))
      for row in rows:
        self.protocol_data.append({"protocol_id": row[0], "record_id": row[1]})
    except Exception as e:
      self.prot_id = None
      self.name = None
      self.begin = None
      self.end = None
      #load records
      self.protocol_data = []
      raise e
    finally:
      cur.close()
  def _load_protocol(self, prot_id=None):
    if prot_id is not None:
      self.prot_id = prot_id
    if self.prot_id is None:
      raise ValueError("Undefined protocol_id")
    self._load_protocol_meta(prot_id)
    try:
      cur = self.db.cursor()
      #load data
      self.data = []
      rows = cur.execute("""SELECT record_id, datetime as "datetime [unixtime]",
value, d_value FROM data WHERE 
datetime>? AND datetime<?""", (self.begin, self.end,))
      for row in rows:
        self.data.append(ProtocolRecord({"record_id": row[0], "datetime": row[1],
  "value": row[2], "d_value": row[3]}))
    except Exception as e:
      self.prot_id = None
      self.data = None
      raise e
    finally:
      cur.close()

  def get_json(self, ostream=None):
    def json_serial(obj):
      """This function takes care of serializing data for json"""
      if isinstance(obj, (datetime.datetime, )):
        return obj.isoformat()
      elif isinstance(obj, ProtocolRecord):
        return obj.todict()
      raise TypeError("Type %s is not serializable" % type(obj))
    ret = {"name": self.name, "begin": self.begin, "end": self.end,
          "protocol_data": self.protocol_data, "data": self.data}
    if ostream:
      if not hasattr(ostream, 'write'):
        raise ValueError("Given objet miss write attribute")
      json.dump(ret, ostream, default=json_serial)
      return
    return json.dumps(ret, default=json_serial)

  def load_json(self, json_data):
    def json_decode(obj):
      if all(k in obj.keys() for k in
             ('record_id', 'datetime', 'value', 'd_value')):
        return ProtocolRecord(obj)
      else:
        return(obj)
    #TODO: Accept stream as json_data
    if isinstance(json_data, str):
      json_data = json.loads(json_data, object_hook=json_decode)
    elif hasattr(json_data, 'read'):
      json_data = json.load(json_data, object_hook=json_decode)
    else:
      raise TypeError("Cant handle json_data type(%s)" %
                      type(json_data).__name__)
    self.name = json_data["name"]
    self.begin = dateutil.parser.parse(json_data["begin"])
    self.end = dateutil.parser.parse(json_data["end"])
    self.protocol_data = json_data["protocol_data"]
    self.data = json_data["data"]
    for rec in self.data:
      rec["datetime"] = dateutil.parser.parse(rec["datetime"])
  def save_protocol(self):
    #Check conflicting protocols
    cur = self.db.cursor()
    cur.execute('SELECT id, name, begin as "begin [unixtime]", '
                'end as "end [unixtime]" FROM protocols WHERE '
                "(begin>=? AND begin<=?) or (end>=? AND end<=?);",
                (self.begin, self.end, self.begin, self.end,)
    )
    conflicting = []
    conflicts = cur.fetchall()
    for conf in conflicts:
      print("Conflicting protocol id:%d %s - %s" % (conf[0], 
                                                    str(conf[2]), conf[3]))
      conflicting.append({"name": conf[1], "id": conf[1]})
    if len(conflicts)>0:
      raise ProtocolOverlapError("There are conflicting protocols id:%d %s - %s" % 
                     (conflicts[0][0], str(conflicts[0][2]), conflicts[0][3]))
    #Check conflicting data
    cur.execute('SELECT count() FROM data WHERE '
                "(datetime>=? AND datetime<=?);",
                (self.begin, self.end))
    conf_data = cur.fetchone()[0]
    if conf_data>0:
      raise ProtocolOverlapError("There are conflicting data")
    try:
#TODO: add transaction support
      cur = self.db.cursor()
      cur.execute('INSERT INTO protocols(name, begin, end) VALUES (?, ?, ?);', (self.name, self.begin, self.end))
      prot_id = cur.lastrowid
      for prot_data in self.protocol_data:
        cur.execute('INSERT INTO protocols_data(protocol_id, record_id) VALUES (?, ?)',
                   (prot_id, prot_data["record_id"],))
      for rec in self.data:
        cur.execute('INSERT INTO data(record_id, datetime, value, d_value)' 
                   'VALUES (?, ?, ?, ?)',
                   (rec["record_id"], rec["datetime"],
                   rec["value"], rec["d_value"],))
      self.db.commit()
    except Exception as e:
      print(e)
      raise e
    print("finished")
    
  def offset_protocol(self, offset):
    self.begin = self.begin+offset
    self.end = self.end+offset
    for d in self.data:
      d["datetime"] += offset
  def sample_cnt(self):
    if self.data is not None:
      return len(self.data)
    elif self.db and self.prot_id:
      cur = self.db.cursor()
      cur.execute('SELECT count() FROM data WHERE datetime>? AND datetime<?;',
                  (self.begin, self.end)
                 )
      return cur.fetchone()[0]
    else:
      raise ValueError('Cannot get protocol with aviable parameters')
  def duration(self):
    return (self.end - self.begin)
