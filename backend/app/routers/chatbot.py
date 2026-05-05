from typing import Any, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import text, or_, and_, func
import requests
import hashlib
import re
import os

import redis
import uuid
import json
import numpy as np
from datetime import datetime, timedelta
from .. import models, schemas, deps
from ..config import get_settings

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
settings = get_settings()


def on_startup():
    """Initialize embedding model and index on startup"""
    # Pre-load embedding model
    try:
        model = get_embedding_model()
        if model:
            print(f"Embedding model ready")
    except Exception as e:
        print(f"Embedding init warning: {e}")
    
    # Load numpy index (lazy load on first search)

# Initialize Redis client
redis_client = None
try:
    if settings.redis_host and settings.redis_port and settings.redis_password:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        redis_client.ping()
except Exception as e:
    print(f"Redis connection failed: {e}")
    redis_client = None


# In-memory conversation state fallback
_memory_state: dict[str, dict] = {}


def get_conversation_state(conversation_id: str | None, user_id: int | None = None) -> dict:
    """Get conversation state from Redis or memory with user isolation"""
    if not conversation_id:
        return {}
    
    state_key = get_state_key(conversation_id, user_id)
    
    if redis_client:
        try:
            data = redis_client.get(state_key)
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis get state error: {e}")
    
    # Fallback to memory (without user prefix)
    return _memory_state.get(conversation_id, {})


def set_conversation_state(conversation_id: str | None, state: dict, user_id: int | None = None) -> None:
    """Set conversation state in Redis or memory with user isolation"""
    if not conversation_id:
        return
    
    state_key = get_state_key(conversation_id, user_id)
    
    if redis_client:
        try:
            redis_client.setex(state_key, 1800, json.dumps(state))
        except Exception as e:
            print(f"Redis set state error: {e}")
    else:
        # Memory fallback without user isolation
        _memory_state[conversation_id] = state


def normalize_message(msg: str) -> str:
    """Normalize message for cache key"""
    return msg.lower().strip()


def get_cache_key(message: str) -> str:
    """Cache key with version"""
    normalized = normalize_message(message)
    return f"chatbot:v2:msg:{hashlib.md5(normalized.encode()).hexdigest()}"


# FAQ Cache Keys (v1 format)
FAQ_CACHE_VERSION = "v1"
FAQ_KEY_PREFIX = f"chatbot:faq:{FAQ_CACHE_VERSION}"


def get_faq_cache_key(message: str) -> str:
    """Generate cache key for FAQ lookup"""
    normalized = normalize_message(message)
    hash_key = hashlib.md5(normalized.encode()).hexdigest()[:16]
    return f"{FAQ_KEY_PREFIX}:q:{hash_key}"


def get_faq_index_key(canonical_question: str) -> str:
    """Index key for canonical question"""
    normalized = normalize_message(canonical_question)
    return f"{FAQ_KEY_PREFIX}:index:{normalized[:50]}"


def check_faq_cache(message: str) -> tuple[bool, str]:
    """Check if message matches FAQ question"""
    if not redis_client:
        return False, ""
    
    try:
        cache_key = get_faq_cache_key(message)
        cached = redis_client.get(cache_key)
        if cached:
            return True, cached
    except Exception as e:
        print(f"FAQ cache check error: {e}")
    
    return False, ""


@router.get("/cache/health")
async def cache_health() -> dict:
    """Check Redis cache health status"""
    if not redis_client:
        return {"status": "disconnected", "redis": False, "faq_version": None}
    
    try:
        info = redis_client.info("stats")
        return {
            "status": "healthy", 
            "redis": True,
            "faq_version": FAQ_CACHE_VERSION,
            "keys": redis_client.dbsize(),
            "memory": redis_client.info("memory").get("used_memory_human", "unknown"),
        }
    except Exception as e:
        return {"status": "error", "redis": False, "error": str(e)}


# Source labels for responses
SOURCE_LABELS = {
    "faq_cache": "Từ FAQ cache",
    "direct_sql": "Từ CSDL tổng hợp",
    "policies": "Từ chính sách",
    "ollama": "Từ AI",
    "fallback": "Từ AI (dự phòng)",
}

# Default suggestions for different contexts
DEFAULT_SUGGESTIONS = {
    "stats": ["Xem qua các năm", "Xem theo tỉnh", "Xem cận nghèo"],
    "policy": ["Xem chi tiết chính sách", "Các điều kiện nhận hỗ trợ", "Tìm chính sách theo năm"],
    "default": ["Số liệu hộ nghèo ở Hà Nội", "Tiêu chí đo lường nghèo", "Chính sách hỗ trợ giảm nghèo"],
}


# Canonical Query Schema
class CanonicalQuery(BaseModel):
    intent: str = "unknown"  # stats | policy | faq | help | unknown
    scope_type: str | None = None  # country | region | province | district | commune
    scope_name: str | None = None
    status: str | None = None  # poor | near_poor | escaped_poverty
    year: int | None = None
    year_from: int | None = None
    year_to: int | None = None
    mode: str = "latest"  # latest | single | trend | region_provinces | overview
    topic: str | None = None
    target: str | None = None
    confidence: float = 0.0

    def to_canonical_string(self) -> str:
        """Build canonical string from non-null fields in fixed order"""
        parts = [f"intent={self.intent}"]
        if self.scope_type:
            parts.append(f"scope_type={self.scope_type}")
        if self.scope_name:
            parts.append(f"scope_name={self.scope_name}")
        if self.status:
            parts.append(f"status={self.status}")
        if self.year:
            parts.append(f"year={self.year}")
        if self.year_from:
            parts.append(f"year_from={self.year_from}")
        if self.year_to:
            parts.append(f"year_to={self.year_to}")
        parts.append(f"mode={self.mode}")
        if self.topic:
            parts.append(f"topic={self.topic}")
        if self.target:
            parts.append(f"target={self.target}")
        return "|".join(parts)

    def to_hash(self) -> str:
        """Generate stable hash for caching"""
        return hashlib.md5(self.to_canonical_string().encode()).hexdigest()[:16]


# Intent labels
INTENT_STATS = "stats"
INTENT_POLICY = "policy"
INTENT_FAQ = "faq"
INTENT_HELP = "help"
INTENT_UNKNOWN = "unknown"


# Hybrid query thresholds
CANONICAL_HIGH_CONF = 0.85
CANONICAL_MID_CONF = 0.65
EMBEDDING_THRESHOLD = 0.82


def hybrid_search(db: Session, message: str, context: dict = None) -> tuple[CanonicalQuery, str]:
    """Hybrid search: rule-based canonical first, then numpy embedding"""
    # Rule-based canonical
    canonical = parse_to_canonical(db, message, context)
    
    source = "canonical"
    
    if canonical.confidence < CANONICAL_HIGH_CONF:
        # Try numpy embedding for fuzzy matching
        try:
            results = search_by_embedding_numpy(
                message,
                top_k=3
            )
            if results and results[0].get("similarity", 0) >= EMBEDDING_THRESHOLD:
                best = results[0]
                canonical.intent = best.get("intent", canonical.intent)
                canonical.topic = best.get("topic", canonical.topic)
                canonical.scope_type = canonical.scope_type or best.get("scope_type")
                canonical.scope_name = canonical.scope_name or best.get("scope_name")
                canonical.confidence = best.get("similarity", 0.7)
                source = "embedding"
        except Exception as e:
            print(f"Embedding search error: {e}")
    
    return canonical, source


def parse_to_canonical(db: Session, message: str, context: dict = None) -> CanonicalQuery:
    """Parse message to CanonicalQuery using rule-based + context"""
    msg = message.lower()
    
    canonical = CanonicalQuery(
        intent=INTENT_UNKNOWN,
        confidence=0.0
    )
    
    # Detect intent
    if is_stats_question(message, context):
        canonical.intent = INTENT_STATS
    elif any(kw in msg for kw in ["chính sách", "hỗ trợ", "thụ hưởng", "điều kiện"]):
        canonical.intent = INTENT_POLICY
    elif "?" in message or any(kw in msg for kw in ["là gì", "như thế nào"]):
        canonical.intent = INTENT_FAQ
    elif any(kw in msg for kw in GREETING_KEYWORDS):
        canonical.intent = INTENT_HELP
    
    # Parse filters
    filters = parse_stats_filters(db, message, context)
    
    # Map to canonical
    if filters.get("scope_type"):
        canonical.scope_type = filters["scope_type"]
        canonical.scope_name = filters.get("scope_name")
    if filters.get("status"):
        canonical.status = filters["status"]
    if filters.get("year"):
        canonical.year = filters["year"]
    if filters.get("year_from"):
        canonical.year_from = filters["year_from"]
    if filters.get("year_to"):
        canonical.year_to = filters["year_to"]
    if filters.get("trend"):
        canonical.mode = "trend"
    if filters.get("mode"):
        canonical.mode = filters["mode"]
    
    # Calculate confidence
    score = 0.0
    if canonical.intent != INTENT_UNKNOWN:
        score += 0.3
    if canonical.scope_type:
        score += 0.25
    if canonical.status:
        score += 0.15
    if canonical.year or canonical.year_from:
        score += 0.15
    if not context:
        score += 0.15
    else:
        score += 0.15
    
    canonical.confidence = min(score, 0.95)
    
    return canonical


def remove_vietnamese_accents(text: str) -> str:
    """Remove Vietnamese accents for canonicalization"""
    import unicodedata
    nfd = unicodedata.normalize('NFD', text)
    result = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    return result


def canonicalize_message(msg: str) -> str:
    """Canonicalize message for cache key - lowercase, no accents, normalized spaces"""
    import unicodedata
    # Normalize to decomposed form
    msg = unicodedata.normalize('NFD', msg.lower().strip())
    # Remove diacritics
    msg = ''.join(c for c in msg if unicodedata.category(c) != 'Mn')
    # Normalize spaces
    msg = re.sub(r'\s+', ' ', msg).strip()
    return msg


# Alias mappings for regions
REGION_ALIASES_CANONICAL = {
    "đbscl": "Đồng bằng sông Cửu Long",
    "dbscl": "Đồng bằng sông Cửu Long",
    "đồng bằng sông cửu long": "Đồng bằng sông Cửu Long",
    "dong bang song cuu long": "Đồng bằng sông Cửu Long",
    "đbsh": "Đồng bằng sông Hồng",
    "dbsh": "Đồng bằng sông Hồng",
    "đồng bằng sông hồng": "Đồng bằng sông Hồng",
    "dong bang song hong": "Đồng bằng sông Hồng",
    "tdmnmbb": "Trung du và miền núi Bắc Bộ",
    "trung du và miền núi bắc bộ": "Trung du và miền núi Bắc Bộ",
    "trung du va mien nui bac bo": "Trung du và miền núi Bắc Bộ",
    "btb": "Bắc Trung Bộ",
    "bắc trung bộ": "Bắc Trung Bộ",
    "bac trung bo": "Bắc Trung Bộ",
    "dhtt": "Duyên hản miền Trung",
    "duyên hản miền trung": "Duyên hản miền Trung",
    "duyen hai mien trung": "Duyên hản miền Trung",
    "tây nguyên": "Tây Nguyên",
    "tay nguyen": "Tây Nguyên",
    "đông nam bộ": "Đông Nam Bộ",
    "dong nam bo": "Đông Nam Bộ",
}


# Status aliases for canonicalization
STATUS_ALIASES_CANONICAL = {
    "hỗ trợ giảm nghèo": "policy_support_reduction",
    "chính sách hỗ trợ": "policy_support_reduction",
    "hỗ trợ hộ nghèo": "policy_support_poor",
    "các hỗ trợ trong công tác giảm nghèo": "policy_support_reduction",
    "ho tro giam ngheo": "policy_support_reduction",
    "chinh sach ho tro": "policy_support_reduction",
}


# ============================================================
# Embedding Model
# ============================================================

EMBEDDING_DIM = 384  # multilingual-e5-small dimension
EMBED_INDEX_NAME = "chatbot_emb_idx"
EMBED_PREFIX = "chatbot:emb:v1"

# Embedding model singleton
_embedding_model = None


def get_embedding_model():
    """Load or return cached embedding model"""
    global _embedding_model
    
    if _embedding_model is not None:
        return _embedding_model
    
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("intfloat/multilingual-e5-small")
        print(f"Loaded embedding model: multilingual-e5-small")
        return _embedding_model
    except ImportError:
        print("sentence-transformers not installed")
        _embedding_model = None
        return None


def encode_text(text: str) -> list[float] | None:
    """Generate embedding vector for text"""
    model = get_embedding_model()
    if model is None:
        return None
    
    try:
        # E5 models need "query: " prefix for semantic search
        embedding = model.encode(f"query: {text}", normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


# ============================================================
# In-Memory Embedding Search (NumPy)
# ============================================================

# In-memory index
_embedding_index = None
_embedding_metadata = []


def load_embedding_index(force: bool = False) -> tuple[np.ndarray, list[dict]]:
    """Load embedding index from numpy file"""
    global _embedding_index, _embedding_metadata
    
    if _embedding_index is not None and not force:
        return _embedding_index, _embedding_metadata
    
    import os
    import json
    
    embed_dir = "/app/data"
    vectors_file = os.path.join(embed_dir, "chatbot_vectors.npy")
    metadata_file = os.path.join(embed_dir, "chatbot_metadata.json")
    
    if os.path.exists(vectors_file) and os.path.exists(metadata_file):
        try:
            _embedding_index = np.load(vectors_file)
            with open(metadata_file, 'r') as f:
                _embedding_metadata = json.load(f)
            print(f"Loaded embedding index: {_embedding_index.shape}")
            return _embedding_index, _embedding_metadata
        except Exception as e:
            print(f"Error loading index: {e}")
    
    return None, []


def search_by_embedding_numpy(
    query_text: str,
    filter_type: str | None = None,
    filter_intent: str | None = None,
    filter_topic: str | None = None,
    top_k: int = 3
) -> list[dict]:
    """Search using numpy cosine similarity"""
    # Load index
    vectors, metadata = load_embedding_index()
    if vectors is None or len(vectors) == 0:
        return []
    
    # Generate query embedding
    query_vec = encode_text(query_text)
    if query_vec is None:
        return []
    
    try:
        query_np = np.array(query_vec)
        
        # Compute cosine similarity: (A . B) / (||A|| * ||B||)
        # Since vectors are normalized, just dot product
        scores = np.dot(vectors, query_np)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] >= 0.5:  # Similarity threshold
                item = metadata[idx].copy()
                item["similarity"] = float(scores[idx])
                results.append(item)
        
        return results
    
    except Exception as e:
        print(f"Numpy search error: {e}")
        return []


# Also keep redis search for compatibility (will fail gracefully if no RediSearch)
def search_by_embedding(
    query_text: str,
    filter_type: str | None = None,
    filter_intent: str | None = None,
    filter_topic: str | None = None,
    top_k: int = 3
) -> list[dict]:
    """Search using embedding - tries numpy first, then Redis fallback"""
    # Try numpy first
    results = search_by_embedding_numpy(query_text, top_k=top_k)
    if results:
        return results
    
    # Fallback to Redis (will fail gracefully if no RediSearch)
    if not redis_client:
        return []
    
    # Generate query embedding
    query_vec = encode_text(query_text)
    if not query_vec:
        return []
    
    try:
        import array
        vec_bytes = array.array('f', query_vec).tobytes()
        
        results = redis_client.execute_command(
            "FT.SEARCH", EMBED_INDEX_NAME,
            f"*=>[KNN {top_k} @vector $vec AS similarity]",
            "PARAMS", "2", "vec", vec_bytes,
            "SORTBY", "similarity",
            "ASC",
            "LIMIT", "0", str(top_k)
        )
        
        if not results or results[0] == 0:
            return []
        
        parsed = []
        for i in range(1, len(results), 2):
            key = results[i].decode() if isinstance(results[i], bytes) else results[i]
            fields = results[i + 1] if i + 1 < len(results) else {}
            
            item = {"key": key}
            if isinstance(fields, dict):
                for k, v in fields.items():
                    key_str = k.decode() if isinstance(k, bytes) else k
                    val = v.decode() if isinstance(v, bytes) else v
                    item[key_str] = val
            
            dist = float(item.get("similarity", 1.0))
            item["similarity"] = 1 - dist
            
            parsed.append(item)
        
        return parsed
    
    except Exception as e:
        # Graceful fallback
        return []


def get_canonical_key(message: str, filters: dict = None) -> str:
    """Generate semantic cache key based on detected intent and filters"""
    msg = canonicalize_message(message)
    
    if filters:
        # Stats request
        if filters.get("scope_type") and filters.get("status"):
            return f"stats|scope={filters['scope_type']}:{filters.get('scope_name', '')}|status={filters['status']}|mode={filters.get('mode', 'single')}"
        elif filters.get("scope_type"):
            return f"stats|scope={filters['scope_type']}:{filters.get('scope_name', '')}"
    
    # Check for policy keywords
    for alias, canonical in STATUS_ALIASES_CANONICAL.items():
        if alias in msg:
            return f"policy|topic={canonical}"
    
    # Default - use canonical message hash
    return f"msg:{hashlib.md5(msg.encode()).hexdigest()[:16]}"


# Context state key helpers with user isolation
def get_state_key(conversation_id: str, user_id: int | None = None) -> str:
    """Get Redis key for conversation state with user isolation"""
    if user_id:
        return f"chatbot:state:user:{user_id}:conv:{conversation_id}"
    return f"chatbot:state:anon:{conversation_id}"


def get_answer_cache_key(message: str, user_id: int | None = None, scope: str = None) -> str:
    """Get cache key for answer with optional user/scope awareness"""
    msg = canonicalize_message(message)
    hash_key = hashlib.md5(msg.encode()).hexdigest()[:16]
    
    if user_id or scope:
        parts = []
        if user_id:
            parts.append(f"user{user_id}")
        if scope:
            parts.append(f"scope{hash(scope) % 10000}")
        return f"chatbot:answer:v1:{':'.join(parts)}:q:{hash_key}"
    
    return f"chatbot:v2:msg:{hash_key}"


INTENT_STATUS_MAP = {
    "poor": ["nghèo", "hộ nghèo", "nghèo đa chiều"],
    "near_poor": ["cận nghèo", "gần nghèo", "cận nghèo"],
    "escaped": ["thoát nghèo", "thoát khỏi nghèo", "đã thoát nghèo"],
}

# Greeting intents
GREETING_KEYWORDS = [
    "bạn là ai", "bot là gì", "giới thiệu", "hello", "xin chào", 
    "chào bot", "chào ipoor", "bạn có thể làm gì", "bạn làm gì"
]

# Static responses for simple queries
STATIC_RESPONSES = {
    "greeting": "Xin chào! Tôi là trợ lý ảo iPOOR, được thiết kế để hỗ trợ bạn trong công tác giảm nghèo đa chiều. Tôi có thể:\n\n- Tra cứu số liệu hộ nghèo, cận nghèo, thoát nghèo theo địa bàn và năm\n- Tìm kiếm các chính sách giảm nghèo\n- Giải đáp thắc mắc về tiêu chí đo lường nghèo\n\nBạn cần tôi giúp gì hôm nay?",
    "help": "Tôi có thể giúp bạn:\n\n1. **Tra cứu số liệu**: 'Hà Nội có bao nhiêu hộ nghèo năm 2026?'\n2. **Tìm chính sách**: 'Các chính sách giảm nghèo mới nhất'\n3. **Thông tin chung**: 'Tiêu chí nghèo đa chiều là gì?'\n\nBạn hỏi tôi đi!",
}

STATUS_LABEL_MAP = {
    "poor": "hộ nghèo",
    "near_poor": "hộ cận nghèo", 
    "escaped": "hộ thoát nghèo",
    "near_poverty": "hộ cận nghèo",
    "escaped_poverty": "hộ thoát nghèo",
}


def detect_intent(message: str) -> Optional[str]:
    """Detect poverty status intent from message"""
    msg = message.lower()
    # Check in order: near_poor -> poor -> escaped (near_poor contains "nghèo")
    for status_key, keywords in INTENT_STATUS_MAP.items():
        for kw in keywords:
            if kw in msg:
                return status_key
    return None


def detect_year(message: str) -> Optional[int]:
    """Extract year from message"""
    matches = re.findall(r'20\d{2}', message)
    if matches:
        return max(int(y) for y in matches)
    return None


def detect_province(db: Session, message: str) -> Optional[str]:
    """Detect province from message"""
    msg = message.lower()
    
    # Get all provinces from dashboard_aggregates
    provinces = db.query(models.DashboardAggregate.scope_name).filter(
        models.DashboardAggregate.scope_type == "province"
    ).distinct().all()
    
    for (province,) in provinces:
        if province and province.lower() in msg:
            return province
    
    # Also check from locations router data
    locations = db.query(models.DashboardAggregate.scope_name).filter(
        or_(
            models.DashboardAggregate.scope_type == "province",
            models.DashboardAggregate.scope_type == "region"
        )
    ).distinct().all()
    
    for (loc,) in locations:
        if loc and loc.lower() in msg:
            return loc
    
    return None


def detect_greeting(message: str) -> Optional[str]:
    """Detect greeting intent"""
    msg = message.lower()
    for kw in GREETING_KEYWORDS:
        if kw in msg:
            return "greeting"
    return None


def detect_help(message: str) -> Optional[str]:
    """Detect help intent"""
    msg = message.lower()
    help_keywords = ["giúp", "hướng dẫn", "cách sử dụng", "sử dụng như thế nào", "help", "help me"]
    for kw in help_keywords:
        if kw in msg:
            return "help"
    return None


STATS_KEYWORDS = [
    "bao nhiêu", "số liệu", "thống kê", "tỷ lệ", 
    "hộ nghèo", "hộ cận nghèo", "thoát nghèo",
    "tổng cộng", "tổng số", "cả nước",
    "các năm", "qua các năm", "theo năm"
]

# Region aliases for detection (combined old + canonical)
REGION_ALIASES = {
    "đồng bằng sông hồng": "Đồng bằng sông Hồng",
    "đbsh": "Đồng bằng sông Hồng",
    "đồng bằng sông cửu long": "Đồng bằng sông Cửu Long",
    "đbscl": "Đồng bằng sông Cửu Long",
    "đồng bằng sông mekong": "Đồng bằng sông Cửu Long",
    "trung du và miền núi bắc bộ": "Trung du và miền núi Bắc Bộ",
    "tdmnmbb": "Trung du và miền núi Bắc Bộ",
    "bắc trung bộ": "Bắc Trung Bộ",
    "btb": "Bắc Trung Bộ",
    "duyên hản miền trung": "Duyên hản miền Trung",
    "dhtt": "Duyên hản miền Trung",
    "tây nguyên": "Tây Nguyên",
    "tn": "Tây Nguyên",
    "đông nam bộ": "Đông Nam Bộ",
    "dnb": "Đông Nam Bộ",
}


# Follow-up keywords that inherit from context
FOLLOWUP_KEYWORDS = [
    "vậy", "còn", "thế", "năm", "còn gì", "tiếp", "tăng", "giảm",
    "xem thêm", "cho xem", "chi tiết hơn", "thêm",
]


def is_stats_question(message: str, context: dict = None) -> bool:
    """Detect if message is asking for statistics or follow-up"""
    msg = message.lower()
    
    # Check direct stats keywords
    for kw in STATS_KEYWORDS:
        if kw in msg:
            return True
    
    # Check follow-up keywords - only if we have context
    if context and context.get("scope_type"):
        for kw in FOLLOWUP_KEYWORDS:
            if kw in msg:
                return True
    
    return False


def detect_year_range(message: str) -> dict:
    """Detect year range from message"""
    msg = message.lower()
    result = {"year": None, "year_from": None, "year_to": None, "trend": False}
    
    # Detect range: "từ 2021 đến 2026"
    range_match = re.search(r'từ\s*(20\d{2})\s*đến\s*(20\d{2})', msg)
    if range_match:
        result["year_from"] = int(range_match.group(1))
        result["year_to"] = int(range_match.group(2))
        return result
    
    # Detect trend keywords
    trend_keywords = ["qua các năm", "các năm", "theo năm", "biến động"]
    for kw in trend_keywords:
        if kw in msg:
            result["trend"] = True
    
    # Single year
    matches = re.findall(r'20\d{2}', message)
    if matches:
        result["year"] = max(int(y) for y in matches)
    
    return result


def parse_stats_filters(db: Session, message: str, context: dict = None) -> dict:
    """Parse filters from stats question with context inheritance"""
    msg = message.lower()
    filters = {
        "scope_type": None, 
        "scope_name": None, 
        "status": None, 
        "year": None,
        "year_from": None,
        "year_to": None,
        "trend": False,
        "mode": "single",  # single, trend, region_provinces
    }
    
    # First detect year range/trend
    year_info = detect_year_range(message)
    filters.update(year_info)
    
    # Detect status
    if "cận nghèo" in msg or "gần nghèo" in msg:
        filters["status"] = "near_poor"
    elif "thoát nghèo" in msg or "đã thoát" in msg:
        filters["status"] = "escaped_poverty"
    elif "nghèo" in msg:
        filters["status"] = "poor"
    
    # Detect location - check region first, then province
    # Normalize message
    normalized_msg = msg
    for alias, region_name in REGION_ALIASES.items():
        if alias in normalized_msg:
            filters["scope_type"] = "region"
            filters["scope_name"] = region_name
            # Check if asking for provinces in region
            if "các tỉnh" in msg or "tỉnh nào" in msg:
                filters["mode"] = "region_provinces"
            break
    
    # If not region, check province
    if not filters["scope_type"]:
        if "cả nước" in msg or "toàn quốc" in msg:
            filters["scope_type"] = "country"
            filters["scope_name"] = "Cả nước"
        else:
            all_scopes = db.query(models.DashboardAggregate.scope_name, models.DashboardAggregate.scope_type).filter(
                models.DashboardAggregate.scope_type.in_(["province"])
            ).distinct().all()
            
            for scope_name, scope_type in all_scopes:
                if scope_name and scope_name.lower() in msg:
                    filters["scope_type"] = scope_type
                    filters["scope_name"] = scope_name
                    break
    
# Inherit from context for follow-up questions
    if context and context.get("scope_type"):
        # Always inherit location if not explicitly specified
        if not filters["scope_type"]:
            filters["scope_type"] = context["scope_type"]
            filters["scope_name"] = context["scope_name"]
        
        # Inherit status unless explicitly changed (e.g., "còn cận nghèo")
        if not filters["status"] and context.get("status"):
            # Check if asking about different status
            if "cận nghèo" not in msg and "thoát nghèo" not in msg:
                filters["status"] = context["status"]
        
        # Inherit trend unless year is explicitly specified
        if not filters["year"] and not filters["year_from"]:
            filters["trend"] = context.get("trend", False)
    
    return filters


def query_stats_direct(db: Session, filters: dict) -> dict:
    """Query dashboard_aggregates directly for stats"""
    from sqlalchemy import func
    from ..routers.dashboard import get_region_map
    
    results = {}
    
    scope_type = filters.get("scope_type")
    scope_name = filters.get("scope_name")
    status = filters.get("status")
    year = filters.get("year")
    year_from = filters.get("year_from")
    year_to = filters.get("year_to")
    mode = filters.get("mode", "single")
    
    # Handle region_provinces mode - get all provinces in region
    if mode == "region_provinces" and scope_type == "region":
        region_map = get_region_map()
        provinces_in_region = [p for p, r in region_map.items() if r == scope_name]
        
        query = db.query(
            models.DashboardAggregate.scope_name,
            models.DashboardAggregate.survey_year,
            models.DashboardAggregate.poverty_status,
            models.DashboardAggregate.household_count,
        ).filter(
            models.DashboardAggregate.scope_name.in_(provinces_in_region),
            models.DashboardAggregate.scope_type == "province",
            models.DashboardAggregate.survey_year == (year or db.query(func.max(models.DashboardAggregate.survey_year)).scalar()),
        )
        
        if status:
            query = query.filter(models.DashboardAggregate.poverty_status == status)
        
        records = query.all()
        
        for r in records:
            province = r[0]
            if province not in results:
                results[province] = r[3]  # household_count
        
        return results
    
    # Build base query
    query = db.query(models.DashboardAggregate)
    
    if scope_type == "province":
        query = query.filter(
            models.DashboardAggregate.scope_name == scope_name,
            models.DashboardAggregate.scope_type == "province"
        )
    elif scope_type == "region":
        query = query.filter(
            models.DashboardAggregate.scope_name == scope_name,
            models.DashboardAggregate.scope_type == "region"
        )
    elif scope_type == "country" or not scope_type:
        query = query.filter(models.DashboardAggregate.scope_type == "country")
    
    # Year range filter
    if year_from and year_to:
        query = query.filter(
            models.DashboardAggregate.survey_year >= year_from,
            models.DashboardAggregate.survey_year <= year_to
        )
    elif year:
        query = query.filter(models.DashboardAggregate.survey_year == year)
    
    # Status filter
    if status:
        query = query.filter(models.DashboardAggregate.poverty_status == status)
    
    # Order by year for trend data
    records = query.order_by(
        models.DashboardAggregate.survey_year.desc(),
        models.DashboardAggregate.poverty_status
    ).all()
    
    # Group results by year and status
    for r in records:
        status_val = r.poverty_status.value if hasattr(r.poverty_status, 'value') else str(r.poverty_status)
        year_val = r.survey_year
        if year_val not in results:
            results[year_val] = {}
        results[year_val][status_val] = r.household_count
    
    return results


def format_vietnamese_number(n: int) -> str:
    """Format number with dot as thousands separator: 3.160"""
    return f"{n:,}".replace(",", ".")


def format_stats_response(filters: dict, data: dict) -> str:
    """Format deterministic markdown response for stats"""
    if not data:
        scope_name = filters.get("scope_name") or "cả nước"
        return f"Không tìm thấy số liệu cho {scope_name}."
    
    scope_type = filters.get("scope_type")
    scope_name = filters.get("scope_name") or "cả nước"
    status = filters.get("status")
    trend = filters.get("trend", False)
    mode = filters.get("mode", "single")
    year_from = filters.get("year_from")
    year_to = filters.get("year_to")
    
    # Handle region_provinces mode - return table of provinces
    if mode == "region_provinces" and isinstance(data, dict):
        # Check if data is dict of {province: count}
        if data and all(isinstance(v, int) for v in data.values()):
            rows = []
            for province, count in sorted(data.items(), key=lambda x: -x[1]):
                rows.append(f"| {province} | {format_vietnamese_number(count)} |")
            return f"**Số hộ {STATUS_LABEL_MAP.get(status, 'nghèo')} tại các tỉnh {scope_name} (năm 2026):**\n\n| Tỉnh | Số hộ |\n|------|------|\n" + "\n".join(rows)
    
    years = sorted(data.keys(), reverse=True)
    latest_year = years[0]
    latest_data = data[latest_year]
    
    # TREND MODE - return markdown table
    if trend or len(years) > 1:
        status_label = STATUS_LABEL_MAP.get(status, "nghèo") if status else "tất cả"
        
        # Build table rows
        table_rows = []
        for year in sorted(years):
            year_data = data.get(year, {})
            count = year_data.get(status, year_data.get("poor", 0)) if status else sum(year_data.values())
            table_rows.append(f"| {year} | {format_vietnamese_number(count)} |")
        
        header = f"**Số hộ {status_label} tại {scope_name}:**\n\n| Năm | Số hộ |\n|------|------|\n"
        
        # Add note about missing years
        note = ""
        if year_from and year_to:
            missing = [y for y in range(year_from, year_to + 1) if y not in years]
            if missing:
                note = f"\n_Không có dữ liệu cho năm: {', '.join(map(str, missing))}_"
        
        return header + "\n".join(table_rows) + note
    
    # SINGLE YEAR MODE
    if status:
        count = latest_data.get(status, 0)
        status_label = STATUS_LABEL_MAP.get(status, "hộ")
        return f"Theo dữ liệu tổng hợp mới nhất, năm **{latest_year}**, **{scope_name}** có **{format_vietnamese_number(count)} {status_label}**."
    
    # Overview query - all statuses
    parts = []
    status_order = ["poor", "near_poor", "escaped_poverty"]
    for st in status_order:
        if st in latest_data:
            label = STATUS_LABEL_MAP.get(st, "hộ")
            parts.append(f"{format_vietnamese_number(latest_data[st])} {label}")
    
    if parts:
        return f"Theo dữ liệu tổng hợp năm **{latest_year}**, **{scope_name}**: {', '.join(parts)}."
    
    return f"Không tìm thấy số liệu cho {scope_name}."


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/ask")
async def ask_chatbot(
    payload: ChatRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User | None = Depends(deps.get_current_user_optional)
) -> dict[str, Any]:
    # Get conversation ID and user ID
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    user_id = current_user.id if current_user else None
    
    # Get conversation context with user isolation
    context = get_conversation_state(conversation_id, user_id)
    
    # Determine message type for suggestions
    message_type = "default"
    source = "ollama"
    confidence = 0.5
    suggestion_list = DEFAULT_SUGGESTIONS["default"]
    
    # 0. Check greeting intent first
    greeting_intent = detect_greeting(payload.message)
    if greeting_intent and greeting_intent in STATIC_RESPONSES:
        reply = STATIC_RESPONSES[greeting_intent]
        source = "faq_cache"
        confidence = 0.98
        suggestion_list = DEFAULT_SUGGESTIONS["default"]
        # Cache greeting
        if redis_client:
            try:
                redis_client.setex(get_cache_key(payload.message), 3600, reply)
            except:
                pass
        return {
            "reply": reply, 
            "conversation_id": conversation_id,
            "source": source,
            "confidence": confidence,
            "suggestions": suggestion_list,
        }
    
# 0b. Check help intent
        help_intent = detect_help(payload.message)
        if help_intent and help_intent in STATIC_RESPONSES:
            reply = STATIC_RESPONSES[help_intent]
            source = "faq_cache"
            confidence = 0.98
            suggestion_list = DEFAULT_SUGGESTIONS["default"]
            if redis_client:
                try:
                    redis_client.setex(get_cache_key(payload.message), 3600, reply)
                except:
                    pass
            return {
                "reply": reply, 
                "conversation_id": conversation_id,
                "source": source,
                "confidence": confidence,
                "suggestions": suggestion_list,
            }
    
    # 0c. Check FAQ cache first for common questions
    if redis_client:
        faq_found, faq_reply = check_faq_cache(payload.message)
        if faq_found:
            return {
                "reply": faq_reply, 
                "source": "faq_cache",
                "conversation_id": conversation_id,
                "confidence": 0.95,
                "suggestions": DEFAULT_SUGGESTIONS["default"],
            }
    
    # 1. Check if it's a stats question - query directly without Ollama
    if is_stats_question(payload.message, context):
        filters = parse_stats_filters(db, payload.message, context)
        data = query_stats_direct(db, filters)
        reply = format_stats_response(filters, data)
        
        source = "direct_sql"
        confidence = 0.98
        message_type = "stats"
        
        # Generate suggestions based on context
        suggestion_list = DEFAULT_SUGGESTIONS["stats"]
        if filters.get("scope_name"):
            suggestion_list = [
                f"Xem {filters['scope_name']} qua các năm",
                f"Xem cận nghèo {filters['scope_name']}",
                f"Xem thoát nghèo {filters['scope_name']}",
            ]
        
        # Save conversation state with user isolation
        if filters.get("scope_type"):
            new_state = context.copy()
            new_state.update({
                "last_intent": "stats",
                "scope_type": filters.get("scope_type"),
                "scope_name": filters.get("scope_name"),
                "status": filters.get("status"),
                "trend": filters.get("trend", False),
                "mode": filters.get("mode", "single"),
            })
            set_conversation_state(conversation_id, new_state, user_id)
        
        # Cache the answer with user scope
        if redis_client:
            try:
                cache_key = get_answer_cache_key(payload.message, user_id, filters.get("scope_name"))
                redis_client.setex(cache_key, 3600, reply)
            except:
                pass
        
        return {
            "reply": reply, 
            "source": source,
            "conversation_id": conversation_id,
            "confidence": confidence,
            "suggestions": suggestion_list,
        }
    
    # 1. Check Redis cache first (v2)
    cache_key = get_cache_key(payload.message)
    if redis_client:
        try:
            cached_reply = redis_client.get(cache_key)
            if cached_reply:
                return {"reply": cached_reply, "source": "cache"}
        except Exception as e:
            print(f"Redis get error: {e}")

    # 2. Detect intent and filters
    detected_status = detect_intent(payload.message)
    detected_year = detect_year(payload.message)
    detected_province = detect_province(db, payload.message)
    
    context_sources = []
    
    # A. Search Policies with public filter
    policy_query = db.query(models.Policy)
    if not current_user:
        policy_query = policy_query.filter(models.Policy.is_public == True)
    
    # Extract keywords for policy search
    msg_lower = payload.message.lower()
    raw_keywords = msg_lower.replace("?", "").replace(".", "").replace(",", "").split()
    stop_words = ["là", "có", "của", "cho", "tại", "về", "trong", "cần", "muốn", "hỏi", "biết", "bao", "nhiêu", "như", "thế", "nào", "cho", "tôi", "biết"]
    keywords = [k for k in raw_keywords if len(k) > 1 and k not in stop_words]
    
    if keywords:
        try:
            fts_keywords = " ".join(keywords[:3])
            stmt = text("""
                SELECT id, title, summary 
                FROM policies 
                WHERE MATCH(title, summary, description) AGAINST(:query IN NATURAL LANGUAGE MODE)
                LIMIT 5
            """)
            found_policies = db.execute(stmt, {"query": fts_keywords}).fetchall()
            if found_policies:
                for p in found_policies:
                    if p[1]:  # title
                        context_sources.append(f"- {p[1]}: {p[2] or ''}")
        except Exception as e:
            print(f"FTS policy error: {e}")
    
    # B. Search Stats with exact province match first
    if detected_province:
        # Exact province match
        stats_query = db.query(models.DashboardAggregate).filter(
            and_(
                models.DashboardAggregate.scope_type == "province",
                models.DashboardAggregate.scope_name == detected_province
            )
        )
        if detected_year:
            stats_query = stats_query.filter(models.DashboardAggregate.survey_year == detected_year)
        
        stats = stats_query.order_by(models.DashboardAggregate.survey_year.desc()).all()
        
        if stats:
            for s in stats:
                status_val = s.poverty_status.value if hasattr(s.poverty_status, 'value') else str(s.poverty_status)
                if detected_status and status_val != detected_status:
                    continue
                label = STATUS_LABEL_MAP.get(status_val, status_val)
                context_sources.append(
                    f"- {detected_province} năm {s.survey_year}: {s.household_count} {label}"
                )
    
    if not context_sources and keywords:
        # Fallback to FTS search
        try:
            fts_keywords = " ".join(keywords[:2])
            stmt = text("""
                SELECT survey_year, scope_name, poverty_status, household_count
                FROM dashboard_aggregates
                WHERE MATCH(scope_name) AGAINST(:query IN NATURAL LANGUAGE MODE)
                ORDER BY survey_year DESC
                LIMIT 10
            """)
            results = db.execute(stmt, {"query": fts_keywords}).fetchall()
            
            for r in results:
                year, scope, status_val, count = r[0], r[1], r[2], r[3]
                if detected_status and status_val != detected_status:
                    continue
                label = STATUS_LABEL_MAP.get(status_val, status_val)
                context_sources.append(f"- {scope} năm {year}: {count} {label}")
        except Exception as e:
            print(f"FTS stats error: {e}")

    # Build context
    if context_sources:
        context = "DỮ LIỆU TRUY VẤN TỪ SQL:\n" + "\n".join(context_sources[:10])
    else:
        context = "Không tìm thấy dữ liệu cho câu hỏi của bạn."

    # Add detected filters to context for LLM
    filters_info = []
    if detected_province:
        filters_info.append(f"Địa bàn: {detected_province}")
    if detected_year:
        filters_info.append(f"Năm: {detected_year}")
    if detected_status:
        filters_info.append(f"Trạng thái: {STATUS_LABEL_MAP.get(detected_status, detected_status)}")
    
    if filters_info:
        context += "\n\nBỘ LỌC: " + ", ".join(filters_info)

    # 3. Call Ollama with strict prompt
    ollama_host = getattr(settings, "ollama_host", "http://host.docker.internal:11434")
    ollama_model = getattr(settings, "ollama_model", "gemma:2b")
    
    try:
        prompt = f"""Bạn là trợ lý iPOOR. 

QUY TẮC TRẢ LỜI:
1. Chỉ trả lời dựa trên DỮ LIỆU TRUY VẤN TỪ SQL được cung cấp.
2. Nếu không có dữ liệu, nói "Không tìm thấy dữ liệu cho câu hỏi của bạn."
3. Không suy diễn hay bịa đặt số liệu.
4. Trả lời ngắn gọn, đúng trọng tâm.

DỮ LIỆU:
{context}

CÂU HỎI: {payload.message}

TRẢ LỜI:"""

        response = requests.post(
            f"{ollama_host}/api/generate",
            json={
                "model": ollama_model,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        reply = "Không có câu trả lời."
        if response.status_code == 200:
            reply = response.json().get("response", "Không có câu trả lời.")
            
            # Clean up response - remove prompt echo if present
            if "TRẢ LỜI:" in reply:
                reply = reply.split("TRẢ LỜI:")[-1].strip()
        
        # Cache successful reply (v2 - with version)
        if redis_client and reply and "Không tìm thấy" not in reply:
            try:
                cache_key = get_answer_cache_key(payload.message, user_id, detected_province)
                redis_client.setex(cache_key, 3600, reply)
            except Exception as e:
                print(f"Redis set error: {e}")
        
        source = "ollama"
        confidence = 0.7
        suggestion_list = DEFAULT_SUGGESTIONS["default"]
        
        # Determine suggestions based on context
        if detected_province:
            suggestion_list = [
                f"Xem {detected_province} qua các năm",
                f"Xem cận nghèo {detected_province}",
                "Xem chi tiết Dashboard",
            ]
        
        return {
            "reply": reply,
            "source": source,
            "conversation_id": conversation_id,
            "confidence": confidence,
            "suggestions": suggestion_list,
        }
        
    except Exception as e:
        print(f"Ollama Error: {e}")
        # Use context data we already collected from SQL
        if context_sources:
            reply = "Hiện tại Model AI đang bận. Đây là thông tin tôi tìm được từ CSDL:\n\n" + "\n".join(context_sources[:5])
            source = "fallback"
        else:
            reply = "Hiện tại Model AI đang bận và không tìm được dữ liệu phù hợp."
            source = "fallback"
        
        return {
            "reply": reply,
            "source": source,
            "conversation_id": conversation_id,
            "confidence": 0.3,
            "suggestions": DEFAULT_SUGGESTIONS["default"],
        }


class FeedbackRequest(BaseModel):
    conversation_id: str
    message: str
    helpful: bool
    reason: str | None = None


@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackRequest,
    current_user: models.User | None = Depends(deps.get_current_user_optional)
) -> dict:
    """Submit feedback for chatbot response"""
    if not redis_client:
        return {"status": "error", "message": "Redis not available"}
    
    try:
        feedback_key = f"chatbot:feedback:{payload.conversation_id}:{int(payload.helpful)}"
        feedback_data = {
            "message": payload.message,
            "helpful": payload.helpful,
            "reason": payload.reason,
            "user_id": current_user.id if current_user else None,
            "timestamp": datetime.now().isoformat(),
        }
        redis_client.setex(feedback_key, 86400 * 30, json.dumps(feedback_data))
        
        return {"status": "ok", "message": "Feedback recorded"}
    except Exception as e:
        return {"status": "error", "message": str(e)}