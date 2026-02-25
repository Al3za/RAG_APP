import hashlib

def email_to_namespace(email: str) -> str:
    return hashlib.sha256(email.encode()).hexdigest()