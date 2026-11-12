from app.providers import Translator

def test_translator_removes_thinking_and_labels():
    assert Translator.clean('<think>internal thoughts</think>\nBản dịch: Tôi sẽ trở lại.') == 'Tôi sẽ trở lại.'
