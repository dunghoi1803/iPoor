from typing import Any, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import text, or_, and_, func
import requests
import hashlib
import re

import redis
import uuid
import json
from datetime import datetime, timedelta
from .. import models, schemas, deps
from ..config import get_settings

router = APIRouter(prefix="/chatbot", tags=["chatbot"])
settings = get_settings()

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


def get_conversation_state(conversation_id: str | None) -> dict:
    """Get conversation state from Redis or memory"""
    if not conversation_id:
        return {}
    
    if redis_client:
        try:
            data = redis_client.get(f"chatbot:state:{conversation_id}")
            if data:
                return json.loads(data)
        except Exception as e:
            print(f"Redis get state error: {e}")
    
    return _memory_state.get(conversation_id, {})


def set_conversation_state(conversation_id: str | None, state: dict) -> None:
    """Set conversation state in Redis or memory"""
    if not conversation_id:
        return
    
    if redis_client:
        try:
            redis_client.setex(f"chatbot:state:{conversation_id}", 1800, json.dumps(state))
        except Exception as e:
            print(f"Redis set state error: {e}")
    else:
        _memory_state[conversation_id] = state


def normalize_message(msg: str) -> str:
    """Normalize message for cache key"""
    return msg.lower().strip()


def get_cache_key(message: str) -> str:
    """Cache key with version"""
    normalized = normalize_message(message)
    return f"chatbot:v2:msg:{hashlib.md5(normalized.encode()).hexdigest()}"


# Intent mapping for poverty status
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

# Region name aliases for matching
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


def is_stats_question(message: str) -> bool:
    """Detect if message is asking for statistics"""
    msg = message.lower()
    for kw in STATS_KEYWORDS:
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
    
    # Inherit from context for short follow-up messages
    if context and len(msg.split()) <= 3:
        if not filters["scope_type"] and context.get("scope_type"):
            filters["scope_type"] = context["scope_type"]
            filters["scope_name"] = context["scope_name"]
        if not filters["status"] and context.get("status"):
            filters["status"] = context["status"]
        if not filters["year"] and not filters["trend"]:
            filters["trend"] = context.get("trend", False)
    
    return filters
    
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
    # Get conversation ID
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    
    # Get conversation context
    context = get_conversation_state(conversation_id)
    
    # 0. Check greeting intent first
    greeting_intent = detect_greeting(payload.message)
    if greeting_intent and greeting_intent in STATIC_RESPONSES:
        reply = STATIC_RESPONSES[greeting_intent]
        # Cache greeting
        if redis_client:
            try:
                redis_client.setex(get_cache_key(payload.message), 3600, reply)
            except:
                pass
        return {"reply": reply, "conversation_id": conversation_id}
    
    # 0b. Check help intent
    help_intent = detect_help(payload.message)
    if help_intent and help_intent in STATIC_RESPONSES:
        reply = STATIC_RESPONSES[help_intent]
        if redis_client:
            try:
                redis_client.setex(get_cache_key(payload.message), 3600, reply)
            except:
                pass
        return {"reply": reply, "conversation_id": conversation_id}
    
    # 1. Check if it's a stats question - query directly without Ollama
    if is_stats_question(payload.message):
        filters = parse_stats_filters(db, payload.message, context)
        data = query_stats_direct(db, filters)
        reply = format_stats_response(filters, data)
        
        # Save conversation state
        if filters.get("scope_type"):
            new_state = context.copy()
            new_state.update({
                "scope_type": filters.get("scope_type"),
                "scope_name": filters.get("scope_name"),
                "status": filters.get("status"),
                "trend": filters.get("trend", False),
            })
            set_conversation_state(conversation_id, new_state)
        
        if redis_client:
            try:
                redis_client.setex(get_cache_key(payload.message), 3600, reply)
            except:
                pass
        return {"reply": reply, "source": "direct", "conversation_id": conversation_id}
    
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
                redis_client.setex(cache_key, 3600, reply)
            except Exception as e:
                print(f"Redis set error: {e}")
        
        return {"reply": reply}
        
    except Exception as e:
        print(f"Ollama Error: {e}")
        # Use context data we already collected from SQL
        if context_sources:
            reply = "Hiện tại Model AI đang bận. Đây là thông tin tôi tìm được từ CSDL:\n\n" + "\n".join(context_sources[:5])
        else:
            reply = "Hiện tại Model AI đang bận và không tìm được dữ liệu phù hợp."
        return {"reply": reply}