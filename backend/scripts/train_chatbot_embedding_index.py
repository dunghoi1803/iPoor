#!/usr/bin/env python3
"""Train embedding index for chatbot semantic search - numpy version"""
import sys
sys.path.insert(0, "/app")

import json
import os
from datetime import datetime
import numpy as np


# Canonical mappings for intent/topic/spatial alias
CANONICAL_MAPPINGS = [
    # Stats aliases
    {"text": "số liệu hộ nghèo", "intent": "stats", "topic": "count", "canonical": "stats|status=poor"},
    {"text": "số liệu hộ cận nghèo", "intent": "stats", "topic": "count", "canonical": "stats|status=near_poor"},
    {"text": "số liệu thoát nghèo", "intent": "stats", "topic": "count", "canonical": "stats|status=escaped_poverty"},
    {"text": "thống kê hộ nghèo", "intent": "stats", "topic": "summary", "canonical": "stats|status=poor"},
    {"text": "tỷ lệ nghèo", "intent": "stats", "topic": "rate", "canonical": "stats|status=poor|mode=rate"},
    
    # Region aliases
    {"text": "đbscl", "intent": "stats", "scope_type": "region", "scope_name": "Đồng bằng sông Cửu Long"},
    {"text": "đồng bằng sông cửu long", "intent": "stats", "scope_type": "region", "scope_name": "Đồng bằng sông Cửu Long"},
    {"text": "miền tây", "intent": "stats", "scope_type": "region", "scope_name": "Đồng bằng sông Cửu Long"},
    {"text": "đbsh", "intent": "stats", "scope_type": "region", "scope_name": "Đồng bằng sông Hồng"},
    {"text": "đồng bằng sông hồng", "intent": "stats", "scope_type": "region", "scope_name": "Đồng bằng sông Hồng"},
    {"text": "tdmnmbb", "intent": "stats", "scope_type": "region", "scope_name": "Trung du và miền núi Bắc Bộ"},
    {"text": "tây nguyên", "intent": "stats", "scope_type": "region", "scope_name": "Tây Nguyên"},
    {"text": "btb", "intent": "stats", "scope_type": "region", "scope_name": "Bắc Trung Bộ"},
    {"text": "dhtt", "intent": "stats", "scope_type": "region", "scope_name": "Duyên hản miền Trung"},
    {"text": "đông nam bộ", "intent": "stats", "scope_type": "region", "scope_name": "Đông Nam Bộ"},
    
    # Province aliases
    {"text": "tp hcm", "intent": "stats", "scope_type": "province", "scope_name": "Thành phố Hồ Chí Minh"},
    {"text": "tp hà nội", "intent": "stats", "scope_type": "province", "scope_name": "Thành phố Hà Nội"},
    
    # Policy topic aliases
    {"text": "chính sách hỗ trợ giảm nghèo", "intent": "policy", "topic": "support_reduction"},
    {"text": "hỗ trợ hộ nghèo", "intent": "policy", "topic": "support_poor"},
    {"text": "hỗ trợ sau thoát nghèo", "intent": "policy", "topic": "post_escaped"},
    {"text": "tín dụng ưu đãi", "intent": "policy", "topic": "credit"},
    {"text": "bảo hiểm xã hội", "intent": "policy", "topic": "social_insurance"},
    {"text": "bảo hiểm y tế", "intent": "policy", "topic": "health_insurance"},
    {"text": "hỗ trợ giáo dục", "intent": "policy", "topic": "education"},
    {"text": "hỗ trợ nhà ở", "intent": "policy", "topic": "housing"},
    {"text": "giải quyết việc làm", "intent": "policy", "topic": "employment"},
    
    # FAQ topics
    {"text": "tiêu chí nghèo đa chiều", "intent": "faq", "topic": "mpi_criteria"},
    {"text": "chuẩn nghèo", "intent": "faq", "topic": "poverty_standard"},
    {"text": "cách xác định hộ nghèo", "intent": "faq", "topic": "identification"},
    {"text": "quy trình rà soát hộ nghèo", "intent": "faq", "topic": "assessment"},
]


def main():
    # Create data directory
    embed_dir = "/app/data"
    os.makedirs(embed_dir, exist_ok=True)
    
    # Load embedding model
    print("Loading embedding model...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("intfloat/multilingual-e5-small")
        print(f"Loaded: multilingual-e5-small")
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    # Encode texts
    texts = [m["text"] for m in CANONICAL_MAPPINGS]
    print(f"Encoding {len(texts)} texts...")
    
    embeddings = model.encode(
        [f"query: {t}" for t in texts],
        normalize_embeddings=True,
        show_progress_bar=False
    )
    
    # Save vectors as numpy
    vectors_file = os.path.join(embed_dir, "chatbot_vectors.npy")
    np.save(vectors_file, embeddings)
    print(f"Saved vectors: {vectors_file}")
    
    # Save metadata
    metadata_file = os.path.join(embed_dir, "chatbot_metadata.json")
    with open(metadata_file, 'w') as f:
        json.dump(CANONICAL_MAPPINGS, f, ensure_ascii=False, indent=2)
    print(f"Saved metadata: {metadata_file}")
    
    # Save version/info
    info = {
        "version": "v1",
        "count": len(CANONICAL_MAPPINGS),
        "dim": embeddings.shape[1],
        "trained_at": datetime.now().isoformat(),
        "model": "intfloat/multilingual-e5-small"
    }
    info_file = os.path.join(embed_dir, "chatbot_info.json")
    with open(info_file, 'w') as f:
        json.dump(info, f, indent=2)
    print(f"Saved info: {info_file}")
    
    # Test loading
    print("\nTesting index load...")
    test_vectors = np.load(vectors_file)
    with open(metadata_file, 'r') as f:
        test_metadata = json.load(f)
    print(f"Loaded: {test_vectors.shape}, {len(test_metadata)} items")
    
    # Test search
    print("\nTesting search...")
    query = "miền tây hộ nghèo"
    query_vec = model.encode(f"query: {query}", normalize_embeddings=True)
    scores = np.dot(test_vectors, query_vec)
    top_idx = np.argmax(scores)
    print(f"  Query: '{query}'")
    print(f"  Top match: '{test_metadata[top_idx]['text']}' (score: {scores[top_idx]:.3f})")
    
    print("\nDone!")


if __name__ == "__main__":
    main()