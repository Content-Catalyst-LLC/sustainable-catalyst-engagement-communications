import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare_schema import compare
class ComparisonTests(unittest.TestCase):
 def setUp(self):
  self.schema={'tables':[{'name':'t','row_security':False,'columns':[{'name':'id','type':'uuid','default':None,'not_null':True,'identity':'','generated':''},{'name':'body','type':'text','default':None,'not_null':False,'identity':'','generated':''}],'constraints':[{'name':'a','type':'p','definition':'PRIMARY KEY (id)'},{'name':'b','type':'c','definition':"CHECK (body <> 'a  b'::text)"}],'indexes':[{'name':'i','definition':'CREATE INDEX i ON public.t USING btree (id)'}]}]}
 def test_object_and_named_collection_order(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['constraints'].reverse()
  result=compare(self.schema,actual);self.assertFalse(result['exact_equal']);self.assertTrue(result['named_collection_order_equal']);self.assertEqual(result['differences'],[])
 def test_column_type_nullability_default_and_rls(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['columns'][0].update(type='text',not_null=False,default="'x'::text");actual['tables'][0]['row_security']=True
  result=compare(self.schema,actual);self.assertEqual(len(result['differences']),4);self.assertFalse(result['deployment_go'])
 def test_column_order_is_not_discarded(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['columns'].reverse();r=compare(self.schema,actual)
  self.assertFalse(r['named_collection_order_equal']);self.assertEqual(r['differences'][0]['kind'],'column_order')
 def test_rename_is_reported_not_approved(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['constraints'][0]['name']='renamed'
  r=compare(self.schema,actual);self.assertEqual(r['differences'][0]['kind'],'constraint_name_only');self.assertFalse(r['deployment_go'])
 def test_sql_literal_whitespace_not_normalized(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['constraints'][1]['definition']="CHECK (body <> 'a b'::text)"
  self.assertTrue(compare(self.schema,actual)['differences'])
 def test_missing_index_and_extra_table(self):
  actual=copy.deepcopy(self.schema);actual['tables'][0]['indexes']=[];actual['tables'].append({'name':'other','row_security':False,'columns':[],'constraints':[],'indexes':[]})
  kinds={x['kind'] for x in compare(self.schema,actual)['differences']};self.assertEqual(kinds,{'missing_indexes','extra_table'})
 def test_duplicate_names_refused(self):
  actual=copy.deepcopy(self.schema);actual['tables'].append(actual['tables'][0]);self.assertRaises(ValueError,compare,self.schema,actual)
if __name__=='__main__':unittest.main()
