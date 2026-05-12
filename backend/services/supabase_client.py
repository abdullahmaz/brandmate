"""
Supabase client factory.

Brandmate is a multi-user app with Row Level Security enabled on
`chats` and `messages`. RLS filters rows by `auth.uid()`, which is read
from the JWT attached to each request. Every DB-touching endpoint
therefore needs a *per-request* Supabase client whose PostgREST session
carries the caller's access token. That is what `client_for_user()`
returns.

`supabase_client.get_client()` is kept as a backwards-compatible alias
for the anon (unauthenticated) client. Use it only for places that
genuinely need anon access (e.g. checking server health, future signup
flows). It will NOT see any RLS-protected rows.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        self.client: Client | None = None

        if not self.url or not self.key:
            print("WARNING: Supabase credentials not set. Database features will be disabled.")
            return

        try:
            self.client = create_client(self.url, self.key)
            print("Supabase client initialized successfully")
        except Exception as e:
            print(f"Error initializing Supabase client: {e}")
            self.client = None

    def get_client(self) -> Client:
        """Anon client. Cannot see RLS-protected user data."""
        if not self.client:
            raise Exception("Supabase client not available. Please check your credentials.")
        return self.client

    def client_for_user(self, access_token: str) -> Client:
        """
        Return a Supabase client whose PostgREST session carries the given
        user JWT. RLS policies that reference `auth.uid()` will then see
        the caller as that user.

        We mint a fresh client per request rather than mutating the shared
        anon client, so concurrent requests cannot leak auth context
        between users.
        """
        if not self.url or not self.key:
            raise Exception("Supabase client not available. Please check your credentials.")

        client = create_client(self.url, self.key)
        # supabase-py exposes the underlying PostgREST client; setting the
        # auth header here makes RLS see the request as the JWT's subject.
        client.postgrest.auth(access_token)
        return client


supabase_client = SupabaseClient()
