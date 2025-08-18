# scripts/reset_password_dev.py
from pathlib import Path; import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

import os, base64, struct, hashlib
from secrets import token_hex
from app.db.session import SessionLocal
from app.db.models.identity import AspNetUser

def create_identity_v3_hash(password: str, iterations: int = 310_000, salt_len: int = 16, subkey_len: int = 32) -> str:
    # Formato Identity v3: 0x01 | prf(4=sha256:1) | iter(4) | saltLen(4) | salt | subkey
    prf_id = 1  # HMAC-SHA256
    salt = os.urandom(salt_len)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=subkey_len)
    blob = bytearray([0x01]) \
        + struct.pack("<I", prf_id) \
        + struct.pack("<I", iterations) \
        + struct.pack("<I", salt_len) \
        + salt + dk
    return base64.b64encode(bytes(blob)).decode("ascii")

EMAIL = "admetasoft@minenergia.cl"
NEW_PASSWORD = "Temporal.2025!"  # elige la que quieras para probar

db = SessionLocal()
u = db.query(AspNetUser).filter(AspNetUser.Email == EMAIL).first()
assert u, "Usuario no encontrado"

u.PasswordHash = create_identity_v3_hash(NEW_PASSWORD)
u.SecurityStamp = token_hex(16)  # buena práctica cuando cambias password
db.add(u)
db.commit()
print("OK, password reseteado:", EMAIL)
