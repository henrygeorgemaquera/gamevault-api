from slowapi import Limiter
from slowapi.util import get_remote_address

# Limita las peticiones según la IP de quien llama
limiter = Limiter(key_func=get_remote_address)
