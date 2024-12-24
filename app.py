from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
import os
import csv
from datetime import datetime

app = Flask(__name__)
PRODUCTS_FILE = 'products.json'

# ฟังก์ชันสำหรับโหลดสินค้า
def load_products():
    if not os.path.exists(PRODUCTS_FILE):
        return []
    with open(PRODUCTS_FILE, 'r') as file:
        return json.load(file)


# ฟังก์ชันสำหรับบันทึกสินค้า
def save_products(products):
    with open(PRODUCTS_FILE, 'w') as file:
        json.dump(products, file)


@app.route('/')
def index():
    products = load_products()
    return render_template('index.html', products=products)


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    products = load_products()  # Load current products
    if 0 <= product_id < len(products):
        products.pop(product_id)  # Remove the product based on index
        save_products(products)  # Save the updated list back to file
    return redirect(url_for('index'))



@app.route('/delete_page')
def delete_page():
    products = load_products()
    return render_template('delete_product.html', products=products)


@app.route('/add-product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        image = request.files['image']

        if not name or not price or not image:
            return "All fields are required!", 400

        image_filename = os.path.join('static', image.filename)
        image.save(image_filename)

        # โหลดสินค้าปัจจุบันและเพิ่มใหม่
        products = load_products()
        new_product = {
            'id': len(products) + 1,  # เพิ่ม ID ให้กับสินค้า
            'name': name,
            'price': price,
            'image': image_filename
        }
        products.append(new_product)
        save_products(products)

        return redirect(url_for('index'))

    return render_template('add_product.html')
# Define the file path for CSV where payment data will be saved
CSV_FILE = 'payments.csv'

@app.route('/save_payment', methods=['POST'])
def save_payment():
    # Get the payment data from the request
    data = request.get_json()
    total_amount = data['totalAmount']
    payment_amount = data['paymentAmount']
    cart = data['cart']

    # Prepare the data for CSV
    payment_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cart_items = ', '.join([f"{item['quantity']} x {item['product']} (${item['totalPrice']})" for item in cart])

    # Write the payment data to CSV
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([payment_time, total_amount, payment_amount, cart_items])

    return jsonify({'message': 'Payment details saved successfully'}), 200

# หน้า dashboard ที่จะแสดงยอดขาย
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = get_product_by_id(product_id)  # Fetch product by ID
    if request.method == 'POST':
        # Update product details
        product.name = request.form['name']
        product.price = request.form['price']
        product.image = request.form['image']
        save_product(product)  # Save updated product
        return redirect(url_for('product_list'))  # Redirect to product list
    return render_template('edit_product.html', product=product)

@app.route('/save_transaction', methods=['POST'])
def save_transaction():
    data = request.get_json()
    total = data.get('total')
    payment = data.get('payment')
    change = data.get('change')

    # บันทึกลงในไฟล์ CSV
    with open('transactions.csv', 'a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Total', 'Payment', 'Change'])
        writer.writerow([total, payment, change])

    return jsonify({'success': True, 'message': 'Transaction saved successfully.'})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000)  # เปิดให้ทุกอุปกรณ์ใน LAN สามารถเข้าถึงได้
