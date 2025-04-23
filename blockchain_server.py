from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pathlib import Path
from threading import Lock
import time, json, math, hashlib
from ecdsa import SigningKey, VerifyingKey, NIST384p, BadSignatureError

# ----------- MODELOS -----------
class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: float
    signature: str = ""
    public_key: str = ""
    metadata: dict = Field(default_factory=dict)

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": round(self.amount,1),
            "signature": self.signature,
            "public_key": self.public_key,
            "metadata": self.metadata
        }

    def to_json(self):
        base = {"sender": self.sender, "recipient": self.recipient, "amount": round(self.amount,1)}
        return json.dumps(base, sort_keys=True)

    def is_valid(self):
        if not self.signature or not self.public_key:
            return False
        try:
            tx_dict = {"sender": self.sender, "recipient": self.recipient, "amount": f"{self.amount:.1f}"}
            tx_json = json.dumps(tx_dict, sort_keys=True, separators=(",", ":"))
            vk = VerifyingKey.from_pem(self.public_key.encode())
            vk.verify(bytes.fromhex(self.signature), tx_json.encode())
            return True
        except Exception:
            return False

class Block:
    def __init__(self, index, timestamp, previous_hash, transactions, nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        tx_str = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        block_string = f"{self.index}{self.timestamp}{self.previous_hash}{tx_str}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, difficulty):
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        txs = [Transaction(**t) for t in data["transactions"]]
        return Block(data["index"], data["timestamp"], data["previous_hash"], txs, data["nonce"])

class Blockchain:
    def __init__(self, difficulty=2, file_path='blockchain.json'):
        self.difficulty = difficulty
        self.blocks = []
        self.pending_transactions = []
        self.file_path = Path(file_path)
        self.lock = Lock()
        self.load_or_create()

    def create_genesis_block(self):
        g = Block(0, time.time(), None, [])
        g.proof_of_work(self.difficulty)
        self.blocks.append(g)
        self.save()

    def latest_block(self):
        return self.blocks[-1]

    def add_transaction(self, tx: Transaction):
        if tx.is_valid() or tx.metadata.get('student_id'):
            self.pending_transactions.append(tx)
            return True
        return False

    def mine_block(self):
        with self.lock:
            if not self.pending_transactions:
                return False
            new = Block(len(self.blocks), time.time(), self.latest_block().hash, self.pending_transactions[:])
            new.proof_of_work(self.difficulty)
            self.blocks.append(new)
            self.pending_transactions = []
            self.save()
            return True

    def is_chain_valid(self):
        for i in range(1, len(self.blocks)):
            curr, prev = self.blocks[i], self.blocks[i-1]
            if curr.hash != curr.calculate_hash() or curr.previous_hash != prev.hash:
                return False
        return True

    def save(self):
        with self.file_path.open('w') as f:
            json.dump([b.to_dict() for b in self.blocks], f, indent=2)

    def load_or_create(self):
        if self.file_path.exists():
            with self.file_path.open() as f:
                data = json.load(f)
                self.blocks = [Block.from_dict(b) for b in data]
        else:
            self.create_genesis_block()

# Funções utilitárias

def generate_keys():
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.verifying_key
    return sk.to_pem().decode(), vk.to_pem().decode()

def sign_transaction(tx_data: str, private_key_pem: str):
    sk = SigningKey.from_pem(private_key_pem)
    return sk.sign(tx_data.encode()).hex()

# Haversine para distância

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(dλ/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Modelos de área e presença
class AreaConfig(BaseModel):
    latitude: float
    longitude: float
    tolerance_m: float

class AttendanceRequest(BaseModel):
    student_id: str
    latitude: float
    longitude: float

# App FastAPI
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'], allow_credentials=True)
blockchain = Blockchain()
area_cfg: AreaConfig = None

@app.post('/attendance/configure')
def configure_area(cfg: AreaConfig):
    global area_cfg
    area_cfg = cfg
    return {"message": "Área configurada", **cfg.dict()}

@app.post('/attendance/check')
def check_attendance(req: AttendanceRequest):
    if area_cfg is None:
        raise HTTPException(400, "Área não configurada")
    dist = haversine(req.latitude, req.longitude, area_cfg.latitude, area_cfg.longitude)
    if dist > area_cfg.tolerance_m:
        raise HTTPException(403, f"Fora da área ({dist:.1f} m)")
    tx = Transaction(
        sender=req.student_id,
        recipient="attendance_contract",
        amount=0.0,
        signature="",
        public_key="",
        metadata={"latitude":req.latitude, "longitude":req.longitude, "timestamp":time.time(), "student_id":req.student_id}
    )
    blockchain.add_transaction(tx)
    return {"message": "Presença registrada"}

@app.post('/generate_keys')
def api_generate_keys():
    priv, pub = generate_keys()
    return {"private_key": priv, "public_key": pub}

@app.post('/sign')
def api_sign(body: dict = Body(...)):
    return {"signature": sign_transaction(body['tx_data'], body['private_key'])}

@app.get('/chain')
def get_chain():
    return [b.to_dict() for b in blockchain.blocks]

@app.post('/mine')
def mine():
    if blockchain.mine_block(): return {"message": "Bloco minerado"}
    raise HTTPException(400, "Nada para minerar")

@app.get('/validate')
def validate():
    return {"valid": blockchain.is_chain_valid()}