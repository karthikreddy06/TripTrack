import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def main():
    base = 'http://127.0.0.1:8000/api'
    
    print('=== 1. Testing Dynamic Autocomplete Suggestions ===')
    url = f'{base}/explore/suggestions?q=Kyoto'
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read().decode())
        suggestions = data if isinstance(data, list) else data.get('suggestions', [])
        print('Suggestions count:', len(suggestions))
        for s in suggestions[:3]:
            print(f"  - {s.get('name')} | {s.get('subtitle')}")

    print('\n=== 2. Testing Worldwide Explore Discovery for Kyoto ===')
    url = f'{base}/explore/search?q=Kyoto&category=all'
    with urllib.request.urlopen(url) as r:
        data = json.loads(r.read().decode())
        places = data.get('places', [])
        print('Verified places returned:', len(places))
        for p in places[:5]:
            print(f"  - {p.get('name')} [{p.get('category')}] | Score: {p.get('travel_score')}")

    from app.auth import create_access_token
    token = create_access_token("65a1234567890abcdef12345")
    auth_headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    print('\n=== 3. Testing AI Assistant Direct General Knowledge Query ===')
    req = urllib.request.Request(
        f'{base}/ai/chat',
        data=json.dumps({'message': 'What is Python and why is it popular?'}).encode(),
        headers=auth_headers
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        print('Tool called:', data.get('tool_called'))
        print('AI Message Response:\n', data.get('response', ''))

    print('\n=== 4. Testing AI Assistant Natural Travel Query ===')
    req = urllib.request.Request(
        f'{base}/ai/chat',
        data=json.dumps({'message': 'What should I visit in Kyoto?'}).encode(),
        headers=auth_headers
    )
    with urllib.request.urlopen(req) as r:
        data = json.loads(r.read().decode())
        print('Tool called:', data.get('tool_called'))
        print('AI Message Response:\n', data.get('response', ''))

if __name__ == '__main__':
    main()
