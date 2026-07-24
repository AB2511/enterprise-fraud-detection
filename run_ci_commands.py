import os
import subprocess
import sys

root = r"D:\Hackathon\enterprise-fraud-detection\backend"
cmds = [
    [r".venv\Scripts\python.exe", "-m", "ruff", "check", "src/", "tests/"],
    [r".venv\Scripts\python.exe", "-m", "pytest", "tests/unit/", "--cov=src", "--cov-report=xml", "--cov-report=term", "-v"],
]

for cmd in cmds:
    print('RUNNING:', ' '.join(cmd))
    proc = subprocess.run(cmd, cwd=root, text=True, capture_output=True)
    print('returncode:', proc.returncode)
    if proc.stdout:
        print('STDOUT:\n' + proc.stdout)
    if proc.stderr:
        print('STDERR:\n' + proc.stderr)
    print('---')
