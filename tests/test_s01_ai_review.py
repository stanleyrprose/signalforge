import unittest
from signalforge.s01_ai_review import build_review_request, validate_review_result

ITEM = {'url': 'https://myanmar.gov.mm/en/news-media/news/latest-news/-/example',
        'title_hint': 'Example headline', 'evidence_status': 'LISTING_HINT_ONLY'}


class S01AIReviewTests(unittest.TestCase):
    def test_request(self):
        p = build_review_request([ITEM], model='gpt-6.1-sol')
        self.assertEqual(p['model'], 'gpt-6.1-sol')
        self.assertIn('listing-only', p['instructions'])
        with self.assertRaises(ValueError):
            build_review_request([ITEM] * 21, model='gpt-6.1-sol')
        with self.assertRaises(ValueError):
            build_review_request([ITEM], model='')

    def test_validation(self):
        item = {'source_url': ITEM['url'], 'chinese_title': '测试', 'chinese_summary': '仅标题',
                'importance': 60, 'category': '政策', 'rationale': '相关',
                'evidence_limitations': '仅列表'}
        self.assertEqual(validate_review_result({'items': [item]}, [ITEM]), [item])
        with self.assertRaises(ValueError):
            validate_review_result({'items': [dict(item, source_url='https://evil.test')]}, [ITEM])
        with self.assertRaises(ValueError):
            validate_review_result({'items': [dict(item, importance=101)]}, [ITEM])
