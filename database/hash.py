from werkzeug.security import generate_password_hash

# Password que queres usar
password = "1234"

# Gerar hash
hash_gerado = generate_password_hash(password)

print(hash_gerado)
