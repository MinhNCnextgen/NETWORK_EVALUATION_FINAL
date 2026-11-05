"""Integration check with a fake ns3 wrapper; no real simulations are run.

Usage: python s-pie/test_batch_runner.py --bash /path/to/bash
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bash', default='bash')
    args = parser.parse_args()
    source = Path(__file__).with_name('run-simulation.sh').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent.resolve()) as folder:
        root = Path(folder)
        script = root/'scratch'/'s-pie'
        script.mkdir(parents=True)
        (script/'run-simulation.sh').write_text(source.replace('PYTHON="python3"', 'PYTHON="python"'), encoding='utf-8', newline='\n')
        (script/'summarize.py').write_text('print("metric,value\\nmock,1")\n', encoding='utf-8')
        (root/'ns3').write_text('''import sys, shlex, time, json
from pathlib import Path
if sys.argv[1] != 'run':
    with open('build.log','a') as f: f.write(sys.argv[1]+'\\n')
    sys.exit(0)
assert '--no-build' in sys.argv
opts=dict(x[2:].split('=',1) for x in shlex.split(sys.argv[-1])[1:])
output=Path(opts['output'])
output.parent.mkdir(parents=True,exist_ok=True)
begin=time.time()
time.sleep(.1)
if Path('fail.flag').exists() and opts['aqm']=='CoDel': sys.exit(7)
output.write_text('mock\\n')
output.with_suffix('.timing.json').write_text(json.dumps([begin,time.time()]))
''', encoding='utf-8')

        def run(*extra):
            return subprocess.run([args.bash,'scratch/s-pie/run-simulation.sh',*extra], cwd=root,
                                  capture_output=True, encoding='utf-8', errors='replace')
        dry = run('--dry-run')
        assert dry.returncode == 0, dry.stderr
        assert dry.stdout.count('--RngRun=') == 24
        assert not (root/'result').exists()
        custom=run('--runs=2','--start-run','4','--scenario','1','--parallel','3','--dry-run')
        assert custom.returncode == 0, custom.stderr
        assert custom.stdout.count('--RngRun=') == 8
        assert 'scenario_1_run_4/' in custom.stdout and 'scenario_1_run_5/' in custom.stdout
        assert '--RngRun=1 ' not in custom.stdout and '--scenario=2' not in custom.stdout
        for bad in [('--runs','0'),('--runs','abc'),('--start-run',),('--parallel','0'),('--scenario','3')]:
            assert run(*bad,'--dry-run').returncode != 0, bad
        assert run('--help').returncode == 0
        result = run()
        assert result.returncode == 0, result.stderr
        assert (root/'build.log').read_text().splitlines() == ['configure','build']
        assert len(list((root/'result').rglob('*-summary.csv'))) == 24
        assert len(list((root/'result').glob('scenario_*_run_*'))) == 6
        events=[]
        for p in (root/'result').rglob('*.timing.json'):
            a,b=json.loads(p.read_text())
            events.extend([(a,1),(b,-1)])
        active=peak=0
        for _,delta in sorted(events):
            active+=delta
            peak=max(peak,active)
        assert peak == 2, peak
        repeat = run()
        assert repeat.returncode != 0
        assert len((root/'build.log').read_text().splitlines()) == 2
        # New output root for failure-path test; preserve successful results.
        p=script/'run-simulation.sh'
        p.write_text(p.read_text(encoding='utf-8').replace('RESULT_DIR="result"', 'RESULT_DIR="failed_result"'),encoding='utf-8',newline='\n')
        (root/'fail.flag').touch()
        failed=run()
        assert failed.returncode != 0
        assert 'Batch' in failed.stderr
        assert len(list((root/'failed_result').rglob('*.log'))) == 24
        # Also exercise actual execution with CLI overrides and a separate output root.
        (root/'fail.flag').unlink()
        custom=run('--runs','1','--start-run','8','--scenario','2','--parallel','1','--result-dir','cli_result')
        assert custom.returncode == 0, custom.stderr
        assert len(list((root/'cli_result'/'scenario_2_run_8').rglob('*-summary.csv'))) == 4
        print('PASS: batch concurrency, output folders, build once, dry-run, overwrite guard, job failure, CLI range/scenario/parallel/output and invalid options.')


if __name__ == '__main__':
    main()
