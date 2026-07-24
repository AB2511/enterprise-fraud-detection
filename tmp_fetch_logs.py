import urllib.request, re, json, sys

urls = [
    'https://github.com/AB2511/enterprise-fraud-detection/actions/runs/30117655577/job/89562191065',
    'https://github.com/AB2511/enterprise-fraud-detection/actions/runs/30117655577/job/89562191026',
]

for url in urls:
    print('URL:', url)
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    html = urllib.request.urlopen(req).read().decode('utf-8', 'replace')
    print('len', len(html))
    for marker in ['Run Ruff', 'Run tests with coverage', 'ruff', 'pytest', 'Traceback', 'FAILED', 'ERROR', 'E   ', 'AssertionError', 'ModuleNotFoundError', 'ImportError', 'SyntaxError', 'No module named']:
        idx = html.lower().find(marker.lower())
        if idx != -1:
            snippet = html[idx-2000:idx+8000]
            print('MARKER', marker, 'idx', idx)
            print(snippet)
            print('---')
    print('===END===')
