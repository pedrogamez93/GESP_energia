import base64, struct, hashlib, hmac


_PRF_MAP = {
    0: "sha1",
    1: "sha256",
    2: "sha512",
}

def _pbkdf2(hash_name: str, password: str, salt: bytes, iterations: int, dklen: int) -> bytes:
    return hashlib.pbkdf2_hmac(hash_name, password.encode("utf-8"), salt, iterations, dklen=dklen)

def verify_aspnet_password(hashed: str, password: str) -> bool:
    """
    Verifica un PasswordHash de ASP.NET Identity.
    Soporta:
    - v3+ (ASP.NET Core): 0x01 | prf(4) | iter(4) | saltLen(4) | salt | subkey
    - v2  (ASP.NET Identity clásico): 0x00 | salt(16) | subkey(32)  (PBKDF2-SHA1, 1000 iter)
    """
    try:
        decoded = base64.b64decode(hashed)
    except Exception:
        return False
    if not decoded:
        return False

    version = decoded[0]
    if version == 0x01:
        # ASP.NET Core Identity (v3+)
        if len(decoded) < 13:
            return False
        prf = struct.unpack("<I", decoded[1:5])[0]
        iterations = struct.unpack("<I", decoded[5:9])[0]
        salt_len = struct.unpack("<I", decoded[9:13])[0]
        if 13 + salt_len > len(decoded):
            return False
        salt = decoded[13:13+salt_len]
        subkey = decoded[13+salt_len:]
        hash_name = _PRF_MAP.get(prf, "sha256")
        dk = _pbkdf2(hash_name, password, salt, iterations, len(subkey))
        return hmac.compare_digest(dk, subkey)

    elif version == 0x00:
        # ASP.NET Identity v2 (PBKDF2-SHA1, 1000 iter, salt 16, subkey 32)
        if len(decoded) != 1 + 16 + 32:
            return False
        salt = decoded[1:17]
        subkey = decoded[17:]
        dk = _pbkdf2("sha1", password, salt, 1000, 32)
        return hmac.compare_digest(dk, subkey)

    return False
