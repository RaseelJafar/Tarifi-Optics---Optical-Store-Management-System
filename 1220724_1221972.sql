drop database if exists optics_store;
create database optics_store;
use optics_store;
set SQL_SAFE_UPDATES=0;
 -- user
    create table user(
        user_id int primary key, 
        password varchar(30));
        
-- customer
    create table customer(
        customer_id int primary key, 
        name varchar(20),
        phone_number varchar(10),
        date_of_birth date,
        location varchar(20),
        user_id int, 
        foreign key(user_id) references user(user_id));
        
-- branch
    create table branch(
        branch_id int primary key, 
        location varchar(30), 
        phone_number varchar(10));
        
-- employee
    create table employee(
        emp_id int primary key,
        name varchar(20), 
        email varchar(50),
        date_of_birth date, 
        salary decimal,
        work_branch int NOT NULL, 
        user_id int, 
        manage_branch int NOT NULL,
        foreign key (work_branch) references branch(branch_id), 
        foreign key (user_id) references user(user_id),
        foreign key (manage_branch) references branch(branch_id));
        
-- owners
    create table owners(
        owner_id int primary key, 
        name varchar(20), 
        date_of_birth date,
        phone_number varchar(10), 
        email varchar(50), 
        ownership_percentage decimal,
        user_id int, 
        foreign key(user_id) references user(user_id));
        
-- owners_branch
    create table owners_branch(
        owner_id int, 
        branch_id int,
        primary key(owner_id,branch_id),
        foreign key(owner_id) references owners(owner_id), 
        foreign key(branch_id) references branch(branch_id)); 
        
-- orderr
    create table orderr(
        order_id int primary key, 
        customer_id int, 
        branch_id int, 
        order_date date,
        total_price decimal, 
        paid_amount decimal, 
        profit decimal, 
        discount decimal,
        foreign key (customer_id) references customer(customer_id),
        foreign key (branch_id) references branch(branch_id));
 
 -- payment_method
    create table payment_method(payment_id int primary key, method_name varchar(30));      

 -- payment
    create table payment(
        payment_id int, 
        order_id int, 
        amount decimal, 
        date date, 
        insurance_discount decimal, 
        insurance varchar(30), primary key (payment_id,order_id),
        foreign key (order_id) references orderr(order_id),
        foreign key(payment_id) references payment_method(payment_id)); 
  
-- medical_examinations
    create table medical_examinations(
        id int primary key, 
        name varchar(30), 
        price decimal, 
        cost decimal); 
        
-- customer_examination
    create table customer_examination(
        examination_id int, 
        customer_id int, 
        date date,
        result varchar(100), 
        profit decimal, 
        primary key (examination_id, customer_id),
        foreign key (examination_id) references medical_examinations(id), payment_id int NOT NULL,
        foreign key (customer_id) references customer(customer_id),
        foreign key(payment_id) references payment_method(payment_id)); 
        
-- product
    create table product(
        product_id int primary key, 
        quantity int, 
        price decimal, 
        cost decimal, 
        product_type varchar(20)); 
        
-- order_details
    create table order_details(
        order_id int NOT NULL, 
        product_id int,
        quantity int, 
        price decimal, 
        primary key(order_id, product_id),
        foreign key (order_id) references orderr(order_id),
        foreign key(product_id) references product(product_id)); 
        
-- sunglasses
    create table sunglasses(
        product_id int primary key, 
        color varchar(30),
        company_name varchar(30), 
        foreign key (product_id) references product(product_id));

 -- accessories
    create table accessories(
        product_id int primary key, 
        type varchar(30), 
        foreign key (product_id) references product(product_id)); 
        
-- optical_glasses
    create table optical_glasses(
        product_id int primary key, 
        optical_type varchar(30),
        degree decimal, 
        foreign key (product_id) references product(product_id)); 
        
-- lenses
create table lenses(
        product_id int primary key, 
        color varchar(30), 
        foreign key (product_id) references product(product_id));

-- warehouse
    create table warehouse(
        warehouse_id int primary key, 
        branch_id int,
        foreign key(branch_id) references branch(branch_id) on delete cascade);
        
-- warehouse_product
    create table warehouse_product(
        warehouse_id int, 
        product_id int, 
        primary key(warehouse_id, product_id), 
        quantity int);
        
-- supplier
    create table supplier(
        supplier_id int primary key, 
        name varchar(30), 
        phone_number varchar(10), 
        email varchar(50));
        
-- purchase_order
    create table purchase_order(
        purchase_order_id int primary key, 
        supplier_id int, 
        purchase_date date,
        foreign key (supplier_id) references supplier(supplier_id));
        
 -- purchase_order_details
    create table purchase_order_details(
        purchase_order_id int primary key, 
        product_id int, 
        quantity int, 
        cost_per_unit decimal,
        foreign key(purchase_order_id) references purchase_order(purchase_order_id),
        foreign key(product_id) references product(product_id));
        
-- branch_place_purchase
    create table branch_place_purchase_order(
        branch_id int, 
        purchase_order_id int, 
        primary key(branch_id, purchase_order_id),
        foreign key (branch_id) references branch(branch_id),
        foreign key (purchase_order_id) references purchase_order(purchase_order_id)); 

 INSERT INTO user (user_id, password) VALUES 
    (2, 'pass2'),
    (3, 'pass3'),
    (4, 'pass4'),
    (5, 'pass5'),
    (6, 'pass6'),
    (7, 'pass7'),
    (8, 'pass8'),
    (9, 'pass9'),
    (10, 'pass10');
    
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

show tables;
select * from user;
select * from customer;
