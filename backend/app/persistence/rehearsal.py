"""Read-only migration rehearsal: validates shape and produces an import plan; never writes."""
import json
from collections import Counter
from pathlib import Path
from app.contracts.canonical import MODEL_REGISTRY
from pydantic import ValidationError

def rehearse(records):
    seen=set(); counts=Counter(); errors=[]
    for i,entry in enumerate(records):
        kind=entry.get('model') if isinstance(entry,dict) else None
        if kind not in MODEL_REGISTRY:
            errors.append({'index':i,'reason':'unknown model'});continue
        try:
            item=MODEL_REGISTRY[kind].model_validate(entry['record'])
            if kind!='organizations' and item.organization_id is None:
                raise ValueError('tenant organization_id required for persistence')
            if kind=='organizations' and item.organization_id not in (None,item.id):
                raise ValueError('organization_id must be self or null')
            legacy=item.legacy_identity
            if legacy:
                key=(legacy.system.value,legacy.object_type,legacy.external_id)
                if key in seen: raise ValueError('duplicate legacy identity')
                seen.add(key)
            counts[kind]+=1
        except (ValidationError,ValueError,KeyError,TypeError) as exc:
            errors.append({'index':i,'reason':str(exc)[:250]})
    return {'mode':'read_only','ready':not errors,'counts':dict(counts),'errors':errors,'records_checked':len(records),'writes':0}

def rehearse_file(path):
    data=json.loads(Path(path).read_text())
    if not isinstance(data,list):raise ValueError('JSON input must be a list')
    return rehearse(data)
