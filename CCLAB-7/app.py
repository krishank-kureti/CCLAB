import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from minio import Minio

app = Flask(__name__)

# --- Block Storage Path ---
if os.path.exists("/mnt/block_volume"):
    BLOCK_STORAGE_PATH = "/mnt/block_volume/ecommerce.db"
else:
    BLOCK_STORAGE_PATH = os.path.join(os.getcwd(), "my_block_data", "ecommerce.db")

app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{BLOCK_STORAGE_PATH}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MinIO Client ---
minio_client = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ROOT_USER", "admin_user"),
    secret_key=os.getenv("MINIO_ROOT_PASSWORD", "admin_password"),
    secure=False
)

# --- Database Model ---
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_name = db.Column(db.String(120))

@app.route('/')
def home():
    return "E-commerce Lab is Running! Send a POST request to /product to add data."

# --- MAIN ROUTE ---
@app.route('/product', methods=['POST'])
def add_product():
    name = request.form.get('name')
    price = request.form.get('price')
    image = request.files.get('image')

    if not image:
        return jsonify({"error": "No image uploaded"}), 400

    temp_path = image.filename
    image.save(temp_path)

    try:
        bucket = "pes2ug23cs285" 

        if not minio_client.bucket_exists(bucket):
            minio_client.make_bucket(bucket)

        file_metadata = {
            "x-amz-meta-product-name": str(name),
            "x-amz-meta-product-price": str(price)
        }

        minio_client.fput_object(
            bucket,
            image.filename,
            temp_path,
            metadata=file_metadata
        )

        new_product = Product(
            name=name,
            price=price,
            image_name=image.filename
        )
        db.session.add(new_product)
        db.session.commit()

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify({
        "status": "success",
        "msg": "Structured data in Block, Image in Object with Metadata"
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("Starting Flask app on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000)
