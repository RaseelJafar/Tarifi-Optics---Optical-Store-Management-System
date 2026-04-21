import pymysql

myDB = pymysql.connect(host="localhost", user="root", password="r@1234")
myCursor = myDB.cursor()

myCursor.execute("drop database if exists optics_store")
myCursor.execute("create database optics_store")
myCursor.execute("use optics_store")
myCursor.execute("set SQL_SAFE_UPDATES=0")

myCursor.execute(""" -- user
    create table user(
        user_id int primary key, 
        password varchar(30)
        );
        """)

myCursor.execute(""" 
    -- customer
    create table customer(
        customer_id int AUTO_INCREMENT primary key, 
        name varchar(20),
        phone_number varchar(10),
        date_of_birth date,
        location varchar(20),
        user_id int, 
        foreign key(user_id) references user(user_id) ON UPDATE CASCADE);
                    """)

myCursor.execute(""" -- branch
    create table branch(
        branch_id int AUTO_INCREMENT primary key, 
        location varchar(30), 
        phone_number varchar(10));
        """)

myCursor.execute(""" -- employee
    create table employee(
        emp_id int AUTO_INCREMENT primary key,
        name varchar(20), 
        email varchar(50),
        date_of_birth date, 
        salary decimal,
        work_branch int NOT NULL, 
        user_id int, 
        manage_branch int,
        foreign key (work_branch) references branch(branch_id) ON DELETE CASCADE ON UPDATE CASCADE, 
        foreign key (user_id) references user(user_id) ON UPDATE CASCADE,
        foreign key (manage_branch) references branch(branch_id) ON DELETE CASCADE ON UPDATE CASCADE);
                 """)


myCursor.execute(""" -- owners
    create table owners(
        owner_id int primary key, 
        name varchar(20), 
        date_of_birth date,
        phone_number varchar(10), 
        email varchar(50), 
        ownership_percentage decimal,
        user_id int, 
        foreign key(user_id) references user(user_id) ON UPDATE CASCADE);
                 """)

myCursor.execute(""" -- owners_branch
    create table owners_branch(
        owner_id int, 
        branch_id int,
        primary key(owner_id,branch_id),
        foreign key(owner_id) references owners(owner_id) ON UPDATE CASCADE, 
        foreign key(branch_id) references branch(branch_id) ON DELETE CASCADE ON UPDATE CASCADE); 
                 """)

myCursor.execute(""" -- orderr
    create table orderr(
        order_id INT AUTO_INCREMENT primary key, 
        customer_id int, 
        branch_id int null4, 
        order_date date,
        total_price decimal, 
        paid_amount decimal, 
        profit decimal, 
        discount decimal,
        foreign key (customer_id) references customer(customer_id) ON UPDATE CASCADE,
        foreign key (branch_id) references branch(branch_id) ON DELETE SET NULL ON UPDATE CASCADE); 
                 """)

myCursor.execute(""" -- payment_method
    create table payment_method(
        payment_id int primary key,
        method_name varchar(30)    
        ); """)

myCursor.execute(""" -- payment
    create table payment(
        payment_id int, 
        order_id int, 
        insurance_discount_percentege decimal(5,2), 
        insurance varchar(30), 
        primary key (payment_id,order_id),
        foreign key (order_id) references orderr(order_id) ON UPDATE CASCADE,
        foreign key(payment_id) references payment_method(payment_id) ON UPDATE CASCADE); 
                 """)
    
myCursor.execute(""" -- medical_examinations
    create table medical_examinations(
        id int primary key, 
        name varchar(30), 
        price decimal, 
        cost decimal); 
                 """)
 

myCursor.execute(""" -- customer_examination
    create table customer_examination(
        examination_id int, 
        customer_id int, 
        date date,
        result varchar(100), 
        profit decimal,
        payment_id int NOT NULL, 
        primary key (examination_id, customer_id),
        foreign key (examination_id) references medical_examinations(id) ON DELETE RESTRICT ON UPDATE CASCADE, 
        foreign key (customer_id) references customer(customer_id) ON UPDATE CASCADE,
        foreign key(payment_id) references payment_method(payment_id) ON UPDATE CASCADE); 
                 """ )

myCursor.execute(""" -- product
    create table product(
        product_id int primary key AUTO_INCREMENT, 
        quantity INT NOT NULL DEFAULT 0, 
        price DECIMAL(10,2) NOT NULL, 
        cost DECIMAL(10,2) NOT NULL, 
        product_type VARCHAR(20) NOT NULL); 
                 """)
 
myCursor.execute(""" -- order_details
    create table order_details(
        order_id int NOT NULL, 
        product_id int,
        quantity int, 
        primary key(order_id, product_id),
        foreign key (order_id) references orderr(order_id) ON UPDATE CASCADE,
        foreign key(product_id) references product(product_id) ON UPDATE CASCADE ON DELETE RESTRICT); 
                 """)
 

myCursor.execute(""" -- sunglasses
    create table sunglasses(
        product_id int primary key, 
        color varchar(30),
        company_name varchar(30), 
        foreign key (product_id) references product(product_id) ON DELETE CASCADE ON UPDATE CASCADE); 
                 """)


myCursor.execute(""" -- accessories
    create table accessories(
        product_id int primary key, 
        type varchar(30), 
        foreign key (product_id) references product(product_id) ON DELETE CASCADE ON UPDATE CASCADE); 
                 """)

myCursor.execute(""" -- optical_glasses
    create table optical_glasses(
        product_id int primary key, 
        optical_type varchar(30),
        degree decimal, 
        foreign key (product_id) references product(product_id) ON UPDATE CASCADE ON DELETE CASCADE); 
                 """)

myCursor.execute(""" -- lenses
create table lenses(
        product_id int primary key, 
        color varchar(30), 
        foreign key (product_id) references product(product_id) ON DELETE CASCADE ON UPDATE CASCADE); """)


myCursor.execute(""" -- warehouse
    create table warehouse(
        warehouse_id int primary key, 
        branch_id int,
        foreign key(branch_id) references branch(branch_id) on delete cascade ON UPDATE CASCADE);""")


myCursor.execute(""" -- warehouse_product
    create table warehouse_product(
        warehouse_id int, 
        product_id int, 
        primary key(warehouse_id, product_id), 
        quantity int,
        foreign key (warehouse_id) references warehouse(warehouse_id) ON DELETE CASCADE ON UPDATE CASCADE,
        foreign key (product_id) references product(product_id) ON UPDATE CASCADE ON DELETE RESTRICT);
                 """)


myCursor.execute(""" -- supplier
    create table supplier(
        supplier_id int primary key, 
        name varchar(30), 
        phone_number varchar(10), 
        email varchar(50));
                 """)


myCursor.execute(""" -- purchase_order
    create table purchase_order(
        purchase_order_id int primary key AUTO_INCREMENT, 
        supplier_id int, 
        purchase_date date,
        foreign key (supplier_id) references supplier(supplier_id) ON UPDATE CASCADE ON DELETE SET NULL);
                 """)


myCursor.execute(""" -- purchase_order_details
    create table purchase_order_details(
        purchase_order_id int, 
        product_id int, 
        primary key(purchase_order_id, product_id),
        quantity int, 
        cost_per_unit decimal,
        foreign key(purchase_order_id) references purchase_order(purchase_order_id) ON UPDATE CASCADE,
        foreign key(product_id) references product(product_id) ON UPDATE CASCADE ON DELETE RESTRICT);
                 """)
 
myCursor.execute(""" -- branch_place_purchase
    create table branch_place_purchase_order(
        branch_id int, 
        purchase_order_id int, 
        primary key(branch_id, purchase_order_id),
        foreign key (branch_id) references branch(branch_id) ON DELETE CASCADE ON UPDATE CASCADE,
        foreign key (purchase_order_id) references purchase_order(purchase_order_id) ON UPDATE CASCADE); 
                 """)

##########################################################################################################################

myCursor.execute("""
    INSERT INTO branch (branch_id, location, phone_number) VALUES
    (1, 'Ramallah', '0590000001'),
    (2, 'Nablus', '0590000002'),
    (3, 'Hebron', '0590000003');
""")


myCursor.execute("""
    INSERT INTO user (user_id, password) VALUES 
    (2, 'pass2'),
    (3, 'pass3'),
    (4, 'pass4'),
    (5, 'pass5'),
    (6, 'pass6'),
    (7, 'pass7'),
    (8, 'pass8'),
    (9, 'pass9'),
    (10, 'pass10'),
    (11, 'pass11'),
    (14, 'pass14'),
    (15, 'pass15'),
    (20, 'pass20');
""")

myCursor.execute("""
    INSERT INTO payment_method(payment_id, method_name) VALUES
    (1, 'Cash'),
    (2, 'Credit Card'),
    (3,'insurance');
    """)


myCursor.execute("""
    INSERT INTO owners(owner_id, name, date_of_birth, phone_number, email, ownership_percentage, user_id) VALUES
    (1, 'Maher Taha', '1970-01-30', '0593334444', 'maher@owners.com', 60.0, 14);

""")

myCursor.execute("""
    INSERT INTO owners_branch(owner_id, branch_id) VALUES
    (1, 1),
    (1, 2);
""")

myCursor.execute("""
    INSERT INTO employee(emp_id, name, email, date_of_birth, salary, work_branch, user_id, manage_branch) VALUES
    (1, 'Sami Odeh', 'sami@optics.com', '1985-12-11', 3500.00, 1, 11, 1),
    (2, 'Haneen Issa', 'haneen@optics.com', '1990-07-05', 3700.00, 2, 15, 2),
    (3, 'Hashem Mohammed', 'Mohammed@optics.com', '1998-09-11', 3400.00, 3, 20, NULL);
""")

myCursor.execute("""
    insert into customer(customer_id, name, phone_number, date_of_birth, location, user_id)
    values
    (1, 'Ahmed', '0591234567', '1995-03-15', 'Ramallah', 2),
    (2, 'Sara', '0597654321', '1997-06-22', 'Nablus', 3),
    (3, 'Khaled', '0591122334', '1990-01-10', 'Hebron', 4),
    (4, 'Leila', '0595566778', '1993-08-05', 'Bethlehem', 5),
    (5, 'Yousef', '0596677889', '1998-11-30', 'Jericho', 6),
    (6, 'Mariam', '0591112233', '1996-07-18', 'Jenin', 7),
    (7, 'Omar', '0593334455', '1994-02-09', 'Tulkarem', 8),
    (8, 'Huda', '0592223344', '1999-09-12', 'Ramallah', 9),
    (9, 'Fadi', '0594445566', '1991-03-27', 'Hebron', 10);
                 """)


myCursor.execute("""
    ALTER TABLE product ADD COLUMN name VARCHAR(50);
"""
)

myCursor.execute("""
    ALTER TABLE product ADD COLUMN image_path VARCHAR(100);
""")

myCursor.execute("""
    INSERT INTO product (product_id, quantity, price, cost, product_type, name, image_path) VALUES
    (1, 10, 150.00, 90.00, 'sunglasses', 'Ray-Ban Aviator', 'images/aviator.jpg'),
    (2, 30, 200.00, 120.00, 'optical_glasses', 'Blue Light Blocker', 'images/bluelight.jpg'),
    (3, 100, 20.00, 10.00, 'accessories', 'Lens Cleaning Kit', 'images/cleaningkit.jpg'),
    (4, 60, 45.00, 25.00, 'lenses', 'Green Tint Lens', 'images/greentint.jpg'),
    (5, 5, 180.00, 100.00, 'sunglasses', 'round', 'images/round_sunglasses.jpg');
    """)

myCursor.execute("""
    INSERT INTO sunglasses (product_id, color, company_name) VALUES
    (1, 'Gold', 'Ray-Ban'),
    (5, 'Black', 'round');
""")

myCursor.execute("""
    INSERT INTO optical_glasses (product_id, optical_type, degree) VALUES
    (2, 'Anti-Blue Light', 0.00);
""")

myCursor.execute("""
    INSERT INTO accessories (product_id, type) VALUES
    (3, 'Cleaning Kit');
""")

myCursor.execute("""
    INSERT INTO lenses (product_id, color) VALUES
    (4, 'Green'); 
""")

myCursor.execute("""
    INSERT INTO orderr (order_id, customer_id, branch_id, order_date, total_price, paid_amount, profit, discount) VALUES
    (101, 1, 1, '2025-06-01', 150.00, 150.00, 60.00, 0.00),
    (102, 2, 1, '2025-06-02', 400.00, 200.00, 150.00, 50.00),
    (103, 1, 2, '2025-06-03', 65.00, 65.00, 30.00, 0.00);              
""")


myCursor.execute("""
    INSERT INTO payment(payment_id, order_id, insurance_discount_percentege, insurance) VALUES
    (1, 101, 0.00, NULL),
    (2, 102, 50.00, 'Medicare'),
    (3, 103, 20.00, 'HealthInsurance');
    """)


myCursor.execute("""
    INSERT INTO medical_examinations(id, name, price, cost) VALUES
    (1, 'Eye Pressure Test', 50.00, 30.00),
    (2, 'Retina Scan', 80.00, 40.00),
    (3, 'Vision Test', 30.00, 15.00);
""")

myCursor.execute("""
    INSERT INTO customer_examination(examination_id, customer_id, date, result, profit, payment_id) VALUES
    (1, 1, '2025-06-15', 'Normal pressure', 20.00, 1),
    (2, 2, '2025-06-20', 'Mild retinal swelling', 40.00, 1);
    """)

myCursor.execute("""
    INSERT INTO order_details (order_id, product_id, quantity) VALUES
    (101, 1, 1),
    (102, 2, 2),
    (102, 5, 1),
    (103, 3, 3),
    (103, 4, 1);
""")

myCursor.execute("""
    INSERT INTO warehouse(warehouse_id, branch_id) VALUES
    (1, 1),
    (2, 2);
""")

myCursor.execute("""
    INSERT INTO warehouse_product(warehouse_id, product_id, quantity) VALUES
    (1, 1, 20),
    (1, 2, 10),
    (2, 3, 50),
    (2, 4, 25);
    """)

myCursor.execute("""
    INSERT INTO supplier(supplier_id, name, phone_number, email) VALUES
    (1, 'OptixCo', '0598889991', 'contact@optixco.com'),
    (2, 'VisionGear', '0598889992', 'sales@visiongear.com');
    """)

myCursor.execute("""
    INSERT INTO purchase_order(purchase_order_id, supplier_id, purchase_date) VALUES
    (1, 1, '2025-05-15'),
    (2, 2, '2025-05-20');
    """)

myCursor.execute("""
    INSERT INTO purchase_order_details(purchase_order_id, product_id, quantity, cost_per_unit) VALUES
    (1, 1, 30, 85.00),
    (2, 2, 20, 100.00);
    """)

myCursor.execute("""
    INSERT INTO branch_place_purchase_order(branch_id, purchase_order_id) VALUES
    (1, 1),
    (2, 2);
    """)



 
myDB.commit()