"""Attention, written out. No library that does it for you."""

import numpy as np


def softmax_rows(scores):
    scores = np.asarray(scores, dtype=float)
    steadied = scores - np.max(scores, axis=-1, keepdims=True)
    exponentiated = np.exp(steadied)
    return exponentiated / np.sum(exponentiated, axis=-1, keepdims=True)


def attention_weights(queries, keys):
    queries = np.asarray(queries, dtype=float)
    keys = np.asarray(keys, dtype=float)
    key_width = keys.shape[-1]
    scores = (queries @ keys.T) / np.sqrt(key_width)
    return softmax_rows(scores)


def scaled_dot_product_attention(queries, keys, values):
    weights = attention_weights(queries, keys)
    values = np.asarray(values, dtype=float)
    return weights @ values


if __name__ == "__main__":
    demo_scores = np.array([[1.0, 2.0, 3.0], [1.0, 1.0, 1.0], [3.0, 2.0, 1.0]])
    weighted = softmax_rows(demo_scores)
    print(f"every row of a softmax adds to one: {weighted.sum(axis=-1)}")

    positions = np.arange(12, dtype=float).reshape(3, 4)
    answered = scaled_dot_product_attention(positions, positions, positions)
    print(f"three positions attending over three, four numbers each -> {answered.shape}")
