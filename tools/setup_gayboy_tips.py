"""Create isolated GAYBOY tip links using the owner's encrypted Stripe setup."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'VIBECHOPPER/scripts'))
from namehero_access import STATE, protect
import stripe


def main():
    private = json.loads(protect((STATE / 'stripe-live.dpapi').read_bytes(), decrypt=True))
    client = stripe.StripeClient(private['stripe_secret_key'], max_network_retries=2)
    product = client.v1.products.create({
        'name': 'Support GAYBOY',
        'description': 'Optional one-time tip for GAYBOY development. The ROM is free at y2kcrisis.com/gayboy.',
        'metadata': {'project': 'gayboy', 'purpose': 'optional_tip'},
    }, {'idempotency_key': 'gayboy-tip-product-v1'})
    links = {}
    for kind in ('five', 'custom'):
        params = {'product': product.id, 'currency': 'usd'}
        if kind == 'five':
            params['unit_amount'] = 500
        else:
            params['custom_unit_amount'] = {'enabled': True, 'preset': 500, 'minimum': 50}
        price = client.v1.prices.create(params, {'idempotency_key': f'gayboy-tip-price-{kind}-v1'})
        link = client.v1.payment_links.create({
            'line_items': [{'price': price.id, 'quantity': 1}],
            'metadata': {'project': 'gayboy', 'purpose': 'optional_tip'},
            'payment_intent_data': {'metadata': {'project': 'gayboy', 'purpose': 'optional_tip'}},
            'after_completion': {'type': 'redirect', 'redirect': {'url': 'https://y2kcrisis.com/gayboy?tip=thanks'}},
        }, {'idempotency_key': f'gayboy-tip-link-{kind}-v1'})
        assert link.livemode and link.active and link.url.startswith('https://buy.stripe.com/')
        links[kind] = link.url
    for folder in (ROOT / 'website', ROOT / 'network'):
        (folder / 'gayboy-tips.json').write_text(json.dumps(links, indent=2) + '\n', encoding='utf-8')
    print('Created and verified live GAYBOY $5 and custom tip links. No charge was made.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Tip setup failed:', type(error).__name__)
        raise SystemExit(1)
