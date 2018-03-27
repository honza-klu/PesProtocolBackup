import argparse
import gzip
import os
from pesnet_protocol_backup import Protocol
from pesnet_protocol_backup import list_protocols

def backup_prot(db_path, prot_id, output_file, compress=None):
  prot = Protocol(db_path, prot_id)
  data = prot.get_json()
  if compress==None:
    f = open(output_file, 'wb')
  elif compress=="gzip":
    f = gzip.open(output_file, 'wb')
  f.write(data.encode('utf8'))
  f.close()

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Manipulate protocols in database export and import them')
  parser.add_argument("action", action="store", type=str,
                     choices=['export', 'import', 'list', 'backup_all'],
                     help="Select required action")
  parser.add_argument("db_path", type=str,
                     help="Path to database")
  parser.add_argument(("--id"), type=int, required=False, default=None)
  parser.add_argument("--output", "-o", type=str,
                     help="Name of output file", default=None)
  parser.add_argument("--input", "-i", type=str,
                     help="Name of input file", default=None)
  parser.add_argument("--compress", action="store_const", default=None,
                     const="gzip")
  args = parser.parse_args()

  db_path = args.db_path
  if args.action=='export':
    prot_id = args.id
    if prot_id==None:
      print("ID of exported protocol is required!")
      exit(-1)
    if args.output==None:
      print("Path to output file is required")
      exit(-1)
    print("Exporting protocol %d" % (prot_id,))
    backup_prot(db_path, prot_id, args.output, args.compress)
  elif args.action=='import':
    prot = Protocol(db_path)
    if args.input==None:
      print("Path to input file is required")
      exit(-1)
    prot = Protocol(db_path)
    f = open(args.input, 'rb')
    #detect if file is compressed
    header = f.read(2)
    f.seek(0)
    if header == b'\x1f\x8b':
      print("Compression detected")
      f.close()
      f = gzip.open(args.input, 'rb')
    data = f.read()
    data=data.decode('utf8')
    f.close()
    prot.load_json(data)
    print("Importing protocol named %s" % (prot.name))
    prot.save_protocol()
  elif args.action=="list":
    protocols = list_protocols(db_path)
    for prot in protocols:
      print("Protocol[%d]: %s.\tStarting at:%s\tending at:%s." %
           (prot["id"], prot["name"], prot["begin"], prot["end"]))
  elif args.action=="backup_all":
    if args.output==None:
      print("Path to output directory is required")
      exit(-1)
    protocols = list_protocols(db_path)
    for prot in protocols:
      file_name = os.path.join(args.output, "protocol-%d-%s.json" %
                               (prot["id"], prot["name"].replace(':', '-'),))
      print("Backing up protocol[%d]: %s to %s" %
           (prot["id"], prot["name"], file_name,))
      backup_prot(db_path, prot["id"], file_name, args.compress)