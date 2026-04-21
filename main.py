import pymysql
from flask import *
import re
from collections import defaultdict
from flask import jsonify
from flask import session, redirect, url_for
from datetime import date, datetime, timedelta



myDB = pymysql.connect(host="localhost", user="root", password="r@1234")
myCursor = myDB.cursor()

myCursor.execute("use optics_store")

app = Flask(__name__)
app.secret_key = 'tarifi'

insurance_discounts = {
    'None': 0,
    'Medicare': 50,
    'HealthInsurance': 20,
    'PrivateCare': 30
}


##################################################
@app.route('/base')
def base():
    return render_template("base.html",base = base)

@app.route('/products')
def products():
    try:
        myCursor.execute("SELECT * FROM product ORDER BY product_id DESC")
        all_products = myCursor.fetchall()

        products = []
        for p in all_products:
            product = {
                'product_id': p[0],
                'quantity': p[1],
                'price': p[2],
                'cost': p[3],
                'product_type': p[4],
                'name': p[5],
                'image_path': p[6],
            }

            # Fetch additional data based on product type
            if p[4] == 'sunglasses':
                myCursor.execute("SELECT color, company_name FROM sunglasses WHERE product_id = %s", (p[0],))
                extra = myCursor.fetchone()
                if extra:
                    product['color'] = extra[0]
                    product['company_name'] = extra[1]

            elif p[4] == 'accessories':
                myCursor.execute("SELECT type FROM accessories WHERE product_id = %s", (p[0],))
                extra = myCursor.fetchone()
                if extra:
                    product['type'] = extra[0]

            elif p[4] == 'optical_glasses':
                myCursor.execute("SELECT optical_type, degree FROM optical_glasses WHERE product_id = %s", (p[0],))
                extra = myCursor.fetchone()
                if extra:
                    product['optical_type'] = extra[0]
                    product['degree'] = extra[1]

            elif p[4] == 'lenses':
                myCursor.execute("SELECT color FROM lenses WHERE product_id = %s", (p[0],))
                extra = myCursor.fetchone()
                if extra:
                    product['color'] = extra[0]

            products.append(product)

        return render_template('products.html', products=products)

    except Exception as e:
        flash(f'Error loading products: {str(e)}', 'error')
        return render_template('products.html', products=[])



# Add to cart
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():

    if 'user_id' not in session:
        flash("Please log in to add items to your cart.", "error")
        return redirect(url_for('login'))
    
    try:
        product_id = int(request.form.get('product_id'))
        quantity = int(request.form.get('quantity', 1))

        if 'cart' not in session:
            session['cart'] = {}

        myCursor.execute("SELECT quantity, name, price FROM product WHERE product_id = %s", (product_id,))
        product = myCursor.fetchone()

        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('products'))

        stock_quantity, name, price = product
        current_cart_quantity = session['cart'].get(str(product_id), 0)
        total_requested = current_cart_quantity + quantity

        if total_requested > stock_quantity:
            flash(f'Only {stock_quantity} items available in stock', 'error')
            return redirect(url_for('products', product_id=product_id))

        session['cart'][str(product_id)] = total_requested
        session.modified = True

        flash(f'{name} added to cart successfully!', 'success')
        return redirect(url_for('products'))

    except Exception as e:
        flash(f'Error adding to cart: {str(e)}', 'error')
        return redirect(url_for('products'))



@app.route('/cart')
def view_cart():

    if 'user_id' not in session:
        flash("Please log in to view your cart.", "error")
        return redirect(url_for('login'))


    if 'cart' not in session or not session['cart']:
        return render_template('cart.html', cart_items=[], total=0)

    cart_items = []
    total = 0

    try:
        for product_id, quantity in session['cart'].items():
            myCursor.execute("""
                SELECT product_id, name, price, image_path, quantity
                FROM product WHERE product_id = %s
            """, (int(product_id),))
            product = myCursor.fetchone()
            if product:
                pid, name, price, image_path, stock_quantity = product
                item_total = price * quantity
                cart_items.append((pid, name, price, quantity, item_total, image_path, stock_quantity))
                total += item_total

    except Exception as e:
        flash(f'Error loading cart: {str(e)}', 'error')
        return render_template('cart.html', cart_items=[], total=0)

    

    return render_template('cart.html', cart_items=cart_items, total=total)


# Update cart quantity
@app.route('/update_cart', methods=['POST'])
def update_cart():
    try:
        product_id = request.form.get('product_id')
        action = request.form.get('action')  # 'increase', 'decrease', or 'set'
        current_quantity = int(request.form.get('quantity', 1))  # default to 1

        if 'cart' not in session:
            session['cart'] = {}

        # Get stock info
        myCursor.execute("SELECT quantity, name FROM product WHERE product_id = %s", (int(product_id),))
        product = myCursor.fetchone()

        if not product:
            flash('Product not found', 'error')
            return redirect(url_for('view_cart'))

        stock_quantity = product[0]

        # Determine new quantity
        if action == 'increase':
            new_quantity = session['cart'].get(product_id, 1) + 1
        elif action == 'decrease':
            new_quantity = session['cart'].get(product_id, 1) - 1
        elif action == 'set':
            new_quantity = current_quantity
        else:
            flash('Invalid action', 'error')
            return redirect(url_for('view_cart'))

        # Remove from cart if quantity is 0 or below
        if new_quantity <= 0:
            session['cart'].pop(product_id, None)
        else:
            if new_quantity <= stock_quantity:
                session['cart'][product_id] = new_quantity
            else:
                flash(f'Only {stock_quantity} items available in stock', 'error')

        session.modified = True
        return redirect(url_for('view_cart'))

    except Exception as e:
        flash(f'Error updating cart: {str(e)}', 'error')
        return redirect(url_for('view_cart'))



# Remove from cart
@app.route('/remove_from_cart/<int:product_id>')
def remove_from_cart(product_id):
    session['cart'].pop(str(product_id), None)
    session.modified = True
    flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))


# Checkout page
@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash("Please log in to proceed to checkout.", "error")
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('products'))

    try:
        total = 0
        for product_id, quantity in session['cart'].items():
            myCursor.execute("SELECT price FROM product WHERE product_id = %s", (int(product_id),))
            product = myCursor.fetchone()
            if product:
                total += product[0] * quantity

        myCursor.execute("SELECT * FROM payment_method")
        payment_methods = myCursor.fetchall()

        myCursor.execute("SELECT * FROM branch")
        branches = myCursor.fetchall()

        return render_template('checkout.html',
                               total=total,
                               payment_methods=payment_methods,
                               branches=branches)


    except Exception as e:
        flash(f'Error loading checkout: {str(e)}', 'error')
        return redirect(url_for('view_cart'))


# Process order
@app.route('/process_order', methods=['POST'])
def process_order():
    if 'user_id' not in session:
        flash("Please log in to complete your order.", "error")
        return redirect(url_for('login'))
    
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('products'))

    try:
        user_id = session['user_id']
        customer_name = session.get('name')
        customer_phone = session.get('phone')
        customer_email = session.get('email')
        branch_id = int(request.form.get('branch_id'))
        payment_method_id = int(request.form.get('payment_method'))
        insurance = request.form.get('insurance', '')


        # Get customer_id from user_id
        myCursor.execute("SELECT customer_id FROM customer WHERE user_id = %s", (user_id,))
        result = myCursor.fetchone()
        if not result:
            flash("Customer record not found for this user.", "error")
            return redirect(url_for('checkout'))
        customer_id = result[0]

        insurance_discounts = {
            'None': 0,
            'Medicare': 50,
            'HealthInsurance': 20,
            'PrivateCare': 30
        }

        discount_percent = insurance_discounts.get(insurance, 0)

        total_price = 0
        total_cost = 0
        for product_id, quantity in session['cart'].items():
            myCursor.execute("SELECT price, cost FROM product WHERE product_id = %s", (int(product_id),))
            product = myCursor.fetchone()
            if product:
                price, cost = product
                total_price += price * quantity
                total_cost += cost * quantity

        profit = total_price - total_cost

         # Apply insurance discount
        discount_amount = total_price * discount_percent / 100
        paid_amount = total_price - discount_amount

        myCursor.execute("""
            INSERT INTO orderr (customer_id, branch_id, order_date, total_price, paid_amount, profit, discount)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (customer_id, branch_id, datetime.now().date(), total_price, paid_amount, profit, discount_amount))
        order_id = myCursor.lastrowid

        for product_id, quantity in session['cart'].items():
            myCursor.execute("SELECT price FROM product WHERE product_id = %s", (int(product_id),))
            product = myCursor.fetchone()
            if product:
                price = product[0]
                myCursor.execute("""
                    INSERT INTO order_details (order_id, product_id, quantity)
                    VALUES (%s, %s, %s)
                """, (order_id, int(product_id), quantity))

                myCursor.execute("""
                    UPDATE product SET quantity = quantity - %s WHERE product_id = %s
                """, (quantity, int(product_id)))

        myCursor.execute("""
            INSERT INTO payment (payment_id, order_id,insurance_discount_percentege, insurance)
            VALUES (%s, %s, %s, %s)
        """, (
            payment_method_id,
            order_id, 
            discount_percent, 
            insurance if insurance != 'None' else None
            ))

        myDB.commit()
        session['cart'] = {}
        session.modified = True

        flash(f'Order #{order_id} placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order_id))

    except Exception as e:
        flash(f'Error processing order: {str(e)}', 'error')
        return redirect(url_for('checkout'))
    

# Order confirmation
@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    try:
            myCursor.execute("""
                SELECT o.order_id, o.order_date, o.total_price, o.paid_amount,o.discount, c.name, b.location
                FROM orderr o
                JOIN customer c ON o.customer_id = c.customer_id
                JOIN branch b ON o.branch_id = b.branch_id
                WHERE o.order_id = %s
            """, (order_id,))
            order = myCursor.fetchone()

            discount_percent = int(round((order[4] / order[2]) * 100)) if order[2] else 0

            if not order:
                flash('Order not found', 'error')
                return redirect(url_for('products'))

            myCursor.execute("""
                SELECT od.product_id, od.quantity, p.price, p.name
                FROM order_details od
                JOIN product p ON od.product_id = p.product_id
                WHERE od.order_id = %s
            """, (order_id,))
            order_items = myCursor.fetchall()

            return render_template('order_confirmation.html', order=order, order_items=order_items, discount_percent=discount_percent)
        

    except Exception as e:
        flash(f'Error loading order confirmation: {str(e)}', 'error')
        return redirect(url_for('products'))


# API endpoint to get cart count
@app.route('/api/cart_count')
def cart_count():
    count = sum(session['cart'].values()) if 'cart' in session else 0
    return jsonify({'count': count})


@app.route('/product_statistics')
def product_statistics():
    # Top-selling products
    myCursor.execute("""
        SELECT p.name, SUM(od.quantity) AS total_sold
        FROM order_details od
        JOIN product p ON od.product_id = p.product_id
        GROUP BY p.name
        ORDER BY total_sold DESC
        LIMIT 5
    """)
    best_sellers = myCursor.fetchall()

    # Product type popularity
    myCursor.execute("""
        SELECT product_type, SUM(od.quantity)
        FROM order_details od
        JOIN product p ON od.product_id = p.product_id
        GROUP BY product_type
    """)
    category_data = myCursor.fetchall()

    # Trending this month (last 30 days)
    myCursor.execute("""
        SELECT p.name, SUM(od.quantity)
        FROM order_details od
        JOIN product p ON od.product_id = p.product_id
        JOIN orderr o ON od.order_id = o.order_id
        WHERE o.order_date >= CURDATE() - INTERVAL 30 DAY
        GROUP BY p.name
        ORDER BY SUM(od.quantity) DESC
        LIMIT 5
    """)
    trending_data = myCursor.fetchall()
    trending_names = [row[0] for row in trending_data]
    trending_counts = [int(row[1]) for row in trending_data]

    return render_template('product_statistics.html',
                           best_sellers=best_sellers,
                           category_data=category_data,
                           trending_names=trending_names,
                           trending_counts=trending_counts)



####################################################

@app.route('/')
def home():

    user_type = session.get('user_type')

    query = """
        SELECT p.name, p.image_path, p.price, SUM(od.quantity) AS total_sold
        FROM product p
        JOIN order_details od ON p.product_id = od.product_id
        GROUP BY p.product_id
        ORDER BY total_sold DESC
        LIMIT 3;
    """
    myCursor.execute(query)
    rows = myCursor.fetchall()

    best_sellers = [
        {
            'name': row[0],
            'image_path': row[1],
            'price': row[2],
            'total_sold': row[3]
        }
        for row in rows
    ]

    myCursor.execute("SELECT location, phone_number FROM branch ORDER BY location;")
    branches = myCursor.fetchall() 

    return render_template('index.html', user_type=user_type, best_sellers=best_sellers, our_branches=branches)


@app.route('/order-history')
def order_history():

    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if not user_id or user_type != 'customer':
        return redirect(url_for('login'))

    myCursor.execute("""
        SELECT customer_id, name, phone_number, location 
        FROM customer 
        WHERE user_id = %s
    """, [user_id])
    
    customer_info = myCursor.fetchone()
    
    if not customer_info:
        return render_template('order_history.html', error="Customer not found")
    
    customer_id = customer_info[0]
    
    # Get all orders with details
    myCursor.execute("""
        SELECT 
            o.order_id,
            o.order_date,
            o.total_price,
            o.paid_amount,
            o.profit,
            o.discount,
            COALESCE(b.location, 'Closed Branch') AS branch_location,
            CASE 
                WHEN o.paid_amount >= o.total_price THEN 'Completed'
                WHEN o.paid_amount > 0 THEN 'Partially Paid'
                ELSE 'Pending'
            END as order_status
        FROM orderr o
        LEFT JOIN branch b ON o.branch_id = b.branch_id
        WHERE o.customer_id = %s
        ORDER BY o.order_date DESC
    """, [customer_id])
    
    orders = myCursor.fetchall()
    
    # Get order details for each order
    order_details = {}
    for order in orders:
        order_id = order[0]
        myCursor.execute("""
            SELECT 
                od.product_id,
                p.name,
                p.product_type,
                od.quantity,
                p.price,
                (od.quantity * p.price) as subtotal
            FROM order_details od
            JOIN product p ON od.product_id = p.product_id
            WHERE od.order_id = %s
        """, [order_id])
        
        order_details[order_id] = myCursor.fetchall()
    
    # Get payment history
    myCursor.execute("""
        SELECT 
            p.order_id,
            pm.method_name,
            o.paid_amount,
            p.insurance_discount_percentege,
            p.insurance,
            o.order_date
        FROM payment p
        JOIN payment_method pm ON p.payment_id = pm.payment_id
        JOIN orderr o ON p.order_id = o.order_id
        WHERE o.customer_id = %s
        ORDER BY o.order_date DESC
    """, [customer_id])
    
    payments = myCursor.fetchall()
    
    # Get medical examinations
    myCursor.execute("""
        SELECT 
            ce.examination_id,
            me.name,
            ce.date,
            ce.result,
            me.price,
            ce.profit,
            pm.method_name
        FROM customer_examination ce
        JOIN medical_examinations me ON ce.examination_id = me.id
        JOIN payment_method pm ON ce.payment_id = pm.payment_id
        WHERE ce.customer_id = %s
        ORDER BY ce.date DESC
    """, [customer_id])
    
    examinations = myCursor.fetchall()
    
    # Calculate summary statistics
    total_orders = len(orders)
    total_spent = sum(order[3] for order in orders)  # total_price
    total_outstanding = sum(max(0, order[2] - order[3]) for order in orders)  # unpaid amount
    
    return render_template('order_history.html', 
                         customer_info=customer_info,
                         orders=orders,
                         order_details=order_details,
                         payments=payments,
                         examinations=examinations,
                         total_orders=total_orders,
                         total_spent=total_spent,
                         total_outstanding=total_outstanding)





###############################



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_type = session.get('user_type')
    
    # Get user information based on user_type
    user_info = {}
    
    try:
        if user_type == 'customer':
            # Get customer information
            myCursor.execute("""
                SELECT c.name, c.phone_number, c.date_of_birth, c.location
                FROM customer c
                JOIN user u ON c.user_id = u.user_id
                WHERE c.user_id = %s
            """, (user_id,))
            result = myCursor.fetchone()
            
            if result:
                user_info = {
                    'name': result[0],
                    'phone': result[1],
                    'date_of_birth': result[2],
                    'location': result[3],
                    'user_type': user_type
                }
                
                # Get order statistics
                myCursor.execute("""
                    SELECT COUNT(*), COALESCE(SUM(total_price), 0)
                    FROM orderr o
                    JOIN customer c ON o.customer_id = c.customer_id
                    WHERE c.user_id = %s
                """, (user_id,))
                stats = myCursor.fetchone()
                user_info['total_orders'] = stats[0] if stats else 0
                user_info['total_spent'] = float(stats[1]) if stats else 0.0
        
        elif user_type == 'employee':
            # Get employee information
            myCursor.execute("""
                SELECT e.name, e.email, e.date_of_birth, e.salary, b.location
                FROM employee e
                JOIN user u ON e.user_id = u.user_id
                JOIN branch b ON e.work_branch = b.branch_id
                WHERE e.user_id = %s
            """, (user_id,))
            result = myCursor.fetchone()
            
            if result:
                user_info = {
                    'name': result[0],
                    'email': result[1],
                    'date_of_birth': result[2],
                    'salary': float(result[3]) if result[3] else 0.0,
                    'work_location': result[4],
                    'user_type': user_type
                }
        
        elif user_type == 'owner':
            # Get owner information
            myCursor.execute("""
                SELECT o.name, o.email, o.phone_number, o.date_of_birth, 
                       o.ownership_percentage
                FROM owners o
                JOIN user u ON o.user_id = u.user_id
                WHERE o.user_id = %s
            """, (user_id,))
            result = myCursor.fetchone()
            
            if result:
                user_info = {
                    'name': result[0],
                    'email': result[1],
                    'phone': result[2],
                    'date_of_birth': result[3],
                    'ownership_percentage': float(result[4]) if result[4] else 0.0,
                    'user_type': user_type
                }
                print("hi")
                print(user_info)
        
        # Set defaults if no info found
        if not user_info:
            user_info = {
                'name': 'User',
                'user_type': user_type or 'customer'
            }
            
    except Exception as e:
        print(f"Database error: {e}")
        user_info = {
            'name': 'User',
            'user_type': user_type or 'customer'
        }
    
    return render_template('account.html', **user_info)

########################################################################################


@app.route('/insert' , methods=['POST'])
def InsertData():

    customer_id = request.form['customer_id']
    name = request.form['name']
    phone_number = request.form['phone_number']
    date_of_birth = request.form['date_of_birth']
    location = request.form['location']
    user_ID = request.form['user_ID']

    InsertIntoCustomer(customer_id , name , phone_number , date_of_birth , location , user_ID )

    myDB.commit()

    return "Data has been inserted successfully!" 

@app.route('/login', methods=['GET', 'POST']) 
def login():

    if request.method == 'POST':
        user_ID = request.form['user_ID']
        password = request.form['password']

        myCursor.execute("SELECT * FROM user WHERE user_id = %s", [user_ID])
        user_info = myCursor.fetchone()

        if user_info is None:
            return render_template("login.html", message="The User does not exist, try again !!!", form_type='login')

        elif user_info[1] == password:
            session['user_id'] = user_info[0]

            # Determine user type by checking in customer, employee, and owners tables
            user_type = None
            user_name = 'User'

            myCursor.execute("SELECT name FROM customer WHERE user_id = %s", [user_ID])
            result = myCursor.fetchone()
            if result:
                user_type = 'customer'
                user_name = result[0]

            else:
                myCursor.execute("SELECT name FROM employee WHERE user_id = %s", [user_ID])
                result = myCursor.fetchone()
                if result:
                    myCursor.execute("SELECT manage_branch From employee WHERE user_id = %s", [user_ID])
                    manage = myCursor.fetchone()[0]
                    print(manage)
                    if manage:
                        user_type = 'manager'
                    else:
                        user_type = 'employee'
                    user_name = result[0]
                else:
                    myCursor.execute("SELECT name FROM owners WHERE user_id = %s", [user_ID])
                    result = myCursor.fetchone()
                    if result:
                        user_type = 'owner'
                        user_name = result[0]

            session['user_type'] = user_type
            session['username'] = user_name

            return redirect(url_for('home'))

        else:
            return render_template("login.html", message="The Password isn't correct, try again !!!", form_type='login')
    
    return render_template('login.html', form_type='login')


@app.route('/signup', methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':
        name = request.form['name']
        user_ID = request.form['user_ID']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        myCursor.execute("SELECT * FROM user WHERE user_id = %s",[user_ID])
        user_info = myCursor.fetchone()

        if not user_ID.isdigit():
            return render_template('login.html', message="You Can't use this User ID..", form_type='signup')

        elif user_info is not None:
            return render_template('login.html', message="This User ID is already used..", form_type='signup')
        
        if password != confirm_password:
            return render_template('login.html', message="Passwords do not match..", form_type='signup')
        
        elif not is_strong_password(password):
            return render_template('login.html', message="Your Password is weak, it must contains at least 8 characters, at least one capital letter, one small letter, and one digit ...", form_type='signup')
        
        else:
            #insert into user table
            InsertIntoUser(user_ID, password)
            myDB.commit()
            # Redirect to next step
            return redirect(url_for('complete_profile', user_ID=user_ID))

    
    return render_template('login.html', form_type='signup')


@app.route('/complete-profile/<user_ID>', methods=['GET', 'POST'])
def complete_profile(user_ID):
    if request.method == 'POST':
        phone_number = request.form['phone_number']
        date_of_birth = request.form['date_of_birth']
        location = request.form['location']
        name = request.form['name']

        myCursor.execute("""
            INSERT INTO customer (name, phone_number, date_of_birth, location, user_ID)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, phone_number, date_of_birth, location, user_ID))
        myDB.commit()

        return redirect(url_for('login'))  

    return render_template('complete_profile.html', user_ID=user_ID)

def is_strong_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def InsertIntoCustomer( customer_id, name, phone_number , date_of_birth , location , user_ID ):

    query = ''' 
        INSERT INTO CUSTOMER (customer_id, name, phone_number, date_of_birth, location, user_ID )
        VALUES (%s, %s, %s, %s, %s, %s);
    '''
    
    data = ( customer_id , name , phone_number , date_of_birth , location , user_ID)

    myCursor.execute(query , data)


def InsertIntoUser( user_id, password):

    query = ''' 
        INSERT INTO user (user_id, password )
        VALUES (%s, %s);
    '''
    
    data = ( user_id, password)

    myCursor.execute(query , data)


@app.route('/delete' , methods=['POST'])
def DeleteData():

    customer_id = request.form['customer_id']

    DeleteFromCustomer(customer_id)

    myDB.commit()

    return "Data has been deleted successfully!" 


def DeleteFromCustomer(customer_id):

    query = '''
        DELETE FROM CUSTOMER 
        WHERE customer_id = %s
    '''
    
    data = (customer_id,)

    myCursor.execute(query , data)


@app.route('/update' , methods=['POST'])
def UpdateData():

    customer_id = request.form['ID']
    new_location = request.form['new_location']

    UpdateCustomerLocation(customer_id , new_location)

    myDB.commit()

    return "Data has been Updated successfully!" 

def UpdateCustomerLocation(customer_id  , new_location):

    query = '''     
        Update CUSTOMER
        set location = %s
        where customer_id = %s;
    '''
    
    data = (new_location , customer_id )

    myCursor.execute(query , data)
############################################################################################

def get_all_suppliers():
    myCursor.execute("SELECT supplier_id, name FROM supplier")
    return myCursor.fetchall()

def get_all_products():
    myCursor.execute("SELECT product_id, name, cost FROM product")
    return myCursor.fetchall()

# Get all purchase orders with supplier names
def get_all_purchase_orders():
    myCursor.execute("""
        SELECT po.purchase_order_id, po.purchase_date, s.name AS supplier_name
        FROM purchase_order po
        JOIN supplier s ON po.supplier_id = s.supplier_id
        ORDER BY po.purchase_order_id DESC
    """)
    return myCursor.fetchall()

# Get one purchase order details
def get_purchase_order_details(order_id):
    myCursor.execute("""
        SELECT p.name, pod.quantity, pod.cost_per_unit,
               (pod.quantity * pod.cost_per_unit) AS subtotal
        FROM purchase_order_details pod
        JOIN product p ON pod.product_id = p.product_id
        WHERE pod.purchase_order_id = %s
    """, [order_id])
    return myCursor.fetchall()

@app.route('/purchase_orders')
def purchase_orders():
    orders = get_all_purchase_orders()
    return render_template('purchase_orders.html', orders=orders)

@app.route('/purchase_order/<int:order_id>')
def view_purchase_order(order_id):
    details = get_purchase_order_details(order_id)
    return render_template('purchase_order_details.html', order_id=order_id, details=details)

@app.route('/create_purchase_order')
def create_purchase_order():
    suppliers = get_all_suppliers()
    products = get_all_products()
    branches = get_all_branches()  # Fetch this from DB
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    return render_template('create_purchase_order.html',
                           suppliers=suppliers,
                           products=products,
                           branches=branches,
                           tomorrow_date=tomorrow)


@app.route('/submit_purchase_order', methods=['POST'])
def submit_purchase_order():
    supplier_id = request.form['supplier_id']
    purchase_date = request.form['purchase_date']
    branch_id = request.form['branch_id'] 

    product_ids = request.form.getlist('product_id[]')
    quantities = request.form.getlist('quantity[]')
    costs = request.form.getlist('cost_per_unit[]')

    #Insert into purchase_order
    myCursor.execute("""
        INSERT INTO purchase_order (supplier_id, purchase_date) 
        VALUES (%s, %s)
    """, (supplier_id, purchase_date))
    purchase_order_id = myCursor.lastrowid

    #Insert into purchase_order_details for each product
    for pid, qty, cost in zip(product_ids, quantities, costs):
        myCursor.execute("""
            INSERT INTO purchase_order_details (
                purchase_order_id, product_id, quantity, cost_per_unit
            ) VALUES (%s, %s, %s, %s)
        """, (purchase_order_id, pid, qty, cost))

    #Insert branch that placed the order
    myCursor.execute("""
        INSERT INTO branch_place_purchase_order (branch_id, purchase_order_id) 
        VALUES (%s, %s)
    """, (branch_id, purchase_order_id))

    myDB.commit()
    flash("Purchase order created successfully!", "success")
    return redirect(url_for('purchase_orders'))

#############################################################################################
# fetch all branches (id, location)
def get_all_branches():

    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    data = myCursor.fetchall()
    return data

#Branch Management -------------------------------------------------------------
@app.route("/branches")
def branches():
    myCursor.execute("SELECT branch_id, location, phone_number FROM branch ORDER BY branch_id;")
    all_branches = myCursor.fetchall()
    return render_template("branches.html", branches=all_branches)

#add new branch
@app.route("/branch/add", methods=["POST"])
def add_branch():
    location = request.form.get("location").strip()
    phone = request.form.get("phone").strip()
    if not location or not phone:
        flash("Location and phone cannot be empty.", "error")
        return redirect(url_for("branches"))
    
    if not phone.isdigit():
        flash("wrong phone Number", "error")
        return redirect(url_for("branches"))

    try:
        myCursor.execute(
            "INSERT INTO branch (location, phone_number) VALUES ( %s, %s);",
            (location, phone),
        )
        myDB.commit()
        flash("Branch added successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding branch: {e}", "error")
    return redirect(url_for("branches"))


#edit a branch info
@app.route("/branch/edit/<int:branch_id>", methods=["POST"])
def edit_branch(branch_id):
    new_location = request.form.get("location").strip()
    new_phone = request.form.get("phone").strip()
    if not new_location or not new_phone:
        flash("Location and phone cannot be empty.", "error")
        return redirect(url_for("branches"))

    try:
        myCursor.execute(
            "UPDATE branch SET location = %s, phone_number = %s WHERE branch_id = %s;",
            (new_location, new_phone, branch_id),
        )
        myDB.commit()
        flash("Branch updated successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating branch: {e}", "error")
    return redirect(url_for("branches"))


#delete a branch
@app.route("/branch/delete/<int:branch_id>", methods=["POST"])
def delete_branch(branch_id):
    try:
        myCursor.execute("DELETE FROM branch WHERE branch_id = %s;", (branch_id,))
        myDB.commit()
        flash("Branch deleted successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting branch: {e}", "error")
    return redirect(url_for("branches"))


#Employee Management --------------------------------------------------
@app.route("/employees", methods=["GET", "POST"])
def employees():
 

    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    branches = myCursor.fetchall() 

    message = None
    success = None

    if request.method == "POST":
        user_id = request.form.get("userid").strip()
        name = request.form.get("name").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        date_of_birth = request.form.get("dob")
        email = request.form.get("email").strip()
        salary = request.form.get("salary")
        branch_ID = request.form.get("branch")

        #Validate user_id is numeric
        if not user_id.isdigit():
            message = "You can't use this User ID (must be numeric)."
        else:
            #Check for existing user
            myCursor.execute("SELECT * FROM user WHERE user_id = %s;", [user_id])
            user_info = myCursor.fetchone()
            if user_info is not None:
                message = "This User ID is already used."
            else:
                #Check password match
                if password != confirm_password:
                    message = "Passwords do not match."
                else:
                    #Check password strength
                    if not is_strong_password(password):
                        message = (
                            "Your password is weak: it must contain at least 8 characters, "
                            "one uppercase, one lowercase, and one digit."
                        )
                    else:
                        #insert into user and employee tables
                        try:
                            # Insert into user
                            myCursor.execute(
                                "INSERT INTO user (user_id, password) VALUES (%s, %s);",
                                (int(user_id), password),
                            )
                            myDB.commit()

                            # Insert into employee:
                            # emp_id is AUTO_INCREMENT; manage_branch can be NULL
                            myCursor.execute(
                                """
                                INSERT INTO employee
                                  (name, email, date_of_birth, salary, work_branch, user_id)
                                VALUES (%s, %s, %s, %s, %s, %s);
                                """,
                                (name, email, date_of_birth, float(salary), int(branch_ID), int(user_id)),
                            )
                            myDB.commit()
                            success = "Employee account created successfully."
                        except Exception as e:
                            myDB.rollback()
                            message = f"Error creating account: {e}"

    #Fetch all existing employees with their branch location
    myCursor.execute(
        """
        SELECT 
          e.emp_id,
          e.name,
          e.email,
          e.date_of_birth AS dob,
          e.salary,
          b.location AS work_location
        FROM employee e
        LEFT JOIN branch b ON e.work_branch = b.branch_id
        ORDER BY e.emp_id;
        """
    )
    all_employees = myCursor.fetchall() 

    return render_template(
        "employees.html",
        branches=branches,
        employees=all_employees,
        message=message,
        success=success,
    )


#adit an employee info
@app.route("/employee/edit/<int:emp_id>", methods=["POST"])
def edit_employee(emp_id):
    try:
        new_salary = float(request.form.get("salary"))
    except ValueError:
        flash("Salary must be a number ≥ 300.", "error")
        return redirect(url_for("employees"))

    if new_salary < 300:
        flash("Salary must be at least 300 USD.", "error")
        return redirect(url_for("employees"))

    new_branch = request.form.get("work_branch")
    if not new_branch or not new_branch.isdigit():
        flash("Please select a valid branch.", "error")
        return redirect(url_for("employees"))

    try:
        myCursor.execute(
            "UPDATE employee SET salary = %s, work_branch = %s WHERE emp_id = %s;",
            (new_salary, int(new_branch), emp_id),
        )
        myDB.commit()
        flash("Employee updated successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating employee: {e}", "error")

    return redirect(url_for("employees"))


#Delete employee 
@app.route("/employee/delete/<int:emp_id>", methods=["POST"])
def delete_employee(emp_id):
    try:
        myCursor.execute("DELETE FROM employee WHERE emp_id = %s;", (emp_id,))
        myDB.commit()
        flash("Employee deleted successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting employee: {e}", "error")

    return redirect(url_for("employees"))

#Manager Management --------------------------------------------------
@app.route("/managers", methods=["GET", "POST"])
def managers():
 

    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    branches = myCursor.fetchall() 

    message = None
    success = None

    if request.method == "POST":
        user_id = request.form.get("userid").strip()
        name = request.form.get("name").strip()
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        date_of_birth = request.form.get("dob")
        email = request.form.get("email").strip()
        salary = request.form.get("salary")
        branch_ID = request.form.get("branch")

        #Validate user_id is numeric
        if not user_id.isdigit():
            message = "You can't use this User ID (must be numeric)."
        else:
            #Check for existing user
            myCursor.execute("SELECT * FROM user WHERE user_id = %s;", [user_id])
            user_info = myCursor.fetchone()
            if user_info is not None:
                message = "This User ID is already used."

            else:
                #Check password match
                if password != confirm_password:
                    message = "Passwords do not match."
                else:
                    #Check password strength
                    if not is_strong_password(password):
                        message = (
                            "Your password is weak: it must contain at least 8 characters, "
                            "one uppercase, one lowercase, and one digit."
                        )
                    else:
                        myCursor.execute("SELECT DISTINCT manage_branch FROM employee;")
                        branches_with_manager = [row[0] for row in myCursor.fetchall()]
                        if int(branch_ID) in branches_with_manager:
                            message="This branch already has a manager."
                        
                        else:
                        #insert into user and employee tables
                            try:
                                # Insert into user
                                myCursor.execute(
                                    "INSERT INTO user (user_id, password) VALUES (%s, %s);",
                                    (int(user_id), password),
                                )
                                myDB.commit()

                                # Insert into employee:
                                # emp_id is AUTO_INCREMENT; manage_branch can be NULL
                                myCursor.execute(
                                    """
                                    INSERT INTO employee
                                    (name, email, date_of_birth, salary, work_branch, user_id, manage_branch)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                                    """,
                                    (name, email, date_of_birth, float(salary), int(branch_ID), int(user_id), int(branch_ID)),
                                )
                                myDB.commit()
                                success = "Manager account created successfully."
                            except Exception as e:
                                myDB.rollback()
                                message = f"Error creating account: {e}"

    #Fetch all existing managers with their branch location
    myCursor.execute(
        """
        SELECT 
          e.emp_id,
          e.name,
          e.email,
          e.date_of_birth AS dob,
          e.salary,
          b.location AS work_location
        FROM employee e
        LEFT JOIN branch b ON e.work_branch = b.branch_id
        WHERE e.manage_branch IS NOT NULL
        ORDER BY e.emp_id;
        """
    )
    all_managers = myCursor.fetchall() 

    return render_template(
        "managers.html",
        branches=branches,
        managers=all_managers,
        message=message,
        success=success,
    )


#edit an manager info
@app.route("/manager/edit/<int:emp_id>", methods=["POST"])
def edit_manager(emp_id):
    try:
        new_salary = float(request.form.get("salary"))
    except ValueError:
        flash("Salary must be a number ≥ 300.", "error")
        return redirect(url_for("managers"))

    if new_salary < 300:
        flash("Salary must be at least 300 USD.", "error")
        return redirect(url_for("managers"))

    new_branch = request.form.get("manage_branch")
    if not new_branch or not new_branch.isdigit():
        flash("Please select a valid branch.", "error")
        return redirect(url_for("managers"))
    
    myCursor.execute("SELECT DISTINCT manage_branch FROM employee;")
    branches_with_manager = [row[0] for row in myCursor.fetchall()]
    if int(new_branch) in branches_with_manager:
        flash("This branch already has a manager.")

    else:
        try:
            myCursor.execute(
                "UPDATE employee SET salary = %s, work_branch = %s, manage_branch = %s WHERE emp_id = %s;",
                (new_salary, int(new_branch),int(new_branch), emp_id),
            )
            myDB.commit()
            flash("Manager updated successfully.", "success")
        except Exception as e:
            myDB.rollback()
            flash(f"Error updating manager: {e}", "error")

    return redirect(url_for("managers"))


#Delete manager 
@app.route("/manager/delete/<int:emp_id>", methods=["POST"])
def delete_manager(emp_id):
    try:
        myCursor.execute("DELETE FROM employee WHERE emp_id = %s;", (emp_id,))
        myDB.commit()
        flash("Manager deleted successfully.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting manager: {e}", "error")

    return redirect(url_for("managers"))

#Medical Examinations Management -------------------------------------------
@app.route("/examinations")
def examinations():
    myCursor.execute("SELECT id, name, price, cost FROM medical_examinations ORDER BY id;")
    data = myCursor.fetchall()
    return render_template("examinations.html", exams=data)


#add a new medical exam
@app.route("/examination/add", methods=["POST"])
def add_examination():
    #Fetch and validate the ID field
    try:
        exam_id = int(request.form.get("id"))
    except (TypeError, ValueError):
        flash("ID must be an integer.", "error")
        return redirect(url_for("examinations"))

    #Check if ID already exists
    myCursor.execute("SELECT 1 FROM medical_examinations WHERE id = %s;", (exam_id,))
    if myCursor.fetchone() is not None:
        flash(f"An examination with ID {exam_id} already exists.", "error")
        return redirect(url_for("examinations"))

    #Fetch the other fields
    name = request.form.get("name").strip()
    try:
        price = float(request.form.get("price"))
        cost = float(request.form.get("cost"))
    except (TypeError, ValueError):
        flash("Price and cost must be numeric.", "error")
        return redirect(url_for("examinations"))

    if not name:
        flash("Name cannot be empty.", "error")
        return redirect(url_for("examinations"))

    #Insert into the table
    try:
        myCursor.execute(
            """INSERT INTO medical_examinations (id, name, price, cost)
               VALUES (%s, %s, %s, %s);""",
            (exam_id, name, price, cost),
        )
        myDB.commit()
        flash("Medical examination added.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding examination: {e}", "error")

    return redirect(url_for("examinations"))


#edit a medical exam info
@app.route("/examination/edit/<int:exam_id>", methods=["POST"])
def edit_examination(exam_id):
    #Fetch and validate new ID
    try:
        new_id = int(request.form.get("id"))
    except (TypeError, ValueError):
        flash("ID must be an integer.", "error")
        return redirect(url_for("examinations"))

    #If ID changed, ensure it’s not already in use by another record
    if new_id != exam_id:
        myCursor.execute("SELECT 1 FROM medical_examinations WHERE id = %s;", (new_id,))
        if myCursor.fetchone() is not None:
            flash(f"ID {new_id} is already taken by another examination.", "error")
            return redirect(url_for("examinations"))

    #Fetch other fields
    name = request.form.get("name").strip()
    try:
        price = float(request.form.get("price"))
        cost = float(request.form.get("cost"))
    except (TypeError, ValueError):
        flash("Price and cost must be numeric.", "error")
        return redirect(url_for("examinations"))

    if not name:
        flash("Name cannot be empty.", "error")
        return redirect(url_for("examinations"))

    #Update the record
    try:
        myCursor.execute(
            """UPDATE medical_examinations
               SET id = %s, name = %s, price = %s, cost = %s
               WHERE id = %s;""",
            (new_id, name, price, cost, exam_id),
        )
        myDB.commit()
        flash("Medical examination updated.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating examination: {e}", "error")

    return redirect(url_for("examinations"))


@app.route("/examination/delete/<int:exam_id>", methods=["POST"])
def delete_examination(exam_id):
    try:
        myCursor.execute("DELETE FROM medical_examinations WHERE id = %s;", (exam_id,))
        myDB.commit()
        flash("Medical examination deleted.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting examination: {e}", "error")

    return redirect(url_for("examinations"))


#Product Management -----------------------------------------
ALLOWED_TYPES = {"Sunglasses", "Optical Glasses", "Lenses", "Accessories"}

def get_sunglasses_color(prod_id):
    myCursor.execute("SELECT color FROM sunglasses WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return row[0] if row else ""

def get_sunglasses_company(prod_id):
    myCursor.execute("SELECT company_name FROM sunglasses WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return row[0] if row else ""

def get_optical_type(prod_id):
    myCursor.execute("SELECT optical_type FROM optical_glasses WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return row[0] if row else ""

def get_optical_degree(prod_id):
    myCursor.execute("SELECT degree FROM optical_glasses WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return float(row[0]) if row else 0.0

def get_lenses_color(prod_id):
    myCursor.execute("SELECT color FROM lenses WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return row[0] if row else ""

def get_accessory_type(prod_id):
    myCursor.execute("SELECT type FROM accessories WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    return row[0] if row else ""

@app.route("/products2")
def products2():
    myCursor.execute(
        "SELECT product_id, quantity, price, cost, product_type, image_path FROM product ORDER BY product_id;"
    )
    prod_data = myCursor.fetchall()
    return render_template(
        "products2.html",
        products2=prod_data,
        get_sunglasses_color=get_sunglasses_color,
        get_sunglasses_company=get_sunglasses_company,
        get_optical_type=get_optical_type,
        get_optical_degree=get_optical_degree,
        get_lenses_color=get_lenses_color,
        get_accessory_type=get_accessory_type,
    )

#add a new product
@app.route("/product2/add", methods=["POST"])
def add_product():
    #Validate ID
    try:
        prod_id = int(request.form.get("id"))
        if prod_id < 1:
            raise ValueError
    except (TypeError, ValueError):
        flash("ID must be a positive integer.", "error")
        return redirect(url_for("products2"))

    # Check if ID already exists
    myCursor.execute("SELECT 1 FROM product WHERE product_id = %s;", (prod_id,))
    if myCursor.fetchone() is not None:
        flash(f"A product with ID {prod_id} already exists.", "error")
        return redirect(url_for("products2"))

    #Validate quantity, price, cost
    try:
        qty = int(request.form.get("quantity"))
        price = float(request.form.get("price"))
        cost = float(request.form.get("cost"))
    except (TypeError, ValueError):
        flash("Quantity must be an integer; price and cost must be numeric.", "error")
        return redirect(url_for("products2"))
    img_path = request.form.get("image_path", "").strip()
    if qty < 0 or price < 0 or cost < 0:
        flash("Quantity, price, and cost must be ≥ 0.", "error")
        return redirect(url_for("products2"))

    #Validate product_type
    ptype = request.form.get("product_type")
    if ptype not in ALLOWED_TYPES:
        flash("Please select a valid product type.", "error")
        return redirect(url_for("products2"))

    #Insert into product table
    try:
        myCursor.execute(
            """
            INSERT INTO product (product_id, quantity, price, cost, product_type, image_path)
            VALUES (%s, %s, %s, %s, %s, %s);
            """,
            (prod_id, qty, price, cost, ptype, img_path),
        )
        myDB.commit()
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding product: {e}", "error")
        return redirect(url_for("products2"))

    #read subtype‐specific fields from the form and insert
    if ptype == "Sunglasses":
        s_color = request.form.get("s_color", "").strip()
        company_name = request.form.get("company_name", "").strip()
        try:
            myCursor.execute(
                "INSERT INTO sunglasses (product_id, color, company_name) VALUES (%s, %s, %s);",
                (prod_id, s_color, company_name),
            )
            myDB.commit()
            flash("Product and sunglasses record added.", "success")
        except Exception as e:
            myDB.rollback()
            flash(f"Error adding sunglasses record: {e}", "error")

    elif ptype == "Optical Glasses":
        optical_type = request.form.get("optical_type", "").strip()
        try:
            degree = float(request.form.get("degree", 0))
        except (TypeError, ValueError):
            degree = 0.0
        try:
            myCursor.execute(
                "INSERT INTO optical_glasses (product_id, optical_type, degree) VALUES (%s, %s, %s);",
                (prod_id, optical_type, degree),
            )
            myDB.commit()
            flash("Product and optical_glasses record added.", "success")
        except Exception as e:
            myDB.rollback()
            flash(f"Error adding optical_glasses record: {e}", "error")

    elif ptype == "Lenses":
        l_color = request.form.get("l_color", "").strip()
        try:
            myCursor.execute(
                "INSERT INTO lenses (product_id, color) VALUES (%s, %s);",
                (prod_id, l_color),
            )
            myDB.commit()
            flash("Product and lenses record added.", "success")
        except Exception as e:
            myDB.rollback()
            flash(f"Error adding lenses record: {e}", "error")

    elif ptype == "Accessories":
        a_type = request.form.get("a_type", "").strip()
        try:
            myCursor.execute(
                "INSERT INTO accessories (product_id, type) VALUES (%s, %s);",
                (prod_id, a_type),
            )
            myDB.commit()
            flash("Product and accessories record added.", "success")
        except Exception as e:
            myDB.rollback()
            flash(f"Error adding accessories record: {e}", "error")

    return redirect(url_for("products2"))

#edit a product 
@app.route("/product/edit/<int:prod_id>", methods=["POST"])
def edit_product(prod_id):
    #Validate new ID
    try:
        new_id = int(request.form.get("id"))
        if new_id < 1:
            raise ValueError
    except (TypeError, ValueError):
        flash("ID must be a positive integer.", "error")
        return redirect(url_for("products"))

    # Check ID if changed
    if new_id != prod_id:
        myCursor.execute("SELECT 1 FROM product WHERE product_id = %s;", (new_id,))
        if myCursor.fetchone() is not None:
            flash(f"ID {new_id} is already taken.", "error")
            return redirect(url_for("products"))

    #Validate quantity, price, cost
    try:
        qty = int(request.form.get("quantity"))
        price = float(request.form.get("price"))
        cost = float(request.form.get("cost"))
    except (TypeError, ValueError):
        flash("Quantity must be an integer; price and cost must be numeric.", "error")
        return redirect(url_for("products"))
    img_path = request.form.get("image_path", "").strip()

    if qty < 0 or price < 0 or cost < 0:
        flash("Quantity, price, and cost must be ≥ 0.", "error")
        return redirect(url_for("products"))

    #Validate product_type
    ptype = request.form.get("product_type")
    if ptype not in ALLOWED_TYPES:
        flash("Please select a valid product type.", "error")
        return redirect(url_for("products"))

    #Fetch old product_type
    myCursor.execute("SELECT product_type FROM product WHERE product_id = %s;", (prod_id,))
    row = myCursor.fetchone()
    if row is None:
        flash("Original product not found.", "error")
        return redirect(url_for("products"))
    old_type = row[0]

    #Update prodcut 
    if new_id == prod_id:
        myCursor.execute(
            """
            UPDATE product
            SET quantity = %s, price = %s, cost = %s, product_type = %s, image_path = %s
            WHERE product_id = %s;
            """,
            (qty, price, cost, ptype,img_path, prod_id),
        )
        myDB.commit()
    else:
        try:
            myCursor.execute(
                """
                UPDATE product
                SET product_id = %s, quantity = %s, price = %s, cost = %s, product_type = %s, image_path = %s
                WHERE product_id = %s;
                """,
                (new_id, qty, price, cost, ptype,img_path, prod_id),
            )
            myDB.commit()
        except Exception as e:
            myDB.rollback()
            flash(f"Error updating product: {e}", "error")
            return redirect(url_for("products2"))

    #Handle subtype changes
    try:
        #If type changed, delete old subtype row and insert new
        if old_type != ptype:
            if old_type == "Sunglasses":
                myCursor.execute("DELETE FROM sunglasses WHERE product_id = %s;", (prod_id,))
            elif old_type == "Optical Glasses":
                myCursor.execute("DELETE FROM optical_glasses WHERE product_id = %s;", (prod_id,))
            elif old_type == "Lenses":
                myCursor.execute("DELETE FROM lenses WHERE product_id = %s;", (prod_id,))
            elif old_type == "Accessories":
                myCursor.execute("DELETE FROM accessories WHERE product_id = %s;", (prod_id,))

            if ptype == "Sunglasses":
                s_color = request.form.get("s_color", "").strip()
                company_name = request.form.get("company_name", "").strip()
                myCursor.execute(
                    "INSERT INTO sunglasses (product_id, color, company_name) VALUES (%s, %s, %s);",
                    (new_id, s_color, company_name),
                )
            elif ptype == "Optical Glasses":
                optical_type = request.form.get("optical_type", "").strip()
                try:
                    degree = float(request.form.get("degree", 0))
                except (TypeError, ValueError):
                    degree = 0.0
                myCursor.execute(
                    "INSERT INTO optical_glasses (product_id, optical_type, degree) VALUES (%s, %s, %s);",
                    (new_id, optical_type, degree),
                )
            elif ptype == "Lenses":
                l_color = request.form.get("l_color", "").strip()
                myCursor.execute(
                    "INSERT INTO lenses (product_id, color) VALUES (%s, %s);",
                    (new_id, l_color),
                )
            elif ptype == "Accessories":
                a_type = request.form.get("a_type", "").strip()
                myCursor.execute(
                    "INSERT INTO accessories (product_id, type) VALUES (%s, %s);",
                    (new_id, a_type),
                )

            myDB.commit()

        else:
            #Type same: update FK if ID changed, and update subtype fields
            if ptype == "Sunglasses":
                if new_id != prod_id:
                    myCursor.execute(
                        "UPDATE sunglasses SET product_id = %s WHERE product_id = %s;",
                        (new_id, prod_id),
                    )
                s_color = request.form.get("s_color", "").strip()
                company_name = request.form.get("company_name", "").strip()
                myCursor.execute(
                    "UPDATE sunglasses SET color = %s, company_name = %s WHERE product_id = %s;",
                    (s_color, company_name, new_id),
                )

            elif ptype == "Optical Glasses":
                if new_id != prod_id:
                    myCursor.execute(
                        "UPDATE optical_glasses SET product_id = %s WHERE product_id = %s;",
                        (new_id, prod_id),
                    )
                optical_type = request.form.get("optical_type", "").strip()
                try:
                    degree = float(request.form.get("degree", 0))
                except (TypeError, ValueError):
                    degree = 0.0
                myCursor.execute(
                    "UPDATE optical_glasses SET optical_type = %s, degree = %s WHERE product_id = %s;",
                    (optical_type, degree, new_id),
                )

            elif ptype == "Lenses":
                if new_id != prod_id:
                    myCursor.execute(
                        "UPDATE lenses SET product_id = %s WHERE product_id = %s;",
                        (new_id, prod_id),
                    )
                l_color = request.form.get("l_color", "").strip()
                myCursor.execute(
                    "UPDATE lenses SET color = %s WHERE product_id = %s;",
                    (l_color, new_id),
                )

            elif ptype == "Accessories":
                if new_id != prod_id:
                    myCursor.execute(
                        "UPDATE accessories SET product_id = %s WHERE product_id = %s;",
                        (new_id, prod_id),
                    )
                a_type = request.form.get("a_type", "").strip()
                myCursor.execute(
                    "UPDATE accessories SET type = %s WHERE product_id = %s;",
                    (a_type, new_id),
                )

            myDB.commit()

        flash("Product and subtype updated.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating subtype record: {e}", "error")

    return redirect(url_for("products2"))


# Delete Product
@app.route("/product/delete/<int:prod_id>", methods=["POST"])
def delete_product(prod_id):
    try:
        # Delete from all subtype tables first
        myCursor.execute("DELETE FROM sunglasses WHERE product_id = %s;", (prod_id,))
        myCursor.execute("DELETE FROM optical_glasses WHERE product_id = %s;", (prod_id,))
        myCursor.execute("DELETE FROM lenses WHERE product_id = %s;", (prod_id,))
        myCursor.execute("DELETE FROM accessories WHERE product_id = %s;", (prod_id,))

        # Delete from product
        myCursor.execute("DELETE FROM product WHERE product_id = %s;", (prod_id,))
        myDB.commit()
        flash("Product and subtype record deleted.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting product: {e}", "error")

    return redirect(url_for("products2"))



#WAREHOUSE Management --------------------------------------------
@app.route("/warehouses")
def warehouses():
    #List all warehouses with branch location
    myCursor.execute(
        """
        SELECT w.warehouse_id, b.location 
        FROM warehouse AS w 
        LEFT JOIN branch AS b ON w.branch_id = b.branch_id
        ORDER BY w.warehouse_id;
        """
    )
    data = myCursor.fetchall()
    return render_template(
        "warehouses.html",
        warehouses=data,
        get_all_branches=get_all_branches
    )


@app.route("/warehouse/add", methods=["POST"])
def add_warehouse():
    #Validate that ID is a positive integer
    raw_id = request.form.get("id", "").strip()
    try:
        wid = int(raw_id)
        if wid < 1:
            raise ValueError
    except (TypeError, ValueError):
        flash("Warehouse ID must be a positive integer.", "error")
        return redirect(url_for("warehouses"))

    #Check if this ID already exists
    myCursor.execute("SELECT 1 FROM warehouse WHERE warehouse_id = %s;", (wid,))
    if myCursor.fetchone() is not None:
        flash(f"A warehouse with ID {wid} already exists.", "error")
        return redirect(url_for("warehouses"))

    #Validate branch_id
    branch_id = request.form.get("branch_id", "").strip()
    if not branch_id.isdigit():
        flash("Select a valid branch.", "error")
        return redirect(url_for("warehouses"))

    #Insert the new warehouse with the chosen ID
    try:
        myCursor.execute(
            "INSERT INTO warehouse (warehouse_id, branch_id) VALUES (%s, %s);",
            (wid, int(branch_id)),
        )
        myDB.commit()
        flash("Warehouse added.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding warehouse: {e}", "error")

    return redirect(url_for("warehouses"))



@app.route("/warehouse/edit/<int:wh_id>", methods=["POST"])
def edit_warehouse(wh_id):
    branch_id = request.form.get("branch_id")
    if not branch_id.isdigit():
        flash("Select a valid branch.", "error")
        return redirect(url_for("warehouses"))
    try:
        myCursor.execute(
            "UPDATE warehouse SET branch_id = %s WHERE warehouse_id = %s;",
            (int(branch_id), wh_id),
        )
        myDB.commit()
        flash("Warehouse updated.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating warehouse: {e}", "error")
    return redirect(url_for("warehouses"))


@app.route("/warehouse/delete/<int:wh_id>", methods=["POST"])
def delete_warehouse(wh_id):
    try:
        myCursor.execute("DELETE FROM warehouse WHERE warehouse_id = %s;", (wh_id,))
        myDB.commit()
        flash("Warehouse deleted.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting warehouse: {e}", "error")

    return redirect(url_for("warehouses"))

# INVENTORY Management --------------------------------------------------
@app.route("/inventory/<int:warehouse_id>")
def inventory(warehouse_id):
    #get warehouse info + product list
    #get warehouse + branch location
    myCursor.execute(
        """
        SELECT w.warehouse_id, b.location 
        FROM warehouse w
        LEFT JOIN branch b ON w.branch_id = b.branch_id
        WHERE w.warehouse_id = %s;
        """,
        (warehouse_id,),
    )
    wh_info = myCursor.fetchone()

    #list all products in this warehouse
    myCursor.execute(
        """
        SELECT wp.product_id, p.product_type, wp.quantity 
        FROM warehouse_product wp
        JOIN product p ON wp.product_id = p.product_id
        WHERE wp.warehouse_id = %s
        ORDER BY wp.product_id;
        """,
        (warehouse_id,),
    )
    items = myCursor.fetchall()

    #list all products (for “add to warehouse”)
    myCursor.execute("SELECT product_id, product_type FROM product ORDER BY product_id;")
    all_products = myCursor.fetchall()

    return render_template(
        "inventory.html",
        wh_info=wh_info,
        items=items,
        all_products=all_products,
    )


@app.route("/inventory/<int:warehouse_id>/add", methods=["POST"])
def add_inventory(warehouse_id):
    prod_id = request.form.get("product_id", "").strip()
    qty_str = request.form.get("quantity", "").strip()

    #Validate product_id and quantity
    if not prod_id.isdigit():
        flash("Select a valid product.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    try:
        qty = int(qty_str)
    except ValueError:
        flash("Quantity must be an integer.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    if qty < 0:
        flash("Quantity cannot be negative.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    prod_id = int(prod_id)

    #Fetch total stock for this product
    myCursor.execute(
        "SELECT quantity FROM product WHERE product_id = %s;", (prod_id,)
    )
    row = myCursor.fetchone()
    if not row:
        flash("Selected product does not exist.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    total_qty = row[0]

    #Compute current total across all warehouses for this product
    myCursor.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM warehouse_product WHERE product_id = %s;", 
        (prod_id,)
    )
    current_sum = myCursor.fetchone()[0]

    #Check if adding 'qty' would exceed total_qty
    if current_sum + qty > total_qty:
        flash(
            f"Cannot add {qty}. The Available quantity is {total_qty - current_sum}", 
            "error"
        )
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    #Perform the insert
    try:
        myCursor.execute(
            """
            INSERT INTO warehouse_product (warehouse_id, product_id, quantity)
            VALUES (%s, %s, %s);
            """,
            (warehouse_id, prod_id, qty),
        )
        myDB.commit()
        flash("Product added to warehouse.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding to inventory: {e}", "error")

    return redirect(url_for("inventory", warehouse_id=warehouse_id))


@app.route("/inventory/<int:warehouse_id>/edit/<int:product_id>", methods=["POST"])
def edit_inventory(warehouse_id, product_id):
    qty_str = request.form.get("quantity", "").strip()

    try:
        new_qty = int(qty_str)
    except ValueError:
        flash("Quantity must be an integer.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    if new_qty < 0:
        flash("Quantity cannot be negative.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    #Fetch total stock
    myCursor.execute(
        "SELECT quantity FROM product WHERE product_id = %s;", (product_id,)
    )
    row = myCursor.fetchone()
    if not row:
        flash("Product no longer exists.", "error")
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    total_qty = row[0]

    #Sum quantities excluding this warehouse..product record
    myCursor.execute(
        """
        SELECT COALESCE(SUM(quantity), 0)
        FROM warehouse_product
        WHERE product_id = %s
          AND NOT (warehouse_id = %s AND product_id = %s)
        """,
        (product_id, warehouse_id, product_id),
    )
    other_sum = myCursor.fetchone()[0]

    #Check if new_qty + other_sum > total_qty
    if other_sum + new_qty > total_qty:
        flash(
            f"Cannot set quantity to {new_qty}. Total in other warehouses is {other_sum}, "
            f"which would exceed master stock ({total_qty}).", 
            "error"
        )
        return redirect(url_for("inventory", warehouse_id=warehouse_id))

    #Perform the update
    try:
        myCursor.execute(
            """
            UPDATE warehouse_product
            SET quantity = %s
            WHERE warehouse_id = %s AND product_id = %s;
            """,
            (new_qty, warehouse_id, product_id),
        )
        myDB.commit()
        flash("Inventory quantity updated.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating inventory: {e}", "error")

    return redirect(url_for("inventory", warehouse_id=warehouse_id))



@app.route("/inventory/<int:warehouse_id>/delete/<int:product_id>", methods=["POST"])
def delete_inventory(warehouse_id, product_id):
    try:
        myCursor.execute(
            """
            DELETE FROM warehouse_product 
            WHERE warehouse_id = %s AND product_id = %s;
            """,
            (warehouse_id, product_id),
        )
        myDB.commit()
        flash("Product removed from warehouse.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error removing from inventory: {e}", "error")

    return redirect(url_for("inventory", warehouse_id=warehouse_id))


#Suppliers MAnagement ----------------------------------------------------
@app.route("/suppliers")
def suppliers():
    myCursor.execute(
        "SELECT supplier_id, name, phone_number, email FROM supplier ORDER BY supplier_id;"
    )
    data = myCursor.fetchall()
    return render_template("suppliers.html", suppliers=data)


#add supplier
@app.route("/supplier/add", methods=["POST"])
def add_supplier():
    #Validate supplied ID field
    raw_id = request.form.get("id", "").strip()
    try:
        sup_id = int(raw_id)
        if sup_id < 1:
            raise ValueError
    except (TypeError, ValueError):
        flash("Supplier ID must be a positive integer.", "error")
        return redirect(url_for("suppliers"))

    #Check uniqueness of the ID
    myCursor.execute(
        "SELECT 1 FROM supplier WHERE supplier_id = %s;", (sup_id,)
    )
    if myCursor.fetchone() is not None:
        flash(f"A supplier with ID {sup_id} already exists.", "error")
        return redirect(url_for("suppliers"))

    #Validate other fields
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    if not name or not phone or not email:
        flash("All fields are required.", "error")
        return redirect(url_for("suppliers"))

    #Insert with the chosen ID
    try:
        myCursor.execute(
            """
            INSERT INTO supplier (supplier_id, name, phone_number, email)
            VALUES (%s, %s, %s, %s);
            """,
            (sup_id, name, phone, email),
        )
        myDB.commit()
        flash("Supplier added.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error adding supplier: {e}", "error")

    return redirect(url_for("suppliers"))


#edit a supplier
@app.route("/supplier/edit/<int:sp_id>", methods=["POST"])
def edit_supplier(sp_id):
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    if not name or not phone or not email:
        flash("All fields are required.", "error")
        return redirect(url_for("suppliers"))

    try:
        myCursor.execute(
            """
            UPDATE supplier
            SET name = %s, phone_number = %s, email = %s
            WHERE supplier_id = %s;
            """,
            (name, phone, email, sp_id),
        )
        myDB.commit()
        flash("Supplier updated.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error updating supplier: {e}", "error")

    return redirect(url_for("suppliers"))


#delete a supplier
@app.route("/supplier/delete/<int:sp_id>", methods=["POST"])
def delete_supplier(sp_id):
    try:
        myCursor.execute(
            "DELETE FROM supplier WHERE supplier_id = %s;", (sp_id,)
        )
        myDB.commit()
        flash("Supplier deleted.", "success")
    except Exception as e:
        myDB.rollback()
        flash(f"Error deleting supplier: {e}", "error")

    return redirect(url_for("suppliers"))



########## Queries ########

@app.route("/stats")
def stats():
    return render_template(
        "stats.html"
    )

################## 1 -------------------------------------
@app.route("/stats/branches/count")
def stat_total_branches():
    myCursor.execute("SELECT COUNT(*) FROM branch;")
    total_branches = myCursor.fetchone()[0]

    myCursor.execute("SELECT * FROM branch;")
    branches_details = myCursor.fetchall()

    #Aggregate counts per location
    myCursor.execute("""
        SELECT location, COUNT(*) AS cnt
        FROM branch
        GROUP BY location
        ORDER BY location;
    """)
    loc_counts = myCursor.fetchall() 
    loc_labels = [row[0] for row in loc_counts]
    loc_values = [row[1] for row in loc_counts]

    return render_template(
        "stat_total_branches.html",
        total_branches=total_branches,
        branches_details=branches_details,
        loc_labels=loc_labels,
        loc_values=loc_values
    )


################## 2 -------------------------------------
@app.route("/stats/branches/city/<string:city>")
def stat_branches_by_city(city):
    #list of all distinct cities for the filtering 
    myCursor.execute("SELECT DISTINCT location FROM branch;")
    all_cities = [r[0] for r in myCursor.fetchall()]

    #Count branches in the chosen city
    myCursor.execute(
        "SELECT COUNT(*) FROM branch WHERE location = %s;",
        (city,)
    )
    count = myCursor.fetchone()[0]

    #Details of branches in that city
    myCursor.execute(
        "SELECT branch_id, location, phone_number FROM branch WHERE location = %s;",
        (city,)
    )
    branches = myCursor.fetchall()

    return render_template(
        "stat_branches_by_city.html",
        all_cities=all_cities,
        city=city,
        count=count,
        branches=branches
    )

################## 3 -------------------------------------
@app.route("/stats/branch/managers")
def stat_branch_managers():
    #Fetch all branches for the filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()  # list of (branch_id, location)

    #Parse optional filter
    raw = request.args.get("branch_id", "").strip()
    if raw.isdigit():
        branch_id = int(raw)
        # Filtered query
        myCursor.execute("""
          SELECT b.branch_id,
                 b.location,
                 e.emp_id,
                 e.name,
                 e.email
          FROM branch b
          JOIN employee e ON b.branch_id = e.manage_branch
          WHERE b.branch_id = %s;
        """, (branch_id,))
    else:
        branch_id = None
        #show all
        myCursor.execute("""
          SELECT b.branch_id,
                 b.location,
                 e.emp_id,
                 e.name,
                 e.email
          FROM branch b
          JOIN employee e ON b.branch_id = e.manage_branch
          ORDER BY b.branch_id, e.name;
        """)

    managers = myCursor.fetchall() 

    return render_template(
        "stat_branch_managers.html",
        all_branches=all_branches,
        selected_branch=branch_id,
        managers=managers
    )

################## 4 -------------------------------------
@app.route("/stats/employees", methods=["GET"])
def stat_employees_per_branch():
    #Fetch all branches
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()  

    #optional branch filter
    raw = request.args.get("branch_id", "").strip()
    if raw.isdigit():
        selected_branch = int(raw)
    else:
        selected_branch = None

    #count employees per branch
    myCursor.execute("""
      SELECT b.branch_id, b.location, COUNT(e.emp_id) AS emp_count
      FROM branch b
      LEFT JOIN employee e ON b.branch_id = e.work_branch
      GROUP BY b.branch_id
      ORDER BY b.branch_id;
    """)
    summary = myCursor.fetchall()
    # If a branch is selected, fetch its employee details
    details = []
    if selected_branch:
        myCursor.execute("""
          SELECT emp_id, name, email, date_of_birth, salary
          FROM employee
          WHERE work_branch = %s
          ORDER BY name;
        """, (selected_branch,))
        details = myCursor.fetchall()

    return render_template(
        "stat_employees_per_branch.html",
        all_branches=all_branches,
        selected_branch=selected_branch,
        summary=summary,
        details=details
    )
################## 5 -------------------------------------
@app.route("/stats/products", methods=["GET"])
def stat_products():
    #Fetch all branches for the filter
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #optional branch filter
    raw = request.args.get("branch_id", "").strip()
    if raw.isdigit():
        selected_branch = int(raw)
    else:
        selected_branch = None

    #all products from product table
    myCursor.execute("""
      SELECT product_id, product_type, price, cost, quantity
      FROM product
      ORDER BY product_id;
    """)
    summary = myCursor.fetchall()

    #If branch selected fetch warehouse stock for that branch
    details = []
    if selected_branch:
        myCursor.execute("""
          SELECT p.product_id, p.product_type, p.price, p.cost, wp.quantity
          FROM warehouse_product wp
          JOIN warehouse w ON wp.warehouse_id = w.warehouse_id
          JOIN product p   ON wp.product_id = p.product_id
          WHERE w.branch_id = %s
          ORDER BY p.product_id;
        """, (selected_branch,))
        details = myCursor.fetchall()

    return render_template(
        "stat_products.html",
        all_branches=all_branches,
        selected_branch=selected_branch,
        summary=summary,
        details=details
    )

################## 6 -------------------------------------
@app.route("/stats/product/quantity", methods=["GET"])
def stat_product_quantity():
    #Fetch all branches for the filter
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #Fetch all products for the filter
    myCursor.execute("SELECT product_id, product_type FROM product ORDER BY product_id;")
    all_products = myCursor.fetchall() 

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_p = request.args.get("product_id", "").strip()
    product_id = int(raw_p) if raw_p.isdigit() else None

    #If both are chosen, fetch the quantity and product details
    quantity = None
    details = None
    if branch_id and product_id:
        myCursor.execute("""
          SELECT wp.quantity,
                 p.product_type,
                 p.price,
                 p.cost
          FROM warehouse_product wp
          JOIN warehouse w ON wp.warehouse_id = w.warehouse_id
          JOIN product p   ON wp.product_id   = p.product_id
          WHERE w.branch_id  = %s
            AND p.product_id = %s;
        """, (branch_id, product_id))
        row = myCursor.fetchone()
        if row:
            quantity, ptype, price, cost = row
            details = {
                "product_id": product_id,
                "product_type": ptype,
                "price": price,
                "cost": cost,
                "branch_id": branch_id,
                "quantity": quantity
            }

    return render_template(
        "stat_product_quantity.html",
        all_branches=all_branches,
        all_products=all_products,
        selected_branch=branch_id,
        selected_product=product_id,
        details=details
    )

################## 7 -------------------------------------
@app.route("/stats/orders/customer", methods=["GET"])
def stat_orders_by_customer():
    #Fetch all customers
    myCursor.execute("SELECT customer_id, name FROM customer ORDER BY name;")
    all_customers = myCursor.fetchall() 

    #optional customer filter
    raw = request.args.get("customer_id", "").strip()
    if raw.isdigit():
        customer_id = int(raw)
    else:
        customer_id = None

    #If selected, count and fetch their orders
    total_orders = None
    orders = []
    if customer_id:
        # total count
        myCursor.execute(
            "SELECT COUNT(*) FROM orderr WHERE customer_id = %s;",
            (customer_id,)
        )
        total_orders = myCursor.fetchone()[0]

        # order details
        myCursor.execute("""
            SELECT order_id, branch_id, order_date, total_price, paid_amount, profit, discount
            FROM orderr
            WHERE customer_id = %s
            ORDER BY order_date DESC;
        """, (customer_id,))
        orders = myCursor.fetchall()  # list of tuples

    return render_template(
        "stat_orders_by_customer.html",
        all_customers=all_customers,
        selected_customer=customer_id,
        total_orders=total_orders,
        orders=orders
    )

################## 8 -------------------------------------
@app.route("/stats/exams/customer", methods=["GET"])
def stat_exams_by_customer():
    #Fetch all customers for filtering
    myCursor.execute("SELECT customer_id, name FROM customer ORDER BY name;")
    all_customers = myCursor.fetchall()

    #optional filter - customer
    raw_c = request.args.get("customer_id", "").strip()
    customer_id = int(raw_c) if raw_c.isdigit() else None

    #optional filter - month
    raw_period = request.args.get("period", "").strip()
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    total_exams = None
    exams = []

    #If customer selected, query their exams - with optional month
    if customer_id:
        #WHERE clauses
        where_clauses = ["ce.customer_id = %s"]
        params = [customer_id]

        if year and month:
            where_clauses.append("YEAR(ce.date) = %s AND MONTH(ce.date) = %s")
            params.extend([year, month])

        where_sql = " AND ".join(where_clauses)

        # Total count
        count_sql = f"SELECT COUNT(*) FROM customer_examination ce WHERE {where_sql};"
        myCursor.execute(count_sql, params)
        total_exams = myCursor.fetchone()[0]

        # Detailed list
        detail_sql = f"""
            SELECT ce.date,
                   me.name,
                   ce.result,
                   ce.profit
            FROM customer_examination ce
            JOIN medical_examinations me 
              ON ce.examination_id = me.id
            WHERE {where_sql}
            ORDER BY ce.date DESC;
        """
        myCursor.execute(detail_sql, params)
        exams = myCursor.fetchall()

    return render_template(
        "stat_exams_by_customer.html",
        all_customers=all_customers,
        selected_customer=customer_id,
        selected_period=raw_period,
        total_exams=total_exams,
        exams=exams
    )


################## 9 -------------------------------------
@app.route("/stats/orders", methods=["GET"])
def stat_orders_per_day():
    #Fetch all branches
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_date = request.args.get("order_date", "").strip()
    order_date = raw_date if raw_date else None

    #the conditional (WHERE)
    filters = []
    params = []
    if branch_id:
        filters.append("o.branch_id = %s")
        params.append(branch_id)
    if order_date:
        filters.append("o.order_date = %s")
        params.append(order_date)
    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""

    #Find the count
    myCursor.execute(f"SELECT COUNT(*) FROM orderr o {where_sql};", params)
    total_orders = myCursor.fetchone()[0]

    #Find order details
    detail_sql = f"""
      SELECT order_id, customer_id, branch_id, order_date,
             total_price, paid_amount, profit, discount
      FROM orderr o
      {where_sql}
      ORDER BY order_date DESC, order_id DESC;
    """
    myCursor.execute(detail_sql, params)
    orders = myCursor.fetchall()

    # ─── Pie chart
    if order_date:
        # if a date is chosen, group only that day
        myCursor.execute("""
          SELECT branch_id, COUNT(*) 
          FROM orderr
          WHERE order_date = %s
          GROUP BY branch_id
          ORDER BY branch_id;
        """, (order_date,))
    else:
        # no date chosen, show full distribution
        myCursor.execute("""
          SELECT branch_id, COUNT(*) 
          FROM orderr
          GROUP BY branch_id
          ORDER BY branch_id;
        """)
    pie_rows = myCursor.fetchall()
    pie_labels = [str(r[0]) for r in pie_rows]
    pie_data   = [r[1] for r in pie_rows]

    return render_template(
        "stat_orders_per_day.html",
        all_branches=all_branches,
        selected_branch=branch_id,
        selected_date=order_date,
        total_orders=total_orders,
        orders=orders,
        pie_labels=pie_labels,
        pie_data=pie_data
    )

################## 10 -------------------------------------
@app.route("/stats/earnings", methods=["GET"])
def stat_earnings():
    # Fetch all Branches
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    # Optional Filter: branch
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    # Optional Filter: month period
    raw_period = request.args.get("period", "").strip()
    period = raw_period if raw_period else None

    # Earnings in selected month (if any)
    order_earn = exam_earn = 0.0
    if period:
        year, month = map(int, period.split("-"))
        # Orders filtered by branch+month or just month
        if branch_id:
            myCursor.execute("""
              SELECT COALESCE(SUM(profit),0)
                FROM orderr
               WHERE branch_id=%s
                 AND YEAR(order_date)=%s
                 AND MONTH(order_date)=%s;
            """, (branch_id, year, month))
        else:
            myCursor.execute("""
              SELECT COALESCE(SUM(profit),0)
                FROM orderr
               WHERE YEAR(order_date)=%s
                 AND MONTH(order_date)=%s;
            """, (year, month))
        order_earn = float(myCursor.fetchone()[0])

        # Exams are never filtered by branch, only by month
        myCursor.execute("""
          SELECT COALESCE(SUM(profit),0)
            FROM customer_examination
           WHERE YEAR(date)=%s
             AND MONTH(date)=%s;
        """, (year, month))
        exam_earn = float(myCursor.fetchone()[0])
    else:
        # No period filter: sum all orders (branch still applies)
        if branch_id:
            myCursor.execute("""
              SELECT COALESCE(SUM(profit),0)
                FROM orderr
               WHERE branch_id=%s;
            """, (branch_id,))
        else:
            myCursor.execute("""
              SELECT COALESCE(SUM(profit),0)
                FROM orderr;
            """)
        order_earn = float(myCursor.fetchone()[0])

        # And sum *all* exams
        myCursor.execute("""
          SELECT COALESCE(SUM(profit),0)
            FROM customer_examination;
        """)
        exam_earn = float(myCursor.fetchone()[0])

    # Total for period
    total_earn = order_earn + exam_earn

    # Detail cards
    details = [
      {"type": "Orders",      "amount": order_earn},
      {"type": "Examinations","amount": exam_earn}
    ]

    # Prepare last 12 months earnings (global)
    today = date.today().replace(day=1)
    labels = []
    data   = []
    for i in range(11, -1, -1):
        m = today - timedelta(days=30*i)
        y, mo = m.year, m.month
        labels.append(f"{y}-{mo:02d}")

        # Order profits
        myCursor.execute("""
          SELECT COALESCE(SUM(profit),0)
            FROM orderr
           WHERE YEAR(order_date)=%s
             AND MONTH(order_date)=%s;
        """, (y, mo))
        o = float(myCursor.fetchone()[0])

        # Exam profits
        myCursor.execute("""
          SELECT COALESCE(SUM(profit),0)
            FROM customer_examination
           WHERE YEAR(date)=%s
             AND MONTH(date)=%s;
        """, (y, mo))
        e = float(myCursor.fetchone()[0])

        data.append(o + e)

    return render_template(
      "stat_earnings.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      selected_period=period,
      order_earn=order_earn,
      exam_earn=exam_earn,
      total_earn=total_earn,
      details=details,
      chart_labels=labels,
      chart_data=data
    )


################## 11 -------------------------------------
from flask import request, render_template

@app.route("/stats/best-sellers", methods=["GET"])
def stat_best_sellers():
    #Fetch all Branches for filtering 
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall() 

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_period = request.args.get("period", "").strip() 
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    #WHERE clauses
    filters = []
    params = []
    if branch_id:
        filters.append("o.branch_id = %s")
        params.append(branch_id)
    if year and month:
        filters.append("YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s")
        params.extend([year, month])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    # 4) Top 5 products query
    sql = f"""
      SELECT 
        od.product_id,
        p.product_type,
        SUM(od.quantity) AS total_sold
      FROM order_details od
      JOIN orderr o ON od.order_id = o.order_id
      JOIN product p ON od.product_id = p.product_id
      {where_sql}
      GROUP BY od.product_id, p.product_type
      ORDER BY total_sold DESC
      LIMIT 5;
    """
    myCursor.execute(sql, params)
    top_products = myCursor.fetchall()  

    return render_template(
      "stat_best_sellers.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      selected_period=raw_period or "",
      top_products=top_products
    )


################## 12-14  -------------------------------------
@app.route("/stats/insurance", methods=["GET"])
def stat_insurance_coverage():
    #Fetch all Branches for filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #Coverage category
    COVERAGE_CATEGORIES = {
        "full":    ("100.0", "100.0"),         # exactly 100%
        "ge50":    ("50.0", "99.9999"),        # [50%,100)
        "lt50":    ("0.0001", "49.9999"),      # (0,50%)
    }

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_period = request.args.get("period", "").strip() 
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    raw_cat = request.args.get("category", "")
    if raw_cat in COVERAGE_CATEGORIES:
        cat = raw_cat
        low, high = COVERAGE_CATEGORIES[cat]
    else:
        cat = None

    #WHERE clauses for filters
    filters = ["p.insurance_discount_percentege > 0"]
    params = []
    if branch_id:
        filters.append("o.branch_id = %s")
        params.append(branch_id)
    if year and month:
        filters.append("YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s")
        params.extend([year, month])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    #Fetch all orders with their insurance coverage %
    sql = f"""
      SELECT
        o.order_id,
        o.branch_id,
        o.order_date,
        o.total_price,
        p.insurance_discount_percentege AS coverage_pct
      FROM orderr o
      JOIN payment p ON o.order_id = p.order_id
      {where_sql}
    """
    myCursor.execute(sql, params)
    rows = myCursor.fetchall()

    #Apply category filter
    def in_category(pct):
        if pct is None:
            return False
        if cat == "full":
            return pct == 100.0
        if cat == "ge50":
            return pct >= 50.0 and pct < 100.0
        if cat == "lt50":
            return pct < 50.0 and pct > 0
        return True

    filtered = []
    for oid, bid, date, total, pct in rows:
        if cat:
            if not in_category(pct):
                continue
        filtered.append((oid, bid, date, total, total*(pct/100), pct))

    return render_template(
      "stat_insurance_coverage.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      selected_period=raw_period or "",
      selected_category=cat or "",
      COVERAGE_CATEGORIES=COVERAGE_CATEGORIES,
      orders=filtered
    )
################## 15  -------------------------------------
@app.route("/stats/top-customers", methods=["GET"])
def stat_top_customers():
    #Fetch all branches for filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall() 

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_period = request.args.get("period", "").strip() 
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    #WHERE clauses
    filters = []
    params = []
    if branch_id:
        filters.append("o.branch_id = %s")
        params.append(branch_id)
    if year and month:
        filters.append("YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s")
        params.extend([year, month])

    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    # 4) Top 5 customers by total spending
    sql = f"""
      SELECT 
        o.customer_id,
        c.name,
        SUM(o.total_price) AS total_spent
      FROM orderr o
      JOIN customer c ON o.customer_id = c.customer_id
      {where_sql}
      GROUP BY o.customer_id, c.name
      ORDER BY total_spent DESC
      LIMIT 5;
    """
    myCursor.execute(sql, params)
    top_customers = myCursor.fetchall()

    return render_template(
      "stat_top_customers.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      selected_period=raw_period or "",
      top_customers=top_customers
    )


################## 16  -------------------------------------
@app.route("/stats/highest-purchase", methods=["GET"])
def stat_highest_purchase():
    #Fetch all branches and customers for filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    myCursor.execute("SELECT customer_id, name FROM customer ORDER BY name;")
    all_customers = myCursor.fetchall()

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_period = request.args.get("period", "").strip()
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    raw_c = request.args.get("customer_id", "").strip()
    customer_id = int(raw_c) if raw_c.isdigit() else None

    #WHERE clauses
    filters = []
    params = []
    if branch_id:
        filters.append("o.branch_id = %s")
        params.append(branch_id)
    if year and month:
        filters.append("YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s")
        params.extend([year, month])
    if customer_id:
        filters.append("o.customer_id = %s")
        params.append(customer_id)

    where_sql = ("WHERE " + " AND ".join(filters)) if filters else ""

    #highest single order total per customer
    sql = f"""
      SELECT
        o.customer_id,
        c.name,
        MAX(o.total_price) AS highest_purchase
      FROM orderr o
      JOIN customer c ON o.customer_id = c.customer_id
      {where_sql}
      GROUP BY o.customer_id, c.name
      ORDER BY highest_purchase DESC
      LIMIT 5;
    """
    myCursor.execute(sql, params)
    top_purchases = myCursor.fetchall()

    return render_template(
      "stat_highest_purchase.html",
      all_branches=all_branches,
      all_customers=all_customers,
      selected_branch=branch_id,
      selected_period=raw_period or "",
      selected_customer=customer_id,
      top_purchases=top_purchases
    )


################## 17  -------------------------------------

################## 18  -------------------------------------
@app.route("/stats/products-by-customer", methods=["GET"])
def stat_products_by_customer():
    #Fetch all customers for the filtering
    myCursor.execute("SELECT customer_id, name FROM customer ORDER BY name;")
    all_customers = myCursor.fetchall()

    #optional filters
    raw_c = request.args.get("customer_id", "").strip()
    customer_id = int(raw_c) if raw_c.isdigit() else None

    raw_period = request.args.get("period", "").strip()
    if raw_period:
        try:
            year, month = map(int, raw_period.split("-"))
        except ValueError:
            year = month = None
    else:
        year = month = None

    #Build WHERE clause
    filters = []
    params = []
    if customer_id:
        filters.append("o.customer_id = %s")
        params.append(customer_id)
    if year and month:
        filters.append("YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s")
        params.extend([year, month])
    where_sql = "WHERE " + " AND ".join(filters) if filters else ""

    #Aggregate purchased products
    sql = f"""
      SELECT
        od.product_id,
        p.product_type,
        SUM(od.quantity)   AS total_qty,
        ROUND(SUM(od.quantity * p.price),2) AS total_spent
      FROM order_details od
      JOIN orderr o   ON od.order_id   = o.order_id
      JOIN product p  ON od.product_id = p.product_id
      {where_sql}
      GROUP BY od.product_id, p.product_type
      ORDER BY total_qty DESC;
    """
    myCursor.execute(sql, params)
    rows = myCursor.fetchall()

    return render_template(
      "stat_products_by_customer.html",
      all_customers=all_customers,
      selected_customer=customer_id,
      selected_period=raw_period or "",
      products=rows
    )


################## 19  -------------------------------------

################## 20-21  -------------------------------------
@app.route("/stats/out-of-stock", methods=["GET"])
def stat_out_of_stock():
    #Fetch all branches for filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #optional branch filter
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    #WHERE clause
    filters = ["wp.quantity = 0"]
    params = []
    if branch_id:
        filters.append("w.branch_id = %s")
        params.append(branch_id)
    where_sql = "WHERE " + " AND ".join(filters)

    #out-of-stock products per branch
    sql = f"""
      SELECT DISTINCT
        w.branch_id,
        p.product_id,
        p.product_type
      FROM warehouse_product wp
      JOIN warehouse w ON wp.warehouse_id = w.warehouse_id
      JOIN product   p ON wp.product_id   = p.product_id
      {where_sql}
      ORDER BY w.branch_id, p.product_id;
    """
    myCursor.execute(sql, params)
    rows = myCursor.fetchall()
  
    return render_template(
      "stat_out_of_stock.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      out_of_stock=rows
    )

################## 22  -------------------------------------
@app.route("/stats/users", methods=["GET"])
def stat_users():
    #optional filter: which type to show
    user_type = request.args.get("type", "").strip().lower()
    allowed = {"all", "owner", "employee", "customer"}
    if user_type not in allowed:
        user_type = "all"

    #Total counts
    myCursor.execute("SELECT COUNT(*) FROM owners;")
    owners_count = myCursor.fetchone()[0]
    myCursor.execute("SELECT COUNT(*) FROM employee;")
    employees_count = myCursor.fetchone()[0]
    myCursor.execute("SELECT COUNT(*) FROM customer;")
    customers_count = myCursor.fetchone()[0]
    total_users = owners_count + employees_count + customers_count

    #details list
    details = []
    if user_type in ("all", "owner"):
        myCursor.execute("SELECT user_id, name FROM owners ORDER BY name;")
        details.extend([("Owner",  oid, nm) for oid, nm in myCursor.fetchall()])

    if user_type in ("all", "employee"):
        myCursor.execute("SELECT user_id, name FROM employee ORDER BY name;")
        details.extend([("Employee", eid, nm) for eid, nm in myCursor.fetchall()])

    if user_type in ("all", "customer"):
        myCursor.execute("SELECT user_id, name FROM customer ORDER BY name;")
        details.extend([("Customer", cid, nm) for cid, nm in myCursor.fetchall()])

    return render_template(
        "stat_users.html",
        total_users=total_users,
        owners_count=owners_count,
        employees_count=employees_count,
        customers_count=customers_count,
        user_type=user_type,
        details=details
    )

################## 23-24  -------------------------------------
@app.route("/stats/available-products", methods=["GET"])
def stat_available_products():
    #Fetch branches for filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #Allowed product types
    PRODUCT_TYPES = ["Sunglasses", "Optical Glasses", "Lenses", "Accessories"]

    #optional filters
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    raw_t = request.args.get("product_type", "").strip()
    product_type = raw_t if raw_t in PRODUCT_TYPES else None

    #WHERE clauses: stock > 0 always
    filters = ["wp.quantity > 0"]
    params = []

    if branch_id:
        filters.append("w.branch_id = %s")
        params.append(branch_id)

    if product_type:
        filters.append("p.product_type = %s")
        params.append(product_type)

    where_sql = "WHERE " + " AND ".join(filters)

    #Find the available products
    sql = f"""
      SELECT
        w.branch_id,
        p.product_id,
        p.product_type,
        wp.quantity
      FROM warehouse_product wp
      JOIN warehouse w ON wp.warehouse_id = w.warehouse_id
      JOIN product   p ON wp.product_id   = p.product_id
      {where_sql}
      ORDER BY w.branch_id, p.product_id;
    """
    myCursor.execute(sql, params)
    rows = myCursor.fetchall()

    total_available = len(rows)

    return render_template(
      "stat_available_products.html",
      all_branches=all_branches,
      product_types=PRODUCT_TYPES,
      selected_branch=branch_id,
      selected_type=product_type,
      total_available=total_available,
      products=rows
    )

######## 28 --------------------------------------------------------
@app.route("/stats/supplied", methods=["GET"])
def stat_supplied():
    #Fetch all suppliers for the dropdown
    myCursor.execute("SELECT supplier_id, name FROM supplier ORDER BY name;")
    all_suppliers = myCursor.fetchall()

    #optional supplier filter
    raw = request.args.get("supplier_id", "").strip()
    supplier_id = int(raw) if raw.isdigit() else None

    #Summary - total quantity supplied per supplier
    summary_filters = []
    params = []
    if supplier_id:
        summary_filters.append("po.supplier_id = %s")
        params.append(supplier_id)
    where_sql = "WHERE " + " AND ".join(summary_filters) if summary_filters else ""

    summary_sql = f"""
      SELECT s.supplier_id,
             s.name,
             COALESCE(SUM(pod.quantity),0) AS total_qty
      FROM supplier s
      LEFT JOIN purchase_order po ON s.supplier_id = po.supplier_id
      LEFT JOIN purchase_order_details pod ON po.purchase_order_id = pod.purchase_order_id
      {where_sql}
      GROUP BY s.supplier_id, s.name
      ORDER BY total_qty DESC;
    """
    myCursor.execute(summary_sql, params)
    summary = myCursor.fetchall()

    #in details which products this supplier supplied
    details = []
    if supplier_id:
        myCursor.execute("""
          SELECT pod.product_id,
                 p.product_type,
                 pod.quantity,
                 pod.cost_per_unit
          FROM purchase_order_details pod
          JOIN purchase_order po ON pod.purchase_order_id = po.purchase_order_id
          JOIN product p ON pod.product_id = p.product_id
          WHERE po.supplier_id = %s
          ORDER BY pod.product_id;
        """, (supplier_id,))
        details = myCursor.fetchall()

    return render_template(
      "stat_supplied.html",
      all_suppliers=all_suppliers,
      selected_supplier=supplier_id,
      summary=summary,
      details=details
    )

####### 29 ------------------------------------------------------------------
@app.route("/stats/restock", methods=["GET"])
def stat_restock():
    #Fetch all branches for the filtering
    myCursor.execute("SELECT branch_id, location FROM branch ORDER BY location;")
    all_branches = myCursor.fetchall()

    #optional branch filter
    raw_b = request.args.get("branch_id", "").strip()
    branch_id = int(raw_b) if raw_b.isdigit() else None

    #optional threshold input (default to 10 if missing or invalid)
    raw_thr = request.args.get("threshold", "").strip()
    try:
        threshold = int(raw_thr)
        if threshold < 0:
            raise ValueError
    except (ValueError, TypeError):
        threshold = 10

    #the restock query
    params = [threshold]
    if branch_id:
        # Sum per product within the chosen branch
        sql = """
          SELECT p.product_id,
                 p.product_type,
                 SUM(wp.quantity) AS total_qty
          FROM warehouse_product wp
          JOIN warehouse w ON wp.warehouse_id = w.warehouse_id
          JOIN product p   ON wp.product_id   = p.product_id
          WHERE w.branch_id = %s
          GROUP BY p.product_id, p.product_type
          HAVING total_qty < %s
          ORDER BY total_qty ASC;
        """
        params.insert(0, branch_id)
    else:
        # Sum per product across all branches
        sql = """
          SELECT p.product_id,
                 p.product_type,
                 SUM(wp.quantity) AS total_qty
          FROM warehouse_product wp
          JOIN product p ON wp.product_id = p.product_id
          GROUP BY p.product_id, p.product_type
          HAVING total_qty < %s
          ORDER BY total_qty ASC;
        """
    myCursor.execute(sql, params)
    rows = myCursor.fetchall()

    total_needed = len(rows)

    return render_template(
      "stat_restock.html",
      all_branches=all_branches,
      selected_branch=branch_id,
      threshold=threshold,
      total_needed=total_needed,
      products=rows
    )


if __name__ == '__main__':
    app.run(debug=True)