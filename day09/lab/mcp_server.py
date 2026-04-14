# mcp_server.py — Mock MCP Server
import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# ─────────────────────────────────────────────
# Tool Schemas
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Tìm kiếm Knowledge Base nội bộ bằng semantic search.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Câu hỏi hoặc keyword"},
                "top_k": {"type": "integer", "description": "Số chunks trả về", "default": 3},
            },
            "required": ["query"],
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Tra cứu thông tin ticket từ hệ thống Jira nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
    },
}

# ─────────────────────────────────────────────
# Tool 1: search_kb — ChromaDB thật
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """Search Knowledge Base qua ChromaDB."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(__file__))
        from workers.retrieval import retrieve_dense

        chunks = retrieve_dense(query, top_k=top_k)
        sources = list({c["source"] for c in chunks})

        return {
            "chunks": chunks,
            "sources": sources,
            "total_found": len(chunks),
        }

    except Exception as e:
        # Fallback mock nếu ChromaDB chưa sẵn sàng
        print(f"  [search_kb] ChromaDB error: {e} → dùng mock")
        return {
            "chunks": [
                {
                    "text": f"[MOCK] Query: '{query}' — ChromaDB chưa sẵn sàng: {e}",
                    "source": "mock_fallback",
                    "score": 0.0,
                }
            ],
            "sources": ["mock_fallback"],
            "total_found": 0,
            "error": str(e),
        }

# ─────────────────────────────────────────────
# Tool 2: get_ticket_info — Mock data
# ─────────────────────────────────────────────

MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": [
            "slack:#incident-p1",
            "email:incident@company.internal",
            "pagerduty:oncall",
        ],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
    "IT-0001": {
        "ticket_id": "IT-0001",
        "priority": "P3",
        "title": "Yêu cầu cấp quyền truy cập Level 2 cho nhân viên mới",
        "status": "pending_approval",
        "assignee": "it.helpdesk@company.internal",
        "created_at": "2026-04-12T08:00:00",
        "sla_deadline": "2026-04-14T08:00:00",
        "escalated": False,
    },
}

def tool_get_ticket_info(ticket_id: str) -> dict:
    """Tra cứu thông tin ticket từ mock database."""
    key = ticket_id.upper().strip()
    ticket = MOCK_TICKETS.get(key)

    if ticket:
        return ticket

    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy.",
        "hint": f"Mock IDs có sẵn: {list(MOCK_TICKETS.keys())}",
    }

# ─────────────────────────────────────────────
# Dispatch Layer
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
}

def list_tools() -> list:
    """Trả về danh sách tools (MCP discovery)."""
    return list(TOOL_SCHEMAS.values())

def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """Gọi tool theo tên và input (MCP execution)."""
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' không tồn tại.",
            "available": list(TOOL_REGISTRY.keys()),
        }
    try:
        return TOOL_REGISTRY[tool_name](**tool_input)
    except TypeError as e:
        return {
            "error": f"Input không hợp lệ cho '{tool_name}': {e}",
            "schema": TOOL_SCHEMAS[tool_name]["inputSchema"],
        }
    except Exception as e:
        return {"error": f"Tool '{tool_name}' lỗi: {e}"}

# ─────────────────────────────────────────────
# Test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("MCP Server — Sprint 3 Test")
    print("=" * 55)

    # Discover
    print("\n📋 Tools available:")
    for t in list_tools():
        print(f"  • {t['name']}: {t['description']}")

    # Test search_kb
    print("\n🔍 Test search_kb — query: 'SLA P1 resolution time'")
    result = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    print(f"  total_found: {result.get('total_found')}")
    print(f"  sources: {result.get('sources')}")
    for c in result.get("chunks", []):
        print(f"  [{c.get('score')}] {c.get('source')}: {c.get('text', '')[:80]}...")

    # Test get_ticket_info — found
    print("\n🎫 Test get_ticket_info — P1-LATEST")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    print(f"  {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    print(f"  assignee: {ticket.get('assignee')}")
    print(f"  sla_deadline: {ticket.get('sla_deadline')}")
    print(f"  notifications: {ticket.get('notifications_sent')}")

    # Test get_ticket_info — not found
    print("\n🎫 Test get_ticket_info — IT-9999 (không tồn tại)")
    err = dispatch_tool("get_ticket_info", {"ticket_id": "IT-9999"})
    print(f"  {err.get('error')}")
    print(f"  {err.get('hint')}")

    print("\n✅ Sprint 3 done.")