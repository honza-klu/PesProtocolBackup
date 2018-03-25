import argparse
from pesnet_protocol_backup import Protocol

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='Manipulate protocols in database export and import them')
  parser.add_argument("action", action="store", type=str,
                     choices=['export', 'import'],
                     help="Select required action")
  parser.add_argument("db_path", type=str,
                     help="Path to database")
  parser.add_argument(("--id"), type=int, required=False, default=None)
  parser.add_argument("--output", "-o", type=str,
                     help="Name of output file", default=None)
  parser.add_argument("--input", "-i", type=str,
                     help="Name of input file", default=None)
  args = parser.parse_args()

  if args.action=='export':
    prot_id = args.id
    db_path = args.db_path
    if prot_id==None:
      print("ID of exported protocol is required!")
      exit(-1)
    if args.output==None:
      print("Path to output file is required")
      exit(-1)
    print("Exporting protocol %d" % (prot_id,))
    prot = Protocol(db_path, prot_id)
    data = prot.get_json()
    f = open(args.output, 'w')
    f.write(data)
    f.close()
  elif args.action=='import':
    db_path = args.db_path
    prot = Protocol(db_path)
    if args.input==None:
      print("Path to input file is required")
      exit(-1)
    prot = Protocol(db_path)
    f = open(args.input, 'r')
    data = f.read()
    f.close()
    prot.load_json(data)
    print("Importing protocol named %s" % (prot.name))
    prot.save_protocol()