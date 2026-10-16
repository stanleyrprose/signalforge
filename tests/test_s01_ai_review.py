import pytest
from signalforge.s01_ai_review import build_review_request,validate_review_result

ITEM = {'url':'https://myanmar.gov.mm/en/news-media/news/latest-news/-/example',
        'title_hint':'Example headline','evidence_status':'LISTING_HINT_ONLY'}


def test_review_request_is_model_explicit_and_bounded():
    p=build_review_request([ITEM],model='gpt-6.1-sol')
    assert p['model']=='gpt-6.1-sol'
    assert 'listing-only' in p['instructions']
    with pytest.raises(ValueError):build_review_request([ITEM]*21,model='gpt-6.1-sol')
    with pytest.raises(ValueError):build_review_request([ITEM],model='')


def test_review_rejects_fabricated_urls_and_bad_scores():
    item={'source_url':ITEM['url'],'chinese_title':'测试','chinese_summary':'仅标题',
          'importance':60,'category':'政策','rationale':'相关','evidence_limitations':'仅列表'}
    assert validate_review_result({'items':[item]},[ITEM])==[item]
    with pytest.raises(ValueError):validate_review_result({'items':[dict(item,source_url='https://evil.test')]},[ITEM])
    with pytest.raises(ValueError):validate_review_result({'items':[dict(item,importance=101)]},[ITEM])
