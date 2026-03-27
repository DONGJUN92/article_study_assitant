import nltk.data

text = 'For example, Miller et al. (1976) found it. Another example is e.g. Landy (1972).'

try:
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
except LookupError:
    try:
        nltk.download('punkt', quiet=True)
        tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    except Exception:
        pass

# Add common academic abbreviations
tokenizer._params.abbrev_types.update(['al', 'e.g', 'i.e', 'fig', 'eq'])

print("With custom abbrevs:")
print(tokenizer.tokenize(text))

# Let's also test my robust merge logic
def robust_tokenize(txt):
    sents = tokenizer.tokenize(txt)
    import re
    merged = []
    for s in sents:
        if merged and re.match(r'^[a-z\(\[\,\;\:]', s.strip()):
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)
    return merged

print("\nWith robust merge:")
print(robust_tokenize(text))
