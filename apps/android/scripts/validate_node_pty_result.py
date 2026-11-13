"""Validate a supplied original-node-pty phone report; never attest a device."""
import argparse
import json
from pathlib import Path

def validate(value, build):
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(value.get('schemaVersion')==1 and value.get('suite')=='original-node-pty-v1','Wrong suite')
    require(value.get('status')=='PASS' and value.get('nativeExitCode')==0,'Failed runtime')
    require(value.get('platform')=='android' and value.get('arch')=='arm64' and value.get('node')=='v24.22.1','Wrong runtime')
    require(value.get('apkSha256')==build['apkSha256']['app-debug.apk'],'APK mismatch')
    for key,library in [('nodePtyAddonSha256','libharness_node_pty.so'),('fixtureSha256','libharness_pty_fixture.so'),('nodeSha256','libnode_executable.so')]:
        require(value.get(key)==build['packagedLibraries'][library]['sha256'],'Native digest mismatch: '+key)
    require(value.get('installedCodeWritable') is False,'Writable installed code')
    uid=value.get('supervisorUid',0);identity=value.get('kernelIdentity',{})
    require(type(uid) is int and uid>0 and identity.get('uid')==uid,'Ordinary UID mismatch')
    require(identity.get('parentPid')==value.get('supervisorPid') and identity.get('pid')!=value.get('supervisorPid'),'Supervisor identity mismatch')
    require(value.get('cwd')==value.get('expectedWorkspace') and isinstance(value.get('cwd'),str),'Workspace mismatch')
    require(value.get('fixtureExecutable','').endswith('/libharness_pty_fixture.so'),'Unexpected child fixture')
    require(value.get('device',{}).get('api',0)>=29,'Device details missing')
    require(value.get('originalNodePtyVersion')=='1.2.0-beta.15' and value.get('nativeSourceModified') is False,'Original package missing')
    for key in ['gate3Passed','originalTerminalIntegrated','generalShellProviderImplemented','harnessStarted','spawnHelperUsed']:
        require(value.get(key) is False,'Unsupported scope claim: '+key)
    cases=value.get('cases',[])
    require([case.get('role') for case in cases]==['--tty-child','--exit-seven','--wait','--wait','--ignore-term'],'Incomplete cases')
    require([case.get('signal') for case in cases]==[0,0,2,15,9],'Signal mismatch')
    require(cases[0].get('exitCode')==0 and cases[1].get('exitCode')==7,'Exit status mismatch')
    require('TTY-INPUT:pty-input ROWS:40 COLS:100' in cases[0].get('output','') and 'TTY-STDERR' in cases[0].get('output',''),'PTY input/resize/output missing')
    require(value.get('stderrMergedByPty') is True and cases[-1].get('timedOut') is True,'Timeout/PTY facts missing')
    for case in cases:
        require(case.get('status')=='PASS','Failed case')
        require(case.get('ready') is True and case.get('exitEventObserved') is True and case.get('childNoLongerObservable') is True,'Exit/readiness evidence missing')
        require(case.get('nativeIdentity',{}).get('pid')==case.get('pid') and case['nativeIdentity'].get('uid')==uid and case['nativeIdentity'].get('parentPid')==identity.get('pid'),'Child identity mismatch')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('result',type=Path);parser.add_argument('--build-record',type=Path,required=True);args=parser.parse_args()
    validate(json.loads(args.result.read_text()),json.loads(args.build_record.read_text()))
    print('PASS: supplied original node-pty record is consistent; physical attribution and terminal integration require separate review')
