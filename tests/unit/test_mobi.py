from manga_optimizer.export import mobi

def test_make_id():
    assert mobi.make_id('testing') == 'B1Z6AM3CXN'
    assert mobi.make_id('My book title') == 'B1UXVFRYCH'