from urllib.parse import urlparse

def normalize_domain(domain: str) -> str:
    if "://" in domain:
        domain = domain.split("://")[1]
    if "/" in domain:
        domain = domain.split("/")[0]
    if domain.startswith("www."):
        domain = domain[4:]
    return domain.lower()

def validate_origin(origin: str | None, allowed_domains: list[str]) -> bool:
    if not origin:
        return False
    try:
        parsed = urlparse(origin)
        origin_domain = parsed.netloc.lower()
        if origin_domain.startswith("www."):
            origin_domain = origin_domain[4:]
    except Exception:
        return False

    for allowed in allowed_domains:
        allowed_norm = normalize_domain(allowed)
        if allowed_norm.startswith("*."):
            base = allowed_norm[2:]
            if origin_domain == base or origin_domain.endswith(f".{base}"):
                return True
        elif origin_domain == allowed_norm:
            return True
        elif allowed_norm.startswith("localhost:") and origin_domain == allowed_norm:
            return True
    return False