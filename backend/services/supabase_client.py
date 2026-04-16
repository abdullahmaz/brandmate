import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        self.client = None
        
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
        if not self.client:
            raise Exception("Supabase client not available. Please check your credentials.")
        return self.client

# Global instance
supabase_client = SupabaseClient()
