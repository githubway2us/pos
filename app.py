from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import json
import os
import csv
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # จำเป็นสำหรับ session
PRODUCTS_FILE = 'products.json'
PAYMENTS_FILE = 'payments.csv'
TRANSACTIONS_FILE = 'transactions.csv'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Utility ----------------
def clean_string(s):
    return s.encode('utf-8', 'ignore').decode('utf-8') if s else ""

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# สร้างโฟลเดอร์สำหรับอัพโหลดถ้ายังไม่มี
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def load_products():
    try:
        if not os.path.exists(PRODUCTS_FILE):
            return []
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as file:
            return json.load(file)
    except UnicodeDecodeError:
        try:
            with open(PRODUCTS_FILE, 'r', encoding='cp874') as file:
                return json.load(file)
        except:
            return []
    except:
        return []

def save_products(products):
    try:
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as file:
            json.dump(products, file, ensure_ascii=False, indent=2)
    except:
        pass

def get_product_by_id(product_id):
    products = load_products()
    for product in products:
        if product['id'] == product_id:
            return product
    return None

# ---------------- Product Routes ----------------
@app.route('/')
def index():
    products = load_products()
    cart = session.get('cart', [])
    return render_template('index.html', products=products, cart=cart)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name'].strip()
        price = float(request.form['price'])
        file = request.files.get('image')

        if not file or not allowed_file(file.filename):
            return jsonify({'error': 'ไฟล์ไม่ถูกต้อง'}), 400

        # โหลดสินค้าปัจจุบัน
        products = load_products()
        # สร้าง id ใหม่
        product_id = max([p.get('id', 0) for p in products], default=0) + 1

        # เปลี่ยนชื่อไฟล์ให้ตรงกับชื่อสินค้า
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"{name}_{product_id}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # บันทึกสินค้าใหม่
        products.append({
            'id': product_id,
            'name': name,
            'price': price,
            'image': filepath
        })
        save_products(products)

        return jsonify({'success': True, 'message': 'เพิ่มสินค้าสำเร็จ'}), 200

    return render_template('add_product.html')


@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    products = load_products()
    product = next((p for p in products if p['id'] == product_id), None)
    if not product:
        return jsonify({'error': 'ไม่พบสินค้า'}), 404

    if request.method == 'POST':
        try:
            name = clean_string(request.form.get('name'))
            price = float(request.form.get('price'))
            image = request.files.get('image')

            product['name'] = name
            product['price'] = price

            if image and allowed_file(image.filename):
                # ลบไฟล์เก่าถ้ามี
                if os.path.exists(product['image']):
                    os.remove(product['image'])
                # เปลี่ยนชื่อไฟล์ใหม่ตามชื่อสินค้า
                ext = image.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"{name}_{product_id}.{ext}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                product['image'] = image_path

            save_products(products)
            return redirect(url_for('index'))
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return render_template('edit_products.html', product=product)


# หน้าแสดงลบสินค้า
@app.route('/delete_page')
def delete_page():
    products = []
    if os.path.exists('products.json'):
        with open('products.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
    return render_template('delete_product.html', products=products)

# ลบสินค้า
# 1. Better secret key
app.secret_key = os.urandom(32)

# 2. Fix delete_product (most dangerous bug right now)
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    products = load_products()
    original_len = len(products)
    products = [p for p in products if p.get('id') != product_id]
    
    if len(products) == original_len:
        return jsonify({'error': 'ไม่พบสินค้านี้'}), 404
        
    # ลบรูป
    for p in load_products():  # load again to get old image path
        if p['id'] == product_id and os.path.exists(p['image']):
            os.remove(p['image'])
            break
            
    save_products(products)
    return jsonify({'message': 'ลบเรียบร้อยแล้ว'})

# 3. Store relative image path (recommended change)
# In add_product & edit_product change:


# Then in template use: <img src="{{ url_for('static', filename=product.image) }}">
# ---------------- Cart ----------------
@app.route('/cart')
def cart():
    cart = session.get('cart', [])
    total = sum(item['price'] * item['quantity'] for item in cart)
    return render_template('cart.html', cart=cart, total=total)

@app.route('/update_cart', methods=['POST'])
def update_cart():
    try:
        data = request.get_json()
        session['cart'] = data['cart']
        session['total'] = data['total']
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- Payments ----------------
@app.route('/save_payment', methods=['POST'])
def save_payment():
    try:
        data = request.get_json()
        print("Received payment data:", data)
        if not data:
            return jsonify({'error': 'ไม่มีข้อมูล'}), 400

        total_amount = data.get('totalAmount')
        payment_amount = data.get('paymentAmount')
        cart = data.get('cart')

        print("Total Amount:", total_amount)
        print("Payment Amount:", payment_amount)
        print("Cart:", cart)

        if not all([total_amount, payment_amount, cart]):
            return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400

        payment_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cart_items = ', '.join([f"{item['quantity']} x {clean_string(item['product'])} ({item['totalPrice']})" for item in cart])
        print("Cart Items to save:", cart_items)

        file_exists = os.path.isfile(PAYMENTS_FILE)
        with open(PAYMENTS_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Date', 'Total Amount', 'Payment Amount', 'Cart Items'])
            writer.writerow([payment_time, total_amount, payment_amount, cart_items])
            print("Data written to payments.csv")

        return jsonify({'message': 'บันทึกข้อมูลการชำระเงินสำเร็จ', 'redirect': '/dashboard'}), 200
    except Exception as e:
        print("Error in save_payment:", str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/save_transaction', methods=['POST'])
def save_transaction():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'ไม่มีข้อมูล'}), 400

        total = data.get('total')
        payment = data.get('payment')
        change = data.get('change')

        if not all([total, payment, change]):
            return jsonify({'error': 'ข้อมูลไม่ครบถ้วน'}), 400

        file_exists = os.path.isfile(TRANSACTIONS_FILE)
        with open(TRANSACTIONS_FILE, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            if not file_exists:
                writer.writerow(['Date', 'Total', 'Payment', 'Change'])
            writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), total, payment, change])

        return jsonify({'success': True, 'message': 'บันทึกธุรกรรมสำเร็จ'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- Dashboard ----------------
@app.route('/dashboard')
def dashboard():
    payments = []
    if os.path.exists(PAYMENTS_FILE):
        try:
            with open(PAYMENTS_FILE, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                payments = list(reader)
                print("Payments loaded:", payments)  # พิมพ์ข้อมูลที่โหลด
        except UnicodeDecodeError:
            with open(PAYMENTS_FILE, 'r', encoding='cp874') as file:
                reader = csv.DictReader(file)
                payments = list(reader)
                print("Payments loaded (cp874):", payments)  # พิมพ์ข้อมูลที่โหลด
        except Exception as e:
            print("Error loading payments:", str(e))  # พิมพ์ข้อผิดพลาด
    else:
        print("Payments file does not exist")
    return render_template('dashboard.html', payments=payments)

# ---------------- API ----------------
@app.route('/api/sales_data')
def sales_data():
    payments = []
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                print("Processing row:", row)  # พิมพ์ข้อมูลแต่ละแถว
                cart_items = row['Cart Items'].split(', ')
                for item in cart_items:
                    match = re.match(r'(\d+) x (.+) \(([0-9.]+)\)', item)
                    if match:
                        quantity = int(match.group(1))
                        product = clean_string(match.group(2))
                        total_price = float(match.group(3))
                        price = total_price / quantity if quantity > 0 else 0
                        payments.append({
                            'product': product,
                            'date': row['Date'],
                            'quantity': quantity,
                            'price': price,
                            'totalSales': total_price
                        })
            print("Processed payments:", payments)  # พิมพ์ข้อมูลที่ประมวลผล
    else:
        print("Payments file does not exist")
    return jsonify(payments)

def aggregate_sales(period="day"):
    summary = defaultdict(float)
    if os.path.exists(PAYMENTS_FILE):
        with open(PAYMENTS_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                try:
                    date = datetime.strptime(row['Date'], "%Y-%m-%d %H:%M:%S")
                    total_amount = float(row['Total Amount'])
                    if period == "day":
                        key = date.strftime("%Y-%m-%d")
                    elif period == "month":
                        key = date.strftime("%Y-%m")
                    elif period == "year":
                        key = date.strftime("%Y")
                    else:
                        key = date.strftime("%Y-%m-%d")
                    summary[key] += total_amount
                except:
                    continue
    return [{"period": k, "total": v} for k, v in sorted(summary.items())]

@app.route('/api/sales_summary/<period>')
def sales_summary(period):
    if period not in ["day", "month", "year"]:
        return jsonify({"error": "Invalid period"}), 400
    data = aggregate_sales(period)
    return jsonify(data)

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3600)
