"""Normalização de texto e embeddings locais determinísticos.

O embedding usa *feature hashing* (palavras, bigramas e n-gramas de caracteres) projetado num
vetor de dimensão fixa e normalizado (L2). Vantagens para o estágio atual do projeto: roda offline,
sem custo, sem baixar modelos e é reprodutível nos testes.

ponytail: similaridade é lexical, não semântica. Para evoluir, troque `embed_text` por um modelo
de embeddings (ex.: endpoint de embeddings do OpenRouter ou sentence-transformers) e reindexe as
coleções com o novo EMBEDDING_DIM.
"""

import hashlib
import math
import re
import unicodedata

_NON_ALNUM = re.compile(r"[^a-z0-9]+")

STOPWORDS = frozenset(
    "a o e as os um uma uns umas de da do das dos em no na nos nas por para pra com sem que se "
    "me mim meu minha meus minhas eu voce ele ela ja ta to estou esta estao tenho tem tive "
    "muito muita pouco pouca mais menos desde hoje ontem dia dias ao aos sinto sentindo".split()
)


def normalize_text(text: str) -> str:
    """Minúsculas, sem acentos e apenas [a-z0-9] separados por espaço."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _NON_ALNUM.sub(" ", without_accents).strip()


def tokenize(text: str) -> list[str]:
    return [token for token in normalize_text(text).split() if token not in STOPWORDS and len(token) > 1]


def _features(tokens: list[str]) -> list[tuple[str, float]]:
    features: list[tuple[str, float]] = [(f"w:{token}", 1.0) for token in tokens]
    features += [(f"b:{a}_{b}", 0.7) for a, b in zip(tokens, tokens[1:], strict=False)]
    for token in tokens:
        padded = f"#{token}#"
        features += [(f"c:{padded[i : i + 4]}", 0.3) for i in range(max(len(padded) - 3, 1))]
    return features


def embed_text(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    for feature, weight in _features(tokenize(text)):
        digest = int.from_bytes(hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest(), "big")
        sign = 1.0 if digest >> 63 else -1.0
        vector[digest % dim] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        # Texto sem termos úteis: vetor unitário fixo evita divisão por zero na similaridade cosseno.
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]
