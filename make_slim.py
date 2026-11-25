import os
import sqlite3

SRC = 'data/raw/airtel.db'
DST = 'data/raw/airtel_slim.db'

if os.path.exists(DST):
    os.remove(DST)

con = sqlite3.connect(SRC)
con.execute("ATTACH DATABASE ? AS slim", (DST,))
for t in ['customer_features', 'recharges']:
    con.execute(f"CREATE TABLE slim.{t} AS SELECT * FROM main.{t}")
con.commit()
con.execute("DETACH DATABASE slim")
con.close()

print('slim size (MB):', round(os.path.getsize(DST) / 1024 / 1024, 1))