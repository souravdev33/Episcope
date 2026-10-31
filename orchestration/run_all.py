"""One-command local build. Public source downloads are opt-in and cached."""
import argparse, os, secrets, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scale',type=float,default=.04)
    parser.add_argument('--seed',type=int,default=4345)
    parser.add_argument('--with-public-data',action='store_true',
                        help='Download/cache S1-S3 public inputs before the synthetic build.')
    args=parser.parse_args()
    env=os.environ.copy()
    env_file=ROOT/'.env'
    if not env.get('EPISCOPE_HASH_SALT') and env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            if line.startswith('EPISCOPE_HASH_SALT='):
                env['EPISCOPE_HASH_SALT']=line.split('=',1)[1].strip().strip('"').strip("'")
    if not env.get('EPISCOPE_HASH_SALT'):
        env['EPISCOPE_HASH_SALT']=secrets.token_hex(32)
        env_file.write_text('EPISCOPE_HASH_SALT='+env['EPISCOPE_HASH_SALT']+'\n',encoding='utf-8')
        print('Created private local .env for ID hashing; it is excluded from Git.')

    def run(*args):
        subprocess.run([sys.executable,*args],cwd=ROOT,env=env,check=True)

    generator_args=['-m','generator.generate','--scale',str(args.scale),
                    '--seed',str(args.seed),'--out','data/input']
    if args.with_public_data:
        run('-m','generator.acquire_public','--out','data/reference')
        generator_args.extend(['--population-file','data/reference/population.csv'])
    run(*generator_args)
    run('-m','pipeline.run','--input','data/input','--output','data/lake',
        '--reference','data/reference')
    run('-m','analytics.run','--input','data/lake','--output','data/serving')

if __name__=='__main__':
    main()



