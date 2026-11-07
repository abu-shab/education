"""One real minimal call, after user confirms the actual API project's Free tier."""
import argparse
import json
import os
import re
from datetime import datetime, timezone
import requests
from dotenv import set_key
from config import DATA, ROOT
from providers.gemini import FREE_MODELS, client, fingerprint
from rag import store

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm-free-tier', action='store_true', help='Only when Free tier is confirmed in AI Studio')
    parser.add_argument('--model', default='gemini-3.5-flash-lite', choices=sorted(FREE_MODELS))
    args = parser.parse_args()
    store.init()
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'model': args.model, 'success': False,
              'key_fingerprint': fingerprint(), 'pricing_url': 'https://ai.google.dev/gemini-api/docs/pricing'}
    try:
        if not os.getenv('GEMINI_API_KEY'):
            raise ValueError('missing_key')
        if not args.confirm_free_tier and os.getenv('GEMINI_FREE_TIER_CONFIRMED', '').lower() != 'true':
            raise ValueError('free_tier_not_confirmed')
        pricing = requests.get(report['pricing_url'] + '.md', timeout=20)
        pricing.raise_for_status()
        section = next((s for s in re.split(r'(?m)^## ', pricing.text) if f'`{args.model}`' in s), '')
        if not ('Free Tier' in section and section.count('Free of charge') >= 2):
            raise ValueError('free_pricing_not_verified')
        with client() as c:
            available = [m.name.removeprefix('models/') for m in c.models.list()]
            report['available_flash_models'] = [m for m in available if 'flash' in m and not any(x in m for x in ['tts','audio','image','live'])]
            if args.model not in available:
                raise ValueError('model_not_available')
            response = c.models.generate_content(model=args.model, contents='Reply with the single word OK.',
                config={'max_output_tokens': 32, 'temperature': 0})
            if not response.text or 'OK' not in response.text:
                raise ValueError('minimal_response_failed')
            report['usage'] = response.usage_metadata.model_dump(mode='json') if response.usage_metadata else {}
            report['response_model'] = getattr(response, 'model_version', None)
            report['success'] = True
            report['status'] = 'verified_minimal_request'
            store.usage(args.model, 'verification_success', report['usage'])
            set_key(str(ROOT / '.env'), 'GEMINI_MODEL', args.model)
            set_key(str(ROOT / '.env'), 'GEMINI_FREE_TIER_CONFIRMED', 'true')
    except Exception as exc:
        # Never print SDK exceptions: they may include request URLs or credential-bearing details.
        report['status'] = str(exc) if isinstance(exc, ValueError) else f'api_error_{getattr(exc, "code", "transport")}'
    (DATA / 'gemini_verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'key_fingerprint'}, ensure_ascii=True, indent=2))
    return 0 if report['success'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
