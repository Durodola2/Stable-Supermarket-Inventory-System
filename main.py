"""Inventory Management System desktop application."""
import os
import json
import secrets
import hashlib
import subprocess
import shutil
import sys
from datetime import datetime, timedelta
from decimal import Decimal

BASE_DIR = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    _bundle_dir = sys._MEIPASS
    os.environ.setdefault("TCL_LIBRARY", os.path.join(_bundle_dir, "tcl", "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", os.path.join(_bundle_dir, "tcl", "tk8.6"))

import tkinter.messagebox as messagebox
import customtkinter as ctk
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import bcrypt

load_dotenv(os.path.join(BASE_DIR, ".env"))
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Database:
    def __init__(self):
        self.config = {"host": os.getenv("DB_HOST", "localhost"), "port": int(os.getenv("DB_PORT", "3306")),
                       "database": os.getenv("DB_NAME", "inventory_management"), "user": os.getenv("DB_USER", "root"),
                       "password": os.getenv("DB_PASSWORD", "")}

    def connect(self):
        return mysql.connector.connect(**self.config)

    def query(self, sql, params=(), one=False):
        conn = self.connect(); cur = conn.cursor(dictionary=True)
        try:
            cur.execute(sql, params); rows = cur.fetchall(); return rows[0] if one and rows else (None if one else rows)
        finally: cur.close(); conn.close()

    def execute(self, sql, params=()):
        conn = self.connect(); cur = conn.cursor()
        try:
            cur.execute(sql, params); conn.commit(); return cur.lastrowid
        except: conn.rollback(); raise
        finally: cur.close(); conn.close()


class Table(ctk.CTkFrame):
    def __init__(self, parent, columns, select_callback=None):
        super().__init__(parent, fg_color="transparent"); self.columns=columns; self.select_callback=select_callback; self.selected=None
        self.grid_columnconfigure(0, weight=1)
        self.header=ctk.CTkFrame(self, fg_color=("#dce7f5", "#20344a")); self.header.grid(row=0,column=0,sticky="ew")
        for i, col in enumerate(columns): self.header.grid_columnconfigure(i, weight=1); ctk.CTkLabel(self.header,text=col.upper(),font=ctk.CTkFont(weight="bold")).grid(row=0,column=i,padx=8,pady=8,sticky="w")
        self.body=ctk.CTkScrollableFrame(self, fg_color="transparent"); self.body.grid(row=1,column=0,sticky="nsew"); self.grid_rowconfigure(1,weight=1)

    def load(self, rows):
        for w in self.body.winfo_children(): w.destroy()
        self.selected=None
        for r, row in enumerate(rows):
            frame=ctk.CTkFrame(self.body, fg_color=("#f7f9fc", "#172432")); frame.pack(fill="x",pady=1)
            for i,col in enumerate(self.columns):
                value=str(self.value(row, col))
                ctk.CTkLabel(frame,text=value,anchor="w").grid(row=0,column=i,padx=8,pady=7,sticky="ew"); frame.grid_columnconfigure(i,weight=1)
            frame.bind("<Button-1>", lambda e, x=row:self.choose(x))
            for child in frame.winfo_children(): child.bind("<Button-1>",lambda e,x=row:self.choose(x))
    def choose(self, row):
        self.selected=row
        if self.select_callback: self.select_callback(row)
    @staticmethod
    def value(row, field):
        target = field.lower().replace(" ", "_")
        for key, value in row.items():
            if key.lower().replace(" ", "_") == target:
                return value
        return ""


class Login(ctk.CTkFrame):
    def __init__(self, app):
        super().__init__(app); self.app=app
        card=ctk.CTkFrame(self,width=390); card.place(relx=.5,rely=.5,anchor="center")
        ctk.CTkLabel(card,text="Inventory Manager",font=ctk.CTkFont(size=28,weight="bold")).pack(pady=(35,5))
        ctk.CTkLabel(card,text="Sign in to continue",text_color="gray").pack(pady=(0,24))
        self.username=ctk.CTkEntry(card,placeholder_text="Username",width=300); self.username.pack(pady=8)
        self.password=ctk.CTkEntry(card,placeholder_text="Password",show="*",width=300); self.password.pack(pady=8)
        self.remember=ctk.CTkCheckBox(card,text="Remember me for 30 days"); self.remember.pack(anchor="w",padx=44,pady=(6,0))
        ctk.CTkButton(card,text="Sign in",width=300,command=self.sign_in).pack(pady=(18,35))
        self.password.bind("<Return>",lambda e:self.sign_in())
    def sign_in(self):
        try:
            user=self.app.db.query("SELECT * FROM users WHERE username=%s",(self.username.get().strip(),),one=True)
            if not user or not bcrypt.checkpw(self.password.get().encode(), user['password_hash'].encode()): raise ValueError
            self.app.user=user
            if self.remember.get(): self.app.remember_user()
            else: self.app.clear_remembered_user()
            self.app.show_main()
        except ValueError: messagebox.showerror("Sign in failed","Incorrect username or password.")
        except Error as e: messagebox.showerror("Database unavailable",f"Could not connect to MySQL.\n\n{e}")


class App(ctk.CTk):
    def __init__(self):
        super().__init__(); self.title("Inventory Management System"); self.geometry("1240x760"); self.minsize(1000,650)
        self.db=Database(); self.user=None; self.current=None; self.sale_cart=[]; self.session_path=os.path.join(BASE_DIR,".session.json"); self.login=Login(self); self.login.pack(fill="both",expand=True)
        self.bootstrap(); self.restore_session()
    def bootstrap(self):
        try:
            if not self.db.query("SHOW TABLES LIKE 'users'"):
                messagebox.showerror("Database not initialized","Run database/schema.sql first, then reopen the app."); return
            self.db.execute("""CREATE TABLE IF NOT EXISTS user_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, token_hash CHAR(64) NOT NULL UNIQUE,
                expires_at DATETIME NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")
            if not self.db.query("SELECT id FROM users LIMIT 1"):
                if messagebox.askyesno("Create administrator","No users exist. Create the initial administrator account now?"):
                    self.create_admin()
        except Error: pass

    def remember_user(self):
        self.clear_remembered_user()
        token=secrets.token_urlsafe(48); token_hash=hashlib.sha256(token.encode()).hexdigest()
        expires_at=datetime.now()+timedelta(days=30)
        self.db.execute("INSERT INTO user_sessions (user_id,token_hash,expires_at) VALUES (%s,%s,%s)",(self.user['id'],token_hash,expires_at))
        with open(self.session_path,"w",encoding="utf-8") as file: json.dump({"token":token},file)

    def clear_remembered_user(self):
        try:
            if os.path.exists(self.session_path):
                with open(self.session_path,encoding="utf-8") as file: token=json.load(file).get("token","")
                if token: self.db.execute("DELETE FROM user_sessions WHERE token_hash=%s",(hashlib.sha256(token.encode()).hexdigest(),))
                os.remove(self.session_path)
        except (OSError, ValueError, Error):
            if os.path.exists(self.session_path): os.remove(self.session_path)

    def restore_session(self):
        try:
            if not os.path.exists(self.session_path): return
            with open(self.session_path,encoding="utf-8") as file: token=json.load(file).get("token","")
            user=self.db.query("""SELECT u.* FROM user_sessions s JOIN users u ON u.id=s.user_id
                WHERE s.token_hash=%s AND s.expires_at>NOW()""",(hashlib.sha256(token.encode()).hexdigest(),),one=True)
            if not user: self.clear_remembered_user(); return
            self.user=user; self.show_main()
        except (OSError, ValueError, Error):
            self.clear_remembered_user()
    def create_admin(self):
        dialog=ctk.CTkInputDialog(text="Enter a username for the administrator:",title="Initial setup"); username=dialog.get_input()
        if not username: return
        password=ctk.CTkInputDialog(text="Enter a password (minimum 8 characters):",title="Initial setup").get_input()
        if not password or len(password)<8: messagebox.showwarning("Invalid password","Use at least 8 characters."); return
        try:
            self.db.execute("INSERT INTO users (username,password_hash,full_name,role) VALUES (%s,%s,%s,'Administrator')",(username,bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),username))
            messagebox.showinfo("Ready","Administrator account created. You can sign in now.")
        except Error as e: messagebox.showerror("Setup failed",str(e))
    def show_main(self):
        self.login.destroy(); self.sidebar=ctk.CTkFrame(self,width=210,corner_radius=0); self.sidebar.pack(side="left",fill="y")
        ctk.CTkLabel(self.sidebar,text="INVENTORY\nMANAGER",font=ctk.CTkFont(size=19,weight="bold"),justify="left").pack(anchor="w",padx=22,pady=(28,20))
        pages=[("Dashboard",self.dashboard),("Products",self.products),("New Sale",self.sales),("Sales History",self.sales_history)]
        if self.user['role']=="Administrator":
            pages.extend([("Categories",lambda:self.simple_crud("Categories","categories",[("name","Name"),("description","Description")])),("Suppliers",lambda:self.simple_crud("Suppliers","suppliers",[("name","Name"),("phone","Phone"),("email","Email"),("address","Address")])),("Customers",lambda:self.simple_crud("Customers","customers",[("name","Name"),("phone","Phone"),("email","Email"),("address","Address")])),("Stock Adjustment",self.stock_adjustment),("Reports",self.reports),("Users",self.users),("Database Backup",self.database_backup)])
        for name,command in pages: ctk.CTkButton(self.sidebar,text=name,anchor="w",fg_color="transparent",hover_color="#284966",command=command).pack(fill="x",padx=12,pady=3)
        ctk.CTkButton(self.sidebar,text="Sign out",anchor="w",fg_color="transparent",command=self.sign_out).pack(side="bottom",fill="x",padx=12,pady=22)
        self.content=ctk.CTkFrame(self,fg_color="transparent"); self.content.pack(side="left",fill="both",expand=True,padx=25,pady=22); self.dashboard()
    def sign_out(self): self.clear_remembered_user(); self.sidebar.destroy(); self.content.destroy(); self.user=None; self.login=Login(self); self.login.pack(fill="both",expand=True)
    def page(self,title,subtitle=""):
        for w in self.content.winfo_children():w.destroy()
        ctk.CTkLabel(self.content,text=title,font=ctk.CTkFont(size=28,weight="bold")).pack(anchor="w")
        ctk.CTkLabel(self.content,text=subtitle,text_color="gray").pack(anchor="w",pady=(0,18))
    def dashboard(self):
        self.page("Dashboard",f"Welcome back, {self.user['full_name']}")
        try:
            metrics=[("Products",self.db.query("SELECT COUNT(*) count FROM products",one=True)['count']),("Units in stock",self.db.query("SELECT COALESCE(SUM(quantity),0) count FROM products",one=True)['count']),("Low stock",self.db.query("SELECT COUNT(*) count FROM products WHERE quantity<=reorder_level",one=True)['count']),("Today sales",self.db.query("SELECT COALESCE(SUM(total),0) count FROM sales WHERE DATE(created_at)=CURDATE()",one=True)['count'])]
            cards=ctk.CTkFrame(self.content,fg_color="transparent"); cards.pack(fill="x");
            for name,value in metrics:
                card=ctk.CTkFrame(cards); card.pack(side="left",fill="x",expand=True,padx=5); ctk.CTkLabel(card,text=name,text_color="gray").pack(anchor="w",padx=16,pady=(14,2)); ctk.CTkLabel(card,text=str(value),font=ctk.CTkFont(size=25,weight="bold")).pack(anchor="w",padx=16,pady=(0,14))
            ctk.CTkLabel(self.content,text="Low-stock products",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",pady=(26,8)); t=Table(self.content,["SKU","Name","Quantity","Reorder Level"]); t.pack(fill="both",expand=True); t.load(self.db.query("SELECT sku SKU,name Name,quantity Quantity,reorder_level `Reorder Level` FROM products WHERE quantity<=reorder_level ORDER BY quantity"))
        except Error as e: messagebox.showerror("Database error",str(e))
    def products(self):
        self.page("Products","Select a product, then edit or remove it. Categories and suppliers are optional."); form=ctk.CTkFrame(self.content); form.pack(fill="x",pady=(0,12)); fields=[("sku","SKU"),("name","Product name"),("quantity","Quantity"),("reorder_level","Reorder level"),("unit_price","Unit price")]; self.pentries={}
        if self.user['role'] != "Administrator":
            ctk.CTkLabel(self.content,text="Staff can view products. An administrator manages product records and stock.",text_color="gray").pack(anchor="w",pady=(0,12))
            self.ptable=Table(self.content,["ID","SKU","Name","Category","Supplier","Quantity","Reorder Level","Unit Price"]); self.ptable.pack(fill="both",expand=True); self.load_products(); form.destroy(); return
        details=ctk.CTkFrame(form,fg_color="transparent"); details.pack(fill="x")
        for key,label in fields:
            box=ctk.CTkEntry(details,placeholder_text=label); box.pack(side="left",padx=5,pady=10,fill="x",expand=True); self.pentries[key]=box
        options=ctk.CTkFrame(form,fg_color="transparent"); options.pack(fill="x",pady=(0,8))
        self.category_options={"-- No category --":None}; self.supplier_options={"-- No supplier --":None}
        for row in self.db.query("SELECT id,name FROM categories ORDER BY name"):
            self.category_options[f"{row['id']} - {row['name']}"]=row['id']
        for row in self.db.query("SELECT id,name FROM suppliers ORDER BY name"):
            self.supplier_options[f"{row['id']} - {row['name']}"]=row['id']
        self.category_menu=ctk.CTkOptionMenu(options,values=list(self.category_options),width=260); self.category_menu.pack(side="left",padx=5)
        self.supplier_menu=ctk.CTkOptionMenu(options,values=list(self.supplier_options),width=260); self.supplier_menu.pack(side="left",padx=5)
        ctk.CTkButton(options,text="Save",command=self.save_product).pack(side="right",padx=5); ctk.CTkButton(options,text="Delete",fg_color="#a33",command=self.delete_product).pack(side="right",padx=5)
        self.ptable=Table(self.content,["ID","SKU","Name","Category","Supplier","Quantity","Reorder Level","Unit Price"],self.fill_product); self.ptable.pack(fill="both",expand=True); self.load_products()
    def load_products(self): self.ptable.load(self.db.query("SELECT p.id,p.sku,p.name,p.category_id,p.supplier_id,COALESCE(c.name,'') category,COALESCE(s.name,'') supplier,p.quantity,p.reorder_level,p.unit_price FROM products p LEFT JOIN categories c ON c.id=p.category_id LEFT JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.name"))
    def fill_product(self,row):
        for k,e in self.pentries.items(): e.delete(0,"end"); e.insert(0,str(Table.value(row, k)))
        category_id=Table.value(row,"category_id"); supplier_id=Table.value(row,"supplier_id")
        self.category_menu.set(next((label for label, value in self.category_options.items() if str(value)==str(category_id)),"-- No category --"))
        self.supplier_menu.set(next((label for label, value in self.supplier_options.items() if str(value)==str(supplier_id)),"-- No supplier --"))
    def save_product(self):
        try:
            v={k:e.get().strip() for k,e in self.pentries.items()}; selected=self.ptable.selected
            if not v['sku'] or not v['name']:
                raise ValueError("SKU and product name are required.")
            if not v['quantity']:
                v['quantity'] = "0"
            if not v['reorder_level']:
                v['reorder_level'] = "5"
            if not v['unit_price']:
                v['unit_price'] = "0"
            if not v['quantity'].isdigit() or not v['reorder_level'].isdigit():
                raise ValueError("Quantity and reorder level must be whole numbers (for example: 0, 5, or 20).")
            params=(v['sku'],v['name'],self.category_options[self.category_menu.get()],self.supplier_options[self.supplier_menu.get()],int(v['quantity']),int(v['reorder_level']),Decimal(v['unit_price']))
            if selected: self.db.execute("UPDATE products SET sku=%s,name=%s,category_id=%s,supplier_id=%s,quantity=%s,reorder_level=%s,unit_price=%s WHERE id=%s",params+(selected['id'],))
            else: self.db.execute("INSERT INTO products (sku,name,category_id,supplier_id,quantity,reorder_level,unit_price) VALUES (%s,%s,%s,%s,%s,%s,%s)",params)
            self.products()
        except (ValueError, ArithmeticError) as e: messagebox.showerror("Check product details",str(e))
        except Error as e: messagebox.showerror("Could not save product",str(e))
    def delete_product(self):
        if self.ptable.selected and messagebox.askyesno("Delete product","Delete the selected product?"):
            try: self.db.execute("DELETE FROM products WHERE id=%s",(self.ptable.selected['id'],)); self.products()
            except Error as e: messagebox.showerror("Could not delete",str(e))
    def simple_crud(self,title,table,fields):
        self.page(title); form=ctk.CTkFrame(self.content); form.pack(fill="x",pady=(0,12)); self.crud_entries={}; self.crud_table_name=table; self.crud_fields=fields
        for key,label in fields:
            e=ctk.CTkEntry(form,placeholder_text=label); e.pack(side="left",padx=5,pady=10,fill="x",expand=True); self.crud_entries[key]=e
        ctk.CTkButton(form,text="Save",command=self.save_crud).pack(side="left",padx=5); ctk.CTkButton(form,text="Delete",fg_color="#a33",command=self.delete_crud).pack(side="left",padx=5)
        cols=["ID"]+[label for _,label in fields]; self.crud_table=Table(self.content,cols,self.fill_crud); self.crud_table.pack(fill="both",expand=True); self.crud_table.load(self.db.query(f"SELECT id,{','.join(k for k,_ in fields)} FROM {table} ORDER BY id DESC"))
    def fill_crud(self,row):
        for k,l in self.crud_fields: self.crud_entries[k].delete(0,"end"); self.crud_entries[k].insert(0,str(Table.value(row, k)))
    def save_crud(self):
        try:
            vals=tuple(e.get().strip() for e in self.crud_entries.values()); keys=','.join(k for k,_ in self.crud_fields); placeholders=','.join(['%s']*len(vals)); selected=self.crud_table.selected
            if selected: self.db.execute(f"UPDATE {self.crud_table_name} SET "+','.join(k+'=%s' for k,_ in self.crud_fields)+" WHERE id=%s",vals+(selected['id'],))
            else:self.db.execute(f"INSERT INTO {self.crud_table_name} ({keys}) VALUES ({placeholders})",vals)
            self.simple_crud(self.content.winfo_children()[0].cget('text'),self.crud_table_name,self.crud_fields)
        except Error as e: messagebox.showerror("Could not save",str(e))
    def delete_crud(self):
        if self.crud_table.selected and messagebox.askyesno("Delete record","Delete the selected record?"):
            try:self.db.execute(f"DELETE FROM {self.crud_table_name} WHERE id=%s",(self.crud_table.selected['id'],)); self.simple_crud(self.content.winfo_children()[0].cget('text'),self.crud_table_name,self.crud_fields)
            except Error as e: messagebox.showerror("Could not delete",str(e))
    def sales(self):
        self.sale_cart=[]
        self.page("New Sale","Choose a customer and product, then complete the sale. You can use the drop-down or enter an SKU.")
        top=ctk.CTkFrame(self.content); top.pack(fill="x")
        self.customer_options={"Walk-in Customer":None}
        for row in self.db.query("SELECT id,name FROM customers ORDER BY name"):
            self.customer_options[f"{row['id']} - {row['name']}"]=row['id']
        ctk.CTkLabel(top,text="Customer:").pack(side="left",padx=(8,0))
        self.customer_menu=ctk.CTkOptionMenu(top,values=list(self.customer_options),width=200); self.customer_menu.pack(side="left",padx=8,pady=10)
        product_row=ctk.CTkFrame(self.content); product_row.pack(fill="x",pady=(8,0))
        products=self.db.query("SELECT id,sku,name FROM products ORDER BY name")
        self.sale_product_options={f"{row['sku']} - {row['name']}":row['id'] for row in products}
        self.sale_product=ctk.CTkComboBox(product_row,values=list(self.sale_product_options),command=self.pick_sale_product,width=390)
        self.sale_product.set(""); self.sale_product.pack(side="left",padx=8,pady=10,fill="x",expand=True)
        self.sale_sku=ctk.CTkEntry(product_row,placeholder_text="Or enter product SKU",width=185); self.sale_sku.pack(side="left",padx=8,pady=10)
        self.sale_qty=ctk.CTkEntry(product_row,placeholder_text="Quantity",width=110); self.sale_qty.pack(side="left",padx=8,pady=10)
        self.sale_qty.insert(0,"1")
        ctk.CTkButton(product_row,text="Add to cart",command=self.add_to_cart).pack(side="left",padx=8)
        self.sale_sku.bind("<Return>",lambda e:self.add_to_cart())
        self.cart_area=ctk.CTkFrame(self.content,fg_color="transparent"); self.cart_area.pack(fill="both",expand=True,pady=(18,0))
        self.refresh_sale_cart()

    def pick_sale_product(self, choice):
        if choice in self.sale_product_options:
            self.sale_sku.delete(0,"end"); self.sale_sku.insert(0,choice.split(" - ",1)[0])

    def add_to_cart(self):
        try:
            sku=self.sale_sku.get().strip(); quantity=int(self.sale_qty.get().strip())
            if quantity <= 0: raise ValueError("Quantity must be greater than zero.")
            if sku:
                product=self.db.query("SELECT id,sku,name,quantity,unit_price FROM products WHERE sku=%s",(sku,),one=True)
            else:
                search=self.sale_product.get().strip()
                if search in self.sale_product_options:
                    product=self.db.query("SELECT id,sku,name,quantity,unit_price FROM products WHERE id=%s",(self.sale_product_options[search],),one=True)
                else:
                    matches=self.db.query("SELECT id,sku,name,quantity,unit_price FROM products WHERE name LIKE %s ORDER BY name LIMIT 2",(f"%{search}%",)) if search else []
                    if len(matches)>1: raise ValueError("More than one product matches. Choose the product from the drop-down list.")
                    product=matches[0] if matches else None
            if not product: raise ValueError("No product was found. Choose a product from the drop-down or enter a valid SKU.")
            existing=next((item for item in self.sale_cart if item['id']==product['id']),None)
            requested=quantity+(existing['quantity'] if existing else 0)
            if requested > product['quantity']: raise ValueError(f"Only {product['quantity']} unit(s) of {product['name']} are in stock.")
            if existing: existing['quantity']=requested
            else: self.sale_cart.append({"id":product['id'],"sku":product['sku'],"product":product['name'],"quantity":quantity,"unit_price":Decimal(product['unit_price'])})
            self.sale_product.set(""); self.sale_sku.delete(0,"end"); self.sale_qty.delete(0,"end"); self.sale_qty.insert(0,"1"); self.sale_product.focus(); self.refresh_sale_cart()
        except ValueError as e: messagebox.showerror("Cannot add item",str(e))
        except Error as e: messagebox.showerror("Database error",str(e))

    def refresh_sale_cart(self):
        for child in self.cart_area.winfo_children(): child.destroy()
        ctk.CTkLabel(self.cart_area,text="Cart",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",pady=(0,8))
        rows=[]
        for item in self.sale_cart:
            rows.append({"id":item['id'],"sku":item['sku'],"product":item['product'],"quantity":item['quantity'],"unit price":f"{item['unit_price']:.2f}","total":f"{item['unit_price']*item['quantity']:.2f}"})
        self.sale_table=Table(self.cart_area,["SKU","Product","Quantity","Unit Price","Total"]); self.sale_table.pack(fill="both",expand=True); self.sale_table.load(rows)
        controls=ctk.CTkFrame(self.cart_area,fg_color="transparent"); controls.pack(fill="x",pady=12)
        total=sum((item['unit_price']*item['quantity'] for item in self.sale_cart),Decimal("0"))
        ctk.CTkLabel(controls,text=f"Total: {total:.2f}",font=ctk.CTkFont(size=21,weight="bold")).pack(side="left")
        ctk.CTkButton(controls,text="Remove selected",fg_color="#a33",command=self.remove_cart_item).pack(side="right",padx=(8,0))
        ctk.CTkButton(controls,text="Complete sale",command=self.complete_sale).pack(side="right")

    def remove_cart_item(self):
        if not self.sale_table.selected:
            messagebox.showwarning("Select an item","Click an item in the cart first."); return
        self.sale_cart=[item for item in self.sale_cart if item['id'] != self.sale_table.selected['id']]
        self.refresh_sale_cart()

    def complete_sale(self):
        try:
            if not self.sale_cart: raise ValueError("Add at least one product to the cart first.")
            conn=self.db.connect(); cur=conn.cursor()
            try:
                total=sum((item['unit_price']*item['quantity'] for item in self.sale_cart),Decimal("0"))
                for item in self.sale_cart:
                    cur.execute("SELECT name,quantity FROM products WHERE id=%s FOR UPDATE",(item['id'],)); product=cur.fetchone()
                    if not product or product[1] < item['quantity']: raise ValueError(f"Insufficient stock for {item['product']}. Refresh the cart and try again.")
                customer_id=self.customer_options.get(self.customer_menu.get())
                cur.execute("INSERT INTO sales (customer_id,total,created_by) VALUES (%s,%s,%s)",(customer_id,total,self.user['id'])); sale=cur.lastrowid
                for item in self.sale_cart:
                    cur.execute("INSERT INTO sale_items (sale_id,product_id,quantity,unit_price) VALUES (%s,%s,%s,%s)",(sale,item['id'],item['quantity'],item['unit_price']))
                    cur.execute("UPDATE products SET quantity=quantity-%s WHERE id=%s",(item['quantity'],item['id']))
                    cur.execute("INSERT INTO inventory_log (product_id,change_quantity,reason,created_by) VALUES (%s,%s,%s,%s)",(item['id'],-item['quantity'],f"Sale #{sale}",self.user['id']))
                conn.commit()
            except: conn.rollback(); raise
            finally:cur.close();conn.close()
            messagebox.showinfo("Sale completed",f"Sale #{sale} recorded. Total: {total:.2f}"); self.sales()
        except Exception as e: messagebox.showerror("Sale not completed",str(e))

    def sales_history(self):
        self.page("Sales History","Search completed sales and open a receipt for any selected sale.")
        filters=ctk.CTkFrame(self.content); filters.pack(fill="x",pady=(0,12))
        self.sale_date=ctk.CTkEntry(filters,placeholder_text="Date (YYYY-MM-DD), optional",width=240); self.sale_date.pack(side="left",padx=8,pady=10)
        ctk.CTkButton(filters,text="Search",command=self.load_sales_history).pack(side="left",padx=5)
        ctk.CTkButton(filters,text="Clear",command=self.sales_history).pack(side="left",padx=5)
        self.sales_history_table=Table(self.content,["Sale ID","Customer","Cashier","Total","Date"],self.select_sale); self.sales_history_table.pack(fill="both",expand=True)
        actions=ctk.CTkFrame(self.content,fg_color="transparent"); actions.pack(fill="x",pady=(12,0))
        ctk.CTkButton(actions,text="View selected sale",command=self.view_sale).pack(side="left",padx=5)
        ctk.CTkButton(actions,text="Open receipt",command=self.open_receipt).pack(side="left",padx=5)
        self.load_sales_history()

    def load_sales_history(self):
        try:
            date=self.sale_date.get().strip()
            if date:
                datetime.strptime(date,"%Y-%m-%d")
                rows=self.db.query("""SELECT s.id `Sale ID`,COALESCE(c.name,'Walk-in Customer') Customer,u.full_name Cashier,
                    s.total Total,DATE_FORMAT(s.created_at,'%Y-%m-%d %H:%i') Date FROM sales s
                    LEFT JOIN customers c ON c.id=s.customer_id JOIN users u ON u.id=s.created_by
                    WHERE DATE(s.created_at)=%s ORDER BY s.created_at DESC""",(date,))
            else:
                rows=self.db.query("""SELECT s.id `Sale ID`,COALESCE(c.name,'Walk-in Customer') Customer,u.full_name Cashier,
                    s.total Total,DATE_FORMAT(s.created_at,'%Y-%m-%d %H:%i') Date FROM sales s
                    LEFT JOIN customers c ON c.id=s.customer_id JOIN users u ON u.id=s.created_by ORDER BY s.created_at DESC LIMIT 200""")
            self.sales_history_table.load(rows)
        except ValueError: messagebox.showwarning("Invalid date","Use the format YYYY-MM-DD, for example 2026-07-10.")
        except Error as e: messagebox.showerror("Could not load sales",str(e))

    def select_sale(self, row):
        self.selected_sale_id=Table.value(row,"sale id")

    def selected_sale(self):
        row=getattr(self,'sales_history_table',None).selected if hasattr(self,'sales_history_table') else None
        if not row: messagebox.showwarning("Select a sale","Click a sale in the table first."); return None
        return Table.value(row,"sale id")

    def sale_details(self, sale_id):
        sale=self.db.query("""SELECT s.id,COALESCE(c.name,'Walk-in Customer') customer,u.full_name cashier,s.total,s.created_at
            FROM sales s LEFT JOIN customers c ON c.id=s.customer_id JOIN users u ON u.id=s.created_by WHERE s.id=%s""",(sale_id,),one=True)
        items=self.db.query("""SELECT p.sku,p.name,si.quantity,si.unit_price,(si.quantity*si.unit_price) total
            FROM sale_items si JOIN products p ON p.id=si.product_id WHERE si.sale_id=%s ORDER BY si.id""",(sale_id,))
        return sale,items

    def view_sale(self):
        sale_id=self.selected_sale()
        if not sale_id: return
        try:
            sale,items=self.sale_details(sale_id)
            window=ctk.CTkToplevel(self); window.title(f"Sale #{sale_id}"); window.geometry("650x430")
            ctk.CTkLabel(window,text=f"Sale #{sale['id']}",font=ctk.CTkFont(size=24,weight="bold")).pack(anchor="w",padx=22,pady=(22,3))
            ctk.CTkLabel(window,text=f"Customer: {sale['customer']}    Cashier: {sale['cashier']}    Date: {sale['created_at']}").pack(anchor="w",padx=22,pady=(0,14))
            table=Table(window,["SKU","Name","Quantity","Unit Price","Total"]); table.pack(fill="both",expand=True,padx=22)
            table.load(items); ctk.CTkLabel(window,text=f"Total: {sale['total']:.2f}",font=ctk.CTkFont(size=20,weight="bold")).pack(anchor="e",padx=22,pady=16)
        except Error as e: messagebox.showerror("Could not load sale",str(e))

    def open_receipt(self):
        sale_id=self.selected_sale()
        if not sale_id: return
        try:
            sale,items=self.sale_details(sale_id); os.makedirs(os.path.join(BASE_DIR,"receipts"),exist_ok=True)
            path=os.path.join(BASE_DIR,"receipts",f"receipt_sale_{sale_id}.txt")
            lines=["STABLE SUPERMARKET","Sales Receipt",f"Receipt: #{sale_id}",f"Date: {sale['created_at']}",f"Customer: {sale['customer']}",f"Cashier: {sale['cashier']}","-"*44]
            for item in items: lines.append(f"{item['name']}\n  {item['quantity']} x {item['unit_price']:.2f} = {item['total']:.2f}")
            lines.extend(["-"*44,f"TOTAL: {sale['total']:.2f}","Thank you for shopping with us."])
            with open(path,"w",encoding="utf-8") as file: file.write("\n".join(lines))
            os.startfile(path)
        except Error as e: messagebox.showerror("Could not create receipt",str(e))
        except OSError as e: messagebox.showerror("Could not open receipt",str(e))

    def stock_adjustment(self):
        self.page("Stock Adjustment","Restock products or record damaged/missing stock. Every change is added to the audit log.")
        form=ctk.CTkFrame(self.content); form.pack(fill="x",pady=(0,12))
        products=self.db.query("SELECT id,sku,name FROM products ORDER BY name")
        self.adjust_options={f"{row['sku']} - {row['name']}":row['id'] for row in products}
        self.adjust_product=ctk.CTkComboBox(form,values=list(self.adjust_options),width=400); self.adjust_product.set(""); self.adjust_product.pack(side="left",padx=8,pady=10,fill="x",expand=True)
        self.adjust_quantity=ctk.CTkEntry(form,placeholder_text="Quantity",width=120); self.adjust_quantity.pack(side="left",padx=8,pady=10)
        self.adjust_type=ctk.CTkOptionMenu(form,values=["Restock (+)","Damage / Missing (-)"]); self.adjust_type.pack(side="left",padx=8,pady=10)
        self.adjust_reason=ctk.CTkEntry(self.content,placeholder_text="Optional note, for example: Delivery received"); self.adjust_reason.pack(fill="x",padx=8,pady=(0,8))
        ctk.CTkButton(self.content,text="Save stock adjustment",command=self.save_stock_adjustment).pack(anchor="e",padx=8,pady=(0,16))
        ctk.CTkLabel(self.content,text="Recent stock adjustments",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",pady=(0,8))
        self.adjustment_table=Table(self.content,["Product","Change","Reason","Date"]); self.adjustment_table.pack(fill="both",expand=True); self.load_adjustments()

    def load_adjustments(self):
        self.adjustment_table.load(self.db.query("""SELECT p.name Product,l.change_quantity `Change`,l.reason Reason,
            DATE_FORMAT(l.created_at,'%Y-%m-%d %H:%i') Date FROM inventory_log l JOIN products p ON p.id=l.product_id
            WHERE l.reason NOT LIKE 'Sale #%' ORDER BY l.created_at DESC LIMIT 100"""))

    def save_stock_adjustment(self):
        try:
            product_id=self.adjust_options.get(self.adjust_product.get()); quantity=int(self.adjust_quantity.get().strip())
            if not product_id: raise ValueError("Choose a product from the drop-down list.")
            if quantity<=0: raise ValueError("Quantity must be greater than zero.")
            adjustment=quantity if self.adjust_type.get()=="Restock (+)" else -quantity
            reason=self.adjust_reason.get().strip() or self.adjust_type.get()
            conn=self.db.connect(); cur=conn.cursor()
            try:
                cur.execute("SELECT quantity FROM products WHERE id=%s FOR UPDATE",(product_id,)); product=cur.fetchone()
                if not product: raise ValueError("Product no longer exists.")
                if product[0]+adjustment<0: raise ValueError("This would make stock negative.")
                cur.execute("UPDATE products SET quantity=quantity+%s WHERE id=%s",(adjustment,product_id))
                cur.execute("INSERT INTO inventory_log (product_id,change_quantity,reason,created_by) VALUES (%s,%s,%s,%s)",(product_id,adjustment,reason,self.user['id']))
                conn.commit()
            except: conn.rollback(); raise
            finally: cur.close(); conn.close()
            messagebox.showinfo("Stock updated","The stock adjustment was saved."); self.stock_adjustment()
        except ValueError as e: messagebox.showerror("Could not save adjustment",str(e))
        except Error as e: messagebox.showerror("Database error",str(e))
    def reports(self):
        self.page("Reports","Low stock and recent inventory activity."); ctk.CTkLabel(self.content,text="Recent inventory movements",font=ctk.CTkFont(size=18,weight="bold")).pack(anchor="w",pady=(0,8)); t=Table(self.content,["Product","Change","Reason","Date"]); t.pack(fill="both",expand=True); t.load(self.db.query("SELECT p.name Product,l.change_quantity `Change`,l.reason Reason,DATE_FORMAT(l.created_at,'%Y-%m-%d %H:%i') Date FROM inventory_log l JOIN products p ON p.id=l.product_id ORDER BY l.created_at DESC LIMIT 100"))
    def users(self):
        self.page("Users","Create staff accounts and control their access. Leave password blank when editing to keep it unchanged.")
        form=ctk.CTkFrame(self.content); form.pack(fill="x",pady=(0,12))
        self.user_username=ctk.CTkEntry(form,placeholder_text="Username"); self.user_username.pack(side="left",padx=5,pady=10,fill="x",expand=True)
        self.user_full_name=ctk.CTkEntry(form,placeholder_text="Full name"); self.user_full_name.pack(side="left",padx=5,pady=10,fill="x",expand=True)
        self.user_password=ctk.CTkEntry(form,placeholder_text="Password (8+ characters)",show="*"); self.user_password.pack(side="left",padx=5,pady=10,fill="x",expand=True)
        self.user_role=ctk.CTkOptionMenu(form,values=["Staff","Administrator"]); self.user_role.pack(side="left",padx=5,pady=10)
        ctk.CTkButton(form,text="Save user",command=self.save_user).pack(side="left",padx=5)
        self.users_table=Table(self.content,["ID","Username","Full Name","Role","Created"],self.fill_user); self.users_table.pack(fill="both",expand=True); self.load_users()

    def load_users(self):
        self.users_table.load(self.db.query("SELECT id,username,full_name,role,DATE_FORMAT(created_at,'%Y-%m-%d') created FROM users ORDER BY full_name"))

    def fill_user(self,row):
        self.user_username.delete(0,"end"); self.user_username.insert(0,str(Table.value(row,"username")))
        self.user_full_name.delete(0,"end"); self.user_full_name.insert(0,str(Table.value(row,"full name")))
        self.user_password.delete(0,"end"); self.user_role.set(str(Table.value(row,"role")))

    def save_user(self):
        try:
            username=self.user_username.get().strip(); full_name=self.user_full_name.get().strip(); password=self.user_password.get(); role=self.user_role.get(); selected=self.users_table.selected
            if not username or not full_name: raise ValueError("Username and full name are required.")
            if selected:
                user_id=Table.value(selected,"id")
                if password:
                    if len(password)<8: raise ValueError("Passwords must have at least 8 characters.")
                    self.db.execute("UPDATE users SET username=%s,full_name=%s,role=%s,password_hash=%s WHERE id=%s",(username,full_name,role,bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),user_id))
                else: self.db.execute("UPDATE users SET username=%s,full_name=%s,role=%s WHERE id=%s",(username,full_name,role,user_id))
            else:
                if len(password)<8: raise ValueError("New users need a password with at least 8 characters.")
                self.db.execute("INSERT INTO users (username,password_hash,full_name,role) VALUES (%s,%s,%s,%s)",(username,bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),full_name,role))
            self.users()
        except ValueError as e: messagebox.showerror("Could not save user",str(e))
        except Error as e: messagebox.showerror("Could not save user",str(e))

    def database_backup(self):
        self.page("Database Backup","Create a local SQL backup of your inventory database. Store backups somewhere safe.")
        ctk.CTkLabel(self.content,text="Click the button to create a dated backup file in the project's backups folder.",text_color="gray").pack(anchor="w",pady=(0,18))
        ctk.CTkButton(self.content,text="Create database backup",command=self.create_database_backup,width=260).pack(anchor="w")

    def create_database_backup(self):
        try:
            tool=shutil.which("mysqldump") or r"C:\xampp\mysql\bin\mysqldump.exe"
            if not os.path.isfile(tool): raise FileNotFoundError("Could not find mysqldump. Confirm XAMPP is installed in C:\\xampp.")
            os.makedirs(os.path.join(BASE_DIR,"backups"),exist_ok=True); stamp=datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            path=os.path.join(BASE_DIR,"backups",f"inventory_backup_{stamp}.sql")
            command=[tool,"--host",os.getenv("DB_HOST","localhost"),"--port",os.getenv("DB_PORT","3306"),"--user",os.getenv("DB_USER","root"),"--single-transaction",os.getenv("DB_NAME","inventory_management")]
            env=os.environ.copy(); env["MYSQL_PWD"]=os.getenv("DB_PASSWORD","")
            with open(path,"w",encoding="utf-8") as output:
                result=subprocess.run(command,stdout=output,stderr=subprocess.PIPE,text=True,env=env,check=False)
            if result.returncode != 0:
                os.remove(path); raise RuntimeError(result.stderr.strip() or "mysqldump failed.")
            messagebox.showinfo("Backup complete",f"Backup created:\n{path}")
        except (OSError, RuntimeError) as e: messagebox.showerror("Backup failed",str(e))

if __name__ == '__main__':
    App().mainloop()
