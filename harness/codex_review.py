"""Independent Codex review of a branch before it is merged (user 2026-11-25: use Codex as a reviewer on every merge).
Codex's sandbox cannot run commands on this PC, so the diff and the goal are pasted into the prompt.
usage: python codex_review.py REPO BRANCH [BASE] [--goal "what the change is for"]
writes results/codex_reviews/<repo>_<branch>_<time>.md and prints it"""
import os, subprocess, sys, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
CODEX = r'C:\fizzy\tools\bin\codex'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results', 'codex_reviews')
args = [a for a in sys.argv[1:] if not a.startswith('--')]
goal = sys.argv[sys.argv.index('--goal') + 1] if '--goal' in sys.argv else ''
if goal in args: args.remove(goal)
repo, branch = args[0], args[1]
base = args[2] if len(args) > 2 else subprocess.run(['git', '-C', repo, 'merge-base', 'HEAD', branch], capture_output=True, text=True).stdout.strip()
diff = subprocess.run(['git', '-C', repo, 'diff', '%s...%s' % (base, branch)], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
log = subprocess.run(['git', '-C', repo, 'log', '--oneline', '%s..%s' % (base, branch)], capture_output=True, text=True).stdout
if len(diff) > 180000:
    diff = diff[:180000] + '\n[... diff truncated at 180k chars ...]'
prompt = ('You are reviewing a change to a Skyrim SE 1.6.1170 SKSE plugin / Community Shaders fork (C++, HLSL, CommonLibSSE-NG, '
          'Address Library IDs). Your sandbox cannot read files, so everything you need is below. Goal of the change: %s\n\n'
          'Commits:\n%s\nReview for: correctness bugs, crash risks (null/dangling pointers, threading with BSJobs and the render '
          'thread, Havok world state, wrong relocation IDs/offsets, unguarded hooks), behaviour regressions against the stated '
          'goal, and performance traps. Rank findings most severe first, cite file and hunk, say how confident you are, and keep '
          'it under 400 words. Say plainly if you find nothing serious.\n\nDiff:\n%s') % (goal or 'see commit messages', log, diff)
t0 = time.time()
p = subprocess.run([CODEX, 'exec', '--skip-git-repo-check', '-'], input=prompt, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
text = p.stdout
marker = text.rfind('\ncodex\n')
review = text[marker + 7:] if marker >= 0 else text
os.makedirs(OUT, exist_ok=True)
path = os.path.join(OUT, '%s_%s_%s.md' % (os.path.basename(repo.rstrip('/\\')), branch.replace('/', '-'), time.strftime('%Y%m%d-%H%M')))
open(path, 'w', encoding='utf-8').write('# Codex review: %s %s (%.0f s)\n\n%s\n' % (repo, branch, time.time() - t0, review))
print(review); print('\nsaved:', path)
