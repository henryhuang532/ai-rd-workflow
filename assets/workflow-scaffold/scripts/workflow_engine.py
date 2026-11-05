#!/usr/bin/env python3
"""Local workflow gates. No daemon, model calls, or claims of authenticated identity."""
from __future__ import annotations
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid
import yaml

class WorkflowError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise WorkflowError(message)

STATUSES = {'PENDING','READY','RUNNING','WAITING_APPROVAL','BLOCKED','FAILED','COMPLETED','CANCELLED'}
STAGES = ['INTAKE','REQUIREMENTS','DESIGN','FEASIBILITY','PLANNING','APPROVAL','IMPLEMENTATION','INTEGRATION','CODE_REVIEW','QA','FIX','DELIVERY']
ROLES = {'INTAKE':'orchestrator','REQUIREMENTS':'product','DESIGN':'architect','FEASIBILITY':'architect','PLANNING':'architect','APPROVAL':'orchestrator','IMPLEMENTATION':'matt','INTEGRATION':'integration','CODE_REVIEW':'reviewer','QA':'tester','FIX':'matt','DELIVERY':'orchestrator'}
CHECKS = {'dependencies','stack','interfaces','migration','test_environment','boundaries','assumptions'}
HIGH_RISKS = {'production_migration','authentication','authorization','important_deletion','irreversible','paid_resource','production_deploy','sensitive_infrastructure'}

def new_state():
    return {'schema_version':2,'revision':0,'capabilities':{'mode':'serial','reason':'Independent execution and workspace probes not supplied','independent_sessions':False},'policy':{'max_parallel':1,'max_attempts':3},'tasks':[]}

def new_task(task_id, title, risk=1):
    return dict(task_id=task_id,parent_task_id=None,requirement_ids=[],title=title,description='',risk_level=risk,risk_factors=[],status='PENDING',stage='INTAKE',dependencies=[],assigned_role='orchestrator',assigned_agent=None,workspace=None,branch=None,acceptance_criteria=[],artifacts=[],attempts=0,timestamps={},evidence=[],requirements=[],requirements_baseline={},open_questions=[],prechecks=[],agent_dispatches=[],design={},plan={},feasibility={},authorization={},reviews=[],tests=[],bugs=[],lease=None,operations={},history=[],checkpoint={},failure=None,next_retry_at=0,implementation_sessions=[],tdd=[])

def safe_path(root, name):
    root = Path(root).resolve()
    p = (root / name).resolve()
    require(p.is_relative_to(root), 'artifact escapes repository')
    return p

def artifact(root, path):
    p = safe_path(root, path)
    require(p.is_file(), f'missing artifact: {path}')
    return {'path':str(path),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def check_artifact(root, record):
    require(isinstance(record,dict) and record.get('path') and record.get('sha256'), 'missing artifact digest')
    require(artifact(root, record['path']) == {k:record[k] for k in ('path','sha256')}, 'stale artifact digest')

def git(root, *args):
    p = subprocess.run(['git','-C',str(root),*args],capture_output=True,check=False)
    require(p.returncode == 0, 'Git unavailable: '+p.stderr.decode(errors='replace'))
    return p.stdout

def snapshot(root):
    """HEAD plus tracked/dirty/untracked bytes, excluding workflow-generated records."""
    sha = git(root,'rev-parse','HEAD').decode().strip()
    names = git(root,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0')
    digest = hashlib.sha256()
    for raw in sorted(set(names)):
        if not raw:
            continue
        name = os.fsdecode(raw)
        if name.startswith(('workflow/','docs/reports/','docs/bugs/','docs/test-cases/')):
            continue
        p = safe_path(root,name)
        digest.update(raw+b'\0')
        digest.update(p.read_bytes() if p.is_file() else b'<deleted>')
        if p.exists():
            digest.update(str(p.stat().st_mode & 0o777).encode())
    return {'sha':sha,'tree':digest.hexdigest()}

def task_by_id(state, tid):
    matches = [t for t in state['tasks'] if t['task_id']==tid]
    require(len(matches)==1, 'unknown or duplicate task')
    return matches[0]

def requirements_digest(t):
    """Bind the PRD, version and delivery scope; the PRD alone may span many tasks."""
    b=t['requirements_baseline']
    payload={k:b[k] for k in ('version','document','requirements','acceptance_ids')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def authorize(t, root,legacy_archived=False):
    requirements_gate(t,root,legacy_archived)
    a = t['authorization']
    require(a.get('decision')=='approved', 'approval required')
    require(a.get('kind') in {'human','preauthorized'}, 'authorization kind required')
    require(t['risk_level'] < 3 or a.get('kind')=='human', 'LEVEL 3/4 requires explicit human authorization')
    require(a.get('risk_level')==t['risk_level'] and t['task_id'] in a.get('scope',[]), 'authorization scope/risk mismatch')
    check_artifact(root,a.get('source'))
    if not legacy_archived:
        require(a.get('requirements_sha256')==requirements_digest(t), 'stale requirements approval')
    for key in ('design','plan'):
        check_artifact(root,t[key])
        require(a.get(key+'_sha256')==t[key]['sha256'], 'stale '+key+' approval')

def requirements_gate(t,root,legacy_archived=False):
    require(t['requirements'] and t['acceptance_criteria'], 'requirements/acceptance missing')
    ids = [r['requirement_id'] for r in t['requirements']]
    require(len(ids)==len(set(ids)) and set(ids)==set(t['requirement_ids']), 'requirement IDs mismatch')
    mapped = {ac for r in t['requirements'] for ac in r['acceptance_ids']}
    require(mapped==set(t['acceptance_criteria']), 'acceptance mapping incomplete')
    if legacy_archived:
        return
    require(len(t['acceptance_criteria'])==len(set(t['acceptance_criteria'])), 'acceptance IDs must be unique')
    require(all(isinstance(ac,str) and ac.strip() for ac in t['acceptance_criteria']), 'empty acceptance ID')
    require(all(isinstance(rid,str) and rid.strip() for rid in ids), 'empty requirement ID')
    require(all(r['acceptance_ids'] for r in t['requirements']), 'requirement has no acceptance criteria')
    b=t.get('requirements_baseline',{})
    require(b.get('status')=='confirmed' and b.get('version'), 'confirmed requirements baseline required')
    check_artifact(root,b.get('document'))
    require(b.get('requirements')==t['requirements'] and b.get('acceptance_ids')==t['acceptance_criteria'], 'requirements baseline scope changed')
    c=b.get('confirmation',{})
    require(c.get('actor') and c.get('timestamp'), 'requirements baseline confirmation source required')
    check_artifact(root,c.get('source'))
    require(c.get('document_sha256')==b['document']['sha256'], 'stale requirements confirmation')
    require(c.get('baseline_sha256')==requirements_digest(t), 'stale requirements confirmation scope/version')
    for q in t.get('open_questions',[]):
        require(q.get('question_id') and q.get('description') and q.get('owner'), 'requirement question metadata missing')
        require(q.get('status') in ('open','resolved','deferred') and isinstance(q.get('blocking'),bool), 'invalid requirement question status')
        scope=q.get('requirement_ids')
        require(isinstance(scope,list), 'requirement question scope missing')
        affected=not scope or bool(set(scope)&set(ids))
        require(not (q['status']!='resolved' and q['blocking'] and affected), 'unresolved requirement question: '+q['question_id'])

def planning_gate(t,root,legacy_archived=False):
    requirements_gate(t,root,legacy_archived)
    for key in ('design','plan'):
        check_artifact(root,t[key])
    f = t['feasibility']
    require(all(f.get('checks',{}).get(k) is True for k in CHECKS), 'feasibility incomplete')
    require(f.get('evidence'), 'feasibility evidence missing')
    for e in f['evidence']:
        check_artifact(root,e)

def command_receipt(root,e):
    check_artifact(root,e.get('receipt'))
    recorded=json.loads(safe_path(root,e['receipt']['path']).read_text())
    require(recorded=={k:v for k,v in e.items() if k!='receipt'}, 'command receipt mismatch')
    check_artifact(root,e.get('output'))
    require(e.get('command') and e.get('session') and e.get('finished_at',0)>=e.get('started_at',0), 'incomplete command evidence')


def implementation_gate(t,root,expected=None):
    require(t['implementation_sessions'], 'implementation identity missing')
    require(t['tdd'], 'TDD RED/GREEN evidence missing')
    covered=set()
    for pair in t['tdd']:
        red,green=pair['red'],pair['green']
        for e in (red,green):
            command_receipt(root,e)
            require(e.get('role')=='matt' and e.get('session') in t['implementation_sessions'], 'TDD implementer mismatch')
        require(red['exit_code']!=0 and not red['timed_out'], 'RED must fail, not timeout')
        require(green['exit_code']==0 and green['snapshot']==(expected or snapshot(root)), 'GREEN stale or failed')
        require(red['finished_at']<=green['started_at'], 'TDD order invalid')
        require(pair.get('failure_reason'), 'RED failure cause must demonstrate target behavior')
        covered.update(pair['acceptance_ids'])
    require(set(t['acceptance_criteria'])<=covered,'TDD coverage incomplete')


def review_gate(t,root,expected=None,legacy_archived=False):
    implementation_gate(t,root,expected)
    current = expected or snapshot(root)
    for dim in ('standards','spec'):
        reviews = [r for r in t['reviews'] if r.get('dimension')==dim]
        require(reviews, 'independent '+dim+' review missing')
        r = reviews[-1]
        if not legacy_archived:
            require(r.get('kind')=='code_review', 'formal code review required; prechecks are advisory')
            require(r.get('requirements_sha256')==requirements_digest(t), 'review requirements version mismatch')
        require(r.get('role')=='reviewer' and r.get('session') and r['session'] not in t['implementation_sessions'], 'self review prohibited')
        require(r.get('verdict')=='pass' and r.get('snapshot')==current, 'review rejected or stale')
        check_artifact(root,r.get('report'))

def test_gate(t,root,expected=None,legacy_archived=False):
    current = expected or snapshot(root)
    covered = set()
    for e in t['tests']:
        # Evidence must match a separately captured command receipt and its output.
        check_artifact(root,e.get('receipt'))
        receipt = json.loads(safe_path(root,e['receipt']['path']).read_text())
        require(receipt=={k:v for k,v in e.items() if k!='receipt'}, 'test fields differ from command receipt')
        check_artifact(root,e.get('output'))
        require(e.get('snapshot')==current, 'test evidence code version mismatch')
        if not legacy_archived:
            require(e.get('kind')=='qa_execution', 'formal QA execution required; document checks do not count')
            require(e.get('requirements_sha256')==requirements_digest(t), 'QA requirements version mismatch')
        require(e.get('exit_code')==0 and not e.get('timed_out'), 'failed test blocks completion')
        require(e.get('command') and e.get('role')=='tester' and e.get('session') and e['session'] not in t['implementation_sessions'], 'independent QA required')
        covered.update(e.get('acceptance_ids',[]))
    require(set(t['acceptance_criteria'])<=covered, 'acceptance test coverage incomplete')
    require(t['tests'], 'test evidence missing')

def delivery_gate(state,t,root,archived=False):
    expected=t.get("completed_snapshot") if archived else snapshot(root)
    require(expected,"completed snapshot missing")
    legacy_archived=archived and 'requirements_baseline' not in t
    planning_gate(t,root,legacy_archived)
    authorize(t,root,legacy_archived)
    require(archived or state['capabilities'].get('independent_sessions') is True, 'independent reviewer/tester execution unavailable')
    require(t['implementation_sessions'], 'implementation identity missing')
    review_gate(t,root,expected,legacy_archived)
    test_gate(t,root,expected,legacy_archived)
    require(not any(b.get('status')!='closed' for b in t['bugs']), 'unresolved defects')
    if not archived:
        require(not git(root,'diff','--name-only','--diff-filter=U').strip(), 'unresolved Git merge conflict')
    require(t.get('integration',{}).get('snapshot')==expected and t['integration'].get('passed') is True, 'integration missing/conflicted/stale')
    check_artifact(root,t['integration'].get('evidence'))
    integration_command=t['integration'].get('command_evidence',{})
    command_receipt(root,integration_command)
    require(integration_command.get('exit_code')==0 and not integration_command.get('timed_out') and integration_command.get('snapshot')==expected, 'integration command failed or stale')
    require(integration_command.get('role')=='integration', 'integration executor role required')
    require(t.get('delivery_report'), 'delivery report missing')
    check_artifact(root,t['delivery_report'])
    require(all(task_by_id(state,d)['status']=='COMPLETED' for d in t['dependencies']), 'dependency incomplete')

def validate(state,root,delivery=False):
    require(isinstance(state,dict) and state.get('schema_version')==2, 'schema version 2 required; migrate explicitly')
    require(isinstance(state.get('revision'),int) and state['revision']>=0,'invalid revision')
    require(isinstance(state.get('tasks'),list), 'tasks list required')
    require(state.get('policy',{}).get('max_parallel',0)>0 and state['policy'].get('max_attempts',0)>0,'invalid limits')
    ids = [t['task_id'] for t in state['tasks']]
    require(len(ids)==len(set(ids)), 'duplicate task IDs')
    seen, visiting = set(), set()
    def visit(tid):
        require(tid not in visiting,'dependency cycle')
        if tid in seen:
            return
        visiting.add(tid)
        for dep in task_by_id(state,tid)['dependencies']:
            require(dep in ids,'missing dependency')
            visit(dep)
        visiting.remove(tid)
        seen.add(tid)
    for t in state['tasks']:
        optional={'requirements_baseline','open_questions','prechecks','agent_dispatches'}
        require(set(new_task('',''))-optional<=set(t), 'task schema fields missing')
        require(t['status'] in STATUSES and t['stage'] in STAGES, 'invalid lifecycle/stage')
        require(t['risk_level'] in (1,2,3,4),'invalid risk')
        if t['status']=='RUNNING':
            require(t.get('lease') and t['lease'].get('session')==t['assigned_agent'] and t['workspace'] and t['attempts']>0, 'RUNNING requires claimed lease/workspace/attempt')
            require(all(task_by_id(state,d)['status']=='COMPLETED' for d in t['dependencies']), 'running dependency incomplete')
        require(not (set(t['risk_factors']) & HIGH_RISKS) or t['risk_level']==4,'high risk incorrectly classified')
        require(not t['parent_task_id'] or t['parent_task_id'] in ids,'missing parent')
        require(t['parent_task_id']!=t['task_id'],'self parent')
        visit(t['task_id'])
        previous = ('PENDING','INTAKE')
        for h in t['history']:
            require(tuple(h['from'])==previous,'broken history chain')
            require(legal_edge(*previous,*h['to']),'illegal history transition')
            require(h.get('actor') and h.get('time') and h.get('reason'),'incomplete history')
            previous=tuple(h['to'])
        require(previous==(t['status'],t['stage']), 'state changed outside transition history')
        if t['status'] not in ('BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL','COMPLETED') and t['stage'] not in ('INTAKE','REQUIREMENTS'):
            requirements_gate(t,root)
        if t['status'] not in ('BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL','COMPLETED') and t['stage'] in ('IMPLEMENTATION','INTEGRATION','CODE_REVIEW','QA','FIX','DELIVERY'):
            planning_gate(t,root)
            authorize(t,root)
        if t['status']=='COMPLETED' or delivery:
            require(t['status']=='COMPLETED' and t['stage']=='DELIVERY', 'delivery requires completed task')
            delivery_gate(state,t,root,archived=not delivery)
    active = [t for t in state['tasks'] if t.get('lease')]
    limit=1
    if state['capabilities'].get('mode')=='parallel':
        require(state['capabilities'].get('independent_sessions') and state['capabilities'].get('probe'),'parallel capability probe missing')
        check_artifact(root,state['capabilities']['probe'])
        limit=state['policy']['max_parallel']
    require(len(active)<=limit, 'active concurrency exceeds capability/policy')
    workspaces=[str(Path(t['workspace']).resolve()) for t in active]
    require(len(workspaces)==len(set(workspaces)), 'workspace collision')

def legal_edge(oldstatus,oldstage,status,stage):
    if oldstatus in ('COMPLETED','CANCELLED'):
        return False
    if status in ('BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL'):
        return stage==oldstage
    if oldstatus in ('BLOCKED','FAILED','WAITING_APPROVAL'):
        return status=='READY' and (stage==oldstage or (stage=='REQUIREMENTS' and oldstage not in ('INTAKE','REQUIREMENTS')))
    if stage==oldstage:
        return (oldstatus,status) in {('PENDING','READY'),('READY','RUNNING'),('RUNNING','READY')} or (status=='COMPLETED' and oldstage=='DELIVERY' and oldstatus=='RUNNING')
    if status!='RUNNING' or oldstatus!='RUNNING':
        return False
    forward = dict(zip(STAGES[:9],STAGES[1:10]))
    forward.update({'QA':'DELIVERY','FIX':'CODE_REVIEW'})
    return forward.get(oldstage)==stage or (oldstage in ('CODE_REVIEW','QA','INTEGRATION') and stage=='FIX') or (oldstage in ('DESIGN','FEASIBILITY','PLANNING','APPROVAL','INTEGRATION','CODE_REVIEW','QA','FIX') and stage in ('DESIGN','REQUIREMENTS'))

def transition(state,task_id,status,stage,actor,root,now=None):
    now=time.time() if now is None else now
    t=task_by_id(state,task_id)
    require(legal_edge(t['status'],t['stage'],status,stage),'illegal transition')
    if status=='RUNNING' or status=='COMPLETED':
        require(t.get('lease') and t['lease']['expires_at']>now and t['lease']['session']==t['assigned_agent'], 'valid owned lease required; use claim')
        require(all(task_by_id(state,d)['status']=='COMPLETED' for d in t['dependencies']), 'dependency incomplete')
    require(actor==ROLES[stage] or actor=='orchestrator','role cannot enter stage')
    if status=='READY':
        require(t['attempts']<state['policy']['max_attempts'],'attempt limit reached; human takeover required')
        require(time.time()>=t['next_retry_at'],'retry backoff not elapsed')
    if status not in ('BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL') and stage not in ('INTAKE','REQUIREMENTS'):
        requirements_gate(t,root)
    if status not in ('BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL') and stage in ('IMPLEMENTATION','INTEGRATION','CODE_REVIEW','QA','FIX','DELIVERY'):
        planning_gate(t,root)
        authorize(t,root)
    if status=='RUNNING' and stage in ('CODE_REVIEW','QA','DELIVERY'):
        implementation_gate(t,root)
    if status=='RUNNING' and stage in ('QA','DELIVERY'):
        review_gate(t,root)
    if (stage=='DELIVERY' and status=='RUNNING') or status=='COMPLETED':
        delivery_gate(state,t,root)
    if status=='COMPLETED':
        t['completed_snapshot']=snapshot(root)
    old=[t['status'],t['stage']]
    t['status'],t['stage']=status,stage
    t['assigned_role']=ROLES[stage]
    t['timestamps']['updated_at']=time.time()
    t['history'].append({'from':old,'to':[status,stage],'actor':actor,'time':time.time(),'reason':'gate-checked transition','session':t['assigned_agent'],'artifacts':copy.deepcopy(t['artifacts']),'validation':{'risk':t['risk_level'],'design':t['design'].get('sha256'),'plan':t['plan'].get('sha256')}})
    if status in ('COMPLETED','BLOCKED','FAILED','CANCELLED','WAITING_APPROVAL'):
        t['lease']=None

def ready(state,root):
    validate(state,root)
    active=[t for t in state['tasks'] if t.get('lease')]
    cap=state['capabilities']
    limit=1
    if cap.get('mode')=='parallel':
        require(cap.get('independent_sessions') and cap.get('probe'), 'parallel capability probe missing')
        check_artifact(root,cap['probe'])
        limit=state['policy']['max_parallel']
    candidates=[]
    for t in state['tasks']:
        if t['status'] not in ('PENDING','READY') or t.get('next_retry_at',0)>time.time():
            continue
        if not all(task_by_id(state,d)['status']=='COMPLETED' for d in t['dependencies']):
            continue
        # Explicit resources supplement worktree isolation (shared schemas, ports, generated outputs).
        conflicts=any(set(t.get('resources',[])) & set(a.get('resources',[])) or (t['workspace'] and a['workspace'] and Path(t['workspace']).resolve()==Path(a['workspace']).resolve()) for a in active+candidates)
        if not conflicts and len(active)+len(candidates)<limit:
            candidates.append(t)
    return [t['task_id'] for t in candidates]

def claim(state,task_id,session,workspace,root,now=None,ttl=300):
    now=time.time() if now is None else now
    require(session and ttl>0, 'session and positive lease TTL required')
    require(Path(workspace).is_dir(),'workspace missing')
    chosen=Path(workspace).resolve()
    for active in state['tasks']:
        if active.get('lease') and active.get('workspace'):
            used=Path(active['workspace']).resolve()
            require(not (chosen.is_relative_to(used) or used.is_relative_to(chosen)), 'workspace collision or nested workspace')
    require(task_id in ready(state,root),'task not schedulable')
    t=task_by_id(state,task_id)
    require(t['attempts']<state['policy']['max_attempts'],'attempt limit reached')
    if state['capabilities'].get('mode')=='parallel':
        git(workspace,'rev-parse','--show-toplevel')
        require(Path(git(workspace,'rev-parse','--show-toplevel').decode().strip()).resolve()==Path(workspace).resolve(),'workspace must be Git root/worktree')
    if t['status']=='PENDING':
        transition(state,task_id,'READY',t['stage'],'orchestrator',root)
    t['branch']=git(workspace,'rev-parse','--abbrev-ref','HEAD').decode().strip()
    t.update(assigned_agent=session,workspace=str(Path(workspace).resolve()),lease={'session':session,'claimed_at':now,'expires_at':now+ttl},attempts=t['attempts']+1)
    transition(state,task_id,'RUNNING',t['stage'],'orchestrator',root,now=now)

def fail(state,task_id,reason,now=None,retry_after=0):
    now=time.time() if now is None else now
    t=task_by_id(state,task_id)
    require(t['status']=='RUNNING','only running tasks may fail')
    target='FAILED' if t['attempts']>=state['policy']['max_attempts'] else 'BLOCKED'
    t['history'].append({'from':[t['status'],t['stage']],'to':[target,t['stage']],'actor':'orchestrator','time':now,'reason':reason})
    t.update(status=target,failure={'reason':reason,'time':now,'session':t['assigned_agent']},lease=None,next_retry_at=now+max(retry_after, min(3600,2**max(1,t['attempts']))))

def recover(state,now=None):
    now=time.time() if now is None else now
    for t in state['tasks']:
        if t.get('lease') and (t['lease']['expires_at']<=now or not Path(t['workspace']).is_dir()):
            fail(state,t['task_id'],'expired lease; reconcile checkpoint, workspace and uncertain operations before resume',now)

def defect(state,task_id,bug_id,category):
    owners={'implementation':'matt','requirement':'product','architecture':'architect','test':'product+tester','environment':'orchestrator','unreproducible':'tester'}
    require(category in owners,'unknown defect category')
    t=task_by_id(state,task_id)
    found=[b for b in t['bugs'] if b['bug_id']==bug_id]
    b=found[0] if found else {'bug_id':bug_id,'attempts':0,'status':'open','category':category,'owner':owners[category]}
    if not found:
        t['bugs'].append(b)
    b['attempts']+=1
    if b['attempts']>=state['policy']['max_attempts'] or category=='environment':
        b['escalation']='independent reviewer root cause required' if category!='environment' else 'environment blocked'
        if t['status']=='RUNNING':
            fail(state,task_id,b['escalation'])
    return b

def heartbeat(state,task_id,session,checkpoint,ttl=300,now=None):
    now=time.time() if now is None else now
    t=task_by_id(state,task_id)
    require(t.get('lease') and t['lease']['session']==session and t['lease']['expires_at']>now, 'lease ownership lost')
    require(ttl>0,'invalid TTL')
    t['lease']['expires_at']=now+ttl
    t['checkpoint']=checkpoint


def escalate(state,task_id,risk_level,reason):
    t=task_by_id(state,task_id)
    require(risk_level>t['risk_level'] and risk_level<=4,'only risk increases allowed')
    require(reason,'risk escalation reason required')
    if t['status']=='RUNNING':
        fail(state,task_id,'risk escalation: '+reason)
    else:
        require(t['status'] not in ('COMPLETED','CANCELLED'),'terminal task must use new change task')
    t['risk_level']=risk_level
    t['authorization']={}
    t.setdefault('risk_history',[]).append({'level':risk_level,'reason':reason,'time':time.time()})


def integration_failure(state,task_id,reason):
    t=task_by_id(state,task_id)
    require(t['status']=='RUNNING' and t['stage']=='INTEGRATION','integration must be running')
    tid=task_id+'-integration-fix-'+str(len([x for x in state['tasks'] if x['parent_task_id']==task_id])+1)
    repair=new_task(tid,'Integration repair: '+reason,t['risk_level'])
    repair.update(parent_task_id=task_id,requirement_ids=list(t['requirement_ids']),description=reason)
    state['tasks'].append(repair)
    fail(state,task_id,'integration conflict; repair task '+tid)
    return repair


def operation(state,task_id,key,idempotent=False):
    t=task_by_id(state,task_id)
    require(key,'idempotency key required')
    old=t['operations'].get(key)
    if old:
        if old['status']=='completed':
            return False
        require(old['idempotent'] and idempotent,'uncertain non-idempotent operation: human reconciliation required')
        return True
    t['operations'][key]={'status':'started','idempotent':idempotent,'time':time.time()}
    return True

def run_evidence(root,command,role,session,acceptance_ids,timeout=30,kind='command',requirements_sha256=None):
    require(command and session,'command/session required')
    require(kind in ('command','qa_execution'), 'invalid command evidence kind')
    if kind=='qa_execution':
        require(role=='tester' and requirements_sha256, 'QA requires tester and requirements digest')
    before=snapshot(root)
    started=time.time()
    timed_out=False
    try:
        p=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,check=False)
        output,code=p.stdout,p.returncode
    except subprocess.TimeoutExpired as exc:
        output,code,timed_out=exc.stdout or b'',124,True
    require(snapshot(root)==before,'command changed code; rerun evidence on final version')
    folder=Path(root)/'workflow/evidence'
    folder.mkdir(parents=True,exist_ok=True)
    name=str(uuid.uuid4())
    out=folder/(name+'.log')
    out.write_bytes(output)
    record={'kind':kind,'requirements_sha256':requirements_sha256,'command':command,'role':role,'session':session,'acceptance_ids':acceptance_ids,'snapshot':before,'started_at':started,'finished_at':time.time(),'exit_code':code,'timed_out':timed_out,'output':artifact(root,str(out.relative_to(root)))}
    receipt=folder/(name+'.json')
    receipt.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    record['receipt']=artifact(root,str(receipt.relative_to(root)))
    return record

class Store:
    """Single local filesystem writer; process death releases flock; CAS rejects stale writers."""
    def __init__(self,path):
        self.path=Path(path)
    def load(self):
        return yaml.safe_load(self.path.read_text())
    def update(self,mutator,root):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with open(str(self.path)+'.lock','a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=self.load()
            old_revision=state['revision']
            result=mutator(state)
            validate(state,root)
            require(self.load()['revision']==old_revision,'revision conflict')
            state['revision']+=1
            fd,tmp=tempfile.mkstemp(dir=self.path.parent,prefix='.workflow-')
            try:
                with os.fdopen(fd,'w') as f:
                    yaml.safe_dump(state,f,allow_unicode=True,sort_keys=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp,self.path)
                dfd=os.open(self.path.parent,os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'workflow/current-task.yaml')
    p.add_argument('--root',type=Path)
    sub=p.add_subparsers(dest='action',required=True)
    for name in ('validate','ready','recover'):
        sub.add_parser(name)
    tr=sub.add_parser('transition'); tr.add_argument('task'); tr.add_argument('status'); tr.add_argument('stage'); tr.add_argument('--actor',default='orchestrator')
    cl=sub.add_parser('claim'); cl.add_argument('task'); cl.add_argument('session'); cl.add_argument('workspace')
    ev=sub.add_parser('run-evidence'); ev.add_argument('--role',required=True); ev.add_argument('--session',required=True); ev.add_argument('--acceptance',action='append',default=[]); ev.add_argument('command',nargs=argparse.REMAINDER)
    ev.add_argument('--kind',choices=['command','qa_execution'],default='command'); ev.add_argument('--requirements-sha256')
    args=p.parse_args()
    root=(args.root or args.file.resolve().parents[1]).resolve()
    store=Store(args.file)
    try:
        if args.action=='validate': validate(store.load(),root)
        elif args.action=='ready': print(json.dumps(ready(store.load(),root)))
        elif args.action=='run-evidence': print(json.dumps(run_evidence(root,args.command,args.role,args.session,args.acceptance,kind=args.kind,requirements_sha256=args.requirements_sha256),ensure_ascii=False))
        elif args.action=='recover': store.update(lambda s:recover(s),root)
        elif args.action=='claim': store.update(lambda s:claim(s,args.task,args.session,args.workspace,root),root)
        else: store.update(lambda s:transition(s,args.task,args.status,args.stage,args.actor,root),root)
        return 0
    except (WorkflowError,KeyError,TypeError,OSError,yaml.YAMLError) as exc:
        print('ERROR: '+str(exc),file=__import__('sys').stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
