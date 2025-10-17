# -*- coding: utf-8 -*-
from janome.tokenizer import Tokenizer
from sklearn.feature_extraction.text import TfidfVectorizer

_tokenizer = Tokenizer()

def tokenize_japanese(text: str):
    return [t.base_form for t in _tokenizer.tokenize(text)
            if t.part_of_speech.split(',')[0] in ['名詞','動詞','形容詞']]

def build_vectorizer(max_features: int = 300):
    return TfidfVectorizer(tokenizer=tokenize_japanese, token_pattern=None, max_features=max_features)
