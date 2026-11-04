#!/usr/bin/env python3
"""Validate v2 state and active gates; legacy aliases intentionally rejected."""
import argparse
from pathlib import Path
import sys
import yaml
from workflow_engine import validate, WorkflowError


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--file',type=Path,default=Path(__file__).resolve().parents[1]/'workflow/current-task.yaml')
    p.add_argument('--stage',choices=['schema','delivery'],default='schema')
    p.add_argument('--root',type=Path)
    args=p.parse_args()
    try:
        state=yaml.safe_load(args.file.read_text())
        validate(state,args.root or args.file.resolve().parents[1],delivery=args.stage=='delivery')
        if args.stage=='delivery' and not state['tasks']:
            raise WorkflowError('empty queue is not a delivery')
    except (WorkflowError,OSError,KeyError,TypeError,ValueError,yaml.YAMLError) as exc:
        print('ERROR: '+str(exc),file=sys.stderr)
        return 1
    print('workflow_check: '+args.stage+' passed (state and evidence consistency; not identity authentication)')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
