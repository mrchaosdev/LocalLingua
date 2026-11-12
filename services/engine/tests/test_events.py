from app.events import EventHub,caption
from app.stability import stable_prefix,RevisionGate

def test_caption_contract():
    e=caption('translation.final','u1',4,'Launch next week.','Ra mắt tuần tới.','mock')
    assert e['is_final'] is True and e['revision']==4

def test_no_duplicate_out_of_order():
    g=RevisionGate()
    assert g.allow('abc',1,False)
    assert not g.allow('abc',1,False)
    assert not g.allow('abc',0,False)
    assert g.allow('abc',2,True)
    assert not g.allow('abc',3,False)

def test_stable_prefix():
    assert stable_prefix('We will launch next','We will launch soon') == 'We will launch'

def test_history_is_bounded():
    h=EventHub(max_history=2)
    for i in range(5): h.publish(caption('translation.final',f'u{i}',1,'hi','chào'))
    assert len(h.history)==2
