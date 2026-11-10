"""Deterministic metadata comparison; no database access or SQL rewriting."""
import hashlib,json

def unwrap(value):
    return value['schema'] if 'schema' in value else value

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def mapped(items,key):
    result={item[key]:item for item in items}
    if len(result)!=len(items):raise ValueError('Duplicate metadata names; refusing ambiguous comparison')
    return result

def canonical(schema):
    # Sort only named collections; retain column order and every SQL expression.
    result=json.loads(json.dumps(unwrap(schema)))
    result['tables'].sort(key=lambda x:x['name'])
    for table in result['tables']:
        for key in ('constraints','indexes'):
            table[key].sort(key=lambda x:x['name'])
    return result

def compare(expected,actual):
    e,a=unwrap(expected),unwrap(actual);changes=[]
    def add(kind,path,left,right):changes.append({'kind':kind,'path':path,'expected':left,'production':right})
    et,at=mapped(e['tables'],'name'),mapped(a['tables'],'name')
    for name in sorted(set(et)|set(at)):
        path='tables/'+name
        if name not in et:add('extra_table',path,None,at[name]);continue
        if name not in at:add('missing_table',path,et[name],None);continue
        x,y=et[name],at[name]
        for key in sorted((set(x)|set(y))-{'name','columns','constraints','indexes'}):
            if x.get(key)!=y.get(key):add('table_attribute',path+'/'+key,x.get(key),y.get(key))
        ec,ac=mapped(x['columns'],'name'),mapped(y['columns'],'name')
        eo,ao=[v['name'] for v in x['columns']],[v['name'] for v in y['columns']]
        if eo!=ao:add('column_order',path+'/columns/order',eo,ao)
        for column in sorted(set(ec)|set(ac)):
            cp=path+'/columns/'+column
            if column not in ec:add('extra_column',cp,None,ac[column]);continue
            if column not in ac:add('missing_column',cp,ec[column],None);continue
            for key in sorted((set(ec[column])|set(ac[column]))-{'name'}):
                if ec[column].get(key)!=ac[column].get(key):add('column_attribute',cp+'/'+key,ec[column].get(key),ac[column].get(key))
        for key in ('constraints','indexes'):
            em,am=mapped(x[key],'name'),mapped(y[key],'name')
            removed=set(em)-set(am);added=set(am)-set(em)
            if key=='constraints':
                # Identify exact same definition/type under another name, but do
                # not declare a rename safe for applications or migration tooling.
                for old in sorted(list(removed)):
                    sig={k:v for k,v in em[old].items() if k!='name'}
                    match=next((new for new in sorted(added) if {k:v for k,v in am[new].items() if k!='name'}==sig),None)
                    if match is not None:
                        add('constraint_name_only',path+'/'+key+'/'+old,em[old],am[match]);removed.remove(old);added.remove(match)
            for item in sorted(removed):add('missing_'+key,path+'/'+key+'/'+item,em[item],None)
            for item in sorted(added):add('extra_'+key,path+'/'+key+'/'+item,None,am[item])
            for item in sorted(set(em)&set(am)):
                for field in sorted((set(em[item])|set(am[item]))-{'name'}):
                    if em[item].get(field)!=am[item].get(field):add(key+'_attribute',path+'/'+key+'/'+item+'/'+field,em[item].get(field),am[item].get(field))
    exact=digest(e)==digest(a);ordered=digest(canonical(e))==digest(canonical(a))
    return {'expected_original_sha256':digest(e),'production_original_sha256':digest(a),'exact_equal':exact,'named_collection_order_equal':ordered,'expected_table_count':len(et),'production_table_count':len(at),'differences':changes,'assessment':'MATCH' if exact else 'NAMED_COLLECTION_ORDER_ONLY' if ordered else 'DIFFERENCES_REQUIRE_REVIEW','sql_expression_normalization_performed':False,'deployment_go':False,'limitations':['No SQL expression, default, type, constraint or index rendering is silently normalized.','PostgreSQL version/search_path differences require review; a textual SQL difference is not automatically incompatibility or safety.','Matching metadata does not certify data, migration history, privileges, writers, backup, identity or privacy.']}
