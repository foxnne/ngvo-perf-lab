"""Queue job: merge a local branch into the fork's working branch (no game, no push). usage: python merge_job.py BRANCH"""
import subprocess, sys
R = 'C:/Users/foxnn/dev/skyrim-community-shaders'
def g(*a): return subprocess.run(['git', '-C', R, *a], capture_output=True, text=True)
if g('status', '--porcelain', '-uno').stdout.strip(): sys.exit('working tree not clean')
r = g('merge', '--no-edit', sys.argv[1]); print(r.stdout, r.stderr)
if r.returncode: g('merge', '--abort'); sys.exit('merge failed, aborted')
print(g('log', '--oneline', '-3').stdout)
