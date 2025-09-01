import os
from typing import Optional
from supabase import create_client, Client

_SUPABASE_URL = os.getenv("SUPABASE_URL")
_SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase: Optional[Client] = None
if _SUPABASE_URL and _SUPABASE_KEY:
    try:
        supabase = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    except Exception as e:
        print("Supabase init failed:", e)
        supabase = None
