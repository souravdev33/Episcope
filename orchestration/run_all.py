"""One-command local rebuild. The generated .env is ignored by Git."""
import argparse, os, secrets, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scale',type=float,default=.002); ap.add_argument('--seed',type=int,default=4345); a=ap.parse_args()
    env=os.environ.copy(); env_file=ROOT/'.env'
    if not env.get('EPISCOPE_HASH_SALT') and env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.startswith('EPISCOPE_HASH_SALT='): env['EPISCOPE_HASH_SALT']=line.split('=',1)[1].strip().strip('"').strip("'")
    if not env.get('EPISCOPE_HASH_SALT'):
        env['EPISCOPE_HASH_SALT']=secrets.token_hex(32)
        env_file.write_text('EPISCOPE_HASH_SALT='+env['EPISCOPE_HASH_SALT']+'\n',encoding='utf-8')
        print('Created private local .env containing the ID hashing key; it is excluded from Git.')
    cmds=[
      [sys.executable,'-m','generator.generate','--scale',str(a.scale),'--seed',str(a.seed),'--out','data/input'],
      [sys.executable,'-m','pipeline.run','--input','data/input','--output','data/lake'],
      [sys.executable,'-m','analytics.run','--input','data/lake','--output','data/serving']]
    for cmd in cmds: subprocess.run(cmd,cwd=ROOT,env=env,check=True)
if __name__=='__main__': main()
