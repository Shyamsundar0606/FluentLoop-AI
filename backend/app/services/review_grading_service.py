"""Accent-sensitive, punctuation-tolerant factual recall; never fuzzy grading."""
import unicodedata

def normalize(value):
    value = unicodedata.normalize("NFC", value).casefold().replace("’", "'").replace("ʼ", "'")
    value = value.replace("–", "-").replace("—", "-")
    return " ".join(value.strip().strip(".!?;:…\"«» ").split())

def grade(answer, alternatives):
    return bool(normalize(answer)) and normalize(answer) in {normalize(a) for a in alternatives}
