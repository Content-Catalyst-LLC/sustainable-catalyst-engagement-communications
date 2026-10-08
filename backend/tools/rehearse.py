import argparse,json
from app.persistence.rehearsal import rehearse_file
p=argparse.ArgumentParser();p.add_argument('json_file');args=p.parse_args()
result=rehearse_file(args.json_file)
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['ready'] else 2)
