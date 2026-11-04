"""Optional local/container integration verification; never print credentials or text."""
import argparse
import json
import subprocess
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--api', default='http://127.0.0.1:18000')
    parser.add_argument('--token-file', type=Path, default=Path('.secrets/audit_token'))
    parser.add_argument('--restart-container', action='store_true')
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    headers = {'Authorization': 'Bearer ' + token}
    samples = [('safe', 'Explain machine learning in two short sentences.', 'ALLOW'),
               ('sensitive', 'My PIN is 6942.', 'BLOCK'),
               ('ambiguous', 'For this fictional debit card, the PIN selected was 6942.', 'HOLD'),
               ('credential', 'api_key = fictional_nonfunctional_deployment_key', 'BLOCK')]
    with httpx.Client(base_url=args.api, trust_env=False, timeout=100) as client:
        assert client.get('/health').status_code == 200
        anonymous = client.get('/audit').status_code
        wrong = client.get('/audit', headers={'Authorization': 'Bearer fictional-wrong'}).status_code
        assert anonymous == wrong == 401
        first = client.get('/audit?limit=200', headers=headers)
        assert first.status_code == 200
        before = first.json()['metrics']
        results, record_ids = [], []
        for name, text, expected in samples:
            response = client.post('/gateway', json={'text': text})
            response.raise_for_status()
            result = response.json()
            assert result['decision'] == expected, name
            assert result['backend_called'] == (expected == 'ALLOW'), name
            record_ids.append(result['audit_id'])
            results.append({'case': name, 'decision': expected, 'backend_completed': result['backend_called']})
        snapshot = client.get('/audit?limit=200', headers=headers).json()
        assert snapshot['metrics']['total'] == before['total'] + 4
        assert snapshot['metrics']['blocked'] == before['blocked'] + 2
        assert snapshot['metrics']['held'] == before['held'] + 1
        assert snapshot['metrics']['allowed'] == before['allowed'] + 1
        rows = [r for r in snapshot['records'] if r['id'] in record_ids]
        assert len(rows) == 4 and all(r['completed_at'] for r in rows)
        assert all(not r['backend_attempted'] for r in rows if r['decision'] != 'ALLOW')
        assert all(text not in json.dumps(snapshot) for _, text, _ in samples)
        assert all(not {'text', 'prompt', 'response', 'exception', 'reason'} & set(r) for r in rows)
        health = client.get('/operations/health', headers=headers).json()
        reports = client.get('/reports', headers=headers).json()
        assert 'ml_experiments.json' in reports['reports']
        if args.restart_container:
            subprocess.run(['docker', 'compose', 'restart', 'api'], check=True, capture_output=True)
            for _ in range(30):
                try:
                    persisted = client.get('/audit?limit=200', headers=headers)
                    if persisted.status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(1)
            else:
                raise AssertionError('Restart health unavailable')
            assert set(record_ids) <= {r['id'] for r in persisted.json()['records']}
            assert persisted.json()['metrics'] == snapshot['metrics']
        print(json.dumps({'status': 'PASS', 'health': health, 'unauthorized': anonymous, 'wrong_token': wrong,
                          'authenticated': first.status_code, 'cases': results, 'monitoring_delta': 4,
                          'finalized_metadata_only': True, 'persisted_after_restart': args.restart_container,
                          'archival_reports': reports.get('archival_display', False)}))


if __name__ == '__main__':
    main()
